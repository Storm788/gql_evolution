import os
import socket
import asyncio

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from strawberry.fastapi import GraphQLRouter

import logging
import logging.handlers

# Load environment variables from .env file
from dotenv import load_dotenv
import os as _os_temp
_env_path = _os_temp.path.join(_os_temp.path.dirname(__file__), '.env')
print(f"DEBUG: Loading .env from: {_env_path}")
load_dotenv(_env_path)
print(f"DEBUG: After load_dotenv, DEMODATA={os.getenv('DEMODATA')}, DEMO={os.getenv('DEMO')}")
del _os_temp

from src.GraphTypeDefinitions import schema
from src.DBDefinitions import startEngine, ComposeConnectionString
from src.DBFeeder import initDB

# region logging setup

logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s.%(msecs)03d\t%(levelname)s:\t%(message)s', 
    datefmt='%Y-%m-%dT%I:%M:%S')
SYSLOGHOST = os.getenv("SYSLOGHOST", None)
if SYSLOGHOST is not None:
    [address, strport, *_] = SYSLOGHOST.split(':')
    assert len(_) == 0, f"SYSLOGHOST {SYSLOGHOST} has unexpected structure, try `localhost:514` or similar (514 is UDP port)"
    port = int(strport)
    my_logger = logging.getLogger()
    my_logger.setLevel(logging.INFO)
    handler = logging.handlers.SysLogHandler(address=(address, port), socktype=socket.SOCK_DGRAM)
    #handler = logging.handlers.SocketHandler('10.10.11.11', 611)
    my_logger.addHandler(handler)

# endregion

# region DB setup

## Definice GraphQL typu (pomoci strawberry https://strawberry.rocks/)
## Strawberry zvoleno kvuli moznosti mit federovane GraphQL API (https://strawberry.rocks/docs/guides/federation, https://www.apollographql.com/docs/federation/)
## Definice DB typu (pomoci SQLAlchemy https://www.sqlalchemy.org/)
## SQLAlchemy zvoleno kvuli moznost komunikovat s DB asynchronne
## https://docs.sqlalchemy.org/en/14/core/future.html?highlight=select#sqlalchemy.future.select


## Zabezpecuje prvotni inicializaci DB a definovani Nahodne struktury pro "Univerzity"
# from gql_workflow.DBFeeder import createSystemDataStructureRoleTypes, createSystemDataStructureGroupTypes

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
    ###########################################################################################################################
    #
    # zde definujte do funkce asyncio.gather
    # vlozte asynchronni funkce, ktere maji data uvest do prvotniho konzistentniho stavu
    async def initDBAndReport():
        logging.info(f"initializing system structures")
        await initDB(result)
        logging.info(f"all done")
        print(f"all done")

    # asyncio.create_task(coro=initDBAndReport())
    await initDBAndReport()

    #
    #
    ###########################################################################################################################
    
    return result

# endregion

# region FastAPI setup
DEMO_DEFAULT_USER_ID = os.getenv(
    "DEMO_DEFAULT_USER_ID",
    "76dac14f-7114-4bb2-882d-0d762eab6f4a",  # ESTERA_ID as fallback
)


