import copy
import typing

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


__all__ = ["ensure_user_in_context"]
