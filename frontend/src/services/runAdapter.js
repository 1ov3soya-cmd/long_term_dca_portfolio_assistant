import {
  loadLatestRunsIndex,
  readRunJson,
  readRunText,
} from './fileLoader.js';

/**
 * 统一表示一个 run 的归档内容。
 */
export function createEmptyRunBundle(commandName = '') {
  return {
    exists: false,
    commandName,
    runId: '',
    manifest: null,
    configSnapshot: null,
    keySummary: null,
    outputArtifacts: null,
    notes: '',
    latestEntry: null,
  };
}

/**
 * 根据 run_id 读取归档目录。
 */
export async function loadRunBundleById(runId, commandName = '') {
  if (!runId) {
    return createEmptyRunBundle(commandName);
  }

  const [manifest, configSnapshot, keySummary, outputArtifacts, notes] = await Promise.all([
    readRunJson(runId, 'run_manifest.json'),
    readRunJson(runId, 'effective_config_snapshot.json'),
    readRunJson(runId, 'key_summary.json'),
    readRunJson(runId, 'output_artifacts.json'),
    readRunText(runId, 'notes.md'),
  ]);

  return {
    exists: Boolean(manifest || configSnapshot || keySummary || outputArtifacts || notes),
    commandName: manifest?.command_name || commandName,
    runId: manifest?.run_id || runId,
    manifest,
    configSnapshot,
    keySummary,
    outputArtifacts,
    notes: notes || '',
    latestEntry: null,
  };
}

/**
 * 读取 latest_index 中某个命令对应的最新 run。
 */
export async function loadLatestRunBundle(commandName, latestIndex = null) {
  const resolvedLatestIndex = latestIndex || (await loadLatestRunsIndex());
  const latestEntry = resolvedLatestIndex?.[commandName];

  if (!latestEntry?.run_id) {
    return createEmptyRunBundle(commandName);
  }

  const bundle = await loadRunBundleById(latestEntry.run_id, commandName);
  return {
    ...bundle,
    latestEntry,
  };
}
