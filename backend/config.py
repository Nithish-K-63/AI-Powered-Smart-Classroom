"""Configuration settings for Smart Classroom AV Assistant."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file from project root
ROOT_DIR = Path(__file__).resolve().parent.parent
env_file = ROOT_DIR / ".env"
try:
    from dotenv import load_dotenv
    load_dotenv(env_file)
except ImportError:
    if env_file.exists():
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


class Settings:
    """Application settings resolved from environment variables with sensible defaults."""

    PROJECT_NAME: str = "Smart Classroom AV Troubleshooting Assistant"
    VERSION: str = "1.0.0"

    # API Server
    API_HOST: str = os.getenv("API_HOST", "127.0.0.1")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    BACKEND_URL: str = os.getenv("BACKEND_URL", f"http://{API_HOST}:{API_PORT}")

    # Dataset
    DATASET_PATH: str = os.getenv(
        "AV_DATASET_PATH",
        str(ROOT_DIR / "data" / "ai_classroom_av_troubleshooting_5000.csv"),
    )

    # MongoDB
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
    MONGODB_DB_NAME: str = os.getenv("MONGODB_DB_NAME", "smart_classroom_av")
    MONGODB_TIMEOUT_MS: int = int(os.getenv("MONGODB_TIMEOUT_MS", "500"))

    # Local Persistence Fallback
    LOCAL_STORE_PATH: Path = ROOT_DIR / "data" / "live_complaints.json"

    # Knowledge Retrieval & RAG
    RETRIEVER_BACKEND: str = os.getenv("RETRIEVER_BACKEND", "auto").lower()
    RAG_EMBEDDING_MODEL: str = os.getenv("RAG_EMBEDDING_MODEL", "all-MiniLM-L6-v2")
    MAX_RAG_RESULTS: int = int(os.getenv("MAX_RAG_RESULTS", "4"))

    # AI / LLM APIs
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")


settings = Settings()
