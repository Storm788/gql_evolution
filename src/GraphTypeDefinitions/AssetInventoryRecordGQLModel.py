import typing
import datetime
import strawberry

from uoishelpers.gqlpermissions import OnlyForAuthentized
from uoishelpers.resolvers import (
    getLoadersFromInfo,
    createInputs2,
    InsertError,
    Insert,
    UpdateError,
    Update,
    DeleteError,
    Delete,
    PageResolver,
    ScalarResolver,
)

from .BaseGQLModel import BaseGQLModel, IDType, Relation
from .context_utils import ensure_user_in_context
from .permissions import is_admin_user
from src.error_codes import format_error_message
from uuid import UUID as ErrorCodeUUID

AssetGQLModel = typing.Annotated["AssetGQLModel", strawberry.lazy(".AssetGQLModel")]
UserGQLModel = typing.Annotated["UserGQLModel", strawberry.lazy(".UserGQLModel")]


# @createInputs2  # Commented out to avoid Apollo Gateway syntax errors with multiline descriptions
@strawberry.input
class AssetInventoryRecordInputFilter:
    id: typing.Optional[IDType] = None
    asset_id: typing.Optional[IDType] = None
    record_date: typing.Optional[datetime.datetime] = None
    status: typing.Optional[str] = None
    checked_by_user_id: typing.Optional[IDType] = None


@strawberry.federation.type(keys=["id"], description="""Physical inventory check record documenting asset verification.
Records periodic inspections to confirm asset presence, condition, and location accuracy.
Each record captures who performed the check, when it was done, the asset's status, and any observations.
Essential for compliance, asset tracking accuracy, and identifying missing or damaged items.
Supports audit trails and inventory reconciliation processes.""")
class AssetInventoryRecordGQLModel(BaseGQLModel):
    @classmethod
    def getLoader(cls, info: strawberry.types.Info):
        return getLoadersFromInfo(info).AssetInventoryRecordModel

    asset_id: typing.Optional[IDType] = strawberry.field(
        description="Asset id",
        default=None,
        permission_classes=[OnlyForAuthentized],
        directives=[Relation(to="AssetGQLModel")]
    )
    record_date: typing.Optional[datetime.datetime] = strawberry.field(description="Record date", default=None, permission_classes=[OnlyForAuthentized])
    status: typing.Optional[str] = strawberry.field(description="Status", default=None, permission_classes=[OnlyForAuthentized])
    note: typing.Optional[str] = strawberry.field(description="Note", default=None, permission_classes=[OnlyForAuthentized])
    checked_by_user_id: typing.Optional[IDType] = strawberry.field(
        description="Checked by user id",
        default=None,
        permission_classes=[OnlyForAuthentized],
        directives=[Relation(to="UserGQLModel")]
    )

    asset: typing.Optional[AssetGQLModel] = strawberry.field(
        description="Asset",
        permission_classes=[OnlyForAuthentized],
        resolver=ScalarResolver[AssetGQLModel](fkey_field_name="asset_id")
    )
    checked_by_user: typing.Optional[UserGQLModel] = strawberry.field(
        description="User who performed the check",
        permission_classes=[OnlyForAuthentized],
        resolver=ScalarResolver[UserGQLModel](fkey_field_name="checked_by_user_id")
    )


@strawberry.type(description="Inventory record queries")
class AssetInventoryRecordQuery:
    @strawberry.field(
        description="Get inventory record by id",
        permission_classes=[OnlyForAuthentized]
    )
    async def asset_inventory_record_by_id(
        self, info: strawberry.types.Info, id: IDType
    ) -> typing.Optional[AssetInventoryRecordGQLModel]:
        """Admin vidí všechno; běžný uživatel jen záznamy pro své assety"""
        loader = getLoadersFromInfo(info).AssetInventoryRecordModel
        record = await loader.load(id)
        if record is None:
            return None
        
        user = ensure_user_in_context(info)
        if user is None:
            return None
        
        # Admin vidí všechno
        if is_admin_user(user):
            return AssetInventoryRecordGQLModel.from_dataclass(record)
        
        # Běžný uživatel - musíme zkontrolovat, zda je custodian assetu
        asset_loader = getLoadersFromInfo(info).AssetModel
        asset = await asset_loader.load(record.asset_id)
        if asset and str(asset.custodian_user_id) == str(user.get("id")):
            return AssetInventoryRecordGQLModel.from_dataclass(record)
        
        return None

    @strawberry.field(
        description="Page of inventory records",
        permission_classes=[OnlyForAuthentized]
    )
    async def asset_inventory_record_page(
        self,
        info: strawberry.types.Info,
        skip: int = 0,
        limit: int = 10,
        orderby: typing.Optional[str] = None,
        where: typing.Optional[AssetInventoryRecordInputFilter] = None,
    ) -> typing.List[AssetInventoryRecordGQLModel]:
        """Admin vidí všechno; běžný uživatel jen záznamy pro své assety"""
        user = ensure_user_in_context(info)
        if user is None:
            return []
        
        loader = getLoadersFromInfo(info).AssetInventoryRecordModel
        
        # Admin vidí všechno
        if is_admin_user(user):
            print(f"DEBUG inventory_record_page: Admin - vracím všechny záznamy")
            results = await loader.page(skip=skip, limit=limit, orderby=orderby, where=where)
            return [AssetInventoryRecordGQLModel.from_dataclass(row) for row in results]
        
        # Běžný uživatel - najdeme jeho assety a pak inventory records pro tyto assety
        uid = str(user.get("id"))
        print(f"DEBUG inventory_record_page: Non-admin user {uid}")
        
        try:
            user_uuid = IDType(uid)
            # Najdi assety, kde je uživatel custodian
            asset_loader = getLoadersFromInfo(info).AssetModel
            user_assets = await asset_loader.filter_by(custodian_user_id=user_uuid)
            asset_ids = [asset.id for asset in user_assets]
            
            if not asset_ids:
                print(f"DEBUG: Uživatel nemá žádné assety")
                return []
            
            # Najdi inventory records pro tyto assety
            all_records = []
            for asset_id in asset_ids:
                records = await loader.filter_by(asset_id=asset_id)
                all_records.extend(records)
            
            print(f"DEBUG: Nalezeno {len(all_records)} inventory records")
            all_records = list(all_records)[skip:skip+limit] if skip or limit else all_records
            return [AssetInventoryRecordGQLModel.from_dataclass(row) for row in all_records]
        except Exception as e:
            print(f"ERROR filtering inventory records: {e}")
            return []


