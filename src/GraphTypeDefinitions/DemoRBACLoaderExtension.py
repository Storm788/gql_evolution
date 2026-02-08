"""
Schema extension, která po RolePermissionSchemaExtension obnoví náš RBAC loader
(z systemdata), když v kontextu není ug_client (demo / lokální režim).

RolePermissionSchemaExtension při každém requestu přepisuje
context["userRolesForRBACQuery_loader"] na GraphQLBatchLoader volající externí
gql_ug službu. Pokud ug_client není nastaven, tento extension znovu nastaví
náš _UserRolesForRBACLoader, aby RBAC fungoval ze systemdata (x-demo-user-id).
"""

from strawberry.extensions import SchemaExtension

from src.Utils.Dataloaders import _UserRolesForRBACLoader


class DemoRBACLoaderExtension(SchemaExtension):
    async def on_execute(self):
        context = self.execution_context
        ctx = getattr(context, "context", None)
        # Přepiš na náš loader ze systemdata, když: chybí ug_client NEBO request používá x-demo-user-id
        if ctx is not None and (ctx.get("ug_client") is None or ctx.get("use_demo_rbac_loader")):
            ctx["userRolesForRBACQuery_loader"] = _UserRolesForRBACLoader()
        yield None
