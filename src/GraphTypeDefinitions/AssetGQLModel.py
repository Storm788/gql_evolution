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
    VectorResolver,
    ScalarResolver,
)
from uoishelpers.resolvers import InputModelMixin

from .BaseGQLModel import BaseGQLModel, IDType, Relation
from .context_utils import ensure_user_in_context


AssetInventoryRecordGQLModel = typing.Annotated[
    "AssetInventoryRecordGQLModel", strawberry.lazy(".AssetInventoryRecordGQLModel")
]
AssetInventoryRecordInputFilter = typing.Annotated[
    "AssetInventoryRecordInputFilter", strawberry.lazy(".AssetInventoryRecordGQLModel")
]
AssetLoanGQLModel = typing.Annotated[
    "AssetLoanGQLModel", strawberry.lazy(".AssetLoanGQLModel")
]
AssetLoanInputFilter = typing.Annotated[
    "AssetLoanInputFilter", strawberry.lazy(".AssetLoanGQLModel")
]
UserGQLModel = typing.Annotated[
    "UserGQLModel", strawberry.lazy(".UserGQLModel")
]


AssetInsertErrorType = InsertError["AssetGQLModel"]  # type: ignore[index]
AssetUpdateErrorType = UpdateError["AssetGQLModel"]  # type: ignore[index]
AssetDeleteErrorType = DeleteError["AssetGQLModel"]  # type: ignore[index]


@createInputs2
class AssetInputFilter:
    """Filter operators for searching assets by fields.
Examples:
{"name": {"_ilike": "%notebook%"}}
{"inventory_code": {"_eq": "INV-001"}}
{"_and": [{"category": {"_eq": "IT"}}, {"location": {"_ilike": "%Lab%"}}]}
"""

    id: IDType
    name: str
    inventory_code: str
    description: str
    location: str
    category: str
    owner_group_id: IDType
    custodian_user_id: IDType


@strawberry.federation.type(
    description="Asset record representing a tangible item in the registry (e.g., notebook, monitor, tool).",
    keys=["id"],
)
class AssetGQLModel(BaseGQLModel):
    @classmethod
    def getLoader(cls, info: strawberry.types.Info):
        return getLoadersFromInfo(info).AssetModel

    name: typing.Optional[str] = strawberry.field(
        description="Human-readable name of the asset (e.g., 'Lenovo T14').",
        default=None,
        permission_classes=[OnlyForAuthentized],
    )

    inventory_code: typing.Optional[str] = strawberry.field(
        description="Inventory code or tag used for physical identification.",
        default=None,
        permission_classes=[OnlyForAuthentized],
    )

    description: typing.Optional[str] = strawberry.field(
        description="Additional description of the asset (configuration, notes).",
        default=None,
        permission_classes=[OnlyForAuthentized],
    )

    location: typing.Optional[str] = strawberry.field(
        description="Current declared location (room, lab, office).",
        default=None,
        permission_classes=[OnlyForAuthentized],
    )

    category: typing.Optional[str] = strawberry.field(
        description="Category/typology for the asset (e.g., IT, furniture).",
        default=None,
        permission_classes=[OnlyForAuthentized],
    )

    owner_group_id: typing.Optional[IDType] = strawberry.field(
        description="Group that owns the asset.",
        default=None,
        permission_classes=[OnlyForAuthentized],
        directives=[Relation(to="GroupGQLModel")],
    )

    custodian_user_id: typing.Optional[IDType] = strawberry.field(
        description="User responsible for the asset (custodian).",
        default=None,
        permission_classes=[OnlyForAuthentized],
        directives=[Relation(to="UserGQLModel")],
    )

    custodian_user: typing.Optional[UserGQLModel] = strawberry.field(
        description="User entity for the custodian responsible for the asset.",
        permission_classes=[OnlyForAuthentized],
        resolver=ScalarResolver[UserGQLModel](fkey_field_name="custodian_user_id"),
    )

    inventory_records: typing.List[AssetInventoryRecordGQLModel] = strawberry.field(
        description="Inventory records documenting physical checks of the asset.",
        permission_classes=[OnlyForAuthentized],
        resolver=VectorResolver[AssetInventoryRecordGQLModel](
            fkey_field_name="asset_id", whereType=AssetInventoryRecordInputFilter
        ),
    )

    loans: typing.List[AssetLoanGQLModel] = strawberry.field(
        description="Loan records capturing asset loans to users.",
        permission_classes=[OnlyForAuthentized],
        resolver=VectorResolver[AssetLoanGQLModel](
            fkey_field_name="asset_id", whereType=AssetLoanInputFilter
        ),
    )


