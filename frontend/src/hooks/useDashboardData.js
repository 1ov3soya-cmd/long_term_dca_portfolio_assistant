import { useEffect, useMemo, useState } from 'react';
import { emptyDashboardData, mockDashboardData } from '../mock/latestData.js';
import { loadLatestDashboardSnapshot } from '../services/dashboardAdapter.js';

const runtimeEnv = (typeof import.meta !== 'undefined' && import.meta.env) ? import.meta.env : {};
const dashboardDataMode = (runtimeEnv.VITE_DASHBOARD_DATA_MODE || 'real').toLowerCase();
const allowMockFallback = (runtimeEnv.VITE_DASHBOARD_ALLOW_MOCK_FALLBACK || 'true').toLowerCase() !== 'false';

/**
 * Dashboard 数据 hook。
 * 支持 real / mock 两种模式，real 失败时可回退 mock。
 */
export function useDashboardData() {
  const [data, setData] = useState(() => (dashboardDataMode === 'mock' ? mockDashboardData : emptyDashboardData));
  const [loading, setLoading] = useState(dashboardDataMode !== 'mock');
  const [error, setError] = useState('');
  const [resolvedMode, setResolvedMode] = useState(dashboardDataMode);

  useEffect(() => {
    let active = true;

    async function load() {
      if (dashboardDataMode === 'mock') {
        setResolvedMode('mock');
        setData(mockDashboardData);
        setLoading(false);
        return;
      }

      setLoading(true);
      setError('');

      try {
        const snapshot = await loadLatestDashboardSnapshot();
        if (!active) {
          return;
        }
        setData(snapshot);
        setResolvedMode('real');
      } catch (loadError) {
        if (!active) {
          return;
        }

        const message = loadError instanceof Error ? loadError.message : '读取归档失败';
        setError(message);

        if (allowMockFallback) {
          setData(mockDashboardData);
          setResolvedMode('mock-fallback');
        } else {
          setData(emptyDashboardData);
          setResolvedMode('real-error');
        }
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    load();

    return () => {
      active = false;
    };
  }, []);

  return useMemo(
    () => ({
      data,
      loading,
      error,
      resolvedMode,
    }),
    [data, loading, error, resolvedMode],
  );
}
