import sys

from sqlalchemy import text
from sqlalchemy.engine import Connection

from app.core.config import settings
from app.db.session import SessionLocal
from .scaffold_tables import up as scaffold_tables
from .seed_data import up as seed_data


MIGRATION_SCHEMA = "migrations"
MIGRATION_TABLE = f"{MIGRATION_SCHEMA}.migration_history"


def get_engine():
    return SessionLocal.kw["bind"]


def ensure_migration_table(
    conn: Connection,
) -> None:
    conn.execute(
        text(
            f"""
            CREATE SCHEMA IF NOT EXISTS {MIGRATION_SCHEMA};

            CREATE TABLE IF NOT EXISTS {MIGRATION_TABLE} (
                id SERIAL PRIMARY KEY,
                migration_name VARCHAR(255) NOT NULL UNIQUE,
                applied_at TIMESTAMPTZ NOT NULL
                    DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
    )


def migration_applied(
    conn: Connection,
    migration_name: str,
) -> bool:
    result = conn.execute(
        text(
            f"""
            SELECT 1
            FROM {MIGRATION_TABLE}
            WHERE migration_name = :name
            LIMIT 1;
            """
        ),
        {
            "name": migration_name,
        },
    )

    return result.scalar() is not None


def record_migration(
    conn: Connection,
    migration_name: str,
) -> None:
    conn.execute(
        text(
            f"""
            INSERT INTO {MIGRATION_TABLE} (
                migration_name
            )
            VALUES (:name);
            """
        ),
        {
            "name": migration_name,
        },
    )


def run_migration(
    *,
    conn: Connection,
    name: str,
    migration,
) -> bool:
    if migration_applied(
        conn,
        name,
    ):
        return False

    print(f"Running migration: {name}")

    migration(conn)

    record_migration(
        conn,
        name,
    )

    print(f"Migration completed: {name}")

    return True


def run() -> dict[str, bool]:
    engine = get_engine()

    with engine.connect() as conn:
        with conn.begin():
            ensure_migration_table(conn)

            scaffold_applied = run_migration(
                conn=conn,
                name="scaffold_tables",
                migration=scaffold_tables,
            )

            seed_applied = run_migration(
                conn=conn,
                name="seed_data",
                migration=seed_data,
            )

    return {
        "scaffold_tables": scaffold_applied,
        "seed_data": seed_applied,
    }


def reset() -> None:
    if settings.APP_ENV != "dev":
        raise RuntimeError(
            "Database reset is only permitted "
            "when APP_ENV='dev'."
        )

    engine = get_engine()

    with engine.connect() as conn:
        with conn.begin():
            conn.execute(
                text(
                    """
                    DROP SCHEMA IF EXISTS
                        authorization CASCADE;

                    DROP SCHEMA IF EXISTS
                        tenancy CASCADE;

                    DROP SCHEMA IF EXISTS
                        migrations CASCADE;
                    """
                )
            )

    print("Database reset completed.")


def rebuild() -> dict[str, bool]:
    reset()
    return run()


def main() -> None:
    command = (
        sys.argv[1].lower()
        if len(sys.argv) > 1
        else "run"
    )

    if command == "run":
        print(run())
        return

    if command == "reset":
        reset()
        return

    if command == "rebuild":
        print(rebuild())
        return

    raise ValueError(
        f"Unknown migration command: {command}"
    )


if __name__ == "__main__":
    main()