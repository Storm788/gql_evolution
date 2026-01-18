import typing
import datetime
import strawberry
from uuid import UUID
from sqlalchemy import text

from uoishelpers.gqlpermissions import OnlyForAuthentized
from uoishelpers.resolvers import getLoadersFromInfo

from .BaseGQLModel import IDType
from .context_utils import ensure_user_in_context
from src.GraphTypeDefinitions.permissions import user_has_role, ADMINISTRATOR_ROLE_ID, EDITOR_ROLE_ID, VIEWER_ROLE_ID, READER_ROLE_ID, ROLE_NAME_TO_ID
from src.error_codes import format_error_message
from uuid import UUID as ErrorCodeUUID

# Default group ID (z dokumentace)
DEFAULT_GROUP_ID = UUID("f2f2d33c-38ee-4f31-9426-f364bc488032")


@strawberry.type(description="Role assignment result")
class RoleAssignmentGQLModel:
    id: IDType = strawberry.field(description="ID of the role assignment")
    user_id: IDType = strawberry.field(description="ID of the user")
    group_id: IDType = strawberry.field(description="ID of the group")
    roletype_id: IDType = strawberry.field(description="ID of the role type")
    valid: bool = strawberry.field(description="Whether the role assignment is valid")
    startdate: typing.Optional[datetime.datetime] = strawberry.field(description="Start date of the role")
    enddate: typing.Optional[datetime.datetime] = strawberry.field(description="End date of the role")


@strawberry.type(description="Error when assigning role")
class RoleAssignmentError:
    msg: str = strawberry.field(description="Error message")
    code: IDType = strawberry.field(description="Error code")


@strawberry.input(description="Input for assigning a role to a user")
class RoleAssignInputGQLModel:
    user_id: IDType = strawberry.field(description="ID of the user to assign role to")
    roletype_id: typing.Optional[IDType] = strawberry.field(default=None, description="ID of the role type (if not provided, role_name will be used)")
    role_name: typing.Optional[str] = strawberry.field(default=None, description="Name of the role (administrator, editor, viewer, čtenář)")
    group_id: typing.Optional[IDType] = strawberry.field(default=None, description="ID of the group (default will be used if not provided)")
    startdate: typing.Optional[datetime.datetime] = strawberry.field(default=None, description="Start date (defaults to now)")
    enddate: typing.Optional[datetime.datetime] = strawberry.field(default=None, description="End date (null = no end date)")


