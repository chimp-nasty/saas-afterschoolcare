from uuid import UUID

from sqlalchemy import Row, text

from app.db.repository import Repository


class PlatformEnquiryRepository(Repository):
    """
    Enquiries to the platform itself (docs/platform-site.md). They arrive
    through public.submit_platform_enquiry (anyone, no session); the
    platform's admins read and close them, under RLS.
    """

    def submit(
        self,
        *,
        name: str,
        email: str,
        phone: str | None,
        business_name: str | None,
        topic: str,
        message: str,
    ) -> UUID:
        return self.db.execute(
            text(
                "SELECT public.submit_platform_enquiry(:name, :email, :phone, :business_name, "
                "CAST(:topic AS public.platform_enquiry_topic_enum), :message)"
            ),
            {"name": name, "email": email, "phone": phone, "business_name": business_name, "topic": topic, "message": message},
        ).scalar_one()

    def list(self, *, closed: bool) -> list[Row]:
        """Open ones (or closed ones), newest first."""
        return self.db.execute(
            text(
                """
                SELECT id, name, email, phone, business_name, topic::text AS topic, message, created_at, closed_at
                FROM public.platform_enquiries
                WHERE (closed_at IS NOT NULL) = :closed
                ORDER BY created_at DESC
                LIMIT 200
                """
            ),
            {"closed": closed},
        ).all()

    def set_closed(self, *, id: UUID, closed: bool) -> Row | None:
        return self.db.execute(
            text(
                """
                UPDATE public.platform_enquiries
                SET closed_at = CASE WHEN :closed THEN now() END
                WHERE id = :id
                RETURNING id, name, email, phone, business_name, topic::text AS topic, message, created_at, closed_at
                """
            ),
            {"id": id, "closed": closed},
        ).first()
