import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import zhCommon from '../locales/zh/common.json';
import enCommon from '../locales/en/common.json';

const storageKey = 'dca-dashboard-language';
const fallbackLanguage = 'zh';

function resolveInitialLanguage() {
  if (typeof window === 'undefined') {
    return fallbackLanguage;
  }

  const cachedLanguage = window.localStorage.getItem(storageKey);
  return cachedLanguage || fallbackLanguage;
}

i18n
  .use(initReactI18next)
  .init({
    resources: {
      zh: { common: zhCommon },
      en: { common: enCommon },
    },
    lng: resolveInitialLanguage(),
    fallbackLng: fallbackLanguage,
    defaultNS: 'common',
    ns: ['common'],
    interpolation: {
      escapeValue: false,
    },
  });

i18n.on('languageChanged', (language) => {
  if (typeof window !== 'undefined') {
    window.localStorage.setItem(storageKey, language);
  }
});

export default i18n;
