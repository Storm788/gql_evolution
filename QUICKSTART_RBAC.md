# 🚀 Quick Start - Apollo Gateway + RBAC

## Architektura

```
┌─────────────────────────────────────────┐
│  Frontend (hrbolek/frontend)            │
│  http://localhost:33001/                │ ← 🔐 Přihlášení (produkce)
│  http://localhost:33001/graphiql/       │ ← 🎯 GraphiQL (přímý přístup v DEMO)
└────────────────┬────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────┐
│  Apollo Gateway (Federation)            │
│  http://localhost:33000                 │
└────────────┬───────────────┬────────────┘
             │               │
             ▼               ▼
┏━━━━━━━━━━━━━━━━┓    ┏━━━━━━━━━━━━━━━━┓
┃ Evolution      ┃    ┃ UG (Users,     ┃
┃ (Assets)       ┃    ┃  Groups)       ┃
┃ :8001          ┃    ┃ :8000          ┃
┗━━━━━━━━━━━━━━━━┛    ┗━━━━━━━━━━━━━━━━┛
```

## Porty

- **🔐 Frontend (přihlášení)**: http://localhost:33001/
- **🌐 GraphiQL Interface**: http://localhost:33001/graphiql/ **← ZDE PRACUJTE**
- **Apollo Gateway**: http://localhost:33000 (interní)
- **Asset Subgraph**: http://localhost:8001 (interní)
- **User/Group Subgraph**: http://localhost:8000 (interní)

**V DEMO módu** (`DEMO=True` v docker-compose):
- ✅ Můžete jít **přímo** na http://localhost:33001/graphiql/
- ✅ Není potřeba přihlášení (použijte HTTP header `x-demo-user-id`)

**V produkci** (`DEMO=False`):
- 🔐 Musíte se nejdřív **přihlásit** na http://localhost:33001/
- 🍪 Po přihlášení dostanete cookie s JWT tokenem
- ✅ Pak můžete používat GraphiQL na http://localhost:33001/graphiql/

## Spuštění

### Pomocí Docker Compose (DOPORUČENO)

```powershell
cd C:\Škola\Programko\backend\gql_evolution
docker-compose -f docker-compose.debug.yml up
```

To spustí:
- ✅ Frontend s GraphiQL na portu 33001
- ✅ Apollo Gateway na portu 33000
- ✅ Asset subgraph (přes proxy)
- ✅ User/Group subgraph
- ✅ PostgreSQL databáze

### Ruční spuštění (Development)

Pokud chcete spustit jen Asset subgraph pro vývoj:

```powershell
cd C:\Škola\Programko\backend\gql_evolution
.venv\Scripts\Activate.ps1
uvicorn main:app --reload --port 8001
```

Pak můžete testovat přímo na:
- http://localhost:8001/graphiql (přímý přístup k subgraph)

## Práce s GraphiQL na http://localhost:33001/graphiql/

## RBAC (Role-Based Access Control)

### 📋 Definované role

| Role | ID | Oprávnění |
|------|---------|-----------|
| **administrátor** | `ced46aa4-3217-4fc1-b79d-f6be7d21c6b6` | ✅ Všechna oprávnění |
| **editor** | `ed1707aa-0000-4000-8000-000000000001` | ✅ Vytváření, editace |
| **viewer** | `ed1707aa-0000-4000-8000-000000000002` | 👁️ Čtení + základní akce |
| **čtenář** | `ed1707aa-0000-4000-8000-000000000003` | 👁️ Pouze čtení |

### 🔑 Testovací uživatelé

| Jméno | ID | Role | Email |
|-------|------|------|-------|
| **Estera Lučková** | `76dac14f-7114-4bb2-882d-0d762eab6f4a` | Admin (by ID) | estera.luckova@example.com |
| **Ornela Nová** | `678a2389-dd49-4d44-88be-28841ae34df1` | Editor | ornela.nova@example.com |
| **Dalimil Kovář** | `83981199-2134-4724-badf-cd1f0f38babf` | Viewer | dalimil.kovar@example.com |

### 🧪 Testování v GraphiQL na http://localhost:33001/graphiql/

#### 1. Otevři GraphiQL Interface
```
http://localhost:33001/graphiql/
```

#### 2. Nastav user identifikaci

**Možnost A: HTTP Headers** (v GraphiQL editoru vpravo nahoře)
```json
{
  "x-demo-user-id": "76dac14f-7114-4bb2-882d-0d762eab6f4a"
}
```

