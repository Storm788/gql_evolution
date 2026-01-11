import os
import datetime
from pathlib import Path
from typing import Union, Iterable

from uoishelpers.feeders import ImportModels
from uoishelpers.dataloaders import readJsonFile

from src.DBDefinitions import (
    EventModel,
    EventInvitationModel,
    AssetModel,
    AssetInventoryRecordModel,
    AssetLoanModel,
)

PathInput = Union[str, os.PathLike]

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATA_PATH = PROJECT_ROOT / "systemdata.combined.json"
DEFAULT_BACKUP_PATH = PROJECT_ROOT / "systemdata.backup.json"


def _parse_dates(records: Iterable[dict], field_names: Iterable[str]) -> None:
    """Convert selected string timestamp fields to datetime objects in-place."""
    for record in records:
        if not isinstance(record, dict):
            continue
        for field in field_names:
            value = record.get(field, None)
            if isinstance(value, str):
                try:
                    record[field] = datetime.datetime.fromisoformat(value)
                except ValueError:
                    pass


def _normalize_dataset_shapes(data: dict) -> dict:
    """Ensure legacy keys exist even when JSON uses *_evolution variants."""
    if isinstance(data, dict):
        if "events" not in data and isinstance(data.get("events_evolution"), list):
            data["events"] = list(data["events_evolution"])
        if "event_invitations" not in data and isinstance(
            data.get("event_invitations_evolution"), list
        ):
            data["event_invitations"] = list(data["event_invitations_evolution"])
        
        # Normalizace pro asset tabulky
        if "assets" not in data and isinstance(data.get("assets_evolution"), list):
            data["assets"] = list(data["assets_evolution"])
        if "asset_inventory_records" not in data and isinstance(
            data.get("asset_inventory_records_evolution"), list
        ):
            data["asset_inventory_records"] = list(data["asset_inventory_records_evolution"])
        if "asset_loans" not in data and isinstance(data.get("asset_loans_evolution"), list):
            data["asset_loans"] = list(data["asset_loans_evolution"])

        _parse_dates(
            data.get("asset_inventory_records_evolution", []),
            ("record_date", "created", "lastchange"),
        )
        _parse_dates(
            data.get("asset_loans_evolution", []),
            ("startdate", "enddate", "returned_date", "created", "lastchange"),
        )
    return data


def get_demodata(filename: PathInput = DEFAULT_DATA_PATH):
    data_path = Path(filename)
    data = readJsonFile(jsonFileName=str(data_path))
    return _normalize_dataset_shapes(data)


async def initDB(asyncSessionMaker, filename: PathInput = DEFAULT_DATA_PATH):

    dbModels = [
    ]

    demodata_value = os.environ.get("DEMODATA", None)
    print(f"DEBUG DBFeeder: DEMODATA={repr(demodata_value)}, type={type(demodata_value)}", flush=True)
    isDemo = demodata_value in ["True", "true", True]
    print(f"DEBUG DBFeeder: isDemo={isDemo}", flush=True)
    if isDemo:
        print("Demo mode", flush=True)
        dbModels = [
            EventModel,
            EventInvitationModel,
            AssetModel,
            AssetInventoryRecordModel,
            AssetLoanModel,
        ]


    jsonData = get_demodata(filename)
    
    # Debug: vypíšeme, jaké klíče a kolik záznamů máme
    print(f"DEBUG: Loading data from {filename}", flush=True)
    print(f"DEBUG: JSON keys: {list(jsonData.keys())[:10]}", flush=True)
    if "assets_evolution" in jsonData:
        print(f"DEBUG: assets_evolution has {len(jsonData['assets_evolution'])} records", flush=True)
    
    # Nejprve zkusíme standardní import
    await ImportModels(asyncSessionMaker, dbModels, jsonData)
    
    # Pak přidáme manuální import pro asset data, pokud standardní nefunguje - POUZE v demo módu
    if isDemo:
        async with asyncSessionMaker() as session:
            # Import assets
            if "assets_evolution" in jsonData:
                assets = jsonData["assets_evolution"]
                print(f"DEBUG: Manually inserting {len(assets)} assets", flush=True)
                for asset_data in assets:
                    # Filtruj metadata pole začínající podtržítkem
                    clean_data = {k: v for k, v in asset_data.items() if not k.startswith('_')}
                    asset = AssetModel(**clean_data)
                    session.add(asset)
                await session.commit()
                print(f"DEBUG: Assets inserted", flush=True)
            
            # Import asset loans
            if "asset_loans_evolution" in jsonData:
                loans = jsonData["asset_loans_evolution"]
                print(f"DEBUG: Manually inserting {len(loans)} loans", flush=True)
                for loan_data in loans:
                    # Filtruj metadata pole začínající podtržítkem
                    clean_data = {k: v for k, v in loan_data.items() if not k.startswith('_')}
                    loan = AssetLoanModel(**clean_data)
                    session.add(loan)
                await session.commit()
                print(f"DEBUG: Loans inserted", flush=True)
            
            # Import asset inventory records
            if "asset_inventory_records_evolution" in jsonData:
                records = jsonData["asset_inventory_records_evolution"]
                print(f"DEBUG: Manually inserting {len(records)} inventory records", flush=True)
                for record_data in records:
                    # Filtruj metadata pole začínající podtržítkem
                    clean_data = {k: v for k, v in record_data.items() if not k.startswith('_')}
                    record = AssetInventoryRecordModel(**clean_data)
                    session.add(record)
                await session.commit()
                print(f"DEBUG: Inventory records inserted", flush=True)

    print("Data initialized", flush=True)


async def backupDB(asyncSessionMaker, filename: PathInput = DEFAULT_BACKUP_PATH):
    import sqlalchemy
    import dataclasses
    import json
    from src.DBDefinitions.BaseModel import IDType

    dbModels = [
        EventModel,
        EventInvitationModel,
        AssetModel,
        AssetInventoryRecordModel,
        AssetLoanModel,
    ]
    data = []
    async with asyncSessionMaker() as session:
        for model in dbModels:
            sqlquery = sqlalchemy.select(model)
            rows = await session.execute(sqlquery)
            # vsechny radky do dict
            rowsdict = {}
            for row in rows:
                # print(row)
                asdict = dataclasses.asdict(row[0])
                id = asdict.get("id", None)
                if id is None: continue
                rowsdict[id] = asdict
            # vsechny primarn�� klice do ids
            ids = set(rowsdict.keys())
            todo = set()
            done = set()
            chunk_id = 0
            while len(done) < len(ids):
                for row in rowsdict.values():
                    id = row.get("id", None)
                    if id in done: continue
                    skip_this_id = False
                    for key, value in row.items():
                        if key == "id": continue
                        # if not isinstance(value, IDType): continue
                        if value is None: continue
                        if value not in ids: continue
                        if value not in done:
                            # print(row, key, value)
                            skip_this_id = True
                            break
                            # primarni klic je zpracovatelny, nemame zavislost na nezpracovanych klicich
                    if skip_this_id: continue
                    row["_chunk"] = chunk_id
                    todo.add(id)
                print(f"{model.__tablename__} chunk {chunk_id} todo/done/all {len(todo)}/{len(done)}/{len(ids)}")
                if len(todo) == 0: break
                done = done.union(todo)
                todo = set()
                chunk_id += 1
            data.append({
                model.__tablename__: list(rowsdict.values())
            })
        with open(Path(filename), "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False, default=str)

    print("backup done", flush=True)
