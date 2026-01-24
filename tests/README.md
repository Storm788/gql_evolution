# 🧪 Spuštění testů

## 📋 Předpoklady

Ujistěte se, že máte nainstalované závislosti pro vývoj:

```bash
pip install -r requirements-dev.txt
```

Nebo pokud používáte venv:
```bash
# Aktivujte venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/Mac

# Nainstalujte závislosti
pip install -r requirements-dev.txt
```

---

## 🚀 Spuštění všech testů

Z kořenového adresáře `gql_evolution`:

```bash
pytest tests/
```

Nebo z adresáře `tests`:

```bash
cd tests
pytest
```

---

## 🎯 Spuštění konkrétního testovacího souboru

```bash
# Testy pro assety
pytest tests/test_assets.py

# Testy pro dataloadery
pytest tests/test_dataloaders.py

# Testy pro GraphQL typy
pytest tests/test_gt_definitions.py

# Testy pro databázi
pytest tests/test_dbdefinitions.py

# Testy pro FastAPI klienta
pytest tests/test_client.py
```

---

## 🔍 Spuštění konkrétního testu

```bash
# Spustit jeden konkrétní test
pytest tests/test_assets.py::test_asset_crud_cycle

# Spustit testy obsahující určitý pattern
pytest tests/ -k "asset"
pytest tests/ -k "loan"
```

---

## 📊 S code coverage

```bash
# Spustit testy s coverage reportem
pytest tests/ --cov=src --cov-report=html

# Zobrazit coverage v terminálu
pytest tests/ --cov=src --cov-report=term

# Otevřít HTML report (po spuštění s --cov-report=html)
# Windows:
start htmlcov/index.html
# Linux/Mac:
open htmlcov/index.html
```

---

## 🔧 Další užitečné volby

```bash
# Verbose výstup (více informací)
pytest tests/ -v

# Velmi verbose (zobrazí print statements)
pytest tests/ -vv -s

# Spustit pouze testy, které selhaly při posledním spuštění
pytest tests/ --lf

# Spustit testy a zastavit při prvním selhání
pytest tests/ -x

# Spustit testy v paralelním režimu (vyžaduje pytest-xdist)
pytest tests/ -n auto
```

---

## 📝 Struktura testů

- **`client.py`** - Funkce `createGQLClient()` pro vytváření testovacího klienta (pouze pro vytváření nových testů)
- **`conftest.py`** - Konfigurace pytest a nastavení importů
- **`shared.py`** - Sdílené pomocné funkce pro testy (příprava DB, demo data, context)
- **`test_*.py`** - Skutečné testovací soubory

---

## 🆕 Vytváření nových testů

1. Vytvořte nový soubor `test_nazev.py` v adresáři `tests/`
2. Importujte potřebné moduly:
   ```python
   import pytest
   from .shared import (
       prepare_in_memory_sqllite,
       prepare_demodata,
       createContext,
   )
   from GraphTypeDefinitions import schema
   ```
3. Použijte `createGQLClient()` z `client.py` pro FastAPI testy:
   ```python
   from .client import createGQLClient
   
   def test_something():
       client = createGQLClient()
       response = client.post("/gql", json={"query": "..."})
       assert response.status_code == 200
   ```
4. Nebo použijte přímé GraphQL testy:
   ```python
   @pytest.mark.asyncio
   async def test_something():
       async_session_maker = await prepare_in_memory_sqllite()
       await prepare_demodata(async_session_maker)
       context_value = createContext(async_session_maker)
       
       query = """
           query { ... }
       """
       resp = await schema.execute(query, context_value=context_value)
       assert resp.errors is None
   ```

---

## ⚠️ Poznámky

- Testy používají **in-memory SQLite databázi** (není potřeba běžící PostgreSQL)
- Testy jsou **asynchronní** - používají `@pytest.mark.asyncio`
- `client.py` je **pouze pro vytváření nových testů**, ne pro spouštění existujících testů

---

## 🐛 Řešení problémů

**Problém:** `ModuleNotFoundError: No module named 'GraphTypeDefinitions'`
- **Řešení:** Ujistěte se, že jste v kořenovém adresáři `gql_evolution` nebo že `conftest.py` správně nastavuje cesty

**Problém:** `pytest: command not found`
- **Řešení:** Nainstalujte pytest: `pip install pytest pytest-asyncio`

**Problém:** Testy selhávají s chybou databáze
- **Řešení:** Testy používají in-memory SQLite, takže by neměly potřebovat externí databázi. Zkontrolujte, zda `prepare_in_memory_sqllite()` funguje správně.
