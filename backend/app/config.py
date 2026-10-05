import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

DEFAULT_MAILBOX_PATH = BASE_DIR / "emails_candidate.json"


def env_int(name: str, default: int) -> int:
    """Read an integer setting from the environment."""
    return int(os.getenv(name, str(default)))


class Settings:
    """Application configuration loaded from environment variables."""

    def __init__(self) -> None:
        """Load configuration values and their default values."""
        self.mailbox_path = os.getenv(
            "MAILBOX_PATH",
            str(DEFAULT_MAILBOX_PATH),
        )
        self.ollama_url = os.getenv(
            "OLLAMA_URL",
            "http://localhost:11434",
        )
        self.ollama_model = os.getenv(
            "OLLAMA_MODEL",
            "qwen2.5:3b",
        )
        self.ollama_timeout = env_int(
            "OLLAMA_TIMEOUT_SECONDS",
            120,
        )
        self.handler_mailbox = os.getenv(
            "HANDLER_MAILBOX",
            "claims@pinnacle-insurance.co.uk",
        )
        self.ingest_interval = env_int(
            "INGEST_INTERVAL_SECONDS",
            30,
        )


settings = Settings()