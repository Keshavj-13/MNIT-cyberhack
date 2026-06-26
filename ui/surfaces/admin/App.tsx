import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
  ShieldAlert, ShieldCheck, AlertCircle, Skull, Activity, Cpu,
  Database, LogOut, RefreshCw, Layers, Bell, Clock, Search, Terminal,
  Bot, BarChart2, Eye, CheckCircle2, XCircle, HelpCircle, ChevronDown, ChevronUp
} from 'lucide-react';
import { usePreferences } from './Preferences';

const T: Record<string, any> = {
  en: {
    header_title: 'MNIT Security Operations',
    header_sub: 'Real-Time Threat Console',
    logout: 'Sign Out',
    tab_dashboard: 'Risk Dashboard',
    tab_providers: 'Intelligence Providers',
    tab_timeline: 'Security Log Feed',
    tab_alerts: 'Incident Alert Stream',
    tab_aria: 'ARIA Investigations',
  },
  hi: {
    header_title: 'एमएनआईटी सुरक्षा संचालन',
    header_sub: 'रीयल-टाइम थ्रेट कंसोल',
    logout: 'साइन आउट',
    tab_dashboard: 'जोखिम डैशबोर्ड',
    tab_providers: 'खुफिया प्रदाता',
    tab_timeline: 'सुरक्षा लॉग फ़ीड',
    tab_alerts: 'घटना अलर्ट स्ट्रीम',
    tab_aria: 'ARIA जांच',
  }
};


axios.defaults.withCredentials = true;
const API_BASE = 'http://localhost:8002';

