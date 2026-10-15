"""LangChain tool wrappers over the metric functions.

Thin by design -- all logic lives in `churn_agent.metrics` so it stays testable
without a model. Cohort tools take no `user_id` parameter, which is the real
reason the analysts scan the cohort once instead of looping over 40 customers:
per-customer iteration is simply not expressible.

Results are memoized on their arguments so a retried or duplicated call is a
dict lookup, and every analyst in a run sees identical numbers.
"""

from __future__ import annotations

from functools import lru_cache

from langchain_core.tools import tool

from churn_agent.metrics import churn as churn_metrics
from churn_agent.metrics import reviews as reviews_metrics
from churn_agent.metrics import support as support_metrics
from churn_agent.metrics import usage as usage_metrics


@lru_cache(maxsize=8)
def _usage_cohort(window_days: int, baseline_days: int) -> dict:
    return usage_metrics.cohort(window_days=window_days, baseline_days=baseline_days)


@lru_cache(maxsize=8)
def _support_cohort(window_days: int) -> dict:
    return support_metrics.cohort(window_days=window_days)


@lru_cache(maxsize=8)
def _reviews_cohort(window_days: int, recent_days: int) -> dict:
    return reviews_metrics.cohort(window_days=window_days, recent_days=recent_days)


@lru_cache(maxsize=4)
def _churn_scores(top_n: int) -> dict:
    return churn_metrics.scores(top_n=top_n)


# --------------------------------------------------------------------------- #
# usage-analyst tools
# --------------------------------------------------------------------------- #
@tool
def usage_cohort_metrics(window_days: int = 30, baseline_days: int = 90) -> dict:
    """Login recency, order recency, baseline cadence and spend change for EVERY
    customer, ranked most-inactive first. Covers the whole cohort in one call --
    call it once; there is no per-customer variant and no need to loop.

    Login recency and order recency are separate fields on purpose: a recent
    login with stale orders is a conversion problem, not churn.
    """
    return _usage_cohort(window_days, baseline_days)


@tool
def usage_customer_detail(user_id: int) -> dict:
    """Session and order timeline for ONE customer. Use only to explain a
    customer already surfaced by usage_cohort_metrics, not to survey the cohort.
    """
    return usage_metrics.customer_detail(user_id)


# --------------------------------------------------------------------------- #
# support-analyst tools
# --------------------------------------------------------------------------- #
@tool
def support_cohort_metrics(window_days: int = 90) -> dict:
    """Ticket volume, unresolved count, dominant category and median resolution
    time for every customer who raised a ticket. Whole cohort in one call.

    Customers with no tickets are omitted rather than returned as zero rows.
    """
    return _support_cohort(window_days)


@tool
def support_customer_detail(user_id: int) -> dict:
    """Full ticket history for ONE customer, with subjects and ages."""
    return support_metrics.customer_detail(user_id)


# --------------------------------------------------------------------------- #
# review-analyst tools
# --------------------------------------------------------------------------- #
@tool
def review_cohort_metrics(window_days: int = 90, recent_days: int = 30) -> dict:
    """Rating average, recent-vs-prior delta, negative count and latest review
    title for every customer who reviewed. Whole cohort in one call.
    """
    return _reviews_cohort(window_days, recent_days)


@tool
def review_customer_detail(user_id: int) -> dict:
    """Recent reviews with full text and product names for ONE customer."""
    return reviews_metrics.customer_detail(user_id)


# --------------------------------------------------------------------------- #
# orchestrator tool
# --------------------------------------------------------------------------- #
@tool
def churn_scores(top_n: int = 0) -> dict:
    """Deterministic churn risk scores and bands for the whole cohort, ranked.

    This is the ONLY source of risk numbers. Copy `score` and `band` from here
    verbatim into the report -- do not compute, adjust, average or re-derive
    them. Pass top_n=0 for every customer.
    """
    return _churn_scores(top_n)


USAGE_TOOLS = [usage_cohort_metrics, usage_customer_detail]
SUPPORT_TOOLS = [support_cohort_metrics, support_customer_detail]
REVIEW_TOOLS = [review_cohort_metrics, review_customer_detail]
ORCHESTRATOR_TOOLS = [churn_scores]
