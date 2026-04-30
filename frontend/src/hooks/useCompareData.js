import { useEffect, useMemo, useState } from 'react';
import { loadLatestComparePageData } from '../services/compareAdapter.js';

/**
 * 读取最新 compare 归档，并为页面提供 loading / error / empty 状态。
 */
export function useCompareData() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;

    async function load() {
      setLoading(true);
      setError('');

      try {
        const snapshot = await loadLatestComparePageData();
        if (!active) {
          return;
        }
        setData(snapshot);
      } catch (loadError) {
        if (!active) {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : 'Failed to load compare archive');
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
      empty: Boolean(data?.empty),
    }),
    [data, loading, error],
  );
}
