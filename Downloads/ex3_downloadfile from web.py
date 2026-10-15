from dotenv import load_dotenv
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from claude_agent_sdk.types import (
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
)
import asyncio
import re
from pathlib import Path
from helper import parse_message, MODEL_NAME

DOWNLOADS_DIR = Path("downloads/downloads")
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)   # make sure the folder exists

# Tools that never need approval (read-only / search)
AUTO_ALLOWED = {"Read", "Glob", "WebSearch", "WebFetch"}

# Patterns that suggest a command downloads something
DOWNLOAD_PATTERN = re.compile(
    r"(Invoke-WebRequest|Invoke-RestMethod|\biwr\b|\birm\b|\bcurl\b|\bwget\b|"
    r"Start-BitsTransfer|DownloadFile|DownloadString)",
    re.IGNORECASE,
)


async def ask_user(prompt: str) -> str:
    # input() blocks, so run it in a thread to avoid freezing the event loop
    return await asyncio.to_thread(input, prompt)


async def custom_tool_checker(
    tool_name: str,
    input_data: dict,
    context: ToolPermissionContext,
) -> PermissionResultAllow | PermissionResultDeny:

    # Safe tools: allow without asking
    if tool_name in AUTO_ALLOWED:
        return PermissionResultAllow(behavior="allow")

    # Everything else (PowerShell) needs approval
    command = str(input_data.get("command", ""))
    is_download = bool(DOWNLOAD_PATTERN.search(command))

    if is_download:
        print("\n⬇️  Claude wants to DOWNLOAD a file:")
    else:
        print(f"\n🔧 Claude wants to run: {tool_name}")
    print(f"   Command: {command or input_data}")

    answer = (await ask_user("Allow? (y/n): ")).strip().lower()
    if answer == "y":
        return PermissionResultAllow(behavior="allow")
    return PermissionResultDeny(
        behavior="deny",
        message="User rejected the tool execution.",
    )


async def main():
    options = ClaudeAgentOptions(
        system_prompt=(
            "You are a helpful assistant. You can search the web, read pages, "
            "and download files. Save all downloaded files in the current "
            "working directory using PowerShell (e.g. Invoke-WebRequest -OutFile)."
        ),
        setting_sources=[],
        model=MODEL_NAME,
        max_turns=30,
        tools=["Read", "Glob", "PowerShell", "WebSearch", "WebFetch"],
        cwd=DOWNLOADS_DIR,
        permission_mode="default",
        can_use_tool=custom_tool_checker,
    )

    async with ClaudeSDKClient(options=options) as client:
        question = input("Give any instruction (search / download / read files): ")
        await client.query(question)
        async for message in client.receive_response():   # stops after final result
            parse_message(message)


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())