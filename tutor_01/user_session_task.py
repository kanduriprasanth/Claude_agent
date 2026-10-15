from dotenv import load_dotenv
import os
import json
import asyncio
from typing import Literal, Optional
from claude_agent_sdk import query
from helper import base_options, parse_messages

TONE_DICT = {
    'DETAILED': """You are a tutor, Explain the question asked in a 
    direct fashion. Ensure you add some examples to answer the question""",
    'REVISION': """You are a tutor, The question asked is before an exam, 
    Help in quickly revising to recollect the learnt topic and give simple, 
    crisp and necessary stuff.""",
    'BEGINNER': """You are a tutor, The question asked by the student who has
    zero or minimal conceptual knowledge. Dont make assumptions, Answer the question
    in a elaborate fashion right from concepts required to answer the question."""
}

SESSION_FILE = "sessions.json"

# ---------- session store ----------
def load_sessions() -> dict:
    if os.path.exists(SESSION_FILE):
        with open(SESSION_FILE, "r") as f:
            return json.load(f)
    return {}

def save_sessions(sessions: dict) -> None:
    with open(SESSION_FILE, "w") as f:
        json.dump(sessions, f, indent=2)

user_sessions: dict[str, str] = load_sessions()   # {'a': 'a_session_id', 'b': 'b_session_id'}


# ---------- conversation ----------
async def initiate_conversation(
    user_id: str,
    tone: Literal["DETAILED", "REVISION", "BEGINNER"],
    question: str = "What is difference between function and generator?"
):
    custom_options = {
        'system_prompt': TONE_DICT.get(tone, TONE_DICT['BEGINNER'])
    }

    # If this user already has a session, resume it
    existing_session: Optional[str] = user_sessions.get(user_id)
    if existing_session:
        custom_options['resume'] = existing_session
        print(f"Resuming session for '{user_id}': {existing_session}")
    else:
        print(f"Starting new session for '{user_id}'")

    options = base_options(**custom_options)

    count = 0
    async for message in query(prompt=question, options=options):
        count += 1
        print(f"{count}:{type(message)}")
        parse_messages(message=message)

        # ResultMessage (last message) carries the session_id
        session_id = getattr(message, "session_id", None)
        if session_id and user_sessions.get(user_id) != session_id:
            user_sessions[user_id] = session_id
            save_sessions(user_sessions)


async def ask_question():
    user_id = input("Enter your user id (e.g. a, b): ").strip()
    question = input("Enter your question: ")
    tone = input("Enter the tone DETAILED REVISION BEGINNER: ").strip().upper()
    await initiate_conversation(user_id, tone, question)


if __name__ == "__main__":
    load_dotenv()
    asyncio.run(ask_question())