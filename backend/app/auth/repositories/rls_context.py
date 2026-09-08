from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session


class RlsContextRepository:
    def __init__(self, *, db: Session):
        self.db = db

    def set_user_id(
        self,
        *,
        user_id: UUID,
    ) -> None:
        self.db.execute(
            select(
                func.set_config(
                    "app.user_id",
                    str(user_id),
                    True,
                )
            )
        )

    def set_login_email(
        self,
        email: str,
    ) -> None:
        self.db.execute(
            select(
                func.set_config(
                    "app.login_email",
                    email,
                    True,
                )
            )
        )