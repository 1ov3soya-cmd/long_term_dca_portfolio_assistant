import {
  loadLatestRunsIndex,
  loadSharedReportJson,
  readArchiveJson,
  readArchiveText,
} from './fileLoader.js';
import { loadLatestRunBundle } from './runAdapter.js';
import { readSnapshotJson } from './staticSnapshotLoader.js';
import {
  buildSymbolDisplayTitle,
  buildSymbolNameMapFromPortfolioConfig,
  mergeSymbolNameMaps,
  pickDisplayName,
} from '../utils/symbolDisplayMap.js';
import {
  buildDebatePreview,
  buildEtfDebatePreviewPack,
  sanitizeDebateText,
} from '../utils/debateText.js';

function normalizePath(value) {
  if (!value) {
    return '';
  }

  const normalized = String(value).replace(/\\/g, '/');
  if (normalized.startsWith('reports/') || normalized.startsWith('config/')) {
    return normalized;
  }

  const reportsIndex = normalized.indexOf('/reports/');
  if (reportsIndex >= 0) {
    return normalized.slice(reportsIndex + 1);
  }

  const configIndex = normalized.indexOf('/config/');
  if (configIndex >= 0) {
    return normalized.slice(configIndex + 1);
  }

  return '';
}

function emptyMonthlyResearchData() {
  return {
    empty: true,
    partial: false,
    meta: {
      sourceType: 'empty',
      updatedAt: '',
      batchId: '',
      sourceSuggestRun: '',
      totalItems: 0,
    },
    summary: {
      totalTargets: 0,
      processedTargets: 0,
      pauseCandidateCount: 0,
      forceReviewCandidateCount: 0,
      thesisBrokenCandidateCount: 0,
      averageConfidence: 0,
      topAttentionSymbols: [],
    },
    dashboardSummary: {
      featuredItems: [],
    },
    items: [],
    reportPreview: '',
    files: {
      available: [],
      missing: [],
    },
  };
}

function fallbackRefFromLatestRun(bundle) {
  if (!bundle?.exists) {
    return null;
  }

  const artifactRoot = bundle.outputArtifacts?.original_outputs || bundle.outputArtifacts || {};
  const monthlyResearch = artifactRoot.monthly_research || {};
  const summaryPath = normalizePath(monthlyResearch.monthly_research_summary);
  const itemsPath = normalizePath(monthlyResearch.debate_items);
  const reportPath = normalizePath(monthlyResearch.monthly_research_report);
  const manifestPath = normalizePath(monthlyResearch.batch_manifest);

  if (!summaryPath && !itemsPath) {
    return null;
  }

  return {
    updated_at: bundle.latestEntry?.finished_at || bundle.manifest?.finished_at || '',
    latest: {
      batch_id: bundle.runId || bundle.manifest?.run_id || '',
      source_suggest_run: bundle.keySummary?.source_suggest_run || '',
      source_type: 'latestRunFallback',
      summary_relative_path: summaryPath,
      items_relative_path: itemsPath,
      report_relative_path: reportPath,
      manifest_relative_path: manifestPath,
      summary: bundle.keySummary || {},
    },
  };
}

function previewMarkdown(text, lines = 28) {
  if (!text) {
    return '';
  }
  return text.split(/\r?\n/).slice(0, lines).join('\n').trim();
}

function normalizeEvidencePoints(value) {
  if (!Array.isArray(value)) {
    return [];
  }
  return value
    .map((item) => String(item || '').trim())
    .filter((item) => item.length > 0);
}

