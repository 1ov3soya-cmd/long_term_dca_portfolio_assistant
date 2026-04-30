"""Agent research output schema for advisory-only research debate."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Literal


ResearchLabel = Literal[
    "neutral_watch",
    "pause_candidate",
    "force_review_candidate",
    "thesis_broken_candidate",
]


@dataclass(slots=True)
class AgentResearchResult:
    """Structured advisory-only research result.

    The schema keeps backward compatibility with the original fields while adding
    richer debate metadata for downstream reports and frontend display.
    """

    symbol: str
    analysis_date: str
    bull_case: str
    bear_case: str
    risk_summary: str
    final_research_label: ResearchLabel
    suggest_manual_pause_buy: bool
    suggest_force_review: bool
    suggest_thesis_broken: bool
    confidence: float
    notes: str
    bull_evidence_points: list[str] = field(default_factory=list)
    bear_evidence_points: list[str] = field(default_factory=list)
    bull_action_implication: str = ""
    bear_action_implication: str = ""
    debate_focus: str = ""
    key_uncertainty: str = ""
    recommendation_rationale: str = ""
    source: str = "tradingagents_poc"

    def to_dict(self) -> dict:
        """Convert the dataclass into a JSON-serializable dictionary."""

        return asdict(self)
