# 🎯 Práce s Apollo Gateway na http://localhost:33001/graphiql/

## Rychlý start

### 1. Spusť Docker Compose

```powershell
cd C:\Škola\Programko\backend\gql_evolution
docker-compose -f docker-compose.debug.yml up
```

Počkej, až uvidíš:
```
✓ apollo running
✓ frontend running
✓ gql_ug running
✓ proxy running
```

### 2. Přístup k aplikaci

**Frontend poskytuje:**
- 🔐 **Přihlášení**: http://localhost:33001/ (hlavní stránka s loginflow)
- 🔍 **GraphiQL**: http://localhost:33001/graphiql/ (přímý přístup bez přihlášení v DEMO módu)

**Poznámka:** V DEMO módu (`DEMO=True`) můžete jít přímo na GraphiQL bez přihlášení. V produkci byste se museli nejdřív přihlásit na hlavní stránce.

---

## Autentizace v GraphiQL

### Option 1: Demo User ID (nejjednodušší)

V GraphiQL klikni na **"Headers"** (vpravo nahoře) a přidej:

```json
{
  "x-demo-user-id": "76dac14f-7114-4bb2-882d-0d762eab6f4a"
}
```

### Option 2: Cookie (automaticky po přihlášení)

Frontend automaticky nastaví cookie po přihlášení, takže nemusíte nic dělat.

---

## Testovací queries

### 1️⃣ Zjisti, kdo jsi

```graphql
query WhoAmI {
  who_am_i {
    id
    email
    name
    surname
  }
}
```

**Výstup:**
```json
{
  "data": {
    "who_am_i": {
      "id": "76dac14f-7114-4bb2-882d-0d762eab6f4a",
      "email": "estera.luckova@example.com",
      "name": "Estera",
      "surname": "Lučková"
    }
  }
}
```

---

### 2️⃣ Seznam všech assetů

```graphql
query AllAssets {
  asset_page(skip: 0, limit: 10) {
    id
    name
    serial_number
    asset_type
    status
    purchase_date
    custodian_user {
      id
      # Toto pole přijde z User subgraph (federace!)
    }
  }
}
```

---

### 3️⃣ Detail konkrétního assetu

```graphql
query AssetDetail($id: UUID!) {
  asset_by_id(id: $id) {
    id
    name
    serial_number
    asset_type
    description
    status
    purchase_date
    purchase_price
    warranty_end
    location
    notes
    
    # Vlastník z User subgraph (federace)
    custodian_user {
      id
    }
    
    # Inventarizační záznamy
    inventory_records {
      id
      check_date
      condition
      notes
      checked_by_user {
        id
      }
    }
    
    # Zápůjčky
    loans {
      id
      startdate
      enddate
      returned_date
      note
      borrower_user {
        id
      }
    }
  }
}
```

**Variables:**
```json
{
  "id": "ASSET_UUID_HERE"
}
```

---

### 4️⃣ Moje zápůjčky

```graphql
query MyLoans {
  asset_loan_page(skip: 0, limit: 10) {
    id
    startdate
    enddate
    returned_date
    note
    borrower_user_email
    borrower_user_fullname
    asset {
      id
      name
      serial_number
      asset_type
    }
  }
}
```

---

## Testovací mutations (pouze Admin)

### 5️⃣ Vytvoř nový asset

```graphql
mutation CreateAsset {
  asset_insert(asset: {
    name: "MacBook Pro 16"
    serial_number: "SN-MBP-2026-001"
    asset_type: "Laptop"
    description: "M4 Max, 64GB RAM"
    status: "Aktivní"
    purchase_date: "2026-01-11T00:00:00"
    purchase_price: 89999.0
    warranty_end: "2029-01-11T00:00:00"
    location: "Kancelář 205"
  }) {
    ... on AssetGQLModel {
      id
      name
      serial_number
      created
    }
    ... on InsertError {
      msg
      code
    }
  }
}
```

**Očekávaný výstup (jako admin):**
```json
{
  "data": {
    "asset_insert": {
      "id": "new-uuid-here",
      "name": "MacBook Pro 16",
      "serial_number": "SN-MBP-2026-001",
      "created": "2026-01-11T08:30:00"
    }
  }
}
```

**Očekávaný výstup (ne-admin):**
```json
{
  "data": {
    "asset_insert": {
      "msg": "OPRÁVNĚNÍ_ZAMÍTNUTO: Nemáte oprávnění provést tuto operaci",
      "code": "4a8b2c3d-5e6f-4b7c-9d0e-1f2a3b4c5d6e"
    }
  }
}
```

---

### 6️⃣ Vytvoř zápůjčku (každý autentizovaný uživatel)

```graphql
mutation CreateLoan {
  asset_loan_insert(loan: {
    asset_id: "ASSET_UUID_HERE"
    startdate: "2026-01-11T00:00:00"
    enddate: "2026-01-18T00:00:00"
    note: "Potřebuji na projekt"
  }) {
    ... on AssetLoanGQLModel {
      id
      startdate
      enddate
      note
      borrower_user_email
      asset {
        id
        name
      }
    }
    ... on InsertError {
      msg
      code
    }
  }
}
```

