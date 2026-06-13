import { useState, useEffect } from 'react';
import axios from 'axios';
import { Shield, Activity, Database, LayoutDashboard, Landmark } from 'lucide-react';
import RiskDashboard from './components/RiskDashboard';
import BankSimulator from './bank/BankSimulator';
import Timeline from './components/Timeline';

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8000";

function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [latestResult, setLatestResult] = useState<any>(null);
  const [timeline, setTimeline] = useState([]);

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
    <div className="flex h-screen bg-slate-950 font-sans">
      {/* Sidebar */}
      <aside className="w-64 border-r border-slate-800 flex flex-col p-6 space-y-8">
        <div className="flex items-center space-x-3 text-blue-500">
          <Shield size={32} />
          <span className="font-bold text-xl tracking-tight text-white">MNIT SEC</span>
        </div>
        
        <nav className="flex-1 space-y-2">
          <button 
            onClick={() => setActiveTab('dashboard')}
            className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition ${activeTab === 'dashboard' ? 'bg-blue-600/20 text-blue-400 border border-blue-600/30' : 'text-slate-400 hover:bg-slate-900'}`}
          >
            <LayoutDashboard size={20} />
            <span>Dashboard</span>
          </button>
          <button
            onClick={() => setActiveTab('playground')}
            className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition ${activeTab === 'playground' ? 'bg-blue-600/20 text-blue-400 border border-blue-600/30' : 'text-slate-400 hover:bg-slate-900'}`}
          >
            <Landmark size={20} />
            <span>Bank Simulator</span>
          </button>
          <button 
            onClick={() => setActiveTab('timeline')}
            className={`w-full flex items-center space-x-3 px-4 py-3 rounded-lg transition ${activeTab === 'timeline' ? 'bg-blue-600/20 text-blue-400 border border-blue-600/30' : 'text-slate-400 hover:bg-slate-900'}`}
          >
            <Activity size={20} />
            <span>Timeline</span>
          </button>
        </nav>

        <div className="border-t border-slate-800 pt-6">
          <div className="flex items-center space-x-3 text-slate-500 text-sm">
            <Database size={16} />
            <span>SQLite Active</span>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      {activeTab === 'playground' ? (
        <main className="flex-1 overflow-hidden">
          <BankSimulator />
        </main>
      ) : (
        <main className="flex-1 overflow-y-auto p-8">
          {activeTab === 'dashboard' && <RiskDashboard result={latestResult} />}
          {activeTab === 'timeline' && <Timeline events={timeline} />}
        </main>
      )}
    </div>
  );
}

export default App;
