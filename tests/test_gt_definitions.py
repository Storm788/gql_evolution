import logging
import os
import sqlalchemy
import sys
import asyncio

import pytest

from GraphTypeDefinitions import schema

from .shared import (
    prepare_demodata,
    prepare_in_memory_sqllite,
    get_demodata,
    createContext,
)

# Nastav GQLUG_ENDPOINT_URL pro testy
os.environ.setdefault("GQLUG_ENDPOINT_URL", "http://localhost:8000/gql")

# Mock externí GraphQL volání pro načítání rolí
try:
    from uoishelpers.schema.WhoAmIExtension import WhoAmIExtension
    original_ug_query = WhoAmIExtension.ug_query
    
    async def mock_ug_query(self, query, variables):
        # Vrať prázdnou odpověď - v testech nepotřebujeme skutečné role
        return {"data": {"result": []}}
    
    WhoAmIExtension.ug_query = mock_ug_query
except Exception as e:
    logging.warning(f"Failed to monkey patch WhoAmIExtension.ug_query: {e}")

def createFrontendQuery(query="{}", variables={}, asserts=[]):
    @pytest.mark.asyncio
    async def test_frontend_query():    
        logging.debug("createFrontendQuery")
        async_session_maker = await prepare_in_memory_sqllite()
        await prepare_demodata(async_session_maker)
        context_value = createContext(async_session_maker)
        logging.debug(f"query for {query} with {variables}")
        resp = await schema.execute(
            query=query, 
            variable_values=variables, 
            context_value=context_value
        )

        assert resp.errors is None
        respdata = resp.data
        logging.debug(f"response: {respdata}")
        for a in asserts:
            a(respdata)
    return test_frontend_query

def runAssert(expression, comment):
    assert expression, comment

test_query_hello = createFrontendQuery(
    query="""{ hello }""",
    variables={},
    asserts = [
        lambda data: runAssert(data.get("hello", None) is not None, "expected data.hello"),
    ]
)
