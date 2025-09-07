# app.py
from contextlib import asynccontextmanager
import json, re, inspect
from typing import Any, Dict, Optional, Callable, Awaitable

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel

import fastmcp
# ⬇︎ Uprav podle umístění tvé MCP instance
from .server_populated import mcp  # e.g.: from myproj.server import mcp



innerlifespan = None
def set_innerlifespan(
    new_innerlifespan
):
    innerlifespan = new_innerlifespan
    
@asynccontextmanager
async def dummy(app: FastAPI):
    yield 

@asynccontextmanager
async def lifespan(app: FastAPI):
    from src.DBFeeder import backupDB
    icm = dummy if innerlifespan is None else innerlifespan
    async with icm(app):
        try:
            yield
        finally:
            pass
    
    # print("App shutdown, nothing to do")

app = FastAPI(lifespan=lifespan)



# app = FastAPI(
#     title="MCP over HTTP (per-item endpoints)",
#     version="0.1.0",
#     description="Expose each MCP resource, prompt and tool as its own GET endpoint."
# )

@app.get("/health", tags=["meta"])
def health():
    return {"ok": True}


def slugify(s: str) -> str:
    s = s.replace("://", "-")
    s = re.sub(r"[^a-zA-Z0-9_-]+", "-", s)
    return re.sub(r"-{2,}", "-", s).strip("-").lower()


class HttpContext:
    """Lehký kontext, kompatibilní s fastmcp 'ctx' parametrem."""
    def __init__(self, headers: Dict[str, str] | None = None):
        self.headers = headers or {}
        self.session: Dict[str, Any] = {}
        self._state: Dict[str, Any] = {}

    def get_state(self, key: str, default: Any = None) -> Any:
        return self._state.get(key, default)

    def set_state(self, key: str, value: Any) -> None:
        self._state[key] = value


def _enabled(obj) -> bool:
    return getattr(obj, "enabled", True)


def _pick_kwargs(fn: Callable, provided: Dict[str, Any], ctx: HttpContext) -> Dict[str, Any]:
    """Namapuje pouze parametry, které funkce přijímá; doplní ctx, pokud je očekáván."""
    sig = inspect.signature(fn)
    out = {}
    names = set(sig.parameters.keys())
    names.discard("ctx")
    if len(names):
        names = list(names)
        values = list(provided.values())
        out[names[0]] = values[0]
        print(f"out {out}")
        for name, param in sig.parameters.items():
            if name == "ctx":
                out[name] = ctx

        return out
    
    for name, param in sig.parameters.items():
        if name == "ctx":
            out[name] = ctx
        elif name in provided:
            out[name] = provided[name]
        elif param.default is inspect._empty and param.kind in (
            param.POSITIONAL_ONLY, param.POSITIONAL_OR_KEYWORD
        ):
            raise HTTPException(status_code=400, detail=f"Missing required parameter: {name}")
    return out


async def _maybe_await(x):
    if inspect.isawaitable(x):
        return await x
    return x


# Volitelně: index dostupných per-item endpointů
class ExposedItem(BaseModel):
    kind: str
    name_or_uri: str
    path: str
    enabled: bool

_INDEX: list[ExposedItem] = []

@app.get("/", 
    # response_model=list[ExposedItem], 
    tags=["meta"]
)
async def index():
    resources = await mcp.get_resources()
    resources_t = await mcp.get_resource_templates()
    resources = {
        **resources,
        **resources_t
    }
    prompts = await mcp.get_prompts()
    tools = await mcp.get_tools()
    print(f"prompts: {prompts}")
    # return _INDEX
    return {
        "resources": [
            {
                "name": resource.name,
                "title": resource.title,
                "description": resource.description,
                # "required": prompt.required
                "parameters": getattr(resource, "parameters", {}).items()
            }
            for name, resource in resources.items()
        ],
        "prompts": [
            {
                "name": prompt.name,
                "title": prompt.title,
                "description": prompt.description,
                # "required": prompt.required
                "arguments": [
                    # {
                    #     "name": argument.name,
                    #     "description"
                    # }
                    argument.model_dump()
                    for argument in prompt.arguments
                ]
            }
            for name, prompt in prompts.items()
        ],
        "tools": [
            {
                "name": tool.name,
                "title": tool.title,
                "description": tool.description,
                # "required": prompt.required
                "arguments": [
                    # {
                    #     "name": argument.name,
                    #     "description"
                    # }
                    argument.model_dump()
                    for argument in tool.arguments
                ]
            }
            for name, tool in tools.items()
        ]
    }


