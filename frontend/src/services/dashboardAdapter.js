import { emptyDashboardData } from '../mock/latestData.js';
import { deepGet, firstDefined, isNonEmptyString } from '../utils/safeAccess.js';
import { loadSharedReportJson, loadSharedReportText } from './fileLoader.js';
import { buildCompareCardData, loadLatestCompareBundle } from './compareAdapter.js';
import { createEmptyRunBundle, loadLatestRunBundle } from './runAdapter.js';
import { readSnapshotJson } from './staticSnapshotLoader.js';

function cloneDefaultDashboardData() {
  return JSON.parse(JSON.stringify(emptyDashboardData));
}

function pickConfigSource(...bundles) {
  return bundles.find((bundle) => bundle?.configSnapshot) || createEmptyRunBundle();
}

function parseCsvLine(line) {
  const values = [];
  let current = '';
  let insideQuotes = false;

  for (let index = 0; index < line.length; index += 1) {
    const character = line[index];

    if (character === '"') {
      const nextCharacter = line[index + 1];
      if (insideQuotes && nextCharacter === '"') {
        current += '"';
        index += 1;
      } else {
        insideQuotes = !insideQuotes;
      }
      continue;
    }

    if (character === ',' && !insideQuotes) {
      values.push(current);
      current = '';
      continue;
    }

    current += character;
  }

  values.push(current);
  return values;
}

function parseCsvRows(csvText) {
  if (!csvText) {
    return [];
  }

  const lines = csvText
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);

  if (lines.length <= 1) {
    return [];
  }

  const headers = parseCsvLine(lines[0]);
  return lines.slice(1).map((line) => {
    const cells = parseCsvLine(line);
    return headers.reduce((row, header, index) => {
      row[header] = cells[index] ?? '';
      return row;
    }, {});
  });
}

function toDateSuffix(dateText) {
  if (!dateText) {
    return '';
  }
  return String(dateText).replace(/-/g, '');
}

function parseMarkdownScalar(markdownText, label) {
  if (!markdownText || !label) {
    return null;
  }

  const escapedLabel = label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const match = markdownText.match(new RegExp(`-\\s+${escapedLabel}:\\s+(.+)`));
  return match?.[1]?.trim() || null;
}

function parseBool(value) {
  if (typeof value === 'boolean') {
    return value;
  }
  if (typeof value === 'number') {
    return value !== 0;
  }
  if (typeof value === 'string') {
    return ['true', '1', 'yes', 'y'].includes(value.trim().toLowerCase());
  }
  return false;
}

function toNumberOrNull(value) {
  if (value === undefined || value === null || value === '') {
    return null;
  }
  const parsed = Number(value);
  return Number.isNaN(parsed) ? null : parsed;
}

function pickLatestDateFromContext(robustnessJson, researchIndex) {
  return firstDefined(
    deepGet(robustnessJson, 'baseline_configuration.backtest_end_date'),
    deepGet(robustnessJson, 'summary_context.end_date_argument'),
    deepGet(researchIndex, 'items.0.analysis_date'),
    '',
  );
}

function buildSharedReportBundle({
  monthlyReportMarkdown,
  monthlySuggestionCsv,
  riskStatusCsv,
  backtestReportMarkdown,
  backtestMetricsCsv,
  baselineSensitivityJson,
}) {
  return {
    monthlyReportMarkdown: monthlyReportMarkdown || '',
    monthlySuggestionRows: parseCsvRows(monthlySuggestionCsv),
    riskStatusRows: parseCsvRows(riskStatusCsv),
    backtestReportMarkdown: backtestReportMarkdown || '',
    backtestMetricsRows: parseCsvRows(backtestMetricsCsv),
    baselineMetrics: baselineSensitivityJson?.metrics || {},
  };
}

function readAllocationText(configSnapshot) {
  const etfWeight = deepGet(configSnapshot, 'portfolio.asset_allocation.etf_total_weight');
  const stockWeight = deepGet(configSnapshot, 'portfolio.asset_allocation.stock_total_weight');

  if (etfWeight === undefined || stockWeight === undefined) {
    return 'ETF 80% / Stock 20%';
  }

  return `ETF ${Math.round(Number(etfWeight) * 100)}% / Stock ${Math.round(Number(stockWeight) * 100)}%`;
}

