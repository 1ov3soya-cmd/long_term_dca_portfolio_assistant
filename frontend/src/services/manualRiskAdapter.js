import {
  loadLatestRunsIndex,
  loadSharedReportJson,
  readArchiveText,
} from './fileLoader.js';
import { loadLatestRunBundle } from './runAdapter.js';

function normalizeBoolean(value) {
  if (typeof value === 'boolean') {
    return value;
  }
  if (typeof value === 'number') {
    return value !== 0;
  }
  if (typeof value === 'string') {
    const normalized = value.trim().toLowerCase();
    return ['true', '1', 'yes', 'y'].includes(normalized);
  }
  return false;
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

function deriveActionCode(payload) {
  if (normalizeBoolean(payload?.thesis_broken) || normalizeBoolean(payload?.suggest_thesis_broken)) {
    return 'thesisBroken';
  }
  if (
    normalizeBoolean(payload?.manual_force_review)
    || normalizeBoolean(payload?.suggest_force_review)
    || normalizeBoolean(payload?.final_force_review)
  ) {
    return 'forceReview';
  }
  if (
    normalizeBoolean(payload?.manual_pause_buy)
    || normalizeBoolean(payload?.suggest_manual_pause_buy)
    || normalizeBoolean(payload?.final_pause_buy)
  ) {
    return 'pauseBuy';
  }
  return 'normal';
}

function mapRow(row, source, fallbackEndDate = '') {
  return {
    symbol: row.symbol || 'N/A',
    assetType: row.asset_type || '',
    effectiveFrom: row.effective_from || 'N/A',
    pauseBuy: normalizeBoolean(row.manual_pause_buy),
    forceReview: normalizeBoolean(row.manual_force_review),
    thesisBroken: normalizeBoolean(row.thesis_broken),
    finalPauseBuy: normalizeBoolean(row.final_pause_buy),
    finalForceReview: normalizeBoolean(row.final_force_review),
    finalPriorityLevel: Number(row.final_priority_level || 0),
    finalReasonCodes: row.final_reason_codes || '',
    finalActionText: row.final_human_readable_action || '',
    finalActionCode: deriveActionCode(row),
    note: row.note || '',
    source,
    updatedAt: row.updated_at || '',
    updatedBy: row.updated_by || '',
    activeOnEndDate: row.active_on_end_date === undefined ? null : normalizeBoolean(row.active_on_end_date),
    effectiveWindowState: row.effective_window_state || '',
    endDate: row.end_date || fallbackEndDate || '',
    inCurrentUniverse: row.in_current_universe === undefined ? null : normalizeBoolean(row.in_current_universe),
  };
}

function extractSymbolsObject(snapshot) {
  if (!snapshot || typeof snapshot !== 'object') {
    return {};
  }

  return snapshot.manual_risk_flags?.symbols
    || snapshot.symbols
    || snapshot.manual_risk_flags_snapshot?.manual_risk_flags?.symbols
    || {};
}

function rowsFromAcceptance(acceptanceReport, previewCsvText) {
  const previewRows = Array.isArray(acceptanceReport?.preview) && acceptanceReport.preview.length > 0
    ? acceptanceReport.preview
    : parseCsvRows(previewCsvText);
  const endDate = acceptanceReport?.end_date || '';
  return previewRows.map((row) => mapRow(row, 'acceptance', endDate));
}

function rowsFromValidation(validationJson, endDate = '') {
  const rows = Array.isArray(validationJson?.flags) ? validationJson.flags : [];
  return rows.map((row) => mapRow(row, 'validation', endDate));
}

function rowsFromLatestRun(latestRun) {
  const symbols = extractSymbolsObject(latestRun?.configSnapshot?.manual_risk_flags_snapshot);
  return Object.entries(symbols).map(([symbol, payload]) => mapRow({
    symbol,
    ...payload,
  }, 'latestRun', latestRun?.manifest?.end_date || ''));
}

function rowsFromFallback(configJson) {
  const symbols = extractSymbolsObject(configJson);
  return Object.entries(symbols).map(([symbol, payload]) => mapRow({
    symbol,
    ...payload,
  }, 'fallback'));
}

function pickRows({
  acceptanceReport,
  previewCsvText,
  validationJson,
  latestRunBundle,
  fallbackConfig,
  fallbackSampleConfig,
}) {
  const acceptanceRows = rowsFromAcceptance(acceptanceReport, previewCsvText);
  if (acceptanceRows.length > 0) {
    return { rows: acceptanceRows, sourceType: 'acceptance' };
  }

  const validationRows = rowsFromValidation(validationJson, acceptanceReport?.end_date || latestRunBundle?.manifest?.end_date || '');
  if (validationRows.length > 0) {
    return { rows: validationRows, sourceType: 'validation' };
  }

  const latestRunRows = rowsFromLatestRun(latestRunBundle);
  if (latestRunRows.length > 0) {
    return { rows: latestRunRows, sourceType: 'latestRun' };
  }

  const fallbackRows = rowsFromFallback(fallbackConfig);
  if (fallbackRows.length > 0) {
    return { rows: fallbackRows, sourceType: 'fallback' };
  }

  const sampleRows = rowsFromFallback(fallbackSampleConfig);
  if (sampleRows.length > 0) {
    return { rows: sampleRows, sourceType: 'fallback' };
  }

  return { rows: [], sourceType: 'empty' };
}

function countEffectiveInRange(rows, endDate) {
  if (!rows.length) {
    return 0;
  }

  const explicitCount = rows.filter((row) => row.activeOnEndDate === true).length;
  if (explicitCount > 0) {
    return explicitCount;
  }

  if (!endDate) {
    return 0;
  }

  return rows.filter((row) => row.effectiveFrom && row.effectiveFrom <= endDate).length;
}

function latestUpdatedAt(rows, fallbacks = []) {
  const candidates = [
    ...rows.map((row) => row.updatedAt).filter(Boolean),
    ...fallbacks.filter(Boolean),
  ];
  if (candidates.length === 0) {
    return 'N/A';
  }
  return [...candidates].sort().at(-1) || 'N/A';
}

function previewMarkdown(text, lines = 24) {
  if (!text) {
    return '';
  }
  return text.split(/\r?\n/).slice(0, lines).join('\n').trim();
}

function buildAvailableFiles(files) {
  return Object.entries(files)
    .filter(([, value]) => Boolean(value))
    .map(([key]) => key);
}

function buildMissingFiles(files) {
  return Object.entries(files)
    .filter(([, value]) => !value)
    .map(([key]) => key);
}

export async function loadManualRiskPageData() {
  const latestRunsIndex = await loadLatestRunsIndex();

  const [
    acceptanceReport,
    previewCsvText,
    checklistMarkdown,
    validationJson,
    validationMarkdown,
    latestRunBundle,
    fallbackConfig,
    fallbackSampleConfig,
  ] = await Promise.all([
    loadSharedReportJson('reports/manual/manual_logic_risk_acceptance_report.json'),
    readArchiveText('reports/manual/manual_logic_risk_acceptance_preview.csv'),
    readArchiveText('reports/manual_logic_risk_acceptance_checklist.md'),
    loadSharedReportJson('reports/manual/manual_risk_flags_validation.json'),
    readArchiveText('reports/manual/manual_risk_flags_validation.md'),
    loadLatestRunBundle('validate-manual-risk-flags', latestRunsIndex),
    loadSharedReportJson('config/manual_risk_flags.json'),
    loadSharedReportJson('config/manual_risk_flags_acceptance_sample.json'),
  ]);

  const picked = pickRows({
    acceptanceReport,
    previewCsvText,
    validationJson,
    latestRunBundle,
    fallbackConfig,
    fallbackSampleConfig,
  });

  const rows = picked.rows;
  const effectiveEndDate = acceptanceReport?.end_date || latestRunBundle?.manifest?.end_date || '';
  const files = {
    acceptanceReport: Boolean(acceptanceReport),
    previewCsv: Boolean(previewCsvText),
    validationReport: Boolean(validationJson || validationMarkdown),
    checklist: Boolean(checklistMarkdown),
    latestRun: Boolean(latestRunBundle?.exists),
    fallbackConfig: Boolean(fallbackConfig || fallbackSampleConfig),
  };

  const pausedCount = rows.filter((row) => row.pauseBuy).length;
  const forceReviewCount = rows.filter((row) => row.forceReview).length;
  const thesisBrokenCount = rows.filter((row) => row.thesisBroken).length;
  const effectiveInRangeCount = countEffectiveInRange(rows, effectiveEndDate);
  const hasData = rows.length > 0 || files.checklist || files.validationReport;

  return {
    empty: !hasData,
    partial: buildMissingFiles(files).length > 0,
    meta: {
      sourceType: picked.sourceType,
      lastUpdated: latestUpdatedAt(rows, [
        acceptanceReport?.end_date,
        latestRunBundle?.latestEntry?.finished_at,
      ]),
      hasData,
      currentSourceLabel: picked.sourceType,
      endDate: effectiveEndDate || 'N/A',
    },
    summary: {
      pausedCount,
      forceReviewCount,
      thesisBrokenCount,
      effectiveInRangeCount,
    },
    rows,
    status: {
      acceptanceReport: files.acceptanceReport,
      previewCsv: files.previewCsv,
      validationReport: files.validationReport,
      checklist: files.checklist,
      latestRun: files.latestRun,
      fallbackConfig: files.fallbackConfig,
      validationValid: validationJson?.valid ?? null,
      validationIssueCount: Array.isArray(validationJson?.issues) ? validationJson.issues.length : 0,
    },
    notes: {
      checklistPreview: previewMarkdown(checklistMarkdown),
      validationPreview: previewMarkdown(validationMarkdown),
    },
    files: {
      available: buildAvailableFiles(files),
      missing: buildMissingFiles(files),
    },
  };
}
