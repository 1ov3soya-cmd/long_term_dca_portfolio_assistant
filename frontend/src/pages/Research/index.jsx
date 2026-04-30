import { Brain, FileSearch, ShieldAlert, StickyNote, TrendingDown, TrendingUp, TriangleAlert } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useResearchData } from '../../hooks/useResearchData.js';
import { compactRunId, fallbackText, formatPercent } from '../../utils/formatters.js';

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

function sourceLabel(sourceType, t) {
  if (sourceType === 'researchIndex') {
    return t('research.sources.researchIndex');
  }
  if (sourceType === 'latestRunFallback') {
    return t('research.sources.latestRunFallback');
  }
  return t('common.dataUnavailable');
}

function labelText(label, t) {
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

function yesNo(value, t) {
  return value ? t('common.yes') : t('common.no');
}

export default function Research() {
  const { t } = useTranslation();
  const { data, loading, error, empty, partial } = useResearchData();
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
          {t('research.loading')}
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
          <div className="font-medium">{t('research.emptyTitle')}</div>
          <div className="mt-1 text-slate-400">{t('research.emptyHint')}</div>
          <pre className="mt-3 overflow-x-auto rounded border border-slate-800 bg-slate-950/80 p-3 text-xs text-slate-300">
            python -m src.main run-agent-research --symbol 600519 --end-date 2025-12-31
          </pre>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 text-slate-200">
      <div className="mb-8">
        <div className="mb-2 flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight text-slate-50">{t('research.title')}</h1>
          <span className="rounded border border-slate-700 bg-slate-800 px-2.5 py-1 text-[11px] uppercase tracking-[0.16em] text-slate-300">
            {sourceLabel(data.meta.sourceType, t)}
          </span>
        </div>
        <p className="text-sm text-slate-400">{t('research.subtitle')}</p>
      </div>

      {partial && (
        <div className="mb-6 rounded-lg border border-slate-700 bg-slate-800/80 px-4 py-3 text-sm text-slate-300">
          <div className="font-medium">{t('common.partialData')}</div>
          <div className="mt-1 text-slate-400">
            {t('research.labels.missingFiles')}: {data.files.missing.join(', ') || t('common.dataUnavailable')}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-12 mb-6">
        <div className="lg:col-span-4">
          <Card title={t('research.sections.overview')} icon={Brain}>
            <KVItem label={t('research.labels.dataSource')} value={sourceLabel(data.meta.sourceType, t)} />
            <KVItem label={t('research.labels.lastUpdated')} value={data.meta.updatedAt} />
            <KVItem label={t('research.labels.totalItems')} value={data.meta.totalItems} />
            <KVItem label={t('research.labels.latestSymbol')} value={data.meta.latestSymbol} />
            <KVItem label={t('research.labels.latestAnalysisDate')} value={data.meta.latestAnalysisDate} />
          </Card>
        </div>

        <div className="lg:col-span-8">
          <Card title={t('research.sections.summary')} icon={ShieldAlert}>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
              <SummaryCard label={t('research.labels.totalItems')} value={data.summary.totalCount} accentClass="text-slate-100" />
              <SummaryCard label={t('research.labels.pauseCandidateCount')} value={data.summary.pauseCandidateCount} accentClass="text-purple-400" />
              <SummaryCard label={t('research.labels.forceReviewCandidateCount')} value={data.summary.forceReviewCandidateCount} accentClass="text-amber-400" />
              <SummaryCard label={t('research.labels.thesisBrokenCandidateCount')} value={data.summary.thesisBrokenCandidateCount} accentClass="text-rose-400" />
              <SummaryCard label={t('research.labels.averageConfidence')} value={formatPercent(data.summary.averageConfidence)} accentClass="text-blue-400" />
            </div>
          </Card>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-3 mb-6">
        <div className="xl:col-span-2">
          <Card title={t('research.sections.resultTable')} icon={FileSearch}>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="text-slate-500">
                  <tr className="border-b border-slate-700">
                    <th className="py-2 pr-4 text-left">{t('research.labels.symbolName')}</th>
                    <th className="py-2 pr-4 text-left">{t('research.labels.analysisDate')}</th>
                    <th className="py-2 pr-4 text-left">{t('research.labels.researchLabel')}</th>
                    <th className="py-2 pr-4 text-left">{t('research.labels.suggestPauseBuy')}</th>
                    <th className="py-2 pr-4 text-left">{t('research.labels.suggestForceReview')}</th>
                    <th className="py-2 pr-4 text-left">{t('research.labels.suggestThesisBroken')}</th>
                    <th className="py-2 pr-4 text-left">{t('research.labels.confidence')}</th>
                    <th className="py-2 pr-4 text-left">{t('research.labels.sourceRun')}</th>
                    <th className="py-2 text-left">{t('research.labels.memoAvailable')}</th>
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
                      <td className="py-3 pr-4 text-slate-300">{item.analysisDate}</td>
                      <td className="py-3 pr-4 text-slate-300">{labelText(item.finalResearchLabel, t)}</td>
                      <td className="py-3 pr-4 text-slate-300">{yesNo(item.suggestPauseBuy, t)}</td>
                      <td className="py-3 pr-4 text-slate-300">{yesNo(item.suggestForceReview, t)}</td>
                      <td className="py-3 pr-4 text-slate-300">{yesNo(item.suggestThesisBroken, t)}</td>
                      <td className="py-3 pr-4 text-slate-300">{formatPercent(item.confidence)}</td>
                      <td className="py-3 pr-4 font-mono text-slate-400">{compactRunId(item.sourceRun, 18)}</td>
                      <td className="py-3 text-slate-300">{yesNo(item.memoAvailable, t)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        <div className="xl:col-span-1">
          <Card title={t('research.sections.mapping')} icon={ShieldAlert}>
            <div className="space-y-2 text-sm text-slate-300">
              <div>{t('research.mapping.readOnly')}</div>
              <div>{t('research.mapping.noAutoWrite')}</div>
              <div>{t('research.mapping.humanDecision')}</div>
            </div>
          </Card>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card title={t('research.sections.detail')} icon={Brain}>
          {selectedItem ? (
            <>
              <KVItem label={t('research.labels.symbol')} value={selectedItem.symbol} />
              <KVItem label={t('research.labels.name')} value={selectedItem.displayName || selectedItem.symbol} />
              <KVItem label={t('research.labels.analysisDate')} value={selectedItem.analysisDate} />
              <KVItem label={t('research.labels.researchLabel')} value={labelText(selectedItem.finalResearchLabel, t)} />
              <KVItem label={t('research.labels.confidence')} value={formatPercent(selectedItem.confidence)} />
              <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
                <div className="mb-2 text-xs uppercase tracking-[0.14em] text-slate-500">
                  {t('research.labels.analystDebate')}
                </div>
                <KVItem
                  label={t('research.labels.debateFocus')}
                  value={fallbackText(selectedDebate.debateFocus, t('common.dataUnavailable'))}
                  valueClass="text-slate-300"
                />
                <KVItem
                  label={t('research.labels.keyUncertainty')}
                  value={fallbackText(selectedDebate.keyUncertainty, t('common.dataUnavailable'))}
                  valueClass="text-slate-300"
                />
              </div>

              <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
                <div className="rounded-md border border-emerald-900/70 bg-emerald-950/20 p-3">
                  <div className="mb-2 flex items-center gap-2 text-emerald-300">
                    <TrendingUp className="h-4 w-4" />
                    <span className="text-xs uppercase tracking-[0.14em]">{t('research.labels.bullCase')}</span>
                  </div>
                  <div className="mb-1 text-[11px] uppercase tracking-[0.12em] text-emerald-300/80">
                    {t('research.labels.debatePreview')}
                  </div>
                  <div className="mb-3 text-sm leading-6 text-emerald-100/90">
                    {fallbackText(selectedDebate.bull.summaryPreview || selectedDebate.bull.summary, t('common.dataUnavailable'))}
                  </div>
                  <div className="mb-1 text-[11px] uppercase tracking-[0.12em] text-emerald-300/80">
                    {t('research.labels.fullDebateContent')}
                  </div>
                  <div className="mb-2 text-[11px] text-emerald-300/80">
                    {t('research.labels.scrollForFullCase')}
                  </div>
                  <div className="mb-3 text-emerald-100/90">
                    <ScrollableText text={selectedDebate.bull.summary} placeholder={t('common.dataUnavailable')} />
                  </div>
                  <div className="mb-2 text-xs uppercase tracking-[0.14em] text-emerald-300">
                    {t('research.labels.bullEvidence')}
                  </div>
                  <EvidenceList
                    points={selectedDebate.bull.evidencePoints}
                    emptyText={t('research.labels.noEvidencePoints')}
                  />
                  <div className="mb-2 mt-3 text-xs uppercase tracking-[0.14em] text-emerald-300">
                    {t('research.labels.bullAction')}
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
                    <span className="text-xs uppercase tracking-[0.14em]">{t('research.labels.bearCase')}</span>
                  </div>
                  <div className="mb-1 text-[11px] uppercase tracking-[0.12em] text-rose-300/80">
                    {t('research.labels.debatePreview')}
                  </div>
                  <div className="mb-3 text-sm leading-6 text-rose-100/90">
                    {fallbackText(selectedDebate.bear.summaryPreview || selectedDebate.bear.summary, t('common.dataUnavailable'))}
                  </div>
                  <div className="mb-1 text-[11px] uppercase tracking-[0.12em] text-rose-300/80">
                    {t('research.labels.fullDebateContent')}
                  </div>
                  <div className="mb-2 text-[11px] text-rose-300/80">
                    {t('research.labels.scrollForFullCase')}
                  </div>
                  <div className="mb-3 text-rose-100/90">
                    <ScrollableText text={selectedDebate.bear.summary} placeholder={t('common.dataUnavailable')} />
                  </div>
                  <div className="mb-2 text-xs uppercase tracking-[0.14em] text-rose-300">
                    {t('research.labels.bearEvidence')}
                  </div>
                  <EvidenceList
                    points={selectedDebate.bear.evidencePoints}
                    emptyText={t('research.labels.noEvidencePoints')}
                  />
                  <div className="mb-2 mt-3 text-xs uppercase tracking-[0.14em] text-rose-300">
                    {t('research.labels.bearAction')}
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
                    {t('research.labels.recommendationRationale')}
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
                  {t('research.labels.riskSummary')}
                </div>
                <div className="mb-1 text-[11px] uppercase tracking-[0.12em] text-slate-500">
                  {t('research.labels.debatePreview')}
                </div>
                <div className="mb-3 text-sm leading-6 text-slate-300">
                  {fallbackText(selectedDebate.riskSummaryPreview || selectedDebate.riskSummary, t('common.dataUnavailable'))}
                </div>
                <div className="mb-1 text-[11px] uppercase tracking-[0.12em] text-slate-500">
                  {t('research.labels.fullDebateContent')}
                </div>
                <div className="whitespace-pre-wrap text-sm leading-6 text-slate-300">
                  <ScrollableText text={selectedDebate.riskSummary} placeholder={t('common.dataUnavailable')} maxHeightClass="max-h-40" />
                </div>
              </div>

              <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
                <div className="mb-2 text-xs uppercase tracking-[0.14em] text-slate-500">{t('research.labels.notes')}</div>
                <ScrollableText
                  text={selectedItem.notes}
                  placeholder={t('common.dataUnavailable')}
                  maxHeightClass="max-h-40"
                />
              </div>
            </>
          ) : (
            <div className="text-slate-400">{t('common.dataUnavailable')}</div>
          )}
        </Card>

        <Card title={t('research.sections.memoPreview')} icon={StickyNote}>
          {selectedItem ? (
            <>
              <KVItem label={t('research.labels.sourceRun')} value={selectedItem.sourceRun} />
              <KVItem label={t('research.labels.jsonPath')} value={selectedItem.archivePaths.json} />
              <KVItem label={t('research.labels.markdownPath')} value={selectedItem.archivePaths.markdown} />
              <pre className="overflow-x-auto whitespace-pre-wrap rounded-md border border-slate-700 bg-slate-900 p-4 text-sm leading-6 text-slate-300">
                {selectedItem.memoPreview || t('common.dataUnavailable')}
              </pre>
            </>
          ) : (
            <div className="text-slate-400">{t('common.dataUnavailable')}</div>
          )}
        </Card>
      </div>
    </div>
  );
}
