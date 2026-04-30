import React from 'react';
import {
  Activity,
  ShieldAlert,
  BarChart3,
  FileSearch,
  ArrowRight,
  GitCompare,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  PauseCircle,
  Search,
  Brain,
  TrendingUp,
  TrendingDown,
  TriangleAlert,
} from 'lucide-react';
import { useDashboardData } from '../../hooks/useDashboardData.js';
import { useResearchData } from '../../hooks/useResearchData.js';
import { useResearchManualRiskData } from '../../hooks/useResearchManualRiskData.js';
import { useMonthlyResearchData } from '../../hooks/useMonthlyResearchData.js';
import { useMonthlyResearchManualRiskData } from '../../hooks/useMonthlyResearchManualRiskData.js';
import { useSuggestPreview } from '../../hooks/useSuggestPreview.js';
import {
  compactRunId,
  fallbackText,
  formatCurrency,
  formatPercent,
  joinSymbols,
} from '../../utils/formatters.js';
import { useTranslation } from 'react-i18next';

const MONTHLY_ALIGNMENT_PRIMARY_ROUTE = '#/research-manual-risk';

const Card = ({ title, icon: Icon, children, footerLink, footerText }) => (
  <div className="bg-slate-800 border border-slate-700 rounded-lg flex flex-col h-full">
    <div className="p-4 border-b border-slate-700 flex items-center gap-2">
      <Icon className="w-5 h-5 text-slate-400" />
      <h3 className="font-semibold text-slate-200">{title}</h3>
    </div>
    <div className="p-4 flex-1 flex flex-col gap-3 text-sm text-slate-300">
      {children}
    </div>
    {footerLink && (
      <div className="p-3 border-t border-slate-700 bg-slate-800/50">
        <a
          href={footerLink}
          className="flex items-center justify-end text-xs text-blue-400 hover:text-blue-300 transition-colors"
        >
          {footerText || 'View Details'} <ArrowRight className="w-3 h-3 ml-1" />
        </a>
      </div>
    )}
  </div>
);

const KVItem = ({ label, value, valueClass = 'text-slate-100 font-mono' }) => (
  <div className="flex justify-between items-center gap-4">
    <span className="text-slate-400">{label}</span>
    <span className={`${valueClass} text-right break-all`}>{fallbackText(value)}</span>
  </div>
);

const RiskBadge = ({ label, count, colorClass, icon: Icon }) => (
  <div className={`flex flex-col items-center justify-center p-3 rounded-md bg-slate-900 border border-slate-700 ${colorClass}`}>
    <Icon className="w-6 h-6 mb-1 opacity-80" />
    <span className="text-xl font-mono font-bold">{fallbackText(count, '0')}</span>
    <span className="text-[10px] tracking-wider uppercase opacity-70 mt-1 text-center leading-tight">{label}</span>
  </div>
);

function renderModeBadge(resolvedMode, t) {
  if (resolvedMode === 'real') {
    return t('common.realArchive');
  }
  if (resolvedMode === 'mock-fallback') {
    return t('common.mockFallback');
  }
  if (resolvedMode === 'mock') {
    return t('common.mockOnly');
  }
  return t('common.unavailable');
}

function sourceText(sourceType, t) {
  if (sourceType === 'researchIndex') {
    return t('research.sources.researchIndex');
  }
  if (sourceType === 'latestRunFallback') {
    return t('research.sources.latestRunFallback');
  }
  if (sourceType === 'acceptance') {
    return t('manualRisk.sources.acceptance');
  }
  if (sourceType === 'validation') {
    return t('manualRisk.sources.validation');
  }
  if (sourceType === 'latestRun') {
    return t('manualRisk.sources.latestRun');
  }
  if (sourceType === 'fallback') {
    return t('manualRisk.sources.fallback');
  }
  return t('common.dataUnavailable');
}

function researchLabelText(label, t) {
  if (label === 'pause_candidate') {
    return t('research.labels.pauseCandidate');
  }
  if (label === 'force_review_candidate') {
    return t('research.labels.forceReviewCandidate');
  }
  if (label === 'thesis_broken_candidate') {
    return t('research.labels.thesisBrokenCandidate');
  }
  if (label === 'neutral_watch') {
    return t('research.labels.neutralWatch');
  }
  return fallbackText(label, t('common.dataUnavailable'));
}

