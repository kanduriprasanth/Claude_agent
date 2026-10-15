"""Process-wide configuration: the frozen analysis clock, API key resolution,
and the Gemini model factory.

The clock matters more than it looks. Every "days since X" figure in this
package is computed against a single `as_of` value frozen at startup, so the
three analyst subagents cannot disagree about what "today" means -- and a run
that straddles midnight does not silently shift every metric by a day.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

# The simulator writes naive ISO strings in IST (quick_commerce_sim.py:55).
# We match that exactly: SQLite's datetime('now') is UTC and would be 5h30m off.
IST = timezone(timedelta(hours=5, minutes=30))

DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_DB = "qcommerce.db"

# Names the Google SDKs actually read, in the order they check them.
_SDK_KEY_NAMES = ("GOOGLE_API_KEY", "GEMINI_API_KEY")
# Names people commonly have exported instead. Bridged onto GOOGLE_API_KEY.
_KEY_ALIASES = ("GOOGLE_GEMINI_API_KEY", "GOOGLE_GENAI_API_KEY", "GEMINI_KEY")

_as_of: datetime | None = None


def freeze_as_of(override: str | None = None) -> datetime:
    """Freeze the analysis clock once per process and return it.

    Subsequent calls ignore their argument and return the frozen value, so
    tools invoked minutes apart still agree. Pass `override` (an ISO string)
    for reproducible runs against a fixed date.
    """
    global _as_of
    if _as_of is None:
        _as_of = (
            datetime.fromisoformat(override)
            if override
            else datetime.now(IST).replace(tzinfo=None)
        )
    return _as_of


def as_of_iso() -> str:
    """The frozen clock as the same ISO format the database stores."""
    return freeze_as_of().isoformat(sep=" ", timespec="seconds")


def load_env() -> None:
    """Load .env if present, then bridge any aliased key onto GOOGLE_API_KEY."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:  # optional at runtime; env vars still work
        pass

    if any(os.getenv(n) for n in _SDK_KEY_NAMES):
        return
    for alias in _KEY_ALIASES:
        value = os.getenv(alias)
        if value:
            os.environ["GOOGLE_API_KEY"] = value
            return


def vertex_enabled() -> bool:
    """True when GOOGLE_GENAI_USE_VERTEXAI is set truthy.

    ChatGoogleGenerativeAI reads this same variable to pick the Vertex backend
    over the Developer API, so honouring it here keeps auth and routing in sync.
    """
    return os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "").strip().lower() in ("1", "true", "yes")


def require_credentials() -> None:
    """Ensure the model has a way to authenticate, for whichever backend is active.

    Vertex authenticates via Application Default Credentials (gcloud auth
    application-default login) or a service account -- not an API key -- so it
    only needs a project set. The Developer API needs a key.
    """
    load_env()
    if vertex_enabled():
        if not os.getenv("GOOGLE_CLOUD_PROJECT"):
            raise SystemExit(
                "GOOGLE_GENAI_USE_VERTEXAI is set but GOOGLE_CLOUD_PROJECT is not.\n"
                "  Set GOOGLE_CLOUD_PROJECT (and GOOGLE_CLOUD_LOCATION) in .env, and make\n"
                "  sure `gcloud auth application-default login` has been run."
            )
        return
    if any(os.getenv(n) for n in _SDK_KEY_NAMES):
        return
    raise SystemExit(
        "No Gemini credentials found.\n"
        "  Developer API: set GOOGLE_API_KEY (or GEMINI_API_KEY), or put it in .env.\n"
        f"    Aliases bridged automatically: {', '.join(_KEY_ALIASES)}\n"
        "  Vertex AI: set GOOGLE_GENAI_USE_VERTEXAI=true and GOOGLE_CLOUD_PROJECT.\n"
        "  Run with --no-llm to skip the model entirely."
    )


def build_model(model_name: str | None = None):
    """Return a Gemini chat model, routed to Vertex or the Developer API by env.

    The `google_genai:` prefix is required either way. ChatGoogleGenerativeAI
    picks the backend from GOOGLE_GENAI_USE_VERTEXAI itself; a bare "gemini-..."
    string would make init_chat_model infer the wrong provider.
    """
    from langchain.chat_models import init_chat_model

    require_credentials()
    name = model_name or os.getenv("CHURN_MODEL") or DEFAULT_MODEL
    return init_chat_model(f"google_genai:{name}", temperature=0)


def db_path(explicit: str | None = None) -> str:
    return explicit or os.getenv("CHURN_DB") or DEFAULT_DB
