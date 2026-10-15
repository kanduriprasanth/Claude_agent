from claude_agent_sdk import(
    ClaudeAgentOptions,
    Message,
    AssistantMessage,
    UserMessage,
    SystemMessage,
    ResultMessage
)
from dotenv import load_dotenv
import os

from claude_agent_sdk.types import TextBlock
Model_Name='claude-haiku-4-5'

def base_options(**arguments) -> ClaudeAgentOptions:
    settings={
        'model':Model_Name,
        'max_turns':3,
        'cli_path': os.path.expanduser(r"C:\Users\kandu\.local\bin\claude.exe")
    }
    settings.update(arguments)
    options=ClaudeAgentOptions(**settings)
    return options

def parse_messages(message:Message):
    if isinstance(message,SystemMessage):
        print(f"subtype:{message.subtype}")
    elif isinstance(message,AssistantMessage):
        for block in message.content:
            if isinstance(block,TextBlock):
                print(block.text)
    elif isinstance(message,ResultMessage):
        print(f"duration: {message.duration_ms}ms")
        print(f"cost in usd:{message.total_cost_usd}ms")
        print(f"session_id:{message.session_id}")
