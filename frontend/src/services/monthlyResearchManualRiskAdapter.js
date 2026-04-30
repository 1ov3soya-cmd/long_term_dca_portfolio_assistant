import { loadManualRiskPageData } from './manualRiskAdapter.js';
import { loadMonthlyResearchPageData } from './monthlyResearchAdapter.js';

const ALIGNMENT_TOP_SYMBOLS_LIMIT = 3;
const PRIORITY_LEVEL = {
  HIGH: 'high',
  MEDIUM: 'medium',
  LOW: 'low',
};

function createEmptyData() {
  return {
    empty: true,
    partial: false,
    meta: {
      batchId: '',
      sourceSuggestRun: '',
      updatedAt: '',
      totalResearchTargets: 0,
      monthlySourceType: 'empty',
      manualSourceType: 'empty',
    },
    summary: {
      pauseCandidateCount: 0,
      forceReviewCandidateCount: 0,
      thesisBrokenCandidateCount: 0,
      matchedCount: 0,
      unmatchedCount: 0,
      highPriorityCount: 0,
      topAttentionSymbols: [],
    },
    items: [],
    warnings: [],
    files: {
      available: [],
      missing: [],
    },
  };
}

function pickLatestManualBySymbol(rows) {
  const bucket = new Map();

  rows.forEach((row) => {
    const current = bucket.get(row.symbol);
    if (!current) {
      bucket.set(row.symbol, row);
      return;
    }

    const currentScore = [
      row.activeOnEndDate === true ? '1' : '0',
      row.effectiveFrom || '',
      row.updatedAt || '',
    ].join('|');
    const previousScore = [
      current.activeOnEndDate === true ? '1' : '0',
      current.effectiveFrom || '',
      current.updatedAt || '',
    ].join('|');

    if (currentScore >= previousScore) {
      bucket.set(row.symbol, row);
    }
  });

  return bucket;
}

function matchStatusAndMismatch(item, manual) {
  const mismatchFields = [];

  if (item.suggestPauseBuy && !manual.manualPauseBuy) {
    mismatchFields.push('pauseBuy');
  }
  if (item.suggestForceReview && !manual.manualForceReview) {
    mismatchFields.push('forceReview');
  }
  if (item.suggestThesisBroken && !manual.manualThesisBroken) {
    mismatchFields.push('thesisBroken');
  }

  return {
    mismatchFields,
    matchStatus: mismatchFields.length === 0 ? 'matched' : 'mismatch',
  };
}

function buildPriority(item, mismatchFields) {
  if (mismatchFields.includes('thesisBroken')) {
    return {
      priorityLevel: PRIORITY_LEVEL.HIGH,
      attentionReasonCode: 'thesis_broken_not_reflected',
    };
  }

  if (mismatchFields.includes('forceReview')) {
    return {
      priorityLevel: PRIORITY_LEVEL.HIGH,
      attentionReasonCode: 'force_review_not_reflected',
    };
  }

  if (mismatchFields.includes('pauseBuy')) {
    return {
      priorityLevel: PRIORITY_LEVEL.MEDIUM,
      attentionReasonCode: 'pause_buy_not_reflected',
    };
  }

  if (item.suggestThesisBroken || item.suggestForceReview || item.suggestPauseBuy) {
    return {
      priorityLevel: PRIORITY_LEVEL.LOW,
      attentionReasonCode: 'covered_by_manual_risk',
    };
  }

  return {
    priorityLevel: PRIORITY_LEVEL.LOW,
    attentionReasonCode: 'no_candidate_signal',
  };
}

function buildComparableItem(item, manualRow) {
  const manual = {
    manualPauseBuy: Boolean(manualRow?.pauseBuy),
    manualForceReview: Boolean(manualRow?.forceReview),
    manualThesisBroken: Boolean(manualRow?.thesisBroken),
  };

  const { mismatchFields, matchStatus } = matchStatusAndMismatch(item, manual);
  const { priorityLevel, attentionReasonCode } = buildPriority(item, mismatchFields);

  return {
    symbol: item.symbol,
    researchLabel: item.finalResearchLabel || '',
    suggestPauseBuy: Boolean(item.suggestPauseBuy),
    suggestForceReview: Boolean(item.suggestForceReview),
    suggestThesisBroken: Boolean(item.suggestThesisBroken),
    confidence: Number(item.confidence ?? 0),
    manualPauseBuy: manual.manualPauseBuy,
    manualForceReview: manual.manualForceReview,
    manualThesisBroken: manual.manualThesisBroken,
    matchStatus,
    mismatchFields,
    priorityLevel,
    attentionReasonCode,
    sourceSuggestRun: item.sourceSuggestRun || '',
    manualEffectiveFrom: manualRow?.effectiveFrom || '',
    manualNote: manualRow?.note || '',
  };
}

function priorityRank(level) {
  if (level === PRIORITY_LEVEL.HIGH) {
    return 0;
  }
  if (level === PRIORITY_LEVEL.MEDIUM) {
    return 1;
  }
  return 2;
}

function sortItems(items) {
  return [...items].sort((left, right) => {
    const priorityDiff = priorityRank(left.priorityLevel) - priorityRank(right.priorityLevel);
    if (priorityDiff !== 0) {
      return priorityDiff;
    }
    const confidenceDiff = Number(right.confidence || 0) - Number(left.confidence || 0);
    if (confidenceDiff !== 0) {
      return confidenceDiff;
    }
    return String(left.symbol || '').localeCompare(String(right.symbol || ''));
  });
}

function latestUpdatedAt(monthly, manual) {
  return [monthly?.meta?.updatedAt, manual?.meta?.lastUpdated]
    .filter(Boolean)
    .sort()
    .at(-1) || '';
}

export async function loadMonthlyResearchManualRiskData() {
  const [monthlyResearchData, manualRiskData] = await Promise.all([
    loadMonthlyResearchPageData(),
    loadManualRiskPageData(),
  ]);

  if (!monthlyResearchData || monthlyResearchData.empty) {
    return createEmptyData();
  }

  const manualMap = pickLatestManualBySymbol(manualRiskData?.rows || []);
  const candidateItems = (monthlyResearchData.items || []).filter(
    (item) => Boolean(item.suggestPauseBuy || item.suggestForceReview || item.suggestThesisBroken),
  );

  const comparedItems = sortItems(
    candidateItems.map((item) => buildComparableItem(item, manualMap.get(item.symbol))),
  );

  const unmatchedItems = comparedItems.filter((item) => item.matchStatus === 'mismatch');
  const topAttentionSymbols = unmatchedItems
    .slice(0, ALIGNMENT_TOP_SYMBOLS_LIMIT)
    .map((item) => item.symbol);

  const warnings = [];
  if (manualRiskData?.empty) {
    warnings.push('manual_unavailable');
  }
  if (monthlyResearchData?.partial || manualRiskData?.partial) {
    warnings.push('source_files_missing');
  }

  return {
    empty: false,
    partial: Boolean(monthlyResearchData?.partial || manualRiskData?.partial || manualRiskData?.empty),
    meta: {
      batchId: monthlyResearchData.meta.batchId || '',
      sourceSuggestRun: monthlyResearchData.meta.sourceSuggestRun || '',
      updatedAt: latestUpdatedAt(monthlyResearchData, manualRiskData),
      totalResearchTargets: Number(monthlyResearchData.summary.totalTargets ?? monthlyResearchData.items.length),
      monthlySourceType: monthlyResearchData.meta.sourceType || 'empty',
      manualSourceType: manualRiskData?.meta?.sourceType || 'empty',
    },
    summary: {
      pauseCandidateCount: Number(monthlyResearchData.summary.pauseCandidateCount ?? 0),
      forceReviewCandidateCount: Number(monthlyResearchData.summary.forceReviewCandidateCount ?? 0),
      thesisBrokenCandidateCount: Number(monthlyResearchData.summary.thesisBrokenCandidateCount ?? 0),
      matchedCount: comparedItems.filter((item) => item.matchStatus === 'matched').length,
      unmatchedCount: unmatchedItems.length,
      highPriorityCount: comparedItems.filter((item) => item.priorityLevel === PRIORITY_LEVEL.HIGH).length,
      topAttentionSymbols,
    },
    items: comparedItems,
    warnings,
    files: {
      available: [
        ...(monthlyResearchData?.files?.available || []),
        ...(manualRiskData?.files?.available || []),
      ],
      missing: [
        ...(monthlyResearchData?.files?.missing || []),
        ...(manualRiskData?.files?.missing || []),
      ],
    },
  };
}
