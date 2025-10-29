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
DEFAULT_DATA_PATH = PROJECT_ROOT / "systemdata.json"
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

    isDemo = os.environ.get("DEMODATA", None) in ["True", "true", True]
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
    await ImportModels(asyncSessionMaker, dbModels, jsonData)

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
