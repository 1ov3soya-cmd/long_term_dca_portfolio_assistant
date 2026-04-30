import { GitCompare, AlertTriangle, FileDiff, Files, SearchCheck } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { useCompareData } from '../../hooks/useCompareData.js';
import { compactRunId, fallbackText } from '../../utils/formatters.js';

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

function renderBooleanLabel(status, t) {
  if (status === 'yes') {
    return t('common.yes');
  }
  if (status === 'no') {
    return t('common.no');
  }
  return t('common.notApplicable');
}

function renderComparableLevel(level, t) {
  const normalized = String(level || '').toLowerCase();
  if (normalized === 'high') {
    return t('compare.status.high');
  }
  if (normalized === 'partial') {
    return t('compare.status.partial');
  }
  if (normalized === 'low') {
    return t('compare.status.low');
  }
  return fallbackText(level, t('common.notApplicable'));
}

function renderStatusLabel(status, t) {
  const normalized = String(status || '').toLowerCase();
  if (normalized === 'success') {
    return t('compare.status.success');
  }
  if (normalized === 'partial') {
    return t('compare.status.partialStatus');
  }
  if (normalized === 'failed') {
    return t('compare.status.failed');
  }
  return fallbackText(status, t('common.notApplicable'));
}

export default function RunCompare() {
  const { t } = useTranslation();
  const { data, loading, error, empty } = useCompareData();

  if (loading) {
    return (
      <div className="p-6">
        <div className="rounded-lg border border-slate-800 bg-slate-900/70 px-4 py-3 text-sm text-slate-300">
          {t('common.loadingCompare')}
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
          <div className="font-medium">{t('common.emptyCompare')}</div>
          <div className="mt-1 text-slate-400">{t('compare.emptyHint')}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 text-slate-200 font-sans">
      <div className="mb-8">
        <div className="flex flex-wrap items-center gap-3 mb-2">
          <h1 className="text-2xl font-bold text-slate-50 tracking-tight">{t('compare.title')}</h1>
          <span className="px-2.5 py-1 rounded border border-slate-700 bg-slate-800 text-[11px] tracking-[0.16em] text-slate-300 uppercase">
            {renderComparableLevel(data.meta.comparableLevel, t)}
          </span>
        </div>
        <p className="text-sm text-slate-400">{t('compare.subtitle')}</p>
      </div>

      {data.files.missing.length > 0 && (
        <div className="mb-6 rounded-lg border border-slate-700 bg-slate-800/80 px-4 py-3 text-sm text-slate-300">
          <div className="font-medium">{t('common.partialData')}</div>
          <div className="mt-1 text-slate-400">
            {t('compare.labels.missingFiles')}: {data.files.missing.join(', ')}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 mb-6">
        <div className="lg:col-span-5">
          <Card title={t('compare.title')} icon={GitCompare}>
            <KVItem label={t('compare.labels.compareId')} value={data.meta.compareId} />
            <KVItem label={t('compare.labels.comparedAt')} value={data.meta.comparedAt} />
            <KVItem label={t('dashboard.labels.comparableLevel')} value={renderComparableLevel(data.meta.comparableLevel, t)} valueClass="text-emerald-400 font-mono font-bold" />
            <KVItem label={t('compare.labels.runA')} value={data.meta.runA} />
            <KVItem label={t('compare.labels.runB')} value={data.meta.runB} />
          </Card>
        </div>

        <div className="lg:col-span-7">
          <Card title={t('compare.sections.basicSummary')} icon={SearchCheck}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <KVItem label={t('compare.labels.compareStatus')} value={renderStatusLabel(data.basic.compareStatus, t)} />
              <KVItem label={t('compare.labels.keyFindingsCount')} value={data.basic.keyFindingsCount} />
              <KVItem label={t('compare.labels.commandMatch')} value={renderBooleanLabel(data.basic.commandMatch, t)} />
              <KVItem label={t('compare.labels.endDateMatch')} value={renderBooleanLabel(data.basic.endDateMatch, t)} />
            </div>
            <div className="mt-2 rounded-md border border-slate-700 bg-slate-900 p-3 text-xs text-slate-400">
              {fallbackText(data.basic.reason, t('common.dataUnavailable'))}
            </div>
          </Card>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <Card title={t('compare.sections.configChanges')} icon={FileDiff}>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
              <div className="text-xs uppercase tracking-wide text-slate-500">{t('compare.labels.manualRiskChanged')}</div>
              <div className="mt-2 text-lg font-mono text-slate-100">{renderBooleanLabel(data.configChanges.manualRiskChanged ? 'yes' : 'no', t)}</div>
            </div>
            <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
              <div className="text-xs uppercase tracking-wide text-slate-500">{t('compare.labels.adjModeChanged')}</div>
              <div className="mt-2 text-lg font-mono text-slate-100">{renderBooleanLabel(data.configChanges.adjModeChanged ? 'yes' : 'no', t)}</div>
            </div>
            <div className="rounded-md border border-slate-700 bg-slate-900 p-3">
              <div className="text-xs uppercase tracking-wide text-slate-500">{t('compare.labels.dataModeChanged')}</div>
              <div className="mt-2 text-lg font-mono text-slate-100">{renderBooleanLabel(data.configChanges.dataModeChanged ? 'yes' : 'no', t)}</div>
            </div>
          </div>

          <div className="mt-3">
            <div className="mb-2 text-xs uppercase tracking-[0.14em] text-slate-500">{t('compare.labels.topConfigChanges')}</div>
            <div className="space-y-2">
              {(data.configChanges.topChanges.length > 0 ? data.configChanges.topChanges : data.configChanges.structuredChanges).slice(0, 8).map((item) => (
                <div key={`${item.path}-${item.changeType}`} className="rounded-md border border-slate-700 bg-slate-900 p-3">
                  <div className="text-xs text-slate-500">{item.changeType}</div>
                  <div className="mt-1 font-mono text-slate-200 break-all">{item.path}</div>
                </div>
              ))}
              {data.configChanges.topChanges.length === 0 && data.configChanges.structuredChanges.length === 0 && (
                <div className="rounded-md border border-slate-700 bg-slate-900 p-3 text-slate-400">
                  {t('common.dataUnavailable')}
                </div>
              )}
            </div>
          </div>

          <div className="mt-3">
            <div className="mb-2 text-xs uppercase tracking-[0.14em] text-slate-500">{t('compare.labels.pathsOnly')}</div>
            <div className="rounded-md border border-slate-700 bg-slate-900 p-3 text-xs text-slate-400">
              {data.configChanges.pathOnlyDifferences.length > 0
                ? data.configChanges.pathOnlyDifferences.slice(0, 8).join(' | ')
                : t('common.dataUnavailable')}
            </div>
            <div className="mt-2 text-xs text-slate-500">{t('compare.filesHint')}</div>
          </div>
        </Card>

        <Card title={t('compare.sections.attentionPoints')} icon={AlertTriangle}>
          <div className="space-y-2">
            {data.attentionPoints.length > 0 ? data.attentionPoints.map((point, index) => (
              <div key={`${point}-${index + 1}`} className="rounded-md border border-slate-700 bg-slate-900 p-3 text-sm text-slate-300">
                {point}
              </div>
            )) : (
              <div className="rounded-md border border-slate-700 bg-slate-900 p-3 text-slate-400">
                {t('common.dataUnavailable')}
              </div>
            )}
          </div>

          <div className="mt-3">
            <div className="mb-2 text-xs uppercase tracking-[0.14em] text-slate-500">{t('compare.labels.warnings')}</div>
            <div className="space-y-2">
              {data.warnings.length > 0 ? data.warnings.map((warning, index) => (
                <div key={`${warning}-${index + 1}`} className="rounded-md border border-slate-700 bg-slate-900 p-3 text-sm text-slate-300">
                  {warning}
                </div>
              )) : (
                <div className="rounded-md border border-slate-700 bg-slate-900 p-3 text-slate-400">
                  {t('common.dataUnavailable')}
                </div>
              )}
            </div>
          </div>
        </Card>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 mb-6">
        <div className="xl:col-span-2">
          <Card title={t('compare.sections.summaryMetrics')} icon={Files}>
            <div className="overflow-x-auto">
              <table className="min-w-full text-sm">
                <thead className="text-slate-500">
                  <tr className="border-b border-slate-700">
                    <th className="py-2 pr-4 text-left">{t('compare.labels.metric')}</th>
                    <th className="py-2 pr-4 text-left">{t('compare.labels.runAValue')}</th>
                    <th className="py-2 pr-4 text-left">{t('compare.labels.runBValue')}</th>
                    <th className="py-2 pr-4 text-left">{t('compare.labels.absoluteDiff')}</th>
                    <th className="py-2 pr-4 text-left">{t('compare.labels.relativeDiff')}</th>
                    <th className="py-2 text-left">{t('compare.labels.direction')}</th>
                  </tr>
                </thead>
                <tbody>
                  {data.summaryChanges.length > 0 ? data.summaryChanges.map((row) => (
                    <tr key={row.metric} className="border-b border-slate-800 align-top">
                      <td className="py-3 pr-4 font-mono text-slate-200">{row.metric}</td>
                      <td className="py-3 pr-4 text-slate-300 break-all">{fallbackText(row.runAValue)}</td>
                      <td className="py-3 pr-4 text-slate-300 break-all">{fallbackText(row.runBValue)}</td>
                      <td className="py-3 pr-4 text-slate-300">{fallbackText(row.absoluteDiff)}</td>
                      <td className="py-3 pr-4 text-slate-300">{fallbackText(row.relativeDiff)}</td>
                      <td className="py-3 text-slate-300">{fallbackText(row.direction)}</td>
                    </tr>
                  )) : (
                    <tr>
                      <td className="py-4 text-slate-400" colSpan={6}>
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
          <Card title={t('compare.sections.outputFiles')} icon={Files}>
            <KVItem label={t('compare.labels.availableFiles')} value={data.files.available.join(', ') || t('common.dataUnavailable')} />
            <KVItem label={t('compare.labels.missingFiles')} value={data.files.missing.join(', ') || t('common.dataUnavailable')} valueClass="text-amber-400 font-mono" />
            <div className="rounded-md border border-slate-700 bg-slate-900 p-3 text-xs text-slate-400">
              {t('compare.filesHint')}
            </div>
          </Card>
        </div>
      </div>

      <Card title={t('compare.sections.reportPreview')} icon={FileDiff}>
        <div className="rounded-md border border-slate-700 bg-slate-900 p-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div className="text-xs uppercase tracking-[0.16em] text-slate-500">{t('common.reportPreview')}</div>
            <div className="text-xs text-slate-500">
              {compactRunId(data.meta.runA, 16)} vs {compactRunId(data.meta.runB, 16)}
            </div>
          </div>
          <pre className="overflow-x-auto whitespace-pre-wrap text-sm leading-6 text-slate-300">
            {data.reportPreview || t('common.dataUnavailable')}
          </pre>
        </div>
      </Card>
    </div>
  );
}
