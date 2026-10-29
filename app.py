"""Entrypoint for Smart Classroom AV Assistant.

Runs the finalized Figma-designed application with custom CSS styling,
role-based navigation, live SQLite persistence, ChromaDB vector store,
and Qwen3-8B AI inference engine.
"""

from pathlib import Path
import sys

# Configure project path
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

# Launch the Figma-designed frontend
frontend_app = CURRENT_DIR / "frontend" / "app.py"
if frontend_app.exists():
    with open(frontend_app, "r", encoding="utf-8") as f:
        code = compile(f.read(), str(frontend_app), "exec")
        exec(code, {"__name__": "__main__", "__file__": str(frontend_app)})