function suggestionActionLabel(item, t) {
  if (item.thesisBroken) {
    return t('dashboard.suggestDetail.tags.thesisBroken');
  }
  if (item.forceReview) {
    return t('dashboard.suggestDetail.tags.forceReview');
  }
  if (item.pauseBuy) {
    return t('dashboard.suggestDetail.tags.pauseBuy');
  }
  return t('dashboard.suggestDetail.tags.normal');
}

function suggestionActionClass(item) {
  if (item.thesisBroken) {
    return 'border-rose-700/70 bg-rose-950/35 text-rose-200';
  }
  if (item.forceReview) {
    return 'border-amber-700/70 bg-amber-950/35 text-amber-200';
  }
  if (item.pauseBuy) {
    return 'border-purple-700/70 bg-purple-950/35 text-purple-200';
  }
  return 'border-emerald-700/70 bg-emerald-950/30 text-emerald-200';
}

function suggestionRiskClass(riskStatus) {
  const normalized = String(riskStatus || '').toUpperCase();
  if (normalized === 'RED') {
    return 'border-rose-700/70 bg-rose-950/35 text-rose-200';
  }
  if (normalized === 'YELLOW') {
    return 'border-amber-700/70 bg-amber-950/35 text-amber-200';
  }
  if (normalized === 'GREEN') {
    return 'border-emerald-700/70 bg-emerald-950/30 text-emerald-200';
  }
  return 'border-slate-600/70 bg-slate-900/70 text-slate-200';
}

function monthlyResearchSourceLabel(sourceType, t) {
  if (sourceType === 'monthlyResearchIndex') {
    return t('monthlyResearch.sources.monthlyResearchIndex');
  }
  if (sourceType === 'latestRunFallback') {
    return t('monthlyResearch.sources.latestRunFallback');
  }
  if (sourceType === 'suggestRun') {
    return t('monthlyResearch.sources.suggestRun');
  }
  if (sourceType === 'shared_monthly_report') {
    return t('monthlyResearch.sources.sharedMonthlyReport');
  }
  return t('common.dataUnavailable');
}

