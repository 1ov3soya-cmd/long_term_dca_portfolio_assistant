"""人工逻辑红线验收辅助输出。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from src.manual_risk_manager import ManualRiskFlagManager
from src.risk_decision import RiskDecisionMerger
from src.utils.logger import get_logger
from src.utils.schemas import RiskSignal


class ManualRiskAcceptanceHelper:
    """生成验收预览、验收报告与验收清单。"""

    def __init__(self, configs: dict[str, dict[str, Any]], project_root: str | Path) -> None:
        self.configs = configs
        self.project_root = Path(project_root)
        self.logger = get_logger(self.__class__.__name__, configs["app"]["runtime"]["log_level"])

    def build_preview_table(
        self,
        target_table: pd.DataFrame,
        manual_risk_file: str | Path,
        end_date: str,
    ) -> pd.DataFrame:
        """构建人工逻辑红线的验收预览表。"""

        manager = ManualRiskFlagManager(
            self._resolve_path(manual_risk_file),
            self._resolve_path(self.configs["universe"]["manual_flags"].get("thesis_flag_file")),
        )
        merger = RiskDecisionMerger(self.configs["risk"])
        start_ts = pd.Timestamp(self.configs["backtest"]["backtest"]["start_date"])
        end_ts = pd.Timestamp(end_date)
        allowed_symbols = set(target_table["symbol"].astype(str).tolist())

        rows: list[dict[str, Any]] = []
        for symbol, flag in manager.load_all_flags().items():
            preview_signal = merger.merge(
                RiskSignal(
                    symbol=symbol,
                    asset_type=flag.asset_type,
                    status="GREEN",
                    reasons=["验收预览基线：价格侧按 GREEN 处理"],
                    pause_buy=False,
                    manual_review=False,
                ),
                flag,
            )
            effective_ts = self._safe_timestamp(flag.effective_from)
            rows.append(
                {
                    "symbol": symbol,
                    "asset_type": flag.asset_type,
                    "effective_from": flag.effective_from,
                    "active_on_end_date": bool(flag.is_active(end_ts)) if effective_ts is not None else False,
                    "effective_window_state": self._window_state(effective_ts, start_ts, end_ts),
                    "manual_pause_buy": flag.manual_pause_buy,
                    "manual_force_review": flag.manual_force_review,
                    "thesis_broken": flag.thesis_broken,
                    "final_pause_buy": preview_signal.final_pause_buy,
                    "final_force_review": preview_signal.final_force_review,
                    "final_priority_level": preview_signal.final_priority_level,
                    "final_reason_codes": ",".join(preview_signal.final_reason_codes),
                    "final_human_readable_action": preview_signal.final_human_readable_action,
                    "expected_behavior": self._expected_behavior(flag),
                    "note": flag.note,
                    "updated_at": flag.updated_at,
                    "updated_by": flag.updated_by,
                    "in_current_universe": symbol in allowed_symbols,
                }
            )

        frame = pd.DataFrame(rows)
        if frame.empty:
            return pd.DataFrame(
                columns=[
                    "symbol",
                    "asset_type",
                    "effective_from",
                    "active_on_end_date",
                    "effective_window_state",
                    "manual_pause_buy",
                    "manual_force_review",
                    "thesis_broken",
                    "final_pause_buy",
                    "final_force_review",
                    "final_priority_level",
                    "final_reason_codes",
                    "final_human_readable_action",
                    "expected_behavior",
                    "note",
                    "updated_at",
                    "updated_by",
                    "in_current_universe",
                ]
            )
        return frame.sort_values(["final_priority_level", "symbol"]).reset_index(drop=True)

    def write_acceptance_artifacts(
        self,
        validation_result: dict[str, Any],
        target_table: pd.DataFrame,
        manual_risk_file: str | Path,
        end_date: str,
    ) -> dict[str, Path]:
        """落盘验收报告、预览明细与验收清单。"""

        preview = self.build_preview_table(target_table, manual_risk_file, end_date)
        manual_file = str(manual_risk_file)
        reports_dir = self.project_root / "reports"
        manual_dir = reports_dir / "manual"
        manual_dir.mkdir(parents=True, exist_ok=True)

        csv_path = manual_dir / "manual_logic_risk_acceptance_preview.csv"
        json_path = manual_dir / "manual_logic_risk_acceptance_report.json"
        report_path = manual_dir / "manual_logic_risk_acceptance_report.md"
        checklist_path = reports_dir / "manual_logic_risk_acceptance_checklist.md"

        preview.to_csv(csv_path, index=False, encoding="utf-8-sig")
        json_payload = {
            "manual_risk_file": manual_file,
            "end_date": end_date,
            "backtest_start_date": self.configs["backtest"]["backtest"]["start_date"],
            "validation_valid": validation_result["valid"],
            "validation_issues": validation_result["issues"].to_dict(orient="records"),
            "preview": preview.to_dict(orient="records"),
        }
        json_path.write_text(json.dumps(json_payload, ensure_ascii=False, indent=2), encoding="utf-8")
        report_path.write_text(
            self._render_acceptance_report(
                preview=preview,
                validation_result=validation_result,
                manual_risk_file=manual_file,
                end_date=end_date,
            ),
            encoding="utf-8",
        )
        checklist_path.write_text(
            self._render_acceptance_checklist(preview=preview, manual_risk_file=manual_file, end_date=end_date),
            encoding="utf-8",
        )

        self.logger.info("人工逻辑红线验收报告已输出: %s", report_path)
        return {
            "preview_csv": csv_path,
            "report_markdown": report_path,
            "report_json": json_path,
            "checklist_markdown": checklist_path,
        }

    def _render_acceptance_report(
        self,
        preview: pd.DataFrame,
        validation_result: dict[str, Any],
        manual_risk_file: str,
        end_date: str,
    ) -> str:
        """渲染验收辅助报告。"""

        active_rows = preview.loc[preview["active_on_end_date"] == True].copy() if not preview.empty else pd.DataFrame()
        active_symbols = self._symbol_list(active_rows["symbol"] if not active_rows.empty else pd.Series(dtype=str))
        paused_symbols = self._symbol_list(active_rows.loc[active_rows["final_pause_buy"] == True, "symbol"] if not active_rows.empty else pd.Series(dtype=str))
        review_symbols = self._symbol_list(active_rows.loc[active_rows["final_force_review"] == True, "symbol"] if not active_rows.empty else pd.Series(dtype=str))
        thesis_symbols = self._symbol_list(active_rows.loc[active_rows["thesis_broken"] == True, "symbol"] if not active_rows.empty else pd.Series(dtype=str))

        lines = [
            "# 人工逻辑红线验收辅助报告",
            "",
            "## 当前启用样例",
            f"- manual_risk_file: {manual_risk_file}",
            f"- backtest_start_date: {self.configs['backtest']['backtest']['start_date']}",
            f"- check_end_date: {end_date}",
            f"- validation_valid: {validation_result['valid']}",
            "",
            "## 当前生效状态摘要",
            f"- end-date 前已生效的 symbol: {active_symbols if active_symbols else '无'}",
            f"- 强制人工复核的 symbol: {review_symbols if review_symbols else '无'}",
            f"- thesis_broken 的 symbol: {thesis_symbols if thesis_symbols else '无'}",
            "",
            "## 最终动作预览",
            self._frame_to_text(preview) if not preview.empty else "当前无人工逻辑红线样例记录",
            "",
            "## 校验问题",
            self._frame_to_text(validation_result["issues"]) if not validation_result["issues"].empty else "当前无配置校验问题",
            "",
            "## 每个案例的预期行为摘要",
        ]

        if preview.empty:
            lines.append("- 当前无案例。")
        else:
            for _, row in preview.iterrows():
                lines.append(
                    f"- {row['symbol']}: {row['final_human_readable_action']} | 生效日期={row['effective_from']} | 预期={row['expected_behavior']}"
                )

        lines.extend(
            [
                "",
                "## 说明",
                "- 本报告仅用于验收人工逻辑红线链路，不构成投资建议。",
                "- 这里的最终动作预览以价格侧 GREEN 作为基线，真正的价格红线与人工逻辑红线合并结果，请继续结合 suggest / backtest 报告核对。",
                "- 使用 --manual-risk-file 可在不覆盖正式配置的前提下切换验收样例。",
            ]
        )
        return "\n".join(lines) + "\n"

    def _render_acceptance_checklist(self, preview: pd.DataFrame, manual_risk_file: str, end_date: str) -> str:
        """渲染可执行的人工验收清单。"""

        pause_case = self._pick_case(preview, lambda frame: frame.loc[(frame["manual_pause_buy"] == True) & (frame["thesis_broken"] == False)])
        review_case = self._pick_case(preview, lambda frame: frame.loc[(frame["manual_force_review"] == True) & (frame["thesis_broken"] == False)])
        thesis_case = self._pick_case(preview, lambda frame: frame.loc[frame["thesis_broken"] == True])

        command_prefix = f"python -m src.main"
        lines = [
            "# 人工逻辑红线验收清单",
            "",
            "## 1. 验收前准备",
            f"- 本次验收请使用样例文件: `{manual_risk_file}`",
            "- 无需覆盖正式 manual_risk_flags.yaml/json；建议直接使用 `--manual-risk-file` 参数。",
            "- 若你仍想手工替换正式文件，请先自行备份正式配置后再操作。",
            "- 建议按顺序执行，避免并发运行导致缓存读写竞争。",
            f"- 建议执行顺序 1: `{command_prefix} validate-manual-risk-flags --manual-risk-file {manual_risk_file} --end-date {end_date}`",
            f"- 建议执行顺序 2: `{command_prefix} suggest --manual-risk-file {manual_risk_file} --end-date {end_date}`",
            f"- 建议执行顺序 3: `{command_prefix} backtest --manual-risk-file {manual_risk_file} --end-date {end_date}`",
            "",
            "## 2. 案例 A 验收步骤：manual_pause_buy",
            self._render_case_checklist(
                case_row=pause_case,
                command_prefix=command_prefix,
                manual_risk_file=manual_risk_file,
                end_date=end_date,
                expected_lines=[
                    "suggest 输出中，该标的应显示暂停新增。",
                    "monthly_report 中，该标的应进入“本月暂缓或无法执行项目”或风险摘要中的暂停新增状态。",
                    "backtest 中，该标的在 effective_from 之后不再新增买入。",
                    "已有持仓不会被自动卖出。",
                ],
            ),
            "",
            "## 3. 案例 B 验收步骤：manual_force_review",
            self._render_case_checklist(
                case_row=review_case,
                command_prefix=command_prefix,
                manual_risk_file=manual_risk_file,
                end_date=end_date,
                expected_lines=[
                    "suggest 输出中，该标的应进入强制人工复核。",
                    "按当前默认配置，manual_force_review 会暂停新增，因此月报中应体现暂停新增/强制复核。",
                    "backtest 中，该标的在生效后不再新增买入。",
                    "若该标的同时触发价格红线，最终动作仍应体现人工逻辑红线优先级更高。",
                ],
            ),
            "",
            "## 4. 案例 C 验收步骤：thesis_broken",
            self._render_case_checklist(
                case_row=thesis_case,
                command_prefix=command_prefix,
                manual_risk_file=manual_risk_file,
                end_date=end_date,
                expected_lines=[
                    "suggest 中应标记为最高优先级人工处理项。",
                    "monthly_report / backtest_report 中应能看到 thesis_broken 状态。",
                    "effective_from 之后，该标的不再新增买入。",
                    "系统不会自动卖出已有持仓。",
                ],
            ),
            "",
            "## 5. 生效日期检查",
            "- 人工检查同一标的在 effective_from 之前的建议与回测记录，应确认逻辑未生效。",
            "- 人工检查 effective_from 当天或之后的建议与回测记录，应确认逻辑开始生效。",
            "- 若发现生效日前后无差异，请优先核对 end-date、样例文件路径和报告中的 effective_from。",
            "",
            "## 6. 合并逻辑检查",
            "- 当价格红线与人工逻辑红线同时存在时，应以人工逻辑红线高优先级为准。",
            "- 月报和回测报告中应能看到 final_reason_codes / final_human_readable_action 或对应中文动作说明。",
            "- 若看到价格 YELLOW 与 manual_force_review 同时存在，最终动作应仍显示为“暂停新增，强制人工复核”或更高优先级动作。",
            "",
            "## 7. 回归检查",
            f"- 改回默认正式文件后运行：`{command_prefix} suggest --end-date {end_date}` 与 `{command_prefix} backtest --end-date {end_date}`。",
            "- 或者将样例文件中所有布尔值改回 false 后重新执行相同命令。",
            "- 对比确认：新能力未悄悄改变原有未启用样例时的建议、回测与不自动卖出边界。",
            "",
            "## 8. 重点查看的输出文件",
            "- reports/manual/manual_risk_flags_validation.md",
            "- reports/manual/manual_logic_risk_acceptance_report.md",
            "- reports/monthly/monthly_report_*.md",
            "- reports/backtest/backtest_report.md",
        ]
        return "\n".join(lines) + "\n"

    @staticmethod
    def _render_case_checklist(
        case_row: pd.Series | None,
        command_prefix: str,
        manual_risk_file: str,
        end_date: str,
        expected_lines: list[str],
    ) -> str:
        """渲染单个验收案例。"""

        if case_row is None:
            return "- 当前样例文件中未找到对应案例。"

        lines = [
            f"- symbol: {case_row['symbol']}",
            f"- effective_from: {case_row['effective_from']}",
            f"- note: {case_row['note']}",
            f"- 运行命令: `{command_prefix} suggest --manual-risk-file {manual_risk_file} --end-date {end_date}`",
            f"- 运行命令: `{command_prefix} backtest --manual-risk-file {manual_risk_file} --end-date {end_date}`",
            "- 重点查看输出文件：monthly_report、backtest_report、manual_logic_risk_acceptance_report。",
        ]
        lines.extend([f"- 预期结果: {item}" for item in expected_lines])
        return "\n".join(lines)

    @staticmethod
    def _pick_case(preview: pd.DataFrame, picker: Any) -> pd.Series | None:
        """从预览表中选择一个案例。"""

        if preview.empty:
            return None
        frame = picker(preview)
        if frame.empty:
            return None
        return frame.iloc[0]

    @staticmethod
    def _safe_timestamp(value: str) -> pd.Timestamp | None:
        """安全解析日期。"""

        try:
            return pd.Timestamp(value)
        except Exception:  # noqa: BLE001
            return None

    @staticmethod
    def _window_state(effective_ts: pd.Timestamp | None, start_ts: pd.Timestamp, end_ts: pd.Timestamp) -> str:
        """给出生效窗口说明。"""

        if effective_ts is None:
            return "effective_from 非法"
        if effective_ts <= start_ts:
            return "回测起点前已生效"
        if effective_ts <= end_ts:
            return "回测区间内生效"
        return "截至检查日尚未生效"

    @staticmethod
    def _expected_behavior(flag: Any) -> str:
        """给出人工逻辑红线的预期行为摘要。"""

        if flag.thesis_broken:
            return "停止新增，最高优先级人工处理，不自动卖出已有持仓"
        if flag.manual_force_review:
            return "强制人工复核；按默认配置暂停新增，不自动卖出已有持仓"
        if flag.manual_pause_buy:
            return "暂停新增，等待人工解除，不自动卖出已有持仓"
        return "当前无人工逻辑动作"

    @staticmethod
    def _symbol_list(series: pd.Series) -> str:
        """将 symbol 列表转为易读文本。"""

        values = sorted({str(item) for item in series.tolist() if str(item)})
        return ",".join(values)

    def _resolve_path(self, value: str | Path | None) -> Path | None:
        """将相对路径解析为项目内绝对路径。"""

        if value is None:
            return None
        path = Path(value)
        return path if path.is_absolute() else self.project_root / path

    @staticmethod
    def _frame_to_text(frame: pd.DataFrame) -> str:
        """将 DataFrame 渲染为 markdown 文本块。"""

        if frame.empty:
            return "无"
        return "```text\n" + frame.to_csv(index=False) + "```"
