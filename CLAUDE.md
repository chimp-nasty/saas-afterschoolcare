# After-school care SaaS

Multi-tenant booking app for out-of-school-hours care: families book and pay for sessions; centre staff and admins run the day. FastAPI + PostgreSQL (Neon) in `backend/`, SvelteKit in `frontend/`. Australian-only (addresses, states, spelling).

Frontend conventions (UI, components, mobile-first, confirmations, formats) live in `frontend/CLAUDE.md`. This file covers the whole project and the backend.

## Rules

### Never run anything that touches a database

Not the migrator (`python -m migrations.migrator ...`, any subcommand), not seed or reset scripts, not `psql` or ad-hoc connection scripts, and not the test suite (its fixtures rebuild the test database). This applies to every database, local, dev and test included.

Writing migrations, seeds and tests is fine. When one needs running, stop and give the exact command, the folder to run it from, and what it will do, then wait for it to be run and the result reported back. Common ones (from `backend/`):

- Rebuild the dev database (wipes dev data, regenerates `app/db/models.py` and `frontend/src/lib/api/schema.ts`): `./venv/Scripts/python -m migrations.migrator rebuild`
- Run the tests: `./venv/Scripts/python -m pytest -q` (one module: `./venv/Scripts/python -m pytest tests/test_<name>.py -q`)

Regenerating the frontend's API types without a database is allowed: export the app's OpenAPI document (`./venv/Scripts/python -c "import json; from app.main import app; open('../frontend/.openapi.json','w').write(json.dumps(app.openapi()))"`), then `npm run gen:api:file` in `frontend/`. Importing the app doesn't connect to the database.

### Schema changes edit the original SQL

While in early development, change tables by editing the original `CREATE TABLE` (and its functions, triggers and policies) in `backend/migrations/schema/000X_*.sql` and the seeds in place. Don't add new `ALTER TABLE` migration files, even though the migrator's docstring suggests it. Editing an applied file breaks the migrator's checksums, so any schema change needs a dev rebuild (give the command above). The existing 0008/0009 files predate this rule; edit them in place too.

Mind the file order: a SQL-language function body is checked when it's created, so it can only reference objects from earlier files (use plpgsql, checked at run time, when it must reference something defined later, e.g. `effective_booking_status` from 0009).

## Backend conventions

### Layers

- Routes call services, never repositories. One router per resource (`app/public/routes/*.py`), prefix `/<resource>/v1`, every handler returns `ApiResponse[...]`.
- Services own transactions (`@transactional` from `app/db/transaction.py`) and business logging. Services are built by `get_service(...)`, which injects any `Repository` subclass named in `__init__` by type.
- Repositories own queries and never commit. Models in `app/db/models.py` are generated from the database (don't edit); request/response models live in `schemas/`.
- Stripe is only called through `StripeClient` (`app/integrations/payments/stripe/client.py`), so tenant Stripe accounts (Connect, later) are one change. Our database is the only source of prices: checkout and refunds send amounts directly; there's no Stripe catalogue.

### Rules live in the database

- Invariants are constraints, unique indexes and triggers in the schema files, not service checks: e.g. capacity, booking rules (`enforce_booking_rules`), refund windows (`booking_is_refundable`, `enforce_refund_rules`), the pickup limit and phone rules, medical review resets.
- A violated constraint becomes an API error through `CONSTRAINT_ERRORS` in `app/errors/database.py`, keyed by constraint name. Triggers raise with an explicit `CONSTRAINT = '...'` name for this. Add an entry for every new rule that should reach the client as a specific message.
- When a rule is needed both in a trigger and in a read (e.g. "is this refundable?"), define it once as a SQL function and call it from both.

### Permissions and RLS

- Every authenticated endpoint uses `require_permission(resource=..., action=...)` (actions `c r u d`); permissions are seeded in `migrations/seed/0001_permissions.sql` and granted per role in `0003_role_permissions.sql`. When adding an endpoint, state which permission it uses and why.
- Row level security does the scoping: `get_rls_db` sets `app.user_id` and `app.location_id` for the request. Customers see their own rows at the session's location; staff and above see the location's (`auth.can_access_location_row`, `auth.is_location_staff`, `auth.is_location_admin`).
- The RLS settings last one transaction. A service that commits and then keeps working (e.g. refunds: save, call Stripe, save again) must set them again with `RlsContextRepository` in each later transaction.
- Staff-only fields on family-owned rows (medical review status, pickup ID checks and kiosk PINs) are enforced by triggers, not the API. Writes with no user session are trusted server code.
- Families own their children and pickup people; staff and admins don't create them. Logins are per location, and a session only counts at its own location.

### Tests

- Integration tests run the real app against a real (disposable) database; each test makes its own users through `tests/factories.py`, so tests don't depend on each other. Shared rows (services, configs) changed by a test are put back afterwards.
- Every test has a plain-English comment above it saying what it proves.
- Stripe is replaced by `FakeStripe` in every test (`tests/conftest.py`); a new service that uses `StripeClient` must be added to its patch list.

## Not built yet (MVP order)

Documents + staff medical review → email (a real provider behind the stubbed `EmailClient`; kiosk PINs are emailed) → kiosk (sign in/out, PIN login/change/forgot, staff ID check and approval) → rest of the staff dashboard (including service day management) → tenant configuration and Stripe Connect.
