import fastmcp
from graphql.language import parse, ObjectTypeDefinitionNode
from typing import Dict, List, Any, Optional
from graphql.language import (
    parse,
    ObjectTypeDefinitionNode,
    InputObjectTypeDefinitionNode,
    InterfaceTypeDefinitionNode,
    UnionTypeDefinitionNode,
    EnumTypeDefinitionNode,
    ScalarTypeDefinitionNode,
    FieldDefinitionNode,
    InputValueDefinitionNode,
    NamedTypeNode,
    ListTypeNode,
    NonNullTypeNode,
    DocumentNode,
)

from ..server import mcp
from .get_graphql_sdl import get_graphql_sdl


def _str_description(node) -> Optional[str]:
    """Return plain string description if present."""
    if getattr(node, "description", None) is not None:
        # description je StringValueNode
        return node.description.value
    return None


def _render_type(tnode) -> str:
    """Stringify GraphQL type AST (handles NonNull/List/Nameds)."""
    if isinstance(tnode, NonNullTypeNode):
        return f"{_render_type(tnode.type)}!"
    if isinstance(tnode, ListTypeNode):
        return f"[{_render_type(tnode.type)}]"
    # Named
    return tnode.name.value  # type: ignore[attr-defined]


def _base_named_type(tnode) -> str:
    """Get the underlying NamedType name (unwrap NonNull/List)."""
    while isinstance(tnode, (NonNullTypeNode, ListTypeNode)):
        tnode = tnode.type
    assert isinstance(tnode, NamedTypeNode)
    return tnode.name.value


def _build_type_description_index(doc: DocumentNode) -> Dict[str, Optional[str]]:
    """Map type name -> description from all definic typů v dokumentu."""
    index: Dict[str, Optional[str]] = {}
    for defn in doc.definitions:
        if isinstance(defn, (
            ObjectTypeDefinitionNode,
            InputObjectTypeDefinitionNode,
            InterfaceTypeDefinitionNode,
            UnionTypeDefinitionNode,
            EnumTypeDefinitionNode,
            ScalarTypeDefinitionNode,
        )):
            index[defn.name.value] = _str_description(defn)
    return index


def _str_description(node) -> Optional[str]:
    """Return plain string description if present."""
    if getattr(node, "description", None) is not None:
        # description je StringValueNode
        return node.description.value
    return None


def _render_type(tnode) -> str:
    """Stringify GraphQL type AST (handles NonNull/List/Nameds)."""
    if isinstance(tnode, NonNullTypeNode):
        return f"{_render_type(tnode.type)}!"
    if isinstance(tnode, ListTypeNode):
        return f"[{_render_type(tnode.type)}]"
    # Named
    return tnode.name.value  # type: ignore[attr-defined]


def _base_named_type(tnode) -> str:
    """Get the underlying NamedType name (unwrap NonNull/List)."""
    while isinstance(tnode, (NonNullTypeNode, ListTypeNode)):
        tnode = tnode.type
    assert isinstance(tnode, NamedTypeNode)
    return tnode.name.value


def _build_type_description_index(doc: DocumentNode) -> Dict[str, Optional[str]]:
    """Map type name -> description from all definic typů v dokumentu."""
    index: Dict[str, Optional[str]] = {}
    for defn in doc.definitions:
        if isinstance(defn, (
            ObjectTypeDefinitionNode,
            InputObjectTypeDefinitionNode,
            InterfaceTypeDefinitionNode,
            UnionTypeDefinitionNode,
            EnumTypeDefinitionNode,
            ScalarTypeDefinitionNode,
        )):
            index[defn.name.value] = _str_description(defn)
    return index


@mcp.resource(
    uri="resource://graphql/operations",
    description=(
        "Returns the list of fields on Query and Mutation types. "
        "Includes names, types, arguments, and descriptions where available."
    ),
)
async def get_available_operations(ctx: fastmcp.Context):
    # AST v kontextu, jinak načíst SDL a zparsovat
    sdl_ast = ctx.get_state("sdl_ast")
    if sdl_ast is None:
        sdl_ast = await get_graphql_sdl.fn(ctx)
        

    # index popisů typů (pro description návratových typů)
    type_desc_idx = _build_type_description_index(sdl_ast)

    def collect_fields(defn: ObjectTypeDefinitionNode) -> List[Dict[str, Any]]:
        out: List[Dict[str, Any]] = []
        for field in defn.fields or []:
            assert isinstance(field, FieldDefinitionNode)
            # Field basics
            field_name = field.name.value
            field_desc = _str_description(field)
            return_type_str = _render_type(field.type)
            return_type_named = _base_named_type(field.type)
            return_type_desc = type_desc_idx.get(return_type_named)

            # Arguments
            args_list: List[Dict[str, Any]] = []
            for arg in field.arguments or []:
                assert isinstance(arg, InputValueDefinitionNode)
                arg_name = arg.name.value
                arg_type_str = _render_type(arg.type)
                arg_named = _base_named_type(arg.type)
                arg_type_desc = type_desc_idx.get(arg_named)
                args_list.append({
                    "name": arg_name,
                    "type": arg_type_str,
                    "description": _str_description(arg),
                    "typeDescription": arg_type_desc,
                })

            out.append({
                "name": field_name,
                "description": field_desc,
                "type": return_type_str,
                "typeDescription": return_type_desc,
                "args": args_list,
            })
        return out

    operations: Dict[str, List[Dict[str, Any]]] = {"query": [], "mutation": []}

    for defn in sdl_ast.definitions:
        if isinstance(defn, ObjectTypeDefinitionNode):
            if defn.name.value == "Query":
                operations["query"] = collect_fields(defn)
            elif defn.name.value == "Mutation":
                operations["mutation"] = collect_fields(defn)

    return operations