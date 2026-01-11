import copy
import typing
import uuid

import strawberry


def ensure_user_in_context(info: strawberry.types.Info) -> typing.Optional[dict]:
    """Guarantee that context['user'] holds an identifier.

    WhoAmIExtension replaces the user payload when upstream UG is unreachable
    (common in unit tests). We keep a copy stored by utils.createLoadersContext
    under '__original_user' and restore it on demand so resolvers relying on the
    helper Insert/Update/Delete utilities continue to function.
    """

    context = info.context
    user = context.get("user") or {}
    if user.get("id"):
        return user

    fallback = context.get("__original_user")
    if fallback and fallback.get("id"):
        # Work on a copy to avoid unexpected mutations.
        restored = copy.deepcopy(fallback)
        context["user"] = restored
        return restored

    return user if user else None


def get_user_id(info: strawberry.types.Info) -> typing.Optional[uuid.UUID]:
    """
    Bezpečně získá user_id z kontextu.
    """
    user = ensure_user_in_context(info)
    if user is None:
        return None
        
    user_id_str = user.get("id")
    if user_id_str:
        try:
            return uuid.UUID(user_id_str)
        except (ValueError, TypeError):
            return None
    return None


__all__ = ["ensure_user_in_context", "get_user_id"]
