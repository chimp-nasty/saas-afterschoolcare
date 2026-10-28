<#
.SYNOPSIS
    Releases SessionPilot to the deployed DEV stack (dev.sessionpilot.com.au):
    the API, the site, or both, optionally rebuilding its database and
    wiping its stored files first.

.DESCRIPTION
    Dev only: everything comes from deploy/gcp/env/dev.env (and the API's
    settings from env/api.dev.yaml), as in deploy/gcp/README.md steps 7 to
    9. Before changing anything it checks gcloud, the files and every
    secret the API needs (that each exists and the API can read it), shows
    what it's about to do, and asks you to type "dev".

    -Rebuild wipes dev's database, so it asks again ("wipe"). Tenant 1's
    Stripe connected account is read from the database first and linked
    again by the dev seed, so it never needs reattaching.

    -WipeBuckets (with -Rebuild) also deletes every stored file: uploaded
    documents and site photos (the documents bucket) and old build uploads.
    Only with a rebuild: on its own it would leave the database pointing at
    files that are gone. The site bucket needs no wipe: every release
    replaces it, removing old files.

    One-off setup (secrets, the load balancer, Stripe, scheduler jobs, SES)
    is still the runbook's.

.EXAMPLE
    .\deploy\gcp\release.ps1
    Builds and releases the API, then the site.

.EXAMPLE
    .\deploy\gcp\release.ps1 -Rebuild
    Rebuilds the database (wiping it) first: for schema changes.

.EXAMPLE
    .\deploy\gcp\release.ps1 -Rebuild -WipeBuckets
    A clean slate: database and stored files.

.EXAMPLE
    .\deploy\gcp\release.ps1 -Only Site
    Releases just the site.
#>
[CmdletBinding()]
param(
    [ValidateSet("Both", "Api", "Site")]
    [string]$Only = "Both",

    # Rebuild dev's database first (wipes it; schema changes).
    [switch]$Rebuild,

    # With -Rebuild: also delete every stored file (documents bucket, old
    # build uploads).
    [switch]$WipeBuckets,

    # Tenant 1's Stripe account to link after a rebuild. Normally left out:
    # the one connected now is kept. "none" links nothing.
    [string]$StripeDevAccountId = ""
)

# Dev only, on purpose: this script wipes things.
$Environment = "dev"

# Native commands (gcloud, git, python) don't stop a script on failure in
# Windows PowerShell, and with "Stop" their stderr would: every native call
# goes through Invoke-Native, which checks the exit code instead.
$ErrorActionPreference = "Continue"

