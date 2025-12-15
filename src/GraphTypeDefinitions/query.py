import strawberry

from .EventGQLModel import EventQuery
from .EventInvitationGQLModel import EventInvitationQuery
from .AssetGQLModel import AssetQuery
from .AssetInventoryRecordGQLModel import AssetInventoryRecordQuery
from .AssetLoanGQLModel import AssetLoanQuery
from .context_utils import ensure_user_in_context

@strawberry.type(description="""Type for query root""")
class Query(EventQuery, EventInvitationQuery, AssetQuery, AssetInventoryRecordQuery, AssetLoanQuery):
    @strawberry.field(
        description="""Returns hello world"""
        )
    async def hello(
        self,
        info: strawberry.types.Info,
    ) -> str:
        return "hello world"

    @strawberry.field(description="Returns id of current user if present")
    async def whoami(self, info: strawberry.types.Info) -> str | None:
        user = ensure_user_in_context(info)
        return None if user is None else user.get("id")
