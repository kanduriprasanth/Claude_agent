from dotenv import load_dotenv
from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    tool,
    create_sdk_mcp_server,
)
from claude_agent_sdk.types import (
    PermissionResultAllow,
    PermissionResultDeny,
    ToolPermissionContext,
)
import asyncio
import re
import requests
from pathlib import Path
from helper import parse_message, MODEL_NAME

DOWNLOADS_DIR = Path("downloads/downloads")
DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)   # make sure the folder exists


# ---------- Custom tool: get_author ----------
def _lookup_author(book_name: str) -> str:
    """Blocking Open Library lookup (runs in a thread)."""
    try:
        resp = requests.get(
            "https://openlibrary.org/search.json",
            params={"title": book_name, "limit": 1, "fields": "title,author_name"},
            timeout=10,
        )
        resp.raise_for_status()
        docs = resp.json().get("docs", [])
    except requests.RequestException as e:
        return f"Error looking up '{book_name}': {e}"

    if not docs or "author_name" not in docs[0]:
        return f"No author found for '{book_name}'."
    return ", ".join(docs[0]["author_name"])


@tool(
    "get_author",
    "Get the author(s) of a book given its title.",
    {"book_name": str},
)
async def get_author(args: dict) -> dict:
    # requests is blocking, so run it in a thread to keep the event loop free
    result = await asyncio.to_thread(_lookup_author, args["book_name"])
    return {"content": [{"type": "text", "text": result}]}


# Bundle the tool into an in-process MCP server
book_server = create_sdk_mcp_server(
    name="books",
    version="1.0.0",
    tools=[get_author],
)

# MCP tool names follow the pattern: mcp__<server_name>__<tool_name>
GET_AUTHOR_TOOL = "mcp__books__get_author"


# Tools that never need approval (read-only / search)
AUTO_ALLOWED = {"Read", "Glob", "WebSearch", "WebFetch", GET_AUTHOR_TOOL}

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
            "working directory using PowerShell (e.g. Invoke-WebRequest -OutFile). "
            "When the user asks who wrote a book, use the get_author tool."
        ),
        setting_sources=[],
        model=MODEL_NAME,
        max_turns=30,
        tools=["Read", "Glob", "PowerShell", "WebSearch", "WebFetch"],
        mcp_servers={"books": book_server},        # register the custom tool server
        allowed_tools=[GET_AUTHOR_TOOL],           # pre-approve the custom tool
        cwd=DOWNLOADS_DIR,
        permission_mode="default",
        can_use_tool=custom_tool_checker,
    )

    async with ClaudeSDKClient(options=options) as client:
        question = input("Give any instruction (search / download / read files / book author): ")
        await client.query(question)
        async for message in client.receive_response():   # stops after final result
            parse_message(message)


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(main())