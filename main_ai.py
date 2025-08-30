import typing
from dotenv import load_dotenv
load_dotenv("environment.txt", override=False)
load_dotenv("environment.secret.txt", override=False)
load_dotenv("environment.super.secret.txt", override=False)

import os
OPENAI_API_KEY=os.getenv("OPENAI_API_KEY")
account = os.getenv("AZURE_COGNITIVE_ACCOUNT_NAME", "")
model_name = os.getenv("AZURE_CHAT_DEPLOYMENT_NAME", "") or "summarization-deployment"
endpoint = f"https://{account}.openai.azure.com"

# from langchain_openai import AzureChatOpenAI
# from langchain.chat_models import AzureChatOpenAI #.azure_openai import AzureChatOpenAI
# from langchain_community import chat_models
# 2) LLM (Azure OpenAI)
# llm = AzureChatOpenAI(
#     azure_endpoint=endpoint,
#     deployment=model_name,  # tvůj deployment name
#     api_key=OPENAI_API_KEY,
#     api_version="2024-12-01-preview"
# )
import asyncio
from openai import AzureOpenAI, AsyncAzureOpenAI
from openai.types.chat import ChatCompletion
from openai.resources.chat.completions import AsyncCompletions

client = AsyncAzureOpenAI(
    azure_endpoint=endpoint,
    azure_deployment=model_name,  # tvůj deployment name
    api_key=OPENAI_API_KEY,
    api_version="2024-12-01-preview"
)

azureCompletions: AsyncCompletions = client.chat.completions

class ChatSession:
    def __init__(self, system_prompt: str = "You are a helpful assistant.",
                 max_turns: int = 12):
        # 1 turn = 1 user + 1 assistant zpráva
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.messages: typing.List[typing.Dict[str, typing.Any]] = [
            {"role": "system", "content": self.system_prompt}
        ]
        self.azureCompletions: AsyncCompletions = client.chat.completions

    def _trim_history(self) -> None:
        # nechá první system zprávu + posledních N tahů
        # (tj. max 1 + 2*max_turns zpráv)
        # najdi index první user/assistant zprávy od konce:
        # jednoduché řešení – seřízni na posledních (2*max_turns) zpráv + system
        keep = 1 + 2 * self.max_turns
        if len(self.messages) > keep:
            self.messages = [self.messages[0]] + self.messages[-(keep - 1):]

    async def get_history(self) -> typing.List[typing.Dict[str, typing.Any]]:
        keep = 1 + 2 * self.max_turns
        result = [self.messages[0]] + self.messages[-(keep - 1):]
        return result

    async def append_history(self, message) -> typing.List[typing.Dict[str, typing.Any]]:
        self.messages.append(message)
        return self.messages

    async def ask(
        self, 
        user_text: str, 
        *, 
        temperature: float = 0.2,
        max_tokens: int = 800
    ) -> str:
        await self.append_history({"role": "user", "content": user_text})
        history = await self.get_history()

        resp = await self.azureCompletions.create(
            model=model_name,          # = deployment name
            messages=history,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        reply = resp.choices[0].message.content or ""
        usage = resp.usage.model_dump()
        await self.append_history({"role": "assistant", "content": reply, "usage": usage})
        return reply

async def main():
    session = ChatSession(system_prompt="You are a helpful assistant that answers in Czech.")
    # print(await session.ask("Napiš mi vtip o kočkách."))
    # print(await session.ask("A teď ho zopakuj."))

# asyncio.run(main())
asyncio.get_running_loop().create_task(main())
# print(dir(llm))