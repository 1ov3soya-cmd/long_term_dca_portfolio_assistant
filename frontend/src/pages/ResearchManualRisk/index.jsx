import { Brain, FileSearch, ShieldAlert, StickyNote } from 'lucide-react';
import { useMemo, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { useResearchManualRiskData } from '../../hooks/useResearchManualRiskData.js';
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

function yesNo(value, t) {
  if (value === null || value === undefined) {
    return t('common.notApplicable');
  }
  return value ? t('common.yes') : t('common.no');
}

function matchStatusText(value, t) {
  if (value === 'matched') {
    return t('researchManualRisk.status.matched');
  }
  if (value === 'mismatch') {
    return t('researchManualRisk.status.mismatch');
  }
  if (value === 'partial') {
    return t('researchManualRisk.status.partial');
  }
  return t('common.dataUnavailable');
}

function priorityText(value, t) {
  if (value === 'high') {
    return t('researchManualRisk.priority.high');
  }
  if (value === 'medium') {
    return t('researchManualRisk.priority.medium');
  }
  if (value === 'low') {
    return t('researchManualRisk.priority.low');
  }
  return t('common.dataUnavailable');
}

function mismatchFieldText(field, t) {
  if (field === 'pause_buy') {
    return t('researchManualRisk.labels.pauseMismatch');
  }
  if (field === 'force_review') {
    return t('researchManualRisk.labels.reviewMismatch');
  }
  if (field === 'thesis_broken') {
    return t('researchManualRisk.labels.thesisMismatch');
  }
  return field;
}

function warningText(code, t) {
  const value = t(`researchManualRisk.warnings.${code}`);
  return value === `researchManualRisk.warnings.${code}` ? code : value;
}

function attentionReasonText(code, t) {
  const value = t(`researchManualRisk.reasons.${code}`);
  return value === `researchManualRisk.reasons.${code}` ? code : value;
}

function badgeClass(matchStatus, priorityLevel) {
  if (priorityLevel === 'high') {
    return 'border-rose-700 bg-rose-950/40 text-rose-300';
  }
  if (matchStatus === 'mismatch') {
    return 'border-amber-700 bg-amber-950/40 text-amber-300';
  }
  if (matchStatus === 'partial') {
    return 'border-blue-700 bg-blue-950/40 text-blue-300';
  }
  return 'border-emerald-700 bg-emerald-950/40 text-emerald-300';
}

export default function ResearchManualRisk() {
  const { t } = useTranslation();
  const { data, loading, error, empty, partial } = useResearchManualRiskData();
  const [selectedId, setSelectedId] = useState('');

  const selectedItem = useMemo(() => {
    if (!data?.items?.length) {
      return null;
    }
    return data.items.find((item) => item.id === selectedId) || data.items[0];
  }, [data, selectedId]);

  const highPriorityItems = data?.items?.filter((item) => item.priorityLevel === 'high') || [];

  if (loading) {
    return (
      <div className="p-6">
        <div className="rounded-lg border border-slate-800 bg-slate-900/70 px-4 py-3 text-sm text-slate-300">
          {t('researchManualRisk.loading')}
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
          <div className="font-medium">{t('researchManualRisk.emptyTitle')}</div>
          <div className="mt-1 text-slate-400">{t('researchManualRisk.emptyHint')}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 text-slate-200">
      <div className="mb-8">
        <div className="mb-2 flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight text-slate-50">{t('researchManualRisk.title')}</h1>
          <span className="rounded border border-slate-700 bg-slate-800 px-2.5 py-1 text-[11px] uppercase tracking-[0.16em] text-slate-300">
            {t('researchManualRisk.labels.totalItems')}: {data.meta.totalItems}
          </span>
        </div>
        <p className="text-sm text-slate-400">{t('researchManualRisk.subtitle')}</p>
      </div>

      {(partial || data.warnings.length > 0) && (
        <div className="mb-6 rounded-lg border border-slate-700 bg-slate-800/80 px-4 py-3 text-sm text-slate-300">
          <div className="font-medium">{partial ? t('common.partialData') : t('researchManualRisk.sections.attention')}</div>
          <div className="mt-2 space-y-1 text-slate-400">
            {data.warnings.map((warning) => (
              <div key={warning}>{warningText(warning, t)}</div>
            ))}
            {data.files.missing.length > 0 && (
              <div>
                {t('researchManualRisk.labels.missingFiles')}: {data.files.missing.join(', ')}
              </div>
            )}
          </div>
        </div>
      )}

      <div className="mb-6 grid grid-cols-1 gap-6 lg:grid-cols-12">
        <div className="lg:col-span-4">
          <Card title={t('researchManualRisk.sections.overview')} icon={Brain}>
            <KVItem label={t('researchManualRisk.labels.updatedAt')} value={data.meta.updatedAt} />
            <KVItem label={t('researchManualRisk.labels.totalItems')} value={data.meta.totalItems} />
            <KVItem label={t('researchManualRisk.labels.researchSource')} value={sourceText(data.meta.researchSourceType, t)} />
            <KVItem label={t('researchManualRisk.labels.manualRiskSource')} value={sourceText(data.meta.manualSourceType, t)} />
          </Card>
        </div>

        <div className="lg:col-span-8">
          <Card title={t('researchManualRisk.sections.summary')} icon={ShieldAlert}>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
              <SummaryCard label={t('researchManualRisk.summary.matchedCount')} value={data.summary.matchedCount} accentClass="text-emerald-400" />
              <SummaryCard label={t('researchManualRisk.summary.mismatchedCount')} value={data.summary.mismatchedCount} accentClass="text-amber-400" />
              <SummaryCard label={t('researchManualRisk.summary.pauseMismatchCount')} value={data.summary.pauseMismatchCount} accentClass="text-purple-400" />
              <SummaryCard label={t('researchManualRisk.summary.reviewMismatchCount')} value={data.summary.reviewMismatchCount} accentClass="text-yellow-400" />
              <SummaryCard label={t('researchManualRisk.summary.thesisMismatchCount')} value={data.summary.thesisMismatchCount} accentClass="text-rose-400" />
              <SummaryCard label={t('researchManualRisk.summary.highPriorityCount')} value={data.summary.highPriorityCount} accentClass="text-red-400" />
            </div>
          </Card>
        </div>
      </div>

      <div className="mb-6 grid grid-cols-1 gap-6 xl:grid-cols-3">
        <div className="xl:col-span-2">
          <Card title={t('researchManualRisk.sections.table')} icon={FileSearch}>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="text-slate-500">
                  <tr className="border-b border-slate-700">
                    <th className="py-2 pr-4 text-left">{t('researchManualRisk.labels.symbol')}</th>
                    <th className="py-2 pr-4 text-left">{t('researchManualRisk.labels.researchLabel')}</th>
                    <th className="py-2 pr-4 text-left">{t('researchManualRisk.labels.suggestPauseBuy')}</th>
                    <th className="py-2 pr-4 text-left">{t('researchManualRisk.labels.suggestForceReview')}</th>
                    <th className="py-2 pr-4 text-left">{t('researchManualRisk.labels.suggestThesisBroken')}</th>
                    <th className="py-2 pr-4 text-left">{t('researchManualRisk.labels.manualPauseBuy')}</th>
                    <th className="py-2 pr-4 text-left">{t('researchManualRisk.labels.manualForceReview')}</th>
                    <th className="py-2 pr-4 text-left">{t('researchManualRisk.labels.manualThesisBroken')}</th>
                    <th className="py-2 pr-4 text-left">{t('researchManualRisk.labels.matchStatus')}</th>
                    <th className="py-2 pr-4 text-left">{t('researchManualRisk.labels.priority')}</th>
                    <th className="py-2 pr-4 text-left">{t('researchManualRisk.labels.confidence')}</th>
                    <th className="py-2 text-left">{t('researchManualRisk.labels.sourceRun')}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.items.map((item) => (
                    <tr
                      key={item.id}
                      className={`cursor-pointer border-b border-slate-800 align-top transition-colors ${selectedItem?.id === item.id ? 'bg-slate-900/80' : 'hover:bg-slate-900/50'}`}
                      onClick={() => setSelectedId(item.id)}
                    >
                      <td className="py-3 pr-4 font-mono text-slate-200">{item.symbol}</td>
                      <td className="py-3 pr-4 text-slate-300">{researchLabelText(item.researchLabel, t)}</td>
                      <td className="py-3 pr-4 text-slate-300">{yesNo(item.suggestPauseBuy, t)}</td>
                      <td className="py-3 pr-4 text-slate-300">{yesNo(item.suggestForceReview, t)}</td>
                      <td className="py-3 pr-4 text-slate-300">{yesNo(item.suggestThesisBroken, t)}</td>
                      <td className="py-3 pr-4 text-slate-300">{yesNo(item.manualPauseBuy, t)}</td>
                      <td className="py-3 pr-4 text-slate-300">{yesNo(item.manualForceReview, t)}</td>
                      <td className="py-3 pr-4 text-slate-300">{yesNo(item.manualThesisBroken, t)}</td>
                      <td className="py-3 pr-4">
                        <span className={`rounded border px-2 py-1 text-xs ${badgeClass(item.matchStatus, item.priorityLevel)}`}>
                          {matchStatusText(item.matchStatus, t)}
                        </span>
                      </td>
                      <td className="py-3 pr-4">
                        <span className={`rounded border px-2 py-1 text-xs ${badgeClass(item.matchStatus, item.priorityLevel)}`}>
                          {priorityText(item.priorityLevel, t)}
                        </span>
                      </td>
                      <td className="py-3 pr-4 text-slate-300">{item.confidence === null ? t('common.notApplicable') : formatPercent(item.confidence)}</td>
                      <td className="py-3 text-slate-400 font-mono">{compactRunId(item.sourceRun, 18)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        <div className="xl:col-span-1">
          <Card title={t('researchManualRisk.sections.highPriority')} icon={ShieldAlert}>
            <div className="rounded-md border border-slate-700 bg-slate-900 p-3 text-sm text-slate-300">
              {t('researchManualRisk.notices.readOnly')}
            </div>
            <div className="rounded-md border border-slate-700 bg-slate-900 p-3 text-sm text-slate-300">
              {t('researchManualRisk.notices.noAutoWrite')}
            </div>
            {highPriorityItems.length > 0 ? highPriorityItems.map((item) => (
              <div key={item.id} className="rounded-md border border-rose-800 bg-rose-950/30 p-3">
                <div className="flex items-center justify-between gap-3">
                  <span className="font-mono text-rose-200">{item.symbol}</span>
                  <span className="rounded border border-rose-700 px-2 py-1 text-xs text-rose-200">
                    {priorityText(item.priorityLevel, t)}
                  </span>
                </div>
                <div className="mt-2 text-sm text-rose-100">{attentionReasonText(item.attentionReasonCode, t)}</div>
              </div>
            )) : (
              <div className="rounded-md border border-slate-700 bg-slate-900 p-3 text-slate-400">
                {t('common.dataUnavailable')}
              </div>
            )}
          </Card>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        <Card title={t('researchManualRisk.sections.detail')} icon={Brain}>
          {selectedItem ? (
            <>
              <KVItem label={t('researchManualRisk.labels.symbol')} value={selectedItem.symbol} />
              <KVItem label={t('researchManualRisk.labels.analysisDate')} value={selectedItem.analysisDate} />
              <KVItem label={t('researchManualRisk.labels.manualEffectiveFrom')} value={selectedItem.manualEffectiveFrom} />
              <KVItem label={t('researchManualRisk.labels.matchStatus')} value={matchStatusText(selectedItem.matchStatus, t)} />
              <KVItem label={t('researchManualRisk.labels.priority')} value={priorityText(selectedItem.priorityLevel, t)} />
              <KVItem label={t('researchManualRisk.labels.attentionReason')} value={attentionReasonText(selectedItem.attentionReasonCode, t)} valueClass="text-slate-100" />
              <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
                <div className="mb-2 text-xs uppercase tracking-[0.14em] text-slate-500">{t('research.labels.bullCase')}</div>
                <div className="whitespace-pre-wrap text-slate-300">{fallbackText(selectedItem.bullCase, t('common.dataUnavailable'))}</div>
              </div>
              <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
                <div className="mb-2 text-xs uppercase tracking-[0.14em] text-slate-500">{t('research.labels.bearCase')}</div>
                <div className="whitespace-pre-wrap text-slate-300">{fallbackText(selectedItem.bearCase, t('common.dataUnavailable'))}</div>
              </div>
              <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
                <div className="mb-2 text-xs uppercase tracking-[0.14em] text-slate-500">{t('research.labels.riskSummary')}</div>
                <div className="whitespace-pre-wrap text-slate-300">{fallbackText(selectedItem.riskSummary, t('common.dataUnavailable'))}</div>
              </div>
            </>
          ) : (
            <div className="text-slate-400">{t('common.dataUnavailable')}</div>
          )}
        </Card>

        <Card title={t('researchManualRisk.sections.detailNotes')} icon={StickyNote}>
          {selectedItem ? (
            <>
              <KVItem label={t('researchManualRisk.labels.manualNote')} value={selectedItem.manualNote} valueClass="text-slate-100" />
              <KVItem
                label={t('researchManualRisk.labels.mismatchFields')}
                value={selectedItem.mismatchFields.length > 0
                  ? selectedItem.mismatchFields.map((field) => mismatchFieldText(field, t)).join(', ')
                  : t('common.notApplicable')}
                valueClass="text-slate-100"
              />
              <KVItem label={t('researchManualRisk.labels.sourceRun')} value={selectedItem.sourceRun} />
              <KVItem label={t('researchManualRisk.labels.researchJsonPath')} value={selectedItem.sourceFiles.researchJson} />
              <KVItem label={t('researchManualRisk.labels.researchMarkdownPath')} value={selectedItem.sourceFiles.researchMarkdown} />
              <KVItem label={t('researchManualRisk.labels.manualRiskSource')} value={sourceText(selectedItem.sourceFiles.manualSource, t)} />
              <div className="rounded-md border border-slate-700 bg-slate-900 p-4">
                <div className="mb-2 text-xs uppercase tracking-[0.14em] text-slate-500">{t('researchManualRisk.sections.memoPreview')}</div>
                <pre className="overflow-x-auto whitespace-pre-wrap text-sm leading-6 text-slate-300">
                  {selectedItem.memoPreview || t('common.dataUnavailable')}
                </pre>
              </div>
            </>
          ) : (
            <div className="text-slate-400">{t('common.dataUnavailable')}</div>
          )}
        </Card>
      </div>
    </div>
  );
}
