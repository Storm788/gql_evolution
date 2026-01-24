import sys
import importlib
import os
from pathlib import Path
import pytest
from unittest.mock import patch, AsyncMock


_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"

if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Ensure modules imported with or without the `src.` prefix resolve to the same instance
graph_module = importlib.import_module("src.GraphTypeDefinitions")
sys.modules.setdefault("GraphTypeDefinitions", graph_module)

db_module = importlib.import_module("src.DBDefinitions")
sys.modules.setdefault("DBDefinitions", db_module)

# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)

# Nastav GQLUG_ENDPOINT_URL pro testy
os.environ.setdefault("GQLUG_ENDPOINT_URL", "http://localhost:8000/gql")

# Mockuj WhoAmIExtension.ug_query globálně - toto je klíčové pro testy
# UserRoleProviderExtension používá WhoAmIExtension.ug_query a očekává, že gql_response není None
try:
    from uoishelpers.schema.WhoAmIExtension import WhoAmIExtension
    if not hasattr(WhoAmIExtension, '_ug_query_patched_in_conftest'):
        original_whoami_ug_query = WhoAmIExtension.ug_query
        
        async def patched_whoami_ug_query(self, query, variables):
            # Vrať správný formát - UserRoleProviderExtension očekává, že gql_response není None
            # Musíme vrátit dict s 'data' klíčem
            result = {"data": {"result": []}}
            return result
        
        # Nastav mock přímo na třídu i instanci
        WhoAmIExtension.ug_query = patched_whoami_ug_query
        WhoAmIExtension._ug_query_patched_in_conftest = True
        WhoAmIExtension._original_ug_query = original_whoami_ug_query
except Exception as e:
    import logging
    logging.warning(f"Failed to monkey patch WhoAmIExtension.ug_query in conftest.py: {e}")

# Mockuj WhoAmIExtension.on_request_start a on_operation_start, aby nepřepisovaly user
try:
    from uoishelpers.schema.WhoAmIExtension import WhoAmIExtension
    if not hasattr(WhoAmIExtension, '_patched_for_tests'):
        original_on_request_start = getattr(WhoAmIExtension, 'on_request_start', None)
        
        async def patched_on_request_start(self, request_context):
            # Nevolaj původní metodu, jen zajisti, že user má id
            context = request_context.context
            if "user" in context:
                current_user = context["user"]
                if current_user and isinstance(current_user, dict):
                    if "id" not in current_user or not current_user.get("id"):
                        current_user["id"] = "2d9dc5ca-a4a2-11ed-b9df-0242ac120003"
            return
        
        if original_on_request_start:
            WhoAmIExtension.on_request_start = patched_on_request_start
        
        original_on_operation_start = getattr(WhoAmIExtension, 'on_operation_start', None)
        if original_on_operation_start:
            async def patched_on_operation_start(self, request_context):
                context = request_context.context
                user_obj = context.get("user")
                if user_obj and isinstance(user_obj, dict):
                    if "id" not in user_obj or not user_obj.get("id"):
                        user_obj["id"] = "2d9dc5ca-a4a2-11ed-b9df-0242ac120003"
                        context["user"] = user_obj
                elif not user_obj or not isinstance(user_obj, dict):
                    context["user"] = {"id": "2d9dc5ca-a4a2-11ed-b9df-0242ac120003"}
                return
            
            WhoAmIExtension.on_operation_start = patched_on_operation_start
        
        WhoAmIExtension._patched_for_tests = True
except Exception as e:
    import logging
    logging.warning(f"Failed to monkey patch WhoAmIExtension in conftest.py: {e}")

# Mockuj uoishelpers.dataloaders.getUserFromInfo
try:
    from uoishelpers import dataloaders as uois_dataloaders
    if not hasattr(uois_dataloaders, '_getUserFromInfo_patched_for_tests'):
        original_getUserFromInfo = getattr(uois_dataloaders, 'getUserFromInfo', None)
        
        def patched_getUserFromInfo(info):
            """Mock getUserFromInfo, aby vždy vrátil user s id."""
            context = info.context
            user = context.get("user")
            if user and isinstance(user, dict):
                if "id" not in user or not user.get("id"):
                    user["id"] = "2d9dc5ca-a4a2-11ed-b9df-0242ac120003"
                    context["user"] = user
                return user
            elif not user or not isinstance(user, dict):
                user = {"id": "2d9dc5ca-a4a2-11ed-b9df-0242ac120003"}
                context["user"] = user
                return user
            return user
        
        if original_getUserFromInfo:
            uois_dataloaders.getUserFromInfo = patched_getUserFromInfo
            uois_dataloaders._getUserFromInfo_patched_for_tests = True
except Exception as e:
    import logging
    logging.warning(f"Failed to monkey patch uoishelpers.dataloaders.getUserFromInfo in conftest.py: {e}")

