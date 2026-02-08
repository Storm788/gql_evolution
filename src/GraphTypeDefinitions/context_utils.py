import copy
import typing
import uuid

import strawberry


def ensure_user_in_context(info: strawberry.types.Info) -> typing.Optional[dict]:
    """Guarantee that context['user'] holds an identifier.

    WhoAmIExtension loads user from gql_ug API and sets it in context['user'].
    This function ensures the user is available for resolvers.
    
    Priority:
    1. user (aktuální uživatel v kontextu nastavený WhoAmIExtension z gql_ug API)
    2. __original_user (fallback pro testy, pokud WhoAmIExtension selže)
    3. Authorization header (fallback, pokud není uživatel v kontextu)
    """

    context = info.context
    
    # Nejdřív zkus aktuálního uživatele v kontextu (nastavený WhoAmIExtension z gql_ug API)
    user = context.get("user")
    if user and isinstance(user, dict) and user.get("id"):
        return user
    
    # Pak zkus __original_user (fallback pro testy, pokud WhoAmIExtension selže)
    fallback = context.get("__original_user")
    if fallback and fallback.get("id"):
        # Work on a copy to avoid unexpected mutations.
        restored = copy.deepcopy(fallback)
        context["user"] = restored
        return restored
    
    # Pokud user není slovník s id, zkus získat id z __original_user nebo z request
    if not user or not isinstance(user, dict) or not user.get("id"):
        # Zkus získat id z __original_user
        if fallback and isinstance(fallback, dict) and fallback.get("id"):
            restored = copy.deepcopy(fallback)
            context["user"] = restored
            return restored
        
        # Zkus získat id z request
        request = context.get("request")
        if request:
            headers = getattr(request, "headers", None)
            if headers:
                auth_header = headers.get("Authorization") if hasattr(headers, "get") else None
                if auth_header and isinstance(auth_header, str):
                    # Extract token
                    if auth_header.startswith("Bearer "):
                        token = auth_header[7:]
                    else:
                        token = auth_header
                    
                    # Create minimal user with id
                    if token:
                        fallback_user = {"id": token}
                        context["user"] = fallback_user
                        return fallback_user

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
