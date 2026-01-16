# 🔐 Role-Based Access Control (RBAC) Guide

## Přehled

Tento projekt používá **RBAC** (Role-Based Access Control) systém, kde:
- **Role** jsou definovány v databázi (např. administrátor, editor, viewer, čtenář)
- **Uživatelé** jsou přiřazeni do rolí prostřednictvím tabulky `roles`
- **Oprávnění** (permissions) jsou vázány na role, ne na jednotlivé uživatele
- **Apollo Gateway** běží na **localhost:33000** (interní)
- **Frontend + GraphiQL** běží na **localhost:33001** ← **ZDE PRACUJTE**
- **Asset subgraph** běží na **localhost:8001** (interní)

## 🎯 Pro práci použijte

**GraphiQL Interface:** http://localhost:33001/graphiql/

Pro detailní návod viz [GATEWAY_USAGE.md](GATEWAY_USAGE.md)

---

## Definované role

Role jsou uloženy v `systemdata.combined.json` a v databázové tabulce `roletypes`:

| Role | UUID | Oprávnění |
|------|------|-----------|
| **administrátor** | `ced46aa4-3217-4fc1-b79d-f6be7d21c6b6` | Všechna oprávnění |
| **editor** | `ed1707aa-0000-4000-8000-000000000001` | Vytváření, editace |
| **viewer** | `ed1707aa-0000-4000-8000-000000000002` | Pouze čtení + základní operace |
| **čtenář** | `ed1707aa-0000-4000-8000-000000000003` | Pouze čtení |

---

## Jak funguje RBAC

### 1. Přiřazení uživatele do role

Uživatelé jsou přiřazeni do rolí prostřednictvím tabulky `roles`:

```json
{
  "id": "77777777-0001-4000-8000-000000000001",
  "group_id": "f2f2d33c-38ee-4f31-9426-f364bc488032",
  "user_id": "76dac14f-7114-4bb2-882d-0d762eab6f4a",
  "roletype_id": "ed1707aa-0000-4000-8000-000000000001",
  "valid": true,
  "startdate": "2025-01-01 00:00:00",
  "enddate": null
}
```

### 2. Kontrola oprávnění

Při každém GraphQL requestu:
1. Server načte uživatele z `user` v kontextu
2. Zavolá `get_user_roles_from_db(user_id, info)` - načte aktivní role z DB
3. Zkontroluje, zda má uživatel požadovanou roli
4. Pokud ano → operace pokračuje, pokud ne → vrátí chybu 401

---

## Permission Classes

### Základní permission classes

```python
from src.GraphTypeDefinitions.permissions import (
    RequireAdmin,      # Pouze administrátor
    RequireEditor,     # Editor nebo administrátor
    RequireViewer,     # Viewer, editor nebo administrátor
    RequireRole,       # Vlastní seznam rolí
)
```

### Použití v GraphQL schema

#### Příklad 1: Admin-only mutation

```python
@strawberry.field(
    description="Smazat asset (pouze admin)",
    permission_classes=[RequireAdmin]
)
async def asset_delete(
    self, info: strawberry.types.Info, asset: AssetDeleteGQLModel
) -> typing.Union[AssetGQLModel, AssetDeleteErrorType]:
    # Pokud user nemá admin roli, nikdy se sem nedostane
    result = await Delete[AssetGQLModel].DoItSafeWay(info=info, entity=asset)
    return result
```

#### Příklad 2: Editor or higher

```python
@strawberry.field(
    description="Upravit asset (editor nebo admin)",
    permission_classes=[RequireEditor]
)
async def asset_update(
    self, info: strawberry.types.Info, asset: AssetUpdateGQLModel
) -> typing.Union[AssetGQLModel, AssetUpdateErrorType]:
    result = await Update[AssetGQLModel].DoItSafeWay(info=info, entity=asset)
    return result
```

#### Příklad 3: Vlastní kombinace rolí

