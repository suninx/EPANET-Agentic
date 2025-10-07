import os
from autogen_ext.models.openai import OpenAIChatCompletionClient


deepseekV3 = OpenAIChatCompletionClient(
            model="deepseek-chat",
            base_url="https://api.deepseek.com/v1",
            api_key=os.environ.get("OPENAI_API_KEY"),
            model_info={
                "vision": True,
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
            api_key=os.environ.get("OPENAI_API_KEY"),
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
            max_tokens=12000
        )


qwen = OpenAIChatCompletionClient(
            model="qwen-vl-max",
            base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
            api_key='sk-xxxxxxxxxxxxxxxxxxxxx',
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