function readMonthlyRule(configSnapshot) {
  const monthlyRule = firstDefined(
    deepGet(configSnapshot, 'app.schedule.monthly_invest_day_rule'),
    deepGet(configSnapshot, 'backtest.backtest.execution_rule'),
  );

  if (!monthlyRule) {
    return 'N/A';
  }

  if (monthlyRule === 'first_trading_day') {
    return 'First trading day';
  }

  if (monthlyRule === 'last_trading_day') {
    return 'Last trading day';
  }

  return monthlyRule;
}

function readRiskLevel(configSnapshot, assetType) {
  if (assetType === 'etf') {
    const yellow = deepGet(configSnapshot, 'risk.etf.yellow_drawdown_from_high');
    const red = deepGet(configSnapshot, 'risk.etf.red_drawdown_from_high');
    return yellow !== undefined && red !== undefined
      ? `Y ${Math.round(Number(yellow) * 100)}% / R ${Math.round(Number(red) * 100)}%`
      : 'N/A';
  }

  const yellow = deepGet(configSnapshot, 'risk.stock.yellow_drawdown_from_cost');
  const red = deepGet(configSnapshot, 'risk.stock.red_drawdown_from_cost');
  return yellow !== undefined && red !== undefined
    ? `Y ${Math.round(Number(yellow) * 100)}% / R ${Math.round(Number(red) * 100)}%`
    : 'N/A';
}

function buildManualRiskSummary(manualValidationJson, configSource) {
  const flags = manualValidationJson?.flags
    || Object.entries(deepGet(configSource, 'configSnapshot.manual_risk_flags_snapshot.manual_risk_flags.symbols', {})).map(
      ([symbol, payload]) => ({ symbol, ...payload }),
    );

  const paused = flags.filter((item) => item.manual_pause_buy).map((item) => item.symbol);
  const forceReview = flags.filter((item) => item.manual_force_review).map((item) => item.symbol);
  const thesisBroken = flags.filter((item) => item.thesis_broken).map((item) => item.symbol);
  const flaggedItems = flags.filter(
    (item) => item.manual_pause_buy || item.manual_force_review || item.thesis_broken,
  );
  const firstEffective = flaggedItems
    .map((item) => item.effective_from)
    .filter(Boolean)
    .sort()[0];
  const notePreview = flaggedItems.find((item) => isNonEmptyString(item.note))?.note
    || '当前 manual risk 配置未启用暂停新增或 thesis_broken 标记。';

  return {
    flags,
    paused,
    forceReview,
    thesisBroken,
    effectiveFrom: firstEffective || 'N/A',
    notePreview,
  };
}

function buildRiskLights(manualRiskSummary, backtestBundle, sharedReportBundle) {
  const totalTracked = manualRiskSummary.flags?.length || 0;
  const manualPauseCount = manualRiskSummary.paused.length;
  const forceReviewCount = manualRiskSummary.forceReview.length;
  const thesisBrokenCount = manualRiskSummary.thesisBroken.length;
  const yellowCount = Number(firstDefined(
    backtestBundle?.keySummary?.total_yellow_triggers,
    sharedReportBundle?.baselineMetrics?.total_yellow_triggers,
    0,
  ));
  const redCount = Number(firstDefined(
    backtestBundle?.keySummary?.total_red_triggers,
    sharedReportBundle?.baselineMetrics?.total_red_triggers,
    0,
  ));

  return {
    GREEN: Math.max(totalTracked - manualPauseCount - forceReviewCount - thesisBrokenCount, 0),
    YELLOW: yellowCount,
    RED: redCount,
    MANUAL_PAUSE: manualPauseCount,
    FORCE_REVIEW: forceReviewCount,
    THESIS_BROKEN: thesisBrokenCount,
  };
}

