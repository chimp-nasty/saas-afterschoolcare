from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings


engine = create_engine(
    settings.DATABASE_URL,
    pool_pre_ping=True,
)


SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)


def assert_rls_enforced() -> None:
    """
    Refuse to run as a database role that skips row level security.

    All tenant and customer isolation lives in the RLS policies, and a
    role with BYPASSRLS (or superuser) silently ignores them; every role
    created in the Neon console has BYPASSRLS. The API must connect as
    app_user, which migrations/schema/0006_runtime_role.sql creates.
    """
    with engine.connect() as conn:
        role, bypasses_rls, is_superuser = conn.execute(
            text("""
                SELECT rolname, rolbypassrls, rolsuper
                FROM pg_roles
                WHERE rolname = current_user;
            """)
        ).one()

    if bypasses_rls or is_superuser:
        raise RuntimeError(
            f"DATABASE_URL connects as '{role}', which bypasses row level "
            "security, so no tenant isolation would apply. Connect as "
            "app_user (see migrations/schema/0006_runtime_role.sql)."
        )
