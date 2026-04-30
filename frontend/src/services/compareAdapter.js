import {
  loadLatestCompareIndex,
  readCompareJson,
  readCompareText,
} from './fileLoader.js';
import { readSnapshotJson } from './staticSnapshotLoader.js';

function createEmptyCompareBundle() {
  return {
    exists: false,
    compareId: '',
    latestCompareIndex: null,
    manifest: null,
    summary: null,
    configDiff: null,
    summaryDiffRows: [],
    reportMarkdown: '',
    missingFiles: [],
  };
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

function parseCsvToRows(csvText) {
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

function summarizeChangedPaths(items = [], limit = 8) {
  return items.slice(0, limit).map((item) => ({
    path: item.path || item.key || 'unknown',
    valueA: item.value_a ?? '',
    valueB: item.value_b ?? '',
    changeType: item.change_type || 'changed',
  }));
}

function normalizeBooleanLabel(value) {
  if (value === true) {
    return 'yes';
  }
  if (value === false) {
    return 'no';
  }
  return 'na';
}

/**
 * 读取最新 compare 归档。
 */
export async function loadLatestCompareBundle() {
  const staticSnapshot = await readSnapshotJson('run_compare_snapshot.json');
  if (staticSnapshot && (staticSnapshot.compare_id || staticSnapshot.manifest || staticSnapshot.summary)) {
    const missingFiles = [];
    if (!staticSnapshot.manifest) missingFiles.push('compare_manifest.json');
    if (!staticSnapshot.summary) missingFiles.push('compare_summary.json');
    if (!staticSnapshot.config_diff) missingFiles.push('config_diff.json');
    if (!staticSnapshot.summary_diff_csv) missingFiles.push('summary_diff.csv');
    if (!staticSnapshot.report_preview) missingFiles.push('compare_report.md');

    return {
      exists: true,
      compareId: staticSnapshot.compare_id || '',
      latestCompareIndex: staticSnapshot.index || null,
      manifest: staticSnapshot.manifest || null,
      summary: staticSnapshot.summary || null,
      configDiff: staticSnapshot.config_diff || null,
      summaryDiffRows: parseCsvToRows(staticSnapshot.summary_diff_csv || ''),
      reportMarkdown: staticSnapshot.report_preview || '',
      missingFiles,
    };
  }

  const latestCompareIndex = await loadLatestCompareIndex();
  const compareId = latestCompareIndex?.compare_id;

  if (!compareId) {
    return createEmptyCompareBundle();
  }

  const [
    manifest,
    summary,
    configDiff,
    summaryDiffCsv,
    reportMarkdown,
  ] = await Promise.all([
    readCompareJson(compareId, 'compare_manifest.json'),
    readCompareJson(compareId, 'compare_summary.json'),
    readCompareJson(compareId, 'config_diff.json'),
    readCompareText(compareId, 'summary_diff.csv'),
    readCompareText(compareId, 'compare_report.md'),
  ]);

  const missingFiles = [];
  if (!manifest) missingFiles.push('compare_manifest.json');
  if (!summary) missingFiles.push('compare_summary.json');
  if (!configDiff) missingFiles.push('config_diff.json');
  if (!summaryDiffCsv) missingFiles.push('summary_diff.csv');
  if (!reportMarkdown) missingFiles.push('compare_report.md');

  return {
    exists: Boolean(latestCompareIndex || manifest || summary || configDiff || summaryDiffCsv || reportMarkdown),
    compareId,
    latestCompareIndex,
    manifest,
    summary,
    configDiff,
    summaryDiffRows: parseCsvToRows(summaryDiffCsv),
    reportMarkdown: reportMarkdown || '',
    missingFiles,
  };
}

/**
 * 对比摘要映射成 Dashboard 卡片需要的 shape。
 */
export function buildCompareCardData(compareBundle) {
  if (!compareBundle?.exists) {
    return {
      runA: 'N/A',
      runB: 'N/A',
      comparableLevel: 'N/A',
      topConfigChange: '暂无对比数据',
      topSummaryChange: '暂无对比数据',
    };
  }

  const topConfigChange = compareBundle.summary?.top_config_changes?.[0];
  const topSummaryChange = compareBundle.summary?.top_summary_changes?.[0];

  return {
    runA: compareBundle.manifest?.run_a?.run_ref || 'N/A',
    runB: compareBundle.manifest?.run_b?.run_ref || 'N/A',
    comparableLevel: String(
      compareBundle.summary?.comparability_assessment?.level
        || compareBundle.manifest?.comparable_level
        || compareBundle.latestCompareIndex?.comparable_level
        || 'N/A',
    ).toUpperCase(),
    topConfigChange: topConfigChange
      ? `${topConfigChange.path || topConfigChange.key || 'config'} -> ${topConfigChange.change_type || 'changed'}`
      : '暂无显著配置差异',
    topSummaryChange: topSummaryChange
      ? `${topSummaryChange.key || 'summary'} -> ${topSummaryChange.direction || topSummaryChange.change_type || 'changed'}`
      : '暂无显著结果差异',
  };
}

/**
 * 构建 Run Compare 页面直接消费的 shape。
 */
export function buildComparePageData(compareBundle) {
  if (!compareBundle?.exists) {
    return {
      exists: false,
      empty: true,
      meta: {
        compareId: '',
        comparedAt: '',
        comparableLevel: '',
        runA: '',
        runB: '',
      },
      basic: {
        compareStatus: '',
        commandMatch: 'na',
        endDateMatch: 'na',
        keyFindingsCount: 0,
        reason: '',
      },
      configChanges: {
        topChanges: [],
        structuredChanges: [],
        manualRiskChanged: false,
        adjModeChanged: false,
        dataModeChanged: false,
        pathOnlyDifferences: [],
      },
      summaryChanges: [],
      attentionPoints: [],
      warnings: [],
      reportPreview: '',
      files: {
        available: [],
        missing: [],
      },
    };
  }

  const manifest = compareBundle.manifest || {};
  const summary = compareBundle.summary || {};
  const configDiff = compareBundle.configDiff || {};
  const manifestDiff = configDiff.manifest_diff || {};
  const configSnapshotDiff = configDiff.config_snapshot_diff || {};
  const artifactDiff = configDiff.artifact_diff || {};

  const structuredConfigChanges = [
    ...summarizeChangedPaths(configSnapshotDiff.changed_values, 10),
    ...summarizeChangedPaths(manifestDiff.changed_items, 10),
  ];

  const pathOnlyDifferences = [
    ...(artifactDiff.added_keys || []),
    ...(artifactDiff.removed_keys || []),
  ].slice(0, 12).map((item) => item.path || 'unknown');

  const availableFiles = [
    'compare_manifest.json',
    'compare_summary.json',
    'config_diff.json',
    'summary_diff.csv',
    'compare_report.md',
  ].filter((fileName) => !compareBundle.missingFiles.includes(fileName));

  return {
    exists: true,
    empty: false,
    meta: {
      compareId: compareBundle.compareId,
      comparedAt: manifest.compared_at || compareBundle.latestCompareIndex?.compared_at || '',
      comparableLevel: String(
        summary.comparability_assessment?.level
          || manifest.comparable_level
          || compareBundle.latestCompareIndex?.comparable_level
          || '',
      ).toUpperCase(),
      runA: manifest.run_a?.run_ref || '',
      runB: manifest.run_b?.run_ref || '',
    },
    basic: {
      compareStatus: manifest.compare_status || compareBundle.latestCompareIndex?.compare_status || '',
      commandMatch: normalizeBooleanLabel(manifest.command_match),
      endDateMatch: normalizeBooleanLabel(manifest.end_date_match),
      keyFindingsCount: Number(manifest.key_findings_count || 0),
      reason: summary.comparability_assessment?.reason || '',
    },
    configChanges: {
      topChanges: (summary.top_config_changes || []).map((item) => ({
        path: item.path || item.key || 'config',
        changeType: item.change_type || 'changed',
        valueA: item.value_a ?? '',
        valueB: item.value_b ?? '',
      })),
      structuredChanges: structuredConfigChanges,
      manualRiskChanged: Boolean(summary.manual_risk_changed),
      adjModeChanged: Boolean(summary.adj_mode_changed),
      dataModeChanged: Boolean(summary.data_mode_changed),
      pathOnlyDifferences,
    },
    summaryChanges: (compareBundle.summaryDiffRows || []).slice(0, 20).map((row) => ({
      metric: row.key || '',
      runAValue: row.value_a || '',
      runBValue: row.value_b || '',
      absoluteDiff: row.absolute_change || '',
      relativeDiff: row.relative_change || '',
      direction: row.direction || row.change_type || '',
    })),
    attentionPoints: summary.top_attention_points || [],
    warnings: [
      ...(configDiff.notes_diff?.warnings?.only_a_items || []),
      ...(configDiff.notes_diff?.warnings?.only_b_items || []),
    ],
    reportPreview: compareBundle.reportMarkdown
      ? compareBundle.reportMarkdown.split(/\r?\n/).slice(0, 24).join('\n')
      : '',
    files: {
      available: availableFiles,
      missing: compareBundle.missingFiles,
    },
  };
}

/**
 * 直接读取最新 compare 并映射为页面数据。
 */
export async function loadLatestComparePageData() {
  const bundle = await loadLatestCompareBundle();
  return buildComparePageData(bundle);
}