# Mockuj UserRoleProviderExtension.resolve_async - úplně obejdi middleware v testech
# V testech nepotřebujeme skutečné role, takže můžeme přímo přeskočit UserRoleProviderExtension
try:
    from uoishelpers.gqlpermissions.UserRoleProviderExtension import UserRoleProviderExtension
    if not hasattr(UserRoleProviderExtension, '_patched_for_tests'):
        original_resolve_async = UserRoleProviderExtension.resolve_async
        
        async def patched_resolve_async(self, source, info, *args, **kwargs):
            # Zajisti, že user má id
            context = info.context
            user_obj = context.get("user")
            
            if user_obj and isinstance(user_obj, dict):
                if "id" not in user_obj or not user_obj.get("id"):
                    user_obj["id"] = "2d9dc5ca-a4a2-11ed-b9df-0242ac120003"
                    context["user"] = user_obj
            elif not user_obj or not isinstance(user_obj, dict):
                context["user"] = {"id": "2d9dc5ca-a4a2-11ed-b9df-0242ac120003"}
            
            # Zkus najít next_ v args nebo kwargs
            # Pro mutation může být next_ volán jako next_(source, info, rbacobject_id=..., *args, **kwargs)
            next_func = None
            if len(args) > 0 and callable(args[0]):
                next_func = args[0]
            elif 'next_' in kwargs:
                next_func = kwargs['next_']
            elif 'next' in kwargs:
                next_func = kwargs['next']
            
            # V testech nepotřebujeme skutečné role - přímo přeskoč middleware a zavolej next()
            if next_func:
                # Zavolej next() přímo, což přeskočí UserRoleProviderExtension
                # Předáme všechny parametry včetně rbacobject_id a dalších kwargs
                if len(args) > 0 and args[0] is next_func:
                    # Pokud je next_ první v args, předáme zbytek args
                    return await next_func(source, info, *args[1:], **kwargs)
                else:
                    # Jinak předáme všechny parametry (args i kwargs)
                    return await next_func(source, info, *args, **kwargs)
            
            # Pokud nemáme next(), zkus zavolat původní metodu s mockovaným ug_query
            # Ale nejdřív zajistíme, že ug_query vrací správnou odpověď
            from uoishelpers.schema.WhoAmIExtension import WhoAmIExtension
            
            # Ujisti se, že ug_query je mockovaný
            if not hasattr(WhoAmIExtension, '_ug_query_patched_in_conftest'):
                async def mock_ug_query_func(self_or_cls, query, variables):
                    return {"data": {"result": []}}
                WhoAmIExtension.ug_query = mock_ug_query_func
                WhoAmIExtension._ug_query_patched_in_conftest = True
            
            try:
                result = await original_resolve_async(self, source, info, *args, **kwargs)
                return result
            except (KeyError, AssertionError) as e:
                error_str = str(e)
                if "query for user roles was not responded properly" in error_str:
                    # Pokud stále selže, zkus najít next() a zavolat ho
                    # Možná je next_ v kwargs, ale nebyl rozpoznán
                    # Zkusíme najít callable v kwargs nebo args
                    for key, value in kwargs.items():
                        if callable(value):
                            try:
                                # Zavolej next_ s původními parametry
                                return await value(source, info, *args, **kwargs)
                            except:
                                pass
                    # Pokud nic nefunguje, vrať None nebo prázdný výsledek
                    return None
                raise
        
        UserRoleProviderExtension.resolve_async = patched_resolve_async
        UserRoleProviderExtension._patched_for_tests = True
except Exception as e:
    import logging
    logging.warning(f"Failed to monkey patch UserRoleProviderExtension.resolve_async in conftest.py: {e}")

# Mockuj také RbacInsertProviderExtension
try:
    from uoishelpers.gqlpermissions.RbacInsertProviderExtension import RbacInsertProviderExtension
    if not hasattr(RbacInsertProviderExtension, '_patched_for_tests'):
        original_rbac_resolve_async = RbacInsertProviderExtension.resolve_async
        
        async def patched_rbac_resolve_async(self, source, info, *args, **kwargs):
            # Zajisti, že user má id před voláním původní metody
            context = info.context
            user_obj = context.get("user")
            
            if user_obj and isinstance(user_obj, dict):
                if "id" not in user_obj or not user_obj.get("id"):
                    user_obj["id"] = "2d9dc5ca-a4a2-11ed-b9df-0242ac120003"
                    context["user"] = user_obj
            elif not user_obj or not isinstance(user_obj, dict):
                context["user"] = {"id": "2d9dc5ca-a4a2-11ed-b9df-0242ac120003"}
            
            return await original_rbac_resolve_async(self, source, info, *args, **kwargs)
        
        RbacInsertProviderExtension.resolve_async = patched_rbac_resolve_async
        RbacInsertProviderExtension._patched_for_tests = True
except Exception as e:
    import logging
    logging.warning(f"Failed to monkey patch RbacInsertProviderExtension.resolve_async in conftest.py: {e}")
