# 🧾 Deníček – commity

### Zadání
**6. Evidence majetku, majetek, inventarizační záznam, zápůjčky**  
Projekt pro dva studenty.  
Vyjít z vlastní zkušenosti – seznam věcí, které byly zapůjčeny.  
Zahrnout provedené kontroly evidovaných věcí.

---

## Říjen 2025 – Základ projektu

### 27. 10. 2025 | Push 1: Správa majetku
Kompletní CRUD systém pro správu assetů.  
Nové modely, dotazy a testy.  
Řešený problém: napojení inventárních záznamů na skupinové vlastnictví a konzistence při autorizaci.

---

### 29. 10. 2025 | Push 2: Stabilní build 1.0
Refaktor `src/DBFeeder.py`, sladění `main.py` s Docker orchestrací.  
Hodinové porovnávání JSON výstupů – ručně dohledané rozdíly v timezone offsetech, které způsobovaly chyby při importu.

---

### 31. 10. 2025 | Push 3: Release 1.1
Regenerace `systemdata.json` a `systemdata.backup.json`, dočasný formát výstupu.  
Kontrola exportu – generátor občas duplikoval pozvánky a vytvářel sirotčí záznamy bez vazby.  
Po opravě a testech export proběhl bez chyb.

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
