import typing
import json

# region mcp
import fastmcp
from fastmcp import FastMCP, Client
from fastmcp.tools.tool import ToolResult, TextContent

# MCP server instance
mcp = FastMCP("My MCP Server")

# Definice toolu
# @mcp.tool(
#     description="return the given text back"
# )
# def echo(text: str, ctx: fastmcp.Context) -> str:
#     """Return the same text back."""
#     return text

# @mcp.resource(
#     uri="resource://{name}/page",
#     mime_type="application/json", # Explicit MIME type
#     tags={"data"}, # Categorization tags
#     meta={"version": "2.1", "team": "infrastructure"}  # Custom metadata
# )
# async def get_details(name: str, ctx: fastmcp.Context) -> dict:
#     """Get details for a specific name."""
#     return {
#         "name": name,
#         "accessed_at": ctx.request_id
#     }

# @mcp.prompt
# def ask_about_topic(topic: str, ctx: fastmcp.Context) -> str:
#     """Generates a user message asking for an explanation of a topic."""
#     return f"Can you please explain the concept of '{topic}'?"

@mcp.prompt(
    description="builds system prompt for appropriate tool selection",
    # uri="prompt://recognizetool"
)
async def get_use_tools(tools: list[dict]) -> str:
    
    toolsstr = json.dumps(tools, indent=2)
#     prompt = ("""
# # Instructions
              
# Choose if a tool defined by mcp server will be called or you can respond to user query.
# You can either answer directly or call exactly one tool.
                    
# ## Responses
              
# If you suggest to call the tool, the response must be in form             

# {"action":"tool", "tool":"here place the picked tool name", "arguments": {...} }

# otherwise return your answer in form

# {"action":"respond", "message": "..."}

# Response must be in valid JSON, so it can be directly used to load json from string
              
# ## Available tools
              
# """
              
# "```json\n"
# f"{toolsstr}"
# "\n```"
      
#     )
    prompt = (
 "You can either answer directly or call exactly one tool.\n"
        "Respond in JSON only.\n"
        "Schema:\n"
        '{"action":"respond","message":"..."}\n'
        "or\n"
        '{"action":"tool","tool":"NAME","arguments":{...}}\n\n'
        "Available tools:\n\n"
        f"{tools}"    )
    prompt = (
        """You are an API that must respond **only in valid JSON**, never plain text.

You have exactly two options for output schema (choose one):

1. Respond directly:
   {"action": "respond", "message": "<plain natural language answer>"}

2. Call exactly one tool:
   {"action": "tool", "tool": "<TOOL_NAME>", "arguments": { ... }}

Rules:
- Output must be valid JSON, no extra text or Markdown fences.
- Choose at most one tool.
- If unsure, prefer {"action":"respond",...}.
- Do not invent tools beyond those listed.

Examples:

Q: "Explain what GraphQL is."
A: {"action":"respond","message":"GraphQL is a query language for APIs that lets clients specify exactly the data they need."}

Q: "Give me all users from the endpoint"
A: {"action":"tool","tool":"getgraphQLdata","arguments":{"usermessage":"Give me all users"}}

Available tools:

"""
f"{tools}" 
    )
    return prompt

@mcp.resource(
    description="extract sdl of the graphql endpoint",
    uri="resource://graphql/sdl",
    mime_type="application/json", # Explicit MIME type
    tags={"metadata"}, # Categorization tags
)
async def get_graphql_sdl(ctx: fastmcp.Context):
    import graphql
    gqlClient = ctx.get_state("gqlClient")
    if gqlClient is None:
        gqlClient = await createGQLClient(
            username="john.newbie@world.com",
            password="john.newbie@world.com"
        )
        ctx.set_state(
            key="gqlClient",
            value=gqlClient
        ) 
    sdl_query = "query __ApolloGetServiceDefinition__ { _service { sdl } }"
    response = await gqlClient(query=sdl_query)
    response_data = response.get("data")
    assert response_data is not None, "Probably the graphql endpoint is not running"
    _service = response_data.get("_service")
    assert _service is not None, "Something went wrong, this could be error in code. _service key in graphql response is missing"
    sdl_str = _service.get("sdl")
    assert sdl_str is not None, "Something went wrong, this could be error in code. sdl key in graphql response is missing"
    sdl_ast = graphql.parse(sdl_str)
    ctx.set_state(
        key="sdl_ast",
        value=sdl_ast
    )
    print(f"get_graphql_sdl - set sdl_ast to {sdl_ast}")
    return sdl_ast

