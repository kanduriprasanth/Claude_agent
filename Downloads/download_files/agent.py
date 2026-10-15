"""Builds the deep agent: one orchestrator over three analyst subagents.

Wiring notes that are easy to get wrong with deepagents 0.6.12:

* The subagent key is **`system_prompt`**, not `prompt`. The wrong key raises
  KeyError at build time -- loud, so it is the least dangerous mistake here.
* Never add a `graph_id` or `runnable` key. Dispatch is decided by key presence,
  and either one silently reroutes to a different subagent implementation.
* `subagent_type` in a `task` call must match a subagent `name` exactly. A typo
  routes to the auto-injected `general-purpose` agent, which answers plausibly
  and wrongly. Hence the shared name constants in prompts.py.
* Omitting `tools` on a subagent makes it **inherit the parent's tools**. Every
  subagent here sets `tools` explicitly so the usage analyst cannot reach for
  ticket data, or for churn_scores.
* The model must be passed explicitly. deepagents defaults to Anthropic, which
  in a Gemini project produces a baffling ANTHROPIC_API_KEY error.
"""

from __future__ import annotations

from deepagents import create_deep_agent

from churn_agent import db, prompts, tools
from churn_agent.config import as_of_iso, build_model, db_path
from churn_agent.schemas import ChurnReport, ReviewFindings, SupportFindings, UsageFindings


def build_subagents(model) -> list[dict]:
    """The three analysts. Plain dicts -- SubAgent is a TypedDict."""
    return [
        {
            "name": prompts.USAGE,
            "description": (
                "Analyses login and ordering behaviour across the whole customer "
                "cohort: recency, cadence and spend change. This is the primary "
                "churn signal. Dispatch once, cohort-wide."
            ),
            "system_prompt": prompts.USAGE_SYSTEM,
            "tools": tools.USAGE_TOOLS,
            "model": model,
            "response_format": UsageFindings,
        },
        {
            "name": prompts.SUPPORT,
            "description": (
                "Analyses support ticket friction across the whole cohort: unresolved "
                "tickets, priority and category. Use for explaining what a flagged "
                "customer is dealing with, not for predicting churn. Dispatch once."
            ),
            "system_prompt": prompts.SUPPORT_SYSTEM,
            "tools": tools.SUPPORT_TOOLS,
            "model": model,
            "response_format": SupportFindings,
        },
        {
            "name": prompts.REVIEW,
            "description": (
                "Analyses product review sentiment across the whole cohort and quotes "
                "specific complaints. Use for colour on a flagged customer, not for "
                "predicting churn. Dispatch once."
            ),
            "system_prompt": prompts.REVIEW_SYSTEM,
            "tools": tools.REVIEW_TOOLS,
            "model": model,
            "response_format": ReviewFindings,
        },
    ]


def build_agent(database: str | None = None, model_name: str | None = None):
    """Wire up the orchestrator and return the compiled graph."""
    db.configure(db_path(database))
    model = build_model(model_name)

    return create_deep_agent(
        model,
        tools.ORCHESTRATOR_TOOLS,
        system_prompt=prompts.ORCHESTRATOR_SYSTEM.format(
            as_of=as_of_iso(),
            usage=prompts.USAGE,
            support=prompts.SUPPORT,
            review=prompts.REVIEW,
        ),
        subagents=build_subagents(model),
        response_format=ChurnReport,
    )


def run(agent, top: int = 12) -> dict:
    """Invoke the agent and return its final state."""
    return agent.invoke(
        {"messages": [{"role": "user", "content": prompts.USER_REQUEST.format(top=top)}]},
        # Orchestrator turns + 3 subagent dispatches + scoring exceeds the default 25.
        {"recursion_limit": 80},
    )
