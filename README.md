# 🧾 Evidence majetku - GQL Evolution

**Projekt pro správu majetku, inventarizace a zápůjček**

---

## 🚀 Rychlý start

### Spuštění celého stacku

```powershell
docker-compose -f docker-compose.debug.yml up
```

### Přístup k GraphiQL

**👉 http://localhost:33001/graphiql/**

### První kroky

1. Otevři GraphiQL: http://localhost:33001/graphiql/
2. Nastav header:
   ```json
   {"x-demo-user-id": "76dac14f-7114-4bb2-882d-0d762eab6f4a"}
   ```
3. Zkus query:
   ```graphql
   query { who_am_i { email name } }
   ```

**📚 Kompletní průvodce:** [docs/GATEWAY_USAGE.md](docs/GATEWAY_USAGE.md)

---

## 📚 Dokumentace

| Dokument | Popis |
|----------|-------|
| **[docs/GATEWAY_USAGE.md](docs/GATEWAY_USAGE.md)** | ⭐ Kompletní průvodce, začni tady |
| **[docs/GRAPHIQL_CHEATSHEET.md](docs/GRAPHIQL_CHEATSHEET.md)** | ⚡ Rychlé copy-paste queries |
| **[docs/RBAC_GUIDE.md](docs/RBAC_GUIDE.md)** | 🔐 Role a oprávnění |
| **[docs/rbac_examples.py](docs/rbac_examples.py)** | 💡 Příklady kódu |
| **[docs/README.md](docs/README.md)** | 📋 Přehled dokumentace |

---

## 🏗️ Architektura

```
Frontend + GraphiQL (:33001) → Apollo Gateway (:33000) → Subgraphs
                                                          ├─ Evolution (Assets) :8001
                                                          └─ UG (Users/Groups) :8000
```

---

## 🔑 Testovací uživatelé

| Jméno | Role | User ID |
|-------|------|---------|
| Estera Lučková | 👑 Admin | `76dac14f-7114-4bb2-882d-0d762eab6f4a` |
| Ornela Nová | ✏️ Editor | `678a2389-dd49-4d44-88be-28841ae34df1` |
| Dalimil Kovář | 👁️ Viewer | `83981199-2134-4724-badf-cd1f0f38babf` |

---

## 📋 Features

- ✅ CRUD operace pro majetek (assets)
- ✅ Inventarizační záznamy
- ✅ Systém zápůjček
- ✅ RBAC (Role-Based Access Control)
- ✅ Apollo Federation
- ✅ GraphiQL interface
- ✅ Docker Compose deployment

---

## Leden 2026 – Autorizace, lokalizace a federace

### 11. 01. 2026 | Push 4: Removed ProfilingExtension, added GraphiQL UI
- Odstraněn `ProfilingExtension` z `src/GraphTypeDefinitions/__init__.py` (vyvolával chyby `'ProfilingExtension.counter'`).
- Vytvořen `public/graphiql.html` – interaktivní GraphQL explorer.
- Vypnuty debug výpisy a odstraněny chyby související s `ProfilingExtension`.

---

### 11. 01. 2026 | Push 5: Add centralized error code dictionary
- Vytvořen `src/error_codes.py` s UUID-based error kódy (`PERMISSION_DENIED`, `NOT_FOUND`, `VALIDATION_ERROR`, atd.).
- Implementace do všech mutation typů (`Asset`, `AssetLoan`, `AssetInventoryRecord`).
- Přidána funkce `format_error_message()` pro konzistentní chybové zprávy.

---

### 11. 01. 2026 | Push 6: Enhance AI-friendly descriptions
- Rozšířena pole `description` u `AssetGQLModel`, `AssetLoanGQLModel`, `AssetInventoryRecordGQLModel`.
- Doplněna dokumentace typů a případů užití v každém modelu.

---

### 11. 01. 2026 | Push 7: Add /whoami endpoint and GraphiQL user bar
- Přidán GET `/whoami` endpoint v `main.py`.
- Aktualizován `public/graphiql.html`:
  - horní lišta s aktuálním uživatelem
  - editor HTTP hlaviček pro testování `x-demo-user-id`

---

### 11. 01. 2026 | Push 8: Admin-only mutations (assets & inventory)
- Přidány admin-only kontroly do:
  - `asset_insert`, `asset_update`, `asset_delete`
  - `asset_inventory_record_insert`, `asset_inventory_record_update`, `asset_inventory_record_delete`
- Zajišťuje, že pouze admin (Estera) může upravovat majetek a inventarizační záznamy.

---

### 11. 01. 2026 | Push 9: Fix error union constructors
- Opraven návrat error objektů:
  - `entity=None` → `_entity=None`
  - doplněno `_input` a `code=ErrorCodeUUID(...)`
- Zajištěn jednotný formát error union návratových typů.

