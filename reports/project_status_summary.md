# Project Status Summary

## Project Name

Long-term DCA Portfolio Assistant

## Positioning

A long-term investment research and review assistant for China A-share / exchange-traded ETF scenarios. It focuses on low-frequency DCA, asset allocation, risk reminders, archive-backed review, and human-confirmed execution.

## Completion Rating

Usable MVP / near-complete research tool.

This project is beyond a prototype in terms of workflow completeness, but it is not a production trading execution system.

## Completed Core Capabilities

- real-data market data pipeline with local cache and archive outputs
- monthly suggestion generation under the fixed ETF 80% / stock 20% framework
- low-frequency backtest and validation outputs
- data validation and backtest consistency checks
- sensitivity testing and robustness summary
- manual logic risk flags and validation
- archived run snapshots and run comparison
- TradingAgents research enhancement PoC output
- archive-backed frontend dashboard and review pages

## Completed Frontend Pages

- Dashboard
- Run Compare
- Manual Risk
- Research
- Research vs Manual Risk

## Current Constraints

- frontend is read-only
- no broker integration
- no auto execution
- no auto sell logic
- TradingAgents remains an advisory research PoC
- some backend commands are represented as summary cards rather than dedicated drill-down pages

## Best Current Usage Mode

The system is best used as a local research workstation:

1. refresh or validate data
2. review monthly suggestion and risk outputs
3. inspect archived runs and compare outputs
4. review manual risk state
5. review agent research memo and research/manual-risk alignment
6. make final decisions manually outside the system

## Enhancement Directions

1. add lightweight frontend smoke tests
2. add dedicated drill-down pages for robustness or backtest reports if needed
3. add a generated frontend snapshot layer to reduce raw archive traversal in the browser
4. improve release-time archive freshness checks
5. keep TradingAgents advisory unless governance rules are explicitly expanded

## Priority TODO

### P1: High Priority, Non-blocking

- add lightweight frontend smoke tests for routing and archive loading
- add a repeatable release checklist for archive freshness and key files
- normalize naming across frontend docs and demo materials

### P2: Medium Priority Enhancements

- add dedicated frontend drill-down pages for robustness and backtest outputs
- generate smaller frontend-friendly snapshots from Python to simplify adapters
- improve empty / partial state coverage with a small automated test matrix

### P3: Longer-term Ideas

- add richer archive search / filtering across runs
- extend research coverage beyond the initial stock enhancement pool
- formalize portfolio-demo screenshots or walkthrough assets for showcase use