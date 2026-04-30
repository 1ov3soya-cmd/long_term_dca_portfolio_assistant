import fs from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

const currentDir = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(currentDir, '..');
const archivePrefix = '/archive-data';
const basePath = process.env.VITE_BASE_PATH || '/';

function contentTypeFor(filePath) {
  const extension = path.extname(filePath).toLowerCase();
  if (extension === '.json') {
    return 'application/json; charset=utf-8';
  }
  if (extension === '.md') {
    return 'text/markdown; charset=utf-8';
  }
  if (extension === '.csv') {
    return 'text/csv; charset=utf-8';
  }
  return 'text/plain; charset=utf-8';
}

function createArchiveMiddleware() {
  return async (req, res, next) => {
    if (!req.url || !req.url.startsWith(archivePrefix)) {
      return next();
    }

    try {
      const relativePath = decodeURIComponent(req.url.slice(archivePrefix.length)).replace(/^\/+/, '');
      const resolvedPath = path.resolve(repoRoot, relativePath);

      if (!resolvedPath.startsWith(repoRoot)) {
        res.statusCode = 403;
        res.end('Forbidden');
        return;
      }

      const fileContent = await fs.readFile(resolvedPath);
      res.setHeader('Content-Type', contentTypeFor(resolvedPath));
      res.statusCode = 200;
      res.end(fileContent);
    } catch (error) {
      res.statusCode = 404;
      res.end('Not Found');
    }
  };
}

function archiveDataPlugin() {
  return {
    name: 'archive-data-plugin',
    configureServer(server) {
      server.middlewares.use(createArchiveMiddleware());
    },
    configurePreviewServer(server) {
      server.middlewares.use(createArchiveMiddleware());
    },
  };
}

export default defineConfig({
  base: basePath,
  plugins: [react(), archiveDataPlugin()],
  server: {
    fs: {
      allow: [repoRoot],
    },
  },
  preview: {
    host: '127.0.0.1',
    port: 4173,
  },
});
