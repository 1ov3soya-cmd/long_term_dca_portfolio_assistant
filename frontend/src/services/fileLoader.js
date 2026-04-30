import {
  readStaticArchiveJson,
  readStaticArchiveText,
} from './staticSnapshotLoader';

const runtimeEnv = (typeof import.meta !== 'undefined' && import.meta.env) ? import.meta.env : {};
const archiveBaseUrl = runtimeEnv.VITE_ARCHIVE_BASE_URL || '/archive-data';

export function buildArchiveUrl(relativePath) {
  const cleanPath = String(relativePath || '').replace(/\\/g, '/').replace(/^\/+/, '');
  return `${archiveBaseUrl}/${cleanPath}`;
}

export async function readArchiveJson(relativePath, options = {}) {
  const { required = false } = options;
  const staticResult = await readStaticArchiveJson(relativePath).catch(() => ({ found: false, value: null }));
  if (staticResult.found) {
    return staticResult.value;
  }

  const response = await fetch(buildArchiveUrl(relativePath), { cache: 'no-store' }).catch((error) => {
    if (required) {
      throw new Error(`Failed to read archive JSON: ${relativePath}. ${error.message}`);
    }
    return null;
  });

  if (!response) {
    return null;
  }

  if (!response.ok) {
    if (required) {
      throw new Error(`Failed to read archive JSON: ${relativePath}. HTTP ${response.status}`);
    }
    return null;
  }

  return response.json();
}

export async function readArchiveText(relativePath, options = {}) {
  const { required = false } = options;
  const staticResult = await readStaticArchiveText(relativePath).catch(() => ({ found: false, value: null }));
  if (staticResult.found) {
    return staticResult.value;
  }

  const response = await fetch(buildArchiveUrl(relativePath), { cache: 'no-store' }).catch((error) => {
    if (required) {
      throw new Error(`Failed to read archive text: ${relativePath}. ${error.message}`);
    }
    return null;
  });

  if (!response) {
    return null;
  }

  if (!response.ok) {
    if (required) {
      throw new Error(`Failed to read archive text: ${relativePath}. HTTP ${response.status}`);
    }
    return null;
  }

  return response.text();
}

export function loadLatestRunsIndex() {
  return readArchiveJson('reports/runs/latest_index.json');
}

export function loadLatestCompareIndex() {
  return readArchiveJson('reports/run_compare/latest_compare_index.json');
}

export function loadSharedReportJson(relativePath) {
  return readArchiveJson(relativePath);
}

export function loadSharedReportText(relativePath) {
  return readArchiveText(relativePath);
}

export function readRunJson(runId, fileName, options = {}) {
  if (!runId) {
    return Promise.resolve(null);
  }
  return readArchiveJson(`reports/runs/${runId}/${fileName}`, options);
}

export function readRunText(runId, fileName, options = {}) {
  if (!runId) {
    return Promise.resolve(null);
  }
  return readArchiveText(`reports/runs/${runId}/${fileName}`, options);
}

export function readCompareJson(compareId, fileName, options = {}) {
  if (!compareId) {
    return Promise.resolve(null);
  }
  return readArchiveJson(`reports/run_compare/${compareId}/${fileName}`, options);
}

export function readCompareText(compareId, fileName, options = {}) {
  if (!compareId) {
    return Promise.resolve(null);
  }
  return readArchiveText(`reports/run_compare/${compareId}/${fileName}`, options);
}
