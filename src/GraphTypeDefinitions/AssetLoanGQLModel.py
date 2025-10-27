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
class AssetLoanInputFilter:
    id: IDType
    asset_id: IDType
    borrower_user_id: IDType
    startdate: datetime.datetime
    enddate: datetime.datetime
    returned_date: datetime.datetime


@strawberry.federation.type(keys=["id"], description="Asset loan to a user")
class AssetLoanGQLModel(BaseGQLModel):
    @classmethod
    def getLoader(cls, info: strawberry.types.Info):
        return getLoadersFromInfo(info).AssetLoanModel

    asset_id: typing.Optional[IDType] = strawberry.field(
        description="Asset id",
        default=None,
        permission_classes=[OnlyForAuthentized],
        directives=[Relation(to="AssetGQLModel")]
    )
    borrower_user_id: typing.Optional[IDType] = strawberry.field(
        description="Borrower user id",
        default=None,
        permission_classes=[OnlyForAuthentized],
        directives=[Relation(to="UserGQLModel")]
    )
    startdate: typing.Optional[datetime.datetime] = strawberry.field(description="Loan start", default=None, permission_classes=[OnlyForAuthentized])
    enddate: typing.Optional[datetime.datetime] = strawberry.field(description="Loan end (expected)", default=None, permission_classes=[OnlyForAuthentized])
    returned_date: typing.Optional[datetime.datetime] = strawberry.field(description="Actual return date", default=None, permission_classes=[OnlyForAuthentized])
    note: typing.Optional[str] = strawberry.field(description="Note", default=None, permission_classes=[OnlyForAuthentized])

    asset: typing.Optional[AssetGQLModel] = strawberry.field(
        description="Asset",
        permission_classes=[OnlyForAuthentized],
        resolver=ScalarResolver[AssetGQLModel](fkey_field_name="asset_id")
    )
    borrower_user: typing.Optional[UserGQLModel] = strawberry.field(
        description="Borrowing user",
        permission_classes=[OnlyForAuthentized],
        resolver=ScalarResolver[UserGQLModel](fkey_field_name="borrower_user_id")
    )


@strawberry.type(description="Asset loan queries")
class AssetLoanQuery:
    asset_loan_by_id: typing.Optional[AssetLoanGQLModel] = strawberry.field(
        description="Get loan by id", permission_classes=[OnlyForAuthentized], resolver=AssetLoanGQLModel.load_with_loader
    )
    asset_loan_page: typing.List[AssetLoanGQLModel] = strawberry.field(
        description="Page of loans", permission_classes=[OnlyForAuthentized], resolver=PageResolver[AssetLoanGQLModel](whereType=AssetLoanInputFilter)
    )


from uoishelpers.resolvers import InputModelMixin


@strawberry.input(description="Asset loan insert input")
class AssetLoanInsertGQLModel(InputModelMixin):
    getLoader = AssetLoanGQLModel.getLoader
    id: typing.Optional[IDType] = strawberry.field(description="id", default=None)
    asset_id: IDType = strawberry.field(description="Asset id")
    borrower_user_id: typing.Optional[IDType] = strawberry.field(
        description="Borrower user id (defaults to current user)",
        default=None
    )
    startdate: typing.Optional[datetime.datetime] = strawberry.field(description="Loan start", default_factory=datetime.datetime.utcnow)
    enddate: typing.Optional[datetime.datetime] = strawberry.field(description="Loan end (expected)", default=None)
    returned_date: typing.Optional[datetime.datetime] = strawberry.field(description="Actual return date", default=None)
    note: typing.Optional[str] = strawberry.field(description="Note", default=None)

    rbacobject_id: strawberry.Private[IDType] = None
    createdby_id: strawberry.Private[IDType] = None


@strawberry.input(description="Asset loan update input")
class AssetLoanUpdateGQLModel(InputModelMixin):
    getLoader = AssetLoanGQLModel.getLoader
    id: IDType = strawberry.field(description="id")
    lastchange: datetime.datetime = strawberry.field(description="lastchange")
    enddate: typing.Optional[datetime.datetime] = strawberry.field(description="Loan end (expected)", default=None)
    returned_date: typing.Optional[datetime.datetime] = strawberry.field(description="Actual return date", default=None)
    note: typing.Optional[str] = strawberry.field(description="Note", default=None)

    changedby_id: strawberry.Private[IDType] = None


@strawberry.input(description="Asset loan delete input")
class AssetLoanDeleteGQLModel:
    id: IDType = strawberry.field(description="id")
    lastchange: datetime.datetime = strawberry.field(description="lastchange")


@strawberry.type(description="Outcome of loan mutations")
class AssetLoanMutationResult:
    id: typing.Optional[IDType] = strawberry.field(
        description="Identifier of the affected loan", default=None
    )
    msg: typing.Optional[str] = strawberry.field(
        description="Diagnostic information when operation fails", default=None
    )
    asset_loan: typing.Optional[AssetLoanGQLModel] = strawberry.field(
        description="Loan entity returned on success", default=None
    )


@strawberry.type(description="Outcome of loan delete operation")
class AssetLoanDeleteResult:
    id: typing.Optional[IDType] = strawberry.field(
        description="Identifier of the deleted loan", default=None
    )
    msg: typing.Optional[str] = strawberry.field(
        description="Diagnostic message", default=None
    )
    error: typing.Optional[DeleteError[AssetLoanGQLModel]] = strawberry.field(
        description="Detailed error payload", default=None
    )


@strawberry.type(description="Asset loan mutations")
class AssetLoanMutation:
    @strawberry.field(description="Insert loan", permission_classes=[OnlyForAuthentized])
    async def asset_loan_insert(self, info: strawberry.types.Info, loan: AssetLoanInsertGQLModel) -> AssetLoanMutationResult:
        ensure_user_in_context(info)
        result = await Insert[AssetLoanGQLModel].DoItSafeWay(info=info, entity=loan)
        if getattr(result, "failed", False):
            return AssetLoanMutationResult(
                id=None,
                msg=getattr(result, "msg", None),
                asset_loan=None
            )
        return AssetLoanMutationResult(id=result.id, msg=None, asset_loan=result)

    @strawberry.field(description="Update loan", permission_classes=[OnlyForAuthentized])
    async def asset_loan_update(self, info: strawberry.types.Info, loan: AssetLoanUpdateGQLModel) -> AssetLoanMutationResult:
        ensure_user_in_context(info)
        result = await Update[AssetLoanGQLModel].DoItSafeWay(info=info, entity=loan)
        if getattr(result, "failed", False):
            entity = getattr(result, "_entity", None)
            return AssetLoanMutationResult(
                id=None,
                msg=getattr(result, "msg", None),
                asset_loan=entity
            )
        return AssetLoanMutationResult(id=result.id, msg=None, asset_loan=result)

    @strawberry.field(description="Delete loan", permission_classes=[OnlyForAuthentized])
    async def asset_loan_delete(self, info: strawberry.types.Info, loan: AssetLoanDeleteGQLModel) -> AssetLoanDeleteResult:
        ensure_user_in_context(info)
        result = await Delete[AssetLoanGQLModel].DoItSafeWay(info=info, entity=loan)
        if result is None:
            return AssetLoanDeleteResult(id=loan.id, msg=None, error=None)
        return AssetLoanDeleteResult(id=None, msg=result.msg, error=result)
