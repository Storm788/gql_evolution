import typing
import strawberry

from uoishelpers.gqlpermissions import (
    OnlyForAuthentized,
)
from uoishelpers.resolvers import (
    VectorResolver,
)

from .BaseGQLModel import IDType
from .AssetGQLModel import AssetGQLModel, AssetInputFilter


@strawberry.federation.type(extend=True, keys=["id"])
class GroupGQLModel:
    id: IDType = strawberry.federation.field(external=True)

    from .BaseGQLModel import resolve_reference

    assets_owned: typing.List[AssetGQLModel] = strawberry.field(
        description="Assets owned by this group.",
        permission_classes=[OnlyForAuthentized],
        resolver=VectorResolver[AssetGQLModel](fkey_field_name="owner_group_id", whereType=AssetInputFilter),
    )

