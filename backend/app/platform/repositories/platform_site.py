from typing import Any

from sqlalchemy import Row, text

from app.db.repository import Repository


# The columns an update may set (the rest are the row's own).
_COLUMNS = (
    "headline",
    "hero_text",
    "about_title",
    "about",
    "logo_key",
    "icon_key",
    "hero_photo_key",
    "hero_photo_alt",
    "about_photo_key",
    "about_photo_alt",
    "primary_color",
    "secondary_color",
    "accent_color",
)


class PlatformSiteRepository(Repository):
    """
    The platform's landing page (docs/platform-site.md): its one row and its
    feature cards. Anyone reads them; RLS lets only the platform's admins
    write.
    """

    def get(self) -> Row | None:
        return self.db.execute(
            text(f"SELECT {', '.join(_COLUMNS)} FROM public.platform_site WHERE id")
        ).first()

    def update(
        self,
        *,
        values: dict[str, Any],
    ) -> None:
        """Change some of the row (columns from _COLUMNS only)."""
        if not values:
            return

        unknown = set(values) - set(_COLUMNS)

        if unknown:
            raise ValueError(f"Not platform site columns: {sorted(unknown)}")

        self.db.execute(
            text(f"UPDATE public.platform_site SET {', '.join(f'{c} = :{c}' for c in values)} WHERE id"),
            values,
        )

    def list_features(self) -> list[Row]:
        return self.db.execute(
            text("SELECT icon, title, description FROM public.platform_features ORDER BY position")
        ).all()

    def replace_features(
        self,
        *,
        features: list[tuple[str, str, str]],
    ) -> None:
        """The whole list, in this order (icon, title, description)."""
        self.db.execute(text("DELETE FROM public.platform_features"))

        for position, (icon, title, description) in enumerate(features):
            self.db.execute(
                text(
                    "INSERT INTO public.platform_features (position, icon, title, description) "
                    "VALUES (:position, :icon, :title, :description)"
                ),
                {"position": position, "icon": icon, "title": title, "description": description},
            )
