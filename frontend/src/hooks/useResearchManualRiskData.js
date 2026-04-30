import { useEffect, useMemo, useState } from 'react';
import { loadResearchManualRiskPageData } from '../services/researchManualRiskAdapter.js';

export function useResearchManualRiskData() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;

    async function load() {
      setLoading(true);
      setError('');

      try {
        const snapshot = await loadResearchManualRiskPageData();
        if (!active) {
          return;
        }
        setData(snapshot);
      } catch (loadError) {
        if (!active) {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : 'Failed to load research/manual risk comparison');
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
