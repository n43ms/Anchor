import os

def _auto_load_dotenv() -> None:
    """Automatically loads .env from current directory or parents when anchor is imported."""
    try:
        curr = os.getcwd()
        while curr:
            dotenv_file = os.path.join(curr, ".env")
            if os.path.exists(dotenv_file):
                with open(dotenv_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            k, v = line.split("=", 1)
                            k, v = k.strip(), v.strip().strip("'\"")
                            if k and not os.environ.get(k):
                                os.environ[k] = v
                break
            parent = os.path.dirname(curr)
            if parent == curr:
                break
            curr = parent
    except Exception:
        pass

_auto_load_dotenv()

from anchor.core.determinism.actions import Done, ModelCall, ToolCall
from anchor.core.determinism.context import StepContext
from anchor.runner import run
from anchor.runtime.agents.decorators import agent
from anchor.runtime.tools.decorators import tool

__all__ = [
    "Done",
    "ModelCall",
    "StepContext",
    "ToolCall",
    "agent",
    "run",
    "tool",
]
