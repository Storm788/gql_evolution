import strawberry
from strawberry.permission import BasePermission

from .context_utils import ensure_user_in_context


ALLOWED_USER_ID = "2d9dc5ca-a4a2-11ed-b9df-0242ac120003"


class OnlyJohnNewbie(BasePermission):
    message = "Not authorized"

    async def has_permission(self, source, info: strawberry.types.Info, **kwargs) -> bool:
        user = ensure_user_in_context(info)
        if not user:
            return False
        return str(user.get("id")) == ALLOWED_USER_ID


__all__ = ["OnlyJohnNewbie", "ALLOWED_USER_ID"]

