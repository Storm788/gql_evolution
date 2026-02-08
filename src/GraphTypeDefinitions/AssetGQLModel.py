import typing
import datetime
import strawberry

from uoishelpers.gqlpermissions import OnlyForAuthentized
from uoishelpers.gqlpermissions.LoadDataExtension import LoadDataExtension
from uoishelpers.gqlpermissions.RbacProviderExtension import RbacProviderExtension
from uoishelpers.gqlpermissions.RbacInsertProviderExtension import RbacInsertProviderExtension
from uoishelpers.gqlpermissions.UserRoleProviderExtension import UserRoleProviderExtension
from uoishelpers.gqlpermissions.UserAccessControlExtension import UserAccessControlExtension
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
        return getLoadersFromInfo(info)["AssetModel"]

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

    @strawberry.field(
        description="Loan records capturing asset loans to users. Admin vidí všechny půjčky k assetu, běžný uživatel jen své (kde je borrower).",
        permission_classes=[OnlyForAuthentized],
    )
    async def loans(
        self,
        info: strawberry.types.Info,
        where: typing.Optional[AssetLoanInputFilter] = None,
    ) -> typing.List[AssetLoanGQLModel]:
        """Admin: všechny půjčky k tomuto assetu. Ne-admin: jen půjčky, kde je borrower aktuální uživatel."""
        if self.id is None:
            return []
        user = ensure_user_in_context(info)
        if user is None:
            return []
        # Použij konkrétní třídu (ne ForwardRef) pro from_dataclass
        from .AssetLoanGQLModel import AssetLoanGQLModel as AssetLoanGQLModelConcrete
        loader = getLoadersFromInfo(info)["AssetLoanModel"]
        is_admin = await user_has_role(user, "administrátor", info)
        asset_id = IDType(str(self.id))
        if is_admin:
            rows = await loader.filter_by(asset_id=asset_id)
            rows_list = list(rows)
        else:
            uid = str(user.get("id"))
            rows = await loader.filter_by(asset_id=asset_id, borrower_user_id=IDType(uid))
            rows_list = list(rows)
        return [AssetLoanGQLModelConcrete.from_dataclass(row) for row in rows_list]


@strawberry.interface(description="Asset queries")
class AssetQuery:
    @strawberry.field(
        description="Get an asset by its id.",
        permission_classes=[OnlyForAuthentized],
    )
    async def asset_by_id(self, info: strawberry.types.Info, id: IDType) -> typing.Optional[AssetGQLModel]:
        """Admin vidí všechno; běžný uživatel jen assety, kde je custodian"""
        loader = getLoadersFromInfo(info)["AssetModel"]
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
        """Admin vidí všechno; běžný uživatel vidí assety, kde je custodian, nebo které má vypůjčené (půjčka)."""
        user = ensure_user_in_context(info)
        if user is None:
            return []
        user_id = user.get("id")
        loader = getLoadersFromInfo(info)["AssetModel"]
        loan_loader = getLoadersFromInfo(info)["AssetLoanModel"]
        is_admin = await user_has_role(user, "administrátor", info)
        if is_admin:
            results = await loader.page(skip=skip, limit=limit, orderby=orderby, where=where)
            results_list = list(results) if hasattr(results, '__iter__') and not isinstance(results, (list, tuple)) else results
            return [AssetGQLModel.from_dataclass(row) for row in results_list]
        try:
            user_uuid = IDType(str(user_id))
            # Assety, kde je uživatel custodian
            custodian_rows = await loader.filter_by(custodian_user_id=user_uuid)
            custodian_list = list(custodian_rows)
            seen_ids = {str(row.id) for row in custodian_list}
            # Assety, které má uživatel vypůjčené (půjčka) – načti i když záznam assetu chybí (stub)
            loan_rows = await loan_loader.filter_by(borrower_user_id=user_uuid)
            for loan in loan_rows:
                if not loan.asset_id:
                    continue
                aid_str = str(loan.asset_id)
                if aid_str in seen_ids:
                    continue
                asset_id_typed = IDType(aid_str)
                asset = await loader.load(asset_id_typed)
                if asset is not None:
                    custodian_list.append(asset)
                    seen_ids.add(aid_str)
                else:
                    # Asset v DB není (nová půjčka, jiný zdroj dat) – přidej stub, aby uživatel půjčku viděl
                    stub = AssetGQLModel(
                        id=asset_id_typed,
                        name=f"Asset ({aid_str[:8]}…)",
                        lastchange=None,
                        created=None,
                        createdby_id=None,
                        changedby_id=None,
                        inventory_code=None,
                        description=None,
                        location=None,
                        category=None,
                        owner_group_id=None,
                        custodian_user_id=None,
                    )
                    custodian_list.append(stub)
                    seen_ids.add(aid_str)
            rows_list = custodian_list[skip:skip + limit] if skip or limit else custodian_list
            out = []
            for row in rows_list:
                if isinstance(row, AssetGQLModel):
                    out.append(row)
                else:
                    out.append(AssetGQLModel.from_dataclass(row))
            return out
        except Exception:
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

    rbacobject_id: strawberry.Private[IDType] = IDType("d75d64a4-bf5f-43c5-9c14-8fda7aff6c09")
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


