import { Brain, FileSearch, ShieldAlert, StickyNote, TrendingDown, TrendingUp, TriangleAlert } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useMonthlyResearchData } from '../../hooks/useMonthlyResearchData.js';
import { useMonthlyResearchManualRiskData } from '../../hooks/useMonthlyResearchManualRiskData.js';
import { compactRunId, fallbackText, formatCurrency, formatPercent, joinSymbols } from '../../utils/formatters.js';

const ALIGNMENT_PREVIEW_ROW_LIMIT = 5;

const Card = ({ title, icon: Icon, children }) => (
  <div className="flex h-full flex-col rounded-lg border border-slate-700 bg-slate-800">
    <div className="flex items-center gap-2 border-b border-slate-700 p-4">
      <Icon className="h-5 w-5 text-slate-400" />
      <h3 className="font-semibold text-slate-200">{title}</h3>
    </div>
    <div className="flex flex-1 flex-col gap-3 p-4 text-sm text-slate-300">
      {children}
    </div>
  </div>
);

const KVItem = ({ label, value, valueClass = 'font-mono text-slate-100' }) => (
  <div className="flex items-start justify-between gap-4">
    <span className="text-slate-400">{label}</span>
    <span className={`${valueClass} break-all text-right`}>{fallbackText(value)}</span>
  </div>
);

const SummaryCard = ({ label, value, accentClass = 'text-slate-100' }) => (
  <div className="rounded-md border border-slate-700 bg-slate-900 p-4">
    <div className="text-xs uppercase tracking-[0.14em] text-slate-500">{label}</div>
    <div className={`mt-2 text-2xl font-mono ${accentClass}`}>{fallbackText(value, '0')}</div>
  </div>
);

const EvidenceList = ({ points, emptyText }) => {
  if (!Array.isArray(points) || points.length === 0) {
    return <div className="text-sm text-slate-400">{emptyText}</div>;
  }
  return (
    <ul className="list-disc space-y-1 pl-4 text-sm leading-6 text-slate-300">
      {points.map((point, index) => (
        <li key={`${point}-${index}`}>{point}</li>
      ))}
    </ul>
  );
};

const ScrollableText = ({ text, placeholder, maxHeightClass = 'max-h-56' }) => (
  <div className={`overflow-y-auto pr-1 ${maxHeightClass}`}>
    <div className="whitespace-pre-wrap text-sm leading-6">
      {fallbackText(text, placeholder)}
    </div>
  </div>
);

function labelText(label, t) {
  if (label === 'pause_candidate') {
    return t('monthlyResearch.labels.pauseCandidate');
  }
  if (label === 'force_review_candidate') {
    return t('monthlyResearch.labels.forceReviewCandidate');
  }
  if (label === 'thesis_broken_candidate') {
    return t('monthlyResearch.labels.thesisBrokenCandidate');
  }
  if (label === 'neutral_watch') {
    return t('monthlyResearch.labels.neutralWatch');
  }
  return fallbackText(label, t('common.dataUnavailable'));
}

function yesNo(value, t) {
  return value ? t('common.yes') : t('common.no');
}

function sourceLabel(sourceType, t) {
  if (sourceType === 'monthlyResearchIndex') {
    return t('monthlyResearch.sources.monthlyResearchIndex');
  }
  if (sourceType === 'latestRunFallback') {
    return t('monthlyResearch.sources.latestRunFallback');
  }
  if (sourceType === 'suggest_run') {
    return t('monthlyResearch.sources.suggestRun');
  }
  if (sourceType === 'shared_monthly_report') {
    return t('monthlyResearch.sources.sharedMonthlyReport');
  }
  return t('common.dataUnavailable');
}

function alignmentReasonText(code, t) {
  if (code === 'thesis_broken_not_reflected') {
    return t('monthlyResearch.alignment.reasons.thesisBrokenNotReflected');
  }
  if (code === 'force_review_not_reflected') {
    return t('monthlyResearch.alignment.reasons.forceReviewNotReflected');
  }
  if (code === 'pause_buy_not_reflected') {
    return t('monthlyResearch.alignment.reasons.pauseBuyNotReflected');
  }
  if (code === 'covered_by_manual_risk') {
    return t('monthlyResearch.alignment.reasons.coveredByManualRisk');
  }
  return t('monthlyResearch.alignment.reasons.noCandidateSignal');
}

