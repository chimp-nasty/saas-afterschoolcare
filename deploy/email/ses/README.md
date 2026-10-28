# Amazon SES setup

How the platform's email sending is set up in AWS. The rules behind it are in `docs/email-policy.md`, section 5; the app side is `backend/app/integrations/email/`.

Everything is in **Sydney (`ap-southeast-2`)**, in one AWS account: the **jnb account** (`069102612762`). Check `aws sts get-caller-identity` before running anything here: another account (`669167971712`) also has SES identities, and isn't this one. Use `$AWS_REGION` for the AWS region when this runs in the same window as `deploy/gcp/README.md`, whose `$REGION` is Google Cloud's.

| Resource | Name | Purpose |
|---|---|---|
| Sending identity | `sessionpilot.com.au` (step 1) | Emails come from `no-reply@sessionpilot.com.au`, under each centre's name. Bounces return to `mail.sessionpilot.com.au` (custom MAIL FROM), so SPF lines up with the From domain |
| Configuration set | `oshc-standard` | Most emails: TLS whenever the receiving server supports it |
| Configuration set | `oshc-tls` | Password reset and kiosk PIN emails: **TLS required**, never sent unencrypted |
| SNS topic | `oshc-ses-events` | Bounce, complaint, delivery, reject and rendering-failure events from both sets, posted to `/api/v1/webhooks/ses` |
| IAM user | `oshc-app-sender` | The app's credentials: may only send, only as `no-reply@sessionpilot.com.au`, only through the two sets |

Neither configuration set has a tracking domain or open/click event destinations, so no tracking pixels or rewritten links.

The JSON files here contain `<ACCOUNT_ID>`. The commands below write filled-in copies to your temp folder; the repo keeps the placeholders.

## Steps (PowerShell, from the repo root)

```powershell
$REGION  = "ap-southeast-2"
$ACCOUNT = aws sts get-caller-identity --query Account --output text
$TOPIC   = "arn:aws:sns:${REGION}:${ACCOUNT}:oshc-ses-events"

# Filled-in copies of the JSON files.
foreach ($file in "event-destination", "sns-topic-policy", "iam-send-policy") {
    (Get-Content "deploy/email/ses/$file.json") -replace "<ACCOUNT_ID>", $ACCOUNT |
        Set-Content -Encoding ascii "$env:TEMP/$file.json"
}
```

### 1. The sending domain: `sessionpilot.com.au`

The platform's own domain, so no tenant's emails mention anyone else's (it replaced `jnb-digital.com.au`). Its DNS is the `sessionpilot` zone in Cloud DNS (`deploy/gcp/README.md`, step 2); load the environment's names first (the snippet at the top of that runbook) for `$DNS_PROJECT_ID`, `$ROOT_ZONE` and `$ROOT_DOMAIN`.

**1.1 Look at what's already there**, so nothing below clashes (an existing SPF, DMARC or `mail.` record would need merging, not a second one):

```powershell
gcloud dns record-sets list --zone="$ROOT_ZONE" --project="$DNS_PROJECT_ID" --filter="type=(TXT OR MX OR CNAME)"
```

**1.2 Create the identity** in Sydney, with Easy DKIM (2048-bit). It prints three DKIM tokens:

```powershell
$TOKENS = aws sesv2 create-email-identity --email-identity $ROOT_DOMAIN --dkim-signing-attributes NextSigningKeyLength=RSA_2048_BIT --region $REGION --query "DkimAttributes.Tokens" --output text
$TOKENS
```

**1.3 Publish the DKIM records** (one CNAME per token):

```powershell
foreach ($token in $TOKENS -split "\s+") {
    gcloud dns record-sets create "$token._domainkey.$ROOT_DOMAIN." --zone="$ROOT_ZONE" --type=CNAME --ttl=3600 `
      --rrdatas="$token.dkim.amazonses.com." --project="$DNS_PROJECT_ID"
}
```

**1.4 Custom MAIL FROM** (`mail.sessionpilot.com.au`): bounces come back to our subdomain instead of `amazonses.com`, so SPF aligns with the From domain for DMARC. Nothing else uses `mail.`, so it can't disturb other mail on the domain:

```powershell
aws sesv2 put-email-identity-mail-from-attributes --email-identity $ROOT_DOMAIN --mail-from-domain "mail.$ROOT_DOMAIN" --behavior-on-mx-failure USE_DEFAULT_VALUE --region $REGION

gcloud dns record-sets create "mail.$ROOT_DOMAIN." --zone="$ROOT_ZONE" --type=MX --ttl=3600 `
  --rrdatas="10 feedback-smtp.$REGION.amazonses.com." --project="$DNS_PROJECT_ID"
gcloud dns record-sets create "mail.$ROOT_DOMAIN." --zone="$ROOT_ZONE" --type=TXT --ttl=3600 `
  --rrdatas='"v=spf1 include:amazonses.com ~all"' --project="$DNS_PROJECT_ID"
