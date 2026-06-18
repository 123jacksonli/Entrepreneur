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

    # Autonomous operation safeguards
    MAX_IDEA_ITERATIONS = int(os.getenv("MAX_IDEA_ITERATIONS", "3"))
    MAX_QA_ITERATIONS = int(os.getenv("MAX_QA_ITERATIONS", "3"))
    MAX_TOKENS_PER_AGENT = int(os.getenv("MAX_TOKENS_PER_AGENT", "0")) or None
    STOP_ON_HIGH_COST = os.getenv("STOP_ON_HIGH_COST", "false").lower() == "true"

    # Execution Agent version control
    EXEC_BRANCH_PREFIX = os.getenv("EXEC_BRANCH_PREFIX", "exec")
    GITHUB_REPO = os.getenv("GITHUB_REPO")  # owner/repo format, e.g. "123jacksonli/Entrepreneur"

    @classmethod
    def api_key_and_base_url(cls) -> tuple[str, str]:
        if cls.ZHIPU_API_KEY:
            return cls.ZHIPU_API_KEY, cls.ZHIPU_BASE_URL
        if cls.OPENAI_API_KEY:
            return cls.OPENAI_API_KEY, cls.OPENAI_BASE_URL
        raise ValueError("No API key configured. Set OPENAI_API_KEY or ZHIPU_API_KEY.")