def _build_handler_for_callable(kind: str, name: str, call_fn: Callable[..., Any]) -> Callable[..., Awaitable[Any]]:
    """
    Vrátí async endpoint handler (GET), který:
      - přečte args= jako JSON z query stringu
      - vytvoří HttpContext
      - namapuje kwargs dle signatury a zavolá MCP funkci
    """
    async def handler(args: Optional[str] = Query(
        default=None,
        description="Arguments as JSON object (e.g. {\"id\":123})")
    ):
        print(f"args: {args} {type(args)}")
        if not _enabled(call_fn.__self__ if hasattr(call_fn, "__self__") else call_fn):
            raise HTTPException(status_code=403, detail=f"{kind} disabled: {name}")
        
        if args:
            if not isinstance(args, dict):
                args = {"args": args}
        else:
            args = {}

        print(f"args: {args} {type(args)}")

        try:
            provided = args
            if not isinstance(provided, dict):
                raise ValueError("args must be a JSON object")
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid 'args' JSON: {e}")

        # ctx = HttpContext()
        ctx = fastmcp.Context(fastmcp=mcp)
        # fastmcp dekorátory typicky ukládají původní funkci do .fn
        target_fn = getattr(call_fn, "fn", call_fn)
        kwargs = _pick_kwargs(target_fn, provided, ctx)
        print(f"kwargs={kwargs}")
        result = await _maybe_await(target_fn(**kwargs))
        print(f"_build_handler_for_callable {result}")
        print(f"_build_handler_for_callable {type(result)}")
        if isinstance(result, (str, dict, list)):
            return result
        if hasattr(result, "to_dict"):
            # return result.to_dict()
            return json.dumps(result.to_dict())
        if hasattr(result, "dump_model"):
            return result.dump_model()
        return f"{result}"
        

    return handler


def _add_endpoint(path: str, handler: Callable, *, summary: str, description: str, operation_id: str, tags: list[str]):
    app.add_api_route(
        path,
        handler,
        methods=["GET"],
        summary=summary,
        description=description,
        operation_id=operation_id,
        tags=tags,
    )


def _register_per_item_endpoints():
    print(f"_register_per_item_endpoints {mcp}")
    # mcp.get_resources()
    # mcp._tool_manager._tools
    # mcp._resource_manager._resources
    # Resources
    print(f"_register_per_item_endpoints {mcp._resource_manager._resources}")
    for r in mcp._resource_manager._resources.values():
        print(r)
        uri = getattr(r, "uri", getattr(r, "name", "unknown"))
        uri = f"{uri}"
        desc = getattr(r, "description", "") or ""
        nm = slugify(uri)
        path = f"/resources/{nm}"
        handler = _build_handler_for_callable("resource", uri, r)
        _add_endpoint(
            path=path,
            handler=handler,
            summary=f"Resource: {uri}",
            description=desc or "Resource endpoint",
            operation_id=f"resource_{nm}",
            tags=["resources"],
        )
        _INDEX.append(ExposedItem(kind="resource", name_or_uri=uri, path=path, enabled=_enabled(r)))

    for r in mcp._resource_manager._templates.values():
        print(r)
        uri = getattr(r, "uri", getattr(r, "name", "unknown"))
        uri = f"{uri}"
        desc = getattr(r, "description", "") or ""
        nm = slugify(uri)
        path = f"/resources/{nm}"
        handler = _build_handler_for_callable("resource", uri, r)
        _add_endpoint(
            path=path,
            handler=handler,
            summary=f"Resource: {uri}",
            description=desc or "Resource endpoint",
            operation_id=f"resource_{nm}",
            tags=["resources"],
        )
        _INDEX.append(ExposedItem(kind="resource", name_or_uri=uri, path=path, enabled=_enabled(r)))

    print(_INDEX)
    # Prompts
    for p in getattr(mcp, "prompts", []):
        name = getattr(p, "name", "unknown")
        desc = getattr(p, "description", "") or ""
        nm = slugify(name)
        path = f"/prompts/{nm}"
        handler = _build_handler_for_callable("prompt", name, p)
        _add_endpoint(
            path=path,
            handler=handler,
            summary=f"Prompt: {name}",
            description=desc or "Prompt endpoint",
            operation_id=f"prompt_{nm}",
            tags=["prompts"],
        )
        _INDEX.append(ExposedItem(kind="prompt", name_or_uri=name, path=path, enabled=_enabled(p)))

    # Tools
    for t in getattr(mcp, "tools", []):
        name = getattr(t, "name", "unknown")
        desc = getattr(t, "description", "") or ""
        nm = slugify(name)
        path = f"/tools/{nm}"
        handler = _build_handler_for_callable("tool", name, t)
        _add_endpoint(
            path=path,
            handler=handler,
            summary=f"Tool: {name}",
            description=desc or "Tool endpoint",
            operation_id=f"tool_{nm}",
            tags=["tools"],
        )
        _INDEX.append(ExposedItem(kind="tool", name_or_uri=name, path=path, enabled=_enabled(t)))


# zaregistruj per-item cesty při startu
_register_per_item_endpoints()
