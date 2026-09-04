from sqlalchemy import text
from sqlalchemy.engine import Connection


def up(conn: Connection) -> None:
    _enable_rls(conn)
    _create_global_policies(conn)
    _create_users_policy(conn)


def _enable_rls(conn: Connection) -> None:
    tables = (
        "roles",
        "permissions",
        "role_permissions",
        "users",
    )

    for table in tables:
        conn.execute(
            text(f"""
                ALTER TABLE auth.{table}
                ENABLE ROW LEVEL SECURITY;
            """)
        )

        conn.execute(
            text(f"""
                ALTER TABLE auth.{table}
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
        "roles",
        "permissions",
        "role_permissions",
    )

    for table in tables:
        conn.execute(
            text(f"""
                CREATE POLICY {table}_scope_policy
                ON auth.{table}
                FOR ALL
                USING (true)
                WITH CHECK (true);
            """)
        )


# -------------------------------------------------------------------------
# USERS
# -------------------------------------------------------------------------

def _create_users_policy(
    conn: Connection,
) -> None:
    predicate = """
        id = current_setting(
            'app.user_id',
            true
        )::uuid

        OR

        EXISTS (
            SELECT 1
            FROM auth.location_user_roles current_ulr

            JOIN auth.roles cr
                ON cr.id = current_ulr.role_id

            JOIN auth.location_user_roles target_ulr
                ON target_ulr.location_id =
                   current_ulr.location_id

            JOIN auth.roles tr
                ON tr.id = target_ulr.role_id

            WHERE current_ulr.user_id =
                current_setting(
                    'app.user_id',
                    true
                )::uuid

              AND target_ulr.user_id =
                  users.id

              AND (
                  (
                      cr.name = 'staff'
                      AND tr.name = 'customer'
                  )

                  OR

                  (
                      cr.name = 'admin'
                      AND tr.name IN (
                          'staff',
                          'customer'
                      )
                  )

                  OR

                  (
                      cr.name = 'superadmin'
                      AND tr.name IN (
                          'admin',
                          'staff',
                          'customer'
                      )
                  )
              )
        )
    """

    conn.execute(
        text(f"""
            CREATE POLICY users_scope_policy
            ON auth.users
            FOR SELECT
            USING (
                {predicate}
            );
        """)
    )

    conn.execute(
        text(f"""
            CREATE POLICY users_update_policy
            ON auth.users
            FOR UPDATE
            USING (
                {predicate}
            )
            WITH CHECK (
                {predicate}
            );
        """)
    )

    conn.execute(
        text(f"""
            CREATE POLICY users_delete_policy
            ON auth.users
            FOR DELETE
            USING (
                {predicate}
            );
        """)
    )

    conn.execute(
        text("""
            CREATE POLICY users_insert_scope_policy
            ON auth.users
            FOR INSERT
            WITH CHECK (true);
        """)
    )