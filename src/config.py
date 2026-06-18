"""Application configuration loaded from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    DEFAULT_AGENT_MODEL = os.getenv("DEFAULT_AGENT_MODEL", "z-ai/glm-4.5")
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://openrouter.ai/api/v1")
    ZHIPU_API_KEY = os.getenv("ZHIPU_API_KEY")
    ZHIPU_BASE_URL = os.getenv("ZHIPU_BASE_URL", "https://open.bigmodel.cn/api/paas/v4")
    SQLITE_PATH = os.getenv("SQLITE_PATH", "data/entrepreneur.db")
    OUTPUTS_DIR = os.getenv("OUTPUTS_DIR", "outputs")

    @classmethod
    def api_key_and_base_url(cls) -> tuple[str, str]:
        if cls.ZHIPU_API_KEY:
            return cls.ZHIPU_API_KEY, cls.ZHIPU_BASE_URL
        if cls.OPENAI_API_KEY:
            return cls.OPENAI_API_KEY, cls.OPENAI_BASE_URL
        raise ValueError("No API key configured. Set OPENAI_API_KEY or ZHIPU_API_KEY.")