export default function App() {
  const pref = usePreferences();
  const t = (key: string) => T[pref.lang][key] || key;

  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Dashboard Data
  const [events, setEvents] = useState<any[]>([]);
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<any>(null);
  const [providers, setProviders] = useState<any[]>([]);
  const [timeline, setTimeline] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState('dashboard');
  const [searchUserId, setSearchUserId] = useState('');
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Explainability state
  const [explainData, setExplainData] = useState<any>(null);
  const [explainLoading, setExplainLoading] = useState(false);
  const [analyzeResult, setAnalyzeResult] = useState<any>(null);
  const [analyzeLoading, setAnalyzeLoading] = useState(false);
  const [showExplain, setShowExplain] = useState(false);

  // ARIA state
  const [ariaInvestigations, setAriaInvestigations] = useState<any[]>([]);
  const [selectedInv, setSelectedInv] = useState<any>(null);
  const [invLoading, setInvLoading] = useState(false);

  // Authenticate Admin
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) return;
    setLoading(true);
    setError('');
    try {
      await axios.post(`${API_BASE}/admin/auth/login`, { username, password });
      setIsAuthenticated(true);
      setActiveTab('dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid admin credentials');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await axios.post(`${API_BASE}/admin/auth/logout`);
    } catch (e) {}
    setIsAuthenticated(false);
    setUsername('');
    setPassword('');
    setSelectedEvent(null);
    setSelectedEventId(null);
  };

  // Check initial session
  useEffect(() => {
    axios.get(`${API_BASE}/admin/auth/me`)
      .then(() => setIsAuthenticated(true))
      .catch(() => setIsAuthenticated(false));
  }, []);

  // Fetch Dashboard Data on Interval
  useEffect(() => {
    if (!isAuthenticated) return;

    async function fetchAdminData() {
      try {
        const eventsRes = await axios.get(`${API_BASE}/admin/events`, {
          params: searchUserId ? { user_id: searchUserId } : {}
        });
        setEvents(eventsRes.data);
        if (eventsRes.data.length > 0 && !selectedEventId) {
          setSelectedEventId(eventsRes.data[0].id);
        }

        const providersRes = await axios.get(`${API_BASE}/admin/providers`);
        setProviders(providersRes.data.providers || []);

        const timelineRes = await axios.get(`${API_BASE}/admin/timeline`);
        setTimeline(timelineRes.data);

        const alertsRes = await axios.get(`${API_BASE}/admin/alerts`);
        setAlerts(alertsRes.data);
      } catch (err) {
        console.error("Admin fetch failed", err);
      }
    }

    fetchAdminData();
    const interval = setInterval(fetchAdminData, 6000);
    return () => clearInterval(interval);
  }, [isAuthenticated, searchUserId, refreshTrigger]);

  // Fetch individual event details
  useEffect(() => {
    if (!selectedEventId || !isAuthenticated) return;
    axios.get(`${API_BASE}/admin/events/${selectedEventId}`)
      .then(res => setSelectedEvent(res.data))
      .catch(err => console.error("Event detail fetch failed", err));
    // reset explainability when event changes
    setExplainData(null); setAnalyzeResult(null); setShowExplain(false);
  }, [selectedEventId, isAuthenticated]);

  // Fetch ARIA investigations when tab active
  useEffect(() => {
    if (!isAuthenticated || activeTab !== 'aria') return;
    setInvLoading(true);
    axios.get(`${API_BASE}/admin/aria/investigations`)
      .then(res => setAriaInvestigations(res.data))
      .catch(() => {})
      .finally(() => setInvLoading(false));
  }, [isAuthenticated, activeTab, refreshTrigger]);

  const fetchExplain = async (eventId: number) => {
    setExplainLoading(true); setExplainData(null);
    try { const r = await axios.get(`${API_BASE}/admin/events/${eventId}/explain`); setExplainData(r.data); }
    catch (e) { console.error(e); }
    finally { setExplainLoading(false); setShowExplain(true); }
  };

  const fetchAnalyze = async (eventId: number) => {
    setAnalyzeLoading(true); setAnalyzeResult(null);
    try { const r = await axios.post(`${API_BASE}/admin/events/${eventId}/analyze`); setAnalyzeResult(r.data); }
    catch (e) { console.error(e); }
    finally { setAnalyzeLoading(false); }
  };

  const updateInvStatus = async (id: number, status: string) => {
    await axios.patch(`${API_BASE}/admin/aria/investigations/${id}/status`, { status });
    setAriaInvestigations(prev => prev.map(i => i.id === id ? { ...i, status } : i));
    if (selectedInv?.id === id) setSelectedInv((p: any) => ({ ...p, status }));
  };

  const levels = [
    { name: 'MONITOR', color: 'bg-emerald-500 text-emerald-400 border-emerald-500/20 bg-emerald-500/10', icon: ShieldCheck },
    { name: 'CHALLENGE', color: 'bg-amber-500 text-amber-400 border-amber-500/20 bg-amber-500/10', icon: AlertCircle },
    { name: 'RESTRICT', color: 'bg-orange-600 text-orange-400 border-orange-500/20 bg-orange-500/10', icon: ShieldAlert },
    { name: 'CONTAINMENT', color: 'bg-red-600 text-red-400 border-red-500/20 bg-red-500/10', icon: Skull }
  ];

  if (!isAuthenticated) {
    return (
      <div className="flex min-h-screen bg-neutral-950 text-white font-sans items-center justify-center p-6">
        <div className="max-w-md w-full bg-neutral-900 border border-white/[0.06] rounded-xl p-8 shadow-2xl space-y-6">
          <div className="flex flex-col items-center space-y-2">
            <div className="w-12 h-12 rounded-xl bg-teal-500/10 border border-teal-500/20 text-teal-400 grid place-items-center mb-1 animate-pulse">
              <Cpu size={24} />
            </div>
            <h1 className="text-xl font-bold tracking-tight text-white uppercase">MNIT Security Administrator</h1>
            <p className="text-xs text-neutral-400 text-center">
              Internal Dashboard for Real-time ML Threat Detection & Auditing
            </p>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            {error && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-400">
                {error}
              </div>
            )}
            
            <div className="space-y-1.5">
              <label className="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Admin ID</label>
              <input 
                type="text" 
                placeholder="admin"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg px-4 py-2 text-xs text-white focus:outline-none focus:border-teal-500/50"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Password</label>
              <input 
                type="password" 
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg px-4 py-2 text-xs text-white focus:outline-none focus:border-teal-500/50"
              />
            </div>

            <button 
              type="submit" 
              disabled={loading}
              className="w-full py-2.5 bg-teal-500 hover:bg-teal-400 text-black font-bold text-xs rounded-lg transition-colors"
            >
              {loading ? 'Verifying Credentials...' : 'Sign In To Dashboard'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-neutral-950 text-white font-sans flex-col">
      {/* Top Header */}
      <header className="border-b border-white/[0.06] bg-neutral-950 px-6 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-3 text-teal-400">
          <div className="w-9 h-9 rounded-lg bg-teal-500/10 border border-teal-500/20 grid place-items-center">
            <Cpu size={20} />
          </div>
          <div>
            <h1 className="font-bold text-base leading-tight text-white">{t('header_title')}</h1>
            <p className="text-[10px] text-neutral-500 font-semibold uppercase tracking-widest font-mono">{t('header_sub')}</p>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="bg-teal-500/10 border border-teal-500/20 text-teal-300 px-3 py-1.5 rounded-full text-xs font-mono">
            SQLite Log DB: Active
          </div>

          <button 
            onClick={() => setRefreshTrigger(prev => prev + 1)}
            className="p-2 text-neutral-500 hover:text-white rounded-lg hover:bg-white/[0.04]"
            title="Refresh Live Data"
          >
            <RefreshCw size={15} />
          </button>

          <div className="flex bg-neutral-900 border border-white/[0.06] rounded-lg p-1">
            <button onClick={() => pref.setFontSize('dec')} className="px-2 text-neutral-400 hover:text-white text-[10px] font-bold">A-</button>
            <button onClick={() => pref.setFontSize('reset')} className="px-2 text-neutral-400 hover:text-white text-[10px] border-x border-white/[0.06] font-bold">A</button>
            <button onClick={() => pref.setFontSize('inc')} className="px-2 text-neutral-400 hover:text-white text-[10px] font-bold">A+</button>
          </div>

          <div className="flex bg-neutral-900 border border-white/[0.06] rounded-lg p-1 text-[10px] font-bold">
            <button onClick={() => pref.setLang('en')} className={`px-2 py-0.5 rounded ${pref.lang === 'en' ? 'bg-teal-500 text-black' : 'text-neutral-400 hover:text-white'}`}>EN</button>
            <button onClick={() => pref.setLang('hi')} className={`px-2 py-0.5 rounded ${pref.lang === 'hi' ? 'bg-teal-500 text-black' : 'text-neutral-400 hover:text-white'}`}>HI</button>
          </div>

          <button 
            onClick={handleLogout}
            className="flex items-center gap-1.5 bg-neutral-900 border border-white/[0.06] hover:bg-neutral-800 text-neutral-400 hover:text-white px-3 py-1.5 rounded-lg text-xs"
          >
            <LogOut size={13} />
            <span>{t('logout')}</span>
          </button>
        </div>
      </header>

      {/* Main Container */}
      <div className="flex-1 flex overflow-hidden">
        {/* Navigation Sidebar */}
        <aside className="w-60 border-r border-white/[0.06] bg-neutral-950 flex flex-col shrink-0 p-4 space-y-1">
          <button 
            onClick={() => setActiveTab('dashboard')}
            className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
              activeTab === 'dashboard' ? 'bg-teal-500/10 text-teal-300' : 'text-neutral-400 hover:text-white hover:bg-white/[0.04]'
            }`}
          >
            <Layers size={18} />
            <span>{t('tab_dashboard')}</span>
          </button>
          <button 
            onClick={() => setActiveTab('providers')}
            className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
              activeTab === 'providers' ? 'bg-teal-500/10 text-teal-300' : 'text-neutral-400 hover:text-white hover:bg-white/[0.04]'
            }`}
          >
            <Cpu size={18} />
            <span>{t('tab_providers')}</span>
          </button>
          <button 
            onClick={() => setActiveTab('timeline')}
            className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
              activeTab === 'timeline' ? 'bg-teal-500/10 text-teal-300' : 'text-neutral-400 hover:text-white hover:bg-white/[0.04]'
            }`}
          >
            <Clock size={18} />
            <span>{t('tab_timeline')}</span>
          </button>
          <button
            onClick={() => setActiveTab('alerts')}
            className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
              activeTab === 'alerts' ? 'bg-teal-500/10 text-teal-300' : 'text-neutral-400 hover:text-white hover:bg-white/[0.04]'
            }`}
          >
            <Bell size={18} />
            <span>{t('tab_alerts')}</span>
          </button>
          <button
            onClick={() => setActiveTab('aria')}
            className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
              activeTab === 'aria' ? 'bg-purple-500/10 text-purple-300' : 'text-neutral-400 hover:text-white hover:bg-white/[0.04]'
            }`}
          >
            <Bot size={18} />
            <span>{t('tab_aria')}</span>
            {ariaInvestigations.filter(i => i.status === 'open').length > 0 && (
              <span className="ml-auto bg-purple-500/20 text-purple-300 text-[9px] font-bold px-1.5 py-0.5 rounded-full">
                {ariaInvestigations.filter(i => i.status === 'open').length}
              </span>
            )}
          </button>
        </aside>

        {/* Content Panel */}
        <main className="flex-1 overflow-hidden bg-neutral-950 flex flex-col">
          
          {/* RISK DASHBOARD */}
          {activeTab === 'dashboard' && (
            <div className="flex-1 flex overflow-hidden">
              {/* Events Sidebar */}
              <div className="w-80 border-r border-white/[0.06] flex flex-col shrink-0">
                <div className="p-4 border-b border-white/[0.06] flex items-center relative">
                  <Search size={14} className="absolute left-7 text-neutral-500" />
                  <input 
                    type="text" 
                    placeholder="Search User ID..."
                    value={searchUserId}
                    onChange={(e) => setSearchUserId(e.target.value)}
                    className="w-full bg-neutral-900 border border-white/[0.08] rounded-lg pl-9 pr-4 py-1.5 text-xs focus:outline-none focus:border-teal-500/50"
                  />
                </div>
                
                <div className="flex-1 overflow-y-auto divide-y divide-white/[0.04]">
                  {events.map((e) => {
                    const level = levels[e.level - 1] || levels[0];
                    return (
                      <button 
                        key={e.id}
                        onClick={() => setSelectedEventId(e.id)}
                        className={`w-full text-left p-4 hover:bg-white/[0.02] transition-colors flex flex-col space-y-1.5 ${
                          selectedEventId === e.id ? 'bg-white/[0.02]' : ''
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-[10px] font-mono text-neutral-400 truncate max-w-[140px]">{e.user_id}</span>
                          <span className="text-[9px] font-mono text-neutral-500">{new Date(e.timestamp).toLocaleTimeString()}</span>
                        </div>
                        <p className="text-xs text-neutral-300 font-medium truncate">{e.why_decision}</p>
                        <div className="flex items-center justify-between">
                          <span className={`text-[9px] px-2 py-0.5 rounded border ${level.color}`}>{level.name}</span>
                          <span className="text-xs font-mono font-bold text-neutral-400">{(e.overall_risk * 100).toFixed(0)}/100</span>
                        </div>
                      </button>
                    );
                  })}
                </div>
              </div>

              {/* Event Detailed View */}
              <div className="flex-1 overflow-y-auto p-8">
                {selectedEvent ? (
                  <div className="space-y-6">
                    <header className="flex justify-between items-start pb-4 border-b border-white/[0.06]">
                      <div>
                        <h2 className="text-xl font-bold tracking-tight">Threat Evaluation: Event #{selectedEvent.id}</h2>
                        <p className="text-xs text-neutral-500 font-mono mt-1">
                          USER: {selectedEvent.user_id} | SESSION: {selectedEvent.session_id} | TIME: {new Date(selectedEvent.timestamp).toLocaleString()}
                        </p>
                      </div>
                      
                      {(() => {
                        const level = levels[selectedEvent.level - 1] || levels[0];
                        const Icon = level.icon;
                        return (
                          <div className={`flex items-center space-x-2 px-4 py-2 rounded-lg border ${level.color}`}>
                            <Icon size={18} />
                            <span className="font-bold text-xs tracking-wider uppercase">{level.name}</span>
                          </div>
                        );
                      })()}
                    </header>

                    {/* Numeric Scores */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                      <div className="bg-neutral-900 border border-white/[0.04] p-5 rounded-xl">
                        <span className="text-neutral-400 text-xs font-medium uppercase tracking-wider">Risk Score</span>
                        <div className="mt-2 flex items-baseline space-x-1.5 font-mono">
                          <span className="text-3xl font-bold text-white">{(selectedEvent.overall_risk * 100).toFixed(1)}</span>
                          <span className="text-neutral-500 text-sm">/ 100</span>
                        </div>
                      </div>

                      <div className="bg-neutral-900 border border-white/[0.04] p-5 rounded-xl">
                        <span className="text-neutral-400 text-xs font-medium uppercase tracking-wider">Confidence Metric</span>
                        <div className="mt-2 flex items-baseline space-x-1 font-mono">
                          <span className="text-3xl font-bold text-white">{(selectedEvent.confidence * 100).toFixed(1)}%</span>
                        </div>
                      </div>

                      <div className="bg-neutral-900 border border-white/[0.04] p-5 rounded-xl">
                        <span className="text-neutral-400 text-xs font-medium uppercase tracking-wider">Auto Decision</span>
                        <div className="mt-2 flex items-baseline font-mono text-xl font-bold">
                          <span className="text-teal-400">{selectedEvent.decision}</span>
                        </div>
                        <p className="text-[10px] text-neutral-400 mt-1 italic">"{selectedEvent.recommendation}"</p>
                      </div>
                    </div>

                    {/* Threat correlation narrative */}
                    <div className="bg-neutral-900 border border-white/[0.04] rounded-xl p-5 space-y-2">
                      <h3 className="text-xs font-bold text-neutral-400 uppercase tracking-wider flex items-center gap-1.5">
                        <ShieldAlert size={14} className="text-teal-400" />
                        <span>Correlation Engine Narrative</span>
                      </h3>
                      <p className="text-xs text-neutral-300 leading-relaxed bg-neutral-950 p-4 border border-white/[0.02] rounded-lg">
                        {selectedEvent.why_decision}
                      </p>
                    </div>

                    {/* Breakdown per model provider */}
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                      <div className="bg-neutral-900 border border-white/[0.04] rounded-xl p-5 space-y-4">
                        <h3 className="text-xs font-bold text-neutral-400 uppercase tracking-wider">Intelligence Provider Sub-Scores</h3>
                        <div className="divide-y divide-white/[0.04] space-y-1">
                          {Object.entries(selectedEvent.breakdown || {}).map(([name, data]: [string, any]) => (
                            <div key={name} className="py-2.5 flex items-center justify-between first:pt-0 last:pb-0">
                              <div>
                                <p className="text-xs font-bold text-white">{name}</p>
                                <p className="text-[10px] text-neutral-500 leading-tight">{data.explanations[0] || 'No specific threat flags raised.'}</p>
                              </div>
                              <span className={`text-xs font-mono font-bold ${data.risk_score > 0.5 ? 'text-amber-400' : 'text-neutral-400'}`}>
                                {(data.risk_score * 100).toFixed(0)}/100
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>

                      {/* Raw JSON payload inspector */}
                      <div className="bg-neutral-900 border border-white/[0.04] rounded-xl p-5 flex flex-col space-y-3">
                        <h3 className="text-xs font-bold text-neutral-400 uppercase tracking-wider flex items-center gap-1.5">
                          <Terminal size={14} />
                          <span>Raw Request Payload</span>
                        </h3>
                        <pre className="flex-1 bg-neutral-950 p-4 border border-white/[0.02] rounded-lg font-mono text-[10px] text-teal-400 overflow-auto max-h-64 select-all">
                          {JSON.stringify(selectedEvent.input_payload, null, 2)}
                        </pre>
                      </div>
                    </div>

                    {/* ── Explainability Panel ── */}
                    <div className="bg-neutral-900 border border-white/[0.04] rounded-xl p-5 space-y-4">
                      <div className="flex items-center justify-between">
                        <h3 className="text-xs font-bold text-neutral-400 uppercase tracking-wider flex items-center gap-1.5">
                          <BarChart2 size={14} className="text-teal-400" />
                          <span>Feature Explainability</span>
                        </h3>
                        <div className="flex items-center gap-2">
                          <button
                            onClick={() => fetchExplain(selectedEvent.id)}
                            disabled={explainLoading}
                            className="flex items-center gap-1.5 text-[10px] font-bold uppercase bg-teal-500/10 border border-teal-500/20 text-teal-300 hover:bg-teal-500/20 px-3 py-1.5 rounded-lg transition-colors"
                          >
                            <Eye size={11} />
                            {explainLoading ? 'Loading...' : 'Explain'}
                          </button>
                          {explainData && (
                            <button
                              onClick={() => fetchAnalyze(selectedEvent.id)}
                              disabled={analyzeLoading}
                              className="flex items-center gap-1.5 text-[10px] font-bold uppercase bg-purple-500/10 border border-purple-500/20 text-purple-300 hover:bg-purple-500/20 px-3 py-1.5 rounded-lg transition-colors"
                            >
                              <Bot size={11} />
                              {analyzeLoading ? 'Asking Qwen...' : 'VLM Analysis'}
                            </button>
                          )}
                          {explainData && (
                            <button onClick={() => setShowExplain(v => !v)} className="text-neutral-500 hover:text-white">
                              {showExplain ? <ChevronUp size={14}/> : <ChevronDown size={14}/>}
                            </button>
                          )}
                        </div>
                      </div>

                      {showExplain && explainData && (
                        <div className="space-y-4">
                          {Object.entries(explainData).map(([name, pdata]: [string, any]) => (
                            <div key={name} className="space-y-2">
                              <div className="flex items-center justify-between">
                                <span className="text-[10px] font-bold text-neutral-300 uppercase">{name}</span>
                                <span className="text-[10px] text-neutral-500 font-mono">{pdata.summary}</span>
                              </div>
                              {pdata.chart_png_b64 && (
                                <img
                                  src={`data:image/png;base64,${pdata.chart_png_b64}`}
                                  alt={`${name} feature importance`}
                                  className="w-full rounded-lg border border-white/[0.04]"
                                />
                              )}
                            </div>
                          ))}

                          {analyzeResult && (
                            <div className="bg-purple-500/5 border border-purple-500/20 rounded-xl p-4 space-y-2">
                              <p className="text-[10px] font-bold text-purple-300 uppercase tracking-wider flex items-center gap-1.5">
                                <Bot size={11}/> Qwen3.5-0.8B VLM Assessment
                              </p>
                              <p className="text-xs text-neutral-300 leading-relaxed">{analyzeResult.assessment}</p>
                            </div>
                          )}
                        </div>
                      )}
                      {!explainData && !explainLoading && (
                        <p className="text-[10px] text-neutral-600">Click Explain to generate feature importance charts for this event's ML providers.</p>
                      )}
                    </div>
                  </div>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-neutral-500 space-y-4">
                    <Activity size={48} className="opacity-20 animate-pulse" />
                    <p className="text-xs font-mono">Waiting for threat data from Customer API...</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* PROVIDERS TAB */}
          {activeTab === 'providers' && (
            <div className="flex-1 overflow-y-auto p-8 max-w-4xl mx-auto w-full space-y-6">
              <header className="pb-4 border-b border-white/[0.06]">
                <h2 className="text-xl font-bold tracking-tight">Intelligence Registry</h2>
                <p className="text-xs text-neutral-500 mt-1">Live status of rule engines and machine learning classifier models.</p>
              </header>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {providers.map((p: any) => (
                  <div key={p.name} className="bg-neutral-900 border border-white/[0.04] rounded-xl p-5 space-y-3">
                    <div className="flex items-center justify-between">
                      <h3 className="text-xs font-bold text-white">{p.name}</h3>
                      <span className={`text-[10px] font-mono font-bold uppercase px-2 py-0.5 rounded ${
                        p.model_loaded ? 'bg-teal-500/10 text-teal-400 border border-teal-500/20' : 'bg-neutral-800 text-neutral-500 border border-white/[0.04]'
                      }`}>
                        {p.model_type}
                      </span>
                    </div>

                    <div className="text-[11px] text-neutral-400 space-y-1">
                      <p><span className="text-neutral-500">Threat Area:</span> <span className="font-semibold">{p.category}</span></p>
                      <p className="truncate"><span className="text-neutral-500">Model Source:</span> <span className="font-mono text-neutral-300">{p.model_path || 'Inline Ruleset'}</span></p>
                    </div>

                    <div className="pt-2 border-t border-white/[0.02] flex items-center justify-between text-[10px]">
                      <span className="text-neutral-500 font-semibold uppercase tracking-wider">Status:</span>
                      <span className={`font-bold uppercase ${p.model_loaded || p.model_type === 'rules' ? 'text-teal-400' : 'text-neutral-500'}`}>
                        {p.model_loaded || p.model_type === 'rules' ? 'ONLINE / VALIDATED' : 'STUB / OFFLINE'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* LOG FEED TAB */}
          {activeTab === 'timeline' && (
            <div className="flex-1 overflow-y-auto p-8 max-w-3xl mx-auto w-full space-y-6">
              <header className="pb-4 border-b border-white/[0.06]">
                <h2 className="text-xl font-bold tracking-tight">Security Log Feed</h2>
                <p className="text-xs text-neutral-500 mt-1">Chronological history of all generated threat evaluations, including simulation scripts.</p>
              </header>

              <div className="relative border-l border-white/[0.08] ml-3 pl-6 space-y-6">
                {timeline.map((item: any) => {
                  const level = levels[item.level - 1] || levels[0];
                  return (
                    <div key={item.id} className="relative group">
                      {/* Node Bullet */}
                      <span className="absolute -left-[31px] top-1.5 w-3 h-3 rounded-full bg-neutral-950 border-2 border-teal-500"></span>
                      
                      <div className="bg-neutral-900 border border-white/[0.04] hover:border-white/[0.08] p-4 rounded-xl space-y-2 transition-colors">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-mono font-bold text-neutral-400 select-all">User: {item.user_id}</span>
                          <span className="text-[10px] text-neutral-500 font-mono">{new Date(item.timestamp).toLocaleString()}</span>
                        </div>
                        <p className="text-xs text-neutral-300">{item.why_decision}</p>
                        <div className="flex items-center gap-4 text-[10px]">
                          <span className={`px-2 py-0.5 rounded border text-[9px] ${level.color}`}>{level.name}</span>
                          <span className="text-neutral-500">Risk Score: <span className="font-bold text-white font-mono">{(item.overall_risk * 100).toFixed(0)}</span></span>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* ALERTS TAB */}
          {activeTab === 'alerts' && (
            <div className="flex-1 overflow-y-auto p-8 max-w-3xl mx-auto w-full space-y-6">
              <header className="pb-4 border-b border-white/[0.06]">
                <h2 className="text-xl font-bold tracking-tight">Incident Alert Stream</h2>
                <p className="text-xs text-neutral-500 mt-1">Real-time alerts for CHALLENGE, RESTRICT, and CONTAINMENT events.</p>
              </header>

              <div className="space-y-4">
                {alerts.map((a: any) => {
                  const level = levels[a.level - 1] || levels[0];
                  const Icon = level.icon;
                  return (
                    <div key={a.id} className="bg-neutral-900 border border-white/[0.04] p-5 rounded-xl flex items-start gap-4">
                      <div className={`grid place-items-center w-9 h-9 rounded-lg border ${level.color} shrink-0`}>
                        <Icon size={18} />
                      </div>
                      <div className="flex-1 space-y-1">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-mono font-bold text-white select-all">Incident ID: #{a.id} (User: {a.user_id})</span>
                          <span className="text-[10px] text-neutral-500 font-mono">{new Date(a.timestamp).toLocaleString()}</span>
                        </div>
                        <p className="text-xs text-neutral-300 leading-relaxed font-sans">{a.why_decision}</p>
                        <div className="flex items-center gap-4 pt-1.5 text-[10px] font-mono">
                          <span className="text-neutral-500">Risk Index: <span className="text-red-400 font-bold">{(a.overall_risk * 100).toFixed(0)}/100</span></span>
                          <span className="text-neutral-500">Escalation State: <span className="text-white font-semibold">{level.name}</span></span>
                        </div>
                      </div>
                    </div>
                  );
                })}
                {alerts.length === 0 && (
                  <div className="h-48 flex items-center justify-center border border-dashed border-white/[0.06] rounded-xl text-neutral-500 text-xs">
                    No active threat incidents reported in the alert stream.
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ARIA TAB */}
          {activeTab === 'aria' && (
            <div className="flex-1 flex overflow-hidden">
              {/* Investigation list */}
              <div className="w-80 border-r border-white/[0.06] flex flex-col shrink-0">
                <div className="p-4 border-b border-white/[0.06] flex items-center justify-between">
                  <span className="text-xs font-bold text-neutral-400 uppercase tracking-wider flex items-center gap-1.5">
                    <Bot size={13} className="text-purple-400"/>ARIA Findings
                  </span>
                  <span className="text-[9px] text-neutral-500 font-mono">auto-scans every 60s</span>
                </div>
                <div className="flex-1 overflow-y-auto divide-y divide-white/[0.04]">
                  {invLoading && <p className="p-4 text-xs text-neutral-500">Scanning...</p>}
                  {!invLoading && ariaInvestigations.length === 0 && (
                    <div className="p-6 text-center text-xs text-neutral-600">
                      No investigations yet. ARIA needs ≥3 events above 0.3 risk from the same user in 10 minutes.
                    </div>
                  )}
                  {ariaInvestigations.map(inv => (
                    <button
                      key={inv.id}
                      onClick={() => setSelectedInv(inv)}
                      className={`w-full text-left p-4 hover:bg-white/[0.02] flex flex-col gap-1.5 ${selectedInv?.id === inv.id ? 'bg-white/[0.02]' : ''}`}
                    >
                      <div className="flex items-center justify-between">
                        <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full uppercase ${
                          inv.status === 'open' ? 'bg-purple-500/20 text-purple-300' :
                          inv.status === 'resolved' ? 'bg-teal-500/20 text-teal-400' :
                          'bg-neutral-700 text-neutral-400'
                        }`}>{inv.status}</span>
                        <span className="text-[9px] text-neutral-500 font-mono">conf {(inv.confidence * 100).toFixed(0)}%</span>
                      </div>
                      <p className="text-xs text-neutral-200 font-medium leading-snug">{inv.hypothesis}</p>
                      <p className="text-[10px] text-neutral-500 font-mono">{inv.cluster_key} · {inv.event_count} events · cycle {inv.cycle}</p>
                    </button>
                  ))}
                </div>
              </div>

              {/* Investigation detail */}
              <div className="flex-1 overflow-y-auto p-8">
                {selectedInv ? (
                  <div className="space-y-6 max-w-3xl">
                    <header className="flex justify-between items-start pb-4 border-b border-white/[0.06]">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <Bot size={16} className="text-purple-400"/>
                          <h2 className="text-lg font-bold">Investigation #{selectedInv.id}</h2>
                          <span className="text-[9px] font-mono bg-neutral-800 text-neutral-400 px-2 py-0.5 rounded uppercase">{selectedInv.classification}</span>
                        </div>
                        <p className="text-xs text-neutral-400">{selectedInv.hypothesis}</p>
                        <p className="text-[10px] text-neutral-600 font-mono mt-1">User: {selectedInv.cluster_key} · {selectedInv.event_count} events · {selectedInv.cycle} scan cycles</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <button onClick={() => updateInvStatus(selectedInv.id, 'resolved')} className="flex items-center gap-1 text-[10px] bg-teal-500/10 border border-teal-500/20 text-teal-400 hover:bg-teal-500/20 px-2.5 py-1.5 rounded-lg font-bold uppercase">
                          <CheckCircle2 size={11}/> Resolve
                        </button>
                        <button onClick={() => updateInvStatus(selectedInv.id, 'fp_confirmed')} className="flex items-center gap-1 text-[10px] bg-neutral-700 border border-white/[0.06] text-neutral-400 hover:text-white px-2.5 py-1.5 rounded-lg font-bold uppercase">
                          <XCircle size={11}/> False Positive
                        </button>
                      </div>
                    </header>

                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-neutral-900 border border-white/[0.04] rounded-xl p-4">
                        <p className="text-[10px] text-neutral-500 uppercase font-bold mb-1">Evidence Summary</p>
                        <p className="text-xs text-neutral-300 leading-relaxed">{selectedInv.evidence_summary}</p>
                      </div>
                      <div className="bg-neutral-900 border border-white/[0.04] rounded-xl p-4">
                        <p className="text-[10px] text-neutral-500 uppercase font-bold mb-1">Confidence</p>
                        <div className="flex items-baseline gap-1 font-mono">
                          <span className="text-2xl font-bold text-purple-300">{(selectedInv.confidence * 100).toFixed(0)}%</span>
                        </div>
                        <div className="mt-2 h-1.5 bg-neutral-800 rounded-full overflow-hidden">
                          <div className="h-full bg-purple-500 rounded-full" style={{width: `${selectedInv.confidence * 100}%`}}/>
                        </div>
                      </div>
                    </div>

                    {selectedInv.vlm_assessment && (
                      <div className="bg-purple-500/5 border border-purple-500/20 rounded-xl p-5 space-y-2">
                        <p className="text-[10px] font-bold text-purple-300 uppercase tracking-wider flex items-center gap-1.5">
                          <Bot size={11}/> Qwen3.5-0.8B VLM Autonomous Analysis
                        </p>
                        <p className="text-xs text-neutral-300 leading-relaxed whitespace-pre-wrap">{selectedInv.vlm_assessment}</p>
                      </div>
                    )}

                    <div className="bg-neutral-900 border border-white/[0.04] rounded-xl p-4 space-y-2">
                      <p className="text-[10px] text-neutral-500 uppercase font-bold">Cluster Event IDs</p>
                      <div className="flex flex-wrap gap-2">
                        {(selectedInv.cluster_event_ids || []).map((id: number) => (
                          <button
                            key={id}
                            onClick={() => { setActiveTab('dashboard'); setSelectedEventId(id); }}
                            className="text-[10px] font-mono bg-neutral-800 hover:bg-neutral-700 text-neutral-300 px-2 py-1 rounded"
                          >
                            #{id}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-neutral-600 space-y-3">
                    <Bot size={40} className="opacity-30"/>
                    <p className="text-xs font-mono">Select an investigation from the list</p>
                  </div>
                )}
              </div>
            </div>
          )}

        </main>
      </div>
    </div>
  );
}
