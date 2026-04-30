import { useTranslation } from 'react-i18next';

const languages = [
  { code: 'zh', label: '中文' },
  { code: 'en', label: 'EN' },
];

export default function LanguageSwitcher() {
  const { i18n, t } = useTranslation();

  return (
    <div className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/80 px-2 py-1.5">
      <span className="text-[11px] uppercase tracking-[0.16em] text-slate-500">
        {t('common.language')}
      </span>
      <div className="flex items-center gap-1">
        {languages.map((language) => {
          const active = i18n.language === language.code;
          return (
            <button
              key={language.code}
              type="button"
              onClick={() => i18n.changeLanguage(language.code)}
              className={`rounded-md px-2.5 py-1 text-xs transition-colors ${
                active
                  ? 'bg-slate-700 text-slate-100'
                  : 'text-slate-400 hover:bg-slate-800 hover:text-slate-200'
              }`}
            >
              {language.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}
