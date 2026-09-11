from inspect import signature
from typing import Callable, TypeVar

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.repository import (
    Pagination,
    Repository,
)
from app.dependencies.pg import get_pagination


ServiceT = TypeVar("ServiceT")


def get_service(
    service: type[ServiceT],
    *,
    db_dependency: Callable,
):
    def dependency(
        db: Session = Depends(db_dependency),
        pagination: Pagination = Depends(
            get_pagination
        ),
    ) -> ServiceT:
        kwargs = {
            "db": db,
        }

        constructor = signature(
            service.__init__
        )

        for name, parameter in constructor.parameters.items():
            if name == "self":
                continue

            dependency_type = parameter.annotation

            if (
                isinstance(dependency_type, type)
                and issubclass(
                    dependency_type,
                    Repository,
                )
            ):
                kwargs[name] = dependency_type(
                    db=db,
                    pagination=pagination,
                )

        return service(**kwargs)

    return dependency