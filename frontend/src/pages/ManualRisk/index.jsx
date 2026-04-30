import { ClipboardCheck, FileSearch, ShieldAlert, StickyNote } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useManualRiskData } from '../../hooks/useManualRiskData.js';
import { fallbackText } from '../../utils/formatters.js';

const Card = ({ title, icon: Icon, children }) => (
  <div className="bg-slate-800 border border-slate-700 rounded-lg flex flex-col h-full">
    <div className="p-4 border-b border-slate-700 flex items-center gap-2">
      <Icon className="w-5 h-5 text-slate-400" />
      <h3 className="font-semibold text-slate-200">{title}</h3>
    </div>
    <div className="p-4 flex-1 flex flex-col gap-3 text-sm text-slate-300">
      {children}
    </div>
  </div>
);

const KVItem = ({ label, value, valueClass = 'text-slate-100 font-mono' }) => (
  <div className="flex items-start justify-between gap-4">
    <span className="text-slate-400">{label}</span>
    <span className={`${valueClass} text-right break-all`}>{fallbackText(value)}</span>
  </div>
);

function booleanText(value, t) {
  return value ? t('common.yes') : t('common.no');
}

function sourceText(sourceType, t) {
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

function actionText(actionCode, actionTextValue, t) {
  if (actionCode === 'thesisBroken') {
    return t('manualRisk.actions.thesisBroken');
  }
  if (actionCode === 'forceReview') {
    return t('manualRisk.actions.forceReview');
  }
  if (actionCode === 'pauseBuy') {
    return t('manualRisk.actions.pauseBuy');
  }
  if (actionCode === 'normal') {
    return t('manualRisk.actions.normal');
  }
  return actionTextValue || t('common.dataUnavailable');
}

const SummaryCard = ({ label, value, accentClass = 'text-slate-100' }) => (
  <div className="rounded-md border border-slate-700 bg-slate-900 p-4">
    <div className="text-xs uppercase tracking-[0.14em] text-slate-500">{label}</div>
    <div className={`mt-2 text-2xl font-mono ${accentClass}`}>{fallbackText(value, '0')}</div>
  </div>
);

export default function ManualRisk() {
  const { t } = useTranslation();
  const { data, loading, error, empty, partial } = useManualRiskData();

  if (loading) {
    return (
      <div className="p-6">
        <div className="rounded-lg border border-slate-800 bg-slate-900/70 px-4 py-3 text-sm text-slate-300">
          {t('manualRisk.loading')}
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
          <div className="font-medium">{t('manualRisk.emptyTitle')}</div>
          <div className="mt-1 text-slate-400">{t('manualRisk.emptyHint')}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 text-slate-200 font-sans">
      <div className="mb-8">
        <div className="mb-2 flex flex-wrap items-center gap-3">
          <h1 className="text-2xl font-bold tracking-tight text-slate-50">{t('manualRisk.title')}</h1>
          <span className="rounded border border-slate-700 bg-slate-800 px-2.5 py-1 text-[11px] uppercase tracking-[0.16em] text-slate-300">
            {sourceText(data.meta.sourceType, t)}
          </span>
        </div>
        <p className="text-sm text-slate-400">{t('manualRisk.subtitle')}</p>
      </div>

      {partial && (
        <div className="mb-6 rounded-lg border border-slate-700 bg-slate-800/80 px-4 py-3 text-sm text-slate-300">
          <div className="font-medium">{t('common.partialData')}</div>
          <div className="mt-1 text-slate-400">
            {t('manualRisk.labels.missingFiles')}: {data.files.missing.join(', ') || t('common.dataUnavailable')}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-6">
        <div className="lg:col-span-4">
          <Card title={t('manualRisk.sections.overview')} icon={ShieldAlert}>
            <KVItem label={t('manualRisk.labels.source')} value={sourceText(data.meta.sourceType, t)} />
            <KVItem label={t('manualRisk.labels.lastUpdated')} value={data.meta.lastUpdated} />
            <KVItem label={t('manualRisk.labels.endDate')} value={data.meta.endDate} />
            <KVItem label={t('manualRisk.labels.hasData')} value={data.meta.hasData ? t('common.yes') : t('common.no')} />
          </Card>
        </div>

        <div className="lg:col-span-8">
          <Card title={t('manualRisk.sections.summary')} icon={ClipboardCheck}>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4">
              <SummaryCard label={t('manualRisk.labels.pausedCount')} value={data.summary.pausedCount} accentClass="text-purple-400" />
              <SummaryCard label={t('manualRisk.labels.forceReviewCount')} value={data.summary.forceReviewCount} accentClass="text-amber-400" />
              <SummaryCard label={t('manualRisk.labels.thesisBrokenCount')} value={data.summary.thesisBrokenCount} accentClass="text-rose-400" />
              <SummaryCard label={t('manualRisk.labels.effectiveInRangeCount')} value={data.summary.effectiveInRangeCount} accentClass="text-blue-400" />
            </div>
          </Card>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-6">
        <div className="xl:col-span-2">
          <Card title={t('manualRisk.sections.currentTable')} icon={FileSearch}>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="text-slate-500">
                  <tr className="border-b border-slate-700">
                    <th className="py-2 pr-4 text-left">{t('manualRisk.labels.symbol')}</th>
                    <th className="py-2 pr-4 text-left">{t('manualRisk.labels.effectiveFrom')}</th>
                    <th className="py-2 pr-4 text-left">{t('manualRisk.labels.pauseBuy')}</th>
                    <th className="py-2 pr-4 text-left">{t('manualRisk.labels.forceReview')}</th>
                    <th className="py-2 pr-4 text-left">{t('manualRisk.labels.thesisBroken')}</th>
                    <th className="py-2 pr-4 text-left">{t('manualRisk.labels.finalAction')}</th>
                    <th className="py-2 pr-4 text-left">{t('manualRisk.labels.note')}</th>
                    <th className="py-2 text-left">{t('manualRisk.labels.sourceLabel')}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.rows.length > 0 ? data.rows.map((row) => (
                    <tr key={`${row.symbol}-${row.effectiveFrom}-${row.source}`} className="border-b border-slate-800 align-top">
                      <td className="py-3 pr-4 font-mono text-slate-200">{row.symbol}</td>
                      <td className="py-3 pr-4 text-slate-300">{fallbackText(row.effectiveFrom)}</td>
                      <td className="py-3 pr-4 text-slate-300">{booleanText(row.pauseBuy, t)}</td>
                      <td className="py-3 pr-4 text-slate-300">{booleanText(row.forceReview, t)}</td>
                      <td className="py-3 pr-4 text-slate-300">{booleanText(row.thesisBroken, t)}</td>
                      <td className="py-3 pr-4 text-slate-300">{actionText(row.finalActionCode, row.finalActionText, t)}</td>
                      <td className="py-3 pr-4 text-slate-400">{fallbackText(row.note, t('common.dataUnavailable'))}</td>
                      <td className="py-3 text-slate-300">{sourceText(row.source, t)}</td>
                    </tr>
                  )) : (
                    <tr>
                      <td className="py-4 text-slate-400" colSpan={8}>
                        {t('common.dataUnavailable')}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </Card>
        </div>

        <div className="xl:col-span-1">
          <Card title={t('manualRisk.sections.status')} icon={ShieldAlert}>
            <KVItem label={t('manualRisk.labels.acceptanceReport')} value={booleanText(data.status.acceptanceReport, t)} />
            <KVItem label={t('manualRisk.labels.previewCsv')} value={booleanText(data.status.previewCsv, t)} />
            <KVItem label={t('manualRisk.labels.validationReport')} value={booleanText(data.status.validationReport, t)} />
            <KVItem label={t('manualRisk.labels.checklist')} value={booleanText(data.status.checklist, t)} />
            <KVItem label={t('manualRisk.labels.latestRun')} value={booleanText(data.status.latestRun, t)} />
            <KVItem label={t('manualRisk.labels.fallbackConfig')} value={booleanText(data.status.fallbackConfig, t)} />
            <KVItem
              label={t('manualRisk.labels.validationValid')}
              value={data.status.validationValid === null ? t('common.notApplicable') : booleanText(data.status.validationValid, t)}
            />
            <KVItem label={t('manualRisk.labels.validationIssueCount')} value={data.status.validationIssueCount} />
          </Card>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title={t('manualRisk.sections.checklistPreview')} icon={StickyNote}>
          <pre className="overflow-x-auto whitespace-pre-wrap text-sm leading-6 text-slate-300">
            {data.notes.checklistPreview || t('common.dataUnavailable')}
          </pre>
        </Card>

        <Card title={t('manualRisk.sections.validationPreview')} icon={ClipboardCheck}>
          <pre className="overflow-x-auto whitespace-pre-wrap text-sm leading-6 text-slate-300">
            {data.notes.validationPreview || t('common.dataUnavailable')}
          </pre>
        </Card>
      </div>
    </div>
  );
}
