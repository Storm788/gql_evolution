import typing
import strawberry
from .BaseGQLModel import IDType

from .EventGQLModel import EventQuery
from .EventInvitationGQLModel import EventInvitationQuery
from .AssetGQLModel import AssetQuery
from .AssetInventoryRecordGQLModel import AssetInventoryRecordQuery
from .AssetLoanGQLModel import AssetLoanQuery
from .context_utils import ensure_user_in_context

@strawberry.type(description="Current authenticated user information")
class WhoAmIType:
    id: typing.Optional[str] = strawberry.field(description="User ID")
    email: typing.Optional[str] = strawberry.field(description="User email")
    name: typing.Optional[str] = strawberry.field(description="User first name")
    surname: typing.Optional[str] = strawberry.field(description="User last name")
    roles: typing.Optional[typing.List[strawberry.scalars.JSON]] = strawberry.field(
        description="User roles",
        default=None
    )

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

    @strawberry.field(name="whoAmI", description="Returns current authenticated user full info")
    async def who_am_i(self, info: strawberry.types.Info) -> typing.Optional[WhoAmIType]:
        """Returns current user id, email, name, surname or null if not authenticated."""
        try:
            user = ensure_user_in_context(info)
            if user is None or not user.get("id"):
                return None
            return WhoAmIType(
                id=str(user.get("id", "")) if user.get("id") else None,
                email=user.get("email"),
                name=user.get("name"),
                surname=user.get("surname"),
                roles=user.get("roles") or None
            )
        except Exception:
            raise