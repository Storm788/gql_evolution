import typing
import fastmcp

import graphql
from graphql.language import parse, InputObjectTypeDefinitionNode, InputValueDefinitionNode, NamedTypeNode, ListTypeNode, NonNullTypeNode, NullValueNode

from ..server import mcp
from .get_graphql_sdl import get_graphql_sdl


@mcp.resource(
    description="Returns the definition of a GraphQL input type, including its description and field list.",
    uri="resource://graphql/inputtype/{inputtype}",
    # uri="resource://graphql/inputtype/inputtype",
    mime_type="application/json",  # Explicit MIME type
    tags={"metadata"},  # Categorization tags
)
async def get_graphql_inputtypes(
    inputtype: typing.Annotated[
        str,
        "The name of the GraphQL input type"
    ],
    ctx: fastmcp.Context,
):
    # inputtype = "UserInputWhereFilter"

    def render_type(tnode) -> str:
        if isinstance(tnode, NonNullTypeNode):
            return f"{render_type(tnode.type)}!"
        if isinstance(tnode, ListTypeNode):
            return f"[{render_type(tnode.type)}]"
        if isinstance(tnode, NamedTypeNode):
            return tnode.name.value
        return str(tnode)
    
    def basic_type(tnode) -> str:
        if isinstance(tnode, NonNullTypeNode):
            return basic_type(tnode.type)
        if isinstance(tnode, ListTypeNode):
            return basic_type(tnode.type)
        if isinstance(tnode, NamedTypeNode):
            return tnode.name.value
        return str(tnode)
    
    sdl_ast = ctx.get_state("sdl_ast")
    if sdl_ast is None or isinstance(sdl_ast, str):
        sdl_ast = await get_graphql_sdl.fn(ctx)

    for node in sdl_ast.definitions:
        if isinstance(node, InputObjectTypeDefinitionNode) and node.name.value == inputtype:
            description = node.description.value if node.description else None
            fields = []
            for field in node.fields or []:
                assert isinstance(field, InputValueDefinitionNode)
                if default_value := getattr(field, "default_value", None):
                    if isinstance(default_value, NullValueNode):
                        default_value = None
                    else:
                        default_value = default_value.value
                fields.append({
                    "name": field.name.value,
                    "description": field.description.value if field.description else None,
                    "encapsulated_type": render_type(field.type),
                    "raw_type": basic_type(field.type),
                    "defaultValue": default_value,
                })
            return {
                "name": node.name.value,
                "description": description,
                "fields": fields,
            }

    # Pokud inputtype nenalezen
    return {
        "name": inputtype,
        "description": None,
        "fields": [],
        "error": f"Input type '{inputtype}' not found in schema",
    }
