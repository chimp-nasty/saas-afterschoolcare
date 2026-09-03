from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.jwt.context import TokenContext
from app.dependencies.db import get_db
from app.dependencies.auth import get_current_token_context


def get_rls_db(
    db: Session = Depends(get_db),
    ctx: TokenContext = Depends(
        get_current_token_context,
    ),
) -> Session:
    db.execute(
        text("""
            SELECT set_config(
                'app.user_id',
                :user_id,
                true
            )
        """),
        {
            "user_id": str(ctx.user_id),
        },
    )

    db.execute(
        text("""
            SELECT set_config(
                'app.location_id',
                :location_id,
                true
            )
        """),
        {
            "location_id": str(ctx.location_id),
        },
    )

    return db