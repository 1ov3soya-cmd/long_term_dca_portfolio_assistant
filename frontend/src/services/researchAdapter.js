import {
  loadLatestRunsIndex,
  loadSharedReportJson,
  readArchiveJson,
  readArchiveText,
} from './fileLoader.js';
import { loadLatestRunBundle } from './runAdapter.js';
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

function createEmptyResearchData() {
  return {
    empty: true,
    partial: false,
    meta: {
      sourceType: 'empty',
      updatedAt: '',
      totalItems: 0,
      latestSymbol: '',
      latestAnalysisDate: '',
    },
    summary: {
      totalCount: 0,
      pauseCandidateCount: 0,
      forceReviewCandidateCount: 0,
      thesisBrokenCandidateCount: 0,
      averageConfidence: 0,
    },
    items: [],
    files: {
      available: [],
      missing: [],
    },
  };
}

function buildFallbackRefFromLatestRun(latestRunBundle) {
  if (!latestRunBundle?.exists) {
    return [];
  }

  const keySummary = latestRunBundle.keySummary || {};
  const artifactRoot = latestRunBundle.outputArtifacts?.original_outputs || latestRunBundle.outputArtifacts || {};
  const artifactPaths = artifactRoot.agent_research || {};
  const jsonRelativePath = normalizePath(artifactPaths.json);
  const markdownRelativePath = normalizePath(artifactPaths.markdown);

  if (!jsonRelativePath && !markdownRelativePath) {
    return [];
  }

  return [
    {
      symbol: keySummary.symbol || '',
      analysis_date: keySummary.analysis_date || latestRunBundle.manifest?.end_date || '',
      final_research_label: keySummary.final_research_label || '',
      suggest_manual_pause_buy: Boolean(keySummary.suggest_manual_pause_buy),
      suggest_force_review: Boolean(keySummary.suggest_force_review),
      suggest_thesis_broken: Boolean(keySummary.suggest_thesis_broken),
      confidence: Number(keySummary.confidence || 0),
      source: keySummary.source || latestRunBundle.manifest?.provider_name || '',
      json_relative_path: jsonRelativePath,
      markdown_relative_path: markdownRelativePath,
      source_run_id: latestRunBundle.runId || latestRunBundle.manifest?.run_id || '',
      updated_at: latestRunBundle.latestEntry?.finished_at || latestRunBundle.manifest?.finished_at || '',
    },
  ];
}

