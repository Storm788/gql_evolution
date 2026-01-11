# 🧾 Deníček – commity

### Zadání
**6. Evidence majetku, majetek, inventarizační záznam, zápůjčky**  
Projekt pro dva studenty.  
Vyjít z vlastní zkušenosti – seznam věcí, které byly zapůjčeny.  
Zahrnout provedené kontroly evidovaných věcí.

---

## 31. 10. 2025 | Release 1.1
Regenerace `systemdata.json` a `systemdata.backup.json`, dočasný formát výstupu.  
Kontrola exportu – generátor občas duplikoval pozvánky a vytvářel sirotky bez vazby.  
Po opravě a testu export proběhl bez chyb.

---

## 29. 10. 2025 | Stabilní build 1.0
Refaktor `src/DBFeeder.py`, sladění `main.py` s docker orchestrace.  
Hodinové porovnávání JSONů – ručně dohledané rozdíly v timezone offsetech, které házely chyby při importu.

---

## 27. 10. 2025 | Správa majetku
Kompletní CRUD systém pro správu assetů.  
Nové modely, dotazy, testy.  
Problém: napojení inventárních záznamů na skupinové vlastnictví a konzistence při autorizaci.

---
## 11. 01. 2026 | Autorizace a lokalizace

### Push 1: Odebrání ProfilingExtension, přidání graphiql.html
- Odstraněn `ProfilingExtension` z `src/GraphTypeDefinitions/__init__.py` (vyvolával `'ProfilingExtension.counter'` chyby).
- Vytvořen `public/graphiql.html` – interaktivní GraphQL explorer.
- Vypnuty debug printy a vychytány chyby z `ProfilingExtension`.
- **Commit:** Removed ProfilingExtension, added GraphiQL UI.

### Push 2: Centralizovaný error code dictionary
- Vytvořen `src/error_codes.py` se UUID-based error kódy (PERMISSION_DENIED, NOT_FOUND, VALIDATION_ERROR, atd.).
- Přidány do všech mutation typů (Asset, AssetLoan, AssetInventoryRecord).
- Funkce `format_error_message()` pro konzistentní chybové zprávy.
- **Commit:** Add centralized error code dictionary with UUID keys.

### Push 3: Vylepšení AI popisů a rozšíření About
- Rozšířeny `description` polia u `AssetGQLModel`, `AssetLoanGQLModel`, `AssetInventoryRecordGQLModel`.
- Dokumentace typu a případů užití v každém modelu.
- **Commit:** Enhance AI-friendly descriptions for all GraphQL types.

### Push 4: Přidání /whoami endpoint a GraphiQL user bar
- Přidán GET `/whoami` endpoint v `main.py` – vrací aktuálního uživatele nebo `{ user: null, label: "No User" }`.
- Aktualizován `public/graphiql.html` s horní lištou zobrazující přihlášeného uživatele.
- Zapnutý editor hlaviček v GraphiQL pro snadné testování `x-demo-user-id`.
- **Commit:** Add /whoami endpoint and GraphiQL user indicator bar.

### Push 5: Ochrana asset mutací – OnlyJohnNewbie permission
- Přidán import `OnlyJohnNewbie` do `src/GraphTypeDefinitions/AssetGQLModel.py`.
- Změněny `permission_classes=[OnlyForAuthentized]` na `permission_classes=[OnlyJohnNewbie]` pro `asset_insert`, `asset_update`, `asset_delete`.
- Garantuje, že pouze admin (Estera) může vytvářet, upravovat a mazat majetek.
- **Commit:** Enforce admin-only asset mutations with OnlyJohnNewbie.

### Push 6: Oprava error union konstruktorů
- Opraveny vnitřní kontroly v `asset_insert`, `asset_update`, `asset_delete` v `AssetGQLModel.py`.
- Změněny vrácené error objekty z `entity=None` na `_entity=None` (správný název pole).
- Přidány `_input=asset` a `code=ErrorCodeUUID(...)` pro úplnost.
- Stejná oprava v `AssetLoanGQLModel.py` pro `asset_loan_insert`, `asset_loan_update`, `asset_loan_delete`.
- **Commit:** Fix error union constructors – use _entity, include _input and code.

### Push 7: Lokalizace error kódů do češtiny
- Přeloženy všechny kategorie a popisy chyb v `src/error_codes.py`:
  - `PERMISSION_DENIED` → `OPRÁVNĚNÍ_ZAMÍTNUTO`
  - `NOT_FOUND` → `NENALEZENO`
  - `VALIDATION_ERROR` → `VALIDAČNÍ_CHYBA`
  - `AUTHENTICATION_REQUIRED` → `VYŽADOVÁNA_AUTENTIZACE`
  - atd.
- Lokalizován fallback: `UNKNOWN_ERROR` → `NEZNÁMÁ_CHYBA`.
- **Commit:** Localize error codes and messages to Czech.

### Push 8: Lokalizace GraphiQL UI a permission zprávy
- Změněny UI popisky v `public/graphiql.html`:
  - `User: Loading…` → `Uživatel: Načítám…`
  - `No User` → `Bez uživatele`
  - Komentáře v default dotazu do češtiny.
- Lokalizován text permisiony v `src/GraphTypeDefinitions/permissions.py`:
  - `OnlyJohnNewbie.message` = `"Nemáte oprávnění: pouze administrátor smí provést tuto akci"`.
- **Commit:** Localize GraphiQL UI and permission messages to Czech.

---

## Shrnutí stavu

✅ **RBAC a autorizace**
- Admin (Estera) vidí vše, běžní uživatelé vidí pouze svá data.
- Mutations assetů a půjček jsou admin-only s česky lokalizovaným chybovým hlášením.
- Dvoustupňová ochrana: schema-level `OnlyJohnNewbie` + vnitřní `is_admin_user()` check.

✅ **Chyby a hlášení**
- Centralizovaný UUID-based error code dictionary.
- Česky lokalizované chybové zprávy s kategoriemi.
- Union vrátí error objekt s `msg`, `code`, `_entity`, `_input`.

✅ **UX a dokumentace**
- GraphiQL s user indicator barem a header editorem.
- /whoami endpoint pro zjištění přihlášeného uživatele.
- AI-friendly popis všech typů.

✅ **Databáze**
- DEMO=True (drop/recreate na startup), DEMODATA=False (žádná demo data).
- Dvě PostgreSQL instance (assets, credentials).

📋 **Zbývá (assignment requirements)**
- Code coverage report (pytest --cov)
- Docker Hub publish
- AssetInventoryRecord mutations (dosud jen queries)
- GraphQL whoAmI query field (dosud jen /whoami endpoint)

---




