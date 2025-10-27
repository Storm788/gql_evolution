import strawberry

from .EventGQLModel import EventQuery
from .EventInvitationGQLModel import EventInvitationQuery
from .AssetGQLModel import AssetQuery
from .AssetInventoryRecordGQLModel import AssetInventoryRecordQuery
from .AssetLoanGQLModel import AssetLoanQuery

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