```python
from src.GraphTypeDefinitions.permissions import RequireRole

@strawberry.field(
    description="Speciální operace pro planning admin",
    permission_classes=[RequireRole(roles=["plánovací administrátor", "administrátor"])]
)
async def special_operation(self, info: strawberry.types.Info) -> str:
    return "Success"
```

#### Příklad 4: Programová kontrola role uvnitř resolveru

```python
from src.GraphTypeDefinitions.permissions import user_has_role, user_has_any_role

@strawberry.field(description="Dynamická kontrola role")
async def conditional_access(self, info: strawberry.types.Info) -> str:
    user = ensure_user_in_context(info)
    
    # Kontrola jedné role
    if await user_has_role(user, "administrátor", info):
        return "Admin access"
    
    # Kontrola více rolí
    if await user_has_any_role(user, ["editor", "viewer"], info):
        return "Editor/Viewer access"
    
    return "No access"
```

---

## Helper funkce

### `get_user_roles_from_db(user_id, info)`

Načte všechny aktivní role uživatele z databáze.

```python
from src.GraphTypeDefinitions.permissions import get_user_roles_from_db

user_id = UUID("76dac14f-7114-4bb2-882d-0d762eab6f4a")
roles = await get_user_roles_from_db(user_id, info)
# Returns: {UUID("ed1707aa-0000-4000-8000-000000000001"), ...}
```

### `user_has_role(user, role_name, info)`

Zkontroluje, zda má uživatel konkrétní roli.

```python
from src.GraphTypeDefinitions.permissions import user_has_role

has_admin = await user_has_role(user, "administrátor", info)
```

### `user_has_any_role(user, role_names, info)`

Zkontroluje, zda má uživatel alespoň jednu z daných rolí.

```python
from src.GraphTypeDefinitions.permissions import user_has_any_role

can_edit = await user_has_any_role(user, ["administrátor", "editor"], info)
```

---

## Příklady použití

### Asset Management

| Operace | Požadovaná role |
|---------|----------------|
| Vytvoření assetu | **administrátor** |
| Editace assetu | **administrátor** |
| Smazání assetu | **administrátor** |
| Zobrazení assetu | **viewer** nebo vyšší |
| Seznam assetů | **viewer** nebo vyšší |

### Asset Loans (Zápůjčky)

| Operace | Požadovaná role |
|---------|----------------|
| Vytvoření zápůjčky (vlastní) | **authentizovaný uživatel** |
| Editace zápůjčky (vlastní) | **vlastník zápůjčky** nebo **admin** |
| Smazání zápůjčky | **administrátor** |
| Zobrazení zápůjček (všech) | **administrátor** |
| Zobrazení vlastních zápůjček | **vlastník** |

---

## Testování RBAC

### 1. Nastavení testovacího uživatele

V Apollo Studio nebo GraphiQL nastavte HTTP hlavičku:

```json
{
  "x-demo-user-id": "76dac14f-7114-4bb2-882d-0d762eab6f4a"
}
```

Nebo cookie:
```
demo-user-id=76dac14f-7114-4bb2-882d-0d762eab6f4a
```

### 2. Ověření aktuálního uživatele

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

### 3. Test oprávnění

```graphql
# Admin-only operace (mělo by fungovat jen pro Estera)
mutation {
  asset_insert(asset: {
    name: "Testovací laptop"
    serial_number: "SN123456"
    asset_type: "Laptop"
  }) {
    ... on AssetGQLModel {
      id
      name
    }
    ... on InsertError {
      msg
      code
    }
  }
}
```

---

## Přidání nové role

### 1. Přidat do systemdata.combined.json

```json
{
  "_chunk": 0,
  "name": "custom_role",
  "name_en": "Custom Role",
  "id": "YOUR-NEW-UUID-HERE",
  "category_id": "774690a0-56b3-45d9-9887-0989ed3de4c0"
}
```

### 2. Aktualizovat permissions.py

```python
CUSTOM_ROLE_ID = UUID("YOUR-NEW-UUID-HERE")

ROLE_NAME_TO_ID = {
    # ...existing...
    "custom_role": CUSTOM_ROLE_ID,
}
```

### 3. Vytvořit permission class (volitelné)