```

**1.5 DMARC**, if 1.1 showed none. Gmail and Yahoo expect one from senders. Start at `p=none` (watch, don't block); tighten to `p=quarantine` once a few weeks of mail have gone out cleanly. There's no receiving mailbox, so no `rua` reports address for now:

```powershell
gcloud dns record-sets create "_dmarc.$ROOT_DOMAIN." --zone="$ROOT_ZONE" --type=TXT --ttl=3600 `
  --rrdatas='"v=DMARC1; p=none; adkim=s; aspf=s"' --project="$DNS_PROJECT_ID"
```

**1.6 Check** (DNS can take up to an hour; SES checks on its own):

```powershell
aws sesv2 get-email-identity --email-identity $ROOT_DOMAIN --region $REGION --query "{verified: VerifiedForSendingStatus, dkim: DkimAttributes.Status, mailFrom: MailFromAttributes.MailFromDomainStatus}"
```

Expect `verified: true`, `dkim: SUCCESS` and `mailFrom: SUCCESS`. Identities are per region: this must be Sydney.

**1.7 New accounts start in the SES sandbox** (only verified recipients). If this account is still there, request production access in the SES console (Account dashboard) before families can receive email.

### 2. Configuration sets

```powershell
aws sesv2 create-configuration-set --configuration-set-name oshc-standard --delivery-options TlsPolicy=OPTIONAL --region $REGION
aws sesv2 create-configuration-set --configuration-set-name oshc-tls --delivery-options TlsPolicy=REQUIRE --region $REGION
```

### 3. Events topic

```powershell
aws sns create-topic --name oshc-ses-events --region $REGION
aws sns set-topic-attributes --topic-arn $TOPIC --attribute-name Policy --attribute-value "file://$env:TEMP/sns-topic-policy.json" --region $REGION

foreach ($set in "oshc-standard", "oshc-tls") {
    aws sesv2 create-configuration-set-event-destination --configuration-set-name $set --event-destination-name oshc-ses-events --event-destination "file://$env:TEMP/event-destination.json" --region $REGION
}
```

Subscribing the webhook needs a public HTTPS address, so it's done when the API is deployed:

```powershell
aws sns subscribe --topic-arn $TOPIC --protocol https --notification-endpoint "https://<api host>/api/v1/webhooks/ses" --region $REGION
```

The API confirms the subscription itself once `SES_EVENTS_TOPIC_ARN` is set to `$TOPIC`. Until then, sent emails stay `sent` in the log rather than becoming `delivered` or `bounced`.

### 4. Account-level suppression list

Applies to every sending identity in this account in Sydney (including other services here): an address that hard-bounces or complains isn't sent to again.

```powershell
aws sesv2 put-account-suppression-attributes --suppressed-reasons BOUNCE COMPLAINT --region $REGION
```

### 5. The app's IAM user

```powershell
aws iam create-user --user-name oshc-app-sender
aws iam put-user-policy --user-name oshc-app-sender --policy-name ses-send --policy-document "file://$env:TEMP/iam-send-policy.json"
aws iam create-access-key --user-name oshc-app-sender
```

The access key goes in `backend/.env` for local testing, and in Google Secret Manager for Cloud Run (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`). It's shown once; don't commit it.

### 6. App settings

```
EMAIL_PROVIDER=ses
SES_CONFIGURATION_SET=oshc-standard
SES_TLS_CONFIGURATION_SET=oshc-tls
SES_USE_TENANTS=false
SES_EVENTS_TOPIC_ARN=arn:aws:sns:ap-southeast-2:<ACCOUNT_ID>:oshc-ses-events
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
```

`SES_FROM_ADDRESS` (`no-reply@sessionpilot.com.au`) and `SES_REGION` (`ap-southeast-2`) have defaults.

**Moving an existing setup from `jnb-digital.com.au`:** do step 1 first and wait for 1.6 to pass, then apply the new IAM policy (step 5's `put-user-policy`, which now names `sessionpilot.com.au`) and release the API with the new default (or set `SES_FROM_ADDRESS` to it), together: the old policy only allows the old address, and the new one only the new. Remove any `SES_FROM_ADDRESS=no-reply@jnb-digital.com.au` left in `backend/.env`. The old identity can then be deleted from SES.

## Not set up yet

- **SES tenants** (one per platform tenant, for separate reputation and suppression). Each needs creating and associating with the identity and both configuration sets, and the IAM policy needs the tenant resources. Until then `SES_USE_TENANTS=false`.
- **Tenants' own sending domains** (`no-reply@after3.com.au`), optional per tenant, with tenant configuration: their DKIM records, checked like custom web domains.
