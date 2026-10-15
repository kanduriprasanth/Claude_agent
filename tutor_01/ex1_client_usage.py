from dotenv import load_dotenv
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, InMemorySessionStore, query
import asyncio
from helper import parse_messages

MODEL_NAME='claude-haiku-4-5'

async def main():
    options=ClaudeAgentOptions(
        model=MODEL_NAME,
        system_prompt="You are helpful assistant",
        setting_sources=[],
        max_turns=3,
        resume="9fda14bb-dfc5-49fa-a915-9ee9f593ccb1"
    )
    async with ClaudeSDKClient(options=options) as client:
        # question="My name is prasanth i live in Hyderabad"
        # await client.query(question)
        # async for message in client.receive_messages():
        #     parse_messages(message)

        question="Where do i live?"
        await client.query(question)
        async for message in client.receive_messages():
            parse_messages(message)

if __name__=="__main__":
    load_dotenv()
    asyncio.run(main())