```python
class RequireCustomRole(BasePermission):
    message = "Vyžadována role: Custom Role"
    
    async def has_permission(self, source, info: strawberry.types.Info, **kwargs) -> bool:
        user = ensure_user_in_context(info)
        if not user:
            return False
        return await user_has_role(user, "custom_role", info)
```

---

## Přiřazení uživatele do role

### Přes GraphQL mutation (pokud implementováno)

```graphql
mutation {
  role_assign(
    user_id: "USER_UUID"
    group_id: "GROUP_UUID"
    roletype_id: "ROLE_UUID"
  ) {
    id
    user_id
    roletype_id
  }
}
```

### Přes SQL (development)

```sql
INSERT INTO roles (id, user_id, group_id, roletype_id, valid, startdate, enddate)
VALUES (
  gen_random_uuid(),
  '76dac14f-7114-4bb2-882d-0d762eab6f4a',  -- user_id
  'f2f2d33c-38ee-4f31-9426-f364bc488032',  -- group_id
  'ced46aa4-3217-4fc1-b79d-f6be7d21c6b6',  -- roletype_id (admin)
  true,
  NOW(),
  NULL
);
```

### Přes systemdata.combined.json

Přidat do sekce `"roles"`:

```json
{
  "id": "NEW-ROLE-ASSIGNMENT-UUID",
  "created": "2026-01-11T00:00:00.000000",
  "lastchange": "2026-01-11T00:00:00.000000",
  "group_id": "GROUP_UUID",
  "user_id": "USER_UUID",
  "valid": true,
  "startdate": "2026-01-01 00:00:00",
  "enddate": null,
  "roletype_id": "ROLE_TYPE_UUID"
}
```

---

## Troubleshooting

### Problem: 401 Unauthorized

**Příčina:** Uživatel není autentizován nebo nemá správnou roli.

**Řešení:**
1. Ověřte, že máte nastavený `x-demo-user-id` header nebo `demo-user-id` cookie
2. Zkontrolujte, že `DEMO=True` v `.env`
3. Zkontrolujte logy serveru pro debug výpisy

### Problem: "Nemáte oprávnění"

**Příčina:** Uživatel nemá požadovanou roli.

**Řešení:**
1. Zkontrolujte, jakou roli má uživatel: `SELECT * FROM roles WHERE user_id='YOUR_ID'`
2. Zkontrolujte, že role je `valid=true` a v platném časovém rozmezí
3. Přiřaďte uživateli správnou roli

### Problem: Role se nenačítají z DB

**Příčina:** Chyba v SQL dotazu nebo připojení k DB.

**Řešení:**
1. Zkontrolujte logy: `Warning: Could not load user roles from DB`
2. Ověřte DB connection string
3. Zkontrolujte, že tabulka `roles` existuje

---

## Best Practices

1. **Vždy používejte role místo hardcoded user IDs**
   ```python
   # ❌ Špatně
   if user.get("id") == SPECIFIC_USER_ID:
   
   # ✅ Správně
   if await user_has_role(user, "administrátor", info):
   ```

2. **Používejte permission_classes na field/mutation level**
   ```python
   # ✅ Preferovaný způsob
   @strawberry.field(permission_classes=[RequireAdmin])
   async def admin_field(...):
   ```

3. **Pro dynamické kontroly používejte helper funkce**
   ```python
   # ✅ Pro složitější logiku
   if await user_has_any_role(user, ["admin", "editor"], info):
   ```

4. **Admin by ID (Estera) má vždy přístup**
   - `is_admin_user()` kontroluje konkrétní admin ID
   - Všechny permission classes respektují tento fallback

---

## Odkazy

- [Apollo Federation Docs](https://www.apollographql.com/docs/federation/)
- [Strawberry GraphQL Permissions](https://strawberry.rocks/docs/guides/permissions)
- [systemdata.combined.json](../systemdata.combined.json) - Definice rolí a přiřazení

---

**Vytvořeno:** 11. 1. 2026  
**Verze:** 1.0  
**Autor:** GQL Evolution Team
