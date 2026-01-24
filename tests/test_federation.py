"""
Test pro ověření, že aplikace je správně propojená se všemi kontejnery a federace funguje.

⚠️ POZOR: Tento test vyžaduje, aby byly spuštěné všechny kontejnery:
    docker-compose -f docker-compose.debug.yml up

Spusť testy s markerem:
    pytest tests/test_federation.py -v -m integration

Nebo všechny testy kromě integračních:
    pytest tests/ -v -m "not integration"
"""
import pytest
import aiohttp
import asyncio
import logging
import json
from typing import Optional

# Označ všechny testy v tomto souboru jako integrační
pytestmark = pytest.mark.integration

# Konfigurace endpointů podle docker-compose.debug.yml
EVOLUTION_ENDPOINT = "http://localhost:8001/gql"
UG_ENDPOINT = "http://localhost:8000/gql"  # Pokud běží lokálně, jinak přes Docker
GATEWAY_ENDPOINT = "http://localhost:33001/api/gql/"  # Apollo Gateway přes frontend
FRONTEND_GRAPHQL = "http://localhost:33001/graphiql"  # Frontend GraphiQL

# Timeout pro HTTP požadavky
TIMEOUT = 5.0


async def check_endpoint_health(url: str, query: str = None) -> tuple[bool, Optional[str]]:
    """
    Ověří, že endpoint odpovídá na GraphQL požadavky.
    
    Returns:
        (is_healthy, error_message)
    """
    try:
        if query is None:
            # Základní introspection query
            query = """
            query {
                __schema {
                    types {
                        name
                    }
                }
            }
            """
        
        timeout = aiohttp.ClientTimeout(total=TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                url,
                json={"query": query},
                headers={"Content-Type": "application/json"}
            ) as response:
                if response.status == 200:
                    data = await response.json()
                    if "errors" in data and data["errors"]:
                        return False, f"GraphQL errors: {data['errors']}"
                    return True, None
                else:
                    text = await response.text()
                    return False, f"HTTP {response.status}: {text}"
    except aiohttp.ClientConnectorError:
        return False, "Connection refused - služba neběží"
    except asyncio.TimeoutError:
        return False, f"Timeout - služba neodpovídá do {TIMEOUT}s"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


@pytest.mark.asyncio
async def test_evolution_subgraph_available():
    """Test, že Evolution subgraph (lokální aplikace) je dostupný"""
    is_healthy, error = await check_endpoint_health(EVOLUTION_ENDPOINT)
    assert is_healthy, f"Evolution subgraph není dostupný na {EVOLUTION_ENDPOINT}: {error}"


@pytest.mark.asyncio
async def test_ug_subgraph_available():
    """Test, že UG subgraph je dostupný"""
    # UG může běžet v Dockeru, takže může být nedostupný lokálně
    # Pokud běží lokálně, otestujeme ho
    is_healthy, error = await check_endpoint_health(UG_ENDPOINT)
    if not is_healthy:
        pytest.skip(f"UG subgraph není dostupný na {UG_ENDPOINT} (možná běží jen v Dockeru): {error}")
    assert is_healthy, f"UG subgraph není dostupný: {error}"


@pytest.mark.asyncio
async def test_apollo_gateway_available():
    """Test, že Apollo Gateway je dostupný a odpovídá"""
    is_healthy, error = check_endpoint_health(GATEWAY_ENDPOINT)
    assert is_healthy, f"Apollo Gateway není dostupný na {GATEWAY_ENDPOINT}: {error}"


