"""
Schema extension, která po RolePermissionSchemaExtension obnoví náš RBAC loader
(z systemdata), když v kontextu není ug_client (demo / lokální režim).

RolePermissionSchemaExtension při každém requestu přepisuje
context["userRolesForRBACQuery_loader"] na GraphQLBatchLoader volající externí
gql_ug službu. Pokud ug_client není nastaven, tento extension znovu nastaví
náš _UserRolesForRBACLoader, aby RBAC fungoval ze systemdata (x-demo-user-id).

Když WhoAmIExtension selže (UG endpoint nedostupný), přepíše context["user"] na {}.
V tom případě zde znovu nastavíme uživatele z x-demo-user-id a systemdata, aby
mutace (assetInsert atd.) prošly s oprávněním.
"""

from strawberry.extensions import SchemaExtension

from src.Utils.Dataloaders import (
    _UserRolesForRBACLoader,
    _extract_demo_user_id,
    _load_user_from_systemdata,
    _extract_user_id_from_jwt,
)


class DemoRBACLoaderExtension(SchemaExtension):
    async def on_execute(self):
        context = self.execution_context
        ctx = getattr(context, "context", None)
        if ctx is None:
            yield None
            return

        request = ctx.get("request")
        use_demo = ctx.get("use_demo_rbac_loader")
        user = ctx.get("user")
        user_has_id = user and isinstance(user, dict) and user.get("id")

        # Když máme demo režim (x-demo-user-id) a user byl přepsán bez id (UG selhal),
        # znovu načti uživatele z requestu a systemdata, aby RBAC a mutace prošly.
        if use_demo and request and not user_has_id:
            demo_user_id = _extract_demo_user_id(request)
            if demo_user_id:
                if demo_user_id.startswith("eyJ") or demo_user_id.startswith("Bearer ") or "eyJ" in demo_user_id:
                    user_id_from_jwt = _extract_user_id_from_jwt(demo_user_id)
                    if user_id_from_jwt:
                        user_data = _load_user_from_systemdata(user_id_from_jwt)
                        if user_data:
                            ctx["user"] = user_data
                            ctx["__original_user"] = user_data
                            ctx["user_roles"] = user_data.get("roles") or []
                        else:
                            ctx["user"] = {"id": user_id_from_jwt}
                            ctx["__original_user"] = {"id": user_id_from_jwt}
                    # else: JWT neparsovatelný, necháme user jak je
                else:
                    user_data = _load_user_from_systemdata(demo_user_id)
                    if user_data:
                        ctx["user"] = user_data
                        ctx["__original_user"] = user_data
                        ctx["user_roles"] = user_data.get("roles") or []
                    else:
                        ctx["user"] = {"id": demo_user_id}
                        ctx["__original_user"] = {"id": demo_user_id}
                user_has_id = True

        # Zajisti, že user má vždy klíč "id" (UserRoleProviderExtension volá user["id"]).
        if "user" in ctx and isinstance(ctx["user"], dict) and "id" not in ctx["user"]:
            ctx["user"]["id"] = None

        # Přepiš na náš loader ze systemdata, když: chybí ug_client NEBO request používá x-demo-user-id
        if ctx.get("ug_client") is None or use_demo:
            ctx["userRolesForRBACQuery_loader"] = _UserRolesForRBACLoader()
        yield None
