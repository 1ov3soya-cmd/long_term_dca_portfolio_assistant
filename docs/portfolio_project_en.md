# Portfolio Project Summary (EN)

## One-line Description

A local research and review workstation for long-term DCA investing in China A-share / exchange-traded ETF scenarios, with archive-backed reporting, manual risk governance, and an advisory research enhancement layer.

## Problem It Solves

This project addresses three practical gaps in long-term investing workflows:

1. low-frequency allocation and DCA suggestions often lack an auditable engineering workflow;
2. risk reminders, manual review, backtest validation, and research notes are usually scattered across scripts and documents;
3. research-enhancement outputs need strict boundaries so they do not overtake human review or the base strategy.

## Core Features

- real market-data ingestion, caching, archive output, and validation
- monthly suggestion generation and low-frequency backtesting
- data validation, backtest consistency checks, sensitivity testing, and robustness summaries
- manual risk flags with acceptance / validation workflow
- run archive and run comparison
- TradingAgents research enhancement PoC
- read-only frontend workspace: Dashboard / Compare / Manual Risk / Research / Research vs Manual Risk

## Tech Stack

- Python 3.11+
- pandas / numpy
- e-finance
- React + Vite + Tailwind
- i18next / react-i18next
- filesystem-based archives (JSON / Markdown / CSV)

## Architecture Highlights

- configuration-driven rules for thresholds, execution cadence, and risk logic
- archive-driven workflow for traceability and reproducibility
- decoupled frontend that reads archived artifacts via `/archive-data/...` instead of a custom API service
- adapter-based frontend data shaping for Dashboard, Compare, Manual Risk, Research, and alignment views

## Risk-Control and Explainability Highlights

- explicit separation between price-based risk rules and manual logic risk rules
- auditable manual pause / force review / thesis broken states
- default behavior is reminder / pause new buys / human review rather than automatic sell execution
- direct side-by-side comparison between agent research suggestions and current manual risk state

## Frontend Workspace Highlights

- dark, restrained, read-only research dashboard style
- dashboard aggregation of latest runs, risk matrix, research summary, and alignment summary
- graceful degradation when some archive files are missing
- bilingual UI support (Chinese / English)

## TradingAgents PoC Highlights

- TradingAgents is constrained to an advisory research layer, not an execution layer
- outputs structured bull / bear / risk memo fields and suggest_* candidate tags
- research outputs are archived and compared against manual risk state in a read-only frontend view

## My Contribution

I designed and implemented the overall architecture, Python research layer, archive system, validation and comparison workflows, frontend adapter layer, and the read-only dashboard integration, while explicitly constraining the research-enhancement layer to remain advisory instead of executable.

## Current Boundaries and Limits

- this is not an auto-trading system
- there is no broker execution integration
- there is no high-frequency or intraday strategy layer
- automatic sell logic is intentionally disabled
- TradingAgents is still a PoC-level research enhancement layer
- the frontend is primarily for archive review and human decision support, not core strategy computation