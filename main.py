import os
import socket
import asyncio

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, FileResponse
from strawberry.fastapi import GraphQLRouter

import logging
import logging.handlers

from src.GraphTypeDefinitions import schema
from src.DBDefinitions import startEngine, ComposeConnectionString
from src.DBFeeder import initDB

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s.%(msecs)03d\t%(levelname)s:\t%(message)s',
    datefmt='%Y-%m-%dT%I:%M:%S')
SYSLOGHOST = os.getenv("SYSLOGHOST", None)
if SYSLOGHOST is not None:
    [address, strport, *_] = SYSLOGHOST.split(':')
    assert len(_) == 0, f"SYSLOGHOST {SYSLOGHOST} has unexpected structure"
    port = int(strport)
    my_logger = logging.getLogger()
    my_logger.setLevel(logging.INFO)
    handler = logging.handlers.SysLogHandler(address=(address, port), socktype=socket.SOCK_DGRAM)
    my_logger.addHandler(handler)

connectionString = ComposeConnectionString()

def singleCall(asyncFunc):
    """Dekorator, ktery dovoli, aby dekorovana funkce byla volana (vycislena) jen jednou. Navratova hodnota je zapamatovana a pri dalsich volanich vracena.
    Dekorovana funkce je asynchronni.
    """
    resultCache = {}

    async def result():
        if resultCache.get("result", None) is None:
            resultCache["result"] = await asyncFunc()
        return resultCache["result"]

    return result

@singleCall
async def RunOnceAndReturnSessionMaker():
    """Provadi inicializaci asynchronniho db engine, inicializaci databaze a vraci asynchronni SessionMaker.
    Protoze je dekorovana, volani teto funkce se provede jen jednou a vystup se zapamatuje a vraci se pri dalsich volanich.
    """

    makeDrop = os.getenv("DEMO", None) == "True"
    logging.info(f'starting engine for "{connectionString} makeDrop={makeDrop}"')

    result = await startEngine(
        connectionstring=connectionString, makeDrop=makeDrop, makeUp=True
    )   
    assert result is not None, "Unable to start engine"
    async def initDBAndReport():
        logging.info("initializing system structures")
        await initDB(result)
        logging.info("all done")
    await initDBAndReport()
    return result


async def get_context(request: Request):
    asyncSessionMaker = await RunOnceAndReturnSessionMaker()
    
    # Ulož sessionmaker do globální cache pro createLoadersContextWrapper
    global _session_maker_cache
    _session_maker_cache = asyncSessionMaker

    from src.Dataloaders import createLoadersContext
    from src.Utils.Dataloaders import _extract_demo_user_id, _load_user_from_systemdata, _load_user_roles_from_systemdata, load_user_roles_from_db, _UserRolesForRBACLoader
    context = createLoadersContext(asyncSessionMaker)
    context["userRolesForRBACQuery_loader"] = _UserRolesForRBACLoader(asyncSessionMaker)
    result = {**context}
    result["request"] = request
    demo_user_id = _extract_demo_user_id(request)

    async def _merge_and_attach_roles(user_id: str):
        """Načte role ze systemdata i z DB a sloučí je do result['user']['roles'] a result['user_roles']."""
        if not user_id:
            return
        roles_systemdata = _load_user_roles_from_systemdata(user_id)
        roles_db = await load_user_roles_from_db(asyncSessionMaker, user_id)
        seen_rt = {str(r.get("roletype_id")) for r in roles_systemdata if r.get("roletype_id")}
        merged = list(roles_systemdata)
        for r in roles_db:
            rt_id = str(r.get("roletype_id")) if r.get("roletype_id") else None
            if rt_id and rt_id not in seen_rt:
                seen_rt.add(rt_id)
                merged.append(r)
        if merged:
            result["user"]["roles"] = merged
            result["user_roles"] = merged

    if demo_user_id:
        result["use_demo_rbac_loader"] = True
        if demo_user_id.startswith('eyJ') or demo_user_id.startswith('Bearer ') or 'eyJ' in demo_user_id:
            from src.Utils.Dataloaders import _extract_user_id_from_jwt
            user_id_from_jwt = _extract_user_id_from_jwt(demo_user_id)
            if user_id_from_jwt:
                user_data = _load_user_from_systemdata(user_id_from_jwt)
                if user_data:
                    result["user"] = user_data
                    result["__original_user"] = user_data
                    result["user_roles"] = user_data.get("roles") or []
                    await _merge_and_attach_roles(user_id_from_jwt)
                else:
                    result["user"] = {"id": user_id_from_jwt}
                    result["__original_user"] = {"id": user_id_from_jwt}
                    await _merge_and_attach_roles(user_id_from_jwt)
        else:
            user_data = _load_user_from_systemdata(demo_user_id)
            if user_data:
                result["user"] = user_data
                result["__original_user"] = user_data
                result["user_roles"] = user_data.get("roles") or []
                await _merge_and_attach_roles(demo_user_id)
            else:
                result["user"] = {"id": demo_user_id}
                result["__original_user"] = {"id": demo_user_id}
                await _merge_and_attach_roles(demo_user_id)
    # Vždy zajisti, že kontext má "user" s klíčem "id" (UserRoleProviderExtension z uoishelpers volá user["id"]).
    # Bez toho při selhání UG endpointu nebo bez x-demo-user-id vzniká KeyError.
    if "user" not in result:
        result["user"] = {"id": None}
    elif isinstance(result.get("user"), dict) and "id" not in result["user"]:
        result["user"]["id"] = None
    return result

