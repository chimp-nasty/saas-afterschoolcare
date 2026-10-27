# Backend development instructions for an agent

This is a reusable backend development contract. Establish the new project's domain before designing its data model. Preserve the architecture and operational rules below; do not carry over the source project's business entities, tenancy assumptions, integrations or deployment configuration. Read the companion [human overview](backend-patterns-overview.md).

## Non-negotiable operating rules

1. Never execute database-affecting commands, against any database. This includes migration commands, resets, seeds, SQL clients, connection scripts, database introspection/model generation, app startup that connects to a database, and database-backed tests. Write SQL, application code and tests; give the human exact commands, working directories and effects, and wait for reported results when verification depends on them. Do not treat permission to implement a feature as permission to operate a database.
2. Do not run tests yourself, including unit tests. Supply tests with each vertical slice and give the human focused and full-suite commands where relevant. Label verification as pending until results are supplied.
3. Use Neon PostgreSQL unless the user explicitly specifies otherwise. Keep production, development and disposable test targets separate.
4. The remaining deployment stack is AWS. Offer AWS services first when a feature needs another service, for example S3 for objects or SES for email. Do not add provider libraries before the feature needs them. Integration implementation and infrastructure design are outside this guide.
5. During development, edit the initial schema SQL and seed files in place. Do not add incremental change migrations for evolving existing objects. Ask the human to rebuild the disposable development database when applied SQL changes. This is intentional, despite the migrator's generic advice to add files. Revisit the migration policy with the user before maintaining a persistent production database; never propose a production rebuild.
6. Do not read or expose environment files or credentials. Ask for non-secret configuration facts and provide placeholder examples. The human configures secrets locally.

## First conversation and portable files

Ask the user to provide this guide and the accompanying `portable/` directory. If files are missing, request the required files before claiming to preserve their implementation. The Python files are source templates, not a runnable application or an installed package. Copy their contents into the corresponding paths under `backend/`; create package `__init__.py` files as needed. Never execute the templates in this documentation directory.

Confirm the domain, users, ownership model, role/action matrix, scope boundaries, public endpoints, login lifetime and Neon branch setup before implementation. Every project gets RBAC and RLS, but not every project has tenants. A scope may be a user, workspace, organisation or tenant; introduce extra scope levels only when the domain needs them. Confirm requirements rather than manufacturing business entities.

### Files to preserve

| Portable path under `portable/` | Treatment |
| --- | --- |
| `app/api/response.py` | Preserve `ApiResponse[T]`, its `ok`, `msg`, `data` fields and nullable data. |
| `app/api/router.py` | Preserve the central aggregator; add domain router imports and registrations. Mount once at `/api`. |
| `app/db/repository.py` | Preserve base repository and bounded pagination. |
| `app/db/transaction.py` | Preserve service transaction decorator and integrity-error mapping. |
| `app/dependencies/db.py` | Preserve request session lifecycle; supply `app.db.session.SessionLocal`. |
| `app/dependencies/service.py` | Preserve repository injection by concrete constructor annotations. |
| `app/errors/base.py` | Preserve application-error contract and event naming. |
| `app/errors/database.py` | Preserve mapper logic; populate the project-specific constraint catalogue. |
| `app/errors/auth.py` | Contains the rate limiter's portable error dependency; extend with the project's auth errors. |
| `app/middleware/error_handler.py` | Preserve error envelopes and registration; configure logging and middleware in the application. |
| `app/middleware/rate_limit.py` | Port the complete module unchanged as the development placeholder. Configure limits at composition time. |
| `migrations/migrator.py` | Preserve the migration engine. Adapt only the explicit project hooks below. |

Unchanged generic files were copied from the reference backend. Router registrations, constraint mappings and auth errors were reduced to generic scaffolds. The migrator defaults to `auth` and `public`; domain-specific schemas and comments were removed. No implementation in the source backend was changed.

## Core libraries

