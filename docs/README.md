# 📚 Dokumentace

## 🚀 Rychlý start

### Pro práci použijte Apollo Gateway

**GraphiQL Interface:** http://localhost:33001/graphiql/

**Kompletní průvodce:** [GATEWAY_USAGE.md](GATEWAY_USAGE.md)

---

## 📄 Dostupné dokumenty

### 1. [GATEWAY_USAGE.md](GATEWAY_USAGE.md) ⭐ START HERE
**Kompletní průvodce prací s Apollo Gateway**
- Jak spustit Docker Compose
- Autentizace v GraphiQL
- Testovací queries a mutations
- Příklady pro všechny operace
- Troubleshooting

**Použijte tento dokument pro:**
- První kroky s projektem
- Testování v GraphiQL na http://localhost:33001/graphiql/
- Příklady GraphQL queries
- Řešení běžných problémů

---

### 2. [USERS_AND_ROLES.md](USERS_AND_ROLES.md) 👥 NEW!
**Přehled všech uživatelů a jejich rolí**
- Kdo má roli administrátora (5 uživatelů)
- Kdo jsou editori (2 uživatelé)
- Kdo jsou vieweři (2 uživatelé)
- Testovací scénáře pro každou roli
- Quick reference s user IDs

**Použijte tento dokument pro:**
- Zjištění, kdo má jakou roli
- Kopírování user IDs pro testování
- Porozumění rozsahu oprávnění
- Plánování testovacích scénářů

---

### 3. [RBAC_GUIDE.md](RBAC_GUIDE.md) 🔐
**Detailní průvodce RBAC systémem**
- Jak fungují role a oprávnění
- Definované role (admin, editor, viewer, čtenář)
- Permission classes (`RequireAdmin`, `RequireEditor`, atd.)
- Helper funkce (`user_has_role`, `user_has_any_role`)
- Přidání nové role
- Přiřazení uživatele do role
- Best practices

**Použijte tento dokument pro:**
- Pochopení permission systému
- Implementaci nových oprávnění
- Debugging autorizačních problémů
- Rozšíření rolí

---

### 4. [rbac_examples.py](rbac_examples.py) 💡
**Příklady implementace RBAC v kódu**
- 7 různých způsobů použití permissions
- Admin-only mutations
- Field-level permissions
- Dynamická kontrola rolí
- Vlastní permission classes
- Best practices vs anti-patterns

**Použijte tento dokument pro:**
- Copy-paste příklady do vašeho kódu
- Inspiraci pro implementaci permissions
- Naučení se správných patterns

---

## 🎯 Které dokumenty potřebuji?

### Jsem nový v projektu
→ Start: [GATEWAY_USAGE.md](GATEWAY_USAGE.md)
→ Pak: [RBAC_GUIDE.md](RBAC_GUIDE.md)

### Chci testovat GraphQL queries
→ [GATEWAY_USAGE.md](GATEWAY_USAGE.md) - sekce "Testovací queries"

### Implementuji nové mutations s permissions
→ [rbac_examples.py](rbac_examples.py) - copy-paste příklady
→ [RBAC_GUIDE.md](RBAC_GUIDE.md) - teorie

### Mám problém s autorizací
→ [GATEWAY_USAGE.md](GATEWAY_USAGE.md) - Troubleshooting
→ [RBAC_GUIDE.md](RBAC_GUIDE.md) - Troubleshooting

### Chci přidat novou roli
→ [RBAC_GUIDE.md](RBAC_GUIDE.md) - sekce "Přidání nové role"

### Debuguji federované queries
→ [GATEWAY_USAGE.md](GATEWAY_USAGE.md) - sekce "Federace v praxi"

---

## 🏗️ Architektura

```
┌─────────────────────────────────────────┐
│  Frontend + GraphiQL                    │
│  http://localhost:33001/graphiql/       │ ← 🎯 PRACUJETE TU
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

---

## 🔑 Quick Reference

### Testovací uživatelé

```json
// Admin (všechna oprávnění)
{
  "x-demo-user-id": "76dac14f-7114-4bb2-882d-0d762eab6f4a"
}

// Editor (vytváření, editace)
{
  "x-demo-user-id": "678a2389-dd49-4d44-88be-28841ae34df1"
}

// Viewer (pouze čtení)
{
  "x-demo-user-id": "83981199-2134-4724-badf-cd1f0f38babf"
}
```

### Základní queries

```graphql
# Kdo jsem?
query { who_am_i { id email } }

# Seznam assetů
query { asset_page(limit: 10) { id name } }

# Moje zápůjčky
query { asset_loan_page(limit: 10) { id borrower_user_email } }
```

### Permission v kódu

```python
from src.GraphTypeDefinitions.permissions import RequireAdmin, RequireEditor

# Admin only
@strawberry.field(permission_classes=[RequireAdmin])
async def admin_operation(...):
    ...

# Editor or admin
@strawberry.field(permission_classes=[RequireEditor])
async def edit_operation(...):
    ...
```

---

## 🔗 Další zdroje

- [Apollo Federation Docs](https://www.apollographql.com/docs/federation/)
- [Strawberry GraphQL Permissions](https://strawberry.rocks/docs/guides/permissions)
- [../systemdata.combined.json](../systemdata.combined.json) - Definice rolí
- [../QUICKSTART_RBAC.md](../QUICKSTART_RBAC.md) - Stručný přehled

---

**Vytvořeno:** 11. 1. 2026  
**Poslední update:** Po implementaci RBAC a Gateway dokumentace
