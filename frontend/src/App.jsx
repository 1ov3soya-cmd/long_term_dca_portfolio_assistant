import { HashRouter, NavLink, Navigate, Route, Routes } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import LanguageSwitcher from './components/LanguageSwitcher.jsx';
import Dashboard from './pages/Dashboard/index.jsx';
import RunCompare from './pages/RunCompare/index.jsx';
import ManualRisk from './pages/ManualRisk/index.jsx';
import Research from './pages/Research/index.jsx';
import ResearchManualRisk from './pages/ResearchManualRisk/index.jsx';
import MonthlyResearch from './pages/MonthlyResearch/index.jsx';

export default function App() {
  const { t } = useTranslation();

  return (
    <HashRouter>
      <div className="min-h-screen bg-slate-900 text-slate-200">
        <header className="sticky top-0 z-20 border-b border-slate-800 bg-slate-950/90 backdrop-blur">
          <div className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-6 py-4">
            <div className="min-w-0">
              <div className="text-sm font-semibold tracking-[0.2em] text-slate-100 uppercase">
                {t('app.brand')}
              </div>
              <div className="mt-1 text-xs text-slate-400">
                {t('app.subtitle')}
              </div>
            </div>

            <div className="flex items-center gap-3">
              <nav className="flex items-center gap-2 rounded-lg border border-slate-800 bg-slate-900/80 p-1 text-sm">
                <NavLink
                  to="/"
                  end
                  className={({ isActive }) => `rounded-md px-3 py-1.5 transition-colors ${isActive ? 'bg-slate-800 text-slate-100' : 'text-slate-400 hover:bg-slate-800/70 hover:text-slate-200'}`}
                >
                  {t('nav.dashboard')}
                </NavLink>
                <NavLink
                  to="/compare"
                  className={({ isActive }) => `rounded-md px-3 py-1.5 transition-colors ${isActive ? 'bg-slate-800 text-slate-100' : 'text-slate-400 hover:bg-slate-800/70 hover:text-slate-200'}`}
                >
                  {t('nav.compare')}
                </NavLink>
                <NavLink
                  to="/manual-risk"
                  className={({ isActive }) => `rounded-md px-3 py-1.5 transition-colors ${isActive ? 'bg-slate-800 text-slate-100' : 'text-slate-400 hover:bg-slate-800/70 hover:text-slate-200'}`}
                >
                  {t('nav.manualRisk')}
                </NavLink>
                <NavLink
                  to="/research"
                  className={({ isActive }) => `rounded-md px-3 py-1.5 transition-colors ${isActive ? 'bg-slate-800 text-slate-100' : 'text-slate-400 hover:bg-slate-800/70 hover:text-slate-200'}`}
                >
                  {t('nav.research')}
                </NavLink>
                <NavLink
                  to="/monthly-research"
                  className={({ isActive }) => `rounded-md px-3 py-1.5 transition-colors ${isActive ? 'bg-slate-800 text-slate-100' : 'text-slate-400 hover:bg-slate-800/70 hover:text-slate-200'}`}
                >
                  {t('nav.monthlyResearch')}
                </NavLink>
                <NavLink
                  to="/research-manual-risk"
                  className={({ isActive }) => `rounded-md px-3 py-1.5 transition-colors ${isActive ? 'bg-slate-800 text-slate-100' : 'text-slate-400 hover:bg-slate-800/70 hover:text-slate-200'}`}
                >
                  {t('nav.researchManualRisk')}
                </NavLink>
              </nav>
              <LanguageSwitcher />
            </div>
          </div>
        </header>

        <main className="mx-auto max-w-7xl">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/compare" element={<RunCompare />} />
            <Route path="/manual-risk" element={<ManualRisk />} />
            <Route path="/research" element={<Research />} />
            <Route path="/monthly-research" element={<MonthlyResearch />} />
            <Route path="/research-manual-risk" element={<ResearchManualRisk />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </HashRouter>
  );
}