from uoishelpers.resolvers import InputModelMixin


@strawberry.input
class AssetInventoryRecordInsertGQLModel(InputModelMixin):
    getLoader = AssetInventoryRecordGQLModel.getLoader
    id: typing.Optional[IDType] = strawberry.field(description="id", default=None)
    asset_id: IDType = strawberry.field(description="Asset id")
    record_date: typing.Optional[datetime.datetime] = strawberry.field(description="Record date", default_factory=datetime.datetime.utcnow)
    status: typing.Optional[str] = strawberry.field(description="Status", default=None)
    note: typing.Optional[str] = strawberry.field(description="Note", default=None)
    checked_by_user_id: typing.Optional[IDType] = strawberry.field(description="Checked by user id", default=None)

    rbacobject_id: strawberry.Private[IDType] = None
    createdby_id: strawberry.Private[IDType] = None


@strawberry.input
class AssetInventoryRecordUpdateGQLModel(InputModelMixin):
    getLoader = AssetInventoryRecordGQLModel.getLoader
    id: IDType = strawberry.field(description="id")
    lastchange: datetime.datetime = strawberry.field(description="lastchange")
    record_date: typing.Optional[datetime.datetime] = strawberry.field(description="Record date", default=None)
    status: typing.Optional[str] = strawberry.field(description="Status", default=None)
    note: typing.Optional[str] = strawberry.field(description="Note", default=None)
    checked_by_user_id: typing.Optional[IDType] = strawberry.field(description="Checked by user id", default=None)

    changedby_id: strawberry.Private[IDType] = None


@strawberry.input
class AssetInventoryRecordDeleteGQLModel:
    id: IDType = strawberry.field(description="id")
    lastchange: datetime.datetime = strawberry.field(description="lastchange")


@strawberry.type(description="Inventory record mutations")
class AssetInventoryRecordMutation:
    @strawberry.field(description="Insert inventory record", permission_classes=[OnlyForAuthentized])
    async def asset_inventory_record_insert(self, info: strawberry.types.Info, record: AssetInventoryRecordInsertGQLModel) -> typing.Union[AssetInventoryRecordGQLModel, InsertError[AssetInventoryRecordGQLModel]]:
        ensure_user_in_context(info)
        result = await Insert[AssetInventoryRecordGQLModel].DoItSafeWay(info=info, entity=record)
        return result

    @strawberry.field(description="Update inventory record", permission_classes=[OnlyForAuthentized])
    async def asset_inventory_record_update(self, info: strawberry.types.Info, record: AssetInventoryRecordUpdateGQLModel) -> typing.Union[AssetInventoryRecordGQLModel, UpdateError[AssetInventoryRecordGQLModel]]:
        ensure_user_in_context(info)
        result = await Update[AssetInventoryRecordGQLModel].DoItSafeWay(info=info, entity=record)
        return result

    @strawberry.field(description="Delete inventory record", permission_classes=[OnlyForAuthentized])
    async def asset_inventory_record_delete(self, info: strawberry.types.Info, record: AssetInventoryRecordDeleteGQLModel) -> typing.Union[AssetInventoryRecordGQLModel, DeleteError[AssetInventoryRecordGQLModel]]:
        ensure_user_in_context(info)
        result = await Delete[AssetInventoryRecordGQLModel].DoItSafeWay(info=info, entity=record)
        if result is None:
            return AssetInventoryRecordGQLModel(id=record.id)
        return result
