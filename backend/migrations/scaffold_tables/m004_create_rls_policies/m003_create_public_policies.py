from sqlalchemy import text
from sqlalchemy.engine import Connection


def up(conn: Connection) -> None:
    _enable_rls(conn)

    _create_global_policies(conn)
    _create_user_owned_policies(conn)
    _create_location_scoped_policies(conn)
    _create_user_location_scoped_policies(conn)

    _create_customer_profile_policy(conn)

    _create_child_inherited_policies(conn)
    _create_booking_inherited_policies(conn)


def _enable_rls(conn: Connection) -> None:
    tables = (
        "service_types",
        "customer_profile",
        "customer_kiosk_pins",
        "booking_groups",
        "location_services",
        "location_service_days",
        "location_kiosk_devices",
        "child_profile",
        "bookings",
        "payment_attempts",
        "refunds",
        "child_medical_state",
        "child_medical_reviews",
        "child_notes",
        "child_documents",
        "authorized_pickup_persons",
        "attendance_records",
    )

    for table in tables:
        conn.execute(
            text(f"""
                ALTER TABLE public.{table}
                ENABLE ROW LEVEL SECURITY;
            """)
        )

        conn.execute(
            text(f"""
                ALTER TABLE public.{table}
                FORCE ROW LEVEL SECURITY;
            """)
        )


# -------------------------------------------------------------------------
# GLOBAL / NO ROW SCOPE
# -------------------------------------------------------------------------

def _create_global_policies(
    conn: Connection,
) -> None:
    conn.execute(
        text("""
            CREATE POLICY service_types_scope_policy
            ON public.service_types
            FOR ALL
            USING (true)
            WITH CHECK (true);
        """)
    )


# -------------------------------------------------------------------------
# USER-OWNED
# -------------------------------------------------------------------------

def _create_user_owned_policies(
    conn: Connection,
) -> None:
    tables = (
        "customer_kiosk_pins",
        "booking_groups",
    )

    for table in tables:
        conn.execute(
            text(f"""
                CREATE POLICY {table}_scope_policy
                ON public.{table}
                FOR ALL
                USING (
                    user_id = current_setting(
                        'app.user_id',
                        true
                    )::uuid
                )
                WITH CHECK (
                    user_id = current_setting(
                        'app.user_id',
                        true
                    )::uuid
                );
            """)
        )


# -------------------------------------------------------------------------
# LOCATION-SCOPED
# -------------------------------------------------------------------------

def _create_location_scoped_policies(
    conn: Connection,
) -> None:
    _create_location_policy(
        conn=conn,
        table="location_services",
        location_expression="location_services.location_id",
    )

    _create_location_policy(
        conn=conn,
        table="location_kiosk_devices",
        location_expression="location_kiosk_devices.location_id",
    )

    _create_location_service_days_policy(conn)


def _create_location_policy(
    *,
    conn: Connection,
    table: str,
    location_expression: str,
) -> None:
    predicate = f"""
        EXISTS (
            SELECT 1
            FROM auth.location_user_roles lur
            WHERE lur.user_id =
                current_setting(
                    'app.user_id',
                    true
                )::uuid

              AND lur.location_id =
                  {location_expression}
        )
    """

    conn.execute(
        text(f"""
            CREATE POLICY {table}_scope_policy
            ON public.{table}
            FOR ALL
            USING (
                {predicate}
            )
            WITH CHECK (
                {predicate}
            );
        """)
    )


def _create_location_service_days_policy(
    conn: Connection,
) -> None:
    predicate = """
        EXISTS (
            SELECT 1
            FROM public.location_services ls
            JOIN auth.location_user_roles lur
                ON lur.location_id = ls.location_id
            WHERE ls.id =
                location_service_days.location_service_id

              AND lur.user_id =
                current_setting(
                    'app.user_id',
                    true
                )::uuid
        )
    """

    conn.execute(
        text(f"""
            CREATE POLICY location_service_days_scope_policy
            ON public.location_service_days
            FOR ALL
            USING (
                {predicate}
            )
            WITH CHECK (
                {predicate}
            );
        """)
    )


# -------------------------------------------------------------------------
# USER + LOCATION SCOPED
# -------------------------------------------------------------------------

def _create_user_location_scoped_policies(
    conn: Connection,
) -> None:
    tables = (
        "child_profile",
        "bookings",
        "payment_attempts",
        "refunds",
    )

    for table in tables:
        _create_user_location_policy(
            conn=conn,
            table=table,
        )