**Možnost B: Cookie** (nastavené automaticky po přihlášení ve Frontend)
```
demo-user-id=76dac14f-7114-4bb2-882d-0d762eab6f4a
```

**Možnost C: JWT Token** (produkční)
```json
{
  "Authorization": "Bearer YOUR_JWT_TOKEN"
}
```

#### 3. Zkus query
```graphql
query {
  who_am_i {
    id
    email
    name
    surname
  }
}
```

#### 4. Test oprávnění - Admin operace
```graphql
mutation {
  asset_insert(asset: {
    name: "Test Laptop"
    serial_number: "SN-TEST-123"
    asset_type: "Laptop"
  }) {
    ... on AssetGQLModel {
      id
      name
      serial_number
    }
    ... on InsertError {
      msg
      code
    }
  }
}
```

### 📝 Použití v kódu

#### Permission Classes

```python
from src.GraphTypeDefinitions.permissions import (
    RequireAdmin,      # Pouze administrátor
    RequireEditor,     # Editor nebo admin
    RequireViewer,     # Viewer, editor nebo admin
    RequireRole,       # Vlastní role
)

# Admin-only mutation
@strawberry.field(permission_classes=[RequireAdmin])
async def delete_asset(self, info, id: IDType) -> bool:
    # Pouze admin se sem dostane
    ...

# Editor or admin
@strawberry.field(permission_classes=[RequireEditor])
async def update_asset(self, info, asset: AssetInput) -> Asset:
    # Editor nebo admin
    ...

# Vlastní kombinace
@strawberry.field(
    permission_classes=[RequireRole(roles=["specialista", "admin"])]
)
async def special_operation(self, info) -> str:
    ...
```

#### Programová kontrola

```python
from src.GraphTypeDefinitions.permissions import user_has_role, user_has_any_role

@strawberry.field()
async def conditional_field(self, info) -> str:
    user = ensure_user_in_context(info)
    
    # Kontrola jedné role
    if await user_has_role(user, "administrátor", info):
        return "Admin content"
    
    # Kontrola více rolí
    if await user_has_any_role(user, ["editor", "viewer"], info):
        return "Editor/Viewer content"
    
    return "Public content"
```

## 🐛 Troubleshooting

### Problem: 401 Unauthorized

**Řešení:**
1. Zkontroluj, že `DEMO=True` v `.env`
2. Nastav `x-demo-user-id` header nebo `demo-user-id` cookie
3. Restartuj server

### Problem: "Nemáte oprávnění"

**Řešení:**
1. Zkontroluj, jakou roli má user:
   ```sql
   SELECT * FROM roles WHERE user_id='YOUR_USER_ID' AND valid=true;
   ```
2. Přiřaď správnou roli

### Problem: Role se nenačítají

**Řešení:**
1. Zkontroluj DB connection
2. Ověř, že tabulka `roles` existuje
3. Zkontroluj logy: `Warning: Could not load user roles from DB`

## 📚 Dokumentace

- **[RBAC_GUIDE.md](docs/RBAC_GUIDE.md)** - Kompletní průvodce RBAC systémem
- **[rbac_examples.py](docs/rbac_examples.py)** - Příklady použití v kódu
- **[systemdata.combined.json](systemdata.combined.json)** - Data s rolemi

## 🔄 Aktualizace

### Přidání nové role

1. Přidat do `systemdata.combined.json`:
```json
{
  "name": "new_role",
  "name_en": "New Role",
  "id": "YOUR-UUID",
  "category_id": "774690a0-56b3-45d9-9887-0989ed3de4c0"
}
```

2. Aktualizovat `src/GraphTypeDefinitions/permissions.py`:
```python
NEW_ROLE_ID = UUID("YOUR-UUID")
ROLE_NAME_TO_ID["new_role"] = NEW_ROLE_ID
```

### Přiřazení role uživateli

V `systemdata.combined.json`, sekce `"roles"`:
```json
{
  "id": "new-uuid",
  "user_id": "USER_UUID",
  "group_id": "GROUP_UUID",
  "roletype_id": "ROLE_UUID",
  "valid": true,
  "startdate": "2026-01-01 00:00:00",
  "enddate": null
}
```

---

**Vytvořeno:** 11. 1. 2026  
**Poslední update:** Po opravě .env načítání a přidání RBAC systému
