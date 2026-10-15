from dotenv import load_dotenv
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, InMemorySessionStore, query
import asyncio
from helper import parse_message,MODEL_NAME
from pathlib import Path

Downloads_DIR=Path("Downloads/download_files")

async def main():
    options=ClaudeAgentOptions(
        system_prompt="You are a helpful assistant",
        setting_sources=[],
        model=MODEL_NAME,
        max_turns=20,
        tools=["Read","Glob","PowerShell"],
        permission_mode="bypassPermissions",
        cwd=Downloads_DIR,
    )

    async with ClaudeSDKClient(options=options) as client:
        question=input("Give any instructions about download folder")
        await client.query(question)
        async for message in client.receive_messages():
            parse_message(message)


# async with ClaudeSDKClient(options=options) as client:
#     while True:
#         question = input("Instruction (or 'exit'): ")
#         if question.strip().lower() in {"exit", "quit"}:
#             break
#         await client.query(question)
#         async for message in client.receive_response():
#             parse_message(message)

if __name__=="__main__":
    load_dotenv()
    asyncio.run(main())