function buildSuggestSummary(suggestBundle, configSnapshot, manualRiskSummary, sharedReportBundle) {
  const suggestionRows = sharedReportBundle?.monthlySuggestionRows || [];
  const buyTargetsFromRows = suggestionRows.filter((row) => {
    const amount = toNumberOrNull(row.recommended_amount);
    return amount !== null && amount > 0;
  }).length;
  const pausedTargetsFromRows = suggestionRows.filter((row) => parseBool(row.pause_buy) || parseBool(row.final_pause_buy)).length;
  const forceReviewTargetsFromRows = suggestionRows.filter((row) => parseBool(row.manual_review) || parseBool(row.final_force_review)).length;
  const thesisBrokenTargetsFromRows = suggestionRows.filter((row) => parseBool(row.thesis_broken)).length;

  const totalBudget = firstDefined(
    suggestBundle?.keySummary?.total_budget,
    deepGet(configSnapshot, 'portfolio.portfolio.monthly_budget'),
    deepGet(configSnapshot, 'backtest.backtest.monthly_budget'),
    0,
  );
  const etfWeight = deepGet(configSnapshot, 'portfolio.asset_allocation.etf_total_weight', 0.8);
  const stockWeight = deepGet(configSnapshot, 'portfolio.asset_allocation.stock_total_weight', 0.2);

  return {
    budgetTotal: Number(firstDefined(totalBudget, 0)),
    budgetEtf: Number(firstDefined(totalBudget, 0)) * Number(firstDefined(etfWeight, 0)),
    budgetStock: Number(firstDefined(totalBudget, 0)) * Number(firstDefined(stockWeight, 0)),
    buyTargets: Number(firstDefined(suggestBundle?.keySummary?.symbols_to_buy_count, buyTargetsFromRows, 0)),
    pausedTargets: Number(firstDefined(suggestBundle?.keySummary?.paused_symbols_count, pausedTargetsFromRows, manualRiskSummary.paused.length, 0)),
    forceReviewTargets: Number(firstDefined(suggestBundle?.keySummary?.force_review_symbols_count, forceReviewTargetsFromRows, manualRiskSummary.forceReview.length, 0)),
    thesisBrokenTargets: Number(firstDefined(suggestBundle?.keySummary?.thesis_broken_symbols_count, thesisBrokenTargetsFromRows, manualRiskSummary.thesisBroken.length, 0)),
  };
}

function buildSuggestedTargets(sharedReportBundle) {
  const suggestionRows = sharedReportBundle?.monthlySuggestionRows || [];

  return suggestionRows.map((row) => {
    const baseSuggestedAmount = firstDefined(toNumberOrNull(row.recommended_amount), 0);
    const pauseBuy = parseBool(row.pause_buy) || parseBool(row.final_pause_buy) || parseBool(row.manual_pause_buy);
    const forceReview = parseBool(row.manual_review) || parseBool(row.final_force_review) || parseBool(row.manual_force_review);
    const thesisBroken = parseBool(row.thesis_broken);

    return {
      symbol: row.symbol || 'N/A',
      assetType: (row.asset_type || '').toUpperCase() || 'N/A',
      baseSuggestedAmount,
      action: row.final_human_readable_action || (pauseBuy ? 'Pause Buy' : 'Normal'),
      riskStatus: row.status || 'N/A',
      note: firstDefined(row.logic_note, row.reasons, ''),
      pauseBuy,
      forceReview,
      thesisBroken,
    };
  });
}

function buildBacktestSummary(backtestBundle, sharedReportBundle) {
  const summary = backtestBundle?.keySummary || {};
  const metricsRow = sharedReportBundle?.backtestMetricsRows?.[0] || {};
  const baselineMetrics = sharedReportBundle?.baselineMetrics || {};
  const cumulativeReturn = firstDefined(
    summary.cumulative_return,
    summary.total_return,
    toNumberOrNull(metricsRow.cumulative_return),
    toNumberOrNull(metricsRow.total_return),
    baselineMetrics.cumulative_return,
    baselineMetrics.total_return,
  );
  const annualizedReturn = firstDefined(
    summary.annualized_return,
    toNumberOrNull(metricsRow.annualized_return),
    baselineMetrics.annualized_return,
  );
  const maxDrawdown = firstDefined(
    summary.max_drawdown,
    toNumberOrNull(metricsRow.max_drawdown),
    baselineMetrics.max_drawdown,
  );
  const investedRatio = firstDefined(
    summary.invested_ratio,
    toNumberOrNull(metricsRow.invested_ratio),
    baselineMetrics.invested_ratio,
  );
  const unfilledAmount = firstDefined(
    summary.unfilled_amount,
    summary.total_uninvested_cash,
    toNumberOrNull(metricsRow.unfilled_amount),
    toNumberOrNull(metricsRow.total_uninvested_cash),
    baselineMetrics.unfilled_amount,
    baselineMetrics.total_uninvested_cash,
    0,
  );
  const yellowTriggers = firstDefined(
    summary.total_yellow_triggers,
    toNumberOrNull(metricsRow.total_yellow_triggers),
    baselineMetrics.total_yellow_triggers,
    0,
  );
  const redTriggers = firstDefined(
    summary.total_red_triggers,
    toNumberOrNull(metricsRow.total_red_triggers),
    baselineMetrics.total_red_triggers,
    0,
  );

  return {
    cumulativeReturn: cumulativeReturn ?? 'N/A',
    annualizedReturn: annualizedReturn ?? 'N/A',
    maxDrawdown: maxDrawdown ?? 'N/A',
    investedRatio: investedRatio ?? 'N/A',
    unfilledAmount: Number(unfilledAmount),
    yellowTriggers: Number(yellowTriggers),
    redTriggers: Number(redTriggers),
  };
}

