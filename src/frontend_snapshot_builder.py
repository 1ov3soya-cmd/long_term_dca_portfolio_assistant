"""前端静态快照构建器。

该模块把现有 reports/config 归档转换为 frontend/public/data 下的静态 JSON。
前端生产构建后可直接读取 /data/*.json，不再依赖 Vite dev server 的
/archive-data 中间件。
"""

from __future__ import annotations

import csv
from datetime import datetime
from io import StringIO
import json
from pathlib import Path
from typing import Any

from src.utils.logger import get_logger


SNAPSHOT_VERSION = "1.0"
SNAPSHOT_FILES = {
    "site_manifest": "site_manifest.json",
    "archive_compat": "archive_compat_snapshot.json",
    "dashboard": "dashboard_snapshot.json",
    "monthly_research": "monthly_research_snapshot.json",
    "manual_risk": "manual_risk_snapshot.json",
    "research_vs_manual_risk": "research_vs_manual_risk_snapshot.json",
    "run_compare": "run_compare_snapshot.json",
    "research": "research_snapshot.json",
}


class FrontendSnapshotBuilder:
    """构建可静态部署的前端数据快照。"""

    def __init__(self, project_root: Path, configs: dict[str, dict[str, Any]]) -> None:
        """初始化构建器。

        Args:
            project_root: 项目根目录。
            configs: 当前生效配置，用于写入 site_manifest 和降级摘要。
        """

        self.project_root = project_root
        self.configs = configs
        self.data_dir = project_root / "frontend" / "public" / "data"
        self.logger = get_logger("frontend_snapshot_builder")

    def build(self, end_date: str | None = None) -> dict[str, Any]:
        """生成所有前端静态快照。

        即使部分归档缺失，也会写出空态 JSON，并在 warnings 中说明。
        """

        generated_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        warnings: list[str] = []
        self.data_dir.mkdir(parents=True, exist_ok=True)

        compat = self._build_archive_compat(warnings)
        archive_compat_path = self._write_snapshot(SNAPSHOT_FILES["archive_compat"], compat)

        dashboard = self._build_dashboard_snapshot(compat, generated_at, warnings)
        monthly_research = self._build_monthly_research_snapshot(compat, generated_at, warnings)
        manual_risk = self._build_manual_risk_snapshot(compat, generated_at, warnings)
        run_compare = self._build_run_compare_snapshot(compat, generated_at, warnings)
        research = self._build_research_snapshot(compat, generated_at, warnings)
        research_vs_manual_risk = self._build_research_vs_manual_risk_snapshot(
            monthly_research=monthly_research,
            manual_risk=manual_risk,
            generated_at=generated_at,
            warnings=warnings,
        )

        paths = {
            "archive_compat": archive_compat_path,
            "dashboard": self._write_snapshot(SNAPSHOT_FILES["dashboard"], dashboard),
            "monthly_research": self._write_snapshot(SNAPSHOT_FILES["monthly_research"], monthly_research),
            "manual_risk": self._write_snapshot(SNAPSHOT_FILES["manual_risk"], manual_risk),
            "research_vs_manual_risk": self._write_snapshot(
                SNAPSHOT_FILES["research_vs_manual_risk"],
                research_vs_manual_risk,
            ),
            "run_compare": self._write_snapshot(SNAPSHOT_FILES["run_compare"], run_compare),
            "research": self._write_snapshot(SNAPSHOT_FILES["research"], research),
        }

        manifest = {
            "generated_at": generated_at,
            "project_name": "long_term_dca_portfolio_assistant",
            "data_mode": self._get_config_value(["app", "runtime", "data_provider"], "unknown"),
            "end_date": end_date or self._get_config_value(["backtest", "backtest", "end_date"], ""),
            "snapshot_version": SNAPSHOT_VERSION,
            "available_snapshots": SNAPSHOT_FILES,
            "warnings": warnings,
            "static_site_note": "该快照仅用于静态只读展示，不会自动下单、自动卖出或修改 manual risk flags。",
        }
        paths["site_manifest"] = self._write_snapshot(SNAPSHOT_FILES["site_manifest"], manifest)

        self.logger.info("前端静态快照已生成: %s", self.data_dir)
        return {
            "generated_at": generated_at,
            "data_dir": str(self.data_dir),
            "paths": {key: str(path) for key, path in paths.items()},
            "warnings": warnings,
        }

    def _build_archive_compat(self, warnings: list[str]) -> dict[str, Any]:
        """生成现有 adapter 可复用的虚拟归档映射。"""

        json_files: dict[str, Any] = {}
        text_files: dict[str, str] = {}
        roots = [self.project_root / "reports", self.project_root / "config"]
        text_suffixes = {".md", ".csv", ".txt"}

        for root in roots:
            if not root.exists():
                warnings.append(f"归档目录不存在: {self._rel(root)}")
                continue
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                relative = self._rel(path)
                suffix = path.suffix.lower()
                if suffix == ".json":
                    payload = self._read_json_file(path, warnings)
                    if payload is not None:
                        json_files[relative] = payload
                elif suffix in text_suffixes:
                    text = self._read_text_file(path, warnings)
                    if text is not None:
                        text_files[relative] = text

        return {
            "snapshot_version": SNAPSHOT_VERSION,
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "json_files": json_files,
            "text_files": text_files,
            "warnings": warnings,
        }

    def _build_dashboard_snapshot(self, compat: dict[str, Any], generated_at: str, warnings: list[str]) -> dict[str, Any]:
        """构建 Dashboard 专用快照摘要。"""

        json_files = compat.get("json_files", {})
        text_files = compat.get("text_files", {})
        dashboard_data = self._build_dashboard_data(json_files, text_files)
        return {
            "generated_at": generated_at,
            "snapshot_type": "dashboard",
            "dashboard_data": dashboard_data,
            "latest_runs_index": json_files.get("reports/runs/latest_index.json"),
            "latest_compare_index": json_files.get("reports/run_compare/latest_compare_index.json"),
            "monthly_research_index": json_files.get("reports/agent_research/monthly/latest_monthly_research_index.json"),
            "research_index": json_files.get("reports/agent_research/research_index.json"),
            "robustness_summary": json_files.get("reports/robustness_summary.json"),
            "manual_acceptance_report": json_files.get("reports/manual/manual_logic_risk_acceptance_report.json"),
            "warnings": warnings,
        }

    def _build_dashboard_data(self, json_files: dict[str, Any], text_files: dict[str, str]) -> dict[str, Any]:
        """构建 Dashboard 可直接消费的页面级数据。"""

        latest_index = json_files.get("reports/runs/latest_index.json") or {}
        end_date = str(self._get_config_value(["backtest", "backtest", "end_date"], ""))
        date_suffix = end_date.replace("-", "")
        suggestion_csv = text_files.get(f"reports/monthly/monthly_suggestion_{date_suffix}.csv", "")
        if not suggestion_csv:
            monthly_candidates = sorted(
                key for key in text_files if key.startswith("reports/monthly/monthly_suggestion_") and key.endswith(".csv")
            )
            suggestion_csv = text_files.get(monthly_candidates[-1], "") if monthly_candidates else ""
        suggestion_rows = self._parse_csv_rows(suggestion_csv)

        manual_validation = json_files.get("reports/manual/manual_risk_flags_validation.json") or {}
        manual_flags = manual_validation.get("flags") if isinstance(manual_validation.get("flags"), list) else []
        manual_paused = [row.get("symbol", "") for row in manual_flags if row.get("manual_pause_buy")]
        manual_review = [row.get("symbol", "") for row in manual_flags if row.get("manual_force_review")]
        manual_broken = [row.get("symbol", "") for row in manual_flags if row.get("thesis_broken")]

        monthly_budget = float(self._get_config_value(["portfolio", "portfolio", "monthly_budget"], 0) or 0)
        etf_weight = float(self._get_config_value(["portfolio", "asset_allocation", "etf_total_weight"], 0.8) or 0)
        stock_weight = float(self._get_config_value(["portfolio", "asset_allocation", "stock_total_weight"], 0.2) or 0)
        suggested_targets = [self._map_suggested_target(row) for row in suggestion_rows]
        buy_targets = sum(1 for row in suggested_targets if float(row.get("baseSuggestedAmount", 0) or 0) > 0)

        compare_snapshot = self._build_compare_card_snapshot(json_files)
        robustness = json_files.get("reports/robustness_summary.json") or {}
        backtest_metrics = self._parse_csv_rows(text_files.get("reports/backtest/metrics.csv", ""))
        backtest_row = backtest_metrics[0] if backtest_metrics else {}

        return {
            "overview": {
                "latestSuggest": self._latest_finished_at(latest_index, "suggest") or self._latest_monthly_report_time(text_files) or "N/A",
                "latestBacktest": self._latest_finished_at(latest_index, "backtest") or "N/A",
                "latestRobustness": self._latest_finished_at(latest_index, "summarize-robustness") or "N/A",
                "latestCompare": self._latest_finished_at(latest_index, "compare-runs") or "N/A",
                "mode": "real",
                "adjMode": self._get_config_value(["app", "efinance", "adjustment_mode"], "N/A"),
                "riskFileStatus": "active" if manual_validation else "unknown",
            },
            "configSummary": {
                "allocation": f"ETF {round(etf_weight * 100)}% / Stock {round(stock_weight * 100)}%",
                "monthlyRule": self._get_config_value(["app", "schedule", "monthly_invest_day_rule"], "first_trading_day"),
                "etfRiskLevel": self._risk_level_text("etf"),
                "stockRiskLevel": self._risk_level_text("stock"),
                "manualRiskEnabled": bool(self._get_config_value(["risk", "risk", "use_logic_redline"], True)),
                "env": f"Local Archive / {self._get_config_value(['app', 'runtime', 'data_provider'], 'N/A')}",
            },
            "suggestSummary": {
                "budgetTotal": monthly_budget,
                "budgetEtf": monthly_budget * etf_weight,
                "budgetStock": monthly_budget * stock_weight,
                "buyTargets": buy_targets,
                "pausedTargets": sum(1 for row in suggested_targets if row.get("pauseBuy")),
                "forceReviewTargets": sum(1 for row in suggested_targets if row.get("forceReview")),
                "thesisBrokenTargets": sum(1 for row in suggested_targets if row.get("thesisBroken")),
            },
            "suggestedTargets": suggested_targets,
            "backtestSummary": {
                "cumulativeReturn": self._number_or_na(backtest_row.get("cumulative_return") or backtest_row.get("total_return")),
                "annualizedReturn": self._number_or_na(backtest_row.get("annualized_return")),
                "maxDrawdown": self._number_or_na(backtest_row.get("max_drawdown")),
                "investedRatio": self._number_or_na(backtest_row.get("invested_ratio")),
                "unfilledAmount": self._number_or_zero(backtest_row.get("unfilled_amount") or backtest_row.get("total_uninvested_cash")),
                "yellowTriggers": self._number_or_zero(backtest_row.get("total_yellow_triggers")),
                "redTriggers": self._number_or_zero(backtest_row.get("total_red_triggers")),
            },
            "riskLights": {
                "GREEN": max(len(manual_flags) - len(manual_paused) - len(manual_review) - len(manual_broken), 0),
                "YELLOW": 0,
                "RED": 0,
                "MANUAL_PAUSE": len(manual_paused),
                "FORCE_REVIEW": len(manual_review),
                "THESIS_BROKEN": len(manual_broken),
            },
            "manualRisk": {
                "paused": manual_paused,
                "forceReview": manual_review,
                "thesisBroken": manual_broken,
                "effectiveFrom": self._first_effective_from(manual_flags),
                "notePreview": self._first_note(manual_flags),
            },
            "robustness": {
                "isBaselineRobust": bool(robustness.get("baseline_assessment")),
                "keepDefaultParams": True,
                "mostSensitive": self._first_nested_label(robustness, ["parameter_classification", "high_sensitive"]),
                "mostRobust": self._first_nested_label(robustness, ["parameter_classification", "robust"]),
                "label": self._get_nested(robustness, ["baseline_assessment", "label"], "N/A"),
            },
            "compare": compare_snapshot,
        }

    def _build_monthly_research_snapshot(
        self,
        compat: dict[str, Any],
        generated_at: str,
        warnings: list[str],
    ) -> dict[str, Any]:
        """构建月度研究辩论快照。"""

        json_files = compat.get("json_files", {})
        text_files = compat.get("text_files", {})
        index = json_files.get("reports/agent_research/monthly/latest_monthly_research_index.json") or {}
        latest = self._latest_from_index(index)
        refs = self._monthly_research_refs(latest)

        summary = json_files.get(refs.get("summary", ""), {})
        raw_items = json_files.get(refs.get("items", ""), [])
        items = self._extract_items(raw_items)
        manifest = json_files.get(refs.get("manifest", ""), {})
        report_preview = self._preview_text(text_files.get(refs.get("report", ""), ""))

        if not latest:
            warnings.append("未找到 latest_monthly_research_index.json 或最新 monthly research 批次。")

        return {
            "generated_at": generated_at,
            "snapshot_type": "monthly_research",
            "index": index,
            "batch_meta": manifest,
            "summary": summary,
            "debate_items": items,
            "report_preview": report_preview,
            "source_files": refs,
            "warnings": warnings,
        }

    def _build_manual_risk_snapshot(self, compat: dict[str, Any], generated_at: str, warnings: list[str]) -> dict[str, Any]:
        """构建人工红线静态快照。"""

        json_files = compat.get("json_files", {})
        text_files = compat.get("text_files", {})
        report = json_files.get("reports/manual/manual_logic_risk_acceptance_report.json")
        validation = json_files.get("reports/manual/manual_risk_flags_validation.json")

        if report is None and validation is None:
            warnings.append("未找到 manual risk acceptance 或 validation JSON。")

        return {
            "generated_at": generated_at,
            "snapshot_type": "manual_risk",
            "source_type": "acceptance" if report is not None else ("validation" if validation is not None else "missing"),
            "acceptance_report": report,
            "validation_report": validation,
            "acceptance_preview_csv": text_files.get("reports/manual/manual_logic_risk_acceptance_preview.csv", ""),
            "acceptance_checklist_preview": self._preview_text(
                text_files.get("reports/manual_logic_risk_acceptance_checklist.md", "")
                or text_files.get("reports/manual/manual_logic_risk_acceptance_report.md", "")
            ),
            "validation_preview": self._preview_text(text_files.get("reports/manual/manual_risk_flags_validation.md", "")),
            "warnings": warnings,
        }

    def _build_run_compare_snapshot(self, compat: dict[str, Any], generated_at: str, warnings: list[str]) -> dict[str, Any]:
        """构建运行对比静态快照。"""

        json_files = compat.get("json_files", {})
        text_files = compat.get("text_files", {})
        index = json_files.get("reports/run_compare/latest_compare_index.json") or {}
        latest = self._latest_from_index(index)
        compare_id = str(latest.get("compare_id") or latest.get("id") or latest.get("latest_compare_id") or "")
        base = f"reports/run_compare/{compare_id}" if compare_id else ""

        if not compare_id:
            warnings.append("未找到 latest compare id。")

        return {
            "generated_at": generated_at,
            "snapshot_type": "run_compare",
            "index": index,
            "compare_id": compare_id,
            "manifest": json_files.get(f"{base}/compare_manifest.json") if base else None,
            "summary": json_files.get(f"{base}/compare_summary.json") if base else None,
            "config_diff": json_files.get(f"{base}/config_diff.json") if base else None,
            "summary_diff_csv": text_files.get(f"{base}/summary_diff.csv", "") if base else "",
            "report_preview": self._preview_text(text_files.get(f"{base}/compare_report.md", "")) if base else "",
            "warnings": warnings,
        }

    def _build_research_snapshot(self, compat: dict[str, Any], generated_at: str, warnings: list[str]) -> dict[str, Any]:
        """构建单标的研究静态快照。"""

        json_files = compat.get("json_files", {})
        text_files = compat.get("text_files", {})
        index = json_files.get("reports/agent_research/research_index.json") or {}
        entries = index.get("items") or index.get("research_items") or index.get("entries") or []
        items: list[dict[str, Any]] = []

        if not entries:
            warnings.append("未找到 research_index 中的单标的研究条目。")

        for entry in entries if isinstance(entries, list) else []:
            json_path = self._entry_path(entry, ["json_path", "json_relative_path", "research_json", "path"])
            md_path = self._entry_path(entry, ["markdown_path", "memo_path", "memo_relative_path", "markdown"])
            detail = json_files.get(json_path, {}) if json_path else {}
            items.append(
                {
                    "index_entry": entry,
                    "detail": detail,
                    "memo_preview": self._preview_text(text_files.get(md_path, "")) if md_path else "",
                    "source_files": {"json": json_path, "markdown": md_path},
                }
            )

        return {
            "generated_at": generated_at,
            "snapshot_type": "research",
            "index": index,
            "items": items,
            "warnings": warnings,
        }

    def _build_research_vs_manual_risk_snapshot(
        self,
        monthly_research: dict[str, Any],
        manual_risk: dict[str, Any],
        generated_at: str,
        warnings: list[str],
    ) -> dict[str, Any]:
        """构建研究建议与人工红线的轻量对照快照。"""

        manual_items = self._extract_manual_items(manual_risk)
        manual_by_symbol = {str(item.get("symbol", "")): item for item in manual_items if item.get("symbol")}
        items: list[dict[str, Any]] = []

        for item in monthly_research.get("debate_items", []):
            symbol = str(item.get("symbol", ""))
            manual = manual_by_symbol.get(symbol, {})
            comparison = self._compare_research_manual(item, manual)
            items.append({**comparison, "symbol": symbol, "research": item, "manual": manual})

        high_priority = [item for item in items if item.get("priority_level") == "high"]
        return {
            "generated_at": generated_at,
            "snapshot_type": "research_vs_manual_risk",
            "summary": {
                "matched_count": sum(1 for item in items if item.get("match_status") == "matched"),
                "unmatched_count": sum(1 for item in items if item.get("match_status") == "mismatch"),
                "high_priority_count": len(high_priority),
                "total_items": len(items),
            },
            "attention_symbols": [item.get("symbol") for item in high_priority[:5]],
            "items": items,
            "warnings": warnings,
            "read_only_notice": "研究建议仅供人工复核，不会自动写回 manual risk flags。",
        }

    def _compare_research_manual(self, research: dict[str, Any], manual: dict[str, Any]) -> dict[str, Any]:
        """比较单条研究建议与人工红线状态。"""

        checks = [
            ("pauseBuy", bool(research.get("suggest_manual_pause_buy")), bool(manual.get("manual_pause_buy"))),
            ("forceReview", bool(research.get("suggest_force_review")), bool(manual.get("manual_force_review"))),
            ("thesisBroken", bool(research.get("suggest_thesis_broken")), bool(manual.get("thesis_broken"))),
        ]
        mismatch_fields = [name for name, suggested, current in checks if suggested and not current]
        if not mismatch_fields:
            return {
                "match_status": "matched",
                "mismatch_fields": [],
                "priority_level": "low",
                "attention_reason": "Already covered by current manual risk state.",
            }
        if "thesisBroken" in mismatch_fields or "forceReview" in mismatch_fields:
            priority = "high"
        elif "pauseBuy" in mismatch_fields:
            priority = "medium"
        else:
            priority = "low"
        return {
            "match_status": "mismatch",
            "mismatch_fields": mismatch_fields,
            "priority_level": priority,
            "attention_reason": "Research suggestion is not yet reflected in manual risk.",
        }

    def _parse_csv_rows(self, csv_text: str) -> list[dict[str, str]]:
        """解析 CSV 文本为字典列表。"""

        if not csv_text:
            return []
        reader = csv.DictReader(StringIO(csv_text))
        return [dict(row) for row in reader]

    def _map_suggested_target(self, row: dict[str, str]) -> dict[str, Any]:
        """把月度建议 CSV 行映射为 Dashboard 明细行。"""

        pause_buy = self._bool_value(row.get("pause_buy")) or self._bool_value(row.get("final_pause_buy")) or self._bool_value(row.get("manual_pause_buy"))
        force_review = self._bool_value(row.get("manual_review")) or self._bool_value(row.get("final_force_review")) or self._bool_value(row.get("manual_force_review"))
        thesis_broken = self._bool_value(row.get("thesis_broken"))
        return {
            "symbol": row.get("symbol") or "N/A",
            "assetType": (row.get("asset_type") or "").upper() or "N/A",
            "baseSuggestedAmount": self._number_or_zero(row.get("recommended_amount")),
            "action": row.get("final_human_readable_action") or ("Pause Buy" if pause_buy else "Normal"),
            "riskStatus": row.get("status") or "N/A",
            "note": row.get("logic_note") or row.get("reasons") or "",
            "pauseBuy": pause_buy,
            "forceReview": force_review,
            "thesisBroken": thesis_broken,
        }

    def _bool_value(self, value: Any) -> bool:
        """兼容布尔、数字和字符串布尔值。"""

        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return value.strip().lower() in {"true", "1", "yes", "y"}
        return False

    def _number_or_zero(self, value: Any) -> float:
        """将数值转换为 float；真实缺失时返回 0。"""

        if value is None or value == "":
            return 0.0
        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    def _number_or_na(self, value: Any) -> float | str:
        """数值存在时保留数值，真实缺失时返回 N/A。"""

        if value is None or value == "":
            return "N/A"
        try:
            return float(value)
        except (TypeError, ValueError):
            return "N/A"

    def _latest_finished_at(self, latest_index: dict[str, Any], command: str) -> str:
        """从 latest_index 中读取某个命令的完成时间。"""

        value = latest_index.get(command) if isinstance(latest_index, dict) else None
        return str(value.get("finished_at", "")) if isinstance(value, dict) else ""

    def _latest_monthly_report_time(self, text_files: dict[str, str]) -> str:
        """月度报告没有对应 run 时，使用最新月度报告文件名作为弱时间线索。"""

        candidates = sorted(
            key for key in text_files if key.startswith("reports/monthly/monthly_report_") and key.endswith(".md")
        )
        if not candidates:
            return ""
        return candidates[-1].replace("reports/monthly/monthly_report_", "").replace(".md", "")

    def _risk_level_text(self, asset_type: str) -> str:
        """读取红线阈值并格式化。"""

        if asset_type == "etf":
            yellow = self._get_config_value(["risk", "etf", "yellow_drawdown_from_high"], None)
            red = self._get_config_value(["risk", "etf", "red_drawdown_from_high"], None)
        else:
            yellow = self._get_config_value(["risk", "stock", "yellow_drawdown_from_cost"], None)
            red = self._get_config_value(["risk", "stock", "red_drawdown_from_cost"], None)
        if yellow is None or red is None:
            return "N/A"
        return f"Y {round(float(yellow) * 100)}% / R {round(float(red) * 100)}%"

    def _first_effective_from(self, rows: list[dict[str, Any]]) -> str:
        """读取第一条有效起始日。"""

        values = sorted(str(row.get("effective_from", "")) for row in rows if row.get("effective_from"))
        return values[0] if values else "N/A"

    def _first_note(self, rows: list[dict[str, Any]]) -> str:
        """读取第一条人工红线备注。"""

        for row in rows:
            note = str(row.get("note", "")).strip()
            if note:
                return note
        return "暂无人工红线备注"

    def _build_compare_card_snapshot(self, json_files: dict[str, Any]) -> dict[str, Any]:
        """构建 Dashboard compare 卡片所需的最小数据。"""

        index = json_files.get("reports/run_compare/latest_compare_index.json") or {}
        latest = self._latest_from_index(index)
        compare_id = str(latest.get("compare_id") or latest.get("id") or latest.get("latest_compare_id") or "")
        manifest = json_files.get(f"reports/run_compare/{compare_id}/compare_manifest.json") if compare_id else {}
        summary = json_files.get(f"reports/run_compare/{compare_id}/compare_summary.json") if compare_id else {}
        top_config = (summary or {}).get("top_config_changes", [{}])
        top_summary = (summary or {}).get("top_summary_changes", [{}])
        top_config_item = top_config[0] if top_config else {}
        top_summary_item = top_summary[0] if top_summary else {}
        return {
            "runA": self._get_nested(manifest or {}, ["run_a", "run_ref"], "N/A"),
            "runB": self._get_nested(manifest or {}, ["run_b", "run_ref"], "N/A"),
            "comparableLevel": str(
                self._get_nested(summary or {}, ["comparability_assessment", "level"], "")
                or (manifest or {}).get("comparable_level")
                or "N/A"
            ).upper(),
            "topConfigChange": f"{top_config_item.get('path') or top_config_item.get('key') or 'config'} -> {top_config_item.get('change_type') or 'changed'}"
            if top_config_item
            else "暂无显著配置差异",
            "topSummaryChange": f"{top_summary_item.get('key') or 'summary'} -> {top_summary_item.get('direction') or top_summary_item.get('change_type') or 'changed'}"
            if top_summary_item
            else "暂无显著结果差异",
        }

    def _get_nested(self, payload: dict[str, Any], keys: list[str], default: Any = "") -> Any:
        """安全读取嵌套字典。"""

        value: Any = payload
        for key in keys:
            if not isinstance(value, dict):
                return default
            value = value.get(key)
        return default if value is None else value

    def _first_nested_label(self, payload: dict[str, Any], keys: list[str]) -> str:
        """读取 robustness 分类中的第一条标签。"""

        value = self._get_nested(payload, keys, [])
        if isinstance(value, list) and value:
            first = value[0]
            if isinstance(first, dict):
                return str(first.get("family_label") or first.get("label") or "N/A")
        return "N/A"

    def _extract_manual_items(self, manual_risk: dict[str, Any]) -> list[dict[str, Any]]:
        """从不同 manual risk 快照结构中提取条目。"""

        report = manual_risk.get("acceptance_report") or {}
        validation = manual_risk.get("validation_report") or {}
        candidates = [
            report.get("items"),
            report.get("records"),
            report.get("flags"),
            validation.get("flags"),
            validation.get("items"),
        ]
        for candidate in candidates:
            if isinstance(candidate, list):
                return candidate
        return []

    def _extract_items(self, payload: Any) -> list[dict[str, Any]]:
        """兼容 list 或 {"items": [...]} 结构。"""

        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            for key in ("items", "debate_items", "records", "rows"):
                value = payload.get(key)
                if isinstance(value, list):
                    return [item for item in value if isinstance(item, dict)]
        return []

    def _monthly_research_refs(self, latest: dict[str, Any]) -> dict[str, str]:
        """从 latest monthly research 索引中解析引用路径。"""

        return {
            "manifest": self._normalize_archive_key(
                latest.get("manifest_relative_path") or latest.get("manifest_path") or latest.get("batch_manifest") or ""
            ),
            "summary": self._normalize_archive_key(
                latest.get("summary_relative_path") or latest.get("summary_path") or latest.get("monthly_research_summary") or ""
            ),
            "items": self._normalize_archive_key(
                latest.get("items_relative_path") or latest.get("items_path") or latest.get("debate_items") or ""
            ),
            "report": self._normalize_archive_key(
                latest.get("report_relative_path") or latest.get("report_path") or latest.get("monthly_research_report") or ""
            ),
        }

    def _latest_from_index(self, index: Any) -> dict[str, Any]:
        """兼容多种 latest index 结构。"""

        if not isinstance(index, dict):
            return {}
        for key in ("latest", "latest_compare", "latest_monthly_research", "current"):
            value = index.get(key)
            if isinstance(value, dict):
                return value
        items = index.get("items") or index.get("entries") or index.get("history")
        if isinstance(items, list) and items:
            return items[0] if isinstance(items[0], dict) else {}
        return index

    def _entry_path(self, entry: Any, keys: list[str]) -> str:
        """从 research index 条目中读取文件路径。"""

        if not isinstance(entry, dict):
            return ""
        for key in keys:
            value = entry.get(key)
            if value:
                return self._normalize_archive_key(value)
        return ""

    def _get_config_value(self, keys: list[str], default: Any = "") -> Any:
        """安全读取嵌套配置。"""

        value: Any = self.configs
        for key in keys:
            if not isinstance(value, dict):
                return default
            value = value.get(key)
        return default if value is None else value

    def _read_json_file(self, path: Path, warnings: list[str]) -> Any | None:
        """读取 JSON 文件，失败时记录 warning 而不中断。"""

        try:
            return json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"读取 JSON 失败: {self._rel(path)}: {exc}")
            return None

    def _read_text_file(self, path: Path, warnings: list[str]) -> str | None:
        """读取文本文件，失败时记录 warning 而不中断。"""

        try:
            return path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError:
            try:
                return path.read_text(encoding="gb18030")
            except Exception as exc:  # noqa: BLE001
                warnings.append(f"读取文本失败: {self._rel(path)}: {exc}")
                return None
        except Exception as exc:  # noqa: BLE001
            warnings.append(f"读取文本失败: {self._rel(path)}: {exc}")
            return None

    def _write_snapshot(self, file_name: str, payload: dict[str, Any]) -> Path:
        """以 UTF-8 写出单个 snapshot JSON。"""

        path = self.data_dir / file_name
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        return path

    def _preview_text(self, text: str, limit: int = 4000) -> str:
        """生成 Markdown/CSV 预览文本，避免 snapshot 页面展示过长。"""

        if not text:
            return ""
        stripped = text.strip()
        return stripped[:limit] + ("\n..." if len(stripped) > limit else "")

    def _normalize_archive_key(self, value: Any) -> str:
        """把绝对路径或相对路径统一成 reports/... / config/... 键。"""

        raw = str(value or "").replace("\\", "/").strip()
        if not raw:
            return ""
        marker_candidates = ["/reports/", "/config/"]
        for marker in marker_candidates:
            if marker in raw:
                return marker.strip("/") + "/" + raw.split(marker, 1)[1]
        if raw.startswith("reports/") or raw.startswith("config/"):
            return raw
        if raw.startswith("/"):
            return raw.lstrip("/")
        return raw

    def _rel(self, path: Path) -> str:
        """返回项目相对路径。"""

        try:
            return path.resolve().relative_to(self.project_root.resolve()).as_posix()
        except ValueError:
            return path.as_posix()