def _create_user_location_policy(
    *,
    conn: Connection,
    table: str,
) -> None:
    predicate = f"""
        EXISTS (
            SELECT 1
            FROM auth.location_user_roles lur
            JOIN auth.roles r
                ON r.id = lur.role_id
            WHERE lur.user_id =
                current_setting(
                    'app.user_id',
                    true
                )::uuid

              AND lur.location_id =
                  {table}.location_id

              AND (
                  r.name IN (
                      'superadmin',
                      'admin',
                      'staff'
                  )

                  OR (
                      r.name = 'customer'
                      AND {table}.user_id =
                          current_setting(
                              'app.user_id',
                              true
                          )::uuid
                  )
              )
        )
    """

    conn.execute(
        text(f"""
            CREATE POLICY {table}_scope_policy
            ON public.{table}
            FOR ALL
            USING (
                {predicate}
            )
            WITH CHECK (
                {predicate}
            );
        """)
    )


# -------------------------------------------------------------------------
# INHERITED FROM USERS
# -------------------------------------------------------------------------

def _create_customer_profile_policy(
    conn: Connection,
) -> None:
    predicate = """
        user_id = current_setting(
            'app.user_id',
            true
        )::uuid

        OR

        EXISTS (
            SELECT 1
            FROM auth.location_user_roles current_lur

            JOIN auth.roles cr
                ON cr.id = current_lur.role_id

            JOIN auth.location_user_roles target_lur
                ON target_lur.location_id =
                   current_lur.location_id

            JOIN auth.roles tr
                ON tr.id = target_lur.role_id

            WHERE current_lur.user_id =
                current_setting(
                    'app.user_id',
                    true
                )::uuid

              AND target_lur.user_id =
                  customer_profile.user_id

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
            CREATE POLICY customer_profile_scope_policy
            ON public.customer_profile
            FOR ALL
            USING (
                {predicate}
            )
            WITH CHECK (
                {predicate}
            );
        """)
    )


# -------------------------------------------------------------------------
# INHERITED FROM CHILD_PROFILE
# -------------------------------------------------------------------------

def _create_child_inherited_policies(
    conn: Connection,
) -> None:
    tables = (
        "child_medical_state",
        "child_medical_reviews",
        "child_notes",
        "child_documents",
        "authorized_pickup_persons",
    )

    for table in tables:
        _create_child_inherited_policy(
            conn=conn,
            table=table,
        )


def _create_child_inherited_policy(
    *,
    conn: Connection,
    table: str,
) -> None:
    predicate = f"""
        EXISTS (
            SELECT 1
            FROM public.child_profile cp
            JOIN auth.location_user_roles lur
                ON lur.location_id = cp.location_id
            JOIN auth.roles r
                ON r.id = lur.role_id
            WHERE cp.id = {table}.child_id

              AND lur.user_id =
                  current_setting(
                      'app.user_id',
                      true
                  )::uuid

              AND (
                  r.name IN (
                      'superadmin',
                      'admin',
                      'staff'
                  )

                  OR (
                      r.name = 'customer'
                      AND cp.user_id =
                          current_setting(
                              'app.user_id',
                              true
                          )::uuid
                  )
              )
        )
    """

    conn.execute(
        text(f"""
            CREATE POLICY {table}_scope_policy
            ON public.{table}
            FOR ALL
            USING (
                {predicate}
            )
            WITH CHECK (
                {predicate}
            );
        """)
    )


# -------------------------------------------------------------------------
# INHERITED FROM BOOKINGS
# -------------------------------------------------------------------------

def _create_booking_inherited_policies(
    conn: Connection,
) -> None:
    predicate = """
        EXISTS (
            SELECT 1
            FROM public.bookings b
            JOIN auth.location_user_roles lur
                ON lur.location_id = b.location_id
            JOIN auth.roles r
                ON r.id = lur.role_id
            WHERE b.id =
                attendance_records.booking_id

              AND lur.user_id =
                  current_setting(
                      'app.user_id',
                      true
                  )::uuid

              AND (
                  r.name IN (
                      'superadmin',
                      'admin',
                      'staff'
                  )

                  OR (
                      r.name = 'customer'
                      AND b.user_id =
                          current_setting(
                              'app.user_id',
                              true
                          )::uuid
                  )
              )
        )
    """

    conn.execute(
        text(f"""
            CREATE POLICY attendance_records_scope_policy
            ON public.attendance_records
            FOR ALL
            USING (
                {predicate}
            )
            WITH CHECK (
                {predicate}
            );
        """)
    )