function buildRobustnessSummary(robustnessJson) {
  const baselineLabel = deepGet(robustnessJson, 'baseline_assessment.label', '暂无数据');
  const highSensitive = deepGet(robustnessJson, 'parameter_classification.high_sensitive.0.family_label', 'N/A');
  const robust = deepGet(robustnessJson, 'parameter_classification.robust.0.family_label', 'N/A');
  const baselineRecommendation = deepGet(
    robustnessJson,
    'default_parameter_recommendations.baseline_default.label',
    '',
  );

  return {
    isBaselineRobust: /稳健|可用|保留/.test(String(baselineLabel)),
    keepDefaultParams: /保留/.test(String(baselineRecommendation)),
    mostSensitive: highSensitive,
    mostRobust: robust,
    label: baselineLabel,
  };
}

function buildOverview(latestIndex, bundles, compareBundle, configSource, manualValidationJson, sharedReportBundle) {
  const monthlyReportUpdatedAt = parseMarkdownScalar(sharedReportBundle?.monthlyReportMarkdown, '最近更新时间');
  const backtestReportUpdatedAt = parseMarkdownScalar(sharedReportBundle?.backtestReportMarkdown, '最近更新时间');
  const dataModeFromReport = firstDefined(
    parseMarkdownScalar(sharedReportBundle?.monthlyReportMarkdown, '数据模式'),
    parseMarkdownScalar(sharedReportBundle?.backtestReportMarkdown, '数据模式'),
  );
  const adjModeFromReport = firstDefined(
    parseMarkdownScalar(sharedReportBundle?.monthlyReportMarkdown, '当前复权模式'),
    parseMarkdownScalar(sharedReportBundle?.backtestReportMarkdown, '复权模式'),
  );

  return {
    latestSuggest: firstDefined(latestIndex?.suggest?.finished_at, monthlyReportUpdatedAt, 'N/A'),
    latestBacktest: firstDefined(latestIndex?.backtest?.finished_at, backtestReportUpdatedAt, 'N/A'),
    latestRobustness: latestIndex?.['summarize-robustness']?.finished_at || 'N/A',
    latestCompare: compareBundle?.latestCompareIndex?.compared_at || latestIndex?.['compare-runs']?.finished_at || 'N/A',
    mode: firstDefined(
      bundles.suggest?.manifest?.data_mode,
      bundles.backtest?.manifest?.data_mode,
      dataModeFromReport,
      deepGet(configSource, 'configSnapshot.sensitivity.sensitivity.data_mode'),
      'real',
    ),
    adjMode: firstDefined(
      bundles.suggest?.manifest?.adj_mode,
      bundles.backtest?.manifest?.adj_mode,
      adjModeFromReport,
      deepGet(configSource, 'configSnapshot.app.efinance.adjustment_mode'),
      'N/A',
    ),
    riskFileStatus: manualValidationJson
      ? (manualValidationJson.valid ? 'active' : 'invalid')
      : 'unknown',
  };
}

function buildConfigSummary(configSnapshot) {
  const manualRiskEnabled = Boolean(
    deepGet(configSnapshot, 'risk.risk.use_logic_redline')
      ?? deepGet(configSnapshot, 'risk.manual_logic')
      ?? deepGet(configSnapshot, 'manual_risk_flags_snapshot')
  );

  return {
    allocation: readAllocationText(configSnapshot),
    monthlyRule: readMonthlyRule(configSnapshot),
    etfRiskLevel: readRiskLevel(configSnapshot, 'etf'),
    stockRiskLevel: readRiskLevel(configSnapshot, 'stock'),
    manualRiskEnabled,
    env: `Local Archive / ${deepGet(configSnapshot, 'app.runtime.data_provider', 'N/A')}`,
  };
}