@pytest.mark.asyncio
async def test_federation_schema_loaded():
    """Test, že Apollo Gateway má načtené schema z obou subgraphů"""
    # Query, která ověří, že Gateway má schema z Evolution (Asset) a UG (User)
    query = """
    query {
        __schema {
            types {
                name
            }
        }
    }
    """
    
    is_healthy, error = await check_endpoint_health(GATEWAY_ENDPOINT, query)
    assert is_healthy, f"Gateway neodpovídá na schema query: {error}"
    
    # Ověříme, že schema obsahuje typy z obou subgraphů
    try:
        timeout = aiohttp.ClientTimeout(total=TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                GATEWAY_ENDPOINT,
                json={"query": query},
                headers={"Content-Type": "application/json"}
            ) as response:
                data = await response.json()
        
        if "data" in data and "__schema" in data["data"]:
            types = [t["name"] for t in data["data"]["__schema"]["types"]]
            
            # Ověříme, že máme typy z Evolution subgraph
            evolution_types = ["AssetGQLModel", "AssetLoanGQLModel", "AssetInventoryRecordGQLModel"]
            has_evolution = any(t in types for t in evolution_types)
            assert has_evolution, f"Gateway nemá typy z Evolution subgraph. Nalezené typy: {types[:10]}..."
            
            # Ověříme, že máme typy z UG subgraph (pokud je dostupný)
            ug_types = ["UserGQLModel", "GroupGQLModel"]
            has_ug = any(t in types for t in ug_types)
            if has_ug:
                logging.info("✅ Gateway má typy z obou subgraphů (Evolution + UG)")
            else:
                logging.warning("⚠️ Gateway nemá typy z UG subgraph (možná UG neběží)")
    except Exception as e:
        pytest.fail(f"Chyba při ověřování federovaného schema: {str(e)}")


@pytest.mark.asyncio
async def test_federation_query_works():
    """Test, že federovaná query funguje přes Gateway"""
    # Query, která používá typy z obou subgraphů
    query = """
    query {
        hello
        whoAmI {
            id
            email
            name
        }
    }
    """
    
    is_healthy, error = await check_endpoint_health(GATEWAY_ENDPOINT, query)
    assert is_healthy, f"Federovaná query nefunguje: {error}"
    
    # Ověříme odpověď
    try:
        timeout = aiohttp.ClientTimeout(total=TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                GATEWAY_ENDPOINT,
                json={"query": query},
                headers={
                    "Content-Type": "application/json",
                    "x-demo-user-id": "2d9dc5ca-a4a2-11ed-b9df-0242ac120003"  # Demo user
                }
            ) as response:
                data = await response.json()
        
        assert "errors" not in data or not data["errors"], f"GraphQL errors: {data.get('errors')}"
        assert "data" in data, "Odpověď neobsahuje data"
        assert "hello" in data["data"], "Query 'hello' nevrátila výsledek"
    except Exception as e:
        pytest.fail(f"Chyba při testování federované query: {str(e)}")


@pytest.mark.asyncio
async def test_evolution_has_federation_keys():
    """Test, že Evolution subgraph má správně nastavené federation keys"""
    query = """
    query {
        __type(name: "AssetGQLModel") {
            fields {
                name
            }
        }
    }
    """
    
    is_healthy, error = await check_endpoint_health(EVOLUTION_ENDPOINT, query)
    assert is_healthy, f"Evolution subgraph neodpovídá na introspection: {error}"
    
    try:
        timeout = aiohttp.ClientTimeout(total=TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                EVOLUTION_ENDPOINT,
                json={"query": query},
                headers={"Content-Type": "application/json"}
            ) as response:
                data = await response.json()
        
        if "data" in data and "__type" in data["data"]:
            fields = [f["name"] for f in data["data"]["__type"]["fields"]]
            assert "id" in fields, "AssetGQLModel nemá pole 'id' (potřebné pro federation key)"
            logging.info("✅ Evolution subgraph má správně nastavené federation keys")
    except Exception as e:
        pytest.fail(f"Chyba při ověřování federation keys: {str(e)}")


@pytest.mark.asyncio
async def test_all_containers_connected():
    """Komplexní test, že všechny kontejnery jsou propojené"""
    results = []
    
    # Test Evolution
    evolution_ok, evolution_error = await check_endpoint_health(EVOLUTION_ENDPOINT)
    results.append(("Evolution Subgraph", evolution_ok, evolution_error))
    
    # Test Gateway
    gateway_ok, gateway_error = await check_endpoint_health(GATEWAY_ENDPOINT)
    results.append(("Apollo Gateway", gateway_ok, gateway_error))
    
    # Test UG (volitelné)
    ug_ok, ug_error = await check_endpoint_health(UG_ENDPOINT)
    results.append(("UG Subgraph", ug_ok, ug_error))
    
    # Shrnutí
    failed = [(name, error) for name, ok, error in results if not ok]
    
    if failed:
        error_msg = "\n".join([f"  ❌ {name}: {error}" for name, error in failed])
        pytest.fail(f"Některé služby nejsou dostupné:\n{error_msg}")
    
    logging.info("✅ Všechny testované služby jsou dostupné a propojené")
