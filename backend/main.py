"""FastAPI Backend Entrypoint for Smart Classroom AV Assistant.

Run from project root:
    python -m uvicorn main:app --reload
or from within backend directory:
    python -m uvicorn main:app --reload
"""

import sys
from pathlib import Path

# Add project root to sys.path so backend modules resolve cleanly
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# Expose app from api module
from backend.api import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, reload=True)

