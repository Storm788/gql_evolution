# 👥 Přehled uživatelů a rolí v systému

## 📊 Statistika

- **Celkem uživatelů**: 1720
- **Celkem typů rolí**: 19
- **Aktivních přiřazení**: 110

---

## 🎭 Hlavní role pro testování Assets

### 👑 ADMINISTRÁTOŘI (5 uživatelů)

Role: **administrator** (`ced46aa4-3217-4fc1-b79d-f6be7d21c6b6`)  
Oprávnění: ✅ Všechna oprávnění (CRUD na assets, inventory, loans)

| # | Jméno | Email | User ID |
|---|-------|-------|---------|
| 1 | **Zdeňka Šimečková** | Zdenka.Simeckova@world.com | `51d101a0-81f1-44ca-8366-6cf51432e8d6` |
| 2 | **Ornela Kucková** | Ornela.Kuckova@world.com | `678a2389-dd49-4d44-88be-28841ae34df1` |
| 3 | **Valentin Křenek** | Valentin.Krenek@world.com | `35176143-7a86-4ce0-a611-c5824d750f66` |
| 4 | **Ludvík Kilik** | Ludvik.Kilik@world.com | `a0506cc4-5d53-4fdb-a989-c06a97e527fd` |

**Použití v GraphiQL:**
```json
{
  "x-demo-user-id": "678a2389-dd49-4d44-88be-28841ae34df1"
}
```

---

### ✏️ EDITORI (2 uživatelé)

Role: **editor** (`ed1707aa-0000-4000-8000-000000000001`)  
Oprávnění: ✅ Vytváření zápůjček, ✅ Čtení assets, ❌ Správa assets/inventory

| # | Jméno | Email | User ID |
|---|-------|-------|---------|
| 1 | **Estera Lučková** | Estera.Luckova@world.com | `76dac14f-7114-4bb2-882d-0d762eab6f4a` |
| 2 | **Radomil Svěrek** | Radomil.Sverek@world.com | `0cd6cd48-1b42-499a-83c8-aaefd7c741a3` |

**Poznámka:** Estera je také **hardcoded admin** (má všechna oprávnění i bez admin role)!

**Použití v GraphiQL:**
```json
{
  "x-demo-user-id": "0cd6cd48-1b42-499a-83c8-aaefd7c741a3"
}
```

---

### 👁️ VIEWEŘI (2 uživatelé)

Role: **viewer** (`ed1707aa-0000-4000-8000-000000000002`)  
Oprávnění: 👁️ Pouze čtení, ❌ Žádné zápisy

| # | Jméno | Email | User ID |
|---|-------|-------|---------|
| 1 | **Oliver Hortík** | Oliver.Hortik@world.com | `6a6ca6e9-2222-498f-b270-b7b07c2afa41` |
| 2 | **Jitka Kloučková** | Jitka.Klouckova@world.com | `3ca2c2cf-28bc-4855-8936-3bafe8c94b7c` |

**Použití v GraphiQL:**
```json
{
  "x-demo-user-id": "6a6ca6e9-2222-498f-b270-b7b07c2afa41"
}
```

---

### 📖 ČTENÁŘI (0 uživatelů)

Role: **reader** (`ed1707aa-0000-4000-8000-000000000003`)  
Oprávnění: 👁️ Čtení základních informací

**Zatím nepřiřazeno žádnému uživateli.**

---

## 🎯 Doporučení pro testování

### Scénář 1: Admin operace
**User:** Ornela Kucková (admin)
```json
{"x-demo-user-id": "678a2389-dd49-4d44-88be-28841ae34df1"}
```

**Test:**
```graphql
mutation {
  asset_insert(asset: {
    name: "Test MacBook"
    serial_number: "SN-TEST-001"
    asset_type: "Laptop"
  }) {
    ... on AssetGQLModel { id name }
    ... on InsertError { msg }
  }
}
```
**Očekávaný výsledek:** ✅ Úspěch

---

### Scénář 2: Editor pokus vytvořit asset
**User:** Radomil Svěrek (editor)
```json
{"x-demo-user-id": "0cd6cd48-1b42-499a-83c8-aaefd7c741a3"}
```

**Test:**
```graphql
mutation {
  asset_insert(asset: {
    name: "Test MacBook"
    serial_number: "SN-TEST-002"
    asset_type: "Laptop"
  }) {
    ... on AssetGQLModel { id name }
    ... on InsertError { msg code }
  }
}
```
**Očekávaný výsledek:** ❌ Chyba oprávnění