def _pick_demo_user_id(request: Request) -> str | None:
    """Resolve the user identifier to be injected into context in demo mode."""
    
    # PRIORITA 1: x-demo-user-id header (pro manuální testování)
    header_key = "x-demo-user-id"
    candidate = request.headers.get(header_key)
    if candidate:
        print(f"DEBUG _pick_demo_user_id: Using x-demo-user-id header: {candidate}")
        return candidate.strip()

    # PRIORITA 2: demo-user-id cookie (nastavená z UG nebo ručně)
    cookie = request.cookies.get("demo-user-id")
    if cookie:
        print(f"DEBUG _pick_demo_user_id: Using demo-user-id cookie: {cookie}")
        return cookie.strip()
    
    # PRIORITA 3: JWT token z Authorization header (od UG přes Apollo Gateway)
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header[7:].strip()  # Remove "Bearer " prefix
        # Dekóduj JWT a získej user_id
        try:
            import jwt
            # Decode bez verifikace (jen pro demo/development)
            decoded = jwt.decode(token, options={"verify_signature": False})
            user_id = decoded.get("id") or decoded.get("sub") or decoded.get("user_id")
            if user_id:
                print(f"DEBUG _pick_demo_user_id: Extracted user_id from JWT: {user_id}")
                return str(user_id)
        except Exception as e:
            print(f"Warning: Could not decode JWT token: {e}")
    
    # PRIORITA 4: Explicit environment variable
    explicit = os.getenv("DEMO_USER_ID")
    if explicit:
        print(f"DEBUG _pick_demo_user_id: Using DEMO_USER_ID env: {explicit}")
        return explicit.strip()

    # FALLBACK: Default demo user (POUZE pokud není v produkci)
    # V demo módu bez explicitní auth vrátíme None, ne admin!
    if os.getenv("DEMO", "True").lower() == "true":
        # Pro dev/testing bez auth - vrátíme None místo fallback na admina
        print(f"DEBUG _pick_demo_user_id: No auth found, returning None (no fallback to admin)")
        return None
    
    print(f"DEBUG _pick_demo_user_id: Using default: {DEMO_DEFAULT_USER_ID}")
    return DEMO_DEFAULT_USER_ID


