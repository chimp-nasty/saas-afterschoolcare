# Terraform (planned, not started)

**Status: agreed 27 October 2026 to do before production; waiting until dev's custom domains are proven end to end (`jnb-digital.online` live).**

The dev environment was set up by hand from `deploy/gcp/README.md`. Production is the same with different names and credentials, so its one-off setup moves into Terraform: one set of code, `dev.tfvars` and `prod.tfvars`.

## What goes in

Terraform: project services, the DNS zones and records (root zone, environment zone, delegation, A records, the base certificate's CNAME), buckets (with lifecycle, CORS, public site access), service accounts and their roles, Artifact Registry, the network and proxy-only subnet, the static address, backend services and bucket, URL maps, proxies, forwarding rules, the base certificate and its DNS authorization, the Cloud Scheduler domain check, and the secrets themselves (empty) with their access.

Not Terraform:

| What | Why / how |
|---|---|
| Secret values | Terraform state holds what it manages in readable form; values stay `Put-Secret` (runbook step 6). |
| Releases (API image, site files) | Routine, not setup; stay Cloud Build + `gcloud run deploy` (later, a trigger on push). |
| The database | The migrator (runbook step 7). |
| Registrar nameservers, Stripe webhooks | One-off manual steps. |

## Traps

1. **The app edits the load balancer.** The domain check adds certificates to the HTTPS proxy and `site-*` redirect host rules and path matchers to the URL map (`app/integrations/domains/google.py`). Terraform must ignore those parts (`lifecycle { ignore_changes = [...] }`), or every apply removes businesses' custom domains. Businesses' own certificates and DNS authorizations (`t-*`, `auth-*`) are the app's, not Terraform's.
2. **Releases change the Cloud Run service's image.** Ignore the image (and revision-level settings set by `gcloud run deploy`), or an apply rolls the API back.

## Plan

1. Write the code here; state in a versioned bucket in Sydney.
2. Import dev (import blocks) until `terraform plan` shows no changes: the code then matches a working environment.
3. Apply to production; then secrets, migrator, releases and Stripe as in the runbook.
4. Shrink `deploy/gcp/README.md` to those steps plus "run Terraform".

Terraform or OpenTofu: either works; the user installs it (`winget install Hashicorp.Terraform`) and runs every command that changes infrastructure.
