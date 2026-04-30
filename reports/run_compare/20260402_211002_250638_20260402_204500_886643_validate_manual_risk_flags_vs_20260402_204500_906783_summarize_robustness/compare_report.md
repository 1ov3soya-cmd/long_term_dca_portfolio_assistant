# 运行结果对比报告

## 1. 比较目的说明
- 本报告用于比较两次已归档运行的输入、配置、摘要结果与告警差异。
- 当前系统仍定位为长期定投研究与人工确认辅助工具，本报告不等于自动决策建议。

## 2. run_a / run_b 基本信息
- run_a: D:\新建文件夹\long_term_dca_portfolio_assistant\reports\runs\20260402_204500_886643_validate_manual_risk_flags
- run_b: D:\新建文件夹\long_term_dca_portfolio_assistant\reports\runs\20260402_204500_906783_summarize_robustness
- run_a command: validate-manual-risk-flags
- run_b command: summarize-robustness
- compare_status: success

## 3. 可比性判断
- comparable_level: low
- comparability_reason: 两次运行的 command_name 不一致，不建议直接比较核心结果。

## 7. 关键 summary 指标差异
- baseline_assessment: value_a=nan, value_b=中性可用, direction=added, absolute_change=, relative_change=
- effective_in_range_count: value_a=9.0, value_b=nan, direction=removed, absolute_change=, relative_change=
- etf_risk_rule_recommendation: value_a=nan, value_b=保留, direction=added, absolute_change=, relative_change=
- force_review_count: value_a=0.0, value_b=nan, direction=removed, absolute_change=, relative_change=
- keep_first_trading_day_default: value_a=nan, value_b=保留, direction=added, absolute_change=, relative_change=
- keep_forward_default: value_a=nan, value_b=保留，但需备注限制, direction=added, absolute_change=, relative_change=
- pause_buy_count: value_a=0.0, value_b=nan, direction=removed, absolute_change=, relative_change=
- stock_risk_rule_recommendation: value_a=nan, value_b=证据不足，暂不调整, direction=added, absolute_change=, relative_change=
- symbols_flagged: value_a=9.0, value_b=nan, direction=removed, absolute_change=, relative_change=
- thesis_broken_count: value_a=0.0, value_b=nan, direction=removed, absolute_change=, relative_change=

## 8. 输出产物差异
- added:
  - original_outputs.key_findings_csv: D:\新建文件夹\long_term_dca_portfolio_assistant\reports\robustness_key_findings.csv
  - original_outputs.recommendation_markdown: D:\新建文件夹\long_term_dca_portfolio_assistant\reports\default_parameter_recommendation.md
  - original_outputs.summary_json: D:\新建文件夹\long_term_dca_portfolio_assistant\reports\robustness_summary.json
  - original_outputs.summary_markdown: D:\新建文件夹\long_term_dca_portfolio_assistant\reports\robustness_summary.md
- removed:
  - original_outputs.acceptance_artifacts.checklist_markdown: D:\新建文件夹\long_term_dca_portfolio_assistant\reports\manual_logic_risk_acceptance_checklist.md
  - original_outputs.acceptance_artifacts.preview_csv: D:\新建文件夹\long_term_dca_portfolio_assistant\reports\manual\manual_logic_risk_acceptance_preview.csv
  - original_outputs.acceptance_artifacts.report_json: D:\新建文件夹\long_term_dca_portfolio_assistant\reports\manual\manual_logic_risk_acceptance_report.json
  - original_outputs.acceptance_artifacts.report_markdown: D:\新建文件夹\long_term_dca_portfolio_assistant\reports\manual\manual_logic_risk_acceptance_report.md
  - original_outputs.validation_report.csv: D:\新建文件夹\long_term_dca_portfolio_assistant\reports\manual\manual_risk_flags_validation.csv
  - original_outputs.validation_report.json: D:\新建文件夹\long_term_dca_portfolio_assistant\reports\manual\manual_risk_flags_validation.json
  - original_outputs.validation_report.markdown: D:\新建文件夹\long_term_dca_portfolio_assistant\reports\manual\manual_risk_flags_validation.md

## 9. warnings / limitations 差异
- warnings:
  - same_items: []
  - only_a_items: ['当前无关键告警。']
  - only_b_items: ['稳健性结论基于部分敏感性测试结果，失败组数量: 1。']
- limitations:
  - same_items: ['当前无失败信息。']
  - only_a_items: []
  - only_b_items: []
- extra_notes:
  - same_items: []
  - only_a_items: []
  - only_b_items: ['稳健性总结基于 sensitivity-test 既有输出生成。']

## 10. 最值得关注的差异摘要
- 可比性判断: low，原因：两次运行的 command_name 不一致，不建议直接比较核心结果。
- 最大结果差异: baseline_assessment，value_a=nan，value_b=中性可用
- 输出产物存在路径差异，请先区分路径变化与结果变化。

## 11. 结论与解释
- 最大配置差异: 无
- 最大结果差异: baseline_assessment
- 纯路径差异不应直接解释为策略或回测结果差异，请结合 key_summary 与配置变更一起判断。

## 12. 限制说明
- 对比器第一版基于 JSON/CSV/Markdown 归档产物，不做复杂语义理解。
- 若 run 目录缺失关键文件，对比结果会降级为 partial 或 failed，并在报告中列出缺失项。
- 不同命令类型之间通常不建议直接比较收益或风险指标。