export async function getDashboardData() {
  const staticDashboardSnapshot = await readSnapshotJson('dashboard_snapshot.json');
  if (staticDashboardSnapshot?.dashboard_data) {
    return staticDashboardSnapshot.dashboard_data;
  }

  const latestIndex = await loadSharedReportJson('reports/runs/latest_index.json');
  const robustnessJsonPromise = loadSharedReportJson('reports/robustness_summary.json');
  const manualValidationJsonPromise = loadSharedReportJson('reports/manual/manual_risk_flags_validation.json');
  const researchIndexPromise = loadSharedReportJson('reports/agent_research/research_index.json');

  const [
    suggestBundle,
    backtestBundle,
    robustnessBundle,
    compareRunBundle,
    manualValidationBundle,
    compareBundle,
    robustnessJson,
    manualValidationJson,
    researchIndex,
  ] = await Promise.all([
    loadLatestRunBundle('suggest', latestIndex),
    loadLatestRunBundle('backtest', latestIndex),
    loadLatestRunBundle('summarize-robustness', latestIndex),
    loadLatestRunBundle('compare-runs', latestIndex),
    loadLatestRunBundle('validate-manual-risk-flags', latestIndex),
    loadLatestCompareBundle(),
    robustnessJsonPromise,
    manualValidationJsonPromise,
    researchIndexPromise,
  ]);

  const latestDate = toDateSuffix(pickLatestDateFromContext(robustnessJson, researchIndex));
  const [
    monthlyReportMarkdown,
    monthlySuggestionCsv,
    riskStatusCsv,
    backtestReportMarkdown,
    backtestMetricsCsv,
    baselineSensitivityJson,
  ] = await Promise.all([
    latestDate ? loadSharedReportText(`reports/monthly/monthly_report_${latestDate}.md`) : Promise.resolve(null),
    latestDate ? loadSharedReportText(`reports/monthly/monthly_suggestion_${latestDate}.csv`) : Promise.resolve(null),
    latestDate ? loadSharedReportText(`reports/monthly/risk_status_${latestDate}.csv`) : Promise.resolve(null),
    loadSharedReportText('reports/backtest/backtest_report.md'),
    loadSharedReportText('reports/backtest/metrics.csv'),
    loadSharedReportJson('reports/sensitivity_groups/baseline.json'),
  ]);

  const sharedReportBundle = buildSharedReportBundle({
    monthlyReportMarkdown,
    monthlySuggestionCsv,
    riskStatusCsv,
    backtestReportMarkdown,
    backtestMetricsCsv,
    baselineSensitivityJson,
  });

  const configSource = pickConfigSource(
    suggestBundle,
    backtestBundle,
    robustnessBundle,
    manualValidationBundle,
    compareRunBundle,
  );
  const manualRiskSummary = buildManualRiskSummary(manualValidationJson, configSource);

  return {
    overview: buildOverview(
      latestIndex,
      {
        suggest: suggestBundle,
        backtest: backtestBundle,
      },
      compareBundle,
      configSource,
      manualValidationJson,
      sharedReportBundle,
    ),
    configSummary: buildConfigSummary(configSource.configSnapshot),
    suggestSummary: buildSuggestSummary(
      suggestBundle,
      configSource.configSnapshot,
      manualRiskSummary,
      sharedReportBundle,
    ),
    suggestedTargets: buildSuggestedTargets(sharedReportBundle),
    backtestSummary: buildBacktestSummary(backtestBundle, sharedReportBundle),
    riskLights: buildRiskLights(manualRiskSummary, backtestBundle, sharedReportBundle),
    manualRisk: {
      paused: manualRiskSummary.paused,
      forceReview: manualRiskSummary.forceReview,
      thesisBroken: manualRiskSummary.thesisBroken,
      effectiveFrom: manualRiskSummary.effectiveFrom,
      notePreview: manualRiskSummary.notePreview,
    },
    robustness: buildRobustnessSummary(robustnessJson),
    compare: buildCompareCardData(compareBundle),
  };
}

export async function loadLatestDashboardSnapshot() {
  const dashboardData = cloneDefaultDashboardData();
  const realData = await getDashboardData();
  return {
    ...dashboardData,
    ...realData,
  };
}
