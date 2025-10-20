import strawberry
from strawberry.types import Info
from GraphTypeDefinitions.eventGQLModel import event_by_id, EventGQLModel
from .eventGQLModel import event_by_id
event_by_id = event_by_id

@strawberry.type(description="""Type for query root""")
class Query:
    @strawberry.field(
        description="""Returns hello world"""
        )
    async def hello(
        self,
        info: strawberry.types.Info,
    ) -> str:
        return "hello world"


    from .eventGQLModel import event_by_id
    event_by_id = event_by_id

schema = strawberry.federation.Schema(
    query=Query
)