Use FastAPI and Uvicorn for HTTP/ASGI, Pydantic v2 for boundary models, pydantic-settings for typed configuration, SQLAlchemy 2 for synchronous sessions and queries, and psycopg2 for PostgreSQL. Use PyJWT for signed tokens and pwdlib with argon2-cffi for password hashing. Use python-dotenv for local configuration loading, sqlacodegen for generated database models, and pytest for tests. `pydantic[email]` supplies email validation; python-multipart is needed when forms or uploads are introduced. Use standard-library logging, datetime, UUID, secrets and hashing tools where appropriate.

The inspected baseline uses FastAPI 0.135.1, SQLAlchemy 2.0.48, psycopg2-binary 2.9.11, Pydantic 2.12.5, pydantic-settings 2.13.1, PyJWT 2.12.1, pwdlib 0.3.0, argon2-cffi 25.1.0, python-dotenv 1.2.2, sqlacodegen 4.0.4 and pytest 9.1.1. These are provenance, not a requirement to install those versions forever. Resolve compatible versions for a new project, pin them in requirements, and have the human install them. Separate development dependencies in `requirements-dev.txt`. Do not copy payment, cloud, imaging, template or domain-management libraries from the source project by default.

## Required structure

```text
backend/
  app/
    main.py
    api/{response.py,router.py}
    core/{config.py,security.py,logging.py}
    db/{session.py,repository.py,transaction.py,models.py}
    dependencies/{db.py,service.py,auth.py,rls.py}
    middleware/{error_handler.py,request_handler.py,rate_limit.py,same_origin.py}
    errors/{base.py,database.py,auth.py,<domain>.py}
    auth/
      jwt/{tokens.py,context.py}
      routes/
      schemas/
      services/
      repositories/
    <domain>/
      routes/
      schemas/
      services/
      repositories/
  migrations/
    migrator.py
    schema/000X_*.sql
    seed/000X_*.sql
    dev_seed/000X_*.py
  tests/{conftest.py,factories.py,test_<slice>.py}
  requirements.txt
  requirements-dev.txt
  pyproject.toml
```

Choose domain names after discovery. Keep the layers within each domain rather than collecting every service or route into one global directory. Split large workflows by use case when useful; do not create empty abstraction layers.

Where helpful, align logical domain folders with PostgreSQL schemas and frontend adapter groups: for example, `app/auth/` and database schema `auth`. This is a recommended organisational pattern, not a requirement to create a database schema per feature or to expose database tables directly through the API.

## Layer boundaries and API contract

| Layer | Owns | Boundary |
| --- | --- | --- |
| Routes | HTTP inputs, dependency declarations, permissions, status codes, response envelopes | Call services, never repositories; no persistence or transaction ownership. |
| Schemas | Request, filter and response shape; typed values; length/format validation and normalisation | Pydantic models are separate from generated ORM models. They do not query or commit. |
| Services | Use-case orchestration, transactions, business-event logging, response construction | Call repositories. Do not duplicate database invariants as preflight checks. |
| Repositories | Queries, explicit joins, persistence, flushes, locks and database function calls | Use the injected session; never commit; do not return HTTP envelopes. |
| PostgreSQL | Durable invariants, relationship integrity, concurrency enforcement and RLS scope | SQL is authoritative for rules that must hold for every writer. |

Use synchronous handlers/services with the synchronous database driver. Construct one repository per dependency using `get_service(Service, db_dependency=get_rls_db)`. Constructor repository annotations must be actual `Repository` subclasses: the preserved injector does not resolve string annotations or arbitrary dependencies. Avoid postponed/string annotations in these constructors; inject non-repository dependencies explicitly through a suitable factory.

Use one router per resource, with `prefix="/<resource>/v1"`. The aggregator in `app/api/router.py` includes resource routers, and `main.py` mounts the aggregator with `prefix="/api"`. Preserve `/api/<resource>/v1/...`, including version position. Return `ApiResponse[ResponseSchema]`, `ApiResponse[list[ResponseSchema]]` or `ApiResponse[None]`; return `ok=True` and a concise message on success. Use actual HTTP error status codes alongside `ok=False`, rather than HTTP 200 for failures. Exceptions requiring raw responses must be explicit design decisions.

The route declares `Depends(require_permission(resource="...", action="c|r|u|d"))` and an RLS-backed service dependency. It derives acting identity and active scope from verified context, passes typed input to the service, and wraps the result. Never accept a body-supplied acting user or scope as authoritative.

