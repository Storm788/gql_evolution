import asyncio
import dataclasses
import datetime
import typing
import strawberry

import strawberry.types
from uoishelpers.gqlpermissions import (
    OnlyForAuthentized,
    SimpleInsertPermission, 
    SimpleUpdatePermission, 
    SimpleDeletePermission
)    
from uoishelpers.resolvers import (
    getLoadersFromInfo, 
    createInputs,
    createInputs2,

    InsertError, 
    Insert, 
    UpdateError, 
    Update, 
    DeleteError, 
    Delete,

    PageResolver,
    VectorResolver,
    ScalarResolver
)
from uoishelpers.gqlpermissions.LoadDataExtension import LoadDataExtension
from uoishelpers.gqlpermissions.RbacProviderExtension import RbacProviderExtension
from uoishelpers.gqlpermissions.RbacInsertProviderExtension import RbacInsertProviderExtension
from uoishelpers.gqlpermissions.UserRoleProviderExtension import UserRoleProviderExtension
from uoishelpers.gqlpermissions.UserAccessControlExtension import UserAccessControlExtension
from uoishelpers.gqlpermissions.UserAbsoluteAccessControlExtension import UserAbsoluteAccessControlExtension

from .BaseGQLModel import BaseGQLModel, IDType, Relation

@createInputs2
class DocumentInputFilter:
    name: str
    name_en: str
    description: str
    id: IDType
    

@strawberry.federation.type(
    description="""Entity representing a Document""",
    keys=["id"]
)
class DocumentGQLModel(BaseGQLModel):
    @classmethod
    def getLoader(cls, info: strawberry.types.Info):
        return getLoadersFromInfo(info).DocumentModel

    path: typing.Optional[str] = strawberry.field(
        description="""Materialized path representing the group's hierarchical location.""",
        default=None,
        permission_classes=[OnlyForAuthentized]
    )

    name: typing.Optional[str] = strawberry.field(
        default=None,
        description="""Document name assigned by an administrator""",
        permission_classes=[
            OnlyForAuthentized
        ]
    )

    name_en: typing.Optional[str] = strawberry.field(
        default=None,
        description="""Document eng name assigned by an administrator""",
        permission_classes=[
            OnlyForAuthentized
        ]
    )

    description: typing.Optional[str] = strawberry.field(
        default=None,
        description="""Document description""",
        permission_classes=[
            OnlyForAuthentized
        ]
    )

    masterdocument_id: typing.Optional[IDType] = strawberry.field(
        default=None,
        description="""Document parent id""",
        permission_classes=[
            OnlyForAuthentized
        ]
    )
    
    masterdocument: typing.Optional["DocumentGQLModel"] = strawberry.field(
        description="""Document which owns this particular document""",
        permission_classes=[
            OnlyForAuthentized
        ],
        resolver=ScalarResolver["DocumentGQLModel"](fkey_field_name="masterdocument_id")
    )

    subdocuments: typing.List["DocumentGQLModel"] = strawberry.field(
        description="""Document children""",
        permission_classes=[
            OnlyForAuthentized
        ],
        resolver=VectorResolver["DocumentGQLModel"](fkey_field_name="masterdocument_id", whereType=DocumentInputFilter)
    )



@strawberry.interface(
    description="""Document queries"""
)
class DocumentQuery:
    document_by_id: typing.Optional[DocumentGQLModel] = strawberry.field(
        description="""get a document by its id""",
        permission_classes=[OnlyForAuthentized],
        resolver=DocumentGQLModel.load_with_loader
    )

    document_page: typing.List[DocumentGQLModel] = strawberry.field(
        description="""get a page of documents""",
        permission_classes=[OnlyForAuthentized],
        resolver=PageResolver[DocumentGQLModel](whereType=DocumentInputFilter)
    )

from uoishelpers.resolvers import TreeInputStructureMixin, InputModelMixin
@strawberry.input(
    description="""Input type for creating a Document"""
)
class DocumentInsertGQLModel(TreeInputStructureMixin):
    getLoader = DocumentGQLModel.getLoader
    masterdocument_id: IDType = strawberry.field(
        description="""Document parent id""",
        # default=None
    )
    name: typing.Optional[str] = strawberry.field(
        description="""Document name assigned by an administrator""",
        default=None
    )
    name_en: typing.Optional[str] = strawberry.field(
        description="""Document eng name assigned by an administrator""",
        default=None
    )
    description: typing.Optional[str] = strawberry.field(
        description="""Document description""",
        default=None
    )
    id: typing.Optional[IDType] = strawberry.field(
        description="""Document id""",
        default=None
    )
    subdocuments: typing.Optional[typing.List["DocumentInsertGQLModel"]] = strawberry.field(
        description="sub documents",
        default_factory=list
    )

    rbacobject_id: strawberry.Private[IDType] = None
    createdby_id: strawberry.Private[IDType] = None


