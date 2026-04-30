import {
  readStaticArchiveJson,
  readStaticArchiveText,
} from './staticSnapshotLoader';

const runtimeEnv = (typeof import.meta !== 'undefined' && import.meta.env) ? import.meta.env : {};
const archiveBaseUrl = runtimeEnv.VITE_ARCHIVE_BASE_URL || '/archive-data';

/**
 * 将归档相对路径转换为 dev server 可读取的 URL。
 */
export function buildArchiveUrl(relativePath) {
  const cleanPath = String(relativePath || '').replace(/\\/g, '/').replace(/^\/+/, '');
  return `${archiveBaseUrl}/${cleanPath}`;
}

/**
 * 读取 JSON 文件。
 * 生产静态部署时优先读取 /data/archive_compat_snapshot.json 中的虚拟归档；
 * 若未生成静态快照，则回退到本地开发用的 /archive-data/...。
 */
export async function readArchiveJson(relativePath, options = {}) {
  const { required = false } = options;
  const staticResult = await readStaticArchiveJson(relativePath).catch(() => ({ found: false, value: null }));
  if (staticResult.found) {
    return staticResult.value;
  }

  const response = await fetch(buildArchiveUrl(relativePath), { cache: 'no-store' }).catch((error) => {
    if (required) {
      throw new Error(`读取归档失败: ${relativePath}. ${error.message}`);
    }
    return null;
  });

  if (!response) {
    return null;
  }

  if (!response.ok) {
    if (required) {
      throw new Error(`读取归档失败: ${relativePath}. HTTP ${response.status}`);
    }
    return null;
  }

  return response.json();
}

/**
 * 读取文本文件，常用于 Markdown/CSV 预览。
 */
export async function readArchiveText(relativePath, options = {}) {
  const { required = false } = options;
  const staticResult = await readStaticArchiveText(relativePath).catch(() => ({ found: false, value: null }));
  if (staticResult.found) {
    return staticResult.value;
  }

  const response = await fetch(buildArchiveUrl(relativePath), { cache: 'no-store' }).catch((error) => {
    if (required) {
      throw new Error(`读取归档文本失败: ${relativePath}. ${error.message}`);
    }
    return null;
  });

  if (!response) {
    return null;
  }

  if (!response.ok) {
    if (required) {
      throw new Error(`读取归档文本失败: ${relativePath}. HTTP ${response.status}`);
    }
    return null;
  }

  return response.text();
}

/**
 * 读取 runs/latest_index。
 */
export function loadLatestRunsIndex() {
  return readArchiveJson('reports/runs/latest_index.json');
}

/**
 * 读取 compare latest 索引。
 */
export function loadLatestCompareIndex() {
  return readArchiveJson('reports/run_compare/latest_compare_index.json');
}

/**
 * 读取共享报告 JSON。
 */
export function loadSharedReportJson(relativePath) {
  return readArchiveJson(relativePath);
}

/**
 * 读取共享报告文本。
 */
export function loadSharedReportText(relativePath) {
  return readArchiveText(relativePath);
}

/**
 * 读取 run 目录下单个 JSON 文件。
 */
export function readRunJson(runId, fileName, options = {}) {
  if (!runId) {
    return Promise.resolve(null);
  }
  return readArchiveJson(`reports/runs/${runId}/${fileName}`, options);
}

/**
 * 读取 run 目录下单个文本文件。
 */
export function readRunText(runId, fileName, options = {}) {
  if (!runId) {
    return Promise.resolve(null);
  }
  return readArchiveText(`reports/runs/${runId}/${fileName}`, options);
}

/**
 * 读取 compare 目录下单个 JSON 文件。
 */
export function readCompareJson(compareId, fileName, options = {}) {
  if (!compareId) {
    return Promise.resolve(null);
  }
  return readArchiveJson(`reports/run_compare/${compareId}/${fileName}`, options);
}

/**
 * 读取 compare 目录下单个文本文件。
 */
export function readCompareText(compareId, fileName, options = {}) {
  if (!compareId) {
    return Promise.resolve(null);
  }
  return readArchiveText(`reports/run_compare/${compareId}/${fileName}`, options);
}
