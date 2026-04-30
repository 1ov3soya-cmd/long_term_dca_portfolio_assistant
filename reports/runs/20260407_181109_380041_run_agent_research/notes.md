# 运行说明

- command_name: run-agent-research
- run_id: 20260407_181109_380041_run_agent_research
- status: success
- started_at: 2026-04-07 18:11:09
- finished_at: 2026-04-07 18:11:09
- duration_seconds: 0.006

## 本次运行做了什么
- 已执行 `run-agent-research` 命令，并记录本次运行的配置快照、输入参数、输出产物索引与关键摘要。

## 关键告警
- 当前无关键告警。

## 失败或限制
- 当前无失败信息。

## 额外说明
- TradingAgents PoC 当前为研究增强层，不直接输出交易执行动作。
- 本次研究结果不会自动改写正式 manual risk flags，需要人工确认后再采纳。
- 第一版仅分析股票增强仓，不分析 ETF 主底仓。

## 关键摘要
- symbol: 600519
- analysis_date: 2025-12-31
- final_research_label: thesis_broken_candidate
- suggest_manual_pause_buy: False
- suggest_force_review: True
- suggest_thesis_broken: True
- confidence: 0.9
- source: tradingagents_poc

## 建议优先查看的输出文件
- agent_research: {'json': 'D:\\新建文件夹\\long_term_dca_portfolio_assistant\\reports\\agent_research\\600519_20251231_agent_research.json', 'markdown': 'D:\\新建文件夹\\long_term_dca_portfolio_assistant\\reports\\agent_research\\600519_20251231_agent_research.md'}
