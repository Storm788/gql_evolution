# 🎯 GraphiQL Cheatsheet - http://localhost:33001/graphiql/

## 🚪 Přístup

### V DEMO módu (výchozí nastavení)
Jděte přímo na: **http://localhost:33001/graphiql/**
- ✅ Není potřeba přihlášení
- ✅ Nastavte jen HTTP header s `x-demo-user-id`

### V produkci
1. Nejdřív se přihlaste na: **http://localhost:33001/**
2. Po přihlášení dostanete cookie s JWT tokenem
3. Pak jděte na: **http://localhost:33001/graphiql/**

---

## ⚡ Rychlý start (3 kroky)

### 1️⃣ Nastav autentizaci
V GraphiQL klikni na **"Headers"** → přidej:
```json
{"x-demo-user-id": "76dac14f-7114-4bb2-882d-0d762eab6f4a"}
```

### 2️⃣ Zkus první query
```graphql
query { who_am_i { email name } }
```

### 3️⃣ Hotovo! 🎉

---

## 📋 Copy-Paste Queries

### Kdo jsem?
```graphql
query { who_am_i { id email name surname } }
```

### Seznam assetů
```graphql
query {
  asset_page(limit: 10) {
    id name serial_number asset_type status
  }
}
```

### Detail assetu
```graphql
query AssetDetail($id: UUID!) {
  asset_by_id(id: $id) {
    id name serial_number description status
    custodian_user { id }
    loans { id startdate enddate borrower_user_email }
  }
}
# Variables: {"id": "PASTE_UUID_HERE"}
```

### Moje zápůjčky
```graphql
query {
  asset_loan_page(limit: 10) {
    id startdate enddate returned_date
    borrower_user_email
    asset { id name }
  }
}
```

---

## ✏️ Copy-Paste Mutations

### Vytvoř asset (admin only)
```graphql
mutation {
  asset_insert(asset: {
    name: "MacBook Pro 16"
    serial_number: "SN-001"
    asset_type: "Laptop"
    status: "Aktivní"
  }) {
    ... on AssetGQLModel { id name }
    ... on InsertError { msg code }
  }
}
```

### Vytvoř zápůjčku
```graphql
mutation CreateLoan($assetId: UUID!) {
  asset_loan_insert(loan: {
    asset_id: $assetId
    startdate: "2026-01-11T00:00:00"
    enddate: "2026-01-18T00:00:00"
    note: "Projekt"
  }) {
    ... on AssetLoanGQLModel { id }
    ... on InsertError { msg }
  }
}
# Variables: {"assetId": "PASTE_UUID_HERE"}
```

### Vrať zápůjčku
```graphql
mutation ReturnLoan($loanId: UUID!) {
  asset_loan_update(loan: {
    id: $loanId
    returned_date: "2026-01-11T10:00:00"
  }) {
    ... on AssetLoanGQLModel { id returned_date }
    ... on UpdateError { msg }
  }
}
# Variables: {"loanId": "PASTE_UUID_HERE"}
```

---

## 🔑 Testovací uživatelé (Headers)

### Admin - Estera
```json
{"x-demo-user-id": "76dac14f-7114-4bb2-882d-0d762eab6f4a"}
```
✅ Může všechno

### Editor - Ornela  
```json
{"x-demo-user-id": "678a2389-dd49-4d44-88be-28841ae34df1"}
```
✅ Vytváření zápůjček  
❌ Správa assetů

### Viewer - Dalimil
```json
{"x-demo-user-id": "83981199-2134-4724-badf-cd1f0f38babf"}
```
✅ Čtení  
❌ Zápis

---

## 🎨 GraphiQL Tips

### Autocomplete
Začni psát a stiskni **Ctrl+Space**

### Dokumentace
Klikni na **"< Docs"** vpravo

### Historie
Klikni na **hodiny** v levém panelu

### Prettify
Klikni na **"Prettify"** nebo stiskni **Shift+Ctrl+P**

### Spusť query
**Ctrl+Enter** nebo klikni ▶️

---

## ❌ Časté chyby

### "Failed to fetch"
→ Zkontroluj, že Docker běží: `docker-compose ps`

### "401 Unauthorized"
→ Přidej header `x-demo-user-id`

### "Nemáte oprávnění"
→ Použij admin user ID (Estera)

### Field vrací `null`
→ Možná nemáš oprávnění na to pole  
→ Zkontroluj permission_classes

---

## 🚀 Pro pokročilé

### Fragmenty
```graphql
fragment AssetBasic on AssetGQLModel {
  id name serial_number
}

query {
  asset_page { ...AssetBasic }
}
```

### Variables
```graphql
query GetAsset($id: UUID!, $includeLoans: Boolean = false) {
  asset_by_id(id: $id) {
    name
    loans @include(if: $includeLoans) { id }
  }
}
```

### Aliases
```graphql
query {
  recent: asset_page(limit: 5)
  all: asset_page(limit: 100)
}
```

---

**URL:** http://localhost:33001/graphiql/  
**Full docs:** [GATEWAY_USAGE.md](GATEWAY_USAGE.md)
