import os
from pathlib import Path

from autogen_ext.models.openai import OpenAIChatCompletionClient
from dotenv import load_dotenv

# Keys are read from the .env sitting next to this file (see .env.example), so the
# lookup does not depend on the current working directory.
_ENV_PATH = Path(__file__).resolve().with_name(".env")
if not _ENV_PATH.exists():
    raise RuntimeError(
        f"No {_ENV_PATH.name} found next to llm.py. "
        "Copy .env.example to .env and fill in your API keys."
    )
load_dotenv(_ENV_PATH)


def _require_key(name: str) -> str:
    """Return the API key held in environment variable `name`, or fail with a clear message.

    The key is resolved explicitly instead of left as None: OpenAIChatCompletionClient
    would otherwise fall back to whatever OPENAI_API_KEY happens to be set in the
    environment, and the request would fail with a 401 that is hard to attribute.
    """
    value = os.environ.get(name, "").strip()
    if not value or "REPLACE_ME" in value:
        raise RuntimeError(
            f"Set a real API key in .env: variable '{name}' is "
            f"{'missing or empty' if not value else 'still the placeholder value'}."
        )
    return value


# deepseek-chat has no image input support, hence "vision": False. autogen strips
# images from the context when vision is False and raises when they are passed on,
# which is the behaviour we want rather than an opaque error from the API.
deepseekV3 = OpenAIChatCompletionClient(
            model="deepseek-chat",
            base_url="https://api.deepseek.com/v1",
            api_key=_require_key("DEEPSEEK_API_KEY"),
            model_info={
                "vision": False,
                "function_calling": True,
                "json_output": True,
                "family": "unknown",
                "structured_output": False,
                "multiple_system_messages": True,
            },
            seed=42,
            temperature=0
        )

deepseekR1 = OpenAIChatCompletionClient(
            model="deepseek-reasoner",
            base_url="https://api.deepseek.com/v1",
            api_key=_require_key("DEEPSEEK_API_KEY"),
            model_info={
                "vision": False,
                "function_calling": True,
                "json_output": True,
                "family": "unknown",
                "structured_output": False,
                "multiple_system_messages": True,
            },
            seed=42,
            temperature=0,
            max_tokens=12000
        )


qwen = OpenAIChatCompletionClient(
            model="qwen-vl-max",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key=_require_key("QWEN_API_KEY"),
            model_info={
                "vision": True,
                "function_calling": True,
                "json_output": True,
                "family": "unknown",
                "structured_output": False,
                "multiple_system_messages": True,
            },
            seed=42,
            temperature=0,
            max_tokens=6000
        )
