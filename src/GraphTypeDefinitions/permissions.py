import strawberry
from strawberry.permission import BasePermission
import json
from pathlib import Path
from uuid import UUID
from typing import List, Set, Optional
import sqlalchemy as sa
from sqlalchemy import select

from .context_utils import ensure_user_in_context


# ==================== ROLE IDs z systemdata.combined.json ====================
# Role type IDs
ADMINISTRATOR_ROLE_ID = UUID("ced46aa4-3217-4fc1-b79d-f6be7d21c6b6")
EDITOR_ROLE_ID = UUID("ed1707aa-0000-4000-8000-000000000001")
VIEWER_ROLE_ID = UUID("ed1707aa-0000-4000-8000-000000000002")
READER_ROLE_ID = UUID("ed1707aa-0000-4000-8000-000000000003")

# Mapování role name -> UUID (standardizované role)
ROLE_NAME_TO_ID = {
    "administrator": ADMINISTRATOR_ROLE_ID,
    "administrátor": ADMINISTRATOR_ROLE_ID,
    "editor": EDITOR_ROLE_ID,
    "viewer": VIEWER_ROLE_ID,
    "čtenář": READER_ROLE_ID,
    "reader": READER_ROLE_ID,
    # další aliasy
    "admin": ADMINISTRATOR_ROLE_ID,
    "vedoucí": ADMINISTRATOR_ROLE_ID, # vedoucí = admin
    "manager": ADMINISTRATOR_ROLE_ID,
    # případně další aliasy podle potřeby
}

# ==================== Helper funkce ====================