export default function Dashboard() {
  const { t } = useTranslation();
  const { data, loading, error, resolvedMode } = useDashboardData();
  const research = useResearchData();
  const monthlyResearch = useMonthlyResearchData();
  const monthlyResearchAlignment = useMonthlyResearchManualRiskData();
  const alignment = useResearchManualRiskData();
  const {
    budgetInput,
    setBudgetInput,
    previewSummary,
    previewTargets,
    resetToDefault,
  } = useSuggestPreview(data.suggestSummary, data.suggestedTargets);
  const latestResearchItem = research.data?.items?.[0] || null;
  const highPrioritySymbols = (alignment.data?.items || [])
    .filter((item) => item.priorityLevel === 'high')
    .map((item) => item.symbol);

  return (
    <div className="text-slate-200 font-sans p-6">
      <div className="mb-8">
        <div className="flex flex-wrap items-center gap-3 mb-2">
          <h1 className="text-2xl font-bold text-slate-50 tracking-tight">{t('dashboard.title')}</h1>
          <span className="px-2.5 py-1 rounded border border-slate-700 bg-slate-800 text-[11px] tracking-[0.16em] text-slate-300">
            {renderModeBadge(resolvedMode, t)}
          </span>
          {loading && (
            <span className="px-2.5 py-1 rounded border border-blue-900 bg-blue-950/60 text-[11px] tracking-[0.12em] text-blue-300">
              {t('common.loadingArchive')}
            </span>
          )}
        </div>
        <p className="text-sm text-slate-400 mt-1">{t('dashboard.subtitle')}</p>
      </div>

      {error && (
        <div className="mb-6 rounded-lg border border-amber-800 bg-amber-950/40 px-4 py-3 text-sm text-amber-200">
          <div className="font-medium">{t('common.archiveReadIssue')}</div>
          <div className="mt-1 text-amber-300/90 break-all">{error}</div>
        </div>
      )}

      {!loading && resolvedMode !== 'real' && (
        <div className="mb-6 rounded-lg border border-slate-700 bg-slate-800/80 px-4 py-3 text-sm text-slate-300">
          {t('common.archiveFallbackHint')}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-6">
        <div className="lg:col-span-4">
          <Card title={t('dashboard.cards.latestRuns')} icon={Activity}>
            <KVItem label={t('dashboard.labels.suggest')} value={data.overview.latestSuggest} />
            <KVItem label={t('dashboard.labels.backtest')} value={data.overview.latestBacktest} />
            <KVItem label={t('dashboard.labels.robustness')} value={data.overview.latestRobustness} />
            <KVItem label={t('dashboard.labels.compare')} value={data.overview.latestCompare} />
            <div className="h-px bg-slate-700 my-1"></div>
            <KVItem
              label={t('dashboard.labels.dataMode')}
              value={String(data.overview.mode || 'N/A').toUpperCase()}
              valueClass="text-emerald-400 font-mono font-bold"
            />
            <KVItem label={t('dashboard.labels.adjMode')} value={data.overview.adjMode} valueClass="text-blue-400 font-mono" />
          </Card>
        </div>

        <div className="lg:col-span-4">
          <Card title={t('dashboard.cards.activeConfig')} icon={FileSearch}>
            <KVItem label={t('dashboard.labels.assetAllocation')} value={data.configSummary.allocation} />
            <KVItem label={t('dashboard.labels.executionRule')} value={data.configSummary.monthlyRule} />
            <KVItem label={t('dashboard.labels.etfLogic')} value={data.configSummary.etfRiskLevel} />
            <KVItem label={t('dashboard.labels.stockLogic')} value={data.configSummary.stockRiskLevel} valueClass="text-amber-400 font-mono" />
            <div className="h-px bg-slate-700 my-1"></div>
            <KVItem
              label={t('dashboard.labels.manualRiskEngine')}
              value={data.configSummary.manualRiskEnabled ? t('dashboard.status.enabled') : t('dashboard.status.disabled')}
              valueClass={data.configSummary.manualRiskEnabled ? 'text-emerald-400 font-bold' : 'text-slate-400 font-bold'}
            />
            <KVItem label={t('common.environment')} value={data.configSummary.env} />
          </Card>
        </div>

        <div className="lg:col-span-4">
          <Card title={t('dashboard.cards.riskMatrix')} icon={ShieldAlert}>
            <div className="grid grid-cols-3 gap-2 flex-1">
              <RiskBadge label={t('dashboard.status.green')} count={data.riskLights.GREEN} colorClass="text-emerald-400" icon={CheckCircle2} />
              <RiskBadge label={t('dashboard.status.yellow')} count={data.riskLights.YELLOW} colorClass="text-amber-400" icon={AlertTriangle} />
              <RiskBadge label={t('dashboard.status.red')} count={data.riskLights.RED} colorClass="text-rose-500" icon={XCircle} />
              <RiskBadge label={t('dashboard.status.pause')} count={data.riskLights.MANUAL_PAUSE} colorClass="text-purple-400" icon={PauseCircle} />
              <RiskBadge label={t('dashboard.status.review')} count={data.riskLights.FORCE_REVIEW} colorClass="text-orange-400" icon={Search} />
              <RiskBadge label={t('dashboard.status.broken')} count={data.riskLights.THESIS_BROKEN} colorClass="text-red-600" icon={ShieldAlert} />
            </div>
          </Card>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <Card title={t('dashboard.cards.monthlySuggestion')} icon={BarChart3}>
          <div className="rounded-md border border-slate-700 bg-slate-900/70 p-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="text-xs uppercase tracking-[0.14em] text-slate-500">
                  {t('dashboard.preview.title')}
                </div>
                <div className="mt-1 text-xs text-slate-400">
                  {t('dashboard.preview.note')}
                </div>
              </div>
              <div className="flex items-center gap-2">
                {previewSummary.isPreview && (
                  <span className="rounded border border-blue-900 bg-blue-950/60 px-2 py-1 text-[11px] tracking-[0.12em] text-blue-300">
                    {t('dashboard.preview.mode')}
                  </span>
                )}
                <button
                  type="button"
                  onClick={resetToDefault}
                  className="rounded border border-slate-700 px-3 py-1.5 text-xs text-slate-300 transition-colors hover:border-slate-500 hover:text-slate-100"
                >
                  {t('dashboard.preview.reset')}
                </button>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-3">
              <label className="text-xs uppercase tracking-[0.14em] text-slate-500" htmlFor="monthly-budget-preview">
                {t('dashboard.preview.inputLabel')}
              </label>
              <input
                id="monthly-budget-preview"
                type="number"
                min="0"
                step="100"
                value={budgetInput}
                onChange={(event) => setBudgetInput(event.target.value)}
                className="w-40 rounded border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none transition-colors focus:border-blue-500"
              />
            </div>
            {previewSummary.invalidInput && (
              <div className="mt-2 text-xs text-amber-300">
                {t('dashboard.preview.invalid')}
              </div>
            )}
          </div>

          <div className="flex gap-4 mb-2">
            <div className="bg-slate-900 p-4 rounded-md border border-slate-700 flex-1">
              <div className="text-slate-400 text-xs uppercase mb-1">{t('dashboard.labels.totalBudget')}</div>
              <div className="text-2xl font-mono text-slate-100">{formatCurrency(previewSummary.previewBudget)}</div>
            </div>
            <div className="bg-slate-900 p-4 rounded-md border border-slate-700 flex-1">
              <div className="text-slate-400 text-xs uppercase mb-1">{t('dashboard.labels.etfStockSplit')}</div>
              <div className="text-xl font-mono text-slate-300">
                <span className="text-blue-400">{formatCurrency(previewSummary.etfBudget)}</span>
                {' / '}
                <span className="text-indigo-400">{formatCurrency(previewSummary.stockBudget)}</span>
              </div>
            </div>
          </div>
          <KVItem label={t('dashboard.labels.buyTargets')} value={data.suggestSummary.buyTargets} />
          <KVItem label={t('dashboard.labels.pausedTargets')} value={data.suggestSummary.pausedTargets} valueClass="text-purple-400 font-mono" />
          <KVItem label={t('dashboard.labels.forceReviewTargets')} value={data.suggestSummary.forceReviewTargets} valueClass="text-amber-400 font-mono" />
          <KVItem label={t('dashboard.labels.thesisBrokenTargets')} value={data.suggestSummary.thesisBrokenTargets} valueClass="text-rose-400 font-mono" />
          <div className="mt-2 rounded-md border border-slate-700 bg-slate-900/70 p-3">
            <div className="mb-3 flex items-center justify-between gap-3">
              <div className="text-xs uppercase tracking-[0.14em] text-slate-500">
                {t('dashboard.suggestDetail.title')}
              </div>
              <div className="text-xs text-slate-400">
                {previewSummary.isPreview ? t('dashboard.preview.mode') : t('dashboard.preview.defaultMode')}
              </div>
            </div>
            {previewTargets.length === 0 ? (
              <div className="text-sm text-slate-400">
                {t('dashboard.suggestDetail.empty')}
              </div>
            ) : (
              <div className="overflow-x-auto rounded-md border border-slate-700/70">
                <table className="min-w-full text-left text-sm text-slate-200">
                  <thead className="bg-slate-900/90 text-[12px] text-slate-300">
                    <tr className="border-b border-slate-700">
                      <th className="px-3 py-2.5 font-semibold whitespace-nowrap">{t('dashboard.suggestDetail.columns.symbol')}</th>
                      <th className="px-3 py-2.5 font-semibold whitespace-nowrap">{t('dashboard.suggestDetail.columns.type')}</th>
                      <th className="px-3 py-2.5 font-semibold whitespace-nowrap">{t('dashboard.suggestDetail.columns.amount')}</th>
                      <th className="px-3 py-2.5 font-semibold whitespace-nowrap min-w-[128px]">{t('dashboard.suggestDetail.columns.action')}</th>
                      <th className="px-3 py-2.5 font-semibold whitespace-nowrap min-w-[110px]">{t('dashboard.suggestDetail.columns.risk')}</th>
                      <th className="px-3 py-2.5 font-semibold">{t('dashboard.suggestDetail.columns.reason')}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {previewTargets.map((item) => (
                      <tr key={item.symbol} className="border-b border-slate-800 align-top transition-colors hover:bg-slate-900/50">
                        <td className="px-3 py-2.5 font-mono text-[14px] font-semibold text-slate-50 whitespace-nowrap">{item.symbol}</td>
                        <td className="px-3 py-2.5 text-slate-300 whitespace-nowrap">
                          <span className="rounded border border-slate-700/80 bg-slate-900 px-2 py-1 text-xs tracking-wide uppercase">
                            {item.assetType}
                          </span>
                        </td>
                        <td className="px-3 py-2.5 font-mono text-[14px] font-semibold text-blue-300 whitespace-nowrap">
                          {formatCurrency(item.previewSuggestedAmount)}
                        </td>
                        <td className="px-3 py-2.5 whitespace-nowrap">
                          <span className={`inline-flex items-center rounded-md border px-2.5 py-1 text-xs font-medium whitespace-nowrap ${suggestionActionClass(item)}`}>
                            {suggestionActionLabel(item, t)}
                          </span>
                        </td>
                        <td className="px-3 py-2.5 whitespace-nowrap">
                          <span className={`inline-flex items-center rounded-md border px-2.5 py-1 text-xs font-medium whitespace-nowrap ${suggestionRiskClass(item.riskStatus)}`}>
                            {fallbackText(item.riskStatus, t('common.dataUnavailable'))}
                          </span>
                        </td>
                        <td className="px-3 py-2.5 text-slate-400 leading-6">
                          {fallbackText(item.note, t('common.dataUnavailable'))}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </Card>

        <Card
          title={t('dashboard.cards.monthlyResearchDebateSummary')}
          icon={Brain}
          footerLink="#/monthly-research"
          footerText={t('dashboard.actions.viewMonthlyResearch')}
        >
          {monthlyResearch.loading ? (
            <div className="text-slate-400">{t('monthlyResearch.loading')}</div>
          ) : monthlyResearch.error || monthlyResearch.empty || !monthlyResearch.data ? (
            <div className="space-y-2">
              <div className="text-slate-300">{t('monthlyResearch.emptyTitle')}</div>
              <div className="text-xs text-slate-500">{t('monthlyResearch.emptyHint')}</div>
              <pre className="mt-2 overflow-x-auto rounded border border-slate-800 bg-slate-950/80 p-3 text-xs text-slate-300">
                python -m src.main run-monthly-research --end-date 2025-12-31
              </pre>
            </div>
          ) : (
            <>
              <div className="rounded-md border border-slate-700 bg-slate-900/70 p-3">
                <div className="grid grid-cols-2 gap-3 xl:grid-cols-3">
                  <div>
                    <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500">{t('monthlyResearch.labels.totalTargets')}</div>
                    <div className="mt-1 text-xl font-mono text-slate-100">{monthlyResearch.data.summary.totalTargets}</div>
                  </div>
                  <div>
                    <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500">{t('monthlyResearch.labels.processedTargets')}</div>
                    <div className="mt-1 text-xl font-mono text-blue-400">{monthlyResearch.data.summary.processedTargets}</div>
                  </div>
                  <div>
                    <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500">{t('monthlyResearch.labels.averageConfidence')}</div>
                    <div className="mt-1 text-xl font-mono text-emerald-400">{formatPercent(monthlyResearch.data.summary.averageConfidence)}</div>
                  </div>
                  <div>
                    <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500">{t('monthlyResearch.labels.pauseCandidateCount')}</div>
                    <div className="mt-1 text-xl font-mono text-purple-400">{monthlyResearch.data.summary.pauseCandidateCount}</div>
                  </div>
                  <div>
                    <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500">{t('monthlyResearch.labels.forceReviewCandidateCount')}</div>
                    <div className="mt-1 text-xl font-mono text-amber-400">{monthlyResearch.data.summary.forceReviewCandidateCount}</div>
                  </div>
                  <div>
                    <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500">{t('monthlyResearch.labels.thesisBrokenCandidateCount')}</div>
                    <div className="mt-1 text-xl font-mono text-rose-400">{monthlyResearch.data.summary.thesisBrokenCandidateCount}</div>
                  </div>
                </div>
                <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-slate-800 pt-3 text-xs text-slate-400">
                  <span>{t('monthlyResearch.labels.lastUpdated')}: {fallbackText(monthlyResearch.data.meta.updatedAt)}</span>
                  <span>{t('monthlyResearch.labels.batchId')}: {compactRunId(monthlyResearch.data.meta.batchId, 24)}</span>
                  <span>{t('monthlyResearch.labels.dataSource')}: {monthlyResearchSourceLabel(monthlyResearch.data.meta.sourceType, t)}</span>
                </div>
                <div className="mt-2 text-xs text-slate-400">
                  {t('monthlyResearch.labels.topAttentionSymbols')}: {joinSymbols(monthlyResearch.data.summary.topAttentionSymbols, t('common.dataUnavailable'))}
                </div>
              </div>

              <div className="rounded-md border border-slate-700 bg-slate-900/70 p-3">
                <div className="mb-3 flex items-center justify-between gap-3">
                  <div className="text-xs uppercase tracking-[0.14em] text-slate-500">
                    {t('monthlyResearch.alignment.title')}
                  </div>
                  <a
                    href={MONTHLY_ALIGNMENT_PRIMARY_ROUTE}
                    className="text-[11px] text-blue-400 transition-colors hover:text-blue-300"
                  >
                    {t('dashboard.actions.viewAlignment')}
                  </a>
                </div>
                {monthlyResearchAlignment.loading ? (
                  <div className="text-sm text-slate-400">{t('common.loading')}</div>
                ) : monthlyResearchAlignment.error || monthlyResearchAlignment.empty || !monthlyResearchAlignment.data ? (
                  <div className="space-y-1">
                    <div className="text-sm text-slate-300">{t('common.dataUnavailable')}</div>
                    <div className="text-xs text-slate-500">{t('monthlyResearch.alignment.empty')}</div>
                  </div>
                ) : (
                  <>
                    <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
                      <div>
                        <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500">
                          {t('monthlyResearch.alignment.matched')}
                        </div>
                        <div className="mt-1 text-xl font-mono text-emerald-400">
                          {monthlyResearchAlignment.data.summary.matchedCount}
                        </div>
                      </div>
                      <div>
                        <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500">
                          {t('monthlyResearch.alignment.unmatched')}
                        </div>
                        <div className="mt-1 text-xl font-mono text-amber-400">
                          {monthlyResearchAlignment.data.summary.unmatchedCount}
                        </div>
                      </div>
                      <div>
                        <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500">
                          {t('monthlyResearch.alignment.highPriority')}
                        </div>
                        <div className="mt-1 text-xl font-mono text-rose-400">
                          {monthlyResearchAlignment.data.summary.highPriorityCount}
                        </div>
                      </div>
                    </div>
                    <div className="mt-3 text-xs text-slate-400">
                      {t('monthlyResearch.alignment.attentionSymbols')}: {joinSymbols(monthlyResearchAlignment.data.summary.topAttentionSymbols, t('common.dataUnavailable'))}
                    </div>
                    {monthlyResearchAlignment.data.summary.unmatchedCount > 0 ? (
                      <div className="mt-2 text-xs text-amber-300">
                        {t('monthlyResearch.alignment.notReflected')}
                      </div>
                    ) : (
                      <div className="mt-2 text-xs text-emerald-300">
                        {t('monthlyResearch.alignment.covered')}
                      </div>
                    )}
                  </>
                )}
              </div>

              {monthlyResearch.data.dashboardSummary.featuredItems.length === 0 ? (
                <div className="rounded-md border border-slate-700 bg-slate-900/50 p-3 text-sm text-slate-400">
                  {t('monthlyResearch.emptyFeatured')}
                </div>
              ) : (
                <div className="space-y-3">
                  {monthlyResearch.data.dashboardSummary.featuredItems.map((item) => (
                    <div key={item.symbol} className="rounded-md border border-slate-700 bg-slate-900/60 p-3">
                      <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                        <div>
                          <div className="flex items-center gap-2">
                            <span className="font-mono text-base text-slate-100">{item.symbol}</span>
                            <span className="rounded border border-slate-700 px-2 py-0.5 text-[11px] text-slate-300">
                              {researchLabelText(item.finalResearchLabel, t)}
                            </span>
                          </div>
                          {item.displayName ? (
                            <div className="mt-1 text-xs text-slate-400">{item.displayName}</div>
                          ) : null}
                          <div className="mt-1 text-xs text-slate-400">
                            {item.assetType} · {t('monthlyResearch.labels.suggestedAmount')}: {formatCurrency(item.suggestedAmount)}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-[11px] uppercase tracking-[0.14em] text-slate-500">{t('monthlyResearch.labels.confidence')}</div>
                          <div className="mt-1 font-mono text-emerald-400">{formatPercent(item.confidence)}</div>
                        </div>
                      </div>

                      <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
                        <div className="rounded-md border border-emerald-900/70 bg-emerald-950/25 p-3">
                          <div className="mb-2 flex items-center gap-2 text-emerald-300">
                            <TrendingUp className="h-4 w-4" />
                            <span className="text-[11px] uppercase tracking-[0.14em]">{t('monthlyResearch.labels.bullCase')}</span>
                          </div>
                          <div className="text-sm leading-6 text-emerald-100/90">
                            {fallbackText(item.bullCaseShort, t('common.dataUnavailable'))}
                          </div>
                        </div>

                        <div className="rounded-md border border-rose-900/70 bg-rose-950/25 p-3">
                          <div className="mb-2 flex items-center gap-2 text-rose-300">
                            <TrendingDown className="h-4 w-4" />
                            <span className="text-[11px] uppercase tracking-[0.14em]">{t('monthlyResearch.labels.bearCase')}</span>
                          </div>
                          <div className="text-sm leading-6 text-rose-100/90">
                            {fallbackText(item.bearCaseShort, t('common.dataUnavailable'))}
                          </div>
                        </div>
                      </div>

                      <div className="mt-3 rounded-md border border-amber-900/60 bg-amber-950/20 p-3">
                        <div className="mb-2 flex items-center gap-2 text-amber-300">
                          <TriangleAlert className="h-4 w-4" />
                          <span className="text-[11px] uppercase tracking-[0.14em]">{t('monthlyResearch.labels.riskSummary')}</span>
                        </div>
                        <div className="text-sm leading-6 text-slate-300">
                          {fallbackText(item.riskSummaryShort, t('common.dataUnavailable'))}
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </>
          )}
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card title={t('dashboard.cards.manualRiskFlags')} icon={ShieldAlert} footerLink="#/manual-risk" footerText={t('common.viewDetails')}>
          <KVItem label={t('dashboard.labels.pausedSymbols')} value={joinSymbols(data.manualRisk.paused, t('common.dataUnavailable'))} valueClass="text-purple-400 font-mono" />
          <KVItem label={t('dashboard.labels.forceReview')} value={joinSymbols(data.manualRisk.forceReview, t('common.dataUnavailable'))} valueClass="text-orange-400 font-mono" />
          <KVItem label={t('dashboard.labels.thesisBroken')} value={joinSymbols(data.manualRisk.thesisBroken, t('common.dataUnavailable'))} valueClass="text-rose-500 font-mono" />
          <KVItem label={t('common.effectiveFrom')} value={data.manualRisk.effectiveFrom} />
          <div className="mt-2 p-3 bg-slate-900 border border-slate-700 rounded text-xs text-slate-400 italic">
            "{fallbackText(data.manualRisk.notePreview, t('dashboard.fallbackNote'))}"
          </div>
        </Card>

        <Card title={t('dashboard.cards.robustness')} icon={CheckCircle2}>
          <KVItem
            label={t('dashboard.labels.baselineRobustness')}
            value={data.robustness.isBaselineRobust ? t('dashboard.status.pass') : data.robustness.label || 'N/A'}
            valueClass={data.robustness.isBaselineRobust ? 'text-emerald-400 font-bold' : 'text-rose-500 font-bold'}
          />
          <KVItem label={t('dashboard.labels.keepDefaultParams')} value={data.robustness.keepDefaultParams ? t('common.yes') : t('common.no')} />
          <div className="h-px bg-slate-700 my-1"></div>
          <KVItem label={t('dashboard.labels.highSensitivityParam')} value={data.robustness.mostSensitive} valueClass="text-amber-400 font-mono text-xs" />
          <KVItem label={t('dashboard.labels.mostStableParam')} value={data.robustness.mostRobust} valueClass="text-emerald-400 font-mono text-xs" />
        </Card>

        <Card title={t('dashboard.cards.latestCompare')} icon={GitCompare} footerLink="#/compare" footerText={t('common.viewDetails')}>
          <div className="flex items-center justify-between bg-slate-900 p-2 rounded border border-slate-700 mb-2 gap-2">
            <span className="text-xs font-mono text-slate-400">{compactRunId(data.compare.runA, 14)}</span>
            <span className="text-xs text-slate-500">vs</span>
            <span className="text-xs font-mono text-slate-400">{compactRunId(data.compare.runB, 14)}</span>
          </div>
          <KVItem label={t('dashboard.labels.comparableLevel')} value={data.compare.comparableLevel} valueClass="text-emerald-400 font-bold" />
          <div className="mt-2 text-xs">
            <div className="text-slate-500 mb-1">{t('dashboard.labels.topConfigChange')}:</div>
            <div className="text-slate-300 font-mono bg-slate-800 p-1 rounded">{fallbackText(data.compare.topConfigChange, t('common.dataUnavailable'))}</div>
          </div>
          <div className="mt-2 text-xs">
            <div className="text-slate-500 mb-1">{t('dashboard.labels.topSummaryChange')}:</div>
            <div className="text-slate-300 font-mono bg-slate-800 p-1 rounded">{fallbackText(data.compare.topSummaryChange, t('common.dataUnavailable'))}</div>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        <Card title={t('dashboard.cards.latestResearch')} icon={Brain} footerLink="#/research" footerText={t('dashboard.actions.viewResearch')}>
          {research.loading ? (
            <div className="text-slate-400">{t('research.loading')}</div>
          ) : research.error || research.empty || !research.data ? (
            <div className="space-y-2">
              <div className="text-slate-300">{t('common.dataUnavailable')}</div>
              <div className="text-xs text-slate-500">{t('research.emptyHint')}</div>
            </div>
          ) : (
            <>
              <KVItem label={t('research.labels.latestSymbol')} value={research.data.meta.latestSymbol} />
              <KVItem label={t('research.labels.latestAnalysisDate')} value={research.data.meta.latestAnalysisDate} />
              <KVItem
                label={t('research.labels.researchLabel')}
                value={researchLabelText(latestResearchItem?.finalResearchLabel, t)}
                valueClass="text-slate-100"
              />
              <KVItem
                label={t('research.labels.confidence')}
                value={latestResearchItem ? formatPercent(latestResearchItem.confidence) : t('common.notApplicable')}
              />
              <div className="h-px bg-slate-700 my-1"></div>
              <KVItem label={t('research.labels.pauseCandidateCount')} value={research.data.summary.pauseCandidateCount} valueClass="text-purple-400 font-mono" />
              <KVItem label={t('research.labels.forceReviewCandidateCount')} value={research.data.summary.forceReviewCandidateCount} valueClass="text-amber-400 font-mono" />
              <KVItem label={t('research.labels.thesisBrokenCandidateCount')} value={research.data.summary.thesisBrokenCandidateCount} valueClass="text-rose-400 font-mono" />
            </>
          )}
        </Card>

        <Card title={t('dashboard.cards.researchManualRiskAlignment')} icon={ShieldAlert} footerLink="#/research-manual-risk" footerText={t('dashboard.actions.viewAlignment')}>
          {alignment.loading ? (
            <div className="text-slate-400">{t('researchManualRisk.loading')}</div>
          ) : alignment.error || alignment.empty || !alignment.data ? (
            <div className="space-y-2">
              <div className="text-slate-300">{t('common.dataUnavailable')}</div>
              <div className="text-xs text-slate-500">{t('researchManualRisk.emptyHint')}</div>
            </div>
          ) : (
            <>
              <KVItem label={t('researchManualRisk.summary.matchedCount')} value={alignment.data.summary.matchedCount} valueClass="text-emerald-400 font-mono" />
              <KVItem label={t('researchManualRisk.summary.mismatchedCount')} value={alignment.data.summary.mismatchedCount} valueClass="text-amber-400 font-mono" />
              <KVItem label={t('researchManualRisk.summary.highPriorityCount')} value={alignment.data.summary.highPriorityCount} valueClass="text-rose-400 font-mono" />
              <KVItem
                label={t('dashboard.labels.attentionSymbols')}
                value={highPrioritySymbols.length > 0 ? joinSymbols(highPrioritySymbols.slice(0, 3), t('common.dataUnavailable')) : t('common.dataUnavailable')}
                valueClass="text-slate-100 font-mono"
              />
              <div className="h-px bg-slate-700 my-1"></div>
              <KVItem label={t('dashboard.labels.researchSource')} value={sourceText(alignment.data.meta.researchSourceType, t)} />
              <KVItem label={t('dashboard.labels.manualRiskSource')} value={sourceText(alignment.data.meta.manualSourceType, t)} />
            </>
          )}
        </Card>
      </div>
    </div>
  );
}
