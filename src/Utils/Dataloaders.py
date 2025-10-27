from Dataloaders import LoaderMap
from uoishelpers.schema.ProfilingExtension import Counter as ProfilingCounter
import copy
import typing

import strawberry

from GraphTypeDefinitions.context_utils import ensure_user_in_context


class _ContextDict(dict):
    """Dictionary variant that keeps the original user payload for later reuse.
    WhoAmIExtension overwrites the `user` entry when federation is not reachable;
    keeping a copy lets resolvers restore the id so helper utilities continue to work.
    """

    def __setitem__(self, key, value):
        if key == "user" and value and "__original_user" not in self:
            super().__setitem__("__original_user", copy.deepcopy(value))
        super().__setitem__(key, value)


def createLoadersContext(session_or_factory):
    """Accepts either an async session factory or a session instance.

    Returns a context dictionary compatible with the expectations of legacy tests
    while preserving the caller provided user information for scenarios where
    WhoAmIExtension cannot reach upstream services during unit tests.
    """

    session = session_or_factory() if callable(session_or_factory) else session_or_factory
    context = _ContextDict()
    context["loaders"] = LoaderMap(session)
    context["ProfilingExtension.counter"] = ProfilingCounter()
    return context


def _extract_authorization_token(request: typing.Any) -> typing.Optional[str]:
    if request is None:
        return None

    headers = getattr(request, "headers", None)
    if headers is None:
        return None

    token = None
    if hasattr(headers, "get"):
        token = headers.get("Authorization")
    else:
        try:
            token = headers["Authorization"]
        except Exception:
            token = None

    if not token:
        return None

    parts = token.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return token


def getUserFromInfo(info: strawberry.types.Info) -> typing.Dict[str, typing.Any]:
    """Return user information from GraphQL execution context.

    Falls back to the Authorization header carried by request when WhoAmIExtension
    is not available (typical for in-memory unit tests).
    """

    context = info.context
    user = ensure_user_in_context(info)
    if user:
        return user

    request = context.get("request")
    token = _extract_authorization_token(request)
    assert token is not None, "User is wanted but not present in context or Authorization header"

    fallback_user = {
        "id": token,
        "token": token,
    }
    context["user"] = fallback_user
    return fallback_user


__all__ = ["createLoadersContext", "getUserFromInfo"]
