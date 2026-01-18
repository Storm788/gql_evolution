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
    logger.debug(f"get_user_roles_from_db: user from context: {user}")
    
    if user:
        # Zkontroluj, zda má uživatel role v kontextu (z WhoAmIExtension nebo z GraphQL query)
        user_roles = user.get("roles")
        logger.debug(f"get_user_roles_from_db: user_roles from context: {user_roles}")
        
        if user_roles:
            role_ids = set()
            for role in user_roles:
                # Role může být dict s "roletype" nebo přímo roletype_id
                if isinstance(role, dict):
                    roletype = role.get("roletype")
                    logger.debug(f"get_user_roles_from_db: processing role={role}, roletype={roletype}")
                    if roletype:
                        roletype_id = roletype.get("id") if isinstance(roletype, dict) else roletype
                        if roletype_id:
                            try:
                                role_ids.add(UUID(str(roletype_id)))
                                logger.debug(f"get_user_roles_from_db: added roletype_id={roletype_id} from roletype")
                            except (ValueError, TypeError) as e:
                                logger.debug(f"get_user_roles_from_db: error converting roletype_id to UUID: {e}")
                    # Alternativně může být roletype_id přímo v role
                    roletype_id = role.get("roletype_id")
                    if roletype_id:
                        try:
                            role_ids.add(UUID(str(roletype_id)))
                            logger.debug(f"get_user_roles_from_db: added roletype_id={roletype_id} from role")
                        except (ValueError, TypeError) as e:
                            logger.debug(f"get_user_roles_from_db: error converting roletype_id to UUID: {e}")
            if role_ids:
                logger.info(f"get_user_roles_from_db: found {len(role_ids)} roles in context: {role_ids}")
                return role_ids
    
    # Pokud nejsou role v kontextu, zkus načíst z databáze
    logger.debug(f"get_user_roles_from_db: roles not in context, loading from DB for user_id={user_id}")
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
                logger.info(f"get_user_roles_from_db: found {len(role_ids)} roles in DB: {role_ids}")
                return role_ids
            else:
                logger.debug(f"get_user_roles_from_db: no roles found in DB for user_id={user_id}")
    except Exception as e:
        logger.warning(f"get_user_roles_from_db: error loading roles from DB: {e}", exc_info=True)

    # Pokud nejsou role v DB, zkus načíst ze systemdata.combined.json
    try:
        import json
        from pathlib import Path
        data_path = Path(__file__).parent.parent.parent / "systemdata.json"
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
        pass # Or log properly
    return set()


async def user_has_role(user, role_name: str, info: strawberry.types.Info) -> bool:
    """Zkontroluje, zda má uživatel danou roli."""
    import logging
    logger = logging.getLogger(__name__)
    
    if not user:
        logger.debug(f"user_has_role: user is None")
        return False
    
    user_id = user.get("id")
    if not user_id:
        logger.debug(f"user_has_role: user_id is None, user={user}")
        return False
        
    if isinstance(user_id, str):
        user_id = UUID(user_id)

    # 1. Zjistí kanonické ID pro požadovaný název role
    role_name_lower = role_name.lower()
    required_role_id = ROLE_NAME_TO_ID.get(role_name_lower)
    
    logger.debug(f"user_has_role: checking role '{role_name}' (lower: '{role_name_lower}') -> required_role_id={required_role_id}")
    
    if not required_role_id:
        logger.debug(f"user_has_role: role name '{role_name}' not found in ROLE_NAME_TO_ID")
        return False

    # 2. Nejdřív zkus načíst role z kontextu uživatele (z WhoAmIExtension nebo z GraphQL query)
    user_roles = user.get("roles")
    logger.debug(f"user_has_role: user roles from context: {user_roles}")
    
    if user_roles:
        for role in user_roles:
            # Role může být dict s "roletype" nebo přímo roletype_id
            roletype_id = None
            if isinstance(role, dict):
                roletype = role.get("roletype")
                logger.debug(f"user_has_role: checking role={role}, roletype={roletype}")
                if roletype:
                    roletype_id = roletype.get("id") if isinstance(roletype, dict) else roletype
                # Alternativně může být roletype_id přímo v role
                if not roletype_id:
                    roletype_id = role.get("roletype_id")
            
            if roletype_id:
                try:
                    roletype_uuid = UUID(str(roletype_id))
                    logger.debug(f"user_has_role: comparing roletype_uuid={roletype_uuid} with required_role_id={required_role_id}")
                    if roletype_uuid == required_role_id:
                        logger.info(f"user_has_role: MATCH FOUND! User {user_id} has role '{role_name}' (roletype_id={roletype_uuid})")
                        return True
                except (ValueError, TypeError) as e:
                    logger.debug(f"user_has_role: error converting roletype_id to UUID: {e}")

    # 3. Pokud nejsou role v kontextu, načti z databáze
    logger.debug(f"user_has_role: roles not found in context, loading from DB for user_id={user_id}")
    user_role_ids = await get_user_roles_from_db(user_id, info)
    logger.debug(f"user_has_role: user_role_ids from DB: {user_role_ids}")

    # 4. Zkontroluje, zda má uživatel požadované ID role
    if required_role_id in user_role_ids:
        logger.info(f"user_has_role: MATCH FOUND in DB! User {user_id} has role '{role_name}' (roletype_id={required_role_id})")
        return True
    
    logger.warning(f"user_has_role: NO MATCH! User {user_id} does NOT have role '{role_name}' (required_role_id={required_role_id}, user_role_ids={user_role_ids})")
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
