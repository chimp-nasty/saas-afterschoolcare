from sqlalchemy import text
from sqlalchemy.engine import Connection


def up(conn: Connection) -> None:
    _enable_rls(conn)
    _create_global_policies(conn)
    _create_tenant_policies(conn)


def _enable_rls(conn: Connection) -> None:
    tables = (
        "locations",
        "location_branding",
        "tenants",
    )

    for table in tables:
        conn.execute(
            text(f"""
                ALTER TABLE tenancy.{table}
                ENABLE ROW LEVEL SECURITY;
            """)
        )

        conn.execute(
            text(f"""
                ALTER TABLE tenancy.{table}
                FORCE ROW LEVEL SECURITY;
            """)
        )


# -------------------------------------------------------------------------
# GLOBAL / NO ROW SCOPE
# -------------------------------------------------------------------------

def _create_global_policies(
    conn: Connection,
) -> None:
    tables = (
        "locations",
        "location_branding",
    )

    for table in tables:
        conn.execute(
            text(f"""
                CREATE POLICY {table}_scope_policy
                ON tenancy.{table}
                FOR ALL
                USING (true)
                WITH CHECK (true);
            """)
        )


# -------------------------------------------------------------------------
# TENANT-SCOPED
# -------------------------------------------------------------------------

def _create_tenant_policies(
    conn: Connection,
) -> None:
    predicate = """
        EXISTS (
            SELECT 1
            FROM auth.location_user_roles ulr
            JOIN auth.roles r
                ON r.id = ulr.role_id
            JOIN tenancy.locations l
                ON l.id = ulr.location_id
            WHERE ulr.user_id =
                current_setting(
                    'app.user_id',
                    true
                )::uuid

              AND l.tenant_id = tenants.id

              AND r.name = 'superadmin'
        )
    """

    conn.execute(
        text(f"""
            CREATE POLICY tenants_scope_policy
            ON tenancy.tenants
            FOR ALL
            USING (
                {predicate}
            )
            WITH CHECK (
                {predicate}
            );
        """)
    )