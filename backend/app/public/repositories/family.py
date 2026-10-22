import re
from datetime import date
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.engine import Row

from app.db.repository import Repository


class FamilyRepository(Repository):
    """
    Families at a location, for its admins (Admin › Families): search, the
    family page, attendance history and payments. Under RLS: admins see the
    location's families (can_manage_user, can_access_location_row).
    """

    def search(
        self,
        *,
        location_id: UUID,
        text_query: str,
        limit: int = 50,
    ) -> list[Row]:
        """
        By a parent's or child's name, an email, or a phone number (contains).
        Phones are matched only when the search looks like one (digits and
        phone punctuation, 4+ digits), so the digits in an email or a name
        ("customer-c04") don't match every mobile.
        """
        words = "%" + text_query.replace("%", "").replace("_", "") + "%"
        looks_like_phone = re.fullmatch(r"[\d\s()+-]+", text_query) is not None
        digits = "".join(ch for ch in text_query if ch.isdigit())
        digits = digits if looks_like_phone and len(digits) >= 4 else ""

        return self.db.execute(
            text("""
                SELECT
                    u.id AS user_id,
                    u.first_name,
                    u.last_name,
                    u.email,
                    cp.phone,
                    (
                        SELECT string_agg(c.first_name, ', ' ORDER BY c.first_name)
                        FROM public.child_profile c
                        WHERE c.user_id = u.id AND c.location_id = l.id AND c.is_active
                    ) AS children,
                    (
                        SELECT count(*)
                        FROM public.bookings b
                        JOIN public.location_service_days d ON d.id = b.location_service_day_id
                        WHERE b.user_id = u.id
                          AND b.location_id = l.id
                          AND b.booking_status = 'CONFIRMED'
                          AND d.service_date >= (now() AT TIME ZONE l.timezone)::date
                    ) AS upcoming,
                    (
                        SELECT count(*)
                        FROM public.bookings b
                        WHERE b.user_id = u.id
                          AND b.location_id = l.id
                          AND public.effective_booking_status(b.booking_status, b.created_at) = 'PENDING'
                    ) AS unpaid
                FROM auth.location_user_roles lur
                JOIN auth.roles r ON r.id = lur.role_id AND r.code = 'customer'
                JOIN tenancy.locations l ON l.id = lur.location_id
                JOIN auth.users u ON u.id = lur.user_id
                LEFT JOIN public.customer_profile cp ON cp.user_id = u.id
                WHERE lur.location_id = :location_id
                  AND (
                      u.first_name ILIKE :words
                      OR u.last_name ILIKE :words
                      OR (u.first_name || ' ' || u.last_name) ILIKE :words
                      OR u.email ILIKE :words
                      OR (:digits <> '' AND regexp_replace(COALESCE(cp.phone, ''), '[^0-9]', '', 'g') LIKE '%' || :digits || '%')
                      OR EXISTS (
                          SELECT 1
                          FROM public.child_profile c
                          WHERE c.user_id = u.id
                            AND c.location_id = l.id
                            AND (c.first_name ILIKE :words OR c.last_name ILIKE :words
                                 OR (c.first_name || ' ' || c.last_name) ILIKE :words)
                      )
                  )
                ORDER BY u.last_name, u.first_name
                LIMIT :limit
            """),
            {"location_id": location_id, "words": words, "digits": digits, "limit": limit},
        ).all()

    def get(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
    ) -> Row | None:
        """The family's parent and profile, if they're a family at this location."""
        return self.db.execute(
            text("""
                SELECT
                    u.id AS user_id, u.first_name, u.last_name, u.email,
                    cp.phone, cp.address_line_1, cp.address_line_2, cp.suburb, cp.state, cp.postcode,
                    cp.emergency_contact_name, cp.emergency_contact_phone,
                    cp.emergency_contact_relation::text AS emergency_contact_relation,
                    cp.emergency_contact_relation_other
                FROM auth.users u
                LEFT JOIN public.customer_profile cp ON cp.user_id = u.id
                WHERE u.id = :user_id
                  AND EXISTS (
                      SELECT 1
                      FROM auth.location_user_roles lur
                      JOIN auth.roles r ON r.id = lur.role_id
                      WHERE lur.user_id = u.id AND lur.location_id = :location_id AND r.code = 'customer'
                  )
            """),
            {"location_id": location_id, "user_id": user_id},
        ).first()

    def children(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
    ) -> list[Row]:
        return self.db.execute(
            text("""
                SELECT c.id, c.first_name, c.last_name, c.dob, c.is_active,
                       COALESCE(ms.review_status::text, 'not_required') AS review_status
                FROM public.child_profile c
                LEFT JOIN public.child_medical_state ms ON ms.child_id = c.id
                WHERE c.user_id = :user_id AND c.location_id = :location_id
                ORDER BY c.is_active DESC, c.first_name, c.last_name
            """),
            {"location_id": location_id, "user_id": user_id},
        ).all()

    def attendance(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
        date_from: date,
        date_to: date,
    ) -> list[Row]:
        """The family's confirmed sessions up to today, newest first, with who did what."""
        return self.db.execute(
            text("""
                SELECT
                    b.id AS booking_id,
                    d.service_date,
                    st.name AS service_name,
                    c.first_name AS child_first_name,
                    c.last_name AS child_last_name,
                    ar.signed_in_at,
                    COALESCE(
                        public.staff_short_name(ar.signed_in_by_user_id),
                        si.first_name || ' ' || si.last_name
                    ) AS signed_in_by,
                    ar.signed_out_at,
                    public.staff_short_name(ar.signed_out_by_user_id) AS signed_out_by,
                    col.first_name || ' ' || col.last_name AS collected_by,
                    CASE WHEN col.id IS NOT NULL THEN
                        col.identity_verified_at IS NOT NULL AND col.identity_verified_at <= ar.signed_out_at
                    END AS collector_id_sighted,
                    ar.released_to_name,
                    ar.release_note,
                    COALESCE(ar.sent_to_school, FALSE) AS sent_to_school,
                    (
                        ar.signed_in_at IS NOT NULL
                        AND COALESCE(ar.signed_out_at, now())
                            > ((d.service_date + lsc.end_time) AT TIME ZONE l.timezone)
                    ) AS left_late
                FROM public.bookings b
                JOIN public.location_service_days d ON d.id = b.location_service_day_id
                JOIN public.location_services ls ON ls.id = d.location_service_id
                JOIN public.service_types st ON st.id = ls.service_type_id
                JOIN public.location_service_config lsc ON lsc.location_service_id = ls.id
                JOIN public.child_profile c ON c.id = b.child_id
                JOIN tenancy.locations l ON l.id = b.location_id
                LEFT JOIN public.attendance_records ar ON ar.booking_id = b.id
                LEFT JOIN public.authorized_pickup_persons si ON si.id = ar.signed_in_by_pickup_person_id
                LEFT JOIN public.authorized_pickup_persons col ON col.id = ar.collected_by_pickup_person_id
                WHERE b.user_id = :user_id
                  AND b.location_id = :location_id
                  AND b.booking_status = 'CONFIRMED'
                  AND d.service_date BETWEEN :date_from AND :date_to
                  AND d.service_date <= (now() AT TIME ZONE l.timezone)::date
                ORDER BY d.service_date DESC, lsc.start_time, c.first_name
            """),
            {"location_id": location_id, "user_id": user_id, "date_from": date_from, "date_to": date_to},
        ).all()

    def payments(
        self,
        *,
        location_id: UUID,
        user_id: UUID,
        limit: int = 100,
    ) -> list[Row]:
        return self.db.execute(
            text("""
                SELECT
                    pa.id, pa.created_at, pa.paid_at, pa.total_cents, pa.currency,
                    pa.stripe_status::text AS stripe_status,
                    pa.stripe_receipt_url AS receipt_url,
                    (SELECT count(*) FROM public.bookings b WHERE b.booking_group_id = pa.booking_group_id) AS bookings,
                    (
                        SELECT COALESCE(sum(r.amount_cents), 0)
                        FROM public.refunds r
                        WHERE r.payment_attempt_id = pa.id AND r.status = 'SUCCEEDED'
                    ) AS refunded_cents
                FROM public.payment_attempts pa
                WHERE pa.user_id = :user_id AND pa.location_id = :location_id
                ORDER BY pa.created_at DESC
                LIMIT :limit
            """),
            {"location_id": location_id, "user_id": user_id, "limit": limit},
        ).all()
