
from .server_populated import mcp
from .openapi import app, set_innerlifespan

# from .prompts import get_build_filter
# from .resources import get_available_operations

mcp_app = mcp.http_app(path="/")
set_innerlifespan(mcp_app.lifespan)

app.mount(path="/mcp", app=mcp_app)
