# Deployment

Everything about running the app outside a developer's machine lives here, so none of it sits inside `backend/` or `frontend/` or ends up in an image.

| Folder | What it covers |
|---|---|
| `gcp/` | Google Cloud: the runbook for setting up an environment and releasing (`gcp/README.md`), each environment's settings (`gcp/env/`), the build files and the load balancer's routes. |
| `docker/` | The API image (`backend.Dockerfile`), built with `backend/` as its context. Its `.dockerignore` lets in only `app/` and `requirements.txt`. |
| `storage/gcs/` | The documents bucket's lifecycle and CORS rules. |
| `email/ses/` | Amazon SES (Sydney): sending, configuration sets and bounce events. |
| `stripe/` | Stripe Connect: platform settings, webhooks and OAuth. |

Secrets never go in this folder. They go in Google Secret Manager (`gcp/README.md`, step 6), and in `backend/.env` for local development.
