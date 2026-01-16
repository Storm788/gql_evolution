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
from .permissions import user_has_role, RequireAdmin, RequireEditor, RequireViewer
from src.error_codes import format_error_message
from uuid import UUID as ErrorCodeUUID


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


# @createInputs2  # Commented out to avoid Apollo Gateway syntax errors with multiline descriptions
@strawberry.input
class AssetInputFilter:

    id: typing.Optional[IDType] = None
    name: typing.Optional[str] = None
    inventory_code: typing.Optional[str] = None
    description: typing.Optional[str] = None
    location: typing.Optional[str] = None
    category: typing.Optional[str] = None
    owner_group_id: typing.Optional[IDType] = None
    custodian_user_id: typing.Optional[IDType] = None


@strawberry.federation.type(
    description="""Asset entity representing tangible physical items tracked in the organization's inventory system.
    Each asset has unique identification, ownership information, location tracking, and categorization.
    Assets can be assigned to custodians, loaned out to users, and regularly inventoried.
    Examples include: laptops, monitors, tools, furniture, vehicles, equipment.
    Supports full lifecycle management from acquisition to disposal.""",
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
    @strawberry.field(
        description="Get an asset by its id.",
        permission_classes=[OnlyForAuthentized],
    )
    async def asset_by_id(self, info: strawberry.types.Info, id: IDType) -> typing.Optional[AssetGQLModel]:
        """Admin vidí všechno; běžný uživatel jen assety, kde je custodian"""
        loader = getLoadersFromInfo(info).AssetModel
        row = await loader.load(id)
        if row is None:
            return None
        
        user = ensure_user_in_context(info)
        if user is None:
            return None
        
        # Admin vidí všechno
        if await user_has_role(user, "administrátor", info):
            return AssetGQLModel.from_dataclass(row)
        
        # Běžný uživatel vidí jen assety, kde je custodian
        if str(row.custodian_user_id) == str(user.get("id")):
            return AssetGQLModel.from_dataclass(row)
        
        return None

    @strawberry.field(
        description="Get a page (vector) of assets filtered and ordered.",
        permission_classes=[OnlyForAuthentized],
    )
    async def asset_page(
        self,
        info: strawberry.types.Info,
        skip: int = 0,
        limit: int = 10,
        orderby: typing.Optional[str] = None,
        where: typing.Optional[AssetInputFilter] = None,
    ) -> typing.List[AssetGQLModel]:
        """Admin vidí všechno; běžný uživatel jen assety, kde je custodian"""
        user = ensure_user_in_context(info)
        if user is None:
            return []
        
        loader = getLoadersFromInfo(info).AssetModel
        
        # Admin vidí všechno
        if await user_has_role(user, "administrátor", info):
            print(f"DEBUG asset_page: Admin - vracím všechny assety")
            results = await loader.page(skip=skip, limit=limit, orderby=orderby, where=where)
            return [AssetGQLModel.from_dataclass(row) for row in results]
        
        # Běžný uživatel vidí jen své assety (kde je custodian)
        uid = str(user.get("id"))
        print(f"DEBUG asset_page: Non-admin user {uid} - filtruje se podle custodian_user_id")
        
        try:
            user_uuid = IDType(uid)
            rows = await loader.filter_by(custodian_user_id=user_uuid)
            rows_list = list(rows)
            print(f"DEBUG: Nalezeno {len(rows_list)} assetů pro custodian {uid}")
            rows_list = rows_list[skip:skip+limit] if skip or limit else rows_list
            return [AssetGQLModel.from_dataclass(row) for row in rows_list]
        except Exception as e:
            print(f"ERROR filtering assets by custodian_user_id {uid}: {e}")
            return []


@strawberry.input
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


@strawberry.input
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


@strawberry.input
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
        user = ensure_user_in_context(info)
        if user is None:
            error_code = ErrorCodeUUID("1a0b1c2d-3e4f-4a5b-6c7d-8e9f0a1b2c3d")
            return AssetInsertErrorType(
                msg=format_error_message(error_code),
                code=error_code,
                _entity=None,
                _input=asset
            )
        
        # Only admin can create assets
        admin = await user_has_role(user, "administrátor", info)
        try:
            print(f"DEBUG asset_insert: user={user.get('id')} admin={admin}")
        except Exception:
            pass
        if not admin:
            error_code = ErrorCodeUUID("4a8b2c3d-5e6f-4b7c-9d0e-1f2a3b4c5d6e")
            return AssetInsertErrorType(
                msg=format_error_message(error_code),
                code=error_code,
                _entity=None,
                _input=asset
            )
        
        result = await Insert[AssetGQLModel].DoItSafeWay(info=info, entity=asset)
        return result

    @strawberry.field(
        description="Update an existing asset record.",
        permission_classes=[OnlyForAuthentized],
    )
    async def asset_update(
        self, info: strawberry.types.Info, asset: AssetUpdateGQLModel
    ) -> typing.Union[AssetGQLModel, AssetUpdateErrorType]:
        user = ensure_user_in_context(info)
        if user is None:
            error_code = ErrorCodeUUID("1a0b1c2d-3e4f-4a5b-6c7d-8e9f0a1b2c3d")
            return AssetUpdateErrorType(
                msg=format_error_message(error_code),
                code=error_code,
                _entity=None,
                _input=asset
            )
        
        admin = await user_has_role(user, "administrátor", info)
        try:
            print(f"DEBUG asset_update: user={user.get('id')} admin={admin}")
        except Exception:
            pass
        if not admin:
            error_code = ErrorCodeUUID("4a8b2c3d-5e6f-4b7c-9d0e-1f2a3b4c5d6f")
            return AssetUpdateErrorType(
                msg=format_error_message(error_code),
                code=error_code,
                _entity=None,
                _input=asset
            )
        
        result = await Update[AssetGQLModel].DoItSafeWay(info=info, entity=asset)
        return result

    @strawberry.field(
        description="Delete an asset record.",
        permission_classes=[OnlyForAuthentized],
    )
    async def asset_delete(
        self, info: strawberry.types.Info, asset: AssetDeleteGQLModel
    ) -> typing.Union[AssetGQLModel, AssetDeleteErrorType]:
        user = ensure_user_in_context(info)
        if user is None:
            error_code = ErrorCodeUUID("1a0b1c2d-3e4f-4a5b-6c7d-8e9f0a1b2c3d")
            return AssetDeleteErrorType(
                msg=format_error_message(error_code),
                code=error_code,
                _entity=None,
                _input=asset
            )
        
        admin = await user_has_role(user, "administrátor", info)
        try:
            print(f"DEBUG asset_delete: user={user.get('id')} admin={admin}")
        except Exception:
            pass
        if not admin:
            error_code = ErrorCodeUUID("4a8b2c3d-5e6f-4b7c-9d0e-1f2a3b4c5d70")
            return AssetDeleteErrorType(
                msg=format_error_message(error_code),
                code=error_code,
                _entity=None,
                _input=asset
            )
        result = await Delete[AssetGQLModel].DoItSafeWay(info=info, entity=asset)
        if result is None:
            return AssetGQLModel(id=asset.id)
        return result