@strawberry.type(description="Role mutations")
class RoleMutation:
    @strawberry.field(
        description="Assign a role to yourself (for development/testing). Only works if you don't have any roles yet.",
        permission_classes=[OnlyForAuthentized]
    )
    async def role_assign_self(
        self,
        info: strawberry.types.Info,
        role_name: str
    ) -> typing.Union[RoleAssignmentGQLModel, RoleAssignmentError]:
        """
        Přiřadí roli aktuálně přihlášenému uživateli. Funguje pouze pokud uživatel ještě nemá žádnou roli.
        Pro development/testing účely.
        """
        user = ensure_user_in_context(info)
        if user is None:
            error_code = ErrorCodeUUID("1a0b1c2d-3e4f-4a5b-6c7d-8e9f0a1b2c3d")
            return RoleAssignmentError(
                msg="User is not authenticated.",
                code=error_code
            )

        user_id = user.get("id")
        if user_id is None:
            error_code = ErrorCodeUUID("1a0b1c2d-3e4f-4a5b-6c7d-8e9f0a1b2c3d")
            return RoleAssignmentError(
                msg="User ID is missing.",
                code=error_code
            )

        # Zkontrolovat, zda uživatel už nemá žádnou roli
        try:
            loaders = getLoadersFromInfo(info)
            session_maker = loaders.session_maker
            
            async with session_maker() as session:
                check_query = text("""
                    SELECT COUNT(*) FROM roles 
                    WHERE user_id = :user_id 
                    AND valid = true
                    AND (enddate IS NULL OR enddate >= NOW())
                """)
                result = await session.execute(
                    check_query,
                    {"user_id": str(user_id)}
                )
                count = result.scalar()
                
                if count > 0:
                    error_code = ErrorCodeUUID("7d8e9f0a-1b2c-4d3e-4f5a-6b7c8d9e0f1a")
                    return RoleAssignmentError(
                        msg="You already have a role assigned. Only users without roles can use this mutation.",
                        code=error_code
                    )

                # Převést název role na UUID
                role_name_lower = role_name.lower()
                roletype_id = ROLE_NAME_TO_ID.get(role_name_lower)
                if roletype_id is None:
                    error_code = ErrorCodeUUID("5b6c7d8e-9f0a-4b1c-2d3e-4f5a6b7c8d9e")
                    return RoleAssignmentError(
                        msg=f"Unknown role name: {role_name}. Valid roles: administrator, editor, viewer, čtenář",
                        code=error_code
                    )

                # Vytvořit nový záznam
                role_id = UUID()
                startdate = datetime.datetime.now()
                insert_query = text("""
                    INSERT INTO roles (id, user_id, group_id, roletype_id, valid, startdate, enddate, createdby_id, changedby_id, created, lastchange)
                    VALUES (:id, :user_id, :group_id, :roletype_id, :valid, :startdate, :enddate, :createdby_id, :changedby_id, NOW(), NOW())
                """)
                
                await session.execute(
                    insert_query,
                    {
                        "id": str(role_id),
                        "user_id": str(user_id),
                        "group_id": str(DEFAULT_GROUP_ID),
                        "roletype_id": str(roletype_id),
                        "valid": True,
                        "startdate": startdate,
                        "enddate": None,
                        "createdby_id": str(user_id),
                        "changedby_id": str(user_id)
                    }
                )
                await session.commit()

                return RoleAssignmentGQLModel(
                    id=role_id,
                    user_id=UUID(str(user_id)),
                    group_id=DEFAULT_GROUP_ID,
                    roletype_id=roletype_id,
                    valid=True,
                    startdate=startdate,
                    enddate=None
                )

        except Exception as e:
            error_code = ErrorCodeUUID("6c7d8e9f-0a1b-4c2d-3e4f-5a6b7c8d9e0f")
            return RoleAssignmentError(
                msg=f"Failed to assign role: {str(e)}",
                code=error_code
            )

    @strawberry.field(
        description="Assign a role to a user. Only administrators can assign roles.",
        permission_classes=[OnlyForAuthentized]
    )
    async def role_assign(
        self,
        info: strawberry.types.Info,
        input: RoleAssignInputGQLModel
    ) -> typing.Union[RoleAssignmentGQLModel, RoleAssignmentError]:
        """
        Přiřadí roli uživateli. Pouze administrátoři mohou přiřazovat role.
        """
        user = ensure_user_in_context(info)
        if user is None:
            error_code = ErrorCodeUUID("1a0b1c2d-3e4f-4a5b-6c7d-8e9f0a1b2c3d")
            return RoleAssignmentError(
                msg="User is not authenticated.",
                code=error_code
            )

        # Pouze administrátoři mohou přiřazovat role
        has_admin_role = await user_has_role(user, "administrátor", info)
        if not has_admin_role:
            error_code = ErrorCodeUUID("3f7a1b2c-4e5d-4a6b-8c9d-0e1f2a3b4c5d")
            return RoleAssignmentError(
                msg="Permission denied: Only administrators can assign roles.",
                code=error_code
            )

        # Zjistit roletype_id
        roletype_id = input.roletype_id
        if roletype_id is None:
            if input.role_name is None:
                error_code = ErrorCodeUUID("4a5b6c7d-8e9f-4a0b-1c2d-3e4f5a6b7c8d")
                return RoleAssignmentError(
                    msg="Either roletype_id or role_name must be provided.",
                    code=error_code
                )
            
            # Převést název role na UUID
            role_name_lower = input.role_name.lower()
            roletype_id = ROLE_NAME_TO_ID.get(role_name_lower)
            if roletype_id is None:
                error_code = ErrorCodeUUID("5b6c7d8e-9f0a-4b1c-2d3e-4f5a6b7c8d9e")
                return RoleAssignmentError(
                    msg=f"Unknown role name: {input.role_name}. Valid roles: administrator, editor, viewer, čtenář",
                    code=error_code
                )

        # Použít default group_id pokud není zadán
        group_id = input.group_id if input.group_id is not None else DEFAULT_GROUP_ID

        # Použít aktuální čas jako startdate pokud není zadán
        startdate = input.startdate if input.startdate is not None else datetime.datetime.now()

        try:
            loaders = getLoadersFromInfo(info)
            session_maker = loaders.session_maker
            
            async with session_maker() as session:
                # Zkontrolovat, zda uživatel už nemá tuto roli
                check_query = text("""
                    SELECT id FROM roles 
                    WHERE user_id = :user_id 
                    AND roletype_id = :roletype_id 
                    AND group_id = :group_id
                    AND valid = true
                    AND (enddate IS NULL OR enddate >= NOW())
                """)
                result = await session.execute(
                    check_query,
                    {
                        "user_id": str(input.user_id),
                        "roletype_id": str(roletype_id),
                        "group_id": str(group_id)
                    }
                )
                existing = result.fetchone()
                
                if existing:
                    # Role už existuje, vrátit existující záznam
                    role_id = existing[0]
                    select_query = text("""
                        SELECT id, user_id, group_id, roletype_id, valid, startdate, enddate
                        FROM roles
                        WHERE id = :role_id
                    """)
                    result = await session.execute(select_query, {"role_id": str(role_id)})
                    row = result.fetchone()
                    
                    return RoleAssignmentGQLModel(
                        id=UUID(row[0]),
                        user_id=UUID(row[1]),
                        group_id=UUID(row[2]),
                        roletype_id=UUID(row[3]),
                        valid=row[4],
                        startdate=row[5],
                        enddate=row[6]
                    )

                # Vytvořit nový záznam
                role_id = UUID()
                insert_query = text("""
                    INSERT INTO roles (id, user_id, group_id, roletype_id, valid, startdate, enddate, createdby_id, changedby_id, created, lastchange)
                    VALUES (:id, :user_id, :group_id, :roletype_id, :valid, :startdate, :enddate, :createdby_id, :changedby_id, NOW(), NOW())
                """)
                
                await session.execute(
                    insert_query,
                    {
                        "id": str(role_id),
                        "user_id": str(input.user_id),
                        "group_id": str(group_id),
                        "roletype_id": str(roletype_id),
                        "valid": True,
                        "startdate": startdate,
                        "enddate": input.enddate,
                        "createdby_id": str(user.get("id")),
                        "changedby_id": str(user.get("id"))
                    }
                )
                await session.commit()

                return RoleAssignmentGQLModel(
                    id=role_id,
                    user_id=input.user_id,
                    group_id=group_id,
                    roletype_id=roletype_id,
                    valid=True,
                    startdate=startdate,
                    enddate=input.enddate
                )

        except Exception as e:
            error_code = ErrorCodeUUID("6c7d8e9f-0a1b-4c2d-3e4f-5a6b7c8d9e0f")
            return RoleAssignmentError(
                msg=f"Failed to assign role: {str(e)}",
                code=error_code
            )