For PATCH, distinguish omitted fields from explicit nulls with `model_dump(exclude_unset=True)` and allow only declared writable fields. Services build response DTOs with `model_validate(..., from_attributes=True)` while the transaction's RLS context still exists. Avoid returning ORM objects that need lazy loads after commit.

## Authentication, RBAC and RLS to implement

Create the auth modules, SQL objects and dependencies; the portable package deliberately does not pretend that scope-specific auth can be copied unchanged.

Use password login, pwdlib's recommended Argon2 hashing, and one signed access JWT stored in an HttpOnly cookie. Default to HS256 and a configurable fixed 90-minute lifetime, matching the reference design. There is no refresh token or background sliding renewal. Explicit login or an authorised scope switch may issue a new token. Use Secure cookies over HTTPS, SameSite=Lax, path `/`, and no broad cookie Domain by default. Local HTTP exceptions must be explicit development settings. Keep cookie set/delete settings consistent.

Issue and validate signature, an allowlisted algorithm, issuer, intended audience, expiry, issued-at and not-before claims; validate identity/scope types when constructing an immutable token context. Use a small configured clock-skew allowance (reference default: 30 seconds). Do not copy optional/missing-claim behaviour without considering the intended contract. Include user ID, roles, effective resource/action permissions and only the scope claims the new domain needs. Do not put secrets or sensitive domain records in tokens.

JWT permissions are a snapshot. A role change does not rewrite existing tokens; logout deletes the browser cookie and does not itself revoke a copied token. Password changes do not automatically revoke previously issued JWTs without an added revocation mechanism. Explain this tradeoff and the fixed lifetime to the user; do not silently add refresh tokens, token blacklists or a session service. Live database grants/RLS may restrict rows sooner, but do not promise immediate universal token revocation.

Create role, permission and role-permission SQL tables and real SQL catalogue seeds. Actions are `c`, `r`, `u`, `d`. Every protected domain route declares its resource/action dependency. Public login/reset endpoints and authenticated session-management endpoints need their own explicit access contract; do not require a pre-existing CRUD permission to log in. If the domain has different permission scopes, keep their maps and dependencies distinct. One scope's grant must not satisfy another's check. If requests are host-bound, validate the verified token against the resolved host scope.

Create `get_rls_db` to set verified identity and active scope with parameterised `set_config(..., true)` on the same request session used by repositories. `true` means transaction-local. After any commit/rollback, reapply all required context before later scoped work. A pooled connection must never leak a previous request's context. Missing context must deny protected operations; exceptions for trusted server workflows must be narrow, documented and tested.

Create RLS policies for reads and writes, including `USING` and `WITH CHECK` where appropriate. Enforce ownership and cross-owner references in the database, including fields writable only by privileged roles. Router RBAC determines whether an operation is permitted; RLS determines which rows are accessible. UI visibility and repository filter conventions do not replace either layer.

Create a restricted runtime login role such as `app_user`, with no superuser/BYPASSRLS privileges, minimal grants and no protected table ownership. Use admin credentials only in the human-run migrator. Supply a startup guard that rejects a runtime role with `rolsuper` or `rolbypassrls`; also inspect table ownership and RLS/force-RLS configuration because the role check alone is insufficient. For privileged SQL functions, pin a safe search path, schema-qualify objects and restrict EXECUTE grants. Do not assume console-created roles enforce RLS.

Preserve same-site browser API hosting under `/api` and protection for cookie-authenticated writes. Implement and test origin checking with a configured trusted origin/proxy contract. The reference middleware compares Origin and Host authorities; do not describe that as full scheme-aware origin validation. Any server endpoint exemption needs its own authentication. CORS alone is not CSRF protection.

## Invariants, transactions and errors

Write durable rules once using PostgreSQL constraints, unique/exclusion indexes, foreign keys, SQL functions and triggers. Services coordinate workflows and may check prerequisites or report not-found results; they must not reproduce database invariants in Python. For a rule needed by both a read and a trigger, define a single SQL function and call it from both. Use database time for comparable persisted event timestamps, timezone-aware timestamps for instants, and date-only values for calendar dates. Define business timezone behaviour after domain discovery.

