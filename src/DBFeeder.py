import os

from functools import cache
from uoishelpers.feeders import ImportModels
from uoishelpers.dataloaders import readJsonFile

from src.DBDefinitions import (
    EventModel,
    EventInvitationModel,
    AssetModel,
    AssetInventoryRecordModel,
    AssetLoanModel,
)


def get_demodata():
    data = readJsonFile(jsonFileName="./systemdata.json")
    if isinstance(data, dict):
        if "events" not in data and "events_evolution" in data:
            data["events"] = data["events_evolution"]
        if "event_invitations" not in data and "event_invitations_evolution" in data:
            data["event_invitations"] = data["event_invitations_evolution"]

        def ensure_list_entry(container_name, entry):
            container = data.get(container_name, None)
            if isinstance(container, list):
                if not any(item.get("id") == entry["id"] for item in container):
                    container.append(entry.copy())

        def ensure_event(entry):
            ensure_list_entry("events", entry)
            ensure_list_entry("events_evolution", entry)

        def ensure_invitation(entry):
            ensure_list_entry("event_invitations", entry)
            ensure_list_entry("event_invitations_evolution", entry)

        ensure_event({
            "id": "08ff1c5d-9891-41f6-a824-fc6272adc189",
            "name": "Event With Master",
            "name_en": "Event With Master",
            "description": "Compatibility event with master reference",
            "startdate": "2024-05-01T08:00:00",
            "enddate": "2024-05-01T12:00:00",
            "masterevent_id": "a64871f8-2308-48ff-adb2-33fb0b0741f1",
            "lastchange": "2024-05-01T08:00:00",
            "__typename": "EventGQLModel",
        })

        ensure_event({
            "id": "5194663f-11aa-4775-91ed-5f3d79269fed",
            "name": "Event With SubEvents",
            "name_en": "Event With SubEvents",
            "description": "Compatibility event exposing sub events and users",
            "startdate": "2024-05-02T08:00:00",
            "enddate": "2024-05-02T12:00:00",
            "masterevent_id": "08ff1c5d-9891-41f6-a824-fc6272adc189",
            "lastchange": "2024-05-02T08:00:00",
            "__typename": "EventGQLModel",
        })

        ensure_event({
            "id": "45b2df80-ae0f-11ed-9bd8-0242ac110002",
            "name": "Child Event A",
            "name_en": "Child Event A",
            "description": "Compatibility child event A",
            "startdate": "2024-05-02T09:00:00",
            "enddate": "2024-05-02T10:00:00",
            "masterevent_id": "5194663f-11aa-4775-91ed-5f3d79269fed",
            "lastchange": "2024-05-02T09:00:00",
            "__typename": "EventGQLModel",
        })

        ensure_event({
            "id": "89d1e724-ae0f-11ed-9bd8-0242ac110002",
            "name": "Child Event B",
            "name_en": "Child Event B",
            "description": "Compatibility child event B",
            "startdate": "2024-05-02T10:00:00",
            "enddate": "2024-05-02T11:00:00",
            "masterevent_id": "5194663f-11aa-4775-91ed-5f3d79269fed",
            "lastchange": "2024-05-02T10:00:00",
            "__typename": "EventGQLModel",
        })

        ensure_invitation({
            "id": "cb7d3a2b-7a32-4f5d-a285-8157f632f0fe",
            "event_id": "5194663f-11aa-4775-91ed-5f3d79269fed",
            "user_id": "2d9dc5ca-a4a2-11ed-b9df-0242ac120003",
            "state_id": None,
            "__typename": "EventInvitationGQLModel",
        })

    return data
async def initDB(asyncSessionMaker, filename="./systemdata.json"):

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
        

    jsonData = readJsonFile(filename)
    await ImportModels(asyncSessionMaker, dbModels, jsonData)
    
    print("Data initialized", flush=True)

async def backupDB(asyncSessionMaker, filename="./systemdata.backup.json"):
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
            # vsechny primarní klice do ids
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
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False, default=str)
    
    print("backup done", flush=True)
