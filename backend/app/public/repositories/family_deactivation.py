from uuid import UUID

from sqlalchemy import Row, text

from app.db.repository import Repository


class FamilyDeactivationRepository(Repository):
    """
    Families deactivated at a centre (public.family_deactivations,
    docs/account-deactivation.md). The database sets the dates and checks
    who may deactivate and when; RLS decides who sees and changes rows.
    """

    def is_deactivated(
        self,
        *,
        user_id: UUID,
        location_id: UUID,
    ) -> bool:
        """Yes or no, before a request's RLS settings exist (SECURITY DEFINER)."""
        return self.db.execute(
            text("SELECT public.family_is_deactivated(:user_id, :location_id)"),
            {"user_id": user_id, "location_id": location_id},
        ).scalar_one()

    def reactivation_requested(
        self,
        *,
        user_id: UUID,
        location_id: UUID,
    ) -> bool:
        """Whether a deactivated family has asked to come back (SECURITY DEFINER, like is_deactivated)."""
        return self.db.execute(
            text("SELECT public.family_reactivation_requested(:user_id, :location_id)"),
            {"user_id": user_id, "location_id": location_id},
        ).scalar_one()

    def get(
        self,
        *,
        user_id: UUID,
        location_id: UUID,
    ) -> Row | None:
        return self.db.execute(
            text(
                """
                SELECT user_id, location_id, deactivated_at, retain_until, reactivation_requested_at
                FROM public.family_deactivations
                WHERE user_id = :user_id AND location_id = :location_id
                """
            ),
            {"user_id": user_id, "location_id": location_id},
        ).first()

    def create(
        self,
        *,
        user_id: UUID,
        location_id: UUID,
    ) -> None:
        # The trigger sets the dates (deactivated_at, retain_until).
        self.db.execute(
            text(
                """
                INSERT INTO public.family_deactivations (user_id, location_id, retain_until)
                VALUES (:user_id, :location_id, now())
                """
            ),
            {"user_id": user_id, "location_id": location_id},
        )

    def request_reactivation(
        self,
        *,
        user_id: UUID,
        location_id: UUID,
    ) -> None:
        # Stamped once, by the database's clock (trg_family_deactivations_keep).
        self.db.execute(
            text(
                """
                UPDATE public.family_deactivations
                SET reactivation_requested_at = now()
                WHERE user_id = :user_id AND location_id = :location_id
                """
            ),
            {"user_id": user_id, "location_id": location_id},
        )

    def delete(
        self,
        *,
        user_id: UUID,
        location_id: UUID,
    ) -> int:
        return self.db.execute(
            text("DELETE FROM public.family_deactivations WHERE user_id = :user_id AND location_id = :location_id"),
            {"user_id": user_id, "location_id": location_id},
        ).rowcount

    def list_reactivation_requests(
        self,
        *,
        location_id: UUID,
    ) -> list[Row]:
        """Families at the centre who've asked to be reactivated, longest waiting first."""
        return self.db.execute(
            text(
                """
                SELECT fd.user_id, u.first_name, u.last_name, u.email,
                       fd.deactivated_at, fd.reactivation_requested_at
                FROM public.family_deactivations fd
                JOIN auth.users u
                    ON u.id = fd.user_id
                WHERE fd.location_id = :location_id
                  AND fd.reactivation_requested_at IS NOT NULL
                ORDER BY fd.reactivation_requested_at
                """
            ),
            {"location_id": location_id},
        ).all()