innerlifespan = None
@asynccontextmanager
async def dummy(app: FastAPI):
    yield 

@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.DBFeeder import backupDB
    icm = dummy if innerlifespan is None else innerlifespan
    async with icm(app):
        initizalizedEngine = await RunOnceAndReturnSessionMaker()
        try:
            yield
        finally:
            pass
        await backupDB(initizalizedEngine)

app = FastAPI(lifespan=lifespan)

graphql_app = GraphQLRouter(
    schema,
    context_getter=get_context
)

from uoishelpers.schema import SessionCommitExtensionFactory
from src.Dataloaders import createLoadersContext

# Globální cache pro sessionmaker (získáme z RunOnceAndReturnSessionMaker)
_session_maker_cache = None

def _get_session_maker():
    """Získá sessionmaker z cache. Cache se naplní při prvním volání get_context."""
    global _session_maker_cache
    if _session_maker_cache is None:
        import logging
        import asyncio
        import concurrent.futures
        logger = logging.getLogger(__name__)
        logger.warning("createLoadersContextWrapper: sessionmaker cache is empty")
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, RunOnceAndReturnSessionMaker())
                _session_maker_cache = future.result()
        except Exception as e:
            logger.error(f"createLoadersContextWrapper: error getting sessionmaker: {e}")
            raise
    return _session_maker_cache

def createLoadersContextWrapper(session_or_factory_or_class):
    """Wrapper pro createLoadersContext – vždy použije sessionmaker z cache."""
    import logging
    from sqlalchemy.ext.asyncio import AsyncSession
    session_maker = _get_session_maker()
    if callable(session_or_factory_or_class):
        if session_or_factory_or_class is AsyncSession or (isinstance(session_or_factory_or_class, type) and issubclass(session_or_factory_or_class, AsyncSession)):
            return createLoadersContext(session_maker)
        if isinstance(session_or_factory_or_class, AsyncSession):
            return createLoadersContext(session_maker)
        return createLoadersContext(session_or_factory_or_class)
    return createLoadersContext(session_maker)

schema.extensions.append(
    SessionCommitExtensionFactory(session_maker_factory=RunOnceAndReturnSessionMaker, loaders_factory=createLoadersContextWrapper)
)


app.include_router(graphql_app, prefix="/gql")

@app.get("/graphiql", response_class=FileResponse)
async def graphiql_endpoint():
    realpath = os.path.realpath("./public/graphiql.html")
    return realpath

@app.get("/voyager", response_class=FileResponse)
async def voyager():
    realpath = os.path.realpath("./public/voyager.html")
    return realpath

@app.get("/doc", response_class=FileResponse)
async def doc():
    realpath = os.path.realpath("./public/liveschema.html")
    return realpath

@app.get("/ui", response_class=FileResponse)
async def ui():
    realpath = os.path.realpath("./public/livedata.html")
    return realpath

@app.get("/test", response_class=FileResponse)
async def test():
    realpath = os.path.realpath("./public/tests.html")
    return FileResponse(realpath)

import prometheus_client
@app.get("/metrics")
async def metrics():
    return Response(
        content=prometheus_client.generate_latest(), 
        media_type=prometheus_client.CONTENT_TYPE_LATEST
        )

@app.get("/whoami")
async def whoami(request: Request):
    """Vrací aktuálního uživatele z x-demo-user-id, cookie nebo Authorization."""
    from src.Utils.Dataloaders import _extract_demo_user_id, _extract_authorization_token, _load_user_from_systemdata
    demo_user_id = _extract_demo_user_id(request)
    if demo_user_id and (demo_user_id.startswith('eyJ') or demo_user_id.startswith('Bearer')):
        return JSONResponse({
            "id": "authenticated",
            "label": "Přihlášený uživatel (JWT)"
        })
    
    if demo_user_id:
        user_data = _load_user_from_systemdata(demo_user_id)
        if user_data:
            return JSONResponse({
                "id": user_data.get("id"),
                "email": user_data.get("email"),
                "name": user_data.get("name"),
                "surname": user_data.get("surname"),
                "label": f"{user_data.get('name', '')} {user_data.get('surname', '')}".strip() or user_data.get('email', 'Unknown')
            })
        else:
            return JSONResponse({
                "id": demo_user_id,
                "label": f"User {demo_user_id}"
            })
    
    auth_token = _extract_authorization_token(request)
    if auth_token:
        return JSONResponse({
            "id": "authenticated",
            "label": "Přihlášený uživatel (Token)"
        })
    
    return JSONResponse({
        "id": None,
        "label": "Bez uživatele"
    })


def envAssertDefined(name):
    result = os.getenv(name, None)
    if result:
        result = result.strip()
    if result is None or result == "":
        try:
            from dotenv import load_dotenv
            from pathlib import Path
            env_path = Path(__file__).parent / '.env'
            if env_path.exists():
                load_dotenv(dotenv_path=env_path, override=True)
                result = os.getenv(name, None)
                if result:
                    result = result.strip()
        except Exception:
            pass
    assert result is not None and result != "", f"{name} environment variable must be explicitly defined"
    return result

DEMO = envAssertDefined("DEMO")
GQLUG_ENDPOINT_URL = envAssertDefined("GQLUG_ENDPOINT_URL")
assert DEMO in ["True", "true", "False", "false"], "DEMO must be True or False"
DEMO = DEMO in ["True", "true"]
logging.info("DEMO=%s GQLUG_ENDPOINT_URL=%s", DEMO, GQLUG_ENDPOINT_URL)