async def get_user_roles_from_db(user_id: UUID, info: strawberry.types.Info) -> Set[UUID]:
    print(f"[DEBUG] get_user_roles_from_db called for user_id: {user_id}")
    """
    Načte všechny aktivní role uživatele z databáze (tabulka roles).
    Vrací set UUID roletype_id.
    """
    from uoishelpers.resolvers import getLoadersFromInfo
    
    try:
        loaders = getLoadersFromInfo(info)
        session_maker = loaders.session_maker
        async with session_maker() as session:
            from sqlalchemy import text
            query = text("""
                SELECT DISTINCT roletype_id 
                FROM roles 
                WHERE user_id = :user_id 
                AND valid = true
                AND (startdate IS NULL OR startdate <= NOW())
                AND (enddate IS NULL OR enddate >= NOW())
            """)
            result = await session.execute(query, {"user_id": str(user_id)})
            role_ids = {UUID(row[0]) for row in result.fetchall()}
            if role_ids:
                return role_ids
    except Exception as e:
        import sys
        print(f"Warning: Could not load user roles from DB: {e}", flush=True)

    # Pokud nejsou role v DB, zkus načíst ze systemdata.combined.json
    try:
        import json
        from pathlib import Path
        data_path = Path(__file__).parent.parent.parent / "systemdata.combined.json"
        if data_path.exists():
            with open(data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                roles = data.get('roles', [])
                user_roles = set()
                for role in roles:
                    if role.get('user_id') == str(user_id) and role.get('valid', True):
                        # Kontrola datumu
                        import datetime
                        now = datetime.datetime.now().isoformat()
                        start = role.get('startdate')
                        end = role.get('enddate')
                        if (not start or start <= now) and (not end or end >= now):
                            roletype_id = role.get('roletype_id')
                            if roletype_id:
                                user_roles.add(UUID(roletype_id))
                if user_roles:
                    return user_roles
    except Exception as e:
        import sys
        print(f"Warning: Could not load user roles from systemdata.combined.json: {e}", flush=True)
    return set()


async def user_has_role(user, role_name: str, info: strawberry.types.Info) -> bool:
    """Zkontroluje, zda má uživatel danou roli."""
    import sys
    print(f"[DEBUG] user_has_role called for user: {user}, looking for role: '{role_name}'", flush=True)
    if not user:
        return False
    
    user_id = user.get("id")
    if not user_id:
        return False
        
    if isinstance(user_id, str):
        user_id = UUID(user_id)

    # 1. Zjistí kanonické ID pro požadovaný název role
    role_name_lower = role_name.lower()
    required_role_id = ROLE_NAME_TO_ID.get(role_name_lower)
    
    if not required_role_id:
        print(f"Warning: Unknown role name '{role_name}' used in permission check.", flush=True)
        return False

    # 2. Načte všechny ID rolí, které má uživatel
    user_role_ids = await get_user_roles_from_db(user_id, info)
    print(f"[DEBUG] User {user_id} has role IDs: {user_role_ids}", flush=True)
    print(f"[DEBUG] Checking for required role ID: {required_role_id}", flush=True)

    # 3. Zkontroluje, zda má uživatel požadované ID role
    if required_role_id in user_role_ids:
        print(f"[DEBUG] SUCCESS: User has the required role '{role_name}'.", flush=True)
        return True
    
    print(f"[DEBUG] FAILURE: User does not have the required role '{role_name}'.", flush=True)
    return False


async def user_has_any_role(user, role_names: List[str], info: strawberry.types.Info) -> bool:
    """
    Zkontroluje, zda má uživatel alespoň jednu z daných rolí.
    """
    if not user:
        return False
    
    for role_name in role_names:
        if await user_has_role(user, role_name, info):
            return True
    return False


# ==================== Permission Classes ====================

class RequireRole(BasePermission):
    """
    Permission class pro kontrolu konkrétní role.
    
    Použití:
        @strawberry.field(permission_classes=[RequireRole(roles=["administrátor"])])
        async def admin_only_field(...) -> str:
            ...
    """
    
    def __init__(self, roles: List[str], message: Optional[str] = None):
        self.roles = roles
        self.message = message or f"Nemáte oprávnění: vyžadována role {', '.join(roles)}"
    
    async def has_permission(self, source, info: strawberry.types.Info, **kwargs) -> bool:
        user = ensure_user_in_context(info)
        if not user:
            return False
        
        # Zkontroluj, zda má user některou z požadovaných rolí
        return await user_has_any_role(user, self.roles, info)


class RequireAdmin(BasePermission):
    """Permission class pro admin-only přístup"""
    message = "Nemáte oprávnění: pouze administrátor smí provést tuto akci"
    
    async def has_permission(self, source, info: strawberry.types.Info, **kwargs) -> bool:
        user = ensure_user_in_context(info)
        if not user:
            return False
        
        return await user_has_role(user, "administrátor", info)


class RequireEditor(BasePermission):
    """Permission class pro editor nebo vyšší"""
    message = "Nemáte oprávnění: vyžadována role editor nebo administrátor"
    
    async def has_permission(self, source, info: strawberry.types.Info, **kwargs) -> bool:
        user = ensure_user_in_context(info)
        if not user:
            return False
        
        return await user_has_any_role(user, ["administrátor", "editor"], info)


class RequireViewer(BasePermission):
    """Permission class pro viewer nebo vyšší"""
    message = "Nemáte oprávnění: vyžadována role viewer, editor nebo administrátor"
    
    async def has_permission(self, source, info: strawberry.types.Info, **kwargs) -> bool:
        user = ensure_user_in_context(info)
        if not user:
            return False
        
        return await user_has_any_role(user, ["administrátor", "editor", "viewer", "čtenář"], info)


__all__ = [
    "RequireRole",
    "RequireAdmin",
    "RequireEditor", 
    "RequireViewer",
    "user_has_role",
    "user_has_any_role",
    "get_user_roles_from_db",
    "ADMINISTRATOR_ROLE_ID",
    "EDITOR_ROLE_ID",
    "VIEWER_ROLE_ID",
    "READER_ROLE_ID",
    "ROLE_NAME_TO_ID",
]
