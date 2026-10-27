# Google Cloud: setting up an environment

How the app runs on Google Cloud, written for **dev** first (`saas-afterschoolcare-dev`, `dev.sessionpilot.com.au`). Production repeats it with `env/prod.env`. Everything is in **Sydney (`australia-southeast1`)**; the database is Neon (AWS Sydney) for now.

```
            dev.sessionpilot.com.au, *.dev.sessionpilot.com.au
                                  │
             regional external load balancer (static IP, wildcard certificate)
               │                       │                          │
           /api/...               /_app/..., files            any other path
               │                       │                          │
       Cloud Run "api"            site bucket                site bucket's index.html
     (deploy/docker/backend…)  (npm run build output)     (the app routes in the browser)
```

The backend and the frontend are released separately: the API is an image deployed to Cloud Run, the site is static files copied to a bucket. When an API change would break the current site, release the API first.

**Commands are PowerShell** (Windows PowerShell 5.1 or PowerShell 7), run from the **repo root**. Start every session by loading the environment's names, and check it worked with `$PROJECT_ID`:

```powershell
cd ~/source/repos/saas-afterschoolcare

foreach ($line in Get-Content deploy/gcp/env/dev.env) {
  if ($line -match '^([A-Z_]+)=(.*)$') { Set-Variable -Name $Matches[1] -Value $Matches[2] }
}
$API_SA = "$API_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com"
$BUILD_SA = "$BUILD_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com"
$TMP = (New-Item -ItemType Directory -Path (Join-Path $env:TEMP "deploy-$(Get-Random)")).FullName
```