function normalizeItem(item = {}) {
  const bullCaseFull = sanitizeDebateText(item.bull_case || '', { removeRoleOpening: true });
  const bearCaseFull = sanitizeDebateText(item.bear_case || '', { removeRoleOpening: true });
  const riskSummaryFull = sanitizeDebateText(item.risk_summary || '');
  const bullEvidencePoints = normalizeEvidencePoints(item.bull_evidence_points);
  const bearEvidencePoints = normalizeEvidencePoints(item.bear_evidence_points);
  const bullActionImplication = sanitizeDebateText(item.bull_action_implication || '');
  const bearActionImplication = sanitizeDebateText(item.bear_action_implication || '');
  const debateFocus = sanitizeDebateText(item.debate_focus || '');
  const keyUncertainty = sanitizeDebateText(item.key_uncertainty || '');
  const recommendationRationale = sanitizeDebateText(item.recommendation_rationale || '');

  return {
    id: `${item.symbol || 'unknown'}-${item.source_research_run || item.source_suggest_run || 'na'}`,
    symbol: item.symbol || 'N/A',
    displayName: '',
    fullTitle: '',
    assetType: item.asset_type || 'N/A',
    suggestedAmount: Number(item.suggested_amount ?? 0),
    bullCase: bullCaseFull,
    bearCase: bearCaseFull,
    riskSummary: riskSummaryFull,
    bullCaseFull,
    bearCaseFull,
    riskSummaryFull,
    bullCasePreview: buildDebatePreview(bullCaseFull, 120),
    bearCasePreview: buildDebatePreview(bearCaseFull, 120),
    riskSummaryPreview: buildDebatePreview(riskSummaryFull, 130),
    bullEvidencePoints,
    bearEvidencePoints,
    bullActionImplication,
    bearActionImplication,
    debateFocus,
    keyUncertainty,
    recommendationRationale,
    analystDebate: {
      debateFocus,
      keyUncertainty,
      recommendationRationale,
      bull: {
        summary: bullCaseFull,
        summaryPreview: buildDebatePreview(bullCaseFull, 120),
        evidencePoints: bullEvidencePoints,
        actionImplication: bullActionImplication,
      },
      bear: {
        summary: bearCaseFull,
        summaryPreview: buildDebatePreview(bearCaseFull, 120),
        evidencePoints: bearEvidencePoints,
        actionImplication: bearActionImplication,
      },
      riskSummary: riskSummaryFull,
      riskSummaryPreview: buildDebatePreview(riskSummaryFull, 130),
    },
    finalResearchLabel: item.final_research_label || 'N/A',
    suggestPauseBuy: Boolean(item.suggest_manual_pause_buy),
    suggestForceReview: Boolean(item.suggest_force_review),
    suggestThesisBroken: Boolean(item.suggest_thesis_broken),
    confidence: Number(item.confidence ?? 0),
    note: item.note || '',
    suggestActionText: item.suggest_action_text || '',
    sourceSuggestRun: item.source_suggest_run || '',
    sourceResearchRun: item.source_research_run || '',
    source: item.source || '',
    rawNameCandidates: [
      item.name,
      item.symbol_name,
      item.company_name,
      item.display_name,
      item.security_name,
      item.cn_name,
    ],
  };
}

function extractItems(payload) {
  if (Array.isArray(payload)) {
    return payload;
  }
  if (Array.isArray(payload?.items)) {
    return payload.items;
  }
  if (Array.isArray(payload?.debate_items)) {
    return payload.debate_items;
  }
  return [];
}

function enrichDisplayName(item, symbolNameMap) {
  const displayName = pickDisplayName(
    item.symbol,
    item.rawNameCandidates || [],
    symbolNameMap,
  );

  const { rawNameCandidates, ...rest } = item;
  const etfPreviewPack = String(rest.assetType || '').toLowerCase() === 'etf'
    ? buildEtfDebatePreviewPack({
      symbol: rest.symbol,
      displayName,
      suggestedAmount: rest.suggestedAmount,
    })
    : null;

  return {
    ...rest,
    displayName,
    fullTitle: buildSymbolDisplayTitle(item.symbol, displayName),
    bullCasePreview: etfPreviewPack?.bullPreview || rest.bullCasePreview,
    bearCasePreview: etfPreviewPack?.bearPreview || rest.bearCasePreview,
    riskSummaryPreview: etfPreviewPack?.riskPreview || rest.riskSummaryPreview,
  };
}