@strawberry.input(
    description="""Input type for updating a Document"""
)
class DocumentUpdateGQLModel:
    id: IDType = strawberry.field(
        description="""Document id""",
    )
    lastchange: datetime.datetime = strawberry.field(
        description="timestamp"
    )
    name: typing.Optional[str] = strawberry.field(
        description="""Document name assigned by an administrator""",
        default=None
    )
    name_en: typing.Optional[str] = strawberry.field(
        description="""Document eng name assigned by an administrator""",
        default=None
    )
    description: typing.Optional[str] = strawberry.field(
        description="""Document description""",
        default=None
    )
    startdate: typing.Optional[datetime.datetime] = strawberry.field(
        description="""Document start date""",
        default=None
    )
    enddate: typing.Optional[datetime.datetime] = strawberry.field(
        description="""Document end date""",
        default=None
    )
    # parent_id: typing.Optional[IDType] = strawberry.field(
    #     description="""Document parent id""",
    #     default=None
    # )
    changedby_id: strawberry.Private[IDType] = None

@strawberry.input(
    description="""Input type for deleting a Document"""
)
class DocumentDeleteGQLModel:
    id: IDType = strawberry.field(
        description="""Document id""",
    )
    lastchange: datetime.datetime = strawberry.field(
        description="""last change""",
    )

@strawberry.interface(
    description="""Document mutations"""
)
class DocumentMutation:
    @strawberry.mutation(
        description="""Insert a Document""",
        permission_classes=[
            OnlyForAuthentized
            # SimpleInsertPermission[DocumentGQLModel](roles=["administrátor"])
        ],
        extensions=[
            # UpdatePermissionCheckRoleFieldExtension[GroupGQLModel](roles=["administrátor", "personalista"]),
            UserAccessControlExtension[UpdateError, DocumentGQLModel](
                roles=[
                    "plánovací administrátor", 
                    # "personalista"
                ]
            ),
            UserRoleProviderExtension[UpdateError, DocumentGQLModel](),
            RbacProviderExtension[UpdateError, DocumentGQLModel](),
            LoadDataExtension[UpdateError, DocumentGQLModel](
                getLoader=DocumentGQLModel.getLoader,
                primary_key_name="masterdocument_id"
            )
        ],
    )
    async def document_insert(
        self,
        info: strawberry.Info,
        document: DocumentInsertGQLModel,
        db_row: typing.Any,
        rbacobject_id: IDType,
        user_roles: typing.List[dict],
    ) -> typing.Union[DocumentGQLModel, InsertError[DocumentGQLModel]]:
        return await Insert[DocumentGQLModel].DoItSafeWay(info=info, entity=document)
    
    

    @strawberry.mutation(
        description="""Update a Document""",
        permission_classes=[
            OnlyForAuthentized
            # SimpleUpdatePermission[DocumentGQLModel](roles=["administrátor"])
        ],
        extensions=[
            # UpdatePermissionCheckRoleFieldExtension[GroupGQLModel](roles=["administrátor", "personalista"]),
            UserAccessControlExtension[UpdateError, DocumentGQLModel](
                roles=[
                    "plánovací administrátor", 
                    # "personalista"
                ]
            ),
            UserRoleProviderExtension[UpdateError, DocumentGQLModel](),
            RbacProviderExtension[UpdateError, DocumentGQLModel](),
            LoadDataExtension[UpdateError, DocumentGQLModel]()
        ],
    )
    async def document_update(
        self,
        info: strawberry.Info,
        document: DocumentUpdateGQLModel
    ) -> typing.Union[DocumentGQLModel, UpdateError[DocumentGQLModel]]:
        return await Update[DocumentGQLModel].DoItSafeWay(info=info, entity=document)
    

    @strawberry.mutation(
        description="""Delete a Document""",
        permission_classes=[
            OnlyForAuthentized,
            # SimpleDeletePermission[DocumentGQLModel](roles=["administrátor"])
        ],
        extensions=[
            # UpdatePermissionCheckRoleFieldExtension[GroupGQLModel](roles=["administrátor", "personalista"]),
            UserAccessControlExtension[DeleteError, DocumentGQLModel](
                roles=[
                    "administrátor dokumentů", 
                    # "personalista"
                ]
            ),
            UserRoleProviderExtension[DeleteError, DocumentGQLModel](),
            RbacProviderExtension[DeleteError, DocumentGQLModel](),
            LoadDataExtension[DeleteError, DocumentGQLModel]()
        ],
    )   
    async def document_delete(
        self,
        info: strawberry.Info,
        document: DocumentDeleteGQLModel
    ) -> typing.Optional[DeleteError[DocumentGQLModel]]:
        return await Delete[DocumentGQLModel].DoItSafeWay(info=info, entity=document)
    