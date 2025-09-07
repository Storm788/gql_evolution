import typing
from ..server import mcp

@mcp.resource(
    uri="resource://graphql/query/{field_name}",
    description="returns sdl of the field of query type",
)
async def get_query_field(
    field_name: typing.Annotated[
        str,
        "the name of the query field"
    ]
):
    return f"neco {field_name}"
    pass