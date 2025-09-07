import os, json, hashlib, asyncio, time
from typing import Optional

import uvicorn
from fastapi import FastAPI, Request, Response, HTTPException
from fastapi.responses import JSONResponse, StreamingResponse, PlainTextResponse
import httpx

# ==== Konfigurace z env ====
UPSTREAM_ACCOUNT = os.getenv("AZURE_COGNITIVE_ACCOUNT_NAME", "")
UPSTREAM_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
UPSTREAM_API_VERSION = os.getenv("AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
UPSTREAM_ENDPOINT = f"https://{UPSTREAM_ACCOUNT}.openai.azure.com"

PROXY_BIND = os.getenv("PROXY_BIND", "0.0.0.0")
PROXY_PORT = int(os.getenv("PROXY_PORT", "8787"))

PROXY_TOKEN = os.getenv("PROXY_TOKEN", "")  # volitelné – pokud je nastaveno, vyžaduje X-Proxy-Token
LOG_PROMPTS = os.getenv("PROXY_LOG_PROMPTS", "false").lower() == "true"
FORCE_JSON_RESPONSE = os.getenv("FORCE_JSON_RESPONSE", "false").lower() == "true"
TIMEOUT_SECS = float(os.getenv("UPSTREAM_TIMEOUT", "60"))


# --- NOVÉ ENV pro OpenAI-compatible režim ---
OPENAI_COMPAT_ENABLED = os.getenv("OPENAI_COMPAT_ENABLED", "true").lower() == "true"
# JSON mapa: "openai_model" -> "azure_deployment"
# např: {"gpt-4o":"gpt4o-prod","gpt-4o-mini":"gpt4o-mini"}
OPENAI_COMPAT_MODEL_MAP = os.getenv("OPENAI_COMPAT_MODEL_MAP", "{}")

try:
    MODEL_MAP: dict[str, str] = json.loads(OPENAI_COMPAT_MODEL_MAP) if OPENAI_COMPAT_MODEL_MAP else {}
except Exception:
    MODEL_MAP = {
        "gpt-5-nano": "gpt-5-nano",
        "gpt-4.1": "orchestration-deployment",
        "gpt-4o-mini": "summarization-deployment",
    }

DEFAULT_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEFAULT_DEPLOYMENT", "summarization-deployment")  # fallback, když model není v mapě


# --- POMOCNÉ FUNKCE PRO OPENAI KOMPAT ---
def resolve_deployment_from_model(model_name: str) -> str:
    """
    Přeloží OpenAI model (např. 'gpt-4o') na Azure deployment (např. 'gpt4o-prod').
    Fallback: DEFAULT_DEPLOYMENT.
    """
    dep = MODEL_MAP.get(model_name)
    if not dep:
        dep = DEFAULT_DEPLOYMENT
    if not dep:
        # nechceme spadnout; ať je chyba čitelná
        raise HTTPException(
            status_code=400, 
            detail=(
                f"No deployment mapped for model '{model_name}'. "
                "\n"
                f"model map: {json.dumps(MODEL_MAP, indent=1)}"
                "\n"
                f"Provide OPENAI_COMPAT_MODEL_MAP or AZURE_OPENAI_DEFAULT_DEPLOYMENT."
            )
        )
    return dep

def azure_chat_url(deployment: str) -> str:
    return f"{UPSTREAM_ENDPOINT}/openai/deployments/{deployment}/chat/completions?api-version={UPSTREAM_API_VERSION}"

def azure_responses_url(deployment: str) -> str:
    return f"{UPSTREAM_ENDPOINT}/openai/deployments/{deployment}/responses?api-version={UPSTREAM_API_VERSION}"



# ==== HTTP klient ====
client = httpx.AsyncClient(timeout=httpx.Timeout(TIMEOUT_SECS, connect=10.0))

app = FastAPI(title="Azure OpenAI Reverse Proxy")

def require_auth(request: Request):
    if PROXY_TOKEN:
        token = request.headers.get("X-Proxy-Token")
        if token != PROXY_TOKEN:
            raise HTTPException(status_code=401, detail="Unauthorized")

def redact(s: str, keep: int = 4) -> str:
    if not s: return ""
    return s[:keep] + "…" if len(s) > keep else "****"

def gen_idempotency_key(body: dict) -> str:
    # deterministicky z modelu + messages + function/tool calls …
    canonical = json.dumps(
        {k: body.get(k) for k in ("model", "messages", "tools", "tool_choice", "response_format", "temperature")},
        sort_keys=True, ensure_ascii=False, separators=(",", ":")
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:32]

async def backoff_delays(max_retries: int = 3):
    # 0.5s, 1s, 2s (+ jitter)
    base = 0.5
    for i in range(max_retries):
        delay = base * (2 ** i)
        yield delay + (0.05 * (i + 1))

def build_upstream_url(deployment: str) -> str:
    return f"{UPSTREAM_ENDPOINT}/openai/deployments/{deployment}/chat/completions?api-version={UPSTREAM_API_VERSION}"

def maybe_force_json_response(body: dict) -> dict:
    if FORCE_JSON_RESPONSE:
        rf = body.get("response_format")
        if not isinstance(rf, dict) or rf.get("type") not in ("json_object", "json_schema"):
            body["response_format"] = {"type": "json_object"}
    return body

def log_req(deployment: str, body: dict):
    meta = {k: body.get(k) for k in ("model","temperature","stream")}
    if LOG_PROMPTS:
        # POZOR: může obsahovat PII
        print(f"[REQ] dep={deployment} meta={meta} messages={json.dumps(body.get('messages', [])[:2], ensure_ascii=False)[:500]}…")
    else:
        # bezpečné minimum
        print(f"[REQ] dep={deployment} meta={meta} messages_count={len(body.get('messages', []))}")

def log_res(status: int, usage: Optional[dict]):
    print(f"[RES] status={status} usage={usage or {}}")

def extract_usage(json_obj: dict) -> Optional[dict]:
    return json_obj.get("usage")

def upstream_headers(request: Request, idemp: str | None) -> dict:
    # klient nemusí posílat Azure API key; proxy vloží vlastní
    h = {
        "api-key": UPSTREAM_API_KEY,
        "Content-Type": "application/json",
    }
    # Idempotency-Key (Azure jej akceptuje; OpenAI standard taky)
    if idemp:
        h["Idempotency-Key"] = idemp
    # Forward-X pro audit
    if request.headers.get("X-Request-Id"):
        h["X-Request-Id"] = request.headers["X-Request-Id"]
    return h

async def forward_nonstream(url: str, headers: dict, body: dict) -> Response:
    r = await client.post(url, headers=headers, json=body)
    # retry vyšší vrstvě neřešíme tady – řeší route
    try:
        data = r.json()
    except Exception:
        data = None
    log_res(r.status_code, extract_usage(data or {}))
    # předej JSON/HTTP status dál
    if data is not None:
        return JSONResponse(status_code=r.status_code, content=data)
    return PlainTextResponse(status_code=r.status_code, content=r.text)

async def stream_generator(url: str, headers: dict, body: dict):
    async with client.stream("POST", url, headers=headers, json=body) as r:
        async for chunk in r.aiter_bytes():
            yield chunk

async def forward_stream(url: str, headers: dict, body: dict) -> Response:
    # zachovej event-stream
    return StreamingResponse(stream_generator(url, headers, body), media_type="text/event-stream")

def should_retry(status: int) -> bool:
    return status in (429, 500, 502, 503, 504)

# ============= ROUTES =============

@app.post("/openai/deployments/{deployment}/chat/completions")
async def chat_completions(deployment: str, request: Request):
    require_auth(request)
    print(f"chat_completions/{deployment}")
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    body = maybe_force_json_response(body)
    idemp = request.headers.get("Idempotency-Key") or gen_idempotency_key(body)

    log_req(deployment, body)
    url = build_upstream_url(deployment)
    headers = upstream_headers(request, idemp)

    # retry smyčka pro non-stream; pro stream uděláme jediný pokus (SSE a retry se hůř skládá)
    if body.get("stream"):
        return await forward_stream(url, headers, body)

    last_exc = None
    # první pokus + max 3 retry
    for delay in [0.0, *[d async for d in backoff_delays(3)]]:
        if delay:
            await asyncio.sleep(delay)
        try:
            resp = await client.post(url, headers=headers, json=body)
            if not should_retry(resp.status_code):
                try:
                    data = resp.json()
                except Exception:
                    data = None
                log_res(resp.status_code, extract_usage(data or {}))
                if data is not None:
                    return JSONResponse(status_code=resp.status_code, content=data)
                return PlainTextResponse(status_code=resp.status_code, content=resp.text)
            else:
                last_exc = f"Upstream status {resp.status_code}, retrying…"
        except httpx.HTTPError as e:
            last_exc = f"HTTP error: {e}"

    # po vyčerpání
    raise HTTPException(status_code=502, detail=f"Upstream failed after retries: {last_exc}")

@app.get("/healthcheck")
async def healthcheck():
    return {"ok": True}

@app.post("/llmtest/{deployment}")
async def llmtest(
    deployment: str,
    query: str
):
    
    from openai import AzureOpenAI, AsyncAzureOpenAI
    from openai.types.chat import ChatCompletion
    from openai.resources.chat.completions import AsyncCompletions
    UPSTREAM_ENDPOINT = "http://localhost:8003/"
    client = AsyncAzureOpenAI(
        azure_endpoint=UPSTREAM_ENDPOINT,
        azure_deployment=deployment,  # tvůj deployment name
        api_key=UPSTREAM_API_KEY,
        api_version=UPSTREAM_API_VERSION
    )

    azureCompletions: AsyncCompletions = client.chat.completions
    resp = await azureCompletions.create(
            model=deployment,          # = deployment name
            messages=[
                {"role": "system", "content": "You are assistent."},
                {"role": "user", "content": query}
            ],
            temperature=0.8,
            max_tokens=1000,
        )
    asjson = resp.model_dump()
    return asjson
    

# ---------- OpenAI-compatible: /v1/models ----------
@app.get("/v1/models")
@app.get("/models")  # volitelně alias
async def list_models_openai():
    """
    Vrátí seznam 'modelů' podle klíčů v OPENAI_COMPAT_MODEL_MAP.
    OpenAI vrací object=list a položky s object=model.
    """
    items = []
    for mid in (MODEL_MAP.keys() or []):
        items.append({"id": mid, "object": "model", "created": 0, "owned_by": "azure-proxy"})
    # fallback: když není mapa, ale je DEFAULT_DEPLOYMENT, ukaž aspoň 1 id
    if not items and DEFAULT_DEPLOYMENT:
        items = [{"id": "gpt-azure", "object": "model", "created": 0, "owned_by": "azure-proxy"}]
    result = {"object": "list", "data": items}
    print(f"list_models_openai: {json.dumps(result, indent=2)}")
    return result

# ---------- OpenAI-compatible: /v1/chat/completions ----------
@app.post("/v1/chat/completions")
@app.post("/chat/completions")
async def openai_v1_chat_completions(request: Request):
    """
    Přijme OpenAI styl (model=..., messages=[...]) a přesměruje na Azure chat/completions.
    """
    if not OPENAI_COMPAT_ENABLED:
        raise HTTPException(status_code=404, detail="OpenAI-compatible mode disabled")

    require_auth(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    model = body.get("model")
    if not isinstance(model, str) or not model.strip():
        raise HTTPException(status_code=400, detail="Missing 'model' in body")

    deployment = resolve_deployment_from_model(model)
    body = maybe_force_json_response(body)  # volitelný forcing JSON output
    idemp = request.headers.get("Idempotency-Key") or gen_idempotency_key(body)

    # Log a hlavičky (vezmeme Azure api-key, ne Authorization)
    log_req(f"OPENAI chat -> {deployment}", body)
    headers = {
        "api-key": UPSTREAM_API_KEY,
        "Content-Type": "application/json",
        "Idempotency-Key": idemp,
    }
    url = azure_chat_url(deployment)

    # stream?
    if body.get("stream"):
        return await forward_stream(url, headers, body)

    # non-stream s retry (použijeme tvůj existující vzor)
    last_exc = None
    for delay in [0.0, *[d async for d in backoff_delays(3)]]:
        if delay:
            await asyncio.sleep(delay)
        try:
            r = await client.post(url, headers=headers, json=body)
            if not should_retry(r.status_code):
                try:
                    data = r.json()
                except Exception:
                    data = None
                log_res(f"OPENAI chat {r.status_code}", extract_usage(data or {}))
                if data is not None:
                    return JSONResponse(status_code=r.status_code, content=data)
                return PlainTextResponse(status_code=r.status_code, content=r.text)
            else:
                last_exc = f"Upstream status {r.status_code}, retrying…"
        except httpx.HTTPError as e:
            last_exc = f"HTTP error: {e}"
    raise HTTPException(status_code=502, detail=f"Upstream failed after retries: {last_exc}")

# ---------- OpenAI-compatible: /v1/responses ----------
@app.post("/v1/responses")
@app.post("/responses")
async def openai_v1_responses(request: Request):
    """
    OpenAI Responses API (model=..., input=[...]).
    Přesměruje na Azure /responses (2024-12-01-preview a novější).
    """
    if not OPENAI_COMPAT_ENABLED:
        raise HTTPException(status_code=404, detail="OpenAI-compatible mode disabled")

    require_auth(request)
    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON body")

    model = body.get("model")
    if not isinstance(model, str) or not model.strip():
        raise HTTPException(status_code=400, detail="Missing 'model' in body")

    deployment = resolve_deployment_from_model(model)
    idemp = request.headers.get("Idempotency-Key") or gen_idempotency_key(body)

    log_req(f"OPENAI responses -> {deployment}", body)
    headers = {
        "api-key": UPSTREAM_API_KEY,
        "Content-Type": "application/json",
        "Idempotency-Key": idemp,
    }
    url = azure_responses_url(deployment)

    if body.get("stream"):
        return await forward_stream(url, headers, body)

    last_exc = None
    for delay in [0.0, *[d async for d in backoff_delays(3)]]:
        if delay:
            await asyncio.sleep(delay)
        try:
            r = await client.post(url, headers=headers, json=body)
            if not should_retry(r.status_code):
                try:
                    data = r.json()
                except Exception:
                    data = None
                log_res(f"OPENAI responses {r.status_code}", extract_usage(data or {}))
                if data is not None:
                    return JSONResponse(status_code=r.status_code, content=data)
                return PlainTextResponse(status_code=r.status_code, content=r.text)
            else:
                last_exc = f"Upstream status {r.status_code}, retrying…"
        except httpx.HTTPError as e:
            last_exc = f"HTTP error: {e}"
    raise HTTPException(status_code=502, detail=f"Upstream failed after retries: {last_exc}")

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    print(f"http.middleware base_url={request.base_url}")
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = time.perf_counter() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response

# volitelně předej i jiné cesty, pokud bys chtěl (např. /images, /responses, atd.)
# … můžeš doplnit další route stejně jako výše

if __name__ == "__main__":
    # Pokud chceš TLS přímo v uvicorn:
    # uvicorn.run(app, host=PROXY_BIND, port=PROXY_PORT, ssl_keyfile="key.pem", ssl_certfile="cert.pem")
    uvicorn.run(app, host=PROXY_BIND, port=PROXY_PORT)
