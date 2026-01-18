from src.Dataloaders import createLoaders
import copy
import typing
import json
from pathlib import Path

import strawberry

from src.GraphTypeDefinitions.context_utils import ensure_user_in_context


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

    context = _ContextDict()
    # Use createLoaders from src.Dataloaders - it expects a session factory (callable)
    # If we got a factory, use it directly; if we got an instance, we can't use it
    from src.Dataloaders import createLoaders
    if callable(session_or_factory):
        # It's a factory, use it directly
        context["loaders"] = createLoaders(session_or_factory)
    else:
        # It's an instance - this shouldn't happen in normal usage
        # But if it does, we need to create a factory that returns this instance
        # However, this is problematic because we can't reuse the same session
        # For now, raise an error to catch this issue
        raise ValueError("createLoadersContext expects a session factory (callable), not a session instance")
    return context


def _extract_authorization_token(request: typing.Any) -> typing.Optional[str]:
    """Extract Authorization token from headers or cookies."""
    if request is None:
        return None

    headers = getattr(request, "headers", None)
    if headers is None:
        return None

    token = None
    # Try Authorization header first
    if hasattr(headers, "get"):
        token = headers.get("Authorization")
    else:
        try:
            token = headers["Authorization"]
        except Exception:
            token = None

    # If no header, try authorization cookie (JWT token from frontend)
    if not token:
        cookies = getattr(request, "cookies", None)
        if cookies:
            if hasattr(cookies, "get"):
                token = cookies.get("authorization")
            else:
                try:
                    token = cookies.get("authorization")
                except Exception:
                    pass

    if not token:
        return None

    # Handle Bearer token format
    parts = token.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return token


def _extract_demo_user_id(request: typing.Any) -> typing.Optional[str]:
    """Extract x-demo-user-id from request headers or cookies.
    Also tries to extract from authorization cookie (JWT token from frontend).
    """
    if request is None:
        return None

    headers = getattr(request, "headers", None)
    if headers is None:
        return None

    # Try x-demo-user-id header
    demo_user_id = None
    if hasattr(headers, "get"):
        demo_user_id = headers.get("x-demo-user-id") or headers.get("X-Demo-User-Id")
    else:
        try:
            demo_user_id = headers.get("x-demo-user-id") or headers.get("X-Demo-User-Id")
        except Exception:
            pass

    if demo_user_id:
        return demo_user_id

    # Try cookies (demo-user-id or authorization)
    cookies = getattr(request, "cookies", None)
    if cookies:
        if hasattr(cookies, "get"):
            # Try demo-user-id cookie first
            demo_user_id = cookies.get("demo-user-id")
            if demo_user_id:
                return demo_user_id
            
            # Try authorization cookie (JWT token from frontend)
            auth_token = cookies.get("authorization")
            if auth_token:
                # Return JWT token - WhoAmIExtension nebo jiná logika ho zpracuje
                return auth_token
        else:
            try:
                demo_user_id = cookies.get("demo-user-id")
                if demo_user_id:
                    return demo_user_id
                auth_token = cookies.get("authorization")
                if auth_token:
                    return auth_token
            except Exception:
                pass

    return None


def _load_user_from_systemdata(user_id: str) -> typing.Optional[typing.Dict[str, typing.Any]]:
    """Load user data from systemdata.json or systemdata.combined.json by user ID."""
    if not user_id:
        return None

    # Try systemdata.combined.json first, then systemdata.json
    for filename in ["systemdata.combined.json", "systemdata.json"]:
        try:
            data_path = Path(__file__).parent.parent.parent / filename
            if data_path.exists():
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    users = data.get('users', [])
                    for user in users:
                        if str(user.get('id')) == str(user_id):
                            return {
                                'id': str(user.get('id')),
                                'email': user.get('email', ''),
                                'name': user.get('name', ''),
                                'surname': user.get('surname', ''),
                            }
        except Exception:
            continue

    return None


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


__all__ = ["createLoadersContext", "getUserFromInfo", "_extract_demo_user_id", "_load_user_from_systemdata"]