function priorityText(priorityLevel, t) {
  if (priorityLevel === 'high') {
    return t('researchManualRisk.priority.high');
  }
  if (priorityLevel === 'medium') {
    return t('researchManualRisk.priority.medium');
  }
  return t('researchManualRisk.priority.low');
}

export default function MonthlyResearch() {
  const { t } = useTranslation();
  const { data, loading, error, empty, partial } = useMonthlyResearchData();
  const alignment = useMonthlyResearchManualRiskData();
  const selectedDefault = useMemo(() => data?.items?.[0]?.id || '', [data]);
  const [selectedId, setSelectedId] = useState('');
  const activeId = selectedId || selectedDefault;
  const selectedItem = data?.items?.find((item) => item.id === activeId) || data?.items?.[0] || null;
  const selectedDebate = selectedItem?.analystDebate || {
    debateFocus: selectedItem?.debateFocus || '',
    keyUncertainty: selectedItem?.keyUncertainty || '',
    recommendationRationale: selectedItem?.recommendationRationale || '',
    bull: {
      summary: selectedItem?.bullCase || '',
      summaryPreview: selectedItem?.bullCasePreview || '',
      evidencePoints: selectedItem?.bullEvidencePoints || [],
      actionImplication: selectedItem?.bullActionImplication || '',
    },
    bear: {
      summary: selectedItem?.bearCase || '',
      summaryPreview: selectedItem?.bearCasePreview || '',
      evidencePoints: selectedItem?.bearEvidencePoints || [],
      actionImplication: selectedItem?.bearActionImplication || '',
    },
    riskSummary: selectedItem?.riskSummary || '',
    riskSummaryPreview: selectedItem?.riskSummaryPreview || '',
  };

  if (loading) {
    return (
      <div className="p-6">
        <div className="rounded-lg border border-slate-800 bg-slate-900/70 px-4 py-3 text-sm text-slate-300">
          {t('monthlyResearch.loading')}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="rounded-lg border border-amber-800 bg-amber-950/40 px-4 py-3 text-sm text-amber-200">
          <div className="font-medium">{t('common.archiveReadIssue')}</div>
          <div className="mt-1 break-all">{error}</div>
        </div>
      </div>
    );
  }

  if (empty || !data) {
    return (
      <div className="p-6">
        <div className="rounded-lg border border-slate-800 bg-slate-900/70 px-4 py-3 text-sm text-slate-300">
          <div className="font-medium">{t('monthlyResearch.emptyTitle')}</div>
          <div className="mt-1 text-slate-400">{t('monthlyResearch.emptyHint')}</div>
          <pre className="mt-3 overflow-x-auto rounded border border-slate-800 bg-slate-950/80 p-3 text-xs text-slate-300">
            python -m src.main run-monthly-research --end-date 2025-12-31
          </pre>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 text-slate-200">
      <div className="mb-8">
        <div className="mb-2 flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight text-slate-50">{t('monthlyResearch.title')}</h1>
          <span className="rounded border border-slate-700 bg-slate-800 px-2.5 py-1 text-[11px] uppercase tracking-[0.16em] text-slate-300">
            {sourceLabel(data.meta.sourceType, t)}
          </span>
        </div>
        <p className="text-sm text-slate-400">{t('monthlyResearch.subtitle')}</p>
      </div>

      {partial && (
        <div className="mb-6 rounded-lg border border-slate-700 bg-slate-800/80 px-4 py-3 text-sm text-slate-300">
          <div className="font-medium">{t('common.partialData')}</div>
          <div className="mt-1 text-slate-400">
            {t('monthlyResearch.labels.missingFiles')}: {data.files.missing.join(', ') || t('common.dataUnavailable')}
          </div>
        </div>
      )}

      <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-12">
        <div className="lg:col-span-4">
          <Card title={t('monthlyResearch.sections.overview')} icon={Brain}>
            <KVItem label={t('monthlyResearch.labels.dataSource')} value={sourceLabel(data.meta.sourceType, t)} />
            <KVItem label={t('monthlyResearch.labels.lastUpdated')} value={data.meta.updatedAt} />
            <KVItem label={t('monthlyResearch.labels.batchId')} value={data.meta.batchId} />
            <KVItem label={t('monthlyResearch.labels.sourceSuggestRun')} value={compactRunId(data.meta.sourceSuggestRun, 24)} />
            <KVItem label={t('monthlyResearch.labels.totalTargets')} value={data.summary.totalTargets} />
          </Card>
        </div>

        <div className="lg:col-span-8">
          <Card title={t('monthlyResearch.sections.summary')} icon={ShieldAlert}>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-6">
              <SummaryCard label={t('monthlyResearch.labels.totalTargets')} value={data.summary.totalTargets} accentClass="text-slate-100" />
              <SummaryCard label={t('monthlyResearch.labels.processedTargets')} value={data.summary.processedTargets} accentClass="text-blue-400" />
              <SummaryCard label={t('monthlyResearch.labels.pauseCandidateCount')} value={data.summary.pauseCandidateCount} accentClass="text-purple-400" />
              <SummaryCard label={t('monthlyResearch.labels.forceReviewCandidateCount')} value={data.summary.forceReviewCandidateCount} accentClass="text-amber-400" />
              <SummaryCard label={t('monthlyResearch.labels.thesisBrokenCandidateCount')} value={data.summary.thesisBrokenCandidateCount} accentClass="text-rose-400" />
              <SummaryCard label={t('monthlyResearch.labels.averageConfidence')} value={formatPercent(data.summary.averageConfidence)} accentClass="text-emerald-400" />
            </div>
            <KVItem label={t('monthlyResearch.labels.topAttentionSymbols')} value={joinSymbols(data.summary.topAttentionSymbols, t('common.dataUnavailable'))} />
          </Card>
        </div>
      </div>

      <div className="mb-6">
        <Card title={t('monthlyResearch.alignment.title')} icon={ShieldAlert}>
          {alignment.loading ? (
            <div className="text-slate-400">{t('common.loading')}</div>
          ) : alignment.error || alignment.empty || !alignment.data ? (
            <div className="space-y-2">
              <div className="text-slate-300">{t('common.dataUnavailable')}</div>
              <div className="text-xs text-slate-500">{t('monthlyResearch.alignment.empty')}</div>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
                <SummaryCard
                  label={t('monthlyResearch.alignment.matched')}
                  value={alignment.data.summary.matchedCount}
                  accentClass="text-emerald-400"
                />
                <SummaryCard
                  label={t('monthlyResearch.alignment.unmatched')}
                  value={alignment.data.summary.unmatchedCount}
                  accentClass="text-amber-400"
                />
                <SummaryCard
                  label={t('monthlyResearch.alignment.highPriority')}
                  value={alignment.data.summary.highPriorityCount}
                  accentClass="text-rose-400"
                />
              </div>
              <KVItem
                label={t('monthlyResearch.alignment.attentionSymbols')}
                value={joinSymbols(alignment.data.summary.topAttentionSymbols, t('common.dataUnavailable'))}
              />
              <div className="rounded-md border border-slate-700 bg-slate-900 p-3 text-xs text-slate-400">
                {alignment.data.summary.unmatchedCount > 0
                  ? t('monthlyResearch.alignment.notReflected')
                  : t('monthlyResearch.alignment.covered')}
              </div>
              <div className="rounded-md border border-slate-700 bg-slate-900 p-3 text-xs text-slate-400">
                {t('monthlyResearch.alignment.readOnly')}
              </div>
              {alignment.data.items.length > 0 && (
                <div className="overflow-x-auto rounded-md border border-slate-700 bg-slate-900">
                  <table className="min-w-full text-xs text-slate-300">
                    <thead className="border-b border-slate-700 text-slate-500">
                      <tr>
                        <th className="px-3 py-2 text-left">{t('monthlyResearch.labels.symbol')}</th>
                        <th className="px-3 py-2 text-left">{t('monthlyResearch.labels.researchLabel')}</th>
                        <th className="px-3 py-2 text-left">{t('monthlyResearch.alignment.priority')}</th>
                        <th className="px-3 py-2 text-left">{t('monthlyResearch.alignment.attentionReason')}</th>
                      </tr>
                    </thead>
                    <tbody>
                      {alignment.data.items.slice(0, ALIGNMENT_PREVIEW_ROW_LIMIT).map((item) => (
                        <tr key={`${item.symbol}-${item.researchLabel}`} className="border-b border-slate-800 align-top">
                          <td className="px-3 py-2 font-mono">{item.symbol}</td>
                          <td className="px-3 py-2">{labelText(item.researchLabel, t)}</td>
                          <td className="px-3 py-2">{priorityText(item.priorityLevel, t)}</td>
                          <td className="px-3 py-2 text-slate-400">
                            {alignmentReasonText(item.attentionReasonCode, t)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </>
          )}
        </Card>
      </div>

      <div className="mb-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <Card title={t('monthlyResearch.sections.table')} icon={FileSearch}>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="text-slate-500">
                  <tr className="border-b border-slate-700">
                    <th className="py-2 pr-4 text-left">{t('monthlyResearch.labels.symbolName')}</th>
                    <th className="py-2 pr-4 text-left">{t('monthlyResearch.labels.assetType')}</th>
                    <th className="py-2 pr-4 text-left">{t('monthlyResearch.labels.suggestedAmount')}</th>
                    <th className="py-2 pr-4 text-left">{t('monthlyResearch.labels.researchLabel')}</th>
                    <th className="py-2 pr-4 text-left">{t('monthlyResearch.labels.suggestPauseBuy')}</th>
                    <th className="py-2 pr-4 text-left">{t('monthlyResearch.labels.suggestForceReview')}</th>
                    <th className="py-2 pr-4 text-left">{t('monthlyResearch.labels.suggestThesisBroken')}</th>
                    <th className="py-2 pr-4 text-left">{t('monthlyResearch.labels.confidence')}</th>
                    <th className="py-2 text-left">{t('monthlyResearch.labels.sourceSuggestRun')}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((item) => (
                    <tr
                      key={item.id}
                      className={`cursor-pointer border-b border-slate-800 align-top transition-colors ${activeId === item.id ? 'bg-slate-900/80' : 'hover:bg-slate-900/50'}`}
                      onClick={() => setSelectedId(item.id)}
                    >
                      <td className="py-3 pr-4 text-slate-200">
                        <div className="font-mono">{item.symbol}</div>
                        {item.displayName ? (
                          <div className="text-xs text-slate-400">{item.displayName}</div>
                        ) : null}
                      </td>
                      <td className="py-3 pr-4 text-slate-300">{item.assetType}</td>
                      <td className="py-3 pr-4 font-mono text-slate-300">{formatCurrency(item.suggestedAmount)}</td>
                      <td className="py-3 pr-4 text-slate-300">{labelText(item.finalResearchLabel, t)}</td>
                      <td className="py-3 pr-4 text-slate-300">{yesNo(item.suggestPauseBuy, t)}</td>
                      <td className="py-3 pr-4 text-slate-300">{yesNo(item.suggestForceReview, t)}</td>
                      <td className="py-3 pr-4 text-slate-300">{yesNo(item.suggestThesisBroken, t)}</td>
                      <td className="py-3 pr-4 text-slate-300">{formatPercent(item.confidence)}</td>
                      <td className="py-3 font-mono text-slate-400">{compactRunId(item.sourceSuggestRun, 18)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        <div className="xl:col-span-1">
          <Card title={t('monthlyResearch.sections.notice')} icon={ShieldAlert}>
            <div className="space-y-2 text-sm text-slate-300">
              <div>{t('monthlyResearch.notice.readOnly')}</div>
              <div>{t('monthlyResearch.notice.noAutoWrite')}</div>
              <div>{t('monthlyResearch.notice.noTradeExecution')}</div>
            </div>
          </Card>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card title={t('monthlyResearch.sections.detail')} icon={Brain}>
          {selectedItem ? (
            <>
              <KVItem label={t('monthlyResearch.labels.symbol')} value={selectedItem.symbol} />
              <KVItem label={t('monthlyResearch.labels.name')} value={selectedItem.displayName || selectedItem.symbol} />
              <KVItem label={t('monthlyResearch.labels.assetType')} value={selectedItem.assetType} />
              <KVItem label={t('monthlyResearch.labels.suggestedAmount')} value={formatCurrency(selectedItem.suggestedAmount)} />
              <KVItem label={t('monthlyResearch.labels.researchLabel')} value={labelText(selectedItem.finalResearchLabel, t)} />
              <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
                <div className="mb-2 text-xs uppercase tracking-[0.14em] text-slate-500">
                  {t('monthlyResearch.labels.analystDebate')}
                </div>
                <KVItem
                  label={t('monthlyResearch.labels.debateFocus')}
                  value={fallbackText(selectedDebate.debateFocus, t('common.dataUnavailable'))}
                  valueClass="text-slate-300"
                />
                <KVItem
                  label={t('monthlyResearch.labels.keyUncertainty')}
                  value={fallbackText(selectedDebate.keyUncertainty, t('common.dataUnavailable'))}
                  valueClass="text-slate-300"
                />
              </div>

              <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
                <div className="rounded-md border border-emerald-900/70 bg-emerald-950/20 p-3">
                  <div className="mb-2 flex items-center gap-2 text-emerald-300">
                    <TrendingUp className="h-4 w-4" />
                    <span className="text-xs uppercase tracking-[0.14em]">{t('monthlyResearch.labels.bullCase')}</span>
                  </div>
                  <div className="mb-1 text-[11px] uppercase tracking-[0.12em] text-emerald-300/80">
                    {t('monthlyResearch.labels.debatePreview')}
                  </div>
                  <div className="mb-3 text-sm leading-6 text-emerald-100/90">
                    {fallbackText(selectedDebate.bull.summaryPreview || selectedDebate.bull.summary, t('common.dataUnavailable'))}
                  </div>
                  <div className="mb-1 text-[11px] uppercase tracking-[0.12em] text-emerald-300/80">
                    {t('monthlyResearch.labels.fullDebateContent')}
                  </div>
                  <div className="mb-2 text-[11px] text-emerald-300/80">
                    {t('monthlyResearch.labels.scrollForFullCase')}
                  </div>
                  <div className="mb-3 text-emerald-100/90">
                    <ScrollableText text={selectedDebate.bull.summary} placeholder={t('common.dataUnavailable')} />
                  </div>
                  <div className="mb-2 text-xs uppercase tracking-[0.14em] text-emerald-300">
                    {t('monthlyResearch.labels.bullEvidence')}
                  </div>
                  <EvidenceList
                    points={selectedDebate.bull.evidencePoints}
                    emptyText={t('monthlyResearch.labels.noEvidencePoints')}
                  />
                  <div className="mb-2 mt-3 text-xs uppercase tracking-[0.14em] text-emerald-300">
                    {t('monthlyResearch.labels.bullAction')}
                  </div>
                  <div className="text-sm leading-6 text-emerald-100/90">
                    <ScrollableText
                      text={selectedDebate.bull.actionImplication}
                      placeholder={t('common.dataUnavailable')}
                      maxHeightClass="max-h-40"
                    />
                  </div>
                </div>

                <div className="rounded-md border border-rose-900/70 bg-rose-950/20 p-3">
                  <div className="mb-2 flex items-center gap-2 text-rose-300">
                    <TrendingDown className="h-4 w-4" />
                    <span className="text-xs uppercase tracking-[0.14em]">{t('monthlyResearch.labels.bearCase')}</span>
                  </div>
                  <div className="mb-1 text-[11px] uppercase tracking-[0.12em] text-rose-300/80">
                    {t('monthlyResearch.labels.debatePreview')}
                  </div>
                  <div className="mb-3 text-sm leading-6 text-rose-100/90">
                    {fallbackText(selectedDebate.bear.summaryPreview || selectedDebate.bear.summary, t('common.dataUnavailable'))}
                  </div>
                  <div className="mb-1 text-[11px] uppercase tracking-[0.12em] text-rose-300/80">
                    {t('monthlyResearch.labels.fullDebateContent')}
                  </div>
                  <div className="mb-2 text-[11px] text-rose-300/80">
                    {t('monthlyResearch.labels.scrollForFullCase')}
                  </div>
                  <div className="mb-3 text-rose-100/90">
                    <ScrollableText text={selectedDebate.bear.summary} placeholder={t('common.dataUnavailable')} />
                  </div>
                  <div className="mb-2 text-xs uppercase tracking-[0.14em] text-rose-300">
                    {t('monthlyResearch.labels.bearEvidence')}
                  </div>
                  <EvidenceList
                    points={selectedDebate.bear.evidencePoints}
                    emptyText={t('monthlyResearch.labels.noEvidencePoints')}
                  />
                  <div className="mb-2 mt-3 text-xs uppercase tracking-[0.14em] text-rose-300">
                    {t('monthlyResearch.labels.bearAction')}
                  </div>
                  <div className="text-sm leading-6 text-rose-100/90">
                    <ScrollableText
                      text={selectedDebate.bear.actionImplication}
                      placeholder={t('common.dataUnavailable')}
                      maxHeightClass="max-h-40"
                    />
                  </div>
                </div>
              </div>

              <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
                <div className="mb-2 flex items-center gap-2 text-amber-300">
                  <TriangleAlert className="h-4 w-4" />
                  <span className="text-xs uppercase tracking-[0.14em]">
                    {t('monthlyResearch.labels.recommendationRationale')}
                  </span>
                </div>
                <div className="whitespace-pre-wrap text-sm leading-6 text-slate-300">
                  <ScrollableText
                    text={selectedDebate.recommendationRationale}
                    placeholder={t('common.dataUnavailable')}
                    maxHeightClass="max-h-48"
                  />
                </div>
                <div className="mb-2 mt-3 text-xs uppercase tracking-[0.14em] text-slate-500">
                  {t('monthlyResearch.labels.riskSummary')}
                </div>
                <div className="mb-1 text-[11px] uppercase tracking-[0.12em] text-slate-500">
                  {t('monthlyResearch.labels.debatePreview')}
                </div>
                <div className="mb-3 text-sm leading-6 text-slate-300">
                  {fallbackText(selectedDebate.riskSummaryPreview || selectedDebate.riskSummary, t('common.dataUnavailable'))}
                </div>
                <div className="mb-1 text-[11px] uppercase tracking-[0.12em] text-slate-500">
                  {t('monthlyResearch.labels.fullDebateContent')}
                </div>
                <div className="whitespace-pre-wrap text-sm leading-6 text-slate-300">
                  <ScrollableText text={selectedDebate.riskSummary} placeholder={t('common.dataUnavailable')} maxHeightClass="max-h-40" />
                </div>
              </div>
              <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
                <div className="mb-2 text-xs uppercase tracking-[0.14em] text-slate-500">{t('monthlyResearch.labels.note')}</div>
                <ScrollableText
                  text={selectedItem.note}
                  placeholder={t('common.dataUnavailable')}
                  maxHeightClass="max-h-40"
                />
              </div>
            </>
          ) : (
            <div className="text-slate-400">{t('common.dataUnavailable')}</div>
          )}
        </Card>

        <Card title={t('monthlyResearch.sections.reportPreview')} icon={StickyNote}>
          <KVItem label={t('monthlyResearch.labels.batchId')} value={data.meta.batchId} />
          <KVItem label={t('monthlyResearch.labels.sourceSuggestRun')} value={compactRunId(data.meta.sourceSuggestRun, 24)} />
          <KVItem label={t('monthlyResearch.labels.topAttentionSymbols')} value={joinSymbols(data.summary.topAttentionSymbols, t('common.dataUnavailable'))} />
          <pre className="overflow-x-auto whitespace-pre-wrap rounded-md border border-slate-700 bg-slate-900 p-4 text-sm leading-6 text-slate-300">
            {data.reportPreview || t('common.dataUnavailable')}
          </pre>
        </Card>
      </div>
    </div>
  );
}
