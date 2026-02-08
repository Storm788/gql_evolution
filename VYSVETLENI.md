# Vysvětlení projektu gql_evolution

Tento dokument popisuje, jak projekt funguje, k čemu slouží jednotlivé části a jak spolu souvisí.

---

## Co je tento projekt

**gql_evolution** je **GraphQL backend** (subgraph) pro správu **majetku (assets)**, **zápůjček (asset loans)** a **invitarizačních záznamů**, včetně **akcí/událostí (events)** a **pozváněk**. Aplikace:

- Běží jako **FastAPI** server s **Strawberry GraphQL**.
- Je součástí **Apollo Federation** – spolu s dalšími subgraphy (např. uživatelé/skupiny) tvoří jeden společný GraphQL endpoint přes Gateway.
- Používá **PostgreSQL** (async přes asyncpg), **RBAC** (role: administrátor, editor, viewer, čtenář) a v demo režimu načítá data z JSON souboru (`systemdata.json`).

---

## Architektura na vysoké úrovni

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Klient / UI    │────▶│  Apollo Gateway   │────▶│  gql_evolution      │
│  (GraphiQL…)    │     │  (port 33000/01)  │     │  (port 8001)        │
└─────────────────┘     └──────────────────┘     │  + další subgraphey │
                          │                       └─────────────────────┘
                          │                       ┌─────────────────────┐
                          └──────────────────────▶│  gql_ug (uživatelé) │
                                                  └─────────────────────┘