@strawberry.interface(description="Asset mutations")
class AssetMutation:
    @strawberry.mutation(
        description="Insert a new asset record.",
        permission_classes=[OnlyForAuthentized],
        extensions=[
            UserAccessControlExtension[InsertError, AssetGQLModel](
                roles=["administrátor"]
            ),
            UserRoleProviderExtension[InsertError, AssetGQLModel](),
            RbacInsertProviderExtension[InsertError, AssetGQLModel](
                rbac_key_name="rbacobject_id"
            ),
        ],
    )
    async def asset_insert(
        self,
        info: strawberry.Info,
        asset: AssetInsertGQLModel,
        rbacobject_id: IDType,
        user_roles: typing.List[dict],
    ) -> typing.Union[AssetGQLModel, AssetInsertErrorType]:
        return await Insert[AssetGQLModel].DoItSafeWay(info=info, entity=asset)

    @strawberry.mutation(
        description="Update an existing asset record.",
        permission_classes=[OnlyForAuthentized],
        extensions=[
            UserAccessControlExtension[UpdateError, AssetGQLModel](
                roles=["administrátor"]
            ),
            UserRoleProviderExtension[UpdateError, AssetGQLModel](),
            RbacProviderExtension[UpdateError, AssetGQLModel](),
            LoadDataExtension[UpdateError, AssetGQLModel](),
        ],
    )
    async def asset_update(
        self,
        info: strawberry.Info,
        asset: AssetUpdateGQLModel,
        db_row: typing.Any,
        rbacobject_id: IDType,
        user_roles: typing.List[dict],
    ) -> typing.Union[AssetGQLModel, AssetUpdateErrorType]:
        return await Update[AssetGQLModel].DoItSafeWay(info=info, entity=asset)

    @strawberry.mutation(
        description="Delete an asset record.",
        permission_classes=[OnlyForAuthentized],
        extensions=[
            UserAccessControlExtension[DeleteError, AssetGQLModel](
                roles=["administrátor"]
            ),
            UserRoleProviderExtension[DeleteError, AssetGQLModel](),
            RbacProviderExtension[DeleteError, AssetGQLModel](),
            LoadDataExtension[DeleteError, AssetGQLModel](),
        ],
    )
    async def asset_delete(
        self,
        info: strawberry.Info,
        asset: AssetDeleteGQLModel,
        db_row: typing.Any,
        rbacobject_id: IDType,
        user_roles: typing.List[dict],
    ) -> typing.Optional[DeleteError[AssetGQLModel]]:
        return await Delete[AssetGQLModel].DoItSafeWay(info=info, entity=asset)
