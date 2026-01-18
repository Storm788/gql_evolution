import strawberry


from .EventGQLModel import EventMutation
from .EventInvitationGQLModel import EventInvitationMutation
from .AssetGQLModel import AssetMutation
from .AssetInventoryRecordGQLModel import AssetInventoryRecordMutation
from .AssetLoanGQLModel import AssetLoanMutation
from .RoleGQLModel import RoleMutation

@strawberry.type(description="""Type for mutation root""")
class Mutation(EventMutation, EventInvitationMutation, AssetMutation, AssetInventoryRecordMutation, AssetLoanMutation, RoleMutation):
    pass