import typing
import strawberry
from .BaseGQLModel import IDType


from uoishelpers.gqlpermissions import (
    OnlyForAuthentized
)
from uoishelpers.resolvers import (
    VectorResolver,
    getLoadersFromInfo,
)
from .EventInvitationGQLModel import EventInvitationGQLModel, EventInvitationInputFilter
from .AssetGQLModel import AssetGQLModel, AssetInputFilter
from .AssetLoanGQLModel import AssetLoanGQLModel, AssetLoanInputFilter
EventGQLModel = typing.Annotated["EventGQLModel", strawberry.lazy(".EventGQLModel")]

@strawberry.federation.type(extend=True, keys=["id"])
class UserGQLModel:
    id: IDType = strawberry.federation.field(external=True)

    from .BaseGQLModel import resolve_reference

    event_invitations: typing.List[EventInvitationGQLModel] = strawberry.field(
        description="Links to events where the user has been invited",
        permission_classes=[
            OnlyForAuthentized
        ],
        resolver=VectorResolver[EventInvitationGQLModel](fkey_field_name="user_id", whereType=EventInvitationInputFilter)
    )

    # async def event_invitations(self, info:strawberry.types.Info)

    custodial_assets: typing.List[AssetGQLModel] = strawberry.field(
        description="Assets where user is custodian",
        permission_classes=[OnlyForAuthentized],
        resolver=VectorResolver[AssetGQLModel](fkey_field_name="custodian_user_id", whereType=AssetInputFilter)
    )

    borrowed_loans: typing.List[AssetLoanGQLModel] = strawberry.field(
        description="Loans borrowed by user",
        permission_classes=[OnlyForAuthentized],
        resolver=VectorResolver[AssetLoanGQLModel](fkey_field_name="borrower_user_id", whereType=AssetLoanInputFilter)
    )

    assets_custodian: typing.List[AssetGQLModel] = strawberry.field(
        description="Assets where this user is the custodian/responsible person.",
        permission_classes=[
            OnlyForAuthentized
        ],
        resolver=VectorResolver[AssetGQLModel](fkey_field_name="custodian_user_id", whereType=AssetInputFilter)
    )

    @strawberry.field(
        name="events",
        description="Events linked to the user (legacy compatibility field).",
        permission_classes=[OnlyForAuthentized]
    )
    async def events_legacy(
        self, info: strawberry.types.Info
    ) -> typing.List[EventGQLModel]:
        loader = getLoadersFromInfo(info).EventInvitationModel
        invitations_iter = await loader.filter_by(user_id=self.id)
        seen_event_ids = set()
        event_ids = []
        for invitation in list(invitations_iter):
            event_id = getattr(invitation, "event_id", None)
            if event_id is None or event_id in seen_event_ids:
                continue
            seen_event_ids.add(event_id)
            event_ids.append(event_id)

        results: typing.List[EventGQLModel] = []
        for event_id in event_ids:
            event = await EventGQLModel.load_with_loader(info=info, id=event_id)
            if event is not None:
                results.append(event)
        return results
