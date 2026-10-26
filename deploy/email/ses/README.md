# Amazon SES setup

How the platform's email sending is set up in AWS. The rules behind it are in `docs/email-policy.md`, section 5; the app side is `backend/app/integrations/email/`.

Everything is in **Sydney (`ap-southeast-2`)**, in one AWS account.

| Resource | Name | Purpose |
|---|---|---|
| Sending identity | `jnb-digital.com.au` (already verified) | Emails come from `no-reply@jnb-digital.com.au`, under each centre's name |
| Configuration set | `oshc-standard` | Most emails: TLS whenever the receiving server supports it |
| Configuration set | `oshc-tls` | Password reset and kiosk PIN emails: **TLS required**, never sent unencrypted |
| SNS topic | `oshc-ses-events` | Bounce, complaint, delivery, reject and rendering-failure events from both sets, posted to `/api/v1/webhooks/ses` |
| IAM user | `oshc-app-sender` | The app's credentials: may only send, only as `no-reply@jnb-digital.com.au`, only through the two sets |

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

### 1. Check the sending domain is verified in Sydney

```powershell
aws sesv2 get-email-identity --email-identity jnb-digital.com.au --region $REGION --query "{verified: VerifiedForSendingStatus, dkim: DkimAttributes.Status}"
```

Expect `verified: true` and `dkim: SUCCESS`. Identities are per region: if it's verified elsewhere, verify it in Sydney first.

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

`SES_FROM_ADDRESS` (`no-reply@jnb-digital.com.au`) and `SES_REGION` (`ap-southeast-2`) have defaults.

## Not set up yet

- **SES tenants** (one per platform tenant, for separate reputation and suppression). Each needs creating and associating with the identity and both configuration sets, and the IAM policy needs the tenant resources. Until then `SES_USE_TENANTS=false`.
- **Custom MAIL FROM subdomain** (e.g. `mail.jnb-digital.com.au`) for SPF alignment of bounces. Set on the identity, so check nothing else relies on the current setting.
- **A dedicated platform domain** to replace `jnb-digital.com.au`.
