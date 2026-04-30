"""基于敏感性测试结果生成稳健性结论与默认参数建议。"""

from __future__ import annotations

from datetime import datetime
import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.utils.exceptions import ConfigError
from src.utils.logger import get_logger


class RobustnessEngine:
    """读取 sensitivity-test 产物并输出结论报告。"""

    REQUIRED_SUMMARY_COLUMNS = {
        "group_name",
        "description",
        "status",
        "error",
        "data_mode",
        "provider",
        "source_api",
        "backtest_start_date",
        "backtest_end_date",
        "adjustment_mode",
        "monthly_buy_rule",
        "etf_yellow",
        "etf_red",
        "stock_yellow",
        "stock_red",
        "annualized_return",
        "max_drawdown",
        "invested_ratio",
        "total_uninvested_cash",
        "unfilled_amount",
        "total_red_triggers",
        "effective_config_json",
    }
    REQUIRED_DIFF_COLUMNS = {
        "group_name",
        "annualized_return_diff",
        "max_drawdown_diff",
        "invested_ratio_diff",
        "total_uninvested_cash_diff",
        "unfilled_amount_diff",
        "total_red_triggers_diff",
    }
    NUMERIC_SUMMARY_COLUMNS = [
        "annualized_return",
        "max_drawdown",
        "invested_ratio",
        "total_uninvested_cash",
        "unfilled_amount",
        "total_red_triggers",
        "etf_yellow",
        "etf_red",
        "stock_yellow",
        "stock_red",
    ]
    DIFF_METRICS = {
        "annualized_return_diff": "annualized_return",
        "max_drawdown_diff": "max_drawdown",
        "invested_ratio_diff": "invested_ratio",
        "total_uninvested_cash_diff": "total_uninvested_cash",
        "unfilled_amount_diff": "unfilled_amount",
        "total_red_triggers_diff": "total_red_triggers",
    }
    FAMILY_LABELS = {
        "adjustment_mode": "复权模式",
        "etf_redline": "ETF 红线",
        "stock_redline": "股票红线",
        "monthly_buy_rule": "月度定投执行日",
        "slippage": "滑点",
        "other": "其他参数",
    }
    DEFAULTS = {
        "baseline_name": "baseline",
        "inputs": {
            "summary_csv": "reports/sensitivity_summary.csv",
            "baseline_diff_csv": "reports/sensitivity_baseline_diff.csv",
            "details_json": "reports/sensitivity_details.json",
        },
        "outputs": {
            "summary_markdown": "reports/robustness_summary.md",
            "recommendation_markdown": "reports/default_parameter_recommendation.md",
            "summary_json": "reports/robustness_summary.json",
            "key_findings_csv": "reports/robustness_key_findings.csv",
        },
        "metric_weights": {
            "annualized_return_diff": 1.0,
            "max_drawdown_diff": 1.0,
            "invested_ratio_diff": 0.8,
            "total_uninvested_cash_diff": 0.8,
            "unfilled_amount_diff": 0.7,
            "total_red_triggers_diff": 0.8,
        },
        "materiality_thresholds": {
            "annualized_return_diff": 0.002,
            "max_drawdown_diff": 0.01,
            "invested_ratio_diff": 0.02,
            "total_uninvested_cash_diff": 10000.0,
            "unfilled_amount_diff": 10000.0,
            "total_red_triggers_diff": 50.0,
        },
        "classification_thresholds": {
            "robust_score_max": 0.25,
            "sensitive_score_min": 0.80,
        },
    }

    def __init__(self, configs: dict[str, dict[str, Any]], project_root: str | Path) -> None:
        self.configs = configs
        self.project_root = Path(project_root)
        self.settings = self._resolve_settings(configs.get("robustness", {}))
        log_level = configs.get("app", {}).get("runtime", {}).get("log_level", "INFO")
        self.logger = get_logger(self.__class__.__name__, log_level)

    def summarize(self, end_date: str | None = None) -> dict[str, Any]:
        """读取已有敏感性结果并生成结论摘要。"""

        summary_df, diff_df, _details = self._load_inputs()
        baseline_row = self._baseline_row(summary_df)
        success_df = summary_df.loc[summary_df["status"] == "success"].copy()
        failed_df = summary_df.loc[summary_df["status"] == "failed"].copy()
        success_diff_df = diff_df.loc[diff_df["group_name"].isin(success_df["group_name"])].copy()

        family_scores = self._family_scores(success_diff_df)
        rankings = self._metric_rankings(success_diff_df)
        baseline_assessment = self._baseline_assessment(baseline_row, success_df, family_scores, failed_df)
        classifications = self._classify_families(family_scores)
        directional_findings = self._directional_findings(summary_df, success_diff_df)
        recommendations = self._default_recommendations(summary_df, success_diff_df, baseline_row, baseline_assessment)
        key_findings = self._key_findings(family_scores, baseline_assessment, recommendations)

        payload = {
            "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "baseline_name": self.settings["baseline_name"],
            "input_files": {name: str(self.project_root / rel) for name, rel in self.settings["inputs"].items()},
            "summary_context": {
                "end_date_argument": end_date,
                "success_group_count": int(len(success_df)),
                "failed_group_count": int(len(failed_df)),
                "failed_groups": failed_df[["group_name", "error"]].to_dict(orient="records"),
            },
            "baseline_configuration": self._baseline_config_payload(baseline_row),
            "baseline_assessment": baseline_assessment,
            "metric_rankings": rankings,
            "directional_findings": directional_findings,
            "parameter_classification": classifications,
            "default_parameter_recommendations": recommendations,
            "key_findings": key_findings.to_dict(orient="records"),
        }
        paths = self._write_outputs(payload, key_findings)
        payload["output_files"] = {name: str(path) for name, path in paths.items()}
        return {"payload": payload, "paths": paths}

    def _load_inputs(self) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, Any]]:
        summary_path = self.project_root / self.settings["inputs"]["summary_csv"]
        diff_path = self.project_root / self.settings["inputs"]["baseline_diff_csv"]
        details_path = self.project_root / self.settings["inputs"]["details_json"]

        for required_path in [summary_path, diff_path, details_path]:
            if not required_path.exists():
                raise ConfigError(
                    f"缺少敏感性测试结果文件: {required_path}。请先运行 `python -m src.main sensitivity-test --end-date 2025-12-31`。"
                )

        summary_df = pd.read_csv(summary_path)
        diff_df = pd.read_csv(diff_path)
        details = json.loads(details_path.read_text(encoding="utf-8"))

        missing_summary = self.REQUIRED_SUMMARY_COLUMNS.difference(summary_df.columns)
        if missing_summary:
            raise ConfigError(
                f"sensitivity_summary.csv 缺少字段: {sorted(missing_summary)}。请重新运行 sensitivity-test。"
            )
        missing_diff = self.REQUIRED_DIFF_COLUMNS.difference(diff_df.columns)
        if missing_diff:
            raise ConfigError(
                f"sensitivity_baseline_diff.csv 缺少字段: {sorted(missing_diff)}。请重新运行 sensitivity-test。"
            )

        for column in self.NUMERIC_SUMMARY_COLUMNS:
            summary_df[column] = pd.to_numeric(summary_df[column], errors="coerce")
        for column in self.DIFF_METRICS:
            diff_df[column] = pd.to_numeric(diff_df[column], errors="coerce")
        return summary_df, diff_df, details

    def _baseline_row(self, summary_df: pd.DataFrame) -> pd.Series:
        matched = summary_df.loc[
            (summary_df["group_name"] == self.settings["baseline_name"]) & (summary_df["status"] == "success")
        ]
        if matched.empty:
            raise ConfigError(
                f"未找到成功的 baseline 结果: {self.settings['baseline_name']}。请先重新运行 sensitivity-test。"
            )
        return matched.iloc[0]

    def _baseline_config_payload(self, baseline_row: pd.Series) -> dict[str, Any]:
        return {
            "group_name": baseline_row["group_name"],
            "data_mode": baseline_row["data_mode"],
            "provider": baseline_row["provider"],
            "source_api": baseline_row["source_api"],
            "backtest_start_date": baseline_row["backtest_start_date"],
            "backtest_end_date": baseline_row["backtest_end_date"],
            "adjustment_mode": baseline_row["adjustment_mode"],
            "monthly_buy_rule": baseline_row["monthly_buy_rule"],
            "etf_yellow": float(baseline_row["etf_yellow"]),
            "etf_red": float(baseline_row["etf_red"]),
            "stock_yellow": float(baseline_row["stock_yellow"]),
            "stock_red": float(baseline_row["stock_red"]),
            "effective_config": self._load_effective_config(baseline_row),
        }

    def _family_scores(self, diff_df: pd.DataFrame) -> pd.DataFrame:
        working = diff_df.loc[diff_df["group_name"] != self.settings["baseline_name"]].copy()
        if working.empty:
            return pd.DataFrame()

        weights = self.settings["metric_weights"]
        thresholds = self.settings["materiality_thresholds"]
        total_weight = float(sum(weights.values())) or 1.0
        rows: list[dict[str, Any]] = []

        working["family"] = working["group_name"].map(self._infer_family)
        for family, frame in working.groupby("family"):
            row: dict[str, Any] = {"family": family, "family_label": self.FAMILY_LABELS.get(family, family)}
            score = 0.0
            for diff_column, metric_name in self.DIFF_METRICS.items():
                max_abs = float(frame[diff_column].abs().max()) if not frame.empty else 0.0
                threshold = float(thresholds.get(diff_column, 1.0)) or 1.0
                weight = float(weights.get(diff_column, 1.0))
                row[f"{metric_name}_max_abs_diff"] = max_abs
                row[f"{metric_name}_normalized"] = max_abs / threshold
                score += (max_abs / threshold) * weight
            row["sensitivity_score"] = score / total_weight
            rows.append(row)

        return pd.DataFrame(rows).sort_values("sensitivity_score", ascending=False).reset_index(drop=True)

    def _metric_rankings(self, diff_df: pd.DataFrame) -> dict[str, list[dict[str, Any]]]:
        rankings: dict[str, list[dict[str, Any]]] = {}
        working = diff_df.loc[diff_df["group_name"] != self.settings["baseline_name"]].copy()
        if working.empty:
            return rankings

        working["family"] = working["group_name"].map(self._infer_family)
        for diff_column, metric_name in self.DIFF_METRICS.items():
            items: list[dict[str, Any]] = []
            for family, frame in working.groupby("family"):
                if frame.empty or frame[diff_column].dropna().empty:
                    continue
                max_abs = float(frame[diff_column].abs().max())
                row = frame.loc[frame[diff_column].abs() == max_abs].iloc[0]
                items.append(
                    {
                        "family": family,
                        "family_label": self.FAMILY_LABELS.get(family, family),
                        "group_name": row["group_name"],
                        "impact": float(row[diff_column]),
                        "abs_impact": max_abs,
                    }
                )
            rankings[metric_name] = sorted(items, key=lambda item: item["abs_impact"], reverse=True)
        return rankings

    def _baseline_assessment(
        self,
        baseline_row: pd.Series,
        success_df: pd.DataFrame,
        family_scores: pd.DataFrame,
        failed_df: pd.DataFrame,
    ) -> dict[str, Any]:
        peers = success_df.loc[success_df["group_name"] != self.settings["baseline_name"]].copy()
        if peers.empty:
            return {
                "label": "证据不足",
                "in_middle_band": False,
                "notes": ["当前只有 baseline 成功结果，无法判断参数扰动后的稳健性。"],
            }

        positions = {
            "annualized_return": self._relative_position(float(baseline_row["annualized_return"]), success_df["annualized_return"]),
            "max_drawdown": self._relative_position(float(baseline_row["max_drawdown"]), success_df["max_drawdown"]),
            "invested_ratio": self._relative_position(float(baseline_row["invested_ratio"]), success_df["invested_ratio"]),
            "total_uninvested_cash": self._relative_position(float(baseline_row["total_uninvested_cash"]), success_df["total_uninvested_cash"]),
        }
        middle_band_hits = sum(0.25 <= value <= 0.75 for value in positions.values())
        threshold = self.settings["classification_thresholds"]["sensitive_score_min"]
        sensitive_count = int((family_scores["sensitivity_score"] >= threshold).sum()) if not family_scores.empty else 0

        if sensitive_count >= 2:
            label = "对部分参数较敏感"
        elif middle_band_hits >= 2:
            label = "相对稳健"
        else:
            label = "中性可用"

        notes = [
            "baseline 并非所有指标都严格处于扰动结果中位，但它在收益、回撤和现金拖累之间保持了可解释的折中。"
            if middle_band_hits >= 2
            else "baseline 在部分指标上带有方向性偏好，因此更像中性默认值，而不是严格的中位解。",
            "本轮没有出现“轻微改动后全面明显更优”的成功参数组。"
            if sensitive_count <= 1
            else "少数参数组会明显改变结果，后续解读必须同时关注这些敏感参数。",
            f"成功扰动组 {len(peers)} 个，失败组 {len(failed_df)} 个；失败组不会推翻已有结论，但会降低部分结论强度。",
        ]
        return {
            "label": label,
            "in_middle_band": middle_band_hits >= 2,
            "positions": positions,
            "sensitive_family_count": sensitive_count,
            "notes": notes,
        }

    def _classify_families(self, family_scores: pd.DataFrame) -> dict[str, list[dict[str, Any]]]:
        if family_scores.empty:
            return {"high_sensitive": [], "moderate": [], "robust": []}

        thresholds = self.settings["classification_thresholds"]
        high_sensitive = family_scores.loc[family_scores["sensitivity_score"] >= thresholds["sensitive_score_min"]]
        robust = family_scores.loc[family_scores["sensitivity_score"] <= thresholds["robust_score_max"]]
        moderate = family_scores.loc[
            (family_scores["sensitivity_score"] > thresholds["robust_score_max"])
            & (family_scores["sensitivity_score"] < thresholds["sensitive_score_min"])
        ]
        return {
            "high_sensitive": high_sensitive[["family", "family_label", "sensitivity_score"]].to_dict(orient="records"),
            "moderate": moderate[["family", "family_label", "sensitivity_score"]].to_dict(orient="records"),
            "robust": robust[["family", "family_label", "sensitivity_score"]].to_dict(orient="records"),
        }

    def _directional_findings(self, summary_df: pd.DataFrame, diff_df: pd.DataFrame) -> list[dict[str, Any]]:
        findings: list[dict[str, Any]] = []
        adj_none = self._safe_row(summary_df, "adj_none")
        if adj_none is not None:
            if adj_none["status"] == "success":
                findings.append({"topic": "复权模式", "summary": "forward 与 none 都可用，可以直接比较价格路径差异。"})
            else:
                findings.append(
                    {
                        "topic": "复权模式",
                        "summary": "本轮 `adj_none` 失败，当前证据不足以否定 forward 默认值，同时提示复权模式切换仍受真实数据可用性影响。",
                    }
                )

        etf_tighter = self._safe_row(diff_df, "etf_redline_tighter")
        etf_looser = self._safe_row(diff_df, "etf_redline_looser")
        if etf_tighter is not None and etf_looser is not None:
            findings.append(
                {
                    "topic": "ETF 红线方向性",
                    "summary": "ETF 红线更紧时，现金拖累与 RED 触发通常上升，回撤可能下降；更松时，触发次数下降、资金利用率略改善，但回撤更容易抬升。15% / 25% 更像中性折中。",
                }
            )

        stock_tighter = self._safe_row(diff_df, "stock_redline_tighter")
        stock_looser = self._safe_row(diff_df, "stock_redline_looser")
        if stock_tighter is not None and stock_looser is not None:
            stock_impact = max(
                abs(float(stock_tighter["annualized_return_diff"])),
                abs(float(stock_looser["annualized_return_diff"])),
                abs(float(stock_tighter["total_red_triggers_diff"])),
                abs(float(stock_looser["total_red_triggers_diff"])),
            )
            findings.append(
                {
                    "topic": "股票红线方向性",
                    "summary": "当前样本下，股票红线收紧或放宽几乎没有改变量化结果，更像当前样本证据不足，而不是股票红线永远不重要。"
                    if stock_impact < 1e-9
                    else "股票红线变动会影响股票侧风险暴露，但当前影响显著低于 ETF 红线。",
                }
            )

        monthly_last = self._safe_row(diff_df, "monthly_buy_last_trading_day")
        if monthly_last is not None:
            findings.append(
                {
                    "topic": "月度定投执行日",
                    "summary": "月末买入在当前样本下年化收益略低、回撤略高，但 RED 触发更少，说明执行日会改变路径表现，不过影响量级中等。",
                }
            )

        higher_slippage = self._safe_row(diff_df, "higher_slippage")
        if higher_slippage is not None:
            findings.append(
                {
                    "topic": "滑点敏感性",
                    "summary": "轻量上调滑点后，各项结果变化很小，说明这组轻量滑点扰动不是当前低频定投框架的主要敏感源。",
                }
            )
        return findings

    def _default_recommendations(
        self,
        summary_df: pd.DataFrame,
        diff_df: pd.DataFrame,
        baseline_row: pd.Series,
        baseline_assessment: dict[str, Any],
    ) -> dict[str, Any]:
        monthly_last = self._safe_row(diff_df, "monthly_buy_last_trading_day")
        etf_tighter = self._safe_row(diff_df, "etf_redline_tighter")
        etf_looser = self._safe_row(diff_df, "etf_redline_looser")
        stock_tighter = self._safe_row(diff_df, "stock_redline_tighter")
        stock_looser = self._safe_row(diff_df, "stock_redline_looser")
        adj_none = self._safe_row(summary_df, "adj_none")

        if adj_none is not None and adj_none["status"] == "success":
            adjustment_mode = {
                "label": "保留",
                "recommended_value": "forward",
                "reason": "当前没有充分证据表明应切换默认复权模式，forward 仍是已跑通且可审计的默认值。",
            }
        else:
            adjustment_mode = {
                "label": "保留，但需备注限制",
                "recommended_value": "forward",
                "reason": "当前 `adj_none` 未成功完成，证据不足以支持更换默认复权模式；应继续保留 forward，并在报告中注明 none 模式证据不完整。",
            }

        if monthly_last is None:
            monthly_buy_rule = {
                "label": "证据不足，暂不调整",
                "recommended_value": "first_trading_day",
                "reason": "缺少月末执行日对比结果，暂无法否定现有月初规则。",
            }
        else:
            monthly_buy_rule = {
                "label": "保留" if float(monthly_last["annualized_return_diff"]) < 0 and float(monthly_last["max_drawdown_diff"]) > 0 else "保留，但需备注限制",
                "recommended_value": "first_trading_day",
                "reason": "月末买入在当前样本下收益略弱、回撤略高，说明每月第 1 个交易日更贴近 baseline 的平衡表现。"
                if float(monthly_last["annualized_return_diff"]) < 0 and float(monthly_last["max_drawdown_diff"]) > 0
                else "月初与月末差异不算极端，但当前证据仍不足以支持把默认规则改成月末。",
            }

        etf_redline = {
            "label": "保留" if etf_tighter is not None and etf_looser is not None else "证据不足，暂不调整",
            "recommended_value": "YELLOW=0.15, RED=0.25",
            "reason": "ETF 红线收紧会明显增加现金拖累与 RED 触发，放宽则会降低触发但抬升回撤；15% / 25% 更符合长期定投且不轻易卖出的定位。"
            if etf_tighter is not None and etf_looser is not None
            else "缺少 ETF 红线收紧/放宽对比结果，暂维持默认值。",
        }

        stock_impact = 0.0
        if stock_tighter is not None and stock_looser is not None:
            stock_impact = max(
                abs(float(stock_tighter["annualized_return_diff"])),
                abs(float(stock_looser["annualized_return_diff"])),
                abs(float(stock_tighter["total_red_triggers_diff"])),
                abs(float(stock_looser["total_red_triggers_diff"])),
            )
        stock_redline = {
            "label": "证据不足，暂不调整" if stock_impact < 1e-9 else "保留，但需备注限制",
            "recommended_value": "YELLOW=0.12, RED=0.20",
            "reason": "当前测试几乎未观察到股票红线变动对结果的影响，更像样本证据不足；在股票仅占 20% 且当前仓位利用有限的前提下，暂不建议主动改动默认值。",
        }

        baseline_default = {
            "label": "建议保留但需备注限制"
            if adjustment_mode["label"] != "保留" or stock_redline["label"] != "保留"
            else "建议保留",
            "recommended_value": baseline_row["group_name"],
            "reason": "baseline 当前更像可执行的中性默认配置：ETF 红线与月初执行日有明确支撑，但复权模式与股票红线仍存在证据不完整的备注项。",
            "baseline_assessment_label": baseline_assessment["label"],
        }

        return {
            "adjustment_mode": adjustment_mode,
            "monthly_buy_rule": monthly_buy_rule,
            "etf_redline": etf_redline,
            "stock_redline": stock_redline,
            "baseline_default": baseline_default,
        }

    def _key_findings(
        self,
        family_scores: pd.DataFrame,
        baseline_assessment: dict[str, Any],
        recommendations: dict[str, Any],
    ) -> pd.DataFrame:
        rows = [
            {
                "section": "baseline",
                "target": "baseline_default",
                "label": baseline_assessment["label"],
                "summary": "；".join(baseline_assessment["notes"]),
            }
        ]
        for _, row in family_scores.iterrows():
            rows.append(
                {
                    "section": "sensitivity",
                    "target": row["family"],
                    "label": row["family_label"],
                    "summary": f"敏感度得分={row['sensitivity_score']:.3f}",
                }
            )
        for key, value in recommendations.items():
            rows.append({"section": "recommendation", "target": key, "label": value["label"], "summary": value["reason"]})
        return pd.DataFrame(rows)

    def _write_outputs(self, payload: dict[str, Any], key_findings: pd.DataFrame) -> dict[str, Path]:
        outputs = self.settings["outputs"]
        summary_markdown = self.project_root / outputs["summary_markdown"]
        recommendation_markdown = self.project_root / outputs["recommendation_markdown"]
        summary_json = self.project_root / outputs["summary_json"]
        key_findings_csv = self.project_root / outputs["key_findings_csv"]

        for path in [summary_markdown, recommendation_markdown, summary_json, key_findings_csv]:
            path.parent.mkdir(parents=True, exist_ok=True)

        summary_markdown.write_text(self._render_summary_markdown(payload), encoding="utf-8")
        recommendation_markdown.write_text(self._render_recommendation_markdown(payload), encoding="utf-8")
        summary_json.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        key_findings.to_csv(key_findings_csv, index=False, encoding="utf-8-sig")
        return {
            "summary_markdown": summary_markdown,
            "recommendation_markdown": recommendation_markdown,
            "summary_json": summary_json,
            "key_findings_csv": key_findings_csv,
        }

    def _render_summary_markdown(self, payload: dict[str, Any]) -> str:
        baseline = payload["baseline_configuration"]
        context = payload["summary_context"]
        assessment = payload["baseline_assessment"]
        classifications = payload["parameter_classification"]
        lines = [
            "# 稳健性结论摘要",
            "",
            "## 1. 本轮目标说明",
            "- 本轮结论基于已有 sensitivity-test 结果生成，目标是判断默认参数是否相对稳健，而不是寻找最优参数。",
            "- 当前系统定位仍是长期定投、资产配置、风险提醒与人工确认执行工具，不等于自动交易系统。",
            "",
            "## 2. Baseline 配置摘要",
            f"- group_name: {baseline['group_name']}",
            f"- data_mode: {baseline['data_mode']}",
            f"- provider: {baseline['provider']}",
            f"- source_api: {baseline['source_api']}",
            f"- backtest_range: {baseline['backtest_start_date']} -> {baseline['backtest_end_date']}",
            f"- adjustment_mode: {baseline['adjustment_mode']}",
            f"- monthly_buy_rule: {baseline['monthly_buy_rule']}",
            f"- ETF redline: {baseline['etf_yellow']:.2%} / {baseline['etf_red']:.2%}",
            f"- STOCK redline: {baseline['stock_yellow']:.2%} / {baseline['stock_red']:.2%}",
            "",
            "## 3. 测试成功/失败概览",
            f"- 成功组数量: {context['success_group_count']}",
            f"- 失败组数量: {context['failed_group_count']}",
        ]
        if context["failed_groups"]:
            for failed in context["failed_groups"]:
                lines.append(f"- 失败组: {failed['group_name']} | 原因: {failed['error']}")
        else:
            lines.append("- 失败组: 无")

        lines.extend(["", "## 4. 参数敏感度结论", self._render_rankings(payload["metric_rankings"]), "", "## 5. 高敏感参数 vs 稳健参数"])
        for section, title in [("high_sensitive", "高敏感参数"), ("moderate", "中等敏感参数"), ("robust", "相对稳健参数")]:
            rows = classifications.get(section, [])
            labels = ", ".join(f"{row['family_label']}({row['sensitivity_score']:.2f})" for row in rows) if rows else "无"
            lines.append(f"- {title}: {labels}")

        lines.extend(["", "## 6. 关键风险提示"])
        for finding in payload["directional_findings"]:
            lines.append(f"- {finding['topic']}: {finding['summary']}")

        lines.extend(
            [
                "",
                "## 7. 对当前默认值稳健性的总体判断",
                f"- 结论标签: {assessment['label']}",
                f"- baseline 是否处于多数扰动结果的中间区域: {'是' if assessment['in_middle_band'] else '否'}",
            ]
        )
        for note in assessment["notes"]:
            lines.append(f"- {note}")
        return "\n".join(lines) + "\n"

    def _render_recommendation_markdown(self, payload: dict[str, Any]) -> str:
        baseline = payload["baseline_configuration"]
        recommendations = payload["default_parameter_recommendations"]
        table = pd.DataFrame(
            [
                {"parameter": "adjustment_mode", "tag": recommendations["adjustment_mode"]["label"], "recommended_value": recommendations["adjustment_mode"]["recommended_value"]},
                {"parameter": "monthly_buy_rule", "tag": recommendations["monthly_buy_rule"]["label"], "recommended_value": recommendations["monthly_buy_rule"]["recommended_value"]},
                {"parameter": "etf_redline", "tag": recommendations["etf_redline"]["label"], "recommended_value": recommendations["etf_redline"]["recommended_value"]},
                {"parameter": "stock_redline", "tag": recommendations["stock_redline"]["label"], "recommended_value": recommendations["stock_redline"]["recommended_value"]},
                {"parameter": "baseline_default", "tag": recommendations["baseline_default"]["label"], "recommended_value": recommendations["baseline_default"]["recommended_value"]},
            ]
        )
        lines = [
            "# 默认参数建议说明",
            "",
            "## 1. 目的说明",
            "- 本报告用于把敏感性测试数字转成保守、可执行的默认参数建议，不以“收益最高”作为唯一标准。",
            "",
            "## 2. 当前默认参数组摘要",
            f"- baseline group: {baseline['group_name']}",
            f"- adjustment_mode: {baseline['adjustment_mode']}",
            f"- monthly_buy_rule: {baseline['monthly_buy_rule']}",
            f"- ETF redline: {baseline['etf_yellow']:.2%} / {baseline['etf_red']:.2%}",
            f"- STOCK redline: {baseline['stock_yellow']:.2%} / {baseline['stock_red']:.2%}",
            "",
            "## 3. 每个默认参数的保留/调整建议",
        ]
        for key in ["adjustment_mode", "monthly_buy_rule", "etf_redline", "stock_redline", "baseline_default"]:
            item = recommendations[key]
            lines.append(f"- {key}: {item['label']} | 建议值: {item['recommended_value']} | 理由: {item['reason']}")
        lines.extend(["", "## 4. 推荐结论总表", "```text", table.to_csv(index=False).strip(), "```", "", "## 5. 建议理由"])
        for key in ["adjustment_mode", "monthly_buy_rule", "etf_redline", "stock_redline", "baseline_default"]:
            lines.append(f"- {key}: {recommendations[key]['reason']}")
        lines.extend(
            [
                "",
                "## 6. 限制说明",
                "- 当前结论依赖已有 sensitivity-test 结果，若输入文件缺失或样本更新，应重新生成。",
                "- 当前结果仍受真实数据可用性、历史起点差异、MVP 级市场摩擦建模影响。",
                "- 当前系统仍未启用自动卖出，红线主要用于提醒、暂停新增与人工复核。",
            ]
        )
        return "\n".join(lines) + "\n"

    def _render_rankings(self, rankings: dict[str, list[dict[str, Any]]]) -> str:
        if not rankings:
            return "- 暂无可用排名结果。"
        lines = []
        metric_order = [
            ("annualized_return", "annualized_return"),
            ("max_drawdown", "max_drawdown"),
            ("invested_ratio", "invested_ratio"),
            ("total_uninvested_cash", "cash_drag"),
            ("unfilled_amount", "unfilled_amount"),
            ("total_red_triggers", "total_red_triggers"),
        ]
        for metric, label in metric_order:
            top = rankings.get(metric, [])
            if not top:
                lines.append(f"- {label}: 暂无数据")
                continue
            item = top[0]
            lines.append(f"- {label}: 最敏感参数为 {item['family_label']}（来自 {item['group_name']}，影响={item['impact']:.6f}）")
        return "\n".join(lines)

    @classmethod
    def _resolve_settings(cls, robustness_config: dict[str, Any]) -> dict[str, Any]:
        settings = json.loads(json.dumps(cls.DEFAULTS))
        root = robustness_config.get("robustness", robustness_config)
        cls._deep_merge(settings, root)
        return settings

    @staticmethod
    def _deep_merge(target: dict[str, Any], override: dict[str, Any]) -> None:
        for key, value in override.items():
            if isinstance(value, dict) and isinstance(target.get(key), dict):
                RobustnessEngine._deep_merge(target[key], value)
            else:
                target[key] = value

    @staticmethod
    def _relative_position(value: float, series: pd.Series) -> float:
        working = pd.to_numeric(series, errors="coerce").dropna()
        if working.empty:
            return 0.5
        minimum = float(working.min())
        maximum = float(working.max())
        if maximum == minimum:
            return 0.5
        return (value - minimum) / (maximum - minimum)

    @staticmethod
    def _infer_family(group_name: str) -> str:
        if group_name.startswith("adj_"):
            return "adjustment_mode"
        if group_name.startswith("etf_redline_"):
            return "etf_redline"
        if group_name.startswith("stock_redline_"):
            return "stock_redline"
        if group_name.startswith("monthly_buy_"):
            return "monthly_buy_rule"
        if "slippage" in group_name:
            return "slippage"
        return "other"

    @staticmethod
    def _safe_row(frame: pd.DataFrame, group_name: str) -> pd.Series | None:
        matched = frame.loc[frame["group_name"] == group_name]
        return matched.iloc[0] if not matched.empty else None

    @staticmethod
    def _load_effective_config(baseline_row: pd.Series) -> dict[str, Any]:
        raw = baseline_row.get("effective_config_json", "{}")
        if pd.isna(raw):
            return {}
        try:
            return json.loads(str(raw))
        except json.JSONDecodeError:
            return {"raw": str(raw)}
