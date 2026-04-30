const runtimeEnv = (typeof import.meta !== 'undefined' && import.meta.env) ? import.meta.env : {};

function joinUrlPath(basePath, childPath) {
  const cleanBase = String(basePath || '/').replace(/\/+$/, '');
  const cleanChild = String(childPath || '').replace(/^\/+/, '');
  return `${cleanBase || ''}/${cleanChild}`;
}

const snapshotBaseUrl = runtimeEnv.VITE_SNAPSHOT_BASE_URL || joinUrlPath(runtimeEnv.BASE_URL || '/', 'data');

let siteManifestPromise;
let archiveCompatPromise;

function normalizeArchivePath(relativePath) {
  return String(relativePath || '').replace(/\\/g, '/').replace(/^\/+/, '');
}

function buildSnapshotUrl(fileName) {
  const cleanName = String(fileName || '').replace(/^\/+/, '');
  return `${snapshotBaseUrl}/${cleanName}`;
}

async function fetchJson(url) {
  const response = await fetch(url, { cache: 'no-store' }).catch(() => null);
  if (!response || !response.ok) {
    return null;
  }
  return response.json();
}

/**
 * 读取静态站点清单。存在该文件时，前端进入 static snapshot mode。
 */
export async function loadSiteManifest() {
  if (!siteManifestPromise) {
    siteManifestPromise = fetchJson(buildSnapshotUrl('site_manifest.json'));
  }
  return siteManifestPromise;
}

/**
 * 读取虚拟归档映射。
 * 该文件把 reports/config 中的 JSON、Markdown、CSV 映射成原有 adapter 可读的键。
 */
export async function loadArchiveCompatSnapshot() {
  if (!archiveCompatPromise) {
    archiveCompatPromise = (async () => {
      const manifest = await loadSiteManifest();
      if (!manifest) {
        return null;
      }
      return fetchJson(buildSnapshotUrl('archive_compat_snapshot.json'));
    })();
  }
  return archiveCompatPromise;
}

export async function isStaticSnapshotMode() {
  return Boolean(await loadSiteManifest());
}

export async function readStaticArchiveJson(relativePath) {
  const archive = await loadArchiveCompatSnapshot();
  const key = normalizeArchivePath(relativePath);
  if (!archive || !archive.json_files || !Object.prototype.hasOwnProperty.call(archive.json_files, key)) {
    return { found: false, value: null };
  }
  return { found: true, value: archive.json_files[key] };
}

export async function readStaticArchiveText(relativePath) {
  const archive = await loadArchiveCompatSnapshot();
  const key = normalizeArchivePath(relativePath);
  if (!archive || !archive.text_files || !Object.prototype.hasOwnProperty.call(archive.text_files, key)) {
    return { found: false, value: null };
  }
  return { found: true, value: archive.text_files[key] };
}

export { buildSnapshotUrl };
