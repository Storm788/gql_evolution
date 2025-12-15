import strawberry

from .BaseGQLModel import IDType


@strawberry.federation.type(extend=True, keys=["id"], description="External user provided by UG service")
class UserGQLModel:
    id: IDType = strawberry.federation.field(external=True)

    @classmethod
    async def resolve_reference(cls, id: IDType):
        return cls(id=id)