function shortenText(value, maxLength = 120) {
  const normalized = String(value || '').replace(/\s+/g, ' ').trim();
  if (!normalized) {
    return '';
  }
  if (normalized.length <= maxLength) {
    return normalized;
  }
  return `${normalized.slice(0, maxLength - 3)}...`;
}

function itemPriority(item) {
  if (item.suggestThesisBroken) {
    return 'high';
  }
  if (item.suggestForceReview) {
    return 'medium';
  }
  if (item.suggestPauseBuy) {
    return 'medium';
  }
  return 'low';
}

function buildFeaturedItems(items, topAttentionSymbols) {
  const topSet = new Set(topAttentionSymbols || []);
  const ordered = [...items].sort((left, right) => {
    const leftAttention = topSet.has(left.symbol) ? 0 : 1;
    const rightAttention = topSet.has(right.symbol) ? 0 : 1;
    if (leftAttention !== rightAttention) {
      return leftAttention - rightAttention;
    }

    const priorityOrder = { high: 0, medium: 1, low: 2 };
    const priorityDiff = priorityOrder[itemPriority(left)] - priorityOrder[itemPriority(right)];
    if (priorityDiff !== 0) {
      return priorityDiff;
    }

    return Number(right.confidence || 0) - Number(left.confidence || 0);
  });

  return ordered.slice(0, 3).map((item) => ({
    symbol: item.symbol,
    displayName: item.displayName || '',
    fullTitle: item.fullTitle || item.symbol,
    assetType: item.assetType,
    suggestedAmount: item.suggestedAmount,
    finalResearchLabel: item.finalResearchLabel,
    confidence: item.confidence,
    bullCaseShort: shortenText(item.bullCasePreview || item.bullCase, 96),
    bearCaseShort: shortenText(item.bearCasePreview || item.bearCase, 96),
    riskSummaryShort: shortenText(item.riskSummaryPreview || item.riskSummary, 110),
    priority: itemPriority(item),
  }));
}