function memoPreview(text, lines = 24) {
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

function buildAnalystDebate(detailJson = {}) {
  const bullSummary = sanitizeDebateText(detailJson.bull_case || '', { removeRoleOpening: true });
  const bearSummary = sanitizeDebateText(detailJson.bear_case || '', { removeRoleOpening: true });
  const riskSummary = sanitizeDebateText(detailJson.risk_summary || '');
  return {
    debateFocus: sanitizeDebateText(detailJson.debate_focus || ''),
    keyUncertainty: sanitizeDebateText(detailJson.key_uncertainty || ''),
    recommendationRationale: sanitizeDebateText(detailJson.recommendation_rationale || ''),
    bull: {
      summary: bullSummary,
      summaryPreview: buildDebatePreview(bullSummary, 120),
      evidencePoints: normalizeEvidencePoints(detailJson.bull_evidence_points),
      actionImplication: sanitizeDebateText(detailJson.bull_action_implication || ''),
    },
    bear: {
      summary: bearSummary,
      summaryPreview: buildDebatePreview(bearSummary, 120),
      evidencePoints: normalizeEvidencePoints(detailJson.bear_evidence_points),
      actionImplication: sanitizeDebateText(detailJson.bear_action_implication || ''),
    },
    riskSummary,
    riskSummaryPreview: buildDebatePreview(riskSummary, 130),
  };
}

function buildSymbolNameMap(portfolioConfig) {
  return mergeSymbolNameMaps(buildSymbolNameMapFromPortfolioConfig(portfolioConfig));
}

function latestItem(items) {
  if (!items.length) {
    return null;
  }
  return [...items].sort((left, right) => {
    const leftKey = `${left.analysisDate || ''}|${left.updatedAt || ''}|${left.symbol || ''}`;
    const rightKey = `${right.analysisDate || ''}|${right.updatedAt || ''}|${right.symbol || ''}`;
    return rightKey.localeCompare(leftKey);
  })[0];
}

function normalizeMonthlyResearchPath(indexJson = {}) {
  const latest = indexJson?.latest || {};
  return normalizePath(latest.items_relative_path);
}

async function loadMonthlyEtfFallbackItems(symbolNameMap) {
  const monthlyIndex = await loadSharedReportJson('reports/agent_research/monthly/latest_monthly_research_index.json');
  const itemsPath = normalizeMonthlyResearchPath(monthlyIndex);
  if (!itemsPath) {
    return [];
  }

  const itemsJson = await readArchiveJson(itemsPath);
  const monthlyItems = Array.isArray(itemsJson?.items) ? itemsJson.items : [];
  if (monthlyItems.length === 0) {
    return [];
  }

  const generatedAt = String(monthlyIndex?.updated_at || '').split(' ')[0] || 'N/A';
  return monthlyItems
    .filter((item) => String(item?.asset_type || '').toLowerCase() === 'etf')
    .map((item) => {
      const symbol = String(item.symbol || 'N/A');
      const displayName = pickDisplayName(
        symbol,
        [
          item?.name,
          item?.symbol_name,
          item?.company_name,
          item?.display_name,
          item?.security_name,
          item?.cn_name,
        ],
        symbolNameMap,
      );
      const etfPreviewPack = buildEtfDebatePreviewPack({
        symbol,
        displayName,
        suggestedAmount: Number(item.suggested_amount ?? 0),
      });
      const analystDebate = buildAnalystDebate(item);

      return {
        id: `monthly-etf-${symbol}-${generatedAt}`,
        symbol,
        displayName,
        fullTitle: buildSymbolDisplayTitle(symbol, displayName),
        analysisDate: generatedAt,
        finalResearchLabel: item?.final_research_label || 'N/A',
        suggestPauseBuy: Boolean(item?.suggest_manual_pause_buy),
        suggestForceReview: Boolean(item?.suggest_force_review),
        suggestThesisBroken: Boolean(item?.suggest_thesis_broken),
        confidence: Number(item?.confidence ?? 0),
        source: item?.source || 'tradingagents_poc',
        sourceRun: item?.source_research_run || monthlyIndex?.latest?.batch_id || '',
        memoAvailable: false,
        bullCase: analystDebate.bull.summary,
        bearCase: analystDebate.bear.summary,
        riskSummary: analystDebate.riskSummary,
        bullCaseFull: analystDebate.bull.summary,
        bearCaseFull: analystDebate.bear.summary,
        riskSummaryFull: analystDebate.riskSummary,
        bullCasePreview: etfPreviewPack.bullPreview,
        bearCasePreview: etfPreviewPack.bearPreview,
        riskSummaryPreview: etfPreviewPack.riskPreview,
        debateFocus: analystDebate.debateFocus,
        keyUncertainty: analystDebate.keyUncertainty,
        bullEvidencePoints: analystDebate.bull.evidencePoints,
        bearEvidencePoints: analystDebate.bear.evidencePoints,
        bullActionImplication: analystDebate.bull.actionImplication,
        bearActionImplication: analystDebate.bear.actionImplication,
        recommendationRationale: analystDebate.recommendationRationale,
        analystDebate: {
          ...analystDebate,
          bull: {
            ...analystDebate.bull,
            summaryPreview: etfPreviewPack.bullPreview,
          },
          bear: {
            ...analystDebate.bear,
            summaryPreview: etfPreviewPack.bearPreview,
          },
          riskSummaryPreview: etfPreviewPack.riskPreview,
        },
        notes: sanitizeDebateText(item?.note || ''),
        memoPreview: '',
        archivePaths: {
          json: itemsPath,
          markdown: '',
        },
        updatedAt: monthlyIndex?.updated_at || '',
        missing: {
          json: false,
          markdown: true,
        },
      };
    });
}

/**
 * 读取 TradingAgents PoC 的研究归档，并映射成前端页面直接消费的结构。
 */
export async function loadResearchPageData() {
  const latestRunsIndex = await loadLatestRunsIndex();
  const [researchIndex, latestRunBundle, portfolioConfig] = await Promise.all([
    loadSharedReportJson('reports/agent_research/research_index.json'),
    loadLatestRunBundle('run-agent-research', latestRunsIndex),
    loadSharedReportJson('config/portfolio_config.json'),
  ]);
  const symbolNameMap = buildSymbolNameMap(portfolioConfig);

  const indexItems = Array.isArray(researchIndex?.items) ? researchIndex.items : [];
  const itemRefs = indexItems.length > 0 ? indexItems : buildFallbackRefFromLatestRun(latestRunBundle);

  if (itemRefs.length === 0) {
    return createEmptyResearchData();
  }

  const resolvedItems = await Promise.all(
    itemRefs.map(async (itemRef) => {
      const jsonRelativePath = normalizePath(itemRef.json_relative_path);
      const markdownRelativePath = normalizePath(itemRef.markdown_relative_path);
      const [detailJson, memoMarkdown] = await Promise.all([
        jsonRelativePath ? readArchiveJson(jsonRelativePath) : Promise.resolve(null),
        markdownRelativePath ? readArchiveText(markdownRelativePath) : Promise.resolve(null),
      ]);

      const analystDebate = buildAnalystDebate(detailJson || {});
      const bullCaseFull = analystDebate.bull.summary;
      const bearCaseFull = analystDebate.bear.summary;
      const riskSummaryFull = analystDebate.riskSummary;

      return {
        displayName: pickDisplayName(
          detailJson?.symbol || itemRef.symbol,
          [
            detailJson?.name,
            detailJson?.symbol_name,
            detailJson?.company_name,
            detailJson?.display_name,
            detailJson?.security_name,
            detailJson?.cn_name,
            itemRef?.name,
            itemRef?.symbol_name,
          ],
          symbolNameMap,
        ),
        id: `${itemRef.symbol || detailJson?.symbol || 'unknown'}-${itemRef.analysis_date || detailJson?.analysis_date || 'na'}`,
        symbol: detailJson?.symbol || itemRef.symbol || 'N/A',
        analysisDate: detailJson?.analysis_date || itemRef.analysis_date || 'N/A',
        finalResearchLabel: detailJson?.final_research_label || itemRef.final_research_label || 'N/A',
        suggestPauseBuy: Boolean(
          detailJson?.suggest_manual_pause_buy ?? itemRef.suggest_manual_pause_buy,
        ),
        suggestForceReview: Boolean(
          detailJson?.suggest_force_review ?? itemRef.suggest_force_review,
        ),
        suggestThesisBroken: Boolean(
          detailJson?.suggest_thesis_broken ?? itemRef.suggest_thesis_broken,
        ),
        confidence: Number(detailJson?.confidence ?? itemRef.confidence ?? 0),
        source: detailJson?.source || itemRef.source || '',
        sourceRun: itemRef.source_run_id || latestRunBundle?.runId || '',
        memoAvailable: Boolean(memoMarkdown),
        bullCase: bullCaseFull,
        bearCase: bearCaseFull,
        riskSummary: riskSummaryFull,
        bullCaseFull,
        bearCaseFull,
        riskSummaryFull,
        bullCasePreview: analystDebate.bull.summaryPreview,
        bearCasePreview: analystDebate.bear.summaryPreview,
        riskSummaryPreview: analystDebate.riskSummaryPreview,
        debateFocus: analystDebate.debateFocus,
        keyUncertainty: analystDebate.keyUncertainty,
        bullEvidencePoints: analystDebate.bull.evidencePoints,
        bearEvidencePoints: analystDebate.bear.evidencePoints,
        bullActionImplication: analystDebate.bull.actionImplication,
        bearActionImplication: analystDebate.bear.actionImplication,
        recommendationRationale: analystDebate.recommendationRationale,
        analystDebate,
        notes: sanitizeDebateText(detailJson?.notes || ''),
        memoPreview: memoPreview(memoMarkdown),
        archivePaths: {
          json: jsonRelativePath,
          markdown: markdownRelativePath,
        },
        updatedAt: itemRef.updated_at || researchIndex?.updated_at || latestRunBundle?.latestEntry?.finished_at || '',
        missing: {
          json: !detailJson,
          markdown: !memoMarkdown,
        },
      };
    }),
  );

  const monthlyEtfItems = await loadMonthlyEtfFallbackItems(symbolNameMap);

  const mergedItems = [
    ...resolvedItems,
    ...monthlyEtfItems.filter(
      (candidate) => !resolvedItems.some((item) => item.symbol === candidate.symbol),
    ),
  ];

  const itemsWithTitle = mergedItems.map((item) => ({
    ...item,
    fullTitle: buildSymbolDisplayTitle(item.symbol, item.displayName),
  }));

  const missingFiles = [];
  mergedItems.forEach((item) => {
    if (item.missing.json && item.archivePaths.json) {
      missingFiles.push(item.archivePaths.json);
    }
    if (item.missing.markdown && item.archivePaths.markdown) {
      missingFiles.push(item.archivePaths.markdown);
    }
  });

  const latest = latestItem(itemsWithTitle);
  const totalCount = itemsWithTitle.length;
  const averageConfidence = totalCount > 0
    ? itemsWithTitle.reduce((sum, item) => sum + Number(item.confidence || 0), 0) / totalCount
    : 0;

  return {
    empty: false,
    partial: missingFiles.length > 0,
    meta: {
      sourceType: indexItems.length > 0 ? 'researchIndex' : 'latestRunFallback',
      updatedAt: researchIndex?.updated_at || latestRunBundle?.latestEntry?.finished_at || '',
      totalItems: totalCount,
      latestSymbol: latest?.symbol || '',
      latestAnalysisDate: latest?.analysisDate || '',
    },
    summary: {
      totalCount,
      pauseCandidateCount: itemsWithTitle.filter((item) => item.finalResearchLabel === 'pause_candidate').length,
      forceReviewCandidateCount: itemsWithTitle.filter((item) => item.finalResearchLabel === 'force_review_candidate').length,
      thesisBrokenCandidateCount: itemsWithTitle.filter((item) => item.finalResearchLabel === 'thesis_broken_candidate').length,
      averageConfidence,
    },
    items: itemsWithTitle,
    files: {
      available: [
        ...(researchIndex ? ['reports/agent_research/research_index.json'] : []),
        ...itemsWithTitle.flatMap((item) => Object.values(item.archivePaths).filter(Boolean)),
      ],
      missing: missingFiles,
    },
  };
}
