import sys
import importlib
from pathlib import Path


_ROOT = Path(__file__).resolve().parent.parent
_SRC = _ROOT / "src"

if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

# Ensure modules imported with or without the `src.` prefix resolve to the same instance
graph_module = importlib.import_module("src.GraphTypeDefinitions")
sys.modules.setdefault("GraphTypeDefinitions", graph_module)

db_module = importlib.import_module("src.DBDefinitions")
sys.modules.setdefault("DBDefinitions", db_module)