Concurrency matters: a SELECT-then-INSERT service check cannot guarantee uniqueness or capacity. Use database constraints and suitable row locks for aggregate rules; document lock ordering. Account for rollback and idempotency in workflows.

Decorate service write entry points with `@transactional`. It commits once on success, rolls back on failure and maps `IntegrityError`. Repositories may flush to obtain IDs or surface constraints but never commit. Avoid nesting decorated service calls that would commit part of an outer workflow. If a workflow needs multiple transactions, make the boundaries explicit and re-establish RLS context in each later transaction.

Define domain exceptions as `ApplicationError` subclasses with HTTP status, safe client message and result. Put internal detail in `log_reason`. Give client-facing constraints stable names and register them in `CONSTRAINT_ERRORS`. Triggers raise an integrity-class SQLSTATE (for example `23514`) and explicit `CONSTRAINT = 'ck_<table>_<rule>'` so psycopg2 diagnostics reach the mapper. The mapper uses constraint names, never brittle message matching. Unknown `ck_` constraints become generic invalid-value errors; other unmapped integrity failures remain server errors.

Register `ApplicationError`, HTTP and request-validation handlers. Install the unhandled-exception middleware so unexpected failures return the same envelope with a safe 500 message. Middleware that rejects a request must return `exception_response` directly, because exceptions there do not reach the route exception handlers. Log request correlation, verified identity/scope where appropriate, event, result and safe reason; services own business-event logging. Never log passwords, JWTs, credentials or sensitive request bodies. Sanitise validation/error log details as the domain requires.

## Rate-limiting module

Copy `portable/app/middleware/rate_limit.py` without rewriting it. Supply its error and response dependencies from this package and register `InMemoryRateLimitMiddleware` in application composition. It uses a per-process deque per IP/path, a default 120 requests per 60 seconds, optional regex full-match route overrides, exempt paths, OPTIONS bypass and an envelope-formatted 429.

It is a development placeholder: workers do not share counters, restarts clear state, raw paths produce separate buckets and retained keys can grow. It trusts the first X-Forwarded-For value, so it needs a trusted proxy that removes client-supplied forwarding headers. Do not claim it provides production abuse protection. Before production, agree an AWS edge/shared enforcement approach with the user; retain the API error contract. Route limits and exemptions belong to the new project's composition, not copied business paths.

## SQL migration and generated-model model

The portable migrator retains filename ordering, schema-before-seed-before-dev-seed execution, SHA-256 history, one transaction per file, `.sql` execution through a raw cursor and Python seed `up(conn: Connection) -> None`. `schema/` defines database objects; `seed/` contains real `.sql` files for required roles, permissions and application reference data. `dev_seed/` contains synthetic development fixtures, using Python when password hashing or generated data is needed. Do not mix demo accounts into production seed SQL.

Once the domain and schema are established, create useful dev seed data: accounts for relevant roles, synthetic owned records, realistic states and at least two independent scopes where applicable. Document local demo login details without using real credentials. Keep tests independent of specific demo records; factories create their own users and rows.

Development and test environments both receive `dev_seed` because the preserved migrator defines `DISPOSABLE_ENVS = ("dev", "test")`. A checksum mismatch after editing initial SQL requires a human-run rebuild, not changing history checksums. New initial files may establish new domains, but do not use the `new` command to append incremental patches for changes to existing development schema. Respect SQL object dependency order; SQL-language function bodies can require referenced objects at creation time.

Keep `migrator.py` relatively untouched. Its intentional adaptation points are:

- `MODEL_SCHEMAS`: defaults to `auth`, `public`; list the project's actual schemas.
- `reset()` schema drop list: match all project-owned schemas, including any later-added domain schema. Keep migration history reset and `public` recreation. Never include unrelated schemas.
- Settings contract: supply `app.core.config.settings.APP_ENV` and the database configuration below.
- Runtime-role SQL: consume transaction-local `app.runtime_password`, passed from `APP_DB_PASSWORD`, and create/grant the restricted runtime role. The migrator does not invent that SQL.
- Generated outputs: preserve `app/db/models.py` reflection via sqlacodegen, explicit repository joins and no generated ORM relationships. Do not hand-edit generated models.
- Frontend hook: retained for compatibility, not a frontend requirement. Dev `run/rebuild` attempts OpenAPI export and `frontend`'s `gen:api:file`; it reports a skip when unavailable. For a backend-only project no frontend needs to be created. If a frontend is later added, configure that script deliberately. Successful migration does not prove skipped code generation succeeded.