@mcp.resource(
    description="returns a list of types at graphql endpoint paired with their description",
    uri="resource://graphql/types",
    mime_type="application/json", # Explicit MIME type
    tags={"metadata"}, # Categorization tags
)
async def get_graphql_types(ctx: fastmcp.Context):
    import graphql
    sdl_ast = ctx.get_state("sdl_ast")
    if sdl_ast is None:       
        sdl_ast = await get_graphql_sdl.fn(ctx)
        print(f"get_graphql_types.sdl_ast = {sdl_ast}")
        
    result = {}
    for node in sdl_ast.definitions:
        if isinstance(node, graphql.language.ast.ObjectTypeDefinitionNode):
            name = node.name.value
            if "Error" in name:
                continue
            description = node.description.value if node.description else None
            result[name] = {"name": name, "description": description}

    result = list(result.values())
    return result

@mcp.resource(
    description=(
        "This resource generates a GraphQL query from an ordered list of types. "
        "The query's root selects the first type; "
        "subsequent levels progressively nest selections to reach each following type in sequence. "
        "If necessary, the generator inserts implicit intermediate types that link the specified types, "
        "even when those intermediates were not explicitly provided."
    ),
    uri="resource://graphql/query/{types*}",
)
async def build_graphql_query_nested(
    types: str,
    ctx: fastmcp.Context
):
    print(f"build_graphql_query_nested: {types}")
    typeslist = types.split("/")
    from src.Utils.GraphQLQueryBuilder import GraphQLQueryBuilder
    sdl_ast = await get_graphql_sdl.fn(ctx)
    querybuilder = GraphQLQueryBuilder(
        sdl_ast=sdl_ast,
        disabled_fields=[
            "createdby",
            "changedby"
        ]
    )
    query = querybuilder.build_query_vector(
        types=typeslist
    )
    from src.Utils.explain_query import explain_graphql_query
    query = explain_graphql_query(
        schema_ast=sdl_ast,
        query=query
    )
    return query
     


@mcp.prompt(
    description="acording user prompt the related graphql types are selected"
)
async def pickup_graphql_types(user_prompt: str, ctx: fastmcp.Context):
    typelist = await get_graphql_types.fn(ctx)
    prompt = f"""
# Instructions

You can pair objects mentioned by the user with GraphQL types described in the JSON below.
Analyze the user prompt and return only valid JSON: an array of strings, each exactly matching a type's `name`.
Respond with a single JSON array—no additional text, no code fences.

Rules:
1. Exclude any types whose names end with `"Error"`, unless explicitly requested.
2. Match on type name or on keywords found in the description.
3. Detect 1:N (one-to-many) or N:1 relationships between the matched types, and order the array so that each parent type appears immediately before its child types.


## Output Example

prompt:
    "Give me a list of study programs and their students"
output:
    ["ProgramGQLModel", "StudentGQLModel"]

## Types to select from

```json
    {json.dumps(typelist, indent=2)}
```
   
## User Prompt

```
{user_prompt}
```
"""
    return prompt


