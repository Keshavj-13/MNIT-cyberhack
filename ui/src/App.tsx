import { useState, useEffect } from 'react';
import axios from 'axios';
import { Shield, Activity, Database, LayoutDashboard, Landmark, ChevronsLeft, ChevronsRight, Cpu } from 'lucide-react';
import RiskDashboard from './components/RiskDashboard';
import BankSimulator from './bank/BankSimulator';
import Timeline from './components/Timeline';
import DataVerification from './components/DataVerification';
import ModelIntelligence from './components/ModelIntelligence';
import { useTelemetry } from './hooks/useTelemetry';

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

const NAV_ITEMS = [
  { key: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { key: 'verification', label: 'Data Verification', icon: Database },
  { key: 'models', label: 'Model Intelligence', icon: Cpu },
  { key: 'playground', label: 'Bank Simulator', icon: Landmark },
  { key: 'timeline', label: 'Timeline', icon: Activity },
];

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [latestResult, setLatestResult] = useState<any>(null);
  const [timeline, setTimeline] = useState([]);
  const [collapsed, setCollapsed] = useState(() => localStorage.getItem('mnit_sidebar_collapsed') === '1');

  // Initialize telemetry
  useTelemetry(activeTab);

  useEffect(() => {
    localStorage.setItem('mnit_sidebar_collapsed', collapsed ? '1' : '0');
  }, [collapsed]);

  const refreshTimeline = async () => {
    try {
      const res = await axios.get(`${API_BASE}/timeline`);
      setTimeline(res.data);
    } catch (err) {
      console.error("Failed to fetch timeline", err);
    }
  };

  useEffect(() => {
    refreshTimeline();
    const interval = setInterval(refreshTimeline, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex h-screen bg-neutral-950 font-sans text-neutral-100">
      {/* Sidebar */}
      <aside
        className={`${collapsed ? 'w-[68px]' : 'w-60'} shrink-0 flex flex-col border-r border-white/[0.06] bg-neutral-950 transition-[width] duration-200 ease-in-out`}
      >
        <div className="flex items-center h-16 px-4 border-b border-white/[0.06]">
          <div className="flex items-center gap-2.5 overflow-hidden">
            <div className="shrink-0 grid place-items-center w-8 h-8 rounded-lg bg-teal-500/10 text-teal-400 border border-teal-500/20">
              <Shield size={17} />
            </div>
            {!collapsed && (
              <span className="font-semibold text-[15px] tracking-tight text-white whitespace-nowrap">
                MNIT Security
              </span>
            )}
          </div>
        </div>

        <nav className="flex-1 px-3 py-4 space-y-1">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = activeTab === item.key;
            return (
              <button
                key={item.key}
                onClick={() => setActiveTab(item.key)}
                title={collapsed ? item.label : undefined}
                className={`w-full flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                  active
                    ? 'bg-teal-500/10 text-teal-300'
                    : 'text-neutral-400 hover:text-neutral-200 hover:bg-white/[0.04]'
                } ${collapsed ? 'justify-center' : ''}`}
              >
                <Icon size={18} className="shrink-0" />
                {!collapsed && <span className="truncate">{item.label}</span>}
              </button>
            );
          })}
        </nav>

        <div className="px-3 py-4 border-t border-white/[0.06] space-y-1">
          {!collapsed && (
            <div className="flex items-center gap-2 px-3 py-1.5 text-xs text-neutral-500">
              <Database size={13} />
              <span>SQLite Active</span>
            </div>
          )}
          <button
            onClick={() => setCollapsed((c) => !c)}
            title={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            className={`w-full flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-medium text-neutral-500 hover:text-neutral-200 hover:bg-white/[0.04] transition-colors ${
              collapsed ? 'justify-center' : ''
            }`}
          >
            {collapsed ? <ChevronsRight size={16} /> : <ChevronsLeft size={16} />}
            {!collapsed && <span>Collapse</span>}
          </button>
        </div>
      </aside>

      {/* Main Content */}
      {activeTab === 'playground' ? (
        <main className="flex-1 overflow-hidden">
          <BankSimulator onGlobalResult={setLatestResult} />
        </main>
      ) : (
        <main className="flex-1 overflow-y-auto p-8">
          {activeTab === 'dashboard' && <RiskDashboard result={latestResult} />}
          {activeTab === 'verification' && <DataVerification />}
          {activeTab === 'models' && <ModelIntelligence />}
          {activeTab === 'timeline' && <Timeline events={timeline} />}
        </main>
      )}
    </div>
  );
}

export default App;