Three things that differ from guides written for bash: lines continue with a backtick (`` ` ``) at the very end, with nothing after it; `curl` is a different command in Windows PowerShell, so the checks use `curl.exe`; and text piped into a program gains a newline, so secrets go through a file (step 6) instead.

| File | What it is |
|---|---|
| `env/dev.env` | The environment's names (projects, domains, buckets). No secrets. |
| `env/api.dev.yaml` | The API's settings that aren't secret (Cloud Run environment). |
| `cloudbuild.backend.yaml` | Builds the API image and pushes it to Artifact Registry. |
| `cloudbuild.frontend.yaml` | Builds the site for one environment and copies it to its bucket. |
| `build.gcloudignore` | What a build uploads: only the app's code. `.env` files never leave your machine. |
| `url-map.yaml`, `url-map-http.yaml` | The load balancer's routes (HTTPS), and HTTP sending everyone to HTTPS. |

Each step says what to check before moving on. Steps 1 to 6 are once per environment; 8 and 9 are every release.

---

## 1. Projects and services

You need `gcloud` installed and `gcloud auth login` done. Find your billing account:

```powershell
gcloud billing accounts list
$BILLING = "<the ACCOUNT_ID from the list>"
```

The DNS project (once, shared by every environment). Project ids are global, so if `sessionpilot-dns` is taken, pick another and change `DNS_PROJECT_ID` in every `env/*.env`.

```powershell
gcloud projects create "$DNS_PROJECT_ID" --name="Session Pilot DNS"
gcloud billing projects link "$DNS_PROJECT_ID" --billing-account="$BILLING"
gcloud services enable dns.googleapis.com --project="$DNS_PROJECT_ID"
```

The environment's project already exists. Check billing is linked and turn on what it uses:

```powershell
gcloud billing projects describe "$PROJECT_ID" --format="value(billingEnabled)"   # True

gcloud services enable `
  run.googleapis.com artifactregistry.googleapis.com cloudbuild.googleapis.com `
  secretmanager.googleapis.com compute.googleapis.com certificatemanager.googleapis.com `
  dns.googleapis.com iamcredentials.googleapis.com storage.googleapis.com `
  --project="$PROJECT_ID"
```

## 2. DNS: move sessionpilot.com.au to Cloud DNS

Nothing uses the domain yet, so there are no records to copy across first. (If that changes before you do this, copy every record into the new zone before step 2.3.)

**2.1 The root zone** (in the DNS project):

```powershell
gcloud dns managed-zones create "$ROOT_ZONE" --dns-name="$ROOT_DOMAIN." `
  --description="sessionpilot.com.au, every environment" --project="$DNS_PROJECT_ID"

gcloud dns managed-zones describe "$ROOT_ZONE" --project="$DNS_PROJECT_ID" --format="value(nameServers)"
```

**2.2 DNSSEC:** in VentraIP, check the domain has no DNSSEC (DS) records; remove any before the next step, or the domain stops resolving.

**2.3 Nameservers:** in VentraIP, set the domain's nameservers to the four printed in 2.1 (without the trailing dot). Then wait until the world sees them; `.au` changes usually take an hour or two:

```powershell
nslookup -type=NS "$ROOT_DOMAIN" 8.8.8.8   # the four ns-cloud-… servers
```

**2.4 The environment's zone** (in its own project), handed over from the root zone:

```powershell
gcloud dns managed-zones create "$BASE_ZONE" --dns-name="$BASE_DOMAIN." `
  --description="$BASE_DOMAIN" --project="$PROJECT_ID"

$BASE_NS = (gcloud dns managed-zones describe "$BASE_ZONE" --project="$PROJECT_ID" --format="value(nameServers)") -replace ';', ','

gcloud dns record-sets create "$BASE_DOMAIN." --zone="$ROOT_ZONE" --type=NS --ttl=3600 `
  --rrdatas="$BASE_NS" --project="$DNS_PROJECT_ID"
```

Check: `nslookup -type=NS "$BASE_DOMAIN" 8.8.8.8` lists the environment zone's four servers.

## 3. Buckets

All in Sydney, uniform access.

```powershell
# Build uploads (the code sent to Cloud Build), deleted after 30 days.
gcloud storage buckets create "gs://$BUILD_BUCKET" --location="$REGION" `
  --uniform-bucket-level-access --public-access-prevention --project="$PROJECT_ID"
[IO.File]::WriteAllText("$TMP\build-lifecycle.json", '{"rule":[{"action":{"type":"Delete"},"condition":{"age":30}}]}')
gcloud storage buckets update "gs://$BUILD_BUCKET" --lifecycle-file="$TMP\build-lifecycle.json"

# The site: public, because the load balancer can only read public buckets.
# It only ever holds the app's own files.
gcloud storage buckets create "gs://$SITE_BUCKET" --location="$REGION" `
  --uniform-bucket-level-access --project="$PROJECT_ID"
gcloud storage buckets add-iam-policy-binding "gs://$SITE_BUCKET" `
  --member=allUsers --role=roles/storage.objectViewer

# Documents and uploads (child documents, logos, policies): never public.
gcloud storage buckets create "gs://$DOCUMENT_BUCKET" --location="$REGION" `
  --uniform-bucket-level-access --public-access-prevention --project="$PROJECT_ID"
gcloud storage buckets update "gs://$DOCUMENT_BUCKET" `
  --lifecycle-file=deploy/storage/gcs/child-documents-lifecycle.json `
  --cors-file=deploy/storage/gcs/child-documents-cors.json
```

The documents bucket's CORS allows any origin: every business has its own host (and later its own domains), and Cloud Storage can't match `*.dev.sessionpilot.com.au`. That's safe because CORS isn't what protects the bucket: every upload and download needs a short-lived link signed by the API, and no cookies are involved. Local development keeps `child-documents-cors.dev.json` on its own bucket.

## 4. Service accounts

Two accounts, each with only what it needs.

```powershell
# The API (Cloud Run).
gcloud iam service-accounts create "$API_ACCOUNT" --display-name="API (Cloud Run)" --project="$PROJECT_ID"

# Reads and writes documents, and signs their upload and download links
# (signing on Cloud Run goes through IAM as the account itself).
gcloud storage buckets add-iam-policy-binding "gs://$DOCUMENT_BUCKET" `
  --member="serviceAccount:$API_SA" --role=roles/storage.objectAdmin
gcloud iam service-accounts add-iam-policy-binding "$API_SA" `
  --member="serviceAccount:$API_SA" --role=roles/iam.serviceAccountTokenCreator --project="$PROJECT_ID"

# Builds (Cloud Build): reads the uploaded code, pushes images, publishes the site, writes logs.
gcloud iam service-accounts create "$BUILD_ACCOUNT" --display-name="Builds (Cloud Build)" --project="$PROJECT_ID"

gcloud projects add-iam-policy-binding "$PROJECT_ID" `
  --member="serviceAccount:$BUILD_SA" --role=roles/logging.logWriter
gcloud storage buckets add-iam-policy-binding "gs://$BUILD_BUCKET" `
  --member="serviceAccount:$BUILD_SA" --role=roles/storage.objectViewer
gcloud storage buckets add-iam-policy-binding "gs://$SITE_BUCKET" `
  --member="serviceAccount:$BUILD_SA" --role=roles/storage.objectAdmin
# Publishing (rsync) also reads the bucket itself, which objectAdmin doesn't cover.
gcloud storage buckets add-iam-policy-binding "gs://$SITE_BUCKET" `
  --member="serviceAccount:$BUILD_SA" --role=roles/storage.legacyBucketReader
```

Secret access is granted per secret in step 6; the API's certificate and load balancer permissions in step 12.

## 5. Image repository

```powershell
gcloud artifacts repositories create "$REPOSITORY" --repository-format=docker `
  --location="$REGION" --description="App images" --project="$PROJECT_ID"

gcloud artifacts repositories add-iam-policy-binding "$REPOSITORY" --location="$REGION" `
  --member="serviceAccount:$BUILD_SA" --role=roles/artifactregistry.writer --project="$PROJECT_ID"
```

## 6. Secrets

Stored in Sydney only. Values are typed in hidden (not echoed or kept in your history), or generated. Each value goes through a file in `$TMP` that's deleted straight after, so nothing adds a newline to it. Define the helpers (again in any new session that needs them):

```powershell
function Put-Secret([string]$Name, [string]$Value) {
  $file = Join-Path $TMP $Name
  [IO.File]::WriteAllText($file, $Value)
  try {
    if (gcloud secrets describe $Name --project="$PROJECT_ID" --format="value(name)" 2>$null) {
      gcloud secrets versions add $Name --data-file="$file" --project="$PROJECT_ID"
    } else {
      gcloud secrets create $Name --data-file="$file" --replication-policy=user-managed `
        --locations="$REGION" --project="$PROJECT_ID"
    }
  } finally { Remove-Item $file }
  gcloud secrets add-iam-policy-binding $Name --member="serviceAccount:$API_SA" `
    --role=roles/secretmanager.secretAccessor --project="$PROJECT_ID" | Out-Null
}
function Read-Secret([string]$Prompt) {
  $secure = Read-Host $Prompt -AsSecureString
  [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
}
function New-RandomBytes([int]$Count) {
  $bytes = New-Object byte[] $Count
  [Security.Cryptography.RandomNumberGenerator]::Create().GetBytes($bytes)
  , $bytes
}
```

Then:

```powershell
Put-Secret JWT_SECRET_KEY ([Convert]::ToBase64String((New-RandomBytes 48)))
# Cloud Scheduler's proof when it calls the domain check (step 12).
Put-Secret DOMAINS_CHECK_SECRET (-join ((New-RandomBytes 32) | ForEach-Object { $_.ToString('x2') }))
Put-Secret DATABASE_URL (Read-Secret "DATABASE_URL (app_user, see step 7)")
Put-Secret STRIPE_SECRET_KEY (Read-Secret "STRIPE_SECRET_KEY (the deployed dev sandbox's, sk_test_..., step 11)")

# The webhook secrets exist once the endpoints do (step 11); start with
# placeholders so the API can start.
Put-Secret STRIPE_WEBHOOK_SECRET unset
Put-Secret STRIPE_CONNECT_WEBHOOK_SECRET unset
```

To change one later, run the same line again, then release the API (step 8's deploy command). Running instances keep the values they started with until then.

## 7. Database (Neon)

Give dev its **own** Neon branch or database in **AWS Sydney (`ap-southeast-2`)**, separate from the one your local `backend/.env` uses, so a local rebuild doesn't wipe the deployed dev site.

1. In Neon, create it and copy two connection strings, both on the **direct** host (not `-pooler`), with `?sslmode=require`:
   - the owner's: becomes `DATABASE_ADMIN_URL` (the migrator only; never given to Cloud Run)
   - the same with `app_user` and a new password you choose: `DATABASE_URL` (step 6). The migrator creates `app_user` with that password (`APP_DB_PASSWORD`).
2. **Build it with the migrator from your machine.** This rebuilds that database: it wipes it, applies the schema, seeds and dev seeds (APP_ENV=dev), then regenerates `app/db/models.py` and the API types (unchanged if the schema matches). The values set here override `backend/.env` for this one command, and are cleared afterwards. Needs `Read-Secret` from step 6. From `backend/`:

   ```powershell
   $env:DATABASE_ADMIN_URL = Read-Secret "DATABASE_ADMIN_URL"
   $env:DATABASE_URL = Read-Secret "DATABASE_URL"
   $env:APP_DB_PASSWORD = Read-Secret "APP_DB_PASSWORD"
   $env:APP_ENV = "dev"
   $env:STRIPE_DEV_ACCOUNT_ID = "none"   # or acct_..., see below
   try { ./venv/Scripts/python -m migrations.migrator rebuild }
   finally {
     Remove-Item Env:DATABASE_ADMIN_URL, Env:DATABASE_URL, Env:APP_DB_PASSWORD, Env:APP_ENV, Env:STRIPE_DEV_ACCOUNT_ID
   }
   ```

   `STRIPE_DEV_ACCOUNT_ID` is overridden because your `backend/.env` holds the local sandbox's connected account, which this environment's sandbox (step 11) can't use. The first time, leave it `none` (anything that isn't an `acct_` id links nothing; PowerShell can't set it to empty) and connect Stripe on the deployed site. Afterwards, put that account's `acct_...` there before rebuilding, so tenant 1 stays connected.

   Later schema changes: the same commands (dev is rebuilt, not migrated).

**The dev seed's logins (password `123`) are reachable by anyone who finds the site.** Until access to dev is limited (see "Later"), treat dev as public: test data only.

## 8. Release the API

Builds from your working tree; the tag says which commit, and `-dirty` if there were uncommitted changes.

```powershell
git diff --quiet HEAD 2>$null
$DIRTY = if ($LASTEXITCODE) { "-dirty" } else { "" }
$TAG = "$(git rev-parse --short HEAD)$DIRTY"

gcloud builds submit . --config=deploy/gcp/cloudbuild.backend.yaml `
  --ignore-file=deploy/gcp/build.gcloudignore `
  --gcs-source-staging-dir="gs://$BUILD_BUCKET/source" `
  --service-account="projects/$PROJECT_ID/serviceAccounts/$BUILD_SA" `
  --region="$REGION" --project="$PROJECT_ID" `
  --substitutions="_REGION=$REGION,_REPOSITORY=$REPOSITORY,_TAG=$TAG"
```

**First time only: check what was uploaded.** Only `backend/app`, `backend/requirements.txt`, `frontend/` sources and the two build files; no `.env` anywhere (`tar` comes with Windows):

```powershell
$LATEST = gcloud storage ls "gs://$BUILD_BUCKET/source/" | Select-Object -Last 1
gcloud storage cp "$LATEST" "$TMP\source.tgz"
tar -tzf "$TMP\source.tgz" | Where-Object { $_ -notmatch '/app/' } | Sort-Object
if (tar -tzf "$TMP\source.tgz" | Select-String '\.env') { "has .env files: stop" } else { "no .env files" }
```

Deploy it. Only the load balancer can reach the service (`--ingress`); `--allow-unauthenticated` is needed because the load balancer doesn't sign in, and the app does its own authentication.

```powershell
gcloud run deploy "$API_SERVICE" `
  --image="$REGION-docker.pkg.dev/$PROJECT_ID/$REPOSITORY/api:$TAG" `
  --service-account="$API_SA" `
  --ingress=internal-and-cloud-load-balancing --allow-unauthenticated `
  --env-vars-file="deploy/gcp/env/api.$ENV_NAME.yaml" `
  --set-secrets="DATABASE_URL=DATABASE_URL:latest,JWT_SECRET_KEY=JWT_SECRET_KEY:latest,STRIPE_SECRET_KEY=STRIPE_SECRET_KEY:latest,STRIPE_WEBHOOK_SECRET=STRIPE_WEBHOOK_SECRET:latest,STRIPE_CONNECT_WEBHOOK_SECRET=STRIPE_CONNECT_WEBHOOK_SECRET:latest,DOMAINS_CHECK_SECRET=DOMAINS_CHECK_SECRET:latest" `
  --cpu=1 --memory=512Mi --min-instances=0 --max-instances=2 `
  --region="$REGION" --project="$PROJECT_ID"
```

Check: it reports a new revision serving 100% of traffic. Its `run.app` address answers **404**: that's the ingress setting working, not a fault.

If `--allow-unauthenticated` is refused, an organisation policy blocks public services (Domain restricted sharing); tell me and we'll use the other route.

## 9. Release the site

```powershell
gcloud builds submit . --config=deploy/gcp/cloudbuild.frontend.yaml `
  --ignore-file=deploy/gcp/build.gcloudignore `
  --gcs-source-staging-dir="gs://$BUILD_BUCKET/source" `
  --service-account="projects/$PROJECT_ID/serviceAccounts/$BUILD_SA" `
  --region="$REGION" --project="$PROJECT_ID" `
  --substitutions="_PLATFORM_HOST=$BASE_DOMAIN,_SITE_BUCKET=$SITE_BUCKET"
```

Check: `gcloud storage ls "gs://$SITE_BUCKET"` shows `index.html`, `favicon.svg`, `robots.txt` and `_app/`.

If a build is refused for the region, Cloud Build doesn't run builds in Sydney for this project yet: drop `--region` (the build then runs globally; it only ever sees the code, never data).

## 10. Load balancer (once)

**10.1 Network and address.** A regional load balancer needs a network with a subnet for its proxies, even with no virtual machines.

```powershell
gcloud compute networks create "$NETWORK" --subnet-mode=custom --project="$PROJECT_ID"
gcloud compute networks subnets create proxy-only --purpose=REGIONAL_MANAGED_PROXY --role=ACTIVE `
  --network="$NETWORK" --range="$PROXY_SUBNET_RANGE" --region="$REGION" --project="$PROJECT_ID"

gcloud compute addresses create web-ip --region="$REGION" --project="$PROJECT_ID"
$IP = gcloud compute addresses describe web-ip --region="$REGION" --project="$PROJECT_ID" --format="value(address)"
$IP
```

**10.2 Where requests go.**

```powershell
# The API.
gcloud compute network-endpoint-groups create api-neg --network-endpoint-type=serverless `
  --cloud-run-service="$API_SERVICE" --region="$REGION" --project="$PROJECT_ID"
gcloud compute backend-services create api --load-balancing-scheme=EXTERNAL_MANAGED --protocol=HTTP `
  --region="$REGION" --project="$PROJECT_ID"
gcloud compute backend-services add-backend api --network-endpoint-group=api-neg `
  --network-endpoint-group-region="$REGION" --region="$REGION" --project="$PROJECT_ID"

# The site.
gcloud compute backend-buckets create site --gcs-bucket-name="$SITE_BUCKET" `
  --load-balancing-scheme=EXTERNAL_MANAGED --region="$REGION" --project="$PROJECT_ID"

# The routes (url-map.yaml with this project and region filled in; -creplace
# matches case, so "regions/" in the file stays as it is).
$urlMap = (Get-Content -Raw -Encoding UTF8 deploy/gcp/url-map.yaml) -creplace 'PROJECT_ID', $PROJECT_ID -creplace 'REGION', $REGION
[IO.File]::WriteAllText("$TMP\url-map.yaml", $urlMap)
gcloud compute url-maps import web --source="$TMP\url-map.yaml" --region="$REGION" --project="$PROJECT_ID" --quiet
gcloud compute url-maps import web-http --source=deploy/gcp/url-map-http.yaml --region="$REGION" --project="$PROJECT_ID" --quiet
```

**10.3 The certificate**, covering `dev.sessionpilot.com.au` and every `*.dev.sessionpilot.com.au`. Google proves the domain through a DNS record:

```powershell
gcloud certificate-manager dns-authorizations create base-domain --domain="$BASE_DOMAIN" `
  --type=PER_PROJECT_RECORD --location="$REGION" --project="$PROJECT_ID"

$AUTH_NAME, $AUTH_DATA = (gcloud certificate-manager dns-authorizations describe base-domain `
  --location="$REGION" --project="$PROJECT_ID" --format="value(dnsResourceRecord.name,dnsResourceRecord.data)") -split "`t"
gcloud dns record-sets create "$AUTH_NAME" --zone="$BASE_ZONE" --type=CNAME --ttl=300 `
  --rrdatas="$AUTH_DATA" --project="$PROJECT_ID"

gcloud certificate-manager certificates create base-domain --domains="$BASE_DOMAIN,*.$BASE_DOMAIN" `
  --dns-authorizations=base-domain --location="$REGION" --project="$PROJECT_ID"
```

Check, repeating until it says `ACTIVE` (usually 10 to 60 minutes; carry on with 10.4 meanwhile):

```powershell
gcloud certificate-manager certificates describe base-domain --location="$REGION" --project="$PROJECT_ID" --format="value(managed.state)"
```

**10.4 Proxies, forwarding rules and DNS.**

```powershell
gcloud compute target-https-proxies create web-https --url-map=web `
  --certificate-manager-certificates=base-domain `
  --region="$REGION" --project="$PROJECT_ID"
gcloud compute target-http-proxies create web-http --url-map=web-http --region="$REGION" --project="$PROJECT_ID"

gcloud compute forwarding-rules create web-https --load-balancing-scheme=EXTERNAL_MANAGED `
  --network="$NETWORK" --address=web-ip --ports=443 `
  --target-https-proxy=web-https --target-https-proxy-region="$REGION" `
  --region="$REGION" --project="$PROJECT_ID"
gcloud compute forwarding-rules create web-http --load-balancing-scheme=EXTERNAL_MANAGED `
  --network="$NETWORK" --address=web-ip --ports=80 `
  --target-http-proxy=web-http --target-http-proxy-region="$REGION" `
  --region="$REGION" --project="$PROJECT_ID"

gcloud dns record-sets create "$BASE_DOMAIN." --zone="$BASE_ZONE" --type=A --ttl=300 --rrdatas="$IP" --project="$PROJECT_ID"
gcloud dns record-sets create "*.$BASE_DOMAIN." --zone="$BASE_ZONE" --type=A --ttl=300 --rrdatas="$IP" --project="$PROJECT_ID"
```

**10.5 Check it works** (once the certificate is `ACTIVE`; a new load balancer can take a few minutes more):

```powershell
$SITE = "https://tenant1.$BASE_DOMAIN"

# The site: 200, text/html, Cache-Control: no-cache.
curl.exe -sI "$SITE/" | Select-String '^HTTP|content-type|cache-control'

# Deep links: the app's index.html, not a 404. This is the one that decides
# whether the site can stay in a bucket.
curl.exe -s -o NUL -w "%{http_code} %{content_type}\n" "$SITE/location1/login"
curl.exe -s -o NUL -w "%{http_code} %{content_type}\n" "$SITE/business/site"

# The API, through the load balancer: 200 with tenant 1's details.
curl.exe -s "$SITE/api/location-branding/v1/public/business"

# HTTP goes to HTTPS: 301.
curl.exe -sI "http://tenant1.$BASE_DOMAIN/" | Select-String '^HTTP|^location'
```

Then in a browser: `https://tenant1.dev.sessionpilot.com.au/location1/login`, log in, reload a deep page, open Business settings (`/business`), and the platform console at `https://dev.sessionpilot.com.au/platform`.

**If the deep links return 404 or an XML error**, the bucket route doesn't support the rewrite. Stop and tell me: the fallback is a small nginx container for the site in place of the bucket; nothing else changes.

## 11. Stripe (a sandbox of its own)

Deployed dev gets **its own Stripe sandbox**, with webhook endpoints registered in Stripe pointing at the dev site. No Stripe CLI is involved; `stripe listen` stays a local-development tool. Keeping it apart from the sandbox your local API uses means each sees only its own events, payments and connected accounts.

1. In the Stripe dashboard, create a sandbox (e.g. "Deployed dev"). Turn on Connect there as in `deploy/stripe/README.md` section 1, because Connect settings are per sandbox. Put its secret key in with `Put-Secret STRIPE_SECRET_KEY (Read-Secret "STRIPE_SECRET_KEY")` if step 6 used another one.
2. **Webhooks**, in that sandbox: two endpoints, `https://dev.sessionpilot.com.au/api/v1/webhooks/stripe` (your account) and `…/stripe/connect` (connected accounts), with the events listed in `deploy/stripe/README.md` section 2.
3. Put their signing secrets in, then release the API again (step 8's deploy command, same `$TAG`). The release is what makes it read them: a running instance keeps the values it started with, so until then every delivery fails with 400 "No signatures found matching the expected signature":

   ```powershell
   Put-Secret STRIPE_WEBHOOK_SECRET (Read-Secret "STRIPE_WEBHOOK_SECRET (your account endpoint)")
   Put-Secret STRIPE_CONNECT_WEBHOOK_SECRET (Read-Secret "STRIPE_CONNECT_WEBHOOK_SECRET (connected accounts endpoint)")
   ```
4. Log in to Business settings on the deployed site (`https://tenant1.dev.sessionpilot.com.au/business`) and connect Stripe under Payments. Note the connected account's id for later rebuilds (step 7).
5. Optional, for "Connect your Stripe account": add the redirect URI `https://dev.sessionpilot.com.au/api/stripe-account/v1/oauth/callback` to the sandbox's OAuth settings, and put its client id in `env/api.dev.yaml` (`STRIPE_CONNECT_CLIENT_ID`).

Check: make a booking and pay with a test card. The booking becomes paid, and the sandbox's webhook page shows the events answered with `200`.

## 12. Custom domains

The API manages businesses' certificates and the load balancer's redirects itself (Business settings › Domains; `docs/tenant-administration.md`, section 7). It needs three things.

**12.1 Permissions** for the API's account: Certificate Manager, and changing the load balancer's certificates and routes. These predefined roles are broader than needed: fine for dev, to be narrowed to a custom role before production.

```powershell
gcloud projects add-iam-policy-binding "$PROJECT_ID" `
  --member="serviceAccount:$API_SA" --role=roles/certificatemanager.editor
gcloud projects add-iam-policy-binding "$PROJECT_ID" `
  --member="serviceAccount:$API_SA" --role=roles/compute.loadBalancerAdmin
```

**12.2 Settings:** in `env/api.dev.yaml`, set `DOMAINS_TARGET_IP` to the load balancer's address (`$IP`, step 10.1), then release the API (all of step 8, the build too, so the image has the current code). Until it's set, Business settings › Domains says custom domains aren't available.

**12.3 The check every 5 minutes** (Cloud Scheduler, calling the API on the platform's site with the secret from step 6):

```powershell
gcloud services enable cloudscheduler.googleapis.com --project="$PROJECT_ID"

$CHECK_SECRET = gcloud secrets versions access latest --secret=DOMAINS_CHECK_SECRET --project="$PROJECT_ID"
gcloud scheduler jobs create http domain-check `
  --schedule="*/5 * * * *" --time-zone="Australia/Sydney" `
  --uri="https://$BASE_DOMAIN/api/internal/v1/domain-check" --http-method=POST `
  --headers="X-Domain-Check-Secret=$CHECK_SECRET" `
  --attempt-deadline=300s --location="$REGION" --project="$PROJECT_ID" --format="value(name)"
Remove-Variable CHECK_SECRET
```

The secret is kept in the job's settings, readable by anyone who can view the project's scheduler jobs. If you change the secret, update the job's header too (`gcloud scheduler jobs update http domain-check --update-headers=...`).

Check: `gcloud scheduler jobs run domain-check --location="$REGION" --project="$PROJECT_ID"`, then the API's logs show `POST /api/internal/v1/domain-check` answered `200`.

**12.4 Try it** with a domain whose DNS you can change (e.g. `after3recclub.online`): log in to Business settings on a business's site, open **Domains**, add it as the main domain, and add the records shown where that domain's DNS is managed. It usually reaches **Live** within an hour, and the business's generated host then sends visitors to it.

## Later

- **Email:** dev logs emails (`EMAIL_PROVIDER: log`), and in dev the log includes their text. **Not before a recipient allow-list exists** (not built): the SES account has production access and is shared with the live After3 stack, so dev sending to the seeded `@test.com` addresses would bounce and put that account at risk. Then, to send for real, follow `deploy/email/ses/README.md`, subscribe the SNS topic to `https://dev.sessionpilot.com.au/api/v1/webhooks/ses`, add `AWS_ACCESS_KEY_ID` and `AWS_SECRET_ACCESS_KEY` with `Put-Secret` and to `--set-secrets`, and the `SES_*` settings to `env/api.dev.yaml`.
- **Limiting who can reach dev:** not decided yet.
- **Production:** `env/prod.env` and `env/api.prod.yaml`, the root domain's own zone records (`sessionpilot.com.au`, `*.sessionpilot.com.au`), live Stripe keys.
