"""TradingAgents-style research bridge for advisory-only analyst debate."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from src.agent_research.research_schema import AgentResearchResult, ResearchLabel
from src.utils.logger import get_logger


@dataclass(frozen=True, slots=True)
class StockDebateProfile:
    """Symbol-specific debate profile used by the placeholder provider."""

    name: str
    sector: str
    role_in_portfolio: str
    bull_thesis: tuple[str, str, str]
    bear_thesis: tuple[str, str, str]
    debate_focus: str
    key_uncertainty: str


@dataclass(frozen=True, slots=True)
class SuggestResearchContext:
    """Context captured from the latest suggest row or monthly batch item."""

    asset_type: str = "stock"
    suggested_amount: float = 0.0
    target_weight: float = 0.0
    current_weight: float = 0.0
    suggest_status: str = ""
    final_action: str = ""
    reasons: str = ""
    logic_note: str = ""
    manual_pause_buy: bool = False
    manual_force_review: bool = False
    thesis_broken: bool = False
    pause_buy: bool = False
    final_priority_level: int | None = None
    final_reason_codes: str = ""


STOCK_DEBATE_PROFILES: dict[str, StockDebateProfile] = {
    "600519": StockDebateProfile(
        name="贵州茅台",
        sector="高端白酒",
        role_in_portfolio="股票 20% 增强仓中的高质量消费观察标的",
        bull_thesis=(
            "品牌资产和渠道掌控力仍是高端白酒里最强的一档，这决定了它在行业放缓时仍有防守属性。",
            "自由现金流、盈利质量和分红能力通常是这类资产长期被资金反复定价的核心依据。",
            "如果本月建议只是把它放回低频观察池，而不是抬高优先级，这种安排和长期定投框架是相容的。",
        ),
        bear_thesis=(
            "高端消费恢复的节奏一旦低于预期，估值就会从稀缺溢价转向耐心折价。",
            "当市场对确定性资产的要求变高时，茅台的下行风险常常不是业绩崩塌，而是估值缓慢压缩。",
            "在股票只是 20% 增强仓的前提下，这类高估值资产一旦证据不够扎实，就不值得抢着新增。",
        ),
        debate_focus="高质量消费资产的长期稀缺性，能否抵消估值与需求验证的不确定性。",
        key_uncertainty="消费复苏强度与高估值之间，究竟哪一方会在未来几个季度占主导。",
    ),
    "000858": StockDebateProfile(
        name="五粮液",
        sector="白酒",
        role_in_portfolio="股票增强仓中的消费替代观察标的",
        bull_thesis=(
            "次高端到高端带的品牌力仍有存量价值，若渠道库存和价盘重新稳定，估值修复弹性会比龙头更大。",
            "市场通常会在悲观阶段低估管理改善和渠道修复的速度，这给长期观察留出空间。",
            "如果只是保留在观察名单而不是提升优先级，研究上仍可以持续跟踪而不违反保守边界。",
        ),
        bear_thesis=(
            "它面临的问题不只是行业周期，而是品牌心智、价盘稳定和渠道执行能否重新形成正反馈。",
            "一旦 thesis 已经被人工标记为 broken，说明系统当前更需要保守治理，而不是继续寻找看多理由。",
            "在这种状态下，继续新增会把研究不确定性直接转化成组合噪音。",
        ),
        debate_focus="修复弹性是否还值得跟踪，还是 thesis 已经劣化到不应继续新增。",
        key_uncertainty="渠道和品牌修复到底是暂时失速，还是更深层的竞争力下滑。",
    ),
    "600036": StockDebateProfile(
        name="招商银行",
        sector="银行",
        role_in_portfolio="股票增强仓中的高 ROE 金融观察标的",
        bull_thesis=(
            "零售银行能力、负债成本管理和风险控制体系，仍然使它在银行板块里具备结构性优势。",
            "如果市场对银行股的担忧主要集中在宏观预期而不是个体基本面，那么招行更容易成为低频增强仓的优先候选。",
            "对于长期定投系统，能稳定贡献股息和盈利质量的金融资产，本来就适合被持续跟踪。",
        ),
        bear_thesis=(
            "银行股最大的风险不是短期波动，而是信用周期和息差压力缓慢侵蚀估值锚。",
            "如果新增理由只是便宜，而没有看到盈利质量和风险暴露的进一步确认，那么看多逻辑并不充分。",
            "股票增强仓不需要为了填满预算而配置一个证据尚不饱满的金融资产。",
        ),
        debate_focus="高质量银行的稳定性，是否足以覆盖信用周期和息差压力的慢变量风险。",
        key_uncertainty="息差、资产质量和市场风险偏好，哪一个会率先改变对银行股的定价。",
    ),
    "000333": StockDebateProfile(
        name="美的集团",
        sector="家电制造",
        role_in_portfolio="股票增强仓中的制造业现金流观察标的",
        bull_thesis=(
            "美的的优势在于经营韧性、全球化制造和现金回流能力，这类特征适合低频长期跟踪。",
            "如果市场情绪过度关注短期需求波动，反而可能低估其在成本控制和产品结构上的主动权。",
            "把它放在增强仓候选池，符合系统对稳健制造业资产的观察逻辑。",
        ),
        bear_thesis=(
            "家电本质上仍受地产、出口和可选消费景气影响，防御属性并没有想象中那么强。",
            "制造业龙头的确定性来自执行力，但执行力并不能完全对冲需求放缓带来的估值压力。",
            "如果本月没有更强证据支持提升优先级，那就不该因为公司质地好而默认继续加码。",
        ),
        debate_focus="制造业龙头的经营韧性，是否足以支撑在增强仓里继续维持跟踪优先级。",
        key_uncertainty="需求端疲弱持续多久，以及成本与出海优势能否继续对冲内需波动。",
    ),
    "601318": StockDebateProfile(
        name="中国平安",
        sector="保险综合金融",
        role_in_portfolio="股票增强仓中的综合金融修复观察标的",
        bull_thesis=(
            "保险资金属性、综合金融平台和长期负债端能力，使它具备不同于纯周期股的配置意义。",
            "若市场对负债端恢复和资产端风险的担忧开始缓解，估值修复空间可能比一般高股息资产更明显。",
            "在增强仓框架里，它适合被视作修复型跟踪标的，而不是立即高优先级执行标的。",
        ),
        bear_thesis=(
            "保险股的复杂性在于负债端、投资端和市场情绪会同时影响定价，单一好消息往往不足以扭转预期。",
            "如果研究证据不能证明修复已经进入更高确定性的阶段，那么继续新增只是提前押注。",
            "对保守型定投系统来说，证据不足的修复逻辑应先停留在观察层，而不是执行层。",
        ),
        debate_focus="修复型综合金融资产，当前更像等待验证的候选，还是已具备继续新增的证据。",
        key_uncertainty="负债端恢复和投资端波动之间，哪一端会主导市场对平安的估值判断。",
    ),
}

ETF_ROLE_MAP: dict[str, str] = {
    "510300": "宽基核心底仓",
    "510500": "中盘宽基补充底仓",
    "515180": "红利风格底仓",
    "518880": "防御型黄金配置仓",
}


class TradingAgentsBridge:
    """Provide TradingAgents-style research debate outputs.

    The current implementation is still a placeholder provider, but it no longer
    emits generic one-size-fits-all text. Instead it produces symbol-aware,
    context-aware analyst-style debate outputs that remain advisory-only.
    """

    def __init__(self, project_root: str | Path, configs: dict[str, dict[str, Any]]) -> None:
        self.project_root = Path(project_root)
        self.configs = configs
        log_level = configs.get("app", {}).get("runtime", {}).get("log_level", "INFO")
        self.logger = get_logger(self.__class__.__name__, log_level)
        self.provider_mode = "placeholder"
        self.etf_weight = float(configs.get("portfolio", {}).get("asset_allocation", {}).get("etf_total_weight", 0.80))
        self.stock_weight = float(configs.get("portfolio", {}).get("asset_allocation", {}).get("stock_total_weight", 0.20))

    def list_stock_pool(self) -> list[dict[str, Any]]:
        """Return the configured stock enhancement pool."""

        return list(self.configs.get("portfolio", {}).get("stock_pool", []))

    def run_symbol_research(
        self,
        symbol: str,
        analysis_date: str,
        context: dict[str, Any] | None = None,
    ) -> AgentResearchResult:
        """Generate one structured research result for a stock or ETF symbol."""

        normalized_context = self._normalize_context(context)
        asset_type = normalized_context.asset_type or self._infer_asset_type(symbol)

        if asset_type == "etf":
            result = self._build_etf_research(symbol=symbol, analysis_date=analysis_date, context=normalized_context)
        else:
            result = self._build_stock_research(symbol=symbol, analysis_date=analysis_date, context=normalized_context)

        self.logger.info(
            "TradingAgents-style research generated: symbol=%s, label=%s, confidence=%.2f",
            result.symbol,
            result.final_research_label,
            result.confidence,
        )
        return result

    def _build_stock_research(
        self,
        symbol: str,
        analysis_date: str,
        context: SuggestResearchContext,
    ) -> AgentResearchResult:
        profile = self._get_stock_profile(symbol)
        label, confidence = self._decide_label(symbol=symbol, analysis_date=analysis_date, context=context)
        suggestions = self._map_label_to_manual_risk(label)

        amount_text = self._format_amount(context.suggested_amount)
        suggestion_signal = context.suggest_status or "未显式标记"
        final_action = context.final_action or "研究层仅提供 advisory-only 建议"

        bull_points = [
            f"组合角色：{profile.role_in_portfolio}，不是主底仓，因此更看重是否值得保留在低频观察和候选名单里。",
            f"经营与资产质量：{profile.bull_thesis[0]}",
            f"研究语境：本月建议金额 {amount_text}，suggest 状态为 {suggestion_signal}，说明它当前至少仍在建议清单或观察边界之内。",
            f"风险治理关系：manual risk 当前动作是“{final_action}”，bull 立场的核心不是直接放宽边界，而是论证它是否仍配得上继续跟踪。",
        ]
        bear_points = [
            f"风险薄弱点：{profile.bear_thesis[0]}",
            f"估值与胜率：{profile.bear_thesis[1]}",
            f"系统边界：股票只占组合 {self._format_percent(self.stock_weight)} 的增强仓，意味着证据不足时应优先保守，而不是强行给它更高执行权重。",
            f"当前建议上下文：reason / logic_note 提示“{self._trim_reason(context.reasons or context.logic_note)}”，bear 立场会把这视为需要先复核而非直接放行的信号。",
        ]

        bull_case = (
            f"Bull researcher 的立场是：{profile.name} 仍值得留在长期定投系统的低频观察池里，"
            f"但前提是把它当作{profile.role_in_portfolio}来理解，而不是当作需要立即执行的高优先级标的。"
            f"支持这一判断的证据主要来自四个层面：第一，{profile.bull_thesis[0]}；第二，{profile.bull_thesis[1]}；"
            f"第三，本月建议金额为 {amount_text}，说明系统并没有彻底把它移出候选清单；第四，当前系统强调 ETF {self._format_percent(self.etf_weight)} / 股票 {self._format_percent(self.stock_weight)}，"
            f"股票增强仓本来就允许保留少量“继续跟踪但不提高主观信心”的观察仓位。"
            f"Bull 立场也承认 bear 侧关于“{profile.key_uncertainty}”的担忧并非无效，但在缺少明确 thesis 崩坏证据之前，"
            f"更合理的动作仍是保留研究覆盖、维持低频跟踪，而不是把它直接从观察池中剔除。"
            f"对当前系统的行动含义是：它可以继续留在候选池或观察名单中，但不应因为单月情绪改善就自动提升执行优先级。"
        )

        bear_case = (
            f"Bear researcher 的立场是：{profile.name} 当前更接近“先复核、再决定是否继续新增”的对象，"
            f"因为它面临的争议点不是短期波动，而是{profile.debate_focus}。"
            f"支持这一判断的证据也至少有四个：第一，{profile.bear_thesis[0]}；第二，{profile.bear_thesis[1]}；第三，"
            f"本月建议上下文里已经出现“{self._trim_reason(context.reasons or context.logic_note)}”这类需要解释的信号；第四，"
            f"在股票只是 {self._format_percent(self.stock_weight)} 增强仓的前提下，研究证据如果没有明显占优，就不值得继续消耗新增预算。"
            f"Bear 立场同样承认 bull 侧关于“{profile.bull_thesis[2]}”的观点并非全错，但这最多说明它还能被研究，"
            f"并不能直接证明本月就应该继续新增。"
            f"对当前系统的行动含义是：更适合把它推向 manual pause / force review / thesis broken 候选讨论，至少不要轻易提高新增优先级。"
        )

        bull_action = (
            f"保留在观察池，继续作为{profile.role_in_portfolio}的一部分做低频跟踪；如果后续证据改善，可讨论是否恢复更积极的新增资格。"
        )
        bear_action = (
            f"在当前证据结构下，更合理的处理是把它靠近 manual risk 人工治理层，先讨论暂停新增或强制复核，而不是给出更高执行信心。"
        )

        risk_summary = (
            f"本次 debate 的焦点是：{profile.debate_focus}。关键不确定性在于“{profile.key_uncertainty}”。"
            f"综合 bull 与 bear 两侧后，当前输出标签为 {label}，对应的建议性 manual risk 映射是 pause={suggestions['suggest_manual_pause_buy']}, "
            f"review={suggestions['suggest_force_review']}, thesis_broken={suggestions['suggest_thesis_broken']}。"
            "这只是 advisory-only 研究结论，用来帮助人工判断是否需要暂停新增、强制复核或讨论 thesis 是否接近失效，不会自动执行。"
        )

        notes = (
            f"Placeholder provider 已按 symbol-aware debate 模式输出。当前 debate 更强调 {profile.sector} 资产在长期定投系统中的研究含义，"
            "而不是预测短期涨跌。后续若接入真实 TradingAgents，可将 analyst inputs 替换为更丰富的数据和多 agent 交叉质询。"
        )

        recommendation_rationale = (
            f"最终给出 {label}，不是因为系统要自动交易，而是因为在当前 suggest 上下文、manual risk 信号和增强仓定位下，"
            f"bear 侧关于“{profile.key_uncertainty}”的约束程度 {'高于' if label != 'neutral_watch' else '尚未高于'} bull 侧继续保留观察的理由。"
            f"因此，本次更适合把研究结论服务于人工治理，而不是服务于直接买卖。"
        )

        return AgentResearchResult(
            symbol=symbol,
            analysis_date=analysis_date,
            bull_case=bull_case,
            bear_case=bear_case,
            risk_summary=risk_summary,
            final_research_label=label,
            suggest_manual_pause_buy=suggestions["suggest_manual_pause_buy"],
            suggest_force_review=suggestions["suggest_force_review"],
            suggest_thesis_broken=suggestions["suggest_thesis_broken"],
            confidence=confidence,
            notes=notes,
            bull_evidence_points=bull_points,
            bear_evidence_points=bear_points,
            bull_action_implication=bull_action,
            bear_action_implication=bear_action,
            debate_focus=profile.debate_focus,
            key_uncertainty=profile.key_uncertainty,
            recommendation_rationale=recommendation_rationale,
            source="tradingagents_poc",
        )

    def _build_etf_research(
        self,
        symbol: str,
        analysis_date: str,
        context: SuggestResearchContext,
    ) -> AgentResearchResult:
        role = ETF_ROLE_MAP.get(symbol, "ETF 底仓配置角色")
        amount_text = self._format_amount(context.suggested_amount)
        status = context.suggest_status or "GREEN"
        label = "neutral_watch"
        suggestions = self._map_label_to_manual_risk(label)

        bull_points = [
            f"配置角色：{symbol} 在组合中承担“{role}”职责，优先服务于资产配置纪律，而不是个股 alpha 辩论。",
            f"执行上下文：本月建议金额 {amount_text}，状态为 {status}，说明它当前更适合由既有价格红线和配置框架管理。",
            f"系统边界：ETF 是 {self._format_percent(self.etf_weight)} 主底仓的一部分，研究层只做轻量解释，不替代主配置逻辑。",
        ]
        bear_points = [
            f"风险信号：若 ETF 已进入 YELLOW/RED 或 manual review，则优先触发既有红线机制，而不是扩写 thesis debate。",
            "组合含义：ETF debate 不应像股票增强仓那样过度拟人化，因为它的主要职责是稳定配置而非主观选股。",
            "治理动作：若有暂停新增或复核需要，也应直接映射到风险治理动作，而不是放大研究措辞。",
        ]

        return AgentResearchResult(
            symbol=symbol,
            analysis_date=analysis_date,
            bull_case=(
                f"Bull researcher 对 {symbol} 的立场更偏中性配置派：它的价值在于维持“{role}”的长期配置功能。"
                f"本月建议金额为 {amount_text}，如果价格红线未进一步恶化，就没有必要把 ETF 底仓的研究讨论写成个股式 thesis 辩论。"
            ),
            bear_case=(
                f"Bear researcher 对 {symbol} 的提醒也偏治理层：如果价格红线、manual review 或新增限制已经出现，"
                "则应优先遵守现有风险框架，而不是通过更激进的研究表述改变底仓逻辑。"
            ),
            risk_summary=(
                "ETF monthly research 只提供角色说明和风险提示，不主动输出 thesis broken 风格结论。"
                "它依然是 advisory-only，用来解释配置角色，而不是替代既有 ETF 红线机制。"
            ),
            final_research_label=label,
            suggest_manual_pause_buy=suggestions["suggest_manual_pause_buy"],
            suggest_force_review=suggestions["suggest_force_review"],
            suggest_thesis_broken=suggestions["suggest_thesis_broken"],
            confidence=0.58,
            notes="ETF debate 在当前阶段保持简洁和中性，不扩展为股票式的高密度 thesis 辩论。",
            bull_evidence_points=bull_points,
            bear_evidence_points=bear_points,
            bull_action_implication="继续把 ETF 作为配置底仓来解释，优先遵循现有定投与红线规则。",
            bear_action_implication="若风险信号升级，则交给既有价格红线和人工复核流程，不由 research 层放大解释。",
            debate_focus="ETF 在组合中的配置角色是否需要被价格或人工风险信号临时压低新增资格。",
            key_uncertainty="风险信号是否已经强到需要暂停新增，而不是继续按常规定投推进。",
            recommendation_rationale="ETF 仍以配置纪律为先，因此研究层保持中性标签，只补充角色说明和风险提示。",
            source="tradingagents_poc",
        )

    def _get_stock_profile(self, symbol: str) -> StockDebateProfile:
        if symbol in STOCK_DEBATE_PROFILES:
            return STOCK_DEBATE_PROFILES[symbol]

        stock_pool = self.list_stock_pool()
        stock_meta = next((item for item in stock_pool if str(item.get("symbol")) == str(symbol)), None)
        if stock_meta is None:
            raise ValueError(
                f"symbol={symbol} 不在当前股票池中，TradingAgents PoC 仅支持股票增强仓研究。",
            )

        return StockDebateProfile(
            name=str(stock_meta.get("name") or symbol),
            sector="股票增强仓",
            role_in_portfolio="股票 20% 增强仓中的低频观察标的",
            bull_thesis=(
                "公司仍可能保留基本面修复或质量溢价的观察价值。",
                "若资金、盈利质量或行业位置没有进一步恶化，则不必急于从观察池中移除。",
                "在保守框架里，它仍可以继续作为研究覆盖对象。",
            ),
            bear_thesis=(
                "当前缺少足够强的证据证明新增是更优动作。",
                "一旦组合只给股票 20% 权重，证据不足本身就是偏空信号。",
                "研究更应服务于人工复核，而不是默认继续新增。",
            ),
            debate_focus="当前证据是否足以支持继续把它保留在股票增强仓候选池。",
            key_uncertainty="基本面验证与风险治理之间，哪一侧更应主导本月判断。",
        )

    def _decide_label(
        self,
        symbol: str,
        analysis_date: str,
        context: SuggestResearchContext,
    ) -> tuple[ResearchLabel, float]:
        """Decide a stable advisory label from system context plus a deterministic tie-breaker."""

        if context.thesis_broken:
            return "thesis_broken_candidate", 0.9
        if context.manual_force_review or context.suggest_status.upper() == "RED":
            return "force_review_candidate", 0.82
        if context.manual_pause_buy or context.pause_buy or context.suggest_status.upper() == "YELLOW":
            return "pause_candidate", 0.74

        digest = sha256(f"{symbol}|{analysis_date}".encode("utf-8")).hexdigest()
        score = int(digest[:8], 16) / 0xFFFFFFFF
        if score >= 0.83:
            return "force_review_candidate", 0.79
        if score >= 0.58:
            return "pause_candidate", 0.7
        return "neutral_watch", round(0.58 + (score * 0.16), 2)

    @staticmethod
    def _map_label_to_manual_risk(label: ResearchLabel) -> dict[str, bool]:
        """Map research label to advisory-only manual risk suggestions."""

        mapping: dict[ResearchLabel, dict[str, bool]] = {
            "neutral_watch": {
                "suggest_manual_pause_buy": False,
                "suggest_force_review": False,
                "suggest_thesis_broken": False,
            },
            "pause_candidate": {
                "suggest_manual_pause_buy": True,
                "suggest_force_review": False,
                "suggest_thesis_broken": False,
            },
            "force_review_candidate": {
                "suggest_manual_pause_buy": False,
                "suggest_force_review": True,
                "suggest_thesis_broken": False,
            },
            "thesis_broken_candidate": {
                "suggest_manual_pause_buy": False,
                "suggest_force_review": True,
                "suggest_thesis_broken": True,
            },
        }
        return mapping[label]

    @staticmethod
    def _normalize_context(context: dict[str, Any] | None) -> SuggestResearchContext:
        if not context:
            return SuggestResearchContext()
        return SuggestResearchContext(
            asset_type=str(context.get("asset_type") or "stock").lower(),
            suggested_amount=float(context.get("suggested_amount") or 0.0),
            target_weight=float(context.get("target_weight") or 0.0),
            current_weight=float(context.get("current_weight") or 0.0),
            suggest_status=str(context.get("suggest_status") or context.get("status") or ""),
            final_action=str(context.get("final_action") or context.get("final_human_readable_action") or ""),
            reasons=str(context.get("reasons") or ""),
            logic_note=str(context.get("logic_note") or ""),
            manual_pause_buy=bool(context.get("manual_pause_buy", False)),
            manual_force_review=bool(context.get("manual_force_review", False)),
            thesis_broken=bool(context.get("thesis_broken", False)),
            pause_buy=bool(context.get("pause_buy", False)),
            final_priority_level=(
                int(context.get("final_priority_level"))
                if context.get("final_priority_level") not in (None, "")
                else None
            ),
            final_reason_codes=str(context.get("final_reason_codes") or ""),
        )

    def _infer_asset_type(self, symbol: str) -> str:
        stock_symbols = {str(item.get("symbol")) for item in self.list_stock_pool()}
        return "stock" if str(symbol) in stock_symbols else "etf"

    @staticmethod
    def _format_amount(value: float) -> str:
        if not value:
            return "0 元"
        return f"{value:,.0f} 元"

    @staticmethod
    def _format_percent(value: float) -> str:
        return f"{value * 100:.0f}%"

    @staticmethod
    def _trim_reason(value: str, limit: int = 42) -> str:
        text = str(value or "").replace("\n", " ").strip()
        if not text:
            return "暂无额外说明"
        if len(text) <= limit:
            return text
        return f"{text[:limit - 3]}..."