---

### Scénář 3: Editor vytváří zápůjčku
**User:** Radomil Svěrek (editor)
```json
{"x-demo-user-id": "0cd6cd48-1b42-499a-83c8-aaefd7c741a3"}
```

**Test:**
```graphql
mutation {
  asset_loan_insert(loan: {
    asset_id: "NĚJAKÝ_ASSET_ID"
    startdate: "2026-01-11T00:00:00"
    note: "Potřebuji na projekt"
  }) {
    ... on AssetLoanGQLModel { id }
    ... on InsertError { msg }
  }
}
```
**Očekávaný výsledek:** ✅ Úspěch (může vytvořit zápůjčku pro sebe)

---

### Scénář 4: Viewer jen čte
**User:** Oliver Hortík (viewer)
```json
{"x-demo-user-id": "6a6ca6e9-2222-498f-b270-b7b07c2afa41"}
```

**Test:**
```graphql
query {
  asset_page(limit: 5) {
    id
    name
    serial_number
  }
}
```
**Očekávaný výsledek:** ✅ Vidí data

**Test zápisu:**
```graphql
mutation {
  asset_loan_insert(loan: {
    asset_id: "NĚJAKÝ_ASSET_ID"
    startdate: "2026-01-11T00:00:00"
  }) {
    ... on AssetLoanGQLModel { id }
    ... on InsertError { msg }
  }
}
```
**Očekávaný výsledek:** ❌ Chyba oprávnění (viewer nemůže vytvářet zápůjčky)

---

## 🏢 Ostatní role v systému

V databázi je celkem **19 typů rolí**. Mimo základní (admin, editor, viewer) máte akademické role:

| Role | Počet uživatelů |
|------|-----------------|
| **head of department** (vedoucí katedry) | 49 |
| **vicedean** (proděkan) | 21 |
| **dean** (děkan) | 7 |
| **grant** (garant) | 7 |
| **grant (deputy)** (zástupce garanta) | 7 |
| **vicerector** (prorektor) | 4 |
| **Správce areálu** | 4 |
| **rector** (rektor) | ? |
| **lecturer** (přednášející) | ? |
| **trainer** (cvičící) | ? |
| **gdpr user** (zpracovatel gdpr) | ? |

**Poznámka:** Tyto akademické role zatím nemají definovaná oprávnění v Asset management systému. Pokud je chcete používat, přidejte je do permission systému v `permissions.py`.

---

## 🔧 Jak změnit role uživatele?

### Možnost 1: Editace systemdata.combined.json

Najděte sekci `"roles"` a přidejte nové přiřazení:

```json
{
  "id": "new-uuid-here",
  "created": "2026-01-11T00:00:00",
  "lastchange": "2026-01-11T00:00:00",
  "group_id": "f2f2d33c-38ee-4f31-9426-f364bc488032",
  "user_id": "USER_UUID",
  "valid": true,
  "startdate": "2026-01-01 00:00:00",
  "enddate": null,
  "roletype_id": "ced46aa4-3217-4fc1-b79d-f6be7d21c6b6"
}
```

Pak restartujte server (v DEMO módu se data znovu načtou).

### Možnost 2: SQL příkaz

```sql
INSERT INTO roles (id, user_id, group_id, roletype_id, valid, startdate, createdby_id, changedby_id)
VALUES (
  gen_random_uuid(),
  'USER_UUID',
  'GROUP_UUID',
  'ced46aa4-3217-4fc1-b79d-f6be7d21c6b6',  -- admin role
  true,
  NOW(),
  'ADMIN_USER_UUID',
  'ADMIN_USER_UUID'
);
```

---

## 📌 Quick Reference

### Kopírovat do GraphiQL Headers:

```json
// Admin - Ornela
{"x-demo-user-id": "678a2389-dd49-4d44-88be-28841ae34df1"}

// Editor - Radomil
{"x-demo-user-id": "0cd6cd48-1b42-499a-83c8-aaefd7c741a3"}

// Viewer - Oliver
{"x-demo-user-id": "6a6ca6e9-2222-498f-b270-b7b07c2afa41"}

// Super Admin - Estera (hardcoded)
{"x-demo-user-id": "76dac14f-7114-4bb2-882d-0d762eab6f4a"}
```

---

**Vytvořeno:** 11. 1. 2026  
**Zdroj dat:** systemdata.combined.json  
**Script:** [show_users_roles.py](show_users_roles.py)
