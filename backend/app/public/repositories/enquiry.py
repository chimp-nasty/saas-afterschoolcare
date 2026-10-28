from uuid import UUID

from sqlalchemy import Row, text

from app.db.repository import Repository


_COLUMNS = "e.id, e.name, e.email, e.phone, e.topic::text AS topic, e.status::text AS status, e.created_at, e.replied_at"


class EnquiryRepository(Repository):
    """
    Contact form enquiries and their replies (docs/enquiries.md). They
    arrive through public.submit_enquiry (anyone, no session); the rest is
    the centre's admins, under RLS.
    """

    def submit(
        self,
        *,
        location_id: UUID,
        name: str,
        email: str,
        phone: str | None,
        topic: str,
        message: str,
    ) -> UUID:
        return self.db.execute(
            text("SELECT public.submit_enquiry(:location_id, :name, :email, :phone, CAST(:topic AS public.enquiry_topic_enum), :message)"),
            {"location_id": location_id, "name": name, "email": email, "phone": phone, "topic": topic, "message": message},
        ).scalar_one()

    def list_for_location(
        self,
        *,
        location_id: UUID,
        statuses: list[str],
    ) -> list[Row]:
        """Newest first, with the start of each message."""
        return self.db.execute(
            text(
                f"""
                SELECT {_COLUMNS}, left(e.message, 140) AS preview
                FROM public.enquiries e
                WHERE e.location_id = :location_id
                  AND e.status::text = ANY(:statuses)
                ORDER BY e.created_at DESC
                LIMIT 200
                """
            ),
            {"location_id": location_id, "statuses": statuses},
        ).all()

    def get(
        self,
        *,
        id: UUID,
        location_id: UUID,
    ) -> Row | None:
        return self.db.execute(
            text(
                f"""
                SELECT {_COLUMNS}, e.message, e.closed_at
                FROM public.enquiries e
                WHERE e.id = :id AND e.location_id = :location_id
                """
            ),
            {"id": id, "location_id": location_id},
        ).first()

    def replies(
        self,
        *,
        enquiry_id: UUID,
    ) -> list[Row]:
        return self.db.execute(
            text(
                """
                SELECT r.id, r.body, r.created_at,
                       NULLIF(btrim(concat_ws(' ', u.first_name, u.last_name)), '') AS staff_name
                FROM public.enquiry_replies r
                LEFT JOIN auth.users u
                    ON u.id = r.staff_user_id
                WHERE r.enquiry_id = :enquiry_id
                ORDER BY r.created_at, r.id
                """
            ),
            {"enquiry_id": enquiry_id},
        ).all()

    def add_reply(
        self,
        *,
        enquiry_id: UUID,
        body: str,
    ) -> None:
        # The trigger sets who, where and when, and marks the enquiry replied.
        self.db.execute(
            text("INSERT INTO public.enquiry_replies (enquiry_id, location_id, body) VALUES (:enquiry_id, (SELECT location_id FROM public.enquiries WHERE id = :enquiry_id), :body)"),
            {"enquiry_id": enquiry_id, "body": body},
        )

    def set_status(
        self,
        *,
        id: UUID,
        status: str,
    ) -> None:
        # The trigger stamps closed_at and keeps the rest as sent.
        self.db.execute(
            text("UPDATE public.enquiries SET status = CAST(:status AS public.enquiry_status_enum) WHERE id = :id"),
            {"id": id, "status": status},
        )
