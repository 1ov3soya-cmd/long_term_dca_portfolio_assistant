"""研究结果落盘器。"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from src.agent_research.research_schema import AgentResearchResult


class ResearchSnapshotWriter:
    """将研究输出写到 ``reports/agent_research``。"""

    def __init__(self, project_root: str | Path) -> None:
        self.project_root = Path(project_root)
        self.output_dir = self.project_root / "reports" / "agent_research"
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def write(
        self,
        result: AgentResearchResult,
        memo_markdown: str,
        source_run_id: str = "",
    ) -> dict[str, Path]:
        """写出 JSON、Markdown，并维护轻量 research index。"""

        safe_date = result.analysis_date.replace("-", "")
        json_path = self.output_dir / f"{result.symbol}_{safe_date}_agent_research.json"
        memo_path = self.output_dir / f"{result.symbol}_{safe_date}_agent_research.md"

        json_path.write_text(
            json.dumps(result.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        memo_path.write_text(memo_markdown, encoding="utf-8")
        self._update_index(result=result, json_path=json_path, memo_path=memo_path, source_run_id=source_run_id)
        return {
            "json": json_path,
            "markdown": memo_path,
        }

    def _update_index(
        self,
        result: AgentResearchResult,
        json_path: Path,
        memo_path: Path,
        source_run_id: str,
    ) -> None:
        """维护前端可直接消费的 research index。"""

        index_path = self.output_dir / "research_index.json"
        if index_path.exists():
            try:
                payload = json.loads(index_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                payload = {}
        else:
            payload = {}

        items = payload.get("items", [])
        relative_json_path = str(json_path.relative_to(self.project_root)).replace("\\", "/")
        relative_markdown_path = str(memo_path.relative_to(self.project_root)).replace("\\", "/")
        now_text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = {
            "symbol": result.symbol,
            "analysis_date": result.analysis_date,
            "final_research_label": result.final_research_label,
            "suggest_manual_pause_buy": bool(result.suggest_manual_pause_buy),
            "suggest_force_review": bool(result.suggest_force_review),
            "suggest_thesis_broken": bool(result.suggest_thesis_broken),
            "confidence": float(result.confidence),
            "source": result.source,
            "json_relative_path": relative_json_path,
            "markdown_relative_path": relative_markdown_path,
            "source_run_id": source_run_id,
            "updated_at": now_text,
        }

        items = [
            item for item in items
            if not (item.get("symbol") == result.symbol and item.get("analysis_date") == result.analysis_date)
        ]
        items.append(entry)
        items.sort(key=lambda item: (item.get("analysis_date", ""), item.get("symbol", "")), reverse=True)

        payload = {
            "updated_at": now_text,
            "items": items,
        }
        index_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")