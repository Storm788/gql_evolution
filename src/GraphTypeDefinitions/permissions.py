import strawberry
from strawberry.permission import BasePermission
import json
from pathlib import Path
from uuid import UUID

from .context_utils import ensure_user_in_context


# Estera Lučková - admin ID
ESTERA_ID = UUID("76dac14f-7114-4bb2-882d-0d762eab6f4a")

# Cache pro systemdata user lookup už není potřeba - používáme přímo ID check

def is_admin_user(user) -> bool:
    """Zkontroluje, zda je uživatel admin na základě ID"""
    if not user:
        return False
    
    user_id = user.get("id")
    if user_id is None:
        return False
    
    # Convert to UUID if string
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    
    return user_id == ESTERA_ID


class OnlyJohnNewbie(BasePermission):
    message = "Nemáte oprávnění: pouze administrátor smí provést tuto akci"

    async def has_permission(self, source, info: strawberry.types.Info, **kwargs) -> bool:
        user = ensure_user_in_context(info)
        if not user:
            return False
        return is_admin_user(user)


__all__ = ["OnlyJohnNewbie", "ESTERA_ID", "is_admin_user"]
