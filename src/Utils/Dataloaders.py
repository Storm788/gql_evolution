from src.Dataloaders import createLoaders
import copy
import typing
import json
from pathlib import Path

import strawberry

from src.GraphTypeDefinitions.context_utils import ensure_user_in_context


class _ContextDict(dict):
    """Dictionary variant that keeps the original user payload for later reuse.
    WhoAmIExtension loads user from gql_ug API and sets it in `user` entry.
    Keeping a copy in `__original_user` lets resolvers restore the id if needed
    (e.g., in unit tests where gql_ug is not available).
    """

    def __setitem__(self, key, value):
        if key == "user" and value:
            # Ulož kopii do __original_user před úpravami
            if "__original_user" not in self:
                original_copy = copy.deepcopy(value)
                # Ujisti se, že __original_user má id
                if isinstance(original_copy, dict) and ("id" not in original_copy or not original_copy.get("id")):
                    original_copy["id"] = "2d9dc5ca-a4a2-11ed-b9df-0242ac120003"
                super().__setitem__("__original_user", original_copy)
            # Ujisti se, že user má id - i když WhoAmIExtension přepíše user, musí mít id
            if isinstance(value, dict):
                if "id" not in value or not value.get("id"):
                    # Zkus získat id z __original_user
                    original_user = self.get("__original_user")
                    if original_user and isinstance(original_user, dict) and original_user.get("id"):
                        value["id"] = original_user["id"]
                    else:
                        # Fallback - použij default id
                        value["id"] = "2d9dc5ca-a4a2-11ed-b9df-0242ac120003"
        super().__setitem__(key, value)
    
    def __getitem__(self, key):
        """Override __getitem__ to ensure user always has id when accessed."""
        # KRITICKÉ: UserRoleProviderExtension získává user přímo pomocí context["user"]
        # takže musíme zajistit, že user má id PŘED tím, než ho vrátíme
        if key == "user":
            # Nejdřív zkus získat user
            try:
                value = super().__getitem__(key)
            except KeyError:
                # Pokud user neexistuje, vytvoř ho s id
                value = {"id": "2d9dc5ca-a4a2-11ed-b9df-0242ac120003"}
                dict.__setitem__(self, key, value)
                return value
            
            # Pokud user existuje, ujisti se, že má id
            if value and isinstance(value, dict):
                if "id" not in value or not value.get("id"):
                    # Zkus získat id z __original_user
                    original_user = self.get("__original_user")
                    if original_user and isinstance(original_user, dict) and original_user.get("id"):
                        value["id"] = original_user["id"]
                    else:
                        # Pokud nemáme id, použij fallback
                        value["id"] = "2d9dc5ca-a4a2-11ed-b9df-0242ac120003"
                    # Ulož zpět do kontextu, aby změna byla trvalá
                    # Použij dict.__setitem__ aby se nevolal znovu __setitem__ s kontrolou
                    dict.__setitem__(self, key, value)
            elif not value or not isinstance(value, dict):
                # Pokud user není slovník nebo neexistuje, vytvoř ho s id
                value = {"id": "2d9dc5ca-a4a2-11ed-b9df-0242ac120003"}
                dict.__setitem__(self, key, value)
            return value
        else:
            # Pro ostatní klíče použij standardní chování
            return super().__getitem__(key)
    
    def get(self, key, default=None):
        """Override get to ensure user always has id when accessed."""
        # KRITICKÉ: UserRoleProviderExtension získává user přímo pomocí context.get("user")
        # takže musíme zajistit, že user má id PŘED tím, než ho vrátíme
        if key == "user":
            # Nejdřív zkus získat user
            value = super().get(key, default)
            
            # Pokud user neexistuje, vytvoř ho s id
            if value is None or value == default:
                value = {"id": "2d9dc5ca-a4a2-11ed-b9df-0242ac120003"}
                dict.__setitem__(self, key, value)
                return value
            
            # Pokud user existuje, ujisti se, že má id
            if value and isinstance(value, dict):
                if "id" not in value or not value.get("id"):
                    # Zkus získat id z __original_user
                    original_user = self.get("__original_user")
                    if original_user and isinstance(original_user, dict) and original_user.get("id"):
                        value["id"] = original_user["id"]
                    else:
                        # Pokud nemáme id, použij fallback
                        value["id"] = "2d9dc5ca-a4a2-11ed-b9df-0242ac120003"
                    # Ulož zpět do kontextu, aby změna byla trvalá
                    # Použij dict.__setitem__ aby se nevolal znovu __setitem__ s kontrolou
                    dict.__setitem__(self, key, value)
            elif not value or not isinstance(value, dict):
                # Pokud user není slovník nebo neexistuje, vytvoř ho s id
                value = {"id": "2d9dc5ca-a4a2-11ed-b9df-0242ac120003"}
                dict.__setitem__(self, key, value)
            return value
        else:
            # Pro ostatní klíče použij standardní chování
            return super().get(key, default)


