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


# Model names: `deepseek-chat` and `deepseek-reasoner` are legacy aliases. Measured against the
# live API they still respond, and both are served by DeepSeek-V4.1-Flash - the aliases differ
# only in thinking mode (off / on). `deepseek-v4-pro` is a genuinely separate model.
#
# Do NOT "modernise" the two strings below to `deepseek-flash`. Thinking mode is enabled by
# default at effort high, this framework never sends `reasoning_content` back (it maps
# `thought` into `content`), and DeepSeek then rejects the multi-turn tool loop with:
#     400 The `reasoning_content` in the thinking mode must be passed back to the API.
# That would break exactly Orchestrator and TaskExecutor - the two agents that pass `tools=`.
# If switching to `deepseek-flash` ever becomes unavoidable, thinking must be disabled too.
# autogen-ext 0.6.1 has no supported way to do that: the constructor silently drops `extra_body`
# and `extra_create_args` rejects it; only assigning
# `client._create_args["extra_body"] = {"thinking": {"type": "disabled"}}` was observed to work.
#
# vision is declared False for these text-oriented clients. autogen strips images when vision is
# False and raises if they are passed anyway, which is the safer behaviour. Whether the aliases
# accept images (the model serving them is multimodal) has not been measured - re-test before
# flipping this to True.
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
