"""Structured hand-off between the analysts and the orchestrator.

A subagent's reply reaches the parent as text unless it has a `response_format`,
in which case the parent receives serialized JSON instead of prose. These models
are that contract.

Two shape rules, both load-bearing:

* **Flat.** Gemini's schema translation is stricter than Anthropic's, so no
  nested models beyond one level, no `dict[str, Any]`, and `-1` sentinels
  instead of `int | None`.
* **No score fields on the analyst models.** An analyst has nowhere to put a
  risk number even if it wants to. Structure enforces what a prompt only asks.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------- #
# usage-analyst
# --------------------------------------------------------------------------- #
class UsageRow(BaseModel):
    u: int = Field(description="user_id")
    dl: int = Field(description="days since last login, -1 if never")
    do: int = Field(description="days since last order, -1 if never")
    st: str = Field(description="active|at_risk|dormant|browsing_not_buying|never_ordered")
    note: str = Field(description="<=90 chars on what the numbers show. No risk score.")


class UsageFindings(BaseModel):
    as_of: str
    n_customers: int
    rows: list[UsageRow] = Field(description="Only customers who are not plainly active.")
    dormant_ids: list[int] = Field(description="No login AND no orders beyond the threshold.")
    browsing_not_buying_ids: list[int] = Field(
        description="Logging in recently but not ordering. A conversion problem, not churn."
    )
    caveats: str = Field(description="<=400 chars. Data-quality notes only.")


# --------------------------------------------------------------------------- #
# support-analyst
# --------------------------------------------------------------------------- #
class SupportRow(BaseModel):
    u: int = Field(description="user_id")
    tk: int = Field(description="tickets in window")
    unres: int = Field(description="unresolved tickets")
    cat: str = Field(description="dominant category")
    note: str = Field(description="<=90 chars of concrete detail worth showing a human.")


class SupportFindings(BaseModel):
    as_of: str
    n_with_tickets: int
    rows: list[SupportRow] = Field(description="Only customers with unresolved or high-priority tickets.")
    friction_ids: list[int] = Field(description="Customers carrying unresolved tickets.")
    caveats: str = Field(
        description="Must state that ticket data cannot predict churn in this dataset."
    )


# --------------------------------------------------------------------------- #
# review-analyst
# --------------------------------------------------------------------------- #
class ReviewRow(BaseModel):
    u: int = Field(description="user_id")
    n: int = Field(description="reviews in window")
    avg: float = Field(description="mean rating")
    neg: int = Field(description="ratings <= 2")
    quote: str = Field(description="Short quote from their most negative recent review.")


class ReviewFindings(BaseModel):
    as_of: str
    n_with_reviews: int
    rows: list[ReviewRow] = Field(description="Only customers who left a negative review.")
    detractor_ids: list[int]
    caveats: str = Field(
        description="Must state that rating trends cannot predict churn in this dataset."
    )


# --------------------------------------------------------------------------- #
# orchestrator
# --------------------------------------------------------------------------- #
class CustomerFinding(BaseModel):
    u: int = Field(description="user_id")
    band: str = Field(description="Copied verbatim from churn_scores. Never recomputed.")
    score: int = Field(description="Copied verbatim from churn_scores. Never recomputed.")
    why: str = Field(description="<=220 chars. What the behaviour shows, citing the numbers.")
    corroboration: str = Field(
        description="Support/review detail for this customer, or '' if none. Explanation only."
    )
    action: str = Field(description="<=120 chars. The intervention this band calls for.")


class ChurnReport(BaseModel):
    as_of: str
    headline: str = Field(description="One sentence on the state of the cohort.")
    findings: list[CustomerFinding]
    caveats: str = Field(description="What this analysis cannot conclude, and why.")