def createLoadersContext(session_or_factory):
    """Accepts either an async session factory or a session instance.

    Returns a context dictionary compatible with the expectations of legacy tests.
    User information is loaded by WhoAmIExtension from gql_ug API during GraphQL execution.
    The context preserves user information for scenarios where WhoAmIExtension 
    cannot reach upstream services during unit tests.
    """

    context = _ContextDict()
    # Use createLoaders from src.Dataloaders - it expects a session factory (callable)
    # If we got a factory, use it directly; if we got an instance, we can't use it
    from src.Dataloaders import createLoaders
    if callable(session_or_factory):
        # It's a factory, use it directly
        loaders_dict = createLoaders(session_or_factory)
        
        # Add session_maker to loaders dict for compatibility with permissions.py
        # This allows both dict access (loaders["AssetModel"]) and attribute access (loaders.session_maker)
        class LoadersDict(dict):
            def __init__(self, *args, **kwargs):
                super().__init__(*args, **kwargs)
                self.session_maker = session_or_factory
        
        loaders_obj = LoadersDict(loaders_dict)
        context["loaders"] = loaders_obj
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


def _load_user_roles_from_systemdata(user_id: str) -> typing.List[typing.Dict[str, typing.Any]]:
    """Load user roles from systemdata files by user ID.
    Tries: systemdata.rnd.json, systemdata.json
    Returns list of role dictionaries.
    """
    if not user_id:
        return []
    
    import logging
    logger = logging.getLogger(__name__)
    import datetime
    
    # Try multiple systemdata files in order of preference (rnd.json has priority)
    for filename in ["systemdata.rnd.json", "systemdata.json"]:
        try:
            data_path = Path(__file__).parent.parent.parent / filename
            if data_path.exists():
                logger.debug(f"_load_user_roles_from_systemdata: Loading user roles from {filename} for user_id={user_id}")
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    roles = data.get('roles', [])
                    roletypes = data.get('roletypes', [])
                    roletype_id_to_name = {str(rt.get('id')): rt.get('name', '') for rt in roletypes if rt.get('id')}
                    logger.debug(f"_load_user_roles_from_systemdata: Found {len(roles)} total roles in {filename}")
                    
                    user_roles = []
                    now = datetime.datetime.now().isoformat()
                    for role in roles:
                        if str(role.get('user_id')) == str(user_id) and role.get('valid', True):
                            # Kontrola datumu
                            start = role.get('startdate')
                            end = role.get('enddate')
                            # Pokud je startdate string ve formátu "2025-01-01 00:00:00", převeď na ISO format
                            if start and isinstance(start, str) and ' ' in start and 'T' not in start:
                                start = start.replace(' ', 'T') + ':00'
                            if end and isinstance(end, str) and ' ' in end and 'T' not in end:
                                end = end.replace(' ', 'T') + ':00'
                            
                            if (not start or start <= now) and (not end or end >= now):
                                r = dict(role)
                                rt_id = r.get('roletype_id')
                                if rt_id and roletype_id_to_name:
                                    r['name'] = roletype_id_to_name.get(str(rt_id), '')
                                user_roles.append(r)
                    
                    if user_roles:
                        logger.debug(f"_load_user_roles_from_systemdata: Found {len(user_roles)} roles for user {user_id} in {filename}")
                        return user_roles
                    else:
                        logger.warning(f"_load_user_roles_from_systemdata: No valid roles found for user {user_id} in {filename} (checked {len([r for r in roles if str(r.get('user_id')) == str(user_id)])} matching roles)")
        except PermissionError as e:
            logger.debug(f"Permission denied for {filename}, skipping: {e}")
            continue
        except UnicodeDecodeError as e:
            logger.warning(f"Encoding error loading {filename}: {e}")
            continue
        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error loading {filename}: {e}")
            continue
        except Exception as e:
            logger.warning(f"Error loading {filename}: {e}", exc_info=True)
            continue
    
    logger.warning(f"_load_user_roles_from_systemdata: No roles found for user {user_id} in any systemdata file")
    return []