---

### 11. 01. 2026 | Push 10: Localize error codes and UI to Czech
- Lokalizace `src/error_codes.py`:
  - `PERMISSION_DENIED` → `OPRÁVNĚNÍ_ZAMÍTNUTO`
  - `NOT_FOUND` → `NENALEZENO`
  - `VALIDATION_ERROR` → `VALIDAČNÍ_CHYBA`
  - fallback `UNKNOWN_ERROR` → `NEZNÁMÁ_CHYBA`
- Lokalizace GraphiQL UI a permission hlášek do češtiny.

---

### 11. 01. 2026 | Push 11: whoAmI query & inventory mutations
- Přidáno GraphQL query pole `who_am_i()` (id, email, name, surname).
- Implementovány CRUD mutace pro `AssetInventoryRecord`.
- Všechny mutace vrací union chyby s UUID kódem a českou zprávou.

---

### 11. 01. 2026 | Push 12: Apollo Federation
- Architektura Apollo Federation:
  - Apollo Gateway (port 33001)
  - Asset subgraph (port 8001)
- Federované entity:
  - `Asset`, `AssetLoan`, `AssetInventoryRecord`, `User`, `Group`
- Výsledek: jednotný GraphQL endpoint nad více subgraphy.

---

### 11. 01. 2026 | Push 13: Complete RBAC System + Documentation

**Hlavní změny:**
- ✅ Kompletní **RBAC (Role-Based Access Control)** systém
- ✅ Opraveno načítání `.env` souboru (`override=True`)
- ✅ Rozšířen `permissions.py` o role-based permissions:
  - `RequireAdmin` - pouze administrátor
  - `RequireEditor` - editor nebo admin  
  - `RequireViewer` - viewer nebo vyšší
  - `RequireRole(roles=[...])` - vlastní kombinace
- ✅ Helper funkce pro práci s rolemi:
  - `get_user_roles_from_db()` - načítání rolí z DB
  - `user_has_role()` - kontrola jedné role
  - `user_has_any_role()` - kontrola více rolí
- ✅ Vytvořena kompletní dokumentace:
  - [docs/GATEWAY_USAGE.md](docs/GATEWAY_USAGE.md) - Kompletní průvodce
  - [docs/GRAPHIQL_CHEATSHEET.md](docs/GRAPHIQL_CHEATSHEET.md) - Rychlý cheatsheet
  - [docs/RBAC_GUIDE.md](docs/RBAC_GUIDE.md) - Detailní RBAC průvodce
  - [docs/rbac_examples.py](docs/rbac_examples.py) - 7 příkladů použití
  - [docs/README.md](docs/README.md) - Přehled dokumentace
- ✅ Aktualizován hlavní README s quick start
- ✅ Server nyní správně běží v DEMO módu

**Technické detaily:**
- Oprávnění jsou vázána na **role v databázi**, ne na hardcoded user IDs
- Role: `administrátor`, `editor`, `viewer`, `čtenář`
- Uživatelé získávají oprávnění prostřednictvím přiřazení do rolí (tabulka `roles`)
- Admin by ID (Estera) má vždy všechna oprávnění jako fallback
- Apollo Gateway běží na portu 33000, Frontend na 33001

**Pro práci použijte:** http://localhost:33001/graphiql/

---

## Shrnutí stavu

✅ **RBAC a autorizace**
- Admin (Estera) vidí všechna data.
- Běžní uživatelé vidí pouze svá vlastní.
- Mutace assetů, půjček a inventarizačních záznamů jsou admin-only.
- Dvoustupňová ochrana: `OnlyForAuthentized` + `is_admin_user()`.

---

✅ **Apollo Federation**
- Gateway agreguje více subgraphů (Assets, Events, Credentials).
- Jednotné schéma a jeden GraphQL endpoint.

---

✅ **GraphQL API**
- Typy: `Asset`, `AssetLoan`, `AssetInventoryRecord` (CRUD).
- Query: `whoami`, `who_am_i`.
- REST endpointy: `/whoami`, `/who_am_i_endpoint`.

---

✅ **Chyby a hlášení**
- Centralizovaný UUID-based error dictionary.
- Česky lokalizované zprávy.
- Error union: `msg`, `code`, `_entity`, `_input`.

---

✅ **UX a dokumentace**
- GraphiQL na `/graphiql` (user bar + header editor).
- Voyager schema visualizer na `/voyager`.
- AI-friendly popisy všech typů.

---

✅ **Databáze**
- `DEMO=True`, `DEMODATA=False`.
- PostgreSQL:
  - assets (5432)
  - credentials (5433)
- SQLAlchemy + asyncpg.

---

📋 **Zbývá (optional / nice-to-have)**
- Code coverage report (`pytest --cov`)
- Docker Hub publish
- Advanced vector filters (`VectorResolver`)
