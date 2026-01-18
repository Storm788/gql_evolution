import os
import socket
import asyncio

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, FileResponse
from strawberry.fastapi import GraphQLRouter

import logging
import logging.handlers

# .env already loaded at the top of the file

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
async def get_context(request: Request):
    asyncSessionMaker = await RunOnceAndReturnSessionMaker()
        
    from src.Dataloaders import createLoadersContext
    from src.Utils.Dataloaders import _extract_demo_user_id, _load_user_from_systemdata
    context = createLoadersContext(asyncSessionMaker)

    result = {**context}
    result["request"] = request
    
    # Nastav uživatele z x-demo-user-id před tím, než WhoAmIExtension začne pracovat
    # WhoAmIExtension pak může použít existujícího uživatele nebo ho přepsat, pokud má lepší data
    demo_user_id = _extract_demo_user_id(request)
    if demo_user_id:
        user_data = _load_user_from_systemdata(demo_user_id)
        if user_data:
            result["user"] = user_data
        else:
            # Pokud nenajdeme uživatele v systemdata, použijeme alespoň ID
            result["user"] = {"id": demo_user_id}
    
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
    context_getter=get_context
)

from uoishelpers.schema import SessionCommitExtensionFactory
from src.Dataloaders import createLoadersContext
schema.extensions.append(
    SessionCommitExtensionFactory(session_maker_factory=RunOnceAndReturnSessionMaker, loaders_factory=createLoadersContext)
)


app.include_router(graphql_app, prefix="/gql")

@app.get("/graphiql", response_class=FileResponse)
async def graphiql_endpoint():
    realpath = os.path.realpath("./public/graphiql.html")
    return realpath

@app.get("/voyager", response_class=FileResponse)
async def voyager():
    realpath = os.path.realpath("./src/Htmls/voyager.html")
    return realpath

@app.get("/doc", response_class=FileResponse)
async def doc():
    realpath = os.path.realpath("./src/Htmls/liveschema.html")
    return realpath

@app.get("/ui", response_class=FileResponse)
async def ui():
    realpath = os.path.realpath("./src/Htmls/livedata.html")
    return realpath

@app.get("/test", response_class=FileResponse)
async def test():
    realpath = os.path.realpath("./src/Htmls/tests.html")
    return realpath

import prometheus_client
@app.get("/metrics")
async def metrics():
    return Response(
        content=prometheus_client.generate_latest(), 
        media_type=prometheus_client.CONTENT_TYPE_LATEST
        )

@app.get("/whoami")
async def whoami(request: Request):
    """Returns current user information from context, headers, or cookies.
    Automatically reads from cookies set by frontend after login.
    """
    from src.Utils.Dataloaders import _extract_demo_user_id, _extract_authorization_token, _load_user_from_systemdata
    
    # Try to get user from x-demo-user-id header or cookie
    demo_user_id = _extract_demo_user_id(request)
    
    # If we got a JWT token (starts with 'eyJ' or 'Bearer'), WhoAmIExtension will handle it
    # For now, just return the token ID
    if demo_user_id and (demo_user_id.startswith('eyJ') or demo_user_id.startswith('Bearer')):
        # It's a JWT token - WhoAmIExtension will process it in GraphQL context
        # For /whoami endpoint, we can't decode JWT here easily, so return basic info
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
    
    # Try Authorization token as fallback
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
    result = os.getenv(name, None)
    # Try to strip whitespace if result exists
    if result:
        result = result.strip()
    if result is None or result == "":
        # Debug: print all env vars that start with DEMO or GQL
        print(f"\nDEBUG: Environment variable '{name}' is not set or empty")
        print(f"DEBUG: All env vars starting with 'DEMO' or 'GQL':")
        for key, value in os.environ.items():
            if 'DEMO' in key.upper() or 'GQL' in key.upper():
                print(f"  {key}={value}")
        # Also try to reload .env file
        try:
            from dotenv import load_dotenv
            from pathlib import Path
            env_path = Path(__file__).parent / '.env'
            if env_path.exists():
                print(f"DEBUG: Attempting to reload .env from {env_path}")
                load_dotenv(dotenv_path=env_path, override=True)
                result = os.getenv(name, None)
                if result:
                    result = result.strip()
                    print(f"DEBUG: After reload, {name}={result}")
        except Exception as e:
            print(f"DEBUG: Could not reload .env: {e}")
    assert result is not None and result != "", f"{name} environment variable must be explicitly defined"
    return result

DEMO = envAssertDefined("DEMO", None)
GQLUG_ENDPOINT_URL = envAssertDefined("GQLUG_ENDPOINT_URL", None)

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