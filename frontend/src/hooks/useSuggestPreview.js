import { useEffect, useMemo, useState } from 'react';

function isPositiveNumber(value) {
  const parsed = Number(value);
  return Number.isFinite(parsed) && parsed > 0;
}

export function useSuggestPreview(suggestSummary, suggestedTargets) {
  const baseBudget = Number(suggestSummary?.budgetTotal ?? 0);
  const [budgetInput, setBudgetInput] = useState(baseBudget > 0 ? String(baseBudget) : '');

  useEffect(() => {
    setBudgetInput(baseBudget > 0 ? String(baseBudget) : '');
  }, [baseBudget]);

  const parsedBudget = isPositiveNumber(budgetInput) ? Number(budgetInput) : null;
  const previewBudget = parsedBudget ?? baseBudget;
  const ratio = baseBudget > 0 && previewBudget > 0 ? previewBudget / baseBudget : 1;
  const isPreview = baseBudget > 0 && parsedBudget !== null && parsedBudget !== baseBudget;
  const invalidInput = budgetInput.trim() !== '' && parsedBudget === null;

  const previewSummary = useMemo(() => ({
    baseBudget,
    previewBudget,
    isPreview,
    invalidInput,
    etfBudget: Number(suggestSummary?.budgetEtf ?? 0) * ratio,
    stockBudget: Number(suggestSummary?.budgetStock ?? 0) * ratio,
  }), [baseBudget, invalidInput, isPreview, previewBudget, ratio, suggestSummary?.budgetEtf, suggestSummary?.budgetStock]);

  const previewTargets = useMemo(
    () => (Array.isArray(suggestedTargets) ? suggestedTargets : []).map((item) => ({
      ...item,
      previewSuggestedAmount: Number(item.baseSuggestedAmount ?? 0) * ratio,
    })),
    [ratio, suggestedTargets],
  );

  function resetToDefault() {
    setBudgetInput(baseBudget > 0 ? String(baseBudget) : '');
  }

  return {
    budgetInput,
    setBudgetInput,
    previewSummary,
    previewTargets,
    resetToDefault,
  };
}
