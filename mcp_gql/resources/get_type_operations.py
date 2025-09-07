import typing
import fastmcp
from graphql.language import (
    parse,
    DocumentNode,
    ObjectTypeDefinitionNode,
    UnionTypeDefinitionNode,
    FieldDefinitionNode,
    InputValueDefinitionNode,
    NamedTypeNode,
    ListTypeNode,
    NonNullTypeNode,
)
from ..server import mcp
from .get_graphql_sdl import get_graphql_sdl


def _str_description(node) -> typing.Optional[str]:
    d = getattr(node, "description", None)
    return d.value if d is not None else None


def _render_type(tnode) -> str:
    if isinstance(tnode, NonNullTypeNode):
        return f"{_render_type(tnode.type)}!"
    if isinstance(tnode, ListTypeNode):
        return f"[{_render_type(tnode.type)}]"
    # Named
    return tnode.name.value  # type: ignore[attr-defined]


def _base_named_type(tnode) -> str:
    """Unwrap NonNull/List až na NamedType a vrať jeho jméno."""
    while isinstance(tnode, (NonNullTypeNode, ListTypeNode)):
        tnode = tnode.type
    assert isinstance(tnode, NamedTypeNode)
    return tnode.name.value


def _build_type_desc_index(doc: DocumentNode) -> dict[str, typing.Optional[str]]:
    """Mapa: název typu -> description (pokud existuje)."""
    out: dict[str, typing.Optional[str]] = {}
    for defn in doc.definitions:
        name = getattr(getattr(defn, "name", None), "value", None)
        if name:
            out[name] = _str_description(defn)
    return out


def _build_union_members_index(doc: DocumentNode) -> dict[str, set[str]]:
    """Map: unionName -> {memberTypeName, ...}"""
    idx: dict[str, set[str]] = {}
    for defn in doc.definitions:
        if isinstance(defn, UnionTypeDefinitionNode):
            u_name = defn.name.value
            members = set()
            for t in defn.types or []:
                members.add(t.name.value)
            idx[u_name] = members
    return idx


@mcp.resource(
    uri="resource://graphql/{gqltypename}/read/operations",
    description=(
        "Returns query fields whose return type is (directly or via wrappers) the given GraphQL type. "
        "Includes names, return types, descriptions, and argument details. "
        "If a field returns a union that includes the target type, the field is included as well."
    ),
)
async def get_type_operations(
    gqltypename: typing.Annotated[
        str,
        "Name of the GraphQL type. Returns query fields that directly or indirectly (list/nonnull) return this type; union members are considered too."
    ],
    ctx: fastmcp.Context,
):
    # gqltypename = "UserGQLModel"
    # AST v kontextu, jinak načíst SDL a zparsovat
    sdl_ast = ctx.get_state("sdl_ast")
    if sdl_ast is None or isinstance(sdl_ast, str):
        sdl_ast = await get_graphql_sdl.fn(ctx)

    type_desc_idx = _build_type_desc_index(sdl_ast)
    union_members_idx = _build_union_members_index(sdl_ast)

    # najdi definici Query
    query_def: typing.Optional[ObjectTypeDefinitionNode] = None
    for defn in sdl_ast.definitions:
        if isinstance(defn, ObjectTypeDefinitionNode) and defn.name.value == "Query":
            query_def = defn
            break

    if query_def is None:
        return {"type": gqltypename, "operations": []}

    def _collect_args(field: FieldDefinitionNode) -> list[dict]:
        args: list[dict] = []
        for arg in field.arguments or []:
            assert isinstance(arg, InputValueDefinitionNode)
            arg_named = _base_named_type(arg.type)
            args.append({
                "name": arg.name.value,
                "type": _render_type(arg.type),
                "description": _str_description(arg),
                "typeDescription": type_desc_idx.get(arg_named),
            })
        return args

    operations: list[dict] = []

    target = gqltypename
    for fld in query_def.fields or []:
        
        assert isinstance(fld, FieldDefinitionNode)
        ret_named = _base_named_type(fld.type)
        # print(f"{fld.name.value}: {ret_named} {ret_named==target} / {target}")
        include = False

        if ret_named == target:
            # print(f"operations: {True}")
            include = True
        elif ret_named in union_members_idx and target in union_members_idx[ret_named]:
            # návratový typ je union, který obsahuje cílový typ
            # print(f"operations: {True}")
            include = True

        if include:
            operations.append({
                "name": fld.name.value,
                "description": _str_description(fld),
                "type": _render_type(fld.type),
                "typeDescription": type_desc_idx.get(ret_named),
                "args": _collect_args(fld),
            })
    # print(f"operations: {operations}")
    return {"type": gqltypename, "operations": operations}
