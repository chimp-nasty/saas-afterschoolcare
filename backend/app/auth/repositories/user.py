from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from app.auth.models.user import User


class UserRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def create(
        self,
        *,
        email: str,
        password_hash: str,
        first_name: str,
        last_name: str,
        terms_accepted_at: datetime,
        terms_version: str = "v1",
        is_active: bool = False,
        last_login: datetime | None = None,
    ) -> User:
        record = User(
            email=email,
            password_hash=password_hash,
            first_name=first_name,
            last_name=last_name,
            terms_accepted_at=terms_accepted_at,
            terms_version=terms_version,
            is_active=is_active,
            last_login=last_login,
        )

        self.db.add(record)
        self.db.flush()

        return record

    def get_by_id(
        self,
        *,
        id: UUID,
    ) -> User | None:
        return (
            self.db.query(User)
            .filter(User.id == id)
            .first()
        )

    def get_by_email(
        self,
        *,
        email: str
    ) -> User | None:
        return (
            self.db.query(User)
            .filter(User.email == email)
            .first()
        )
        
    def update_last_login(
        self,
        *,
        user: User
    ) -> None:
        user.last_login = datetime.now(timezone.utc)
        
    def update_password_hash(
        self,
        *,
        user: User,
        password_hash: str
    ) -> None:
        user.password_hash = password_hash