from functools import wraps

from sqlalchemy.exc import IntegrityError

from app.errors.database import map_integrity_error


def transactional(method):
    """
    Wrap a service write method in a transaction on `self.db`: commit when
    it returns, roll back when it raises, and turn constraint violations
    into API errors (app/errors/database.py).

    Build the response inside the method: after the commit the session's
    RLS settings are gone, so lazy-loading attributes afterwards can fail.
    """

    @wraps(method)
    def wrapper(self, *args, **kwargs):
        try:
            result = method(self, *args, **kwargs)
            self.db.commit()
            return result

        except IntegrityError as exc:
            self.db.rollback()

            mapped = map_integrity_error(exc)

            if mapped is exc:
                raise

            raise mapped from exc

        except Exception:
            self.db.rollback()
            raise

    return wrapper
