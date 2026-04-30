# 运行说明

- command_name: summarize-robustness
- run_id: 20260402_204500_906783_summarize_robustness
- status: partial
- started_at: 2026-04-02 20:45:00
- finished_at: 2026-04-02 20:45:01
- duration_seconds: 0.12

## 本次运行做了什么
- 已执行 `summarize-robustness` 命令，并记录本次运行的配置快照、输入参数、输出产物索引与关键摘要。

## 关键告警
- 稳健性结论基于部分敏感性测试结果，失败组数量: 1。

## 失败或限制
- 当前无失败信息。

## 额外说明
- 稳健性总结基于 sensitivity-test 既有输出生成。

## 关键摘要
- baseline_assessment: 中性可用
- keep_forward_default: 保留，但需备注限制
- keep_first_trading_day_default: 保留
- etf_risk_rule_recommendation: 保留
- stock_risk_rule_recommendation: 证据不足，暂不调整

## 建议优先查看的输出文件
- summary_markdown: D:\新建文件夹\long_term_dca_portfolio_assistant\reports\robustness_summary.md
- recommendation_markdown: D:\新建文件夹\long_term_dca_portfolio_assistant\reports\default_parameter_recommendation.md
- summary_json: D:\新建文件夹\long_term_dca_portfolio_assistant\reports\robustness_summary.json
- key_findings_csv: D:\新建文件夹\long_term_dca_portfolio_assistant\reports\robustness_key_findings.csv
