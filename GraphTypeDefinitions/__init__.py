import strawberry

from .eventGQLModel import (
    EventGQLModel,
    event_by_id,
    event_insert,
    event_update,
    EventResultGQLModel,
)

from .userGQLModel import UserGQLModel
from .permissions import SensitiveInfo


@strawberry.type(description="Root Query for GraphQL API")
class Query:
    @strawberry.field(description="Simple hello world test")
    def hello(self) -> str:
        """Basic test field to verify API is running"""
        return "world"

    # Query field for fetching event by ID
    event_by_id = event_by_id


@strawberry.type(description="Root Mutation for GraphQL API")
class Mutation:
    # Mutation for inserting a new event
    event_insert = event_insert

    # Mutation for updating an existing event
    event_update = event_update


# Define schema with all GraphQL types included in federation
schema = strawberry.federation.Schema(
    query=Query,
    mutation=Mutation,
    types=[EventGQLModel, UserGQLModel],
)
