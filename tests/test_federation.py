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