async def get_context(request: Request):
    asyncSessionMaker = await RunOnceAndReturnSessionMaker()
        
    from src.Dataloaders import createLoadersContext
    context = createLoadersContext(asyncSessionMaker)

    result = {**context}
    result["request"] = request

    # ID mapping z starých Docker IDs na systemdata IDs
    OLD_TO_SYSTEMDATA_ID = {
        '2d9dc5ca-a4a2-11ed-b9df-0242ac120003': '76dac14f-7114-4bb2-882d-0d762eab6f4a',  # Estera
        'ccb397ad-0de7-46e7-bff0-42452f11dd5e': '678a2389-dd49-4d44-88be-28841ae34df1',  # Ornela
        '27831740-f1cb-46ea-acdf-a4728029b0fb': '83981199-2134-4724-badf-cd1f0f38babf',  # Dalimil (jediný potřebuje mapování)
    }

    def load_user_from_systemdata(user_id: str) -> dict:
        """Helper to load user data from systemdata.combined.json"""
        try:
            import json
            from pathlib import Path
            data_path = Path(__file__).parent / "systemdata.combined.json"
            if data_path.exists():
                with open(data_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    users = data.get('users', [])
                    for user in users:
                        if user.get('id') == user_id:
                            return {
                                "id": user_id,
                                "email": user.get('email', ''),
                                "name": user.get('name', ''),
                                "surname": user.get('surname', '')
                            }
        except Exception as e:
            print(f"Warning: Could not load user data from systemdata: {e}")
        return {"id": user_id}

    # Získej user_id z různých zdrojů (header, cookie, JWT, ...)
    demo_user_id = _pick_demo_user_id(request) if os.getenv("DEMO", "True").lower() == "true" else None
    
    if demo_user_id:
        # Mapuj staré Docker ID na systemdata ID
        systemdata_id = OLD_TO_SYSTEMDATA_ID.get(demo_user_id, demo_user_id)
        print(f"DEBUG get_context: user_id={demo_user_id}, mapped={systemdata_id}")
        
        # Načti user data ze systemdata
        user_data = load_user_from_systemdata(systemdata_id)
        result["user"] = user_data
        result.setdefault("__original_user", user_data.copy())
        print(f"DEBUG get_context: User loaded: email={user_data.get('email', 'N/A')}")
    else:
        # Není žádná autentizace - user je None
        print(f"DEBUG get_context: No authentication found, user=None")
        result["user"] = None

    # V produkci vyžaduj autentizaci
    if os.getenv("DEMO", "False").lower() != "true" and not result.get("user"):
        raise HTTPException(status_code=401, detail="Authorization required")

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
        print(f"FastAPI.lifespan {innerlifespan is None}")
        initizalizedEngine = await RunOnceAndReturnSessionMaker()
        try:
            yield
        finally:
            pass
        await backupDB(initizalizedEngine)
    
    # print("App shutdown, nothing to do")

app = FastAPI(lifespan=lifespan)

graphql_app = GraphQLRouter(
    schema,
    context_getter=get_context,
)

from uoishelpers.schema import SessionCommitExtensionFactory
from src.Dataloaders import createLoadersContext
schema.extensions.append(
    SessionCommitExtensionFactory(session_maker_factory=RunOnceAndReturnSessionMaker, loaders_factory=createLoadersContext)
)


app.include_router(graphql_app, prefix="/gql")

@app.get("/graphiql", response_class=FileResponse)
async def graphiql():
    realpath = os.path.realpath("./public/graphiql.html")
    return realpath

@app.get("/whoami")
async def whoami(request: Request):
    """Return current user info or a simple 'No User' marker."""
    try:
        ctx = await get_context(request)
        user = ctx.get("user")
        if not user:
            return JSONResponse({"user": None, "label": "No User"})
        # compose a friendly label
        name = user.get("name")
        surname = user.get("surname")
        fullname = (
            f"{name} {surname}".strip()
            if (name or surname)
            else user.get("email") or str(user.get("id"))
        )
        return JSONResponse({
            "user": {
                "id": user.get("id"),
                "email": user.get("email"),
                "name": name,
                "surname": surname
            },
            "label": fullname or "No User"
        })
    except Exception as e:
        # In case of unexpected errors, default to No User
        return JSONResponse({"user": None, "label": "No User", "error": str(e)})

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
    return realpath

import prometheus_client
@app.get("/metrics")
async def metrics():
    return Response(
        content=prometheus_client.generate_latest(), 
        media_type=prometheus_client.CONTENT_TYPE_LATEST
        )


logging.info("All initialization is done")

# @app.get('/hello')
# def hello():
#    return {'hello': 'world'}

###########################################################################################################################
#
# pokud jste pripraveni testovat GQL funkcionalitu, rozsirte apollo/server.js
#
###########################################################################################################################
# endregion

# region ENV setup tests
def envAssertDefined(name, default=None):
    result = os.getenv(name, default)
    assert result is not None, f"{name} environment variable must be explicitly defined"
    return result

DEMO = envAssertDefined("DEMO", "False")
GQLUG_ENDPOINT_URL = envAssertDefined("GQLUG_ENDPOINT_URL", "http://localhost:8000/gql")

assert (DEMO in ["True", "true", "False", "false"]), "DEMO environment variable can have only `True` or `False` values"
DEMO = DEMO in ["True", "true"]

if DEMO:
    print("####################################################")
    print("#                                                  #")
    print("# RUNNING IN DEMO                                  #")
    print("#                                                  #")
    print("####################################################")

    logging.info("####################################################")
    logging.info("#                                                  #")
    logging.info("# RUNNING IN DEMO                                  #")
    logging.info("#                                                  #")
    logging.info("####################################################")
else:
    print("####################################################")
    print("#                                                  #")
    print("# RUNNING DEPLOYMENT                               #")
    print("#                                                  #")
    print("####################################################")

    logging.info("####################################################")
    logging.info("#                                                  #")
    logging.info("# RUNNING DEPLOYMENT                               #")
    logging.info("#                                                  #")
    logging.info("####################################################")    

logging.info(f"DEMO = {DEMO}")
logging.info(f"SYSLOGHOST = {SYSLOGHOST}")
logging.info(f"GQLUG_ENDPOINT_URL = {GQLUG_ENDPOINT_URL}")

# endregion
