import typing
import fastmcp

from ..server import mcp

@mcp.prompt(
    description=()
)
async def identify_graphql_types(
    user_message: typing.Annotated[
        str,
        "Natural language query from user describing the data"
    ],
    ctx: fastmcp.Context
):
    result = [
        {
            "role": "assistant",
            "content": (
                "You are graphql endpoint expert. "
                "You are cappable to decide which graphql types are related to user question. "
                "\n"
                "The available types are: \n\n"
                # f"{json.dumps(graphql_types, indent=2, ensure_ascii=False)}"
            )
        }
    ]
    return result
