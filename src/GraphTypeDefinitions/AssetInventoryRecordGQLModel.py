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

AssetGQLModel = typing.Annotated["AssetGQLModel", strawberry.lazy(".AssetGQLModel")]
UserGQLModel = typing.Annotated["UserGQLModel", strawberry.lazy(".UserGQLModel")]


@createInputs2
class AssetInventoryRecordInputFilter:
    id: IDType
    asset_id: IDType
    record_date: datetime.datetime
    status: str
    checked_by_user_id: IDType


@strawberry.federation.type(keys=["id"], description="Inventory check record of an asset")
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
    asset_inventory_record_by_id: typing.Optional[AssetInventoryRecordGQLModel] = strawberry.field(
        description="Get inventory record by id", permission_classes=[OnlyForAuthentized], resolver=AssetInventoryRecordGQLModel.load_with_loader
    )
    asset_inventory_record_page: typing.List[AssetInventoryRecordGQLModel] = strawberry.field(
        description="Page of inventory records", permission_classes=[OnlyForAuthentized], resolver=PageResolver[AssetInventoryRecordGQLModel](whereType=AssetInventoryRecordInputFilter)
    )


from uoishelpers.resolvers import InputModelMixin


@strawberry.input(description="Inventory record insert input")
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


@strawberry.input(description="Inventory record update input")
class AssetInventoryRecordUpdateGQLModel(InputModelMixin):
    getLoader = AssetInventoryRecordGQLModel.getLoader
    id: IDType = strawberry.field(description="id")
    lastchange: datetime.datetime = strawberry.field(description="lastchange")
    record_date: typing.Optional[datetime.datetime] = strawberry.field(description="Record date", default=None)
    status: typing.Optional[str] = strawberry.field(description="Status", default=None)
    note: typing.Optional[str] = strawberry.field(description="Note", default=None)
    checked_by_user_id: typing.Optional[IDType] = strawberry.field(description="Checked by user id", default=None)

    changedby_id: strawberry.Private[IDType] = None


@strawberry.input(description="Inventory record delete input")
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