```

- **Gateway** slučuje schémata z více subgraphů (evolution = majetek/akce, ug = uživatelé/skupiny).
- **gql_evolution** obsluhuje entity: `Asset`, `AssetLoan`, `AssetInventoryRecord`, `Event`, `EventInvitation` a federované reference na `User`, `Group`, `Role`.

---

## Struktura složek a souborů

### Kořen projektu

| Soubor / složka | Účel |
|-----------------|------|
| **main.py** | Vstupní bod aplikace: FastAPI app, GraphQL router, kontext, endpointy (/gql, /graphiql, /whoami, /metrics…), načtení env (DEMO, GQLUG_ENDPOINT_URL). |
| **.env** | Lokální konfigurace (DEMO, GQLUG_ENDPOINT_URL, volitelně DB). Načítá se při startu, není v gitu. |
| **.env.example** | Šablona proměnných prostředí (např. pro Docker). |
| **requirements.txt** | Python závislosti (FastAPI, Strawberry, SQLAlchemy, asyncpg, uoishelpers, …). |
| **Dockerfile** | Obraz pro běh aplikace v kontejneru (uvicorn na portu 8000). |
| **docker-compose.debug.yml** | Skládání služeb pro ladění v Dockeru. |
| **log_conf.yaml** | Konfigurace logování (volitelně). |
| **systemdata.json** | Demo data (uživatelé, role, assety, zápůjčky, akce…) pro režim DEMO=True. |
| **systemdata.backup.json** | Záloha demo dat (používá se při backupu DB). |
| **README.md** | Historie změn a shrnutí stavu projektu. |
| **VYSVETLENI.md** | Tento soubor – popis projektu a souborů. |

---

### Složka `src/` – jádro aplikace

#### `src/DBDefinitions/` – databázové modely (SQLAlchemy)

Definice tabulek a vztahů. Vše dědí z **BaseModel** (id, created, lastchange, createdby_id, changedby_id, rbacobject_id).

| Soubor | Účel |
|--------|------|
| **__init__.py** | Export `startEngine`, `ComposeConnectionString`, všech modelů. Načítá modely a vytváří async engine + session maker. |
| **BaseModel.py** | Bázová třída pro všechny DB modely (UUID primární klíče, FK na users, rbacobject_id). Pomocné funkce `UUIDColumn`, `UUIDFKey`. |
| **uuid.py** | Pomocné typy/konstanty pro UUID. |
| **EventDBModel.py** | Tabulka akcí/událostí (event). |
| **EventInvitationModel.py** | Tabulka pozvánek na akce. |
| **AssetModel.py** | Tabulka majetku (asset). |
| **AssetLoanModel.py** | Tabulka zápůjček majetku. |
| **AssetInventoryRecordModel.py** | Tabulka inventarizačních záznamů. |

**Poznámka:** `ComposeConnectionString()` skládá connection string z env (POSTGRES_HOST, POSTGRES_USER, … nebo CONNECTION_STRING). `startEngine()` vytváří async engine, volitelně drop/create tabulky a vrací async session maker.

---

#### `src/GraphTypeDefinitions/` – GraphQL schéma a resolvery

Strawberry typy, query, mutation a federované entity. Schéma je **Apollo Federation** (strawberry.federation.Schema).

| Soubor | Účel |
|--------|------|
| **__init__.py** | Sestaví `schema` (Query, Mutation, všechny typy), přidá rozšíření (WhoAmIExtension, PrometheusExtension, RolePermissionSchemaExtension / DemoRBACLoaderExtension). Definuje scalar `timedelta`. |
| **query.py** | Kořen **Query**: `hello`, `whoami`, `who_am_i` (WhoAmIType) a děděné query z Event, EventInvitation, Asset, AssetInventoryRecord, AssetLoan. |
| **mutation.py** | Kořen **Mutation**: dědí mutace z Event, EventInvitation, Asset, AssetInventoryRecord, AssetLoan, Role. |
| **BaseGQLModel.py** | Bázový GraphQL model (federovaný interface): `id`, `lastchange`, `created`, pomocné metody `getLoader`, `from_dataclass`, `load_with_loader`, `resolve_reference`. Direktiva `Relation`. |
| **UserGQLModel.py** | Federovaný typ **User** (reference z tohoto subgraphu – např. custodian); neobsahuje vlastní pole `roles` (to přináší subgraph ug). |
| **GroupGQLModel.py** | Federovaný typ **Group** (reference). |
| **RoleGQLModel.py** | Federovaný typ **Role** a RoleMutation. |
| **EventGQLModel.py** | GraphQL typ a query/mutation pro **Event**. |
| **EventInvitationGQLModel.py** | GraphQL typ a query/mutation pro **EventInvitation**. |
| **AssetGQLModel.py** | GraphQL typ a query/mutation pro **Asset** (včetně stránkování `asset_page`, RBAC – admin vidí vše, ostatní jen kde jsou custodian). |
| **AssetLoanGQLModel.py** | GraphQL typ a query/mutation pro **AssetLoan** (včetně kontroly role u insert). |
| **AssetInventoryRecordGQLModel.py** | GraphQL typ a query/mutation pro **AssetInventoryRecord**. |
| **TimeUnit.py** | GraphQL enum nebo typ pro časové jednotky (např. u zápůjček). |
| **permissions.py** | RBAC: konstanty role (ADMINISTRATOR_ROLE_ID, EDITOR_ROLE_ID, …), `get_user_roles_from_db()`, `user_has_role()`, `user_has_any_role()`, permission třídy (`RequireAdmin`, `RequireEditor`, `RequireViewer`, `RequireRole`). |
| **context_utils.py** | Pomocné funkce pro kontext – např. `ensure_user_in_context(info)` pro získání aktuálního uživatele z kontextu. |
| **DemoRBACLoaderExtension.py** | Rozšíření schématu pro demo režim – načítání RBAC rolí (např. ze systemdata). |

Každý *GQLModel* typ obvykle:

- Mapuje DB model na Strawberry typ.
- Implementuje `getLoader(info)` vrací loader z kontextu (např. `AssetModel`).
- Definuje query (seznam, stránkování, detail podle id) a mutation (insert, update, delete) s kontrolami oprávnění a vracením error union typů.

---

#### `src/Dataloaders/` – dataloadery pro GraphQL

| Soubor | Účel |
|--------|------|
| **__init__.py** | `createLoaders(asyncSessionMaker)` – vytvoří dataloadery pro EventModel, EventInvitationModel, AssetModel, AssetLoanModel, AssetInventoryRecordModel (pomocí uoishelpers `createIdLoader`). `createLoadersContext()` vrací dict `{"loaders": loaders_obj}` pro kontext. `getLoadersFromInfo(info)` pro resolvery. |

Dataloadery zajišťují batch loading podle ID a tím omezují N+1 dotazy.

---

#### `src/Utils/` – pomocné moduly

| Soubor | Účel |
|--------|------|
| **Dataloaders.py** | Rozšířená logika pro načítání uživatelů/rolí – např. `_extract_demo_user_id`, `_load_user_from_systemdata`, `_UserRolesForRBACLoader` pro demo režim (z requestu a systemdata). |
| **DBFeeder.py** | (Duplikát názvu s kořenovým DBFeeder – viz níže; zde může jít o re-export nebo pomocné funkce pro DB.) |
| **gql_client.py** | Async GraphQL klient pro volání jiného GQL API (OAuth login, posílání query s tokenem) – použití např. při volání User/Group služby. |
| **explain_query.py** | Nástroj na „vysvětlení“ GraphQL dotazu (parametry, typy, popisy polí) – využití pro dokumentaci nebo generování. |
| **GraphQLQueryBuilder.py** | Staví GraphQL dotazy/fragmenty ze SDL schématu (např. cesta mezi typy, generování fragmentů). |
| **utils_sdl_2.py** | Pomocné funkce pro práci se SDL AST (fragmenty, vektory, cesty). |

---

#### `src/DBFeeder.py` (v kořeni src/)

| Účel |
|------|
| Načítání a zápis dat do DB: `get_demodata()` čte `systemdata.json`, normalizuje tvary (`_normalize_dataset_shapes`). `initDB(asyncSessionMaker)` naplní tabulky z demodata (events, event_invitations, assets, asset_loans, asset_inventory_records). `backupDB(engine)` zálohuje data do `systemdata.backup.json`. Používá uoishelpers `ImportModels`. |

Volá se při startu aplikace (v `RunOnceAndReturnSessionMaker` → `initDB`) a při ukončení (v lifespan → `backupDB`).

---

#### `src/error_codes.py`

| Účel |
|------|
| Centralizovaný slovník chybových kódů (UUID) a českých zpráv: OPRÁVNĚNÍ_ZAMÍTNUTO, NENALEZENO, VALIDAČNÍ_CHYBA, VYŽADOVÁNA_AUTENTIZACE, CHYBA_DATABÁZE atd. Funkce `get_error_info(code)`, `format_error_message(code, …)`. Používá se v mutation resolvers při vracení InsertError/UpdateError/DeleteError. |

---

### Složka `tests/`

| Soubor | Účel |
|--------|------|
| **conftest.py** | Pytest fixture a nastavení: cesta k `src`, mock WhoAmIExtension (ug_query, on_request_start), nastavení GQLUG_ENDPOINT_URL, příprava DB/session pro testy. |
| **client.py** | Testovací GraphQL klient (např. async request na /gql). |
| **shared.py** | Sdílené konstanty, pomocné funkce pro testy. |
| **test_client.py** | Testy HTTP/GraphQL klienta. |
| **test_federation.py** | Testy federovaného schématu (reference, entity). |
| **test_dataloaders.py** | Testy dataloaderů. |
| **test_dbdefinitions.py** | Testy DB modelů. |
| **test_gt_definitions.py** | Testy GraphQL typů a resolverů. |
| **test_coverage.py** | Testy pokrytí kódu. |
| **README.md** | Návod k testům. |

---

### Složka `public/`

Statické HTML stránky obsluhované přes FastAPI (main.py je vrací jako FileResponse).

| Soubor | Účel |
|--------|------|
| **graphiql.html** | GraphiQL UI – editor dotazů, hlavičky (např. x-demo-user-id), zobrazení aktuálního uživatele. |
| **voyager.html** | Voyager – vizualizace GraphQL schématu. |
| **liveschema.html** | Živé zobrazení schématu (dokumentace). |
| **livedata.html** | Stránka pro živá data (UI). |
| **tests.html** | Testovací stránka (např. jednoduché testy z prohlížeče). |

Endpointy v main: `/graphiql`, `/voyager`, `/doc`, `/ui`, `/test`.

---

### Složka `docs/`

Dokumentace k použití a architektuře.

| Soubor | Účel |
|--------|------|
| **README.md** | Přehled dokumentace. |
| **GATEWAY_USAGE.md** | Použití Apollo Gateway. |
| **RBAC_GUIDE.md** | Průvodce RBAC (role, oprávnění). |
| **GRAPHIQL_CHEATSHEET.md** | Rychlý cheatsheet pro GraphiQL. |
| **ASSET_LOAN_QUERIES.md** | Příklady dotazů pro majetek a zápůjčky. |
| **USERS_AND_ROLES.md** | Uživatelé a role. |
| **apollo_federation_services_update.md** | Aktualizace federovaných služeb. |

---

### Složka `proxy/`

Jednoduchý **aiohttp proxy** – přeposílá požadavky na jiný server (např. na gql_evolution). Použití při nasazení, kdy frontend/gateway volá přes proxy (TARGET_SERVER z env).

| Soubor | Účel |
|--------|------|
| **main.py** | Web server, který proxy requesty na TARGET_SERVER. |
| **Dockerfile** | Obraz pro proxy službu. |
| **requirements.txt** | aiohttp. |

---

## Průběh startu aplikace

1. **main.py** se načte; na konci souboru se volá `envAssertDefined("DEMO")` a `envAssertDefined("GQLUG_ENDPOINT_URL")` (načte z os.environ nebo z `.env`).
2. **FastAPI** app se vytvoří s `lifespan` kontextem.
3. V **lifespan** se zavolá `RunOnceAndReturnSessionMaker()` (jednou):
   - `ComposeConnectionString()` → connection string k PostgreSQL.
   - `startEngine(..., makeDrop= když DEMO==True, makeUp=True)` → vytvoření/drop tabulek.
   - `initDB(sessionMaker)` → naplnění z `systemdata.json`.
4. Při každém **GraphQL požadavku** se volá `get_context(request)`:
   - Získá session maker a vytvoří kontext s dataloadery (`createLoadersContext`).
   - V demo režimu doplní uživatele a role z hlavičky/cookie (`x-demo-user-id`) a ze systemdata.
   - Kontext obsahuje `request`, `loaders`, `user`, `user_roles`, případně `userRolesForRBACQuery_loader`.
5. **GraphQL** request jde na `/gql` přes Strawberry router se schématem z `src.GraphTypeDefinitions.schema`.

---

## Důležité proměnné prostředí

- **DEMO** – `True` / `False`. V True se při startu může dělat drop tabulek a data se berou i ze systemdata; RBAC může používat demo loader.
- **GQLUG_ENDPOINT_URL** – URL GraphQL endpointu služby uživatelů/skupin (pro WhoAmI a federaci).
- **POSTGRES_HOST**, **POSTGRES_USER**, **POSTGRES_PASSWORD**, **POSTGRES_DB** – připojení k DB (nebo **CONNECTION_STRING**).
- **SYSLOGHOST** – volitelně adresa:port pro syslog.
- **TARGET_SERVER** – v proxy složce, kam proxy posílá requesty.

---

## Shrnutí: k čemu je který soubor

- **main.py** – vstup, FastAPI, GraphQL, kontext, endpointy, env.
- **src/DBDefinitions/** – databáze (tabulky, engine, connection string).
- **src/GraphTypeDefinitions/** – GraphQL schéma, query, mutation, typy, RBAC, federace.
- **src/Dataloaders/** – batch loadery pro resolvery.
- **src/Utils/** – klient na jiné GQL API, demo uživatelé/role, explain/query builder.
- **src/DBFeeder.py** – naplnění DB z JSON, záloha.
- **src/error_codes.py** – chybové kódy a zprávy.
- **tests/** – pytest testy a konfigurace.
- **public/** – GraphiQL, Voyager, testovací HTML.
- **docs/** – návody a popisy.
- **proxy/** – HTTP proxy na backend.

Tím máte přehled, jak celý projekt funguje a k čemu slouží jednotlivé soubory a složky.
