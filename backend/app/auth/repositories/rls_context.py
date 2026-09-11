from uuid import UUID

from sqlalchemy import func, select

from app.db.repository import Repository


class RlsContextRepository(Repository):
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