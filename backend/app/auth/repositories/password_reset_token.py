from datetime import datetime
from uuid import UUID

from sqlalchemy import func

from app.db.repository import Repository
from app.db.models import PasswordResetToken


class PasswordResetTokenRepository(Repository):
    def create(
        self,
        *,
        user_id: UUID,
        location_id: UUID,
        token_hash: str,
        expires_at: datetime,
        used_at: datetime | None = None,
    ) -> PasswordResetToken:
        record = PasswordResetToken(
            user_id=user_id,
            location_id=location_id,
            token_hash=token_hash,
            expires_at=expires_at,
            used_at=used_at,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> PasswordResetToken | None:
        return (
            self.db.query(PasswordResetToken)
            .filter(PasswordResetToken.id == id)
            .first()
        )

    def get_valid_by_token_hash(
        self,
        *,
        token_hash
    ) -> PasswordResetToken | None:
        return (
            self.db.query(PasswordResetToken)
            .filter(PasswordResetToken.token_hash == token_hash)
            .filter(PasswordResetToken.used_at.is_(None))
            .filter(PasswordResetToken.expires_at > func.now())
            .first()
        )

    def revoke_unused(
        self,
        *,
        user_id: UUID,
        location_id: UUID,
    ) -> None:
        """Earlier links for this user at this location stop working (a new invite)."""
        (
            self.db.query(PasswordResetToken)
            .filter(
                PasswordResetToken.user_id == user_id,
                PasswordResetToken.location_id == location_id,
                PasswordResetToken.used_at.is_(None),
            )
            .update({PasswordResetToken.used_at: func.now()}, synchronize_session=False)
        )

    def mark_used(
        self,
        *,
        token: PasswordResetToken,
    ) -> None:
        token.used_at = func.now()