$Root = (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
Set-Location $Root

# The secrets Cloud Run maps into the API (step 8), each from Secret
# Manager's latest version under the same name.
$ApiSecrets = @(
    "DATABASE_URL",
    "JWT_SECRET_KEY",
    "STRIPE_SECRET_KEY",
    "STRIPE_WEBHOOK_SECRET",
    "STRIPE_CONNECT_WEBHOOK_SECRET",
    "DOMAINS_CHECK_SECRET",
    "PAYMENT_CHECK_SECRET",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY"
)

function Invoke-Native([string]$What, [scriptblock]$Command) {
    & $Command

    if ($LASTEXITCODE -ne 0) {
        throw "$What failed (exit code $LASTEXITCODE). Nothing after it was run."
    }
}

function Read-Secret([string]$Prompt) {
    $secure = Read-Host $Prompt -AsSecureString
    [Runtime.InteropServices.Marshal]::PtrToStringBSTR([Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure))
}

function Write-Step([string]$Text) {
    Write-Host ""
    Write-Host "== $Text" -ForegroundColor Cyan
}

try {
    # --- Configuration --------------------------------------------------

    $envFile = Join-Path $Root "deploy\gcp\env\$Environment.env"

    if (-not (Test-Path $envFile)) {
        throw "No $envFile. Environments are deploy/gcp/env/<name>.env."
    }

    $cfg = @{}
    foreach ($line in Get-Content $envFile) {
        if ($line -match '^([A-Z_]+)=(.*)$') { $cfg[$Matches[1]] = $Matches[2].Trim() }
    }

    foreach ($name in "ENV_NAME", "PROJECT_ID", "REGION", "BASE_DOMAIN", "REPOSITORY", "API_SERVICE", "API_ACCOUNT", "BUILD_ACCOUNT", "SITE_BUCKET", "BUILD_BUCKET") {
        if (-not $cfg[$name]) { throw "$name is missing from $envFile." }
    }

    $project = $cfg.PROJECT_ID
    $region = $cfg.REGION
    $apiSa = "$($cfg.API_ACCOUNT)@$project.iam.gserviceaccount.com"
    $buildSa = "$($cfg.BUILD_ACCOUNT)@$project.iam.gserviceaccount.com"
    $apiEnvFile = "deploy/gcp/env/api.$($cfg.ENV_NAME).yaml"

    $doApi = $Only -in "Both", "Api"
    $doSite = $Only -in "Both", "Site"

    if ($WipeBuckets -and -not $Rebuild) {
        throw "-WipeBuckets only goes with -Rebuild: on its own the database would point at files that are gone."
    }

    # The buckets -WipeBuckets empties: stored files, and old build uploads.
    $wipeTargets = @()
    if ($WipeBuckets) {
        if (-not $cfg.DOCUMENT_BUCKET) { throw "DOCUMENT_BUCKET is missing from $envFile." }
        $wipeTargets = @($cfg.DOCUMENT_BUCKET, $cfg.BUILD_BUCKET)
    }

    if ($doApi -and -not (Test-Path (Join-Path $Root $apiEnvFile))) {
        throw "No $apiEnvFile (the API's settings)."
    }

    # Only committed code is released: the build uploads the working tree,
    # so any change (staged, unstaged or a new file) would go out under a
    # commit that doesn't contain it. The image tag is that commit.
    $changes = @(git status --porcelain)
    if ($changes.Count -gt 0) {
        $shown = ($changes | Select-Object -First 15) -join "`n  "
        $more = if ($changes.Count -gt 15) { "`n  ... and $($changes.Count - 15) more" } else { "" }
        throw "Not releasing: there are uncommitted changes. Commit (or stash) them first, then run this again.`n  $shown$more"
    }

    $tag = (git rev-parse --short HEAD).Trim()

    $account = (gcloud config get-value account 2>$null | Out-String).Trim()

    if (-not $account) { throw "gcloud isn't logged in: run 'gcloud auth login'." }

    # --- Checks before anything changes -------------------------------

    Write-Step "Checking $project"

    Invoke-Native "Reaching project $project" { gcloud projects describe $project --format="value(projectId)" | Out-Null }

    $problems = @()

    if ($doApi) {
        foreach ($secret in $ApiSecrets) {
            $policy = gcloud secrets get-iam-policy $secret --project=$project --format=json 2>$null | Out-String

            if ($LASTEXITCODE -ne 0) {
                $problems += "Secret $secret doesn't exist (create it: deploy/gcp/README.md, step 6)."
                continue
            }

            $readers = @()
            $bindings = ($policy | ConvertFrom-Json).bindings
            foreach ($binding in $bindings) {
                if ($binding.role -eq "roles/secretmanager.secretAccessor") { $readers += $binding.members }
            }

            if ("serviceAccount:$apiSa" -notin $readers) {
                $problems += "The API ($apiSa) can't read ${secret}: gcloud secrets add-iam-policy-binding $secret --member=serviceAccount:$apiSa --role=roles/secretmanager.secretAccessor --project=$project"
            }
        }
    }

    if ($problems.Count -gt 0) {
        Write-Host ""
        Write-Host "Not releasing:" -ForegroundColor Red
        $problems | ForEach-Object { Write-Host "  - $_" -ForegroundColor Red }
        exit 1
    }

    # --- What's about to happen ---------------------------------------

    $steps = @()
    if ($Rebuild) { $steps += "rebuild the database (WIPES it, keeps tenant 1's Stripe account)" }
    if ($WipeBuckets) { $steps += "empty the buckets ($($wipeTargets -join ', '))" }
    if ($doApi) { $steps += "build and release the API" }
    if ($doSite) { $steps += "build and release the site" }

    Write-Host ""
    Write-Host "Release" -ForegroundColor Yellow
    Write-Host ("  Environment   {0}  ({1})" -f $cfg.ENV_NAME, $envFile)
    Write-Host ("  Site          https://{0}" -f $cfg.BASE_DOMAIN)
    Write-Host ("  Project       {0}  ({1})" -f $project, $region)
    Write-Host ("  gcloud as     {0}" -f $account)
    Write-Host ("  Commit        {0}  {1}" -f $tag, (git log -1 --format=%s).Trim())
    if ($doApi) {
        Write-Host ("  API           {0}, settings {1}, {2} secrets checked" -f $cfg.API_SERVICE, $apiEnvFile, $ApiSecrets.Count)
    }
    if ($doSite) {
        Write-Host ("  Site bucket   gs://{0}" -f $cfg.SITE_BUCKET)
    }
    Write-Host ("  Steps         {0}" -f ($steps -join ", then "))
    Write-Host ""

    if ((Read-Host "Type '$($cfg.ENV_NAME)' to release, anything else to stop") -ne $cfg.ENV_NAME) {
        Write-Host "Stopped. Nothing was changed."
        exit 0
    }

    # --- 1. Database (optional) ---------------------------------------

    if ($Rebuild) {
        Write-Step "Rebuilding the $($cfg.ENV_NAME) database"

        Write-Host "This wipes $($cfg.ENV_NAME)'s database: every account, booking and payment there is lost." -ForegroundColor Red
        if ($WipeBuckets) {
            Write-Host "It also deletes every file in: $($wipeTargets -join ', ') (recoverable for 7 days by the buckets' soft delete)." -ForegroundColor Red
        }
        if ((Read-Host "Type 'wipe' to go ahead") -ne "wipe") {
            Write-Host "Stopped before the database. Nothing was changed."
            exit 0
        }

        # The app's connection is the API's own secret; app_user's password
        # (which the migrator sets) is in it. Only the owner's connection,
        # which never leaves this machine, is typed.
        $databaseUrl = (gcloud secrets versions access latest --secret=DATABASE_URL --project=$project | Out-String).Trim()
        if ($LASTEXITCODE -ne 0 -or -not $databaseUrl) { throw "Couldn't read DATABASE_URL from Secret Manager." }

        $appPassword = [Uri]::UnescapeDataString(([Uri]$databaseUrl).UserInfo.Split(":", 2)[1])

        $python = Join-Path $Root "backend\venv\Scripts\python.exe"

        $env:DATABASE_ADMIN_URL = Read-Secret "DATABASE_ADMIN_URL (the database owner's connection, step 7)"

        # The owner's connection must be for the database the API uses: a
        # pasted local or other branch's string would rebuild that one
        # instead, leaving dev on the old schema. Host and database name
        # only (no passwords) are compared and shown.
        try {
            $adminUri = [Uri]$env:DATABASE_ADMIN_URL
            $appUri = [Uri]$databaseUrl
        } catch {
            Remove-Item Env:DATABASE_ADMIN_URL -ErrorAction SilentlyContinue
            throw "That isn't a connection string (postgresql://user:password@host/database?sslmode=require)."
        }

        $adminTarget = "$($adminUri.Host)$($adminUri.AbsolutePath)"
        $appTarget = "$($appUri.Host)$($appUri.AbsolutePath)"

        if ($adminTarget -ne $appTarget) {
            Remove-Item Env:DATABASE_ADMIN_URL -ErrorAction SilentlyContinue
            throw "Not rebuilding: that owner connection is for $adminTarget, but dev's API uses $appTarget (Secret Manager's DATABASE_URL). Use the owner connection for $appTarget. Nothing was changed."
        }

        Write-Host "Rebuilding $appTarget"

        try {
            # Tenant 1's Stripe account, read before the wipe and linked
            # again by the dev seed, so it never needs reattaching. A given
            # -StripeDevAccountId wins.
            $stripeAccount = $StripeDevAccountId
            if (-not $stripeAccount) {
                $stripeAccount = (& $python (Join-Path $Root "deploy\gcp\read_stripe_account.py") | Out-String).Trim()
            }
            if ($stripeAccount -like "acct_*") {
                Write-Host "Keeping tenant 1's Stripe account: $stripeAccount"
            } else {
                Write-Host "Tenant 1 has no Stripe account to keep: connect one in Admin > Payments after the release." -ForegroundColor Yellow
                $stripeAccount = "none"
            }

            $env:DATABASE_URL = $databaseUrl
            $env:APP_DB_PASSWORD = $appPassword
            $env:APP_ENV = $cfg.ENV_NAME
            $env:STRIPE_DEV_ACCOUNT_ID = $stripeAccount

            Push-Location (Join-Path $Root "backend")
            try {
                Invoke-Native "Rebuilding the database" { & $python -m migrations.migrator rebuild }
            } finally {
                Pop-Location
            }
        } finally {
            Remove-Item Env:DATABASE_ADMIN_URL, Env:DATABASE_URL, Env:APP_DB_PASSWORD, Env:APP_ENV, Env:STRIPE_DEV_ACCOUNT_ID -ErrorAction SilentlyContinue
        }
    }

    # --- 1b. Buckets (optional, with a rebuild) -----------------------

    foreach ($bucket in $wipeTargets) {
        Write-Step "Emptying gs://$bucket"

        # Nothing there: nothing to delete (rm fails on no matches).
        $objects = gcloud storage ls "gs://$bucket/**" --project=$project 2>$null
        if (-not $objects) {
            Write-Host "Already empty."
            continue
        }

        Invoke-Native "Emptying gs://$bucket" { gcloud storage rm "gs://$bucket/**" --project=$project --quiet }
    }

    # --- 2. API -------------------------------------------------------

    if ($doApi) {
        Write-Step "Building the API image ($tag)"

        Invoke-Native "Building the API" {
            gcloud builds submit . --config=deploy/gcp/cloudbuild.backend.yaml `
                --ignore-file=deploy/gcp/build.gcloudignore `
                --gcs-source-staging-dir="gs://$($cfg.BUILD_BUCKET)/source" `
                --service-account="projects/$project/serviceAccounts/$buildSa" `
                --region=$region --project=$project `
                --substitutions="_REGION=$region,_REPOSITORY=$($cfg.REPOSITORY),_TAG=$tag"
        }

        Write-Step "Releasing the API"

        $secretMap = ($ApiSecrets | ForEach-Object { "$($_)=$($_):latest" }) -join ","

        Invoke-Native "Releasing the API" {
            gcloud run deploy $cfg.API_SERVICE `
                --image="$region-docker.pkg.dev/$project/$($cfg.REPOSITORY)/api:$tag" `
                --service-account=$apiSa `
                --ingress=internal-and-cloud-load-balancing --allow-unauthenticated `
                --env-vars-file=$apiEnvFile `
                --set-secrets=$secretMap `
                --cpu=1 --memory=512Mi --min-instances=0 --max-instances=2 `
                --region=$region --project=$project --quiet
        }
    }

    # --- 3. Site ------------------------------------------------------

    if ($doSite) {
        Write-Step "Building and releasing the site"

        # The Maps key is read from Google each time, never kept in the repo
        # (step 13); without one, pages show map links instead.
        $mapsKeyName = (gcloud services api-keys list --project=$project --filter="displayName='Maps embed (public site)'" --format="value(name)" 2>$null | Out-String).Trim()
        $mapsKey = ""
        if ($mapsKeyName) {
            $mapsKey = (gcloud services api-keys get-key-string $mapsKeyName --format="value(keyString)" | Out-String).Trim()
        }

        Invoke-Native "Building the site" {
            gcloud builds submit . --config=deploy/gcp/cloudbuild.frontend.yaml `
                --ignore-file=deploy/gcp/build.gcloudignore `
                --gcs-source-staging-dir="gs://$($cfg.BUILD_BUCKET)/source" `
                --service-account="projects/$project/serviceAccounts/$buildSa" `
                --region=$region --project=$project `
                --substitutions="_PLATFORM_HOST=$($cfg.BASE_DOMAIN),_SITE_BUCKET=$($cfg.SITE_BUCKET),_MAPS_EMBED_KEY=$mapsKey"
        }
    }

    Write-Host ""
    Write-Host ("Released {0} to https://{1}" -f $tag, $cfg.BASE_DOMAIN) -ForegroundColor Green
}
catch {
    Write-Host ""
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
