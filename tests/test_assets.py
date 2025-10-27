import logging
import pytest

from GraphTypeDefinitions import schema
from .shared import (
    prepare_in_memory_sqllite,
    prepare_demodata,
    createContext,
)


@pytest.mark.asyncio
async def test_asset_crud_cycle():
    async_session_maker = await prepare_in_memory_sqllite()
    await prepare_demodata(async_session_maker)
    context_value = createContext(async_session_maker)

    # insert asset
    insert_query = """
        mutation {
            result: assetInsert(asset: {name: "Laptop", inventoryCode: "INV-001", location: "Room 101"}) {
                id
                msg
                entity: asset { id name inventoryCode location lastchange }
            }
        }
    """
    resp = await schema.execute(insert_query, context_value=context_value)
    assert resp.errors is None
    data = resp.data["result"]
    assert data is not None
    asset = data["entity"]
    assert asset is not None
    asset_id = asset["id"]
    assert asset_id is not None

    # query by id
    byid_query = """
        query($id: UUID!) { result: assetById(id: $id) { id name inventoryCode location } }
    """
    resp = await schema.execute(byid_query, variable_values={"id": asset_id}, context_value=context_value)
    assert resp.errors is None
    asset2 = resp.data["result"]
    assert asset2 is not None
    assert asset2["name"] == "Laptop"

    # update
    lastchange = data["entity"].get("lastchange")
    update_query = """
        mutation($id: UUID!, $lc: DateTime!) {
            result: assetUpdate(asset: {id: $id, lastchange: $lc, location: "Room 102"}) {
                id
                entity: asset { id location }
            }
        }
    """
    resp = await schema.execute(update_query, variable_values={"id": asset_id, "lc": lastchange}, context_value=context_value)
    assert resp.errors is None
    entity = resp.data["result"]["entity"]
    assert entity["location"] == "Room 102"

    # create inventory record
    inv_insert = """
        mutation($assetId: UUID!) {
            result: assetInventoryRecordInsert(record: {assetId: $assetId, status: "ok"}) {
                id
                entity: assetInventoryRecord { id status asset { id } }
            }
        }
    """
    resp = await schema.execute(inv_insert, variable_values={"assetId": asset_id}, context_value=context_value)
    assert resp.errors is None
    inv = resp.data["result"]["entity"]
    assert inv["status"] == "ok"

    # create loan
    loan_insert = """
        mutation($assetId: UUID!) {
            result: assetLoanInsert(loan: {assetId: $assetId}) {
                id
                entity: assetLoan { id asset { id } }
            }
        }
    """
    resp = await schema.execute(loan_insert, variable_values={"assetId": asset_id}, context_value=context_value)
    assert resp.errors is None
    loan = resp.data["result"]["entity"]
    assert loan is not None
