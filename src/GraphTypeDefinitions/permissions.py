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
    """
    Načte všechny aktivní role uživatele z databáze (tabulka roles) nebo z kontextu.
    Vrací set UUID roletype_id.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    from .context_utils import ensure_user_in_context
    
    # Nejdřív zkus načíst role z kontextu uživatele (z WhoAmIExtension nebo z federovaného UserGQLModel)
    user = ensure_user_in_context(info)
    if user:
        user_roles = user.get("roles")
        if user_roles:
            role_ids = set()
            for role in user_roles:
                if isinstance(role, dict):
                    roletype = role.get("roletype")
                    if roletype:
                        roletype_id = roletype.get("id") if isinstance(roletype, dict) else roletype
                        if roletype_id:
                            try:
                                role_ids.add(UUID(str(roletype_id)))
                            except (ValueError, TypeError):
                                pass
                    roletype_id = role.get("roletype_id")
                    if roletype_id:
                        try:
                            role_ids.add(UUID(str(roletype_id)))
                        except (ValueError, TypeError):
                            pass
            if role_ids:
                return role_ids
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
        logger.warning(f"get_user_roles_from_db: error loading roles from DB: {e}", exc_info=True)

    # Pokud nejsou role v DB, zkus načíst ze systemdata souborů
    try:
        import json
        from pathlib import Path
        # Zkus více souborů v pořadí: rnd (priorita), standard
        for filename in ["systemdata.rnd.json", "systemdata.json"]:
            data_path = Path(__file__).parent.parent.parent / filename
            if data_path.exists():
                logger.debug(f"Loading roles from {filename}")
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    roles = data.get('roles', [])
                    logger.debug(f"Found {len(roles)} roles in {filename}")
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
                        logger.debug(f"Found {len(user_roles)} roles for user {user_id} in {filename}")
                        return user_roles
    except UnicodeDecodeError as e:
        logger.warning(f"Encoding error loading roles from systemdata files: {e}")
    except json.JSONDecodeError as e:
        logger.warning(f"JSON decode error loading roles from systemdata files: {e}")
    except Exception as e:
        logger.debug(f"Error loading roles from systemdata files: {e}", exc_info=True)
    return set()


async def user_has_role(user, role_name: str, info: strawberry.types.Info) -> bool:
    """Zkontroluje, zda má uživatel danou roli."""
    if not user or not user.get("id"):
        return False
    user_id = user.get("id")
    if isinstance(user_id, str):
        user_id = UUID(user_id)
    role_name_lower = role_name.lower()
    required_role_id = ROLE_NAME_TO_ID.get(role_name_lower)
    if not required_role_id:
        return False
    user_roles = user.get("roles")
    if user_roles:
        for role in user_roles:
            roletype_id = None
            if isinstance(role, dict):
                roletype = role.get("roletype")
                if roletype:
                    roletype_id = roletype.get("id") if isinstance(roletype, dict) else roletype
                if not roletype_id:
                    roletype_id = role.get("roletype_id")
            if roletype_id:
                try:
                    if UUID(str(roletype_id)) == required_role_id:
                        return True
                except (ValueError, TypeError):
                    pass
    user_role_ids = await get_user_roles_from_db(user_id, info)
    if required_role_id in user_role_ids:
        return True
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
