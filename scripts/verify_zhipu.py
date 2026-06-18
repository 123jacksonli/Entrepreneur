"""Verify the Zhipu-via-OpenRouter connection is working."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.llm_factory import create_completion, DEFAULT_MODEL


def main() -> None:
    print(f"Using model: {DEFAULT_MODEL}")

    content = create_completion(
        agent_id="research",
        system_prompt="You are a helpful assistant.",
        user_prompt="Say hello",
        max_tokens=50,
    )

    print(f"Response: {content}")


if __name__ == "__main__":
    main()
