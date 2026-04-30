import { useEffect, useMemo, useState } from 'react';
import { loadMonthlyResearchManualRiskData } from '../services/monthlyResearchManualRiskAdapter.js';

export function useMonthlyResearchManualRiskData() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;

    async function load() {
      setLoading(true);
      setError('');

      try {
        const snapshot = await loadMonthlyResearchManualRiskData();
        if (!active) {
          return;
        }
        setData(snapshot);
      } catch (loadError) {
        if (!active) {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : 'Failed to load monthly research/manual risk alignment');
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

