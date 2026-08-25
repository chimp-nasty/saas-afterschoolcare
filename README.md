# Backend Shell

Agreed FastAPI backend shell.

## Architectural rules

- Routes call services, never repositories directly.
- Services own transactions and business/application logging.
- Repositories own persistence and never commit.
- SQLAlchemy models and repositories generally map one-to-one.
- Pydantic request/response models live under `schemas`.
- Simple cohesive CRUD may share an entity service.
- Complex workflows use dedicated service modules.
- External providers live behind `integrations`.
- PostgreSQL schemas are `authorization`, `tenancy`, and `public`.
- Custom migrations live outside `app`.
- API contract uses `/api/v1`.
- JWTs carry one active tenant context plus roles and a permission snapshot.
- Tests target meaningful behaviour rather than requiring a test per module.