export async function loadMonthlyResearchPageData() {
  const staticSnapshot = await readSnapshotJson('monthly_research_snapshot.json');
  if (staticSnapshot && (Array.isArray(staticSnapshot.debate_items) || staticSnapshot.summary)) {
    const portfolioConfig = await loadSharedReportJson('config/portfolio_config.json');
    const symbolNameMap = mergeSymbolNameMaps(buildSymbolNameMapFromPortfolioConfig(portfolioConfig));
    const summaryPayload = staticSnapshot.summary || {};
    const items = extractItems(staticSnapshot.debate_items)
      .map(normalizeItem)
      .map((item) => enrichDisplayName(item, symbolNameMap));
    const topAttentionSymbols = Array.isArray(summaryPayload.top_attention_symbols)
      ? summaryPayload.top_attention_symbols
      : [];

    return {
      empty: items.length === 0 && !summaryPayload.batch_id,
      partial: false,
      meta: {
        sourceType: staticSnapshot.source_files ? 'staticSnapshot' : 'monthlyResearchSnapshot',
        updatedAt: staticSnapshot.generated_at || summaryPayload.generated_at || '',
        batchId: summaryPayload.batch_id || staticSnapshot.batch_meta?.batch_id || '',
        sourceSuggestRun: summaryPayload.source_suggest_run || staticSnapshot.batch_meta?.source_suggest_run || '',
        totalItems: items.length,
        generatedAt: summaryPayload.generated_at || staticSnapshot.generated_at || '',
      },
      summary: {
        totalTargets: Number(summaryPayload.total_targets ?? items.length),
        processedTargets: Number(summaryPayload.processed_targets ?? items.length),
        pauseCandidateCount: Number(summaryPayload.pause_candidate_count ?? 0),
        forceReviewCandidateCount: Number(summaryPayload.force_review_candidate_count ?? 0),
        thesisBrokenCandidateCount: Number(summaryPayload.thesis_broken_candidate_count ?? 0),
        averageConfidence: Number(summaryPayload.average_confidence ?? 0),
        topAttentionSymbols,
      },
      dashboardSummary: {
        featuredItems: buildFeaturedItems(items, topAttentionSymbols),
      },
      items,
      reportPreview: previewMarkdown(staticSnapshot.report_preview || ''),
      files: {
        available: Object.values(staticSnapshot.source_files || {}).filter(Boolean),
        missing: [],
      },
      manifest: staticSnapshot.batch_meta || {},
    };
  }

  const latestRunsIndex = await loadLatestRunsIndex();
  const [latestIndex, latestRunBundle, portfolioConfig] = await Promise.all([
    loadSharedReportJson('reports/agent_research/monthly/latest_monthly_research_index.json'),
    loadLatestRunBundle('run-monthly-research', latestRunsIndex),
    loadSharedReportJson('config/portfolio_config.json'),
  ]);
  const symbolNameMap = mergeSymbolNameMaps(buildSymbolNameMapFromPortfolioConfig(portfolioConfig));

  const resolvedIndex = latestIndex?.latest ? latestIndex : fallbackRefFromLatestRun(latestRunBundle);
  if (!resolvedIndex?.latest) {
    return emptyMonthlyResearchData();
  }

  const latest = resolvedIndex.latest;
  const summaryPath = normalizePath(latest.summary_relative_path);
  const itemsPath = normalizePath(latest.items_relative_path);
  const reportPath = normalizePath(latest.report_relative_path);
  const manifestPath = normalizePath(latest.manifest_relative_path);

  const [summaryJson, itemsJson, reportMarkdown, manifestJson] = await Promise.all([
    summaryPath ? readArchiveJson(summaryPath) : Promise.resolve(null),
    itemsPath ? readArchiveJson(itemsPath) : Promise.resolve(null),
    reportPath ? readArchiveText(reportPath) : Promise.resolve(null),
    manifestPath ? readArchiveJson(manifestPath) : Promise.resolve(null),
  ]);

  const items = Array.isArray(itemsJson?.items)
    ? itemsJson.items.map(normalizeItem).map((item) => enrichDisplayName(item, symbolNameMap))
    : [];
  const summaryPayload = summaryJson || latest.summary || {};
  const missing = [];
  if (summaryPath && !summaryJson) {
    missing.push(summaryPath);
  }
  if (itemsPath && !itemsJson) {
    missing.push(itemsPath);
  }
  if (reportPath && !reportMarkdown) {
    missing.push(reportPath);
  }
  if (manifestPath && !manifestJson) {
    missing.push(manifestPath);
  }

  return {
    empty: false,
    partial: missing.length > 0,
    meta: {
      sourceType: latest.source_type || 'monthlyResearchIndex',
      updatedAt: resolvedIndex.updated_at || summaryPayload.generated_at || latestRunBundle?.latestEntry?.finished_at || '',
      batchId: summaryPayload.batch_id || latest.batch_id || '',
      sourceSuggestRun: summaryPayload.source_suggest_run || latest.source_suggest_run || '',
      totalItems: items.length,
      generatedAt: summaryPayload.generated_at || '',
    },
    summary: {
      totalTargets: Number(summaryPayload.total_targets ?? items.length),
      processedTargets: Number(summaryPayload.processed_targets ?? items.length),
      pauseCandidateCount: Number(summaryPayload.pause_candidate_count ?? 0),
      forceReviewCandidateCount: Number(summaryPayload.force_review_candidate_count ?? 0),
      thesisBrokenCandidateCount: Number(summaryPayload.thesis_broken_candidate_count ?? 0),
      averageConfidence: Number(summaryPayload.average_confidence ?? 0),
      topAttentionSymbols: Array.isArray(summaryPayload.top_attention_symbols)
        ? summaryPayload.top_attention_symbols
        : [],
    },
    dashboardSummary: {
      featuredItems: buildFeaturedItems(
        items,
        Array.isArray(summaryPayload.top_attention_symbols) ? summaryPayload.top_attention_symbols : [],
      ),
    },
    items,
    reportPreview: previewMarkdown(reportMarkdown),
    files: {
      available: [summaryPath, itemsPath, reportPath, manifestPath].filter(Boolean),
      missing,
    },
    manifest: manifestJson,
  };
}
