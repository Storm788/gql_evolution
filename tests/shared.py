import sqlalchemy
import sys
import asyncio

# setting path
sys.path.append("../gql_events")

import pytest

# from ..uoishelpers.uuid import UUIDColumn

from DBDefinitions import BaseModel, EventModel


async def prepare_in_memory_sqllite():
    from sqlalchemy.ext.asyncio import create_async_engine
    from sqlalchemy.ext.asyncio import AsyncSession
    from sqlalchemy.orm import sessionmaker

    asyncEngine = create_async_engine("sqlite+aiosqlite:///:memory:")
    # asyncEngine = create_async_engine("sqlite+aiosqlite:///data.sqlite")
    async with asyncEngine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)

    async_session_maker = sessionmaker(
        asyncEngine, expire_on_commit=False, class_=AsyncSession
    )

    return async_session_maker


from src.DBFeeder import get_demodata


async def prepare_demodata(async_session_maker):
    data = get_demodata()

    from uoishelpers.feeders import ImportModels

    await ImportModels(
        async_session_maker,
        [
            EventModel
        ],
        data,
    )


from src.Utils.Dataloaders import createLoadersContext

def createContext(asyncSessionMaker, withuser=True):
    # Mock getUserFromInfo z uoishelpers.Dataloaders, pokud je potřeba
    # Toto zajistí, že UserRoleProviderExtension z uoishelpers dostane user s id
    loadersContext = createLoadersContext(asyncSessionMaker)
    user = {
        "id": "2d9dc5ca-a4a2-11ed-b9df-0242ac120003",
        "name": "John",
        "surname": "Newbie",
        "email": "john.newbie@world.com"
    }
    if withuser:
        # Přidej mock request pro getUserFromInfo
        class Request():
            @property
            def headers(self):
                return {"Authorization": "Bearer 2d9dc5ca-a4a2-11ed-b9df-0242ac120003"}
            
            @property
            def cookies(self):
                return {}
        
        loadersContext["request"] = Request()
        
        # Nastav user PŘÍMO do kontextu - UserRoleProviderExtension z uoishelpers
        # očekává user s id přímo v context["user"]
        # Musíme použít dict() místo copy.deepcopy, protože _ContextDict může upravit user
        import copy
        user_dict = dict(user)  # Vytvoř nový slovník z user
        # Ujisti se, že user má id
        if "id" not in user_dict:
            user_dict["id"] = user["id"]
        
        # Nastav user do kontextu - _ContextDict automaticky uloží kopii do __original_user
        # pokud tam ještě není
        # KRITICKÉ: Použij dict.__setitem__ aby se nevolal znovu __setitem__ s kontrolou
        # Toto zajistí, že user má id i když _ContextDict.__setitem__ ho upraví
        dict.__setitem__(loadersContext, "user", user_dict)
        
        # Ujisti se, že __original_user má id (pokud existuje)
        if "__original_user" in loadersContext and loadersContext["__original_user"]:
            if not isinstance(loadersContext["__original_user"], dict):
                dict.__setitem__(loadersContext, "__original_user", {"id": user["id"]})
            elif "id" not in loadersContext["__original_user"]:
                loadersContext["__original_user"]["id"] = user["id"]
                dict.__setitem__(loadersContext, "__original_user", loadersContext["__original_user"])
        
        # Finální kontrola - ujisti se, že user má id
        # Toto je kritické - UserRoleProviderExtension z uoishelpers očekává user s id
        # Použijeme __getitem__ aby prošel přes _ContextDict.__getitem__
        try:
            final_user = loadersContext["user"]
            if final_user and isinstance(final_user, dict):
                if "id" not in final_user or not final_user.get("id"):
                    final_user["id"] = user["id"]
                    dict.__setitem__(loadersContext, "user", final_user)
        except KeyError:
            # Pokud user neexistuje, vytvoř ho
            dict.__setitem__(loadersContext, "user", {"id": user["id"]})
        
        # DODATEČNÁ kontrola - ujisti se, že user má id i po všech úpravách
        # Toto je důležité, protože _ContextDict nebo WhoAmIExtension může upravit user
        # Použijeme get() aby prošel přes _ContextDict.get()
        final_check_user = loadersContext.get("user")
        if final_check_user and isinstance(final_check_user, dict):
            if "id" not in final_check_user or not final_check_user.get("id"):
                final_check_user["id"] = user["id"]
                dict.__setitem__(loadersContext, "user", final_check_user)
        elif not final_check_user or not isinstance(final_check_user, dict):
            dict.__setitem__(loadersContext, "user", {"id": user["id"]})
    
    return loadersContext

def createInfo(asyncSessionMaker, withuser=True):
    class Request():
        @property
        def headers(self):
            return {"Authorization": "Bearer 2d9dc5ca-a4a2-11ed-b9df-0242ac120003"}
        
    class Info():
        @property
        def context(self):
            context = createContext(asyncSessionMaker, withuser=withuser)
            context["request"] = Request()
            return context
        
    return Info()