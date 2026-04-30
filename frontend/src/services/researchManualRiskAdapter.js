import { loadManualRiskPageData } from './manualRiskAdapter.js';
import { loadResearchPageData } from './researchAdapter.js';

function compareKey(left, right) {
  return `${left || ''}|${right || ''}`;
}

function pickLatestResearchBySymbol(items) {
  const bucket = new Map();

  items.forEach((item) => {
    const existing = bucket.get(item.symbol);
    if (!existing) {
      bucket.set(item.symbol, item);
      return;
    }

    const currentKey = compareKey(item.analysisDate, item.updatedAt);
    const existingKey = compareKey(existing.analysisDate, existing.updatedAt);
    if (currentKey >= existingKey) {
      bucket.set(item.symbol, item);
    }
  });

  return bucket;
}

function pickLatestManualBySymbol(rows) {
  const bucket = new Map();

  rows.forEach((row) => {
    const existing = bucket.get(row.symbol);
    if (!existing) {
      bucket.set(row.symbol, row);
      return;
    }

    const currentScore = [
      row.activeOnEndDate === true ? '1' : '0',
      row.effectiveFrom || '',
      row.updatedAt || '',
    ].join('|');
    const existingScore = [
      existing.activeOnEndDate === true ? '1' : '0',
      existing.effectiveFrom || '',
      existing.updatedAt || '',
    ].join('|');

    if (currentScore >= existingScore) {
      bucket.set(row.symbol, row);
    }
  });

  return bucket;
}

function mismatchFields(researchItem, manualItem) {
  const fields = [];

  if (researchItem.suggestPauseBuy !== manualItem.pauseBuy) {
    fields.push('pause_buy');
  }
  if (researchItem.suggestForceReview !== manualItem.forceReview) {
    fields.push('force_review');
  }
  if (researchItem.suggestThesisBroken !== manualItem.thesisBroken) {
    fields.push('thesis_broken');
  }

  return fields;
}

function buildAttentionReasonCode({
  hasResearch,
  hasManual,
  researchItem,
  manualItem,
  mismatches,
}) {
  if (!hasResearch && hasManual) {
    return 'manual_only_no_research';
  }

  if (hasResearch && !hasManual) {
    if (researchItem.suggestThesisBroken) {
      return 'research_only_thesis_broken';
    }
    if (researchItem.suggestForceReview) {
      return 'research_only_force_review';
    }
    if (researchItem.suggestPauseBuy) {
      return 'research_only_pause_buy';
    }
    return 'research_only_neutral';
  }

  if (mismatches.includes('thesis_broken')) {
    return 'thesis_broken_mismatch';
  }

  if (mismatches.includes('force_review')) {
    return 'force_review_mismatch';
  }

  if (mismatches.includes('pause_buy')) {
    return 'pause_buy_mismatch';
  }

  if (manualItem.thesisBroken) {
    return 'manual_stricter_thesis_broken';
  }

  if (manualItem.forceReview) {
    return 'manual_stricter_force_review';
  }

  if (manualItem.pauseBuy) {
    return 'manual_stricter_pause_buy';
  }

  return 'aligned';
}

function buildPriorityLevel({
  hasResearch,
  hasManual,
  researchItem,
  manualItem,
  mismatches,
}) {
  if (!hasResearch && hasManual) {
    return 'low';
  }

  if (researchItem.suggestThesisBroken && (!hasManual || !manualItem.thesisBroken)) {
    return 'high';
  }

  if (researchItem.suggestForceReview && (!hasManual || !manualItem.forceReview)) {
    return hasManual ? 'medium' : 'high';
  }

  if (researchItem.suggestPauseBuy && (!hasManual || !manualItem.pauseBuy)) {
    return 'medium';
  }

  if (mismatches.length > 0) {
    return 'low';
  }

  return 'low';
}

function buildMatchStatus(hasResearch, hasManual, mismatches) {
  if (!hasResearch || !hasManual) {
    return 'partial';
  }
  if (mismatches.length > 0) {
    return 'mismatch';
  }
  return 'matched';
}

function buildCombinedItem(symbol, researchItem, manualItem) {
  const hasResearch = Boolean(researchItem);
  const hasManual = Boolean(manualItem);
  const mismatches = hasResearch && hasManual ? mismatchFields(researchItem, manualItem) : [];
  const matchStatus = buildMatchStatus(hasResearch, hasManual, mismatches);
  const priorityLevel = buildPriorityLevel({
    hasResearch,
    hasManual,
    researchItem,
    manualItem,
    mismatches,
  });
  const attentionReasonCode = buildAttentionReasonCode({
    hasResearch,
    hasManual,
    researchItem,
    manualItem,
    mismatches,
  });

  return {
    id: symbol,
    symbol,
    analysisDate: researchItem?.analysisDate || '',
    researchLabel: researchItem?.finalResearchLabel || '',
    suggestPauseBuy: hasResearch ? researchItem.suggestPauseBuy : null,
    suggestForceReview: hasResearch ? researchItem.suggestForceReview : null,
    suggestThesisBroken: hasResearch ? researchItem.suggestThesisBroken : null,
    confidence: hasResearch ? Number(researchItem.confidence || 0) : null,
    manualPauseBuy: hasManual ? manualItem.pauseBuy : null,
    manualForceReview: hasManual ? manualItem.forceReview : null,
    manualThesisBroken: hasManual ? manualItem.thesisBroken : null,
    manualEffectiveFrom: manualItem?.effectiveFrom || '',
    manualNote: manualItem?.note || '',
    matchStatus,
    mismatchFields: mismatches,
    priorityLevel,
    attentionReasonCode,
    sourceRun: researchItem?.sourceRun || '',
    memoAvailable: Boolean(researchItem?.memoAvailable),
    bullCase: researchItem?.bullCase || '',
    bearCase: researchItem?.bearCase || '',
    riskSummary: researchItem?.riskSummary || '',
    notes: researchItem?.notes || '',
    memoPreview: researchItem?.memoPreview || '',
    sourceFiles: {
      researchJson: researchItem?.archivePaths?.json || '',
      researchMarkdown: researchItem?.archivePaths?.markdown || '',
      manualSource: manualItem?.source || '',
    },
  };
}

function sortCombinedItems(items) {
  const priorityRank = { high: 0, medium: 1, low: 2 };
  const matchRank = { mismatch: 0, partial: 1, matched: 2 };

  return [...items].sort((left, right) => {
    const priorityDiff = (priorityRank[left.priorityLevel] ?? 9) - (priorityRank[right.priorityLevel] ?? 9);
    if (priorityDiff !== 0) {
      return priorityDiff;
    }

    const matchDiff = (matchRank[left.matchStatus] ?? 9) - (matchRank[right.matchStatus] ?? 9);
    if (matchDiff !== 0) {
      return matchDiff;
    }

    const analysisDiff = (right.analysisDate || '').localeCompare(left.analysisDate || '');
    if (analysisDiff !== 0) {
      return analysisDiff;
    }

    return (left.symbol || '').localeCompare(right.symbol || '');
  });
}

function latestUpdatedAt(values) {
  const candidates = values.filter(Boolean);
  if (candidates.length === 0) {
    return '';
  }
  return [...candidates].sort().at(-1) || '';
}

function createEmptyData() {
  return {
    empty: true,
    partial: false,
    meta: {
      sourceType: 'empty',
      updatedAt: '',
      totalItems: 0,
    },
    summary: {
      matchedCount: 0,
      mismatchedCount: 0,
      pauseMismatchCount: 0,
      reviewMismatchCount: 0,
      thesisMismatchCount: 0,
      highPriorityCount: 0,
    },
    items: [],
    warnings: [],
    files: {
      available: [],
      missing: [],
    },
  };
}

export async function loadResearchManualRiskPageData() {
  const [researchData, manualRiskData] = await Promise.all([
    loadResearchPageData(),
    loadManualRiskPageData(),
  ]);

  const researchMap = pickLatestResearchBySymbol(researchData?.items || []);
  const manualMap = pickLatestManualBySymbol(manualRiskData?.rows || []);
  const symbols = [...new Set([...researchMap.keys(), ...manualMap.keys()])];

  if (symbols.length === 0) {
    return createEmptyData();
  }

  const items = sortCombinedItems(
    symbols.map((symbol) => buildCombinedItem(symbol, researchMap.get(symbol), manualMap.get(symbol))),
  );

  const warningCodes = [];
  if (researchData?.empty) {
    warningCodes.push('research_unavailable');
  }
  if (manualRiskData?.empty) {
    warningCodes.push('manual_unavailable');
  }
  if (researchData?.partial || manualRiskData?.partial) {
    warningCodes.push('source_files_missing');
  }
  if (items.some((item) => item.matchStatus === 'partial')) {
    warningCodes.push('symbol_partial');
  }

  return {
    empty: false,
    partial: Boolean(researchData?.partial || manualRiskData?.partial || items.some((item) => item.matchStatus === 'partial')),
    meta: {
      sourceType: 'combined',
      updatedAt: latestUpdatedAt([
        researchData?.meta?.updatedAt,
        manualRiskData?.meta?.lastUpdated,
      ]),
      totalItems: items.length,
      researchSourceType: researchData?.meta?.sourceType || 'empty',
      manualSourceType: manualRiskData?.meta?.sourceType || 'empty',
    },
    summary: {
      matchedCount: items.filter((item) => item.matchStatus === 'matched').length,
      mismatchedCount: items.filter((item) => item.matchStatus === 'mismatch').length,
      pauseMismatchCount: items.filter((item) => item.mismatchFields.includes('pause_buy')).length,
      reviewMismatchCount: items.filter((item) => item.mismatchFields.includes('force_review')).length,
      thesisMismatchCount: items.filter((item) => item.mismatchFields.includes('thesis_broken')).length,
      highPriorityCount: items.filter((item) => item.priorityLevel === 'high').length,
    },
    items,
    warnings: warningCodes,
    files: {
      available: [
        ...(researchData?.files?.available || []),
        ...(manualRiskData?.files?.available || []),
      ],
      missing: [
        ...(researchData?.files?.missing || []),
        ...(manualRiskData?.files?.missing || []),
      ],
    },
  };
}
