"""Monthly research debate batch service."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.agent_research.research_schema import AgentResearchResult
from src.agent_research.tradingagents_bridge import TradingAgentsBridge
from src.utils.logger import get_logger


def _normalize_archive_path(project_root: Path, value: str | None) -> Path | None:
    """Convert archived absolute/relative paths to a local project path."""

    if not value:
        return None

    raw = str(value).replace("\\", "/")
    if raw.startswith("reports/") or raw.startswith("config/"):
        return project_root / raw

    reports_index = raw.find("/reports/")
    if reports_index >= 0:
        return project_root / raw[reports_index + 1 :]

    config_index = raw.find("/config/")
    if config_index >= 0:
        return project_root / raw[config_index + 1 :]

    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    return project_root / candidate


def _to_bool(value: Any) -> bool:
    """Normalize booleans from csv/json payloads."""

    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y"}
    return False


def _to_float(value: Any) -> float:
    """Normalize numeric values while preserving zero."""

    if value in (None, ""):
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


class MonthlyResearchService:
    """Generate monthly research debate batches from suggest details."""

    def __init__(self, project_root: str | Path, configs: dict[str, dict[str, Any]]) -> None:
        self.project_root = Path(project_root)
        self.configs = configs
        self.logger = get_logger(
            self.__class__.__name__,
            configs.get("app", {}).get("runtime", {}).get("log_level", "INFO"),
        )
        self.bridge = TradingAgentsBridge(project_root=self.project_root, configs=configs)
        self.output_root = self.project_root / "reports" / "agent_research" / "monthly"
        self.output_root.mkdir(parents=True, exist_ok=True)

    def run(
        self,
        end_date: str,
        source_research_run_id: str,
        suggest_run_id: str | None = None,
    ) -> dict[str, Any]:
        """Generate a monthly research batch from the latest suggest detail."""

        suggest_source = self._resolve_suggest_source(end_date=end_date, suggest_run_id=suggest_run_id)
        suggestion_rows = self._load_suggestion_rows(suggest_source["csv_path"])
        if not suggestion_rows:
            raise ValueError(f"未找到可用于 monthly research 的建议明细: {suggest_source['csv_path']}")

        items = [
            self._build_debate_item(
                row=row,
                analysis_date=end_date,
                source_suggest_run=suggest_source["source_suggest_run"],
                source_research_run=source_research_run_id,
            )
            for row in suggestion_rows
        ]

        summary = self._build_summary(
            batch_id=source_research_run_id,
            source_suggest_run=suggest_source["source_suggest_run"],
            items=items,
        )
        report_markdown = self._render_report(summary=summary, items=items, source=suggest_source)
        paths = self._write_batch(
            batch_id=source_research_run_id,
            summary=summary,
            items=items,
            report_markdown=report_markdown,
            source=suggest_source,
        )

        self.logger.info(
            "Monthly research debate generated: batch_id=%s, items=%s",
            summary["batch_id"],
            len(items),
        )
        return {
            "summary": summary,
            "items": items,
            "paths": paths,
            "source": suggest_source,
        }

    def _resolve_suggest_source(self, end_date: str, suggest_run_id: str | None) -> dict[str, str]:
        """Resolve the best suggest detail source."""

        if suggest_run_id:
            from_run = self._resolve_from_run_id(suggest_run_id)
            if from_run:
                return from_run

        latest_index_path = self.project_root / "reports" / "runs" / "latest_index.json"
        if latest_index_path.exists():
            try:
                payload = json.loads(latest_index_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = {}
            latest_suggest = payload.get("suggest", {})
            latest_suggest_run = latest_suggest.get("run_id")
            if latest_suggest_run:
                from_latest = self._resolve_from_run_id(latest_suggest_run)
                if from_latest:
                    return from_latest

        shared_csv = self.project_root / "reports" / "monthly" / f"monthly_suggestion_{end_date.replace('-', '')}.csv"
        if shared_csv.exists():
            return {
                "source_type": "shared_monthly_report",
                "source_suggest_run": "",
                "csv_path": str(shared_csv),
                "report_path": str(
                    self.project_root / "reports" / "monthly" / f"monthly_report_{end_date.replace('-', '')}.md"
                ),
            }

        raise ValueError("未找到 suggest 明细来源，请先生成月度建议报告。")

    def _resolve_from_run_id(self, run_id: str) -> dict[str, str] | None:
        """Resolve monthly suggestion detail from an archived suggest run."""

        output_artifacts_path = self.project_root / "reports" / "runs" / run_id / "output_artifacts.json"
        if not output_artifacts_path.exists():
            return None

        try:
            payload = json.loads(output_artifacts_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

        artifacts = payload.get("original_outputs", {})
        monthly_report = artifacts.get("monthly_report", {})
        csv_path = _normalize_archive_path(self.project_root, monthly_report.get("csv"))
        markdown_path = _normalize_archive_path(self.project_root, monthly_report.get("markdown"))

        if csv_path and csv_path.exists():
            return {
                "source_type": "suggest_run",
                "source_suggest_run": run_id,
                "csv_path": str(csv_path),
                "report_path": str(markdown_path) if markdown_path else "",
            }
        return None

    @staticmethod
    def _load_suggestion_rows(csv_path: str) -> list[dict[str, str]]:
        """Load suggestion detail rows from CSV."""

        with Path(csv_path).open("r", encoding="utf-8-sig", newline="") as handle:
            return list(csv.DictReader(handle))

    def _build_debate_item(
        self,
        row: dict[str, str],
        analysis_date: str,
        source_suggest_run: str,
        source_research_run: str,
    ) -> dict[str, Any]:
        """Convert one suggest row into one research debate item."""

        symbol = str(row.get("symbol", "")).strip()
        asset_type = str(row.get("asset_type", "")).strip().lower()
        suggested_amount = _to_float(row.get("recommended_amount"))
        action_text = row.get("final_human_readable_action") or row.get("status") or ""
        logic_note = row.get("logic_note") or row.get("reasons") or ""

        context = {
            "asset_type": asset_type or "unknown",
            "suggested_amount": suggested_amount,
            "target_weight": _to_float(row.get("target_weight")),
            "current_weight": _to_float(row.get("current_weight")),
            "suggest_status": row.get("status", ""),
            "final_action": action_text,
            "reasons": row.get("reasons", ""),
            "logic_note": logic_note,
            "manual_pause_buy": _to_bool(row.get("manual_pause_buy")),
            "manual_force_review": _to_bool(row.get("manual_force_review")),
            "thesis_broken": _to_bool(row.get("thesis_broken")),
            "pause_buy": _to_bool(row.get("pause_buy")),
            "final_priority_level": row.get("final_priority_level"),
            "final_reason_codes": row.get("final_reason_codes", ""),
        }
        research = self.bridge.run_symbol_research(
            symbol=symbol,
            analysis_date=analysis_date,
            context=context,
        )

        return {
            "symbol": symbol,
            "asset_type": asset_type or "unknown",
            "suggested_amount": suggested_amount,
            "bull_case": research.bull_case,
            "bear_case": research.bear_case,
            "risk_summary": research.risk_summary,
            "final_research_label": research.final_research_label,
            "suggest_manual_pause_buy": bool(research.suggest_manual_pause_buy),
            "suggest_force_review": bool(research.suggest_force_review),
            "suggest_thesis_broken": bool(research.suggest_thesis_broken),
            "confidence": float(research.confidence),
            "note": logic_note,
            "suggest_action_text": action_text,
            "suggest_status": row.get("status", ""),
            "manual_pause_buy": _to_bool(row.get("manual_pause_buy")),
            "manual_force_review": _to_bool(row.get("manual_force_review")),
            "manual_thesis_broken": _to_bool(row.get("thesis_broken")),
            "pause_buy": _to_bool(row.get("pause_buy")),
            "bull_evidence_points": list(research.bull_evidence_points),
            "bear_evidence_points": list(research.bear_evidence_points),
            "bull_action_implication": research.bull_action_implication,
            "bear_action_implication": research.bear_action_implication,
            "debate_focus": research.debate_focus,
            "key_uncertainty": research.key_uncertainty,
            "recommendation_rationale": research.recommendation_rationale,
            "source_suggest_run": source_suggest_run,
            "source_research_run": source_research_run,
            "source": research.source,
        }

    @staticmethod
    def _build_summary(
        batch_id: str,
        source_suggest_run: str,
        items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Build batch summary for frontend and archival consumers."""

        processed_targets = len(items)
        pause_count = sum(1 for item in items if item["suggest_manual_pause_buy"])
        force_review_count = sum(1 for item in items if item["suggest_force_review"])
        thesis_broken_count = sum(1 for item in items if item["suggest_thesis_broken"])
        average_confidence = (
            round(sum(float(item["confidence"]) for item in items) / processed_targets, 4)
            if processed_targets
            else 0.0
        )
        attention_items = sorted(
            items,
            key=lambda item: (
                0 if item["suggest_thesis_broken"] else 1 if item["suggest_force_review"] else 2 if item["suggest_manual_pause_buy"] else 3,
                -float(item["confidence"]),
            ),
        )
        top_attention_symbols = [item["symbol"] for item in attention_items[:3]]

        return {
            "batch_id": batch_id,
            "source_suggest_run": source_suggest_run,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "total_targets": processed_targets,
            "processed_targets": processed_targets,
            "pause_candidate_count": pause_count,
            "force_review_candidate_count": force_review_count,
            "thesis_broken_candidate_count": thesis_broken_count,
            "average_confidence": average_confidence,
            "top_attention_symbols": top_attention_symbols,
        }

    def _write_batch(
        self,
        batch_id: str,
        summary: dict[str, Any],
        items: list[dict[str, Any]],
        report_markdown: str,
        source: dict[str, str],
    ) -> dict[str, Path]:
        """Persist batch outputs and refresh latest monthly research index."""

        batch_dir = self.output_root / batch_id
        batch_dir.mkdir(parents=True, exist_ok=True)

        batch_manifest = {
            "batch_id": batch_id,
            "generated_at": summary["generated_at"],
            "source_type": source["source_type"],
            "source_suggest_run": source["source_suggest_run"],
            "source_csv_path": source["csv_path"],
            "source_report_path": source.get("report_path", ""),
            "total_targets": summary["total_targets"],
        }

        paths = {
            "batch_manifest": batch_dir / "batch_manifest.json",
            "monthly_research_summary": batch_dir / "monthly_research_summary.json",
            "debate_items": batch_dir / "debate_items.json",
            "monthly_research_report": batch_dir / "monthly_research_report.md",
        }

        paths["batch_manifest"].write_text(json.dumps(batch_manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        paths["monthly_research_summary"].write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        paths["debate_items"].write_text(json.dumps({"items": items}, ensure_ascii=False, indent=2), encoding="utf-8")
        paths["monthly_research_report"].write_text(report_markdown, encoding="utf-8")

        self._update_latest_index(batch_id=batch_id, summary=summary, paths=paths, source=source)
        return paths

    def _update_latest_index(
        self,
        batch_id: str,
        summary: dict[str, Any],
        paths: dict[str, Path],
        source: dict[str, str],
    ) -> None:
        """Maintain a frontend-friendly latest monthly research index."""

        index_path = self.output_root / "latest_monthly_research_index.json"
        payload = {
            "updated_at": summary["generated_at"],
            "latest": {
                "batch_id": batch_id,
                "source_suggest_run": source["source_suggest_run"],
                "source_type": source["source_type"],
                "summary_relative_path": str(paths["monthly_research_summary"].relative_to(self.project_root)).replace("\\", "/"),
                "items_relative_path": str(paths["debate_items"].relative_to(self.project_root)).replace("\\", "/"),
                "report_relative_path": str(paths["monthly_research_report"].relative_to(self.project_root)).replace("\\", "/"),
                "manifest_relative_path": str(paths["batch_manifest"].relative_to(self.project_root)).replace("\\", "/"),
                "summary": summary,
            },
        }
        index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def _render_report(summary: dict[str, Any], items: list[dict[str, Any]], source: dict[str, str]) -> str:
        """Render markdown report for batch review."""

        lines = [
            "# Monthly Research Debate",
            "",
            f"- batch_id: {summary['batch_id']}",
            f"- generated_at: {summary['generated_at']}",
            f"- source_type: {source['source_type']}",
            f"- source_suggest_run: {source['source_suggest_run'] or 'N/A'}",
            f"- source_csv_path: {source['csv_path']}",
            "",
            "## Summary",
            "",
            f"- total_targets: {summary['total_targets']}",
            f"- processed_targets: {summary['processed_targets']}",
            f"- pause_candidate_count: {summary['pause_candidate_count']}",
            f"- force_review_candidate_count: {summary['force_review_candidate_count']}",
            f"- thesis_broken_candidate_count: {summary['thesis_broken_candidate_count']}",
            f"- average_confidence: {summary['average_confidence']}",
            f"- top_attention_symbols: {', '.join(summary['top_attention_symbols']) if summary['top_attention_symbols'] else 'N/A'}",
            "",
            "## Debate Items",
            "",
        ]

        for item in items:
            bull_points = [f"- {point}" for point in item["bull_evidence_points"]] or ["- N/A"]
            bear_points = [f"- {point}" for point in item["bear_evidence_points"]] or ["- N/A"]
            lines.extend(
                [
                    f"### {item['symbol']} ({item['asset_type']})",
                    f"- suggested_amount: {item['suggested_amount']}",
                    f"- final_research_label: {item['final_research_label']}",
                    f"- suggest_manual_pause_buy: {item['suggest_manual_pause_buy']}",
                    f"- suggest_force_review: {item['suggest_force_review']}",
                    f"- suggest_thesis_broken: {item['suggest_thesis_broken']}",
                    f"- confidence: {item['confidence']}",
                    f"- source_suggest_run: {item['source_suggest_run'] or 'N/A'}",
                    f"- debate_focus: {item['debate_focus']}",
                    f"- key_uncertainty: {item['key_uncertainty']}",
                    "",
                    "**Bull Case**",
                    "",
                    item["bull_case"],
                    "",
                    "**Bull Evidence Points**",
                    *bull_points,
                    "",
                    "**Bull Action Implication**",
                    "",
                    item["bull_action_implication"] or "N/A",
                    "",
                    "**Bear Case**",
                    "",
                    item["bear_case"],
                    "",
                    "**Bear Evidence Points**",
                    *bear_points,
                    "",
                    "**Bear Action Implication**",
                    "",
                    item["bear_action_implication"] or "N/A",
                    "",
                    "**Risk Summary**",
                    "",
                    item["risk_summary"],
                    "",
                    "**Recommendation Rationale**",
                    "",
                    item["recommendation_rationale"] or "N/A",
                    "",
                    "**Note**",
                    "",
                    item["note"] or "N/A",
                    "",
                ]
            )

        lines.extend(
            [
                "## Manual Risk Notice",
                "",
                "- 本批次 monthly research 仅提供研究增强建议。",
                "- suggest_* 字段不会自动写回 manual risk flags。",
                "- 本报告不会触发自动交易或自动调仓。",
                "",
            ]
        )
        return "\n".join(lines)