@mcp.tool(
    description=(
        "Asks graphql endpoint for data. "
        "If the query is known this is appropriate tool for extraction data from graphql endpoint. "
        "Data are returned as markdown table."
    )
)
async def ask_graphql_endpoint(
    # query: typing.Annotated[str, "graphql query"],
    # variables: typing.Annotated[dict, "variables for the graphql query"],
    query: str,
    variables: dict,
    ctx: fastmcp.Context
) -> ToolResult:
    gqlClient = ctx.get_state("gqlClient")
    if gqlClient is None:
        gqlClient = await createGQLClient(
            username="john.newbie@world.com",
            password="john.newbie@world.com"
        )
        ctx.set_state(
            key="gqlClient",
            value=gqlClient
        ) 

    response_data_set = await gqlClient(query=query, variables=variables)
    response_errors = response_data_set.get("errors") 
    # assert response_errors is None, f"During query {query} got response {response_data_set}"
    if response_errors is not None:
        return ToolResult(
            content=TextContent(
                type="text",
                text=f"During query {query} got response with errors {response_data_set}"
            ),
            structured_content={
                "sourceid": "9e3ab68d-a166-416c-941c-8eb1a87c728f",
                "errors": response_errors
            }
        )
    response_data = response_data_set.get("data")
    # assert response_data is not None, "Probably the graphql endpoint is not running"
    if response_data is None:
        return ToolResult(
            content=TextContent(
                type="text",
                text=f"Probably the graphql endpoint is not running"
            ),
            structured_content={
                "sourceid": "b40aa51b-4013-426b-989d-4748bc8b55a6",
                "errors": f"Probably the graphql endpoint is not running"
            }
        )
    print(f"response_data: {response_data}")
    data_list = next(iter(response_data.values()), None)
    print(f"data_list: {data_list}")
    # assert data_list is not None, f"Cannot found expected list of entities in graphql response {response_data_set}"
    if data_list is None:
        return ToolResult(
            content=TextContent(
                type="text",
                text=f"Cannot found expected list of entities in graphql response {response_data_set}"
            ),
            structured_content={
                "sourceid": "8fdeb496-9612-4067-a08d-f77126c81e50",
                "errors": f"Cannot found expected list of entities in graphql response {response_data_set}"
            }
        )
    md_table = await display_list_of_dict_as_table.fn(
        data=data_list,
        ctx=ctx
    )
    return ToolResult(
        content=TextContent(
            type="text",
            text=md_table
        ),
        structured_content={
            "sourceid": "0d5febef-6fc3-4648-a255-640332bf4df2",
            "response": md_table,
            "graphql": {
                "query": query,
                "variables": variables,
                "result": response_data
            }
        }
    )

    

@mcp.tool(
    description="Retreieves data from graphql endpoint. If the user want to get some data or entities this is appropriate tool to run.",
    tags={"system"}
)
async def get_graphQL_data(
    user_message: str, 
    ctx: fastmcp.Context
) -> ToolResult:
    import json
    import graphql

    # gqlClient = await createGQLClient(
    #     username="john.newbie@world.com",
    #     password="john.newbie@world.com"
    # )

    # # sdl analysis
    # sdl_query = "query __ApolloGetServiceDefinition__ { _service { sdl } }"
    # response = await gqlClient(query=sdl_query)
    # response_data = response.get("data")
    # assert response_data is not None, "Probably the graphql endpoint is not running"
    # _service = response_data.get("_service")
    # assert _service is not None, "Something went wrong, this could be error in code. _service key in graphql response is missing"
    # sdl_str = _service.get("sdl")
    # assert sdl_str is not None, "Something went wrong, this could be error in code. sdl key in graphql response is missing"
    # sdl_ast = graphql.parse(sdl_str)

    # sdl_ast = get_graphql_sdl.fn(ctx)
    # types and its description extraction

    availableGQLTypes = await get_graphql_types.fn(ctx)
    # sdl_ast = ctx.get_state("sdl_ast")
    gqlClient = ctx.get_state("gqlClient")
    assert gqlClient is not None, f"ctx.state does not contains gqlClient, that is code error"
    print(f"get_graphQL_data.availableGQLTypes: {availableGQLTypes[:2]} ...")
    
    prompt = await pickup_graphql_types.fn(
        user_prompt=user_message,
        ctx=ctx
    )

    # dotaz (callback / mcp.sample) na LLM pro vyber dotcenych typu
    llmresponse = await ctx.sample(
        messages=prompt
    )
    print(f"get_graphQL_data.llmresponse: {llmresponse}")
    type_list = json.loads(llmresponse.text)
    query = await build_graphql_query_nested.fn(
        types="/".join(type_list),
        ctx=ctx
    )
    
    await ctx.report_progress(
        progress=50,
        total=100,
        message=(
            "### Dotaz na GQL endpoint\n\n"
            "```gql\n"
            f"{query}"
            "\n```"
        )
    )
    response_data_set = await gqlClient(query=query)
    response_error = response_data_set.get("errors") 
    assert response_error is None, f"During query {query} got response {response_data_set}"
    response_data = response_data_set.get("data")
    assert response_data is not None, "Probably the graphql endpoint is not running"
    print(f"response_data: {response_data}")
    data_list = next(iter(response_data.values()), None)
    print(f"data_list: {data_list}")
    assert data_list is not None, f"Cannot found expected list of entities in graphql response {response_data_set}"
    md_table = await display_list_of_dict_as_table.fn(
        data=data_list,
        ctx=ctx
    )
    return ToolResult(
        content=TextContent(
            type="text",
            text=md_table
        ),
        structured_content={
            "sourceid": "9d5e6b6b-4e87-4cc6-872d-9a7083574dfe",
            "graphql": {
                "query": query,
                "variables": {},
                "result": response_data
            }
        }
    )
    


@mcp.tool(
    description="transforms the list of dict into table represented as a markdown fragment"
)
async def display_list_of_dict_as_table(data: typing.List[typing.Dict], ctx: fastmcp.Context) -> str:
    if not data:
        return "*(no data)*"

    # Sloupce vezmeme z klíčů prvního dictu
    headers = [key for key, value in data[0].items() if not isinstance(value, (dict, list))]

    # Hlavička
    header_line = "| " + " | ".join(headers) + " |"
    separator_line = "| " + " | ".join("---" for _ in headers) + " |"

    # Řádky
    rows = []
    for item in data:
        row = "| " + " | ".join(str(item.get(col, "")) for col in headers) + " |"
        rows.append(row)

    # Spojení všeho
    return "\n".join([header_line, separator_line] + rows)


async def createGQLClient(*, url: str = "http://localhost:33001/api/gql", username: str, password: str, token: str = None):
    import aiohttp
    async def getToken():
        authurl = url.replace("/api/gql", "/oauth/login3")
        async with aiohttp.ClientSession() as session:
            # print(headers, cookies)
            async with session.get(authurl) as resp:
                json = await resp.json()

            payload = {
                **json,
                "username": username,
                "password": password
            }
            async with session.post(authurl, json=payload) as resp:
                json = await resp.json()
            # print(f"createGQLClient: {json}")
            token = json["token"]
        return token
    token = await getToken() if token is None else token
    total_attempts = 10
    async def client(query, variables={}, cookies={"authorization": token}):
        # gqlurl = "http://host.docker.internal:33001/api/gql"
        # gqlurl = "http://localhost:33001/api/gql"
        nonlocal total_attempts
        if total_attempts < 1:
            raise Exception(msg="Max attempts to reauthenticate to graphql endpoint has been reached")
        attempts = 2
        while attempts > 0:
            
            payload = {"query": query, "variables": variables}
            # print("Query payload", payload, flush=True)
            try:
                async with aiohttp.ClientSession() as session:
                    # print(headers, cookies)
                    async with session.post(url, json=payload, cookies=cookies) as resp:
                        # print(resp.status)
                        if resp.status != 200:
                            text = await resp.text()
                            # print(text, flush=True)
                            raise Exception(f"Unexpected GQL response", text)
                        else:
                            text = await resp.text()
                            # print(text, flush=True)
                            response = await resp.json()
                            # print(response, flush=True)
                            return response
            except aiohttp.ContentTypeError as e:
                attempts = attempts - 1
                total_attempts = total_attempts - 1
                print(f"attempts {attempts}-{total_attempts}", flush=True)
                nonlocal token
                token = await getToken()

    return client

# Připoj MCP router k umbrella app
# app.include_router(mcp, prefix="/mcp")
mcp_app = mcp.http_app(path="/")

# v následujícím dotazu identifikuj datové entity, a podmínky, které mají splňovat. seznam datových entit (jejich odhadnuté názvy) uveď jako json list obsahující stringy - názvy seznam podmínek uveď jako json list obsahující dict např. {"name": {"_eq": "Pavel"}} pokud se jedná o podmínku v relaci, odpovídající dict je tento {"related_entity": {"attribute_name": {"_eq": "value"}}} v dict nikdy není použit klíč, který by sdružoval více názvů atributů dotaz: najdi mi všechny uživatele, kteří jsou členy katedry K209
