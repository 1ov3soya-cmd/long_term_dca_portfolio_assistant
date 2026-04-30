"""Render structured agent research into a readable markdown memo."""

from __future__ import annotations

from src.agent_research.research_schema import AgentResearchResult


class ResearchMemoGenerator:
    """Convert structured research results into a Markdown memo."""

    def render(self, result: AgentResearchResult) -> str:
        """Render a research memo for one symbol."""

        lines = [
            f"# TradingAgents Research Memo - {result.symbol}",
            "",
            f"- analysis_date: {result.analysis_date}",
            f"- source: {result.source}",
            f"- final_research_label: {result.final_research_label}",
            f"- confidence: {result.confidence}",
            f"- debate_focus: {result.debate_focus or 'N/A'}",
            f"- key_uncertainty: {result.key_uncertainty or 'N/A'}",
            "",
            "## Bull Case",
            result.bull_case,
            "",
            "### Bull Evidence Points",
        ]

        if result.bull_evidence_points:
            lines.extend([f"- {point}" for point in result.bull_evidence_points])
        else:
            lines.append("- N/A")

        lines.extend(
            [
                "",
                "### Bull Action Implication",
                result.bull_action_implication or "N/A",
                "",
                "## Bear Case",
                result.bear_case,
                "",
                "### Bear Evidence Points",
            ]
        )

        if result.bear_evidence_points:
            lines.extend([f"- {point}" for point in result.bear_evidence_points])
        else:
            lines.append("- N/A")

        lines.extend(
            [
                "",
                "### Bear Action Implication",
                result.bear_action_implication or "N/A",
                "",
                "## Risk Summary",
                result.risk_summary,
                "",
                "## Recommendation Rationale",
                result.recommendation_rationale or "N/A",
                "",
                "## Manual Risk Mapping Suggestion",
                f"- suggest_manual_pause_buy: {result.suggest_manual_pause_buy}",
                f"- suggest_force_review: {result.suggest_force_review}",
                f"- suggest_thesis_broken: {result.suggest_thesis_broken}",
                "",
                "## Notes",
                result.notes,
                "",
                "## Boundary Reminder",
                "- This memo is for research enhancement and manual review support only.",
                "- It does not automatically write back to manual risk flags.",
                "- It does not generate trading execution instructions.",
                "",
            ]
        )
        return "\n".join(lines)
