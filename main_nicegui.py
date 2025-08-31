import json
import typing

# region nicegui
import nicegui
from nicegui import ui, app as nicegui_app, storage, core
from starlette.middleware.sessions import SessionMiddleware
nicegui_app.add_middleware(storage.RequestTrackingMiddleware)
nicegui_app.add_middleware(SessionMiddleware, secret_key='SUPER-SECRET')
from graphql import parse

from src.GraphTypeDefinitions import schema
from main_ai import ChatSession
import fastmcp

MCPURL = "http://localhost:8002/mcp"

@ui.page("/")
async def index_page():
    chatSession = ChatSession()
    mcpClient = fastmcp.Client(MCPURL)
    
    async with mcpClient:
        # result["tool.response"] = await client.call_tool("echo", {"text": "hello"})
        mcp_tools = await mcpClient.list_tools()
        prompts = await mcpClient.list_prompts()
        print(f"mcp tools: {mcp_tools}")
        print(f"mcp prompts: {prompts}")
        
    #     resources = await client.list_resource_templates()
        
    #     # Filter resources by tag
    #     result["config_resources"] = [
    #         resource for resource in resources 
    #         # if hasattr(resource, '_meta') and resource._meta and
    #         #     resource._meta.get('_fastmcp', {}) and
    #         #     'config' in resource._meta.get('_fastmcp', {}).get('tags', [])
    #     ]        
    # return result
    # https://github.com/zauberzeug/nicegui/blob/main/examples/chat_with_ai/main.py

    # print("Index page", type(request), type(response), type(unknown))
    # ui.label("Hello, World!")
    # ui.button("Click me", on_click=lambda: ui.notify("Clicked!"))
    async def addAssistantMsg(msg):
        with message_container:
            response_message = ui.chat_message(name='Asistent', sent=False).classes("no-tail").props('bg-color=grey-8 text-color=black')    
            # response_message = ui.chat_message(name='Asistent', sent=False).classes("no-tail")
            with response_message:
                # ui.html(part["content"])
                with ui.element('div').classes('table-responsive'):
                    ui.markdown(msg)
        return response_message

    async def addUserMsg(msg):
        with message_container:
            response_message = ui.chat_message(name='You', sent=True).classes("no-tail")
            with response_message:
                # ui.html(part["content"])
                ui.markdown(msg)
        return response_message

    async def send() -> None:
        question = text.value
        text.value = ''
        with message_container:
            ui.chat_message(text=question, name='You', sent=True).classes("no-tail")

        # chatSession.ask
        
        if question.strip() == "sdl":
            response = [
                {"type": "text", "content": f"I have responded to {question}"},
                {"type": "md", "content": schema.as_str().replace("\\n", "\n").replace('\\"', '"') }
            ]
        elif question.strip() == "explain":
            from src.Utils.explain_query import explain_graphql_query
            from src.Utils.gql_client import createGQLClient
            client = await createGQLClient(username="john.newbie@world.com", password="john.newbie@world.com")
            sdl_query = """query __ApolloGetServiceDefinition__ { _service { sdl } }"""
            result = await client(sdl_query, variables={})
            print(result)
            sdl = result["data"]["_service"]["sdl"]
            schema_ast = parse(sdl)
            # sdl = schema.as_str()
            query = """
query userPage($skip: Int, $limit: Int, $orderby: String, $where: UserInputWhereFilter) {
  userPage(skip: $skip, limit: $limit, orderby: $orderby, where: $where) {
  __typename
id
lastchange
created

name
givenname
middlename
email
firstname
surname
valid
startdate
enddate
}
}
"""
            result = explain_graphql_query(schema_ast, query)
            response = [
                {"type": "text", "content": f"I have responded to {question}"},
                {"type": "md", "content": f"```gql\n{result}\n```"} 
            ]
        else:
            from mcp.types import SamplingMessage, CreateMessageRequestParams
            async def onSampling(
                messages: typing.List[SamplingMessage], 
                params: CreateMessageRequestParams, 
                context
            ) -> str:
                
                query = "\n".join([message.content.text for message in messages])
                await addAssistantMsg(f"Musím se zeptat sám sebe")
                await addAssistantMsg(f"{query}")
                llm_response = await chatSession.ask(query)
                # llm_response = '["UserGQLModel"]'
                await addAssistantMsg((
                    "Odpovídám si \n\n"
                    "```json\n"
                    f"{llm_response}"
                    "\n```"
                ))
                print(f"onSampling {messages}, {params}")
                return llm_response

            async def onProgress(
                progress: float, 
                total: float | None, 
                message: str | None
            ):
                await addAssistantMsg(f"{message}")
                await chatSession.append_history(
                    {"role": "assistant", "content": message}
                )
                pass

            response = []
            async with fastmcp.Client(
                MCPURL,
                sampling_handler=onSampling,
                progress_handler=onProgress
            ) as mcpClient:
                # await addUserMsg(question)
                await chatSession.append_history(
                    {"role": "user", "content": question}
                )

                tools = [tool.model_dump() for tool in mcp_tools]
                # print(f"niceguid.page.tools {tools}")
                tool_prompt = await mcpClient.get_prompt(
                    name="get_use_tools",
                    arguments={
                        "tools": tools
                    }
                )
                
                promptLines = [msg.content.text for msg in tool_prompt.messages]
                await addUserMsg('\n\n'.join(promptLines))
                
                chat_str_response = await chatSession.ask('\n\n'.join(promptLines))
                chat_str_response_json = {
                    "action": "respond",
                    "message": f"{chat_str_response}"
                }
                hasErrors = False
                try:
                # print(f"tool_prompt: {tool_prompt}")
                    chat_str_response_json = json.loads(chat_str_response)
                    await addAssistantMsg((
                        '```json\n'
                        f'{chat_str_response_json}'
                        '\n```'
                    ))
                    print(f"chat_str_response_json: {chat_str_response_json}")
                    action = chat_str_response_json.get("action")
                except Exception as e:
                    hasErrors = True
                    response.append(
                            {"type": "md", "content": (
                                f"Doslo k chybe {chat_str_response}"
                                "\n"
                                f"Exception {e}"
                            )}
                        )
                    
                action = chat_str_response_json.get("action")
                print(f"action: {action}")
                if action != "tool":
                    response.append(
                        {"type": "md", "content": f'{chat_str_response_json["message"]}'}    
                    )
                tries = 0
                maxTries = 3
                while tries < maxTries and not hasErrors and action == "tool":
                    try:
                        tool_to_call = chat_str_response_json["tool"]
                        arguments = chat_str_response_json.get("arguments")
                        await addAssistantMsg((
                            f"vybral jsem  vhodný nástroj `{tool_to_call}`"
                            "\ns parametry\n"
                            "```json\n"
                            f"{arguments}"
                            "\n```"
                        ))
                        # await addAssistantMsg(f"Volím nástroj {tool_to_call}.")
                        tool_response = await mcpClient.call_tool(
                            name=tool_to_call,
                            arguments=arguments,
                        )
                        tool_response_text = "\n".join([block.text for block in tool_response.content])
                        # vrat mi seznam skupin
                        response.append(
                            {"type": "md", "content": tool_response_text}    
                        )
                        tries = maxTries
                    except Exception as e:
                        hasErrors = True
                        toolDefinition = next(filter(lambda tool: tool["name"] == tool_to_call, tools, None))
                        chatSession.append_history({
                            "role": "user", 
                            "content": (
                                "volani nástroje mi hlásí chybu, zkus to opravit\n\n"
                                "definice nástroje, který jsi doporučil volat je\n\n"
                                f"{json.dumps(toolDefinition)}"
                                "\n\nchyba, kterou to hlásí je\n\n"
                                f"{e}"
                            )
                        })
                        response.append(
                            {"type": "md", "content": (
                                f"Doslo k chybe {chat_str_response}"
                                "\n"
                                f"Exception {e}"
                            )}
                        )
                
                # response = [
                #     # {"type": "text", "content": f"I have responded to {question}"},
                #     {"type": "md", "content": f"{chat_str_response}"}
                # ]

        with message_container:
            response_message = ui.chat_message(name='Assistent', sent=False).classes("no-tail")
        for part in response:
            # await asyncio.sleep(1)
            if part["type"] == "text":
                with response_message:
                    # ui.html(part["content"])
                    ui.markdown(part["content"])
            elif part["type"] == "md":
                with response_message:
                    with ui.element('div').classes('table-responsive'):
                        ui.markdown(part["content"])
        ui.run_javascript('window.scrollTo(0, document.body.scrollHeight)')

        # text.value = ''



    ui.add_css(r'a:link, a:visited {color: inherit !important; text-decoration: none; font-weight: 500}')
    ui.add_head_html("""
    <style>
    /* bloky kódu z trojitých backticků */
    .q-message .markdown pre {
    background: #f6f8fa;       /* světlé pozadí pro čitelnost */
    color: inherit;
    padding: 12px;
    border-radius: 8px;
    overflow: auto;
    box-shadow: inset 0 0 0 1px rgba(0,0,0,.04);
    }
    /* inline `code` */
    .q-message .markdown code:not(pre code) {
    background: rgba(0,0,0,.06);
    padding: .15em .35em;
    border-radius: 4px;
    }
    /* ať se nenasčítají pozadí u pre > code */
    .q-message .markdown pre code {
    background: transparent;
    padding: 0;
    }
    </style>
    """)    

    ui.add_head_html("""
    <style>
    /* Bootstrap-like responsive wrapper */
    .table-responsive {
    display: block;
    width: 100%;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    }
    /* optional: aby se tabulka nerozpadala a nevylézala z bubliny */
    .table-responsive table {
    margin-bottom: 0;
    border-collapse: collapse;
    }
    .table-responsive th, 
    .table-responsive td {
    /* buď nech svinování textu... */
    white-space: nowrap;      /* ← zruš, pokud chceš zalamovat */
    /* ...a nebo povol zalamování:
    white-space: normal;
    word-break: break-word;
    */
    }
    </style>
    """)    
    # ui.add_css("""
    # .q-chat-message--sent .q-message-container:before,
    # .q-chat-message--received .q-message-container:before {
    #     display: none !important;
    # }
    # """)
    ui.add_css("""
    .hide-zobacek:before {
        display: none !important;
    }
    """)
    ui.add_css("""
.no-tail .q-message-text--sent:before,
.no-tail .q-message-text--sent:after,
.no-tail .q-message-text--received:before,
.no-tail .q-message-text--received:after {
    display: none !important;
    content: none !important;
}
""")
    # the queries below are used to expand the contend down to the footer (content can then use flex-grow to expand)
    ui.query('.q-page').classes('flex')
    ui.query('.nicegui-content').classes('w-full')

    with ui.tabs().classes('w-full') as tabs:
        chat_tab = ui.tab('Chat')
        logs_tab = ui.tab('Logs')
    with ui.tab_panels(tabs, value=chat_tab).classes('w-full max-w-5xl mx-auto flex-grow items-stretch'): #.classes('w-full max-w-2xl mx-auto flex-grow items-stretch'):
        message_container = ui.tab_panel(chat_tab).classes('items-stretch')
        with message_container:
            # ui.chat_message(text="I have arrived", name='You', sent=True).classes("no-tail")
            ui.chat_message(text="Hello! I'm your friendly bot. How can I assist you today?", name='Asistent', sent=False).classes("no-tail")
            # ui.markdown("""
            #             # My response
            #             ```json
            #             {
            #                 "question": "{question}"
            #             }
            #             ```
            #             """
            #             """I have responded to {question}""")
            
            # ui.chat_message(text="Hi! How can I help you?", name='Asistent', sent=False)
        with ui.tab_panel(logs_tab):
            log = ui.log().classes('w-full h-full') 

    with ui.footer().classes("bg-gray-600"), ui.column().classes('w-full max-w-3xl mx-auto my-6'):
        with ui.row().classes('w-full no-wrap items-center'):
            placeholder = ("message" 
                # if "OPENAI_API_KEY" != 'not-set' else \
                # 'Please provide your OPENAI key in the Python script first!'
            )
            text = ui.input(label="User query", placeholder=placeholder).props('rounded outlined input-class mx-3') \
                .classes('w-full self-center').on('keydown.enter', send)

# endregion