import typing
import strawberry
from .BaseGQLModel import IDType


from uoishelpers.gqlpermissions import (
    OnlyForAuthentized
)
from uoishelpers.resolvers import (
    VectorResolver
)
from .EventInvitationGQLModel import EventInvitationGQLModel, EventInvitationInputFilter
from .AssetLoanGQLModel import AssetLoanGQLModel, AssetLoanInputFilter
from .AssetInventoryRecordGQLModel import AssetInventoryRecordGQLModel, AssetInventoryRecordInputFilter

@strawberry.federation.type(extend=True, keys=["id"])
class UserGQLModel:
    id: IDType = strawberry.federation.field(external=True)

    @classmethod
    async def resolve_reference(cls, id: IDType):
        return cls(id=id)

    event_invitations: typing.List[EventInvitationGQLModel] = strawberry.field(
        description="Links to events where the user has been invited",
        permission_classes=[
            OnlyForAuthentized
        ],
        resolver=VectorResolver[EventInvitationGQLModel](fkey_field_name="user_id", whereType=EventInvitationInputFilter)
    )

    asset_loans: typing.List[AssetLoanGQLModel] = strawberry.field(
        description="Loans of assets to the user",
        permission_classes=[
            OnlyForAuthentized
        ],
        resolver=VectorResolver[AssetLoanGQLModel](fkey_field_name="borrower_user_id", whereType=AssetLoanInputFilter)
    )

    asset_inventory_records: typing.List[AssetInventoryRecordGQLModel] = strawberry.field(
        description="Inventory records checked by the user",
        permission_classes=[
            OnlyForAuthentized
        ],
        resolver=VectorResolver[AssetInventoryRecordGQLModel](fkey_field_name="checked_by_user_id", whereType=AssetInventoryRecordInputFilter)
    )

    # Note: The 'roles' field is provided by the 'ug' subgraph as [RoleGQLModel!]!
    # We removed the duplicate definition here to avoid Apollo Federation composition errors.
    # If you need roles from systemdata, use the 'roles' field from the 'ug' subgraph instead.