import { useEffect, useMemo, useState } from 'react';
import { loadManualRiskPageData } from '../services/manualRiskAdapter.js';

/**
 * 读取 Manual Risk 页面所需的真实归档数据，并提供 loading / error / empty 状态。
 */
export function useManualRiskData() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;

    async function load() {
      setLoading(true);
      setError('');

      try {
        const snapshot = await loadManualRiskPageData();
        if (!active) {
          return;
        }
        setData(snapshot);
      } catch (loadError) {
        if (!active) {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : 'Failed to load manual risk archive');
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
      partial: Boolean(data?.partial),
    }),
    [data, loading, error],
  );
}