The script's `APP_ENV` reset guard does not verify which Neon branch a URL reaches. Human target verification is mandatory; a value of `dev` cannot make a production URL safe. Never execute any migrator subcommand as the agent, even a seemingly harmless one.

## Human Neon configuration handoff

### Generated SQLAlchemy models: explain this to the human

`sqlacodegen` inspects the actual PostgreSQL schema and writes Python SQLAlchemy classes to `app/db/models.py`. Those classes describe persisted columns so repositories can query them. SQL files are the source of truth; never hand-edit the generated models. Change initial SQL, have the human rebuild the development database, and regenerate from that database. Pydantic request/response models are separate, handwritten API contracts.

**Do not use SQLAlchemy ORM relationships anywhere in the project.** Generated models stay decoupled, with plain columns and foreign keys. Repositories express joins explicitly. Do not add `relationship()`, backrefs or relationship-driven lazy/eager loading. The portable migrator keeps sqlacodegen's `nojoined` option and removes generated relationship declarations; preserve that behaviour and inspect regenerated output.

For first setup, the human runs `./venv/Scripts/python -m pip install -r requirements-dev.txt` from `backend/` to install declared development dependencies including sqlacodegen (this downloads packages). After configuring the correct Neon development target, the human runs the documented `rebuild` command to recreate it and generate models. If only models need refreshing from an already-correct dev database, give `./venv/Scripts/python -m migrations.migrator models` from `backend/`: this connects with the configured admin URL, reflects schemas and overwrites `app/db/models.py`, without intentionally rebuilding tables. The agent never runs it. Check the output for skipped generation; review and commit the generated file. On POSIX use `./venv/bin/python`.

If a generated class is wrong, inspect SQL and generation configuration; do not patch `models.py`. API-type generation is a separate step based on Pydantic/OpenAPI, documented in the [frontend agent guide](frontend-agent-guide.md).

### Branch and connection setup

Provide these steps with each new project's concrete schema/runtime-role names. Do not provision branches yourself.

1. In Neon, keep the production branch separate. Create a development branch and a disposable test branch from development. A production-derived branch is an explicit user choice; prefer a schema-only/sanitised source when production holds sensitive data. Tests destroy data on their target; branching is not a reason to use production credentials.
2. Have the human identify the branch and endpoint for each target. Obtain TLS connection details through Neon. Use an owner/admin URL for migrations and a restricted runtime-role URL for the application on that same branch/database. A direct admin endpoint is a suitable default for schema operations; validate pooling compatibility for runtime use.
3. The human configures local development environment values: `APP_ENV=dev`, `DATABASE_ADMIN_URL=<dev admin URL>`, `DATABASE_URL=<dev runtime URL>`, `APP_DB_PASSWORD=<runtime role password>`, JWT secret/issuer/audience/lifetime and cookie settings. Provide a secret-free configuration template in the new project when implementing it. `APP_DB_PASSWORD` must match the runtime URL password, correctly URL-encoded in that URL.
4. Separately configure test values targeting only the disposable branch, with `APP_ENV=test`. The test harness loads this configuration before importing app settings, and must not fall back to dev/prod database URLs. Both test URLs must reach the same test database; neither may reach development or production.
5. Implement pre-rebuild fixture checks for missing configuration, recognised disposable branch/endpoint identity and dev/prod target mismatch. Compare normalised endpoint/database identities, not just raw URL strings: different users or pooled/direct URLs can reach the same target. Prefer an explicit allowlisted test target verified by the human. The reference fixture only checks missing values and exact URL equality; strengthen that when creating the new harness.
6. The human creates the runtime role/grants through the initial admin migration. A first rebuild must complete before runtime login is usable. Shared role/password behaviour across branches must be checked in the user's Neon setup; do not assume isolation from a URL label.
7. Give the human rebuild/test commands below, state destructive effects, and ask them to report the output. Tests exercise the app using runtime credentials, not the owner connection. Reserve admin test connections for fixture setup or explicit enforcement tests.