@strawberry.interface(description="Asset queries")
class AssetQuery:
    asset_by_id: typing.Optional[AssetGQLModel] = strawberry.field(
        description="Get an asset by its id.",
        permission_classes=[OnlyForAuthentized],
        resolver=AssetGQLModel.load_with_loader,
    )

    asset_page: typing.List[AssetGQLModel] = strawberry.field(
        description="Get a page (vector) of assets filtered and ordered.",
        permission_classes=[OnlyForAuthentized],
        resolver=PageResolver[AssetGQLModel](whereType=AssetInputFilter),
    )


@strawberry.input(description="Asset insert mutation")
class AssetInsertGQLModel(InputModelMixin):
    getLoader = AssetGQLModel.getLoader

    id: typing.Optional[IDType] = strawberry.field(description="Asset id", default=None)
    name: typing.Optional[str] = strawberry.field(
        description="Human-readable name of the asset.", default=None
    )
    inventory_code: typing.Optional[str] = strawberry.field(
        description="Inventory code or tag.", default=None
    )
    description: typing.Optional[str] = strawberry.field(
        description="Additional description or notes.", default=None
    )
    location: typing.Optional[str] = strawberry.field(
        description="Declared location.", default=None
    )
    category: typing.Optional[str] = strawberry.field(
        description="Category/typology for reporting.", default=None
    )
    owner_group_id: typing.Optional[IDType] = strawberry.field(
        description="Owning group id.", default=None
    )
    custodian_user_id: typing.Optional[IDType] = strawberry.field(
        description="Responsible user id.", default=None
    )

    rbacobject_id: strawberry.Private[IDType] = None
    createdby_id: strawberry.Private[IDType] = None


@strawberry.input(description="Asset update mutation")
class AssetUpdateGQLModel(InputModelMixin):
    getLoader = AssetGQLModel.getLoader

    id: IDType = strawberry.field(description="Asset id")
    lastchange: datetime.datetime = strawberry.field(description="Concurrency token")
    name: typing.Optional[str] = strawberry.field(
        description="Updated name", default=None
    )
    inventory_code: typing.Optional[str] = strawberry.field(
        description="Updated inventory code", default=None
    )
    description: typing.Optional[str] = strawberry.field(
        description="Updated description", default=None
    )
    location: typing.Optional[str] = strawberry.field(
        description="Updated location", default=None
    )
    category: typing.Optional[str] = strawberry.field(
        description="Updated category", default=None
    )
    owner_group_id: typing.Optional[IDType] = strawberry.field(
        description="Updated owner group", default=None
    )
    custodian_user_id: typing.Optional[IDType] = strawberry.field(
        description="Updated custodian user", default=None
    )

    changedby_id: strawberry.Private[IDType] = None


@strawberry.input(description="Asset delete mutation")
class AssetDeleteGQLModel:
    id: IDType = strawberry.field(description="Asset id")
    lastchange: datetime.datetime = strawberry.field(description="Concurrency token")


@strawberry.type(description="Asset mutations")
class AssetMutation:
    @strawberry.field(
        description="Insert a new asset record.",
        permission_classes=[OnlyForAuthentized],
    )
    async def asset_insert(
        self, info: strawberry.types.Info, asset: AssetInsertGQLModel
    ) -> typing.Union[AssetGQLModel, AssetInsertErrorType]:
        ensure_user_in_context(info)
        result = await Insert[AssetGQLModel].DoItSafeWay(info=info, entity=asset)
        return result

    @strawberry.field(
        description="Update an existing asset record.",
        permission_classes=[OnlyForAuthentized],
    )
    async def asset_update(
        self, info: strawberry.types.Info, asset: AssetUpdateGQLModel
    ) -> typing.Union[AssetGQLModel, AssetUpdateErrorType]:
        ensure_user_in_context(info)
        result = await Update[AssetGQLModel].DoItSafeWay(info=info, entity=asset)
        return result

    @strawberry.field(
        description="Delete an asset record.",
        permission_classes=[OnlyForAuthentized],
    )
    async def asset_delete(
        self, info: strawberry.types.Info, asset: AssetDeleteGQLModel
    ) -> typing.Union[AssetGQLModel, AssetDeleteErrorType]:
        ensure_user_in_context(info)
        result = await Delete[AssetGQLModel].DoItSafeWay(info=info, entity=asset)
        if result is None:
            return AssetGQLModel(id=asset.id)
        return result