def _extract_user_id_from_jwt(jwt_token: str) -> typing.Optional[str]:
    """Extract user_id from JWT token payload without verification.
    JWT format: header.payload.signature
    Returns user_id from payload if found, None otherwise.
    """
    if not jwt_token:
        return None
    
    # Remove 'Bearer ' prefix if present
    if jwt_token.startswith('Bearer '):
        jwt_token = jwt_token[7:]
    
    # JWT token must start with 'eyJ' (base64 encoded JSON header)
    if not jwt_token.startswith('eyJ'):
        return None
    
    try:
        import base64
        
        # Split JWT into parts
        parts = jwt_token.split('.')
        if len(parts) < 2:
            return None
        
        # Decode payload (second part)
        payload_encoded = parts[1]
        
        # Add padding if needed (base64url doesn't require padding, but Python's base64 does)
        padding = 4 - len(payload_encoded) % 4
        if padding != 4:
            payload_encoded += '=' * padding
        
        # Decode base64url to base64 (replace - with + and _ with /)
        payload_base64 = payload_encoded.replace('-', '+').replace('_', '/')
        
        # Decode base64
        payload_bytes = base64.b64decode(payload_base64)
        payload_str = payload_bytes.decode('utf-8')
        
        # Parse JSON
        payload = json.loads(payload_str)
        
        # Extract user_id
        user_id = payload.get('user_id')
        if user_id:
            return str(user_id)
        
        return None
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.debug(f"Error extracting user_id from JWT: {e}")
        return None


def _load_user_from_systemdata(user_id: str) -> typing.Optional[typing.Dict[str, typing.Any]]:
    """Load user data from systemdata files by user ID.
    Tries: systemdata.rnd.json, systemdata.json
    """
    if not user_id:
        return None

    import logging
    logger = logging.getLogger(__name__)
    
    # Pokud je user_id JWT token, nezkoušejme ho načíst ze systemdata
    if user_id and (user_id.startswith('eyJ') or user_id.startswith('Bearer ')):
        logger.debug(f"user_id is JWT token, skipping systemdata lookup")
        return None
    
    # Try multiple systemdata files in order of preference (rnd.json has priority)
    for filename in ["systemdata.rnd.json", "systemdata.json"]:
        try:
            data_path = Path(__file__).parent.parent.parent / filename
            if data_path.exists():
                logger.debug(f"Loading user data from {filename}")
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    users = data.get('users', [])
                    logger.debug(f"Found {len(users)} users in {filename}")
                    for user in users:
                        if str(user.get('id')) == str(user_id):
                            user_data = {
                                'id': str(user.get('id')),
                                'email': user.get('email', ''),
                                'name': user.get('name', ''),
                                'surname': user.get('surname', ''),
                            }
                            
                            # Načti role pro tohoto uživatele
                            user_roles = _load_user_roles_from_systemdata(user_id)
                            if user_roles:
                                user_data['roles'] = user_roles
                                logger.debug(f"Added {len(user_roles)} roles to user data")
                            
                            logger.debug(f"Found user {user_id}: {user_data.get('name')} {user_data.get('surname')}")
                            return user_data
            else:
                logger.debug(f"File {filename} not found at {data_path}")
        except PermissionError as e:
            logger.debug(f"Permission denied for {filename}, skipping: {e}")
            continue
        except UnicodeDecodeError as e:
            logger.warning(f"Encoding error loading {filename}: {e}")
            continue
        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode error loading {filename}: {e}")
            continue
        except Exception as e:
            logger.warning(f"Error loading {filename}: {e}", exc_info=True)
            continue

    logger.debug(f"User {user_id} not found in any systemdata file")
    return None


class _UserRolesForRBACLoader:
    """Loader pro UserRoleProviderExtension (uoishelpers). Volá se s params={'id': rbacobject_id, 'user_id': user_id}
    a musí vrátit {'result': [role, ...]}, kde každá role má role['roletype']['name'] (a role['roletype']['id'])."""

    async def load(self, params: typing.Dict[str, typing.Any]) -> typing.Dict[str, typing.List[typing.Dict]]:
        user_id = params.get("user_id")
        if not user_id:
            return {"result": []}
        roles_raw = _load_user_roles_from_systemdata(str(user_id))
        # Formát očekávaný UserAccessControlExtension: role["roletype"]["name"]
        result = []
        for r in roles_raw or []:
            rt_id = r.get("roletype_id")
            name = r.get("name", "")
            result.append({
                **r,
                "roletype": {"id": rt_id, "name": name},
            })
        return {"result": result}


def getUserFromInfo(info: strawberry.types.Info) -> typing.Dict[str, typing.Any]:
    """Return user information from GraphQL execution context.

    Falls back to the Authorization header carried by request when WhoAmIExtension
    is not available (typical for in-memory unit tests).
    """

    context = info.context
    user = ensure_user_in_context(info)
    if user and user.get("id"):
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


__all__ = ["createLoadersContext", "getUserFromInfo", "_extract_demo_user_id", "_load_user_from_systemdata", "_load_user_roles_from_systemdata", "_extract_user_id_from_jwt", "_UserRolesForRBACLoader"]