## Vertical slices and user-run verification

Build incrementally in vertical slices. Before implementation, propose a staged plan in dependency order. Each stage should deliver a small, coherent capability that the human can exercise and confirm. Break each slice into sensible steps: agree behaviour and access rules; define SQL, invariants and seeds; implement repositories and services; expose schemas and routes; add tests and user verification instructions. These are steps within a slice, not permission to build every database table or every route across the entire project before delivering working behaviour.

Start with the minimum foundation needed to verify a first end-to-end capability, including database configuration, authentication and access enforcement where required. Then add domain capabilities in dependency order. State each slice's purpose, prerequisites, scope, expected observable behaviour and acceptance criteria before building it. Keep slices small enough that failures can be traced and corrected before dependent work begins.

After completing a slice, stop at its verification checkpoint. Give the human the exact rebuild and test commands, working directories, effects and any manual checks needed. Wait for the human to report results and explicitly confirm the slice before implementing the next slice. Elapsed time or silence is not confirmation. If verification fails, repair the current slice and hand it back for verification; do not build dependent slices on an unconfirmed result. Update the staged plan as requirements or evidence change.

For each slice deliver SQL/rules/RLS, permission seeds and grants, repository methods, service workflow, schemas, routes/registration, named errors, relevant dev fixtures and behavioural tests together. Do not defer access tests until the end.

Integration tests use the real app and real disposable PostgreSQL branch so policies and triggers are exercised. Rebuild once per test session; use per-test factories and unique identities. Restore shared reference state if a test changes it. Add a plain-English comment above each test stating what it proves. Fake external services so tests cannot send email, incur cloud side effects or depend on providers.

Cover success, invalid input, unauthenticated/expired JWTs, missing permissions, cross-user/scope reads and writes, cross-owner references, direct database rejection of invariant violations, error-envelope mapping, rollback, transaction-local context restoration and concurrency where meaningful. Public endpoints need abuse/negative-path coverage. Test JWT fixed expiry and cookie behaviour. Use the application's runtime role when asserting RLS enforcement.

Every handoff says what changed, what SQL rebuild is needed, what tests were added, what was statically inspected and what remains unverified. Never claim a passing suite from inspecting test code.

Example commands for the human, working directory `backend/` (Windows virtual environment):

```powershell
# DESTRUCTIVE: drops configured project schemas on the DEV target,
# reapplies schema + production seeds + dev fixtures, then attempts
# ORM model and optional frontend API type regeneration.
./venv/Scripts/python -m migrations.migrator rebuild

# DESTRUCTIVE ON TEST TARGET: fixture rebuilds the disposable TEST branch.
# Replace test_<slice>.py with the actual module delivered.
./venv/Scripts/python -m pytest tests/test_<slice>.py -q

# Also rebuilds the disposable TEST target at session start.
./venv/Scripts/python -m pytest -q
```

For POSIX, use `./venv/bin/python` with the same module arguments. A normal rebuild uses development configuration; pytest must select test configuration before imports. Do not tell the human to rebuild development merely to execute tests: tests rebuild their own target. A schema/model change may require the separate dev rebuild to regenerate checked-in models first. Wait for those outputs before claiming runtime verification.

## Completion criteria

A slice is ready for user verification when boundaries are preserved, routes declare their access contract, RBAC seeds and RLS agree, database invariants have named error mappings, generated-model changes are handed off for human generation, meaningful tests and dev fixtures exist, and exact human commands/effects are documented. Runtime acceptance remains pending until the human supplies successful results.

## Evidence and limits

Derived by static inspection on 2026-10-27 of the reference backend's requirements, API composition, auth/JWT/configuration, dependencies, SQLAlchemy session/repository/transaction code, middleware/error handlers, representative domain layers, migration engine, foundation/runtime-role SQL and test bootstrap. Integration implementations were excluded. No environment files were read, no tests or database commands were executed, and deployed state was not verified. The portable sources are unexecuted templates; target-identity guards and domain-specific auth/RLS are implementation requirements, not shipped functionality in this package.