---

### 7️⃣ Vrať zápůjčku

```graphql
mutation ReturnLoan {
  asset_loan_update(loan: {
    id: "LOAN_UUID_HERE"
    returned_date: "2026-01-11T10:00:00"
  }) {
    ... on AssetLoanGQLModel {
      id
      returned_date
    }
    ... on UpdateError {
      msg
      code
    }
  }
}
```

---

### 8️⃣ Inventarizace (admin only)

```graphql
mutation CreateInventoryRecord {
  asset_inventory_record_insert(record: {
    asset_id: "ASSET_UUID_HERE"
    check_date: "2026-01-11T00:00:00"
    condition: "Dobrý"
    notes: "Kontrola provedena"
  }) {
    ... on AssetInventoryRecordGQLModel {
      id
      check_date
      condition
      notes
    }
    ... on InsertError {
      msg
      code
    }
  }
}
```

---

## Testování oprávnění

### Test 1: Admin operace

**Nastav header:**
```json
{
  "x-demo-user-id": "76dac14f-7114-4bb2-882d-0d762eab6f4a"
}
```

**Zkus vytvořit asset** (mělo by fungovat ✅)

---

### Test 2: Ne-admin operace

**Změň header na jiného uživatele:**
```json
{
  "x-demo-user-id": "678a2389-dd49-4d44-88be-28841ae34df1"
}
```

**Zkus vytvořit asset** (mělo selhat ❌ s chybou oprávnění)

---

### Test 3: Vlastní zápůjčky

Každý uživatel může:
- ✅ Vytvořit zápůjčku pro sebe
- ✅ Zobrazit své zápůjčky
- ❌ Zobrazit cizí zápůjčky (vidí jen admin)

---

## Testovací uživatelé

| Jméno | User ID | Role | Email |
|-------|---------|------|-------|
| **Estera Lučková** | `76dac14f-7114-4bb2-882d-0d762eab6f4a` | 👑 Admin | estera.luckova@example.com |
| **Ornela Nová** | `678a2389-dd49-4d44-88be-28841ae34df1` | ✏️ Editor | ornela.nova@example.com |
| **Dalimil Kovář** | `83981199-2134-4724-badf-cd1f0f38babf` | 👁️ Viewer | dalimil.kovar@example.com |

---

## Federace v praxi

Apollo Gateway spojuje dvě služby:

### Evolution Subgraph (Assets) - port 8001
```graphql
type AssetGQLModel @key(fields: "id") {
  id: UUID!
  name: String
  custodian_user_id: UUID  # ← Toto je jen ID
  custodian_user: UserGQLModel  # ← Resolver to rozšíří na celý objekt
}
```

### UG Subgraph (Users/Groups) - port 8000
```graphql
type UserGQLModel @key(fields: "id") {
  id: UUID!
  email: String
  name: String
  surname: String
}
```

### Výsledek v Gateway
```graphql
query {
  asset_by_id(id: "...") {
    name
    custodian_user {  # ← Gateway automaticky spojí data
      email         # ← Toto přijde z UG subgraph
      name
    }
  }
}
```

---

## Troubleshooting

### ❌ Problem: "Failed to fetch"

**Řešení:**
1. Zkontroluj, že Docker Compose běží: `docker-compose ps`
2. Zkontroluj logy: `docker-compose logs frontend`
3. Zkontroluj, že všechny služby jsou "healthy"

### ❌ Problem: "401 Unauthorized" 

**Řešení:**
1. Přidej header `x-demo-user-id` v GraphiQL
2. Zkontroluj, že DEMO=True v environment

### ❌ Problem: "Nemáte oprávnění"

**Řešení:**
1. Zkontroluj, že používáš správný user ID
2. Pro admin operace použij Estera ID: `76dac14f-7114-4bb2-882d-0d762eab6f4a`
3. Zkontroluj role v DB: `SELECT * FROM roles WHERE user_id='YOUR_ID'`

### ❌ Problem: Federated pole vrací null

**Příklad:**
```graphql
query {
  asset_by_id(id: "...") {
    custodian_user {
      email  # ← vrací null
    }
  }
}
```

**Řešení:**
1. Zkontroluj, že UG subgraph běží
2. Zkontroluj Apollo Gateway logy: `docker-compose logs apollo`
3. Ověř, že `custodian_user_id` existuje v Asset

---

## Pro rychlé testování

Zkopíruj celý tento blok do GraphiQL a spusť (Ctrl+Enter):

```graphql
# 1. Zjisti, kdo jsi
query WhoAmI {
  who_am_i {
    id
    email
    name
  }
}

# 2. Seznam assetů
query Assets {
  asset_page(limit: 5) {
    id
    name
    serial_number
  }
}

# 3. Moje zápůjčky
query MyLoans {
  asset_loan_page(limit: 5) {
    id
    startdate
    borrower_user_email
    asset {
      name
    }
  }
}
```

---

**URL:** http://localhost:33001/graphiql/  
**Dokumentace:** [RBAC_GUIDE.md](RBAC_GUIDE.md)  
**Vytvořeno:** 11. 1. 2026
