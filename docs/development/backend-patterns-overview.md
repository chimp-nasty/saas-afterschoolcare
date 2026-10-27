# Backend patterns: a human overview

This is the backend approach to carry into future projects. The business model changes between projects; the structure, security boundaries and development workflow stay consistent. The detailed [agent guide](backend-agent-guide.md) and accompanying [Python templates](portable/) make it actionable.

## The stack

Python with FastAPI serves the API through Uvicorn. Pydantic describes and validates requests and responses; pydantic-settings manages configuration. SQLAlchemy handles database sessions and queries, with psycopg2 connecting to PostgreSQL. Neon is the database provider unless we explicitly choose another one. Database models are generated from SQL using sqlacodegen; pytest tests the application against a disposable database.

Passwords use Argon2 through pwdlib. PyJWT signs and checks login tokens. Other AWS libraries are introduced only when a feature needs them: AWS is our first choice for services such as file storage and email. Payment processors and other project-specific integrations are outside this baseline.

## How the code is divided

Each business domain has its own `routes`, `schemas`, `services` and `repositories` folders. Shared API, database, security and error-handling code lives alongside those domains.

| Piece | Responsibility |
| --- | --- |
| Route | Receives HTTP input, checks the required permission, calls a service and returns an API response. |
| Schema | Defines valid inputs and the fields a response exposes. |
| Service | Coordinates a complete business operation and owns its transaction. |
| Repository | Reads and writes data using the shared database session; it never commits. |
| Database | Enforces ownership scope, relationships and rules that must always hold. |

For example, creating a record passes through a typed request, a permission-checked route, a service and a repository. PostgreSQL decides whether the resulting data is valid. A successful service commits the operation; a failed operation rolls back. This keeps HTTP concerns, workflow decisions and persistence separate.

## A consistent API

The API lives under `/api`. Resource versions follow the resource name, for example `/api/records/v1/`. A central `api/router.py` registers resource routers, while `api/response.py` defines the shared response shape:

```json
{"ok": true, "msg": "Record created", "data": {"id": "..."}}
```

Errors use the same fields with `ok: false` and an appropriate HTTP error status. This gives clients predictable handling across features.

## Login and access

The default login model uses one signed JWT in an HttpOnly browser cookie, with a fixed 90-minute lifespan. There is no refresh-token flow or automatic extension on each request. A user logs in again after expiry; an authorised scope switch can issue a new token. Passwords are hashed, and HTTPS cookies use Secure and SameSite settings. Browser writes also need cross-site request protection.

The token includes identity, roles, permissions and the relevant access scope. Permissions use role-based access control (RBAC): roles grant actions such as create, read, update and delete. The route confirms that the user may perform the requested action. PostgreSQL row-level security (RLS) limits which records the operation can touch.

Every project uses this split, but the scope comes from its domain. One project might isolate personal records by user; another might use organisations or tenants. We agree those boundaries before building the schema. Multiple scope levels get separate checks where needed.

Permissions in a token are a snapshot. Logging out removes the cookie but does not revoke a copied token; role or password changes do not automatically invalidate every existing token. Live database rules may restrict access sooner. If immediate revocation is a requirement, that is an explicit extension to agree.

## Rules belong in PostgreSQL

Database constraints, indexes, functions and triggers enforce durable rules such as uniqueness, valid relationships and allowed state changes. Services do not repeat those rules as competing Python checks. This also protects data when requests race or another trusted tool writes to the database.

Named database violations map to application errors with safe, useful messages. Unexpected failures return a generic server error and are logged internally. Services can still coordinate workflow prerequisites; PostgreSQL remains the authority for data invariants.

The application connects using a restricted database role so RLS applies. Admin credentials are reserved for human-run database setup. User and scope context lasts for one transaction, so workflows with later transactions must establish it again.

## Development, seeds and testing

During development we intentionally edit the original schema SQL files instead of accumulating incremental migrations for each change. The human rebuilds the development database after those edits. A rebuild destroys its target's data. Before maintaining production data, we explicitly agree a production migration policy.

Required seed data—such as the permission catalogue and roles—lives in real SQL files. Synthetic development data is separate: useful demo accounts and representative records are created once the domain is established. Production never receives these demo fixtures. Generated SQLAlchemy models follow the database schema and are not edited by hand.

The tool `sqlacodegen` reads the real database structure and writes `app/db/models.py`. Change SQL first, then have the human rebuild/regenerate; never correct the generated file directly. Models have no ORM relationships: repositories write explicit joins, keeping the model classes decoupled. The agent guide provides first-time installation and generation instructions. Frontend API types follow a similar source-to-generated workflow using OpenAPI.

Domain folders can align with database schemas and frontend API groups—for example, `auth` in all three—when that helps clarity. This is a recommended structure, not a requirement for every feature.

Neon has separate production, development and disposable test branches. The test branch normally comes from development; using production as its source is an explicit choice. The human configures separate admin/runtime connection details for each target and verifies the branch identity. Tests rebuild only the disposable test database.

Work is planned in sensible stages and built one small vertical slice at a time. Each slice delivers an end-to-end capability with clear acceptance criteria, including its database rules, permissions, application layers, dev fixtures and meaningful tests. Within a slice, work proceeds from agreed behaviour and access rules through data design, implementation and verification.

Tests cover successful operations, denied access, isolation, invalid changes and rollback. The agent writes tests and provides exact commands and effects; the human runs all tests and database operations, then reports the results. The agent waits for successful verification and the human's confirmation before starting the next slice. Failed checks are resolved within the current slice first. The agent never executes database-affecting commands.

The in-memory rate limiter is a development placeholder. Production rate limiting is a separate deployment decision.

## Decisions at the start of a project

Agree the domain and users, roles/actions, record ownership and scope, which endpoints are public, whether the default login lifetime fits, and how Neon branches are configured. Preserve the structure and core contracts; introduce additional services when a concrete feature requires them, offering AWS first.

This overview reflects static source inspection on 2026-10-27. No tests, application startup or database operations were run. The accompanying files are reusable templates, not a complete configured backend.
