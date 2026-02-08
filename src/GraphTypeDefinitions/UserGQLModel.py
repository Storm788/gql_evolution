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
from .AssetLoanGQLModel import AssetLoanGQLModel, AssetLoanInputFilter
from .AssetInventoryRecordGQLModel import AssetInventoryRecordGQLModel, AssetInventoryRecordInputFilter

# Federation @override: role z evolution (systemdata + DB) mají přednost před ug, aby se zobrazily na /ug/user/view/
_OVERRIDE_FROM_UG = "ug"


@strawberry.federation.type(extend=True, keys=["id"])
class UserGQLModel:
    id: IDType = strawberry.federation.field(external=True)

    @classmethod
    async def resolve_reference(cls, info: strawberry.types.Info, id: IDType):
        if id is None:
            return None
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

    @strawberry.federation.field(
        description="User roles (from systemdata + DB). Overrides ug so /ug/user/view/ shows roles.",
        permission_classes=[OnlyForAuthentized],
        override=_OVERRIDE_FROM_UG,
    )
    async def roles(
        self,
        info: strawberry.types.Info,
    ) -> typing.List[strawberry.scalars.JSON]:
        """Vrací role uživatele ze systemdata a z DB (tabulka roles), aby se zobrazily na stránce /ug/user/view/."""
        if self.id is None:
            return []
        from src.Utils.Dataloaders import _load_user_roles_from_systemdata, load_user_roles_from_db
        user_id = str(self.id)
        roles_systemdata = _load_user_roles_from_systemdata(user_id)
        loaders = getLoadersFromInfo(info)
        session_maker = getattr(loaders, "session_maker", None)
        roles_db = await load_user_roles_from_db(session_maker, user_id) if session_maker else []
        seen_rt = {str(r.get("roletype_id")) for r in roles_systemdata if r.get("roletype_id")}
        merged = list(roles_systemdata)
        for r in roles_db:
            rt_id = str(r.get("roletype_id")) if r.get("roletype_id") else None
            if rt_id and rt_id not in seen_rt:
                seen_rt.add(rt_id)
                merged.append(r)
        return merged if merged else []