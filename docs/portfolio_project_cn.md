# 项目展示版说明（中文）

## 一句话介绍

一个面向中国 A 股 / 场内 ETF 长期定投场景的本地投研与风险复核工作台，支持真实归档、低频回测、人工风险标记与研究增强输出。

## 解决的问题

这个项目主要解决了长期投资场景中的三个问题：

1. 低频定投与资产配置建议缺少可追溯的工程化工具。
2. 风险提醒、人工复核、回测验证和研究结论往往散落在不同脚本或文档里。
3. 即使接入研究增强能力，也需要明确边界，避免它越过人工决策和主策略约束。

## 核心功能

- 真实行情数据接入、缓存、归档与校验
- 月度定投建议与低频回测
- 数据验证、回测一致性检查、敏感性测试、稳健性总结
- manual risk flags 与 acceptance / validation 流程
- run archive 与 run compare
- TradingAgents 研究增强层 PoC
- 只读前端工作台：Dashboard / Compare / Manual Risk / Research / Research vs Manual Risk

## 技术栈

- Python 3.11+
- pandas / numpy
- e-finance
- React + Vite + Tailwind
- i18next / react-i18next
- 文件系统归档（JSON / Markdown / CSV）

## 架构亮点

- 配置驱动：关键参数、红线阈值、执行规则都可配置
- 归档驱动：每次关键运行都会生成快照和可追溯产物
- 前后端解耦：前端通过 `/archive-data/...` 直接读取归档，不依赖额外 API 服务
- 适配层设计：Dashboard、Compare、Manual Risk、Research 都通过 adapter/hook 读取统一 shape

## 风控与可解释性亮点

- 明确区分价格红线与人工逻辑红线
- manual pause / force review / thesis broken 均可审计
- 风险逻辑默认以提醒、暂停新增、人工复核为主，不自动卖出
- 对比视图可以直接看到 research 建议与 manual risk 真实状态是否一致

## 前端工作台亮点

- 深色、克制、只读的投研面板风格
- 首页聚合最新运行、风险矩阵、Research 摘要与 Alignment 摘要
- 支持真实归档缺失时的降级展示
- 支持中英文切换

## TradingAgents PoC 亮点

- TradingAgents 被约束在研究增强层，不直接进入交易执行链路
- 输出 bull / bear / risk memo 与 suggest_* 候选标签
- 研究结果可进入归档，并在前端与 manual risk 状态做只读对照

## 我的个人贡献

我独立完成了项目的整体架构、Python 研究层、归档机制、验证与对比流程、前端适配层与只读工作台集成，并明确限制了研究增强层的职责边界，使其只作为人工决策辅助而不是自动执行模块。

## 当前边界与限制

- 当前不是自动交易系统
- 不接自动下单
- 不做高频/分钟级策略
- 不做自动卖出
- TradingAgents 目前仍是 PoC 级研究增强层
- 前端主要用于归档回看与人工复核，不负责计算主策略