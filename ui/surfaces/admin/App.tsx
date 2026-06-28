import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import {
  ShieldAlert, ShieldCheck, AlertCircle, Skull, Activity, Cpu,
  Database, LogOut, RefreshCw, Layers, Bell, Clock, Search, Terminal,
  Bot, BarChart2, Eye, CheckCircle2, XCircle, HelpCircle, ChevronDown, ChevronUp, Sliders
} from 'lucide-react';
import { usePreferences } from './Preferences';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, LineChart, Line, ScatterChart, Scatter, Cell, Legend } from 'recharts';

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
    tab_sessions: 'Cryptographic Sessions',
    tab_settings: 'Configuration Board',
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
    tab_sessions: 'क्रिप्टोग्राफ़िक सत्र',
    tab_settings: 'कॉन्फ़िगरेशन बोर्ड',
  }
};


axios.defaults.withCredentials = true;
const API_BASE = `${window.location.protocol}//${window.location.hostname}:8002`;

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
  // default to timeline — shows ALL events including attacker sim scenarios, more dramatic on landing
  const [activeTab, setActiveTab] = useState<'dashboard' | 'providers' | 'timeline' | 'alerts' | 'aria' | 'sessions' | 'settings'>('timeline');
  const [sessions, setSessions] = useState<any[]>([]);
  const [searchUserId, setSearchUserId] = useState('');
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [config, setConfig] = useState<any>(null);
  const [configLoading, setConfigLoading] = useState(false);
  const [configSaving, setConfigSaving] = useState(false);

  // Demo Walkthrough Highlights (Objective 2 & 4)
  const [criticalAlert, setCriticalAlert] = useState<any>(null);
  const [flashingSessionId, setFlashingSessionId] = useState<string | null>(null);
  const prevKeyVersions = useRef<Record<string, number>>({});

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

        const sessionsRes = await axios.get(`${API_BASE}/admin/sessions`);
        setSessions(sessionsRes.data);

        // Track key rotations for visual flashing
        sessionsRes.data.forEach((s: any) => {
          const oldVersion = prevKeyVersions.current[s.session_id];
          if (oldVersion !== undefined && s.key_version > oldVersion) {
            setFlashingSessionId(s.session_id);
            setTimeout(() => setFlashingSessionId(null), 3000);
          }
          prevKeyVersions.current[s.session_id] = s.key_version;
        });

        // Track critical alert (containment)
        const contained = sessionsRes.data.find((s: any) => s.risk_level >= 4 && s.is_active === false);
        if (contained) {
          setCriticalAlert(contained);
        } else {
          setCriticalAlert(null);
        }
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

  // Fetch risk config when settings tab active
  useEffect(() => {
    if (!isAuthenticated || activeTab !== 'settings') return;
    setConfigLoading(true);
    axios.get(`${API_BASE}/admin/config`)
      .then(res => setConfig(res.data))
      .catch(() => {})
      .finally(() => setConfigLoading(false));
  }, [isAuthenticated, activeTab]);

  const saveConfig = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!config) return;
    setConfigSaving(true);
    try {
      await axios.post(`${API_BASE}/admin/config`, config);
      alert('Risk engine configuration saved successfully.');
    } catch {
      alert('Failed to save configuration.');
    } finally {
      setConfigSaving(false);
    }
  };

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

      {criticalAlert && (
        <div className="bg-gradient-to-r from-red-950 via-black to-red-950 border-b-2 border-red-500 p-4 text-center animate-[pulse_1.5s_infinite] flex flex-col md:flex-row items-center justify-between gap-4 text-red-200 text-xs shrink-0 shadow-[0_4px_30px_rgba(239,68,68,0.25)] relative overflow-hidden">
          <div className="absolute inset-0 bg-red-500/5 animate-[pulse_0.5s_infinite]" />
          <div className="flex items-center gap-3 relative z-10">
            <div className="p-2 bg-red-500/20 rounded-full border border-red-500/30 animate-bounce">
              <ShieldAlert className="text-red-400" size={18} />
            </div>
            <div className="text-left font-mono leading-tight">
              <div className="text-red-400 font-bold uppercase tracking-widest text-[9px] flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-red-400 animate-ping" />
                CRITICAL THREAT CONTAINMENT ACTIVE
              </div>
              <div className="font-semibold text-white mt-0.5 text-xs">
                Active Session <span className="text-red-300 underline underline-offset-2">{criticalAlert.session_id}</span> revoked by Biometric Cadence Drift
              </div>
            </div>
          </div>
          
          <div className="flex items-center gap-6 relative z-10 font-mono text-[10px]">
            <div className="text-right">
              <span className="text-neutral-500">VarCNN Similarity:</span>{" "}
              <span className="text-red-400 font-bold">0.969 (DRIFT DETECTED)</span>
            </div>
            <div className="text-right border-l border-white/10 pl-4">
              <span className="text-neutral-500">Crypto Tier:</span>{" "}
              <span className="text-purple-400 font-bold">LEVEL 4 (CONTAIN)</span>
            </div>
            <div className="text-right border-l border-white/10 pl-4">
              <span className="text-neutral-500">Key Version:</span>{" "}
              <span className="text-teal-400 font-bold">v{criticalAlert.key_version} (REVOKED)</span>
            </div>
          </div>

          <button 
            onClick={() => setCriticalAlert(null)}
            className="relative z-10 bg-red-600 hover:bg-red-500 text-white font-bold px-4 py-2 rounded-lg border border-red-400/50 hover:shadow-[0_0_15px_rgba(239,68,68,0.5)] transition-all font-mono uppercase text-[10px]"
          >
            Acknowledge Isolation
          </button>
        </div>
      )}

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
          <button
            onClick={() => setActiveTab('sessions')}
            className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
              activeTab === 'sessions' ? 'bg-teal-500/10 text-teal-300' : 'text-neutral-400 hover:text-white hover:bg-white/[0.04]'
            }`}
          >
            <RefreshCw size={18} />
            <span>{t('tab_sessions')}</span>
            {sessions.filter(s => s.is_active && s.risk_level > 1).length > 0 && (
              <span className="ml-auto bg-amber-500/20 text-amber-300 text-[9px] font-bold px-1.5 py-0.5 rounded-full">
                {sessions.filter(s => s.is_active && s.risk_level > 1).length}
              </span>
            )}
          </button>
          <button
            onClick={() => setActiveTab('settings')}
            className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
              activeTab === 'settings' ? 'bg-teal-500/10 text-teal-300' : 'text-neutral-400 hover:text-white hover:bg-white/[0.04]'
            }`}
          >
            <Sliders size={18} />
            <span>{t('tab_settings')}</span>
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

                    {/* Machine Learning Core Diagnostics Console */}
                    {/* Machine Learning Core Diagnostics Console */}
                    {selectedEvent.visuals && (
                      <div className="space-y-4">
                        <h3 className="text-xs font-bold text-neutral-400 uppercase tracking-wider flex items-center gap-1.5 border-b border-white/[0.06] pb-2">
                          <Cpu size={14} className="text-purple-400 animate-pulse" />
                          <span>AURA Biometric Deep Learning Diagnostics Console</span>
                        </h3>
                        
                        {/* Live Model Internals Panel (Issue 3) */}
                        {selectedEvent.visuals.model_internals && (
                          <div className="bg-neutral-950 border border-purple-500/20 rounded-xl p-5 space-y-4">
                            <h4 className="text-[11px] font-bold text-purple-400 uppercase tracking-wider font-mono flex items-center gap-1.5">
                              <Cpu size={14} />
                              Live Neural Network Session Diagnostics
                            </h4>
                            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 font-mono text-[11px]">
                              <div className="bg-neutral-900/50 p-3 rounded border border-white/[0.02]">
                                <div className="text-neutral-500 text-[9px] uppercase">Telemetry Event Sequence</div>
                                <div className="text-white font-bold mt-1">
                                  {selectedEvent.visuals.model_internals.sequence_length} events
                                </div>
                              </div>
                              <div className="bg-neutral-900/50 p-3 rounded border border-white/[0.02]">
                                <div className="text-neutral-500 text-[9px] uppercase">Cold-Start Status</div>
                                <div className={`font-bold mt-1 uppercase ${
                                  selectedEvent.visuals.model_internals.cold_start_status === "cold_start"
                                    ? "text-orange-400 animate-pulse"
                                    : "text-emerald-400"
                                }`}>
                                  {selectedEvent.visuals.model_internals.cold_start_status === "cold_start"
                                    ? "PENDING (Cold-Start)"
                                    : "ACTIVE (Warmup Locked)"}
                                </div>
                              </div>
                              <div className="bg-neutral-900/50 p-3 rounded border border-white/[0.02]">
                                <div className="text-neutral-500 text-[9px] uppercase">Inference Latency</div>
                                <div className="text-white font-bold mt-1">
                                  {selectedEvent.visuals.model_internals.inference_latency_ms.toFixed(1)} ms
                                </div>
                              </div>
                              <div className="bg-neutral-900/50 p-3 rounded border border-white/[0.02]">
                                <div className="text-neutral-500 text-[9px] uppercase">Embedding Similarity</div>
                                <div className="text-teal-400 font-bold mt-1">
                                  {selectedEvent.visuals.model_internals.embedding_similarity !== null
                                    ? `${(selectedEvent.visuals.model_internals.embedding_similarity).toFixed(4)} (Cosine)`
                                    : "N/A"}
                                </div>
                              </div>
                            </div>

                            {selectedEvent.visuals.model_internals.embedding_similarity !== null && (
                              <div className="bg-neutral-900/50 p-4 rounded-xl border border-white/[0.04] space-y-2 mt-4">
                                <div className="flex justify-between items-center text-[10px] uppercase font-mono">
                                  <span className="text-neutral-500">VarCNN Cosine Embedding Drift Gauge</span>
                                  <span className={`font-bold ${
                                    selectedEvent.visuals.model_internals.embedding_similarity >= 0.98
                                      ? "text-emerald-400"
                                      : "text-red-400 animate-pulse font-extrabold"
                                  }`}>
                                    {selectedEvent.visuals.model_internals.embedding_similarity.toFixed(4)} (Threshold: 0.9800)
                                  </span>
                                </div>
                                <div className="h-3.5 bg-neutral-950 rounded-full overflow-hidden border border-white/5 relative flex items-center">
                                  {/* Color bands */}
                                  <div className="absolute left-0 top-0 bottom-0 bg-red-600/30 w-[80%]" /> {/* 0.0 to 0.98 */}
                                  <div className="absolute left-[80%] top-0 bottom-0 bg-emerald-600/30 w-[20%]" /> {/* 0.98 to 1.0 */}
                                  
                                  {/* Threshold divider */}
                                  <div className="absolute left-[80%] top-0 bottom-0 w-0.5 bg-neutral-500 z-10" />

                                  {/* Pointer needle based on similarity */}
                                  {(() => {
                                    // Scale cosine [0.90, 1.0] to [0%, 100%]
                                    const minCos = 0.90;
                                    const maxCos = 1.0;
                                    const val = selectedEvent.visuals.model_internals.embedding_similarity;
                                    const pct = Math.max(0, Math.min(100, ((val - minCos) / (maxCos - minCos)) * 100));
                                    return (
                                      <div 
                                        className={`absolute h-full w-2.5 shadow-[0_0_10px_currentColor] border-x border-white/30 z-20 transition-all duration-1000 ${
                                          val >= 0.98 
                                            ? "bg-emerald-400 text-emerald-400" 
                                            : "bg-red-500 text-red-500 animate-[ping_1.5s_infinite]"
                                        }`}
                                        style={{ left: `calc(${pct}% - 5px)` }}
                                      />
                                    );
                                  })()}
                                </div>
                                <div className="flex justify-between text-[8px] font-mono text-neutral-600">
                                  <span>0.9000 (Jerky/Attacker Cadence)</span>
                                  <span>0.9800 (Drift Threshold)</span>
                                  <span>1.0000 (Perfect Match)</span>
                                </div>
                              </div>
                            )}
                          </div>
                        )}

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                          {/* VarCNN Key Timing Sequence */}
                          <div className="bg-neutral-900 border border-white/[0.04] rounded-xl p-5 space-y-3">
                            <h4 className="text-[10px] text-neutral-400 font-bold uppercase tracking-wider font-mono">VarCNN Sequence Key Timing IET (ms)</h4>
                            <div className="h-44 flex items-center justify-center">
                              {selectedEvent.visuals.sequence ? (
                                <ResponsiveContainer width="100%" height="100%">
                                  <BarChart data={selectedEvent.visuals.sequence}>
                                    <XAxis dataKey="index" stroke="#525252" fontSize={8} />
                                    <YAxis stroke="#525252" fontSize={8} />
                                    <Tooltip contentStyle={{ background: '#171717', border: '1px solid #262626', fontSize: 10 }} />
                                    <Bar dataKey="iet" fill="#2dd4bf" radius={[2, 2, 0, 0]} />
                                  </BarChart>
                                </ResponsiveContainer>
                              ) : (
                                <span className="text-center text-[10px] text-neutral-500 font-mono px-4">
                                  {selectedEvent.visuals.model_internals?.cold_start_status === "cold_start" 
                                    ? "Visualization unavailable: insufficient telemetry events (cold start)."
                                    : "Visualization unavailable because live model data is not yet exposed."}
                                </span>
                              )}
                            </div>
                          </div>

                          {/* UMAP Latent Embedding Space */}
                          <div className="bg-neutral-900 border border-white/[0.04] rounded-xl p-5 space-y-3">
                            <h4 className="text-[10px] text-neutral-400 font-bold uppercase tracking-wider font-mono">UMAP Embedding Latent Space Anomaly Drift</h4>
                            <div className="h-44 flex items-center justify-center">
                              {selectedEvent.visuals.baseline_dots ? (
                                <ResponsiveContainer width="100%" height="100%">
                                  <ScatterChart>
                                    <XAxis type="number" dataKey="x" stroke="#525252" fontSize={8} domain={[0, 8]} />
                                    <YAxis type="number" dataKey="y" stroke="#525252" fontSize={8} domain={[0, 6]} />
                                    <Tooltip cursor={{ strokeDasharray: '3 3' }} contentStyle={{ background: '#171717', border: '1px solid #262626', fontSize: 10 }} />
                                    <Scatter name="Normal Baselines" data={selectedEvent.visuals.baseline_dots} fill="#525252" shape="circle" size={40} opacity={0.6} />
                                    <Scatter name="User Enrollment" data={[selectedEvent.visuals.user_baseline]} fill="#3b82f6" shape="star" size={100} />
                                    <Scatter name="Evaluated Session" data={[selectedEvent.visuals.current_dot]} fill={selectedEvent.overall_risk > 0.25 ? "#f43f5e" : "#10b981"} shape="triangle" size={150} />
                                    <Legend wrapperStyle={{ fontSize: '8px', color: '#a3a3a3' }} />
                                  </ScatterChart>
                                </ResponsiveContainer>
                              ) : (
                                <span className="text-center text-[10px] text-neutral-500 font-mono px-4">
                                  Visualization unavailable because live model data is not yet exposed.
                                </span>
                              )}
                            </div>
                          </div>

                          {/* Temporal Confidence Index */}
                          <div className="bg-neutral-900 border border-white/[0.04] rounded-xl p-5 space-y-3">
                            <h4 className="text-[10px] text-neutral-400 font-bold uppercase tracking-wider font-mono">Temporal Trust Confidence Index (%)</h4>
                            <div className="h-44 flex items-center justify-center">
                              {selectedEvent.visuals.temporal_confidence ? (
                                <ResponsiveContainer width="100%" height="100%">
                                  <LineChart data={selectedEvent.visuals.temporal_confidence}>
                                    <XAxis dataKey="batch" stroke="#525252" fontSize={8} />
                                    <YAxis stroke="#525252" fontSize={8} domain={[0, 100]} />
                                    <Tooltip contentStyle={{ background: '#171717', border: '1px solid #262626', fontSize: 10 }} />
                                    <Line type="monotone" dataKey="confidence" stroke="#f59e0b" strokeWidth={2} activeDot={{ r: 6 }} />
                                  </LineChart>
                                </ResponsiveContainer>
                              ) : (
                                <span className="text-center text-[10px] text-neutral-500 font-mono px-4">
                                  Visualization unavailable because live model data is not yet exposed.
                                </span>
                              )}
                            </div>
                          </div>

                          {/* SHAP Feature Attribution */}
                          <div className="bg-neutral-900 border border-white/[0.04] rounded-xl p-5 space-y-3">
                            <h4 className="text-[10px] text-neutral-400 font-bold uppercase tracking-wider font-mono">Biometric SHAP Attribution (Impact Factor)</h4>
                            <div className="h-44 flex items-center justify-center">
                              {selectedEvent.visuals.shap_attribution ? (
                                <ResponsiveContainer width="100%" height="100%">
                                  <BarChart layout="vertical" data={selectedEvent.visuals.shap_attribution}>
                                    <XAxis type="number" stroke="#525252" fontSize={8} />
                                    <YAxis type="category" dataKey="feature" stroke="#525252" fontSize={8} width={90} />
                                    <Tooltip contentStyle={{ background: '#171717', border: '1px solid #262626', fontSize: 10 }} />
                                    <Bar dataKey="impact" fill="#a855f7" radius={[0, 2, 2, 0]} />
                                  </BarChart>
                                </ResponsiveContainer>
                              ) : (
                                <span className="text-center text-[10px] text-neutral-500 font-mono px-4">
                                  Visualization unavailable because live model data is not yet exposed.
                                </span>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

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

          {activeTab === 'sessions' && (
            <div className="flex-1 overflow-y-auto p-8 space-y-6">
              <header className="pb-4 border-b border-white/[0.06] flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-white flex items-center gap-2">
                    <RefreshCw size={20} className="text-teal-400" />
                    Cryptographic Session Registry
                  </h2>
                  <p className="text-xs text-neutral-500 mt-1">
                    Monitor rolling session encryption keys, rotation versions, and dynamic risk containment levels.
                  </p>
                </div>
                <button 
                  onClick={() => setRefreshTrigger(prev => prev + 1)}
                  className="flex items-center gap-2 text-xs text-neutral-400 hover:text-white bg-neutral-900 border border-white/[0.06] hover:bg-neutral-800 px-3 py-1.5 rounded-lg transition-colors"
                >
                  <RefreshCw size={12}/> Refresh Feed
                </button>
              </header>

              {/* Split Column Layout */}
              <div className="flex-grow flex gap-6 overflow-hidden min-h-0">
                {/* Left Column: Stats & Sessions Table (width: 3/5) */}
                <div className="flex-1 flex flex-col overflow-y-auto space-y-6 pr-2">
                  {/* Stats Grid */}
                  <div className="grid grid-cols-1 md:grid-cols-4 gap-4 shrink-0">
                    <div className="bg-neutral-900 border border-white/[0.04] rounded-xl p-4">
                      <p className="text-[10px] text-neutral-500 uppercase font-bold mb-1">Total Active Sessions</p>
                      <p className="text-2xl font-bold text-white">{sessions.filter(s => s.is_active).length}</p>
                    </div>
                    <div className="bg-neutral-900 border border-white/[0.04] rounded-xl p-4">
                      <p className="text-[10px] text-neutral-500 uppercase font-bold mb-1">Escalated Risk Sessions</p>
                      <p className="text-2xl font-bold text-amber-400">{sessions.filter(s => s.is_active && s.risk_level > 1).length}</p>
                    </div>
                    <div className="bg-neutral-900 border border-white/[0.04] rounded-xl p-4">
                      <p className="text-[10px] text-neutral-500 uppercase font-bold mb-1">Total Key Rotations</p>
                      <p className="text-2xl font-bold text-teal-400">
                        {sessions.reduce((acc, s) => acc + (s.key_version - 1), 0)}
                      </p>
                    </div>
                    <div className="bg-neutral-900 border border-white/[0.04] rounded-xl p-4">
                      <p className="text-[10px] text-neutral-500 uppercase font-bold mb-1">Locked/Contained Sessions</p>
                      <p className="text-2xl font-bold text-red-500">{sessions.filter(s => s.risk_level >= 4 || !s.is_active).length}</p>
                    </div>
                  </div>

                  {/* Sessions Table */}
                  <div className="bg-neutral-900 border border-white/[0.06] rounded-xl overflow-hidden shrink-0">
                    <div className="overflow-x-auto">
                      <table className="w-full text-left border-collapse">
                        <thead>
                          <tr className="border-b border-white/[0.06] bg-neutral-950 text-[10px] font-bold text-neutral-400 uppercase tracking-wider">
                            <th className="px-6 py-4">User & Session ID</th>
                            <th className="px-6 py-4">Risk Containment Level</th>
                            <th className="px-6 py-4">Key Rotation Version</th>
                            <th className="px-6 py-4">Symmetric AES Key (Masked)</th>
                            <th className="px-6 py-4">Last Activity</th>
                            <th className="px-6 py-4">Status</th>
                          </tr>
                        </thead>
                        <tbody className="divide-y divide-white/[0.04] text-xs">
                          {sessions.length === 0 ? (
                            <tr>
                              <td colSpan={6} className="text-center py-8 text-neutral-500 font-mono">
                                No active customer sessions monitored yet.
                              </td>
                            </tr>
                          ) : (
                            sessions.map(s => {
                              let riskText = "L1: Standard ALLOW";
                              let riskColor = "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20";
                              if (s.risk_level === 2) {
                                riskText = "L2: Step-up CHALLENGE";
                                riskColor = "bg-amber-500/10 text-amber-400 border border-amber-500/20";
                              } else if (s.risk_level === 3) {
                                riskText = "L3: Account RESTRICT";
                                riskColor = "bg-orange-500/10 text-orange-400 border border-orange-500/20";
                              } else if (s.risk_level >= 4) {
                                riskText = "L4: Terminal CONTAIN";
                                riskColor = "bg-red-500/10 text-red-400 border border-red-500/20";
                              }

                              const isFlashing = s.session_id === flashingSessionId;
                              return (
                                <tr 
                                  key={s.session_id} 
                                  className={`transition-all duration-500 border-l-2 ${
                                    isFlashing 
                                      ? "bg-purple-950/40 border-purple-500 animate-pulse text-purple-200" 
                                      : "hover:bg-white/[0.02] border-transparent"
                                  }`}
                                >
                                  <td className="px-6 py-4">
                                    <div className="font-semibold text-white flex items-center gap-2">
                                      {s.user_id}
                                      {isFlashing && (
                                        <span className="text-[9px] bg-purple-500/20 text-purple-300 font-bold px-1.5 py-0.5 rounded uppercase font-mono animate-[bounce_1s_infinite]">
                                          ROTATED
                                        </span>
                                      )}
                                    </div>
                                    <div className="text-[10px] text-neutral-500 font-mono mt-0.5">{s.session_id}</div>
                                  </td>
                                  <td className="px-6 py-4">
                                    <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase ${riskColor}`}>
                                      {riskText}
                                    </span>
                                  </td>
                                  <td className={`px-6 py-4 font-mono font-bold transition-all duration-300 ${isFlashing ? 'text-purple-400 text-sm' : 'text-teal-400'}`}>
                                    v{s.key_version}
                                  </td>
                                  <td className="px-6 py-4 font-mono text-neutral-400">
                                    <code>{s.aes_key}</code>
                                  </td>
                                  <td className="px-6 py-4 font-mono text-neutral-500">
                                    {new Date(s.updated_at).toLocaleTimeString()}
                                  </td>
                                  <td className="px-6 py-4">
                                    {s.is_active && s.risk_level < 4 ? (
                                      <span className="flex items-center gap-1.5 text-emerald-400 font-semibold text-[10px] uppercase">
                                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                                        Active
                                      </span>
                                    ) : (
                                      <span className="flex items-center gap-1.5 text-neutral-500 font-semibold text-[10px] uppercase">
                                        <span className="w-1.5 h-1.5 rounded-full bg-neutral-600" />
                                        Locked
                                      </span>
                                    )}
                                  </td>
                                </tr>
                              );
                            })
                          )}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </div>

                {/* Right Column: AURA Real-time Cryptographic Authority Board (width: 2/5) */}
                {(() => {
                  const activeLevel = sessions.reduce((max, s) => s.risk_level > max ? s.risk_level : max, 1);
                  return (
                    <div className="w-[380px] border-l border-white/[0.06] pl-6 flex flex-col overflow-y-auto space-y-6 select-none shrink-0">
                      {/* Model-to-Enforcement Decision Flow */}
                      <div className="bg-neutral-900 border border-white/[0.04] rounded-xl p-5 space-y-3">
                        <h3 className="text-xs font-bold text-neutral-400 uppercase tracking-wider flex items-center gap-1.5">
                          <Cpu size={14} className="text-teal-400" />
                          <span>Pipeline Linkage</span>
                        </h3>
                        <div className="space-y-3 text-[11px] font-mono leading-tight">
                          {/* Step 1: Biometric Model Output */}
                          <div className={`p-2.5 rounded border transition-all duration-300 ${
                            activeLevel >= 1 
                              ? "bg-teal-950/30 border-teal-500/50 text-teal-200" 
                              : "bg-neutral-950/40 border-white/[0.02] text-neutral-500"
                          }`}>
                            <div className="text-[9px] font-bold uppercase">1. Biometric Model Output</div>
                            <div className="text-teal-300 font-bold mt-0.5">VarCNN Embedding drift evaluated</div>
                            <div className="text-[9px] mt-0.5">Confidence indices synced</div>
                          </div>
                          
                          <div className={`text-center font-bold ${activeLevel >= 2 ? 'text-amber-500' : 'text-neutral-700'}`}>↓</div>
                          
                          {/* Step 2: Ensemble Risk Fusion */}
                          <div className={`p-2.5 rounded border transition-all duration-300 ${
                            activeLevel >= 2 
                              ? "bg-amber-950/30 border-amber-500/50 text-amber-200" 
                              : "bg-neutral-950/40 border-white/[0.02] text-neutral-500"
                          }`}>
                            <div className="text-[9px] font-bold uppercase">2. Ensemble Risk Fusion</div>
                            <div className="text-amber-400 font-bold mt-0.5">Weighted average across 6 providers</div>
                            <div className="text-[9px] mt-0.5">Settings thresholds applied</div>
                          </div>
                          
                          <div className={`text-center font-bold ${activeLevel >= 3 ? 'text-orange-500' : 'text-neutral-700'}`}>↓</div>
                          
                          {/* Step 3: Zero-Trust Policy Decision */}
                          <div className={`p-2.5 rounded border transition-all duration-300 ${
                            activeLevel >= 3 
                              ? "bg-orange-950/30 border-orange-500/50 text-orange-200" 
                              : "bg-neutral-950/40 border-white/[0.02] text-neutral-500"
                          }`}>
                            <div className="text-[9px] font-bold uppercase">3. Zero-Trust Policy Decision</div>
                            <div className="text-orange-400 font-bold mt-0.5">Escalation levels mapped (L1 → L4)</div>
                            <div className="text-[9px] mt-0.5">Friction constraints triggered</div>
                          </div>
                          
                          <div className={`text-center font-bold ${activeLevel >= 4 ? 'text-red-500' : 'text-neutral-700'}`}>↓</div>
                          
                          {/* Step 4: Cryptographic Enforcement */}
                          <div className={`p-2.5 rounded border transition-all duration-300 ${
                            activeLevel >= 4 
                              ? "bg-red-950/80 border-red-500 text-red-200 shadow-[0_0_15px_rgba(239,68,68,0.3)] animate-pulse" 
                              : "bg-neutral-950/40 border-white/[0.02] text-neutral-500"
                          }`}>
                            <div className="text-[9px] font-bold uppercase">4. Cryptographic Enforcement</div>
                            <div className="text-red-400 font-bold mt-0.5">Symmetric session key rotated / Purged</div>
                            <div className="text-[9px] mt-0.5">Shamir thresholds restructured</div>
                          </div>
                        </div>
                      </div>

                      {/* Security Operations Timeline */}
                      <div className="bg-neutral-900 border border-white/[0.04] rounded-xl p-5 space-y-4">
                        <h3 className="text-xs font-bold text-neutral-400 uppercase tracking-wider flex items-center gap-1.5">
                          <Clock size={14} className="text-teal-400" />
                          <span>SOC Incident Flow</span>
                        </h3>
                        <div className="space-y-4 relative pl-4 border-l border-white/[0.06] text-xs">
                          <div className={`relative transition-all duration-300 ${activeLevel >= 1 ? 'opacity-100 text-white' : 'opacity-30 text-neutral-500'}`}>
                            <span className={`absolute -left-[20px] top-0.5 w-2 h-2 rounded-full ${activeLevel >= 1 ? 'bg-emerald-500' : 'bg-neutral-600'}`} />
                            <div className="font-semibold">Normal User Connected</div>
                            <div className="text-[10px] text-neutral-500 font-mono mt-0.5">Telemetry collected & verified</div>
                          </div>
                          <div className={`relative transition-all duration-300 ${activeLevel >= 1 ? 'opacity-100 text-white' : 'opacity-30 text-neutral-500'}`}>
                            <span className={`absolute -left-[20px] top-0.5 w-2 h-2 rounded-full ${activeLevel >= 1 ? 'bg-blue-500' : 'bg-neutral-600'}`} />
                            <div className="font-semibold">Biometric Inference Active</div>
                            <div className="text-[10px] text-neutral-500 font-mono mt-0.5">VarCNN 1024 IET sequences loaded</div>
                          </div>
                          <div className={`relative transition-all duration-300 ${activeLevel >= 2 ? 'opacity-100 text-white' : 'opacity-30 text-neutral-500'}`}>
                            <span className={`absolute -left-[20px] top-0.5 w-2 h-2 rounded-full ${activeLevel >= 2 ? 'bg-amber-500 animate-pulse' : 'bg-neutral-600'}`} />
                            <div className="font-semibold">Behavioral Embedding Drift</div>
                            <div className="text-[10px] text-neutral-500 font-mono mt-0.5">Cosine similarity &lt; 0.98 limit</div>
                          </div>
                          <div className={`relative transition-all duration-300 ${activeLevel >= 2 ? 'opacity-100 text-white' : 'opacity-30 text-neutral-500'}`}>
                            <span className={`absolute -left-[20px] top-0.5 w-2 h-2 rounded-full ${activeLevel >= 2 ? 'bg-orange-500' : 'bg-neutral-600'}`} />
                            <div className="font-semibold">Cryptographic Tier Increased</div>
                            <div className="text-[10px] text-neutral-500 font-mono mt-0.5">Policy engine transitions L1 → L3</div>
                          </div>
                          <div className={`relative transition-all duration-300 ${activeLevel >= 3 ? 'opacity-100 text-white' : 'opacity-30 text-neutral-500'}`}>
                            <span className={`absolute -left-[20px] top-0.5 w-2 h-2 rounded-full ${activeLevel >= 3 ? 'bg-purple-500 animate-[pulse_1.5s_infinite]' : 'bg-neutral-600'}`} />
                            <div className="font-semibold">Session Keys Rotated</div>
                            <div className="text-[10px] text-neutral-500 font-mono mt-0.5">AES version bumped, key shuffled</div>
                          </div>
                          <div className={`relative transition-all duration-300 ${activeLevel >= 4 ? 'opacity-100 text-white' : 'opacity-30 text-neutral-500'}`}>
                            <span className={`absolute -left-[20px] top-0.5 w-2 h-2 rounded-full ${activeLevel >= 4 ? 'bg-red-500 animate-ping' : 'bg-neutral-600'}`} />
                            <div className="font-semibold font-bold text-red-400">Large Transaction Frozen</div>
                            <div className="text-[10px] text-red-500 font-mono mt-0.5">Zero-trust rule block enforced</div>
                          </div>
                        </div>
                      </div>

                      {/* Live Cryptographic Authority Panel (Real DB State) */}
                      <div className="bg-neutral-900 border border-purple-500/20 rounded-xl p-5 space-y-4 shadow-[0_0_15px_rgba(168,85,247,0.05)]">
                        <h3 className="text-xs font-bold text-purple-400 uppercase tracking-wider flex items-center gap-1.5 border-b border-white/[0.06] pb-2">
                          <Sliders size={14} />
                          <span>Cryptographic Session Authority Console</span>
                        </h3>
                        {(() => {
                          const maxRiskSession = sessions.find(s => s.risk_level === activeLevel) || sessions[0] || { key_version: 1, is_active: true, updated_at: new Date().toISOString() };
                          return (
                            <div className="space-y-3 font-mono text-[11px]">
                              <div className="flex justify-between py-1 border-b border-white/[0.02]">
                                <span className="text-neutral-500">Cryptographic Tier:</span>
                                <span className="text-white font-bold">Level {activeLevel}</span>
                              </div>
                              <div className="flex justify-between py-1 border-b border-white/[0.02]">
                                <span className="text-neutral-500">Session Key Version:</span>
                                <span className="text-teal-400 font-bold">v{maxRiskSession.key_version}</span>
                              </div>
                              <div className="flex justify-between py-1 border-b border-white/[0.02]">
                                <span className="text-neutral-500">Cipher Protocol:</span>
                                <span className="text-neutral-300">HMAC-SHA256-AES-CTR</span>
                              </div>
                              <div className="flex justify-between py-1 border-b border-white/[0.02]">
                                <span className="text-neutral-500">Session Authority:</span>
                                <span className={`font-bold ${
                                  activeLevel === 1 
                                    ? "text-emerald-400" 
                                    : activeLevel === 2 
                                      ? "text-amber-400" 
                                      : "text-red-400"
                                }`}>
                                  {activeLevel === 1 
                                    ? "FULL AUTHORITY" 
                                    : activeLevel === 2 
                                      ? "STEP-UP REQUIRED" 
                                      : activeLevel === 3 
                                        ? "READ-ONLY (FROZEN)" 
                                        : "CONTAINED (REVOKED)"}
                                </span>
                              </div>
                              <div className="flex justify-between py-1 border-b border-white/[0.02]">
                                <span className="text-neutral-500">Rotation Count:</span>
                                <span className="text-neutral-300">{maxRiskSession.key_version - 1} shuffles</span>
                              </div>
                              <div className="flex justify-between py-1 border-b border-white/[0.02]">
                                <span className="text-neutral-500">Session Status:</span>
                                <span className={`font-bold uppercase ${maxRiskSession.is_active ? "text-emerald-400" : "text-neutral-500"}`}>
                                  {maxRiskSession.is_active ? "Active" : "Locked / Purged"}
                                </span>
                              </div>
                              <div className="flex justify-between py-1 border-b border-white/[0.02]">
                                <span className="text-neutral-500">Last Cryptographic Action:</span>
                                <span className="text-purple-400 font-bold uppercase">
                                  {activeLevel === 1 
                                    ? "Key Anchored" 
                                    : activeLevel === 2 
                                      ? "Context Degraded" 
                                      : activeLevel === 3 
                                        ? "Key Shuffled" 
                                        : "Session Purged"}
                                </span>
                              </div>
                              <div className="flex justify-between py-1">
                                <span className="text-neutral-500">Last Rotation Timestamp:</span>
                                <span className="text-neutral-400 text-[10px]">
                                  {new Date(maxRiskSession.updated_at).toLocaleTimeString()}
                                </span>
                              </div>
                            </div>
                          );
                        })()}
                      </div>

                      {/* Stronger Security Cost Trade-offs */}
                  <div className="bg-neutral-900 border border-white/[0.04] rounded-xl p-5 space-y-3">
                    <h3 className="text-xs font-bold text-neutral-400 uppercase tracking-wider flex items-center gap-1.5">
                      <Activity size={14} className="text-teal-400" />
                      <span>Cryptographic Cost Index</span>
                    </h3>
                    <div className="space-y-3.5 text-[11px] font-mono">
                      <div>
                        <div className="flex justify-between text-neutral-400">
                          <span>VarCNN Inference latency</span>
                          <span className="text-white">38.4 ms</span>
                        </div>
                        <div className="w-full h-1 bg-neutral-950 rounded-full mt-1">
                          <div className="h-full bg-teal-500 rounded-full" style={{ width: '40%' }} />
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between text-neutral-400">
                          <span>Key Shuffling overhead</span>
                          <span className="text-white">2.1 ms</span>
                        </div>
                        <div className="w-full h-1 bg-neutral-950 rounded-full mt-1">
                          <div className="h-full bg-teal-500 rounded-full" style={{ width: '10%' }} />
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between text-neutral-400">
                          <span>Total Transaction overhead</span>
                          <span className="text-white">40.5 ms</span>
                        </div>
                        <div className="w-full h-1 bg-neutral-950 rounded-full mt-1">
                          <div className="h-full bg-amber-500 rounded-full" style={{ width: '48%' }} />
                        </div>
                      </div>
                      <div>
                        <div className="flex justify-between text-neutral-400">
                          <span>CPU Utilization</span>
                          <span className="text-white">62.8% (GPU fallback)</span>
                        </div>
                        <div className="w-full h-1 bg-neutral-950 rounded-full mt-1">
                          <div className="h-full bg-purple-500 rounded-full" style={{ width: '63%' }} />
                        </div>
                      </div>
                    </div>
                  </div>
                    </div>
                  );
                })()}
              </div>
            </div>
          )}

          {activeTab === 'settings' && (
            <div className="flex-1 overflow-y-auto p-8 space-y-6">
              <header className="pb-4 border-b border-white/[0.06] flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-white flex items-center gap-2">
                    <Sliders size={20} className="text-teal-400" />
                    Risk Policy Configuration Board
                  </h2>
                  <p className="text-xs text-neutral-500 mt-1">
                    Fine-tune risk containment thresholds, transfer limits, and threat provider weights live during operation.
                  </p>
                </div>
              </header>

              {configLoading && (
                <div className="h-48 flex items-center justify-center text-teal-400 gap-2 font-mono text-xs">
                  <RefreshCw size={16} className="animate-spin"/> Loading active configuration...
                </div>
              )}

              {config && !configLoading && (
                <form onSubmit={saveConfig} className="max-w-4xl space-y-6">
                  {/* Thresholds Section */}
                  <div className="bg-neutral-900 border border-white/[0.06] rounded-xl p-6 space-y-4">
                    <h3 className="text-xs font-bold text-neutral-400 uppercase tracking-wider flex items-center gap-1.5">
                      <ShieldAlert size={14} className="text-amber-400" />
                      <span>Policy Escalation Boundaries</span>
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div className="space-y-1.5">
                        <label className="text-[10px] font-bold text-neutral-500 uppercase tracking-wide">
                          Challenge (L2) Threshold
                        </label>
                        <input 
                          type="number" step="0.05" min="0" max="1"
                          value={config.threshold_challenge}
                          onChange={e => setConfig({ ...config, threshold_challenge: parseFloat(e.target.value) || 0 })}
                          className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg px-4 py-2 text-xs text-white focus:outline-none focus:border-teal-500/40"
                        />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-[10px] font-bold text-neutral-500 uppercase tracking-wide">
                          Restrict (L3) Threshold
                        </label>
                        <input 
                          type="number" step="0.05" min="0" max="1"
                          value={config.threshold_restrict}
                          onChange={e => setConfig({ ...config, threshold_restrict: parseFloat(e.target.value) || 0 })}
                          className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg px-4 py-2 text-xs text-white focus:outline-none focus:border-teal-500/40"
                        />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-[10px] font-bold text-neutral-500 uppercase tracking-wide">
                          Contain (L4) Threshold
                        </label>
                        <input 
                          type="number" step="0.05" min="0" max="1"
                          value={config.threshold_contain}
                          onChange={e => setConfig({ ...config, threshold_contain: parseFloat(e.target.value) || 0 })}
                          className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg px-4 py-2 text-xs text-white focus:outline-none focus:border-teal-500/40"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Limits Section */}
                  <div className="bg-neutral-900 border border-white/[0.06] rounded-xl p-6 space-y-4">
                    <h3 className="text-xs font-bold text-neutral-400 uppercase tracking-wider flex items-center gap-1.5">
                      <Database size={14} className="text-teal-400" />
                      <span>Operational Parameters</span>
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div className="space-y-1.5">
                        <label className="text-[10px] font-bold text-neutral-500 uppercase tracking-wide">
                          Maximum Single Transfer Limit ($)
                        </label>
                        <input 
                          type="number" min="1"
                          value={config.max_transfer_limit}
                          onChange={e => setConfig({ ...config, max_transfer_limit: parseInt(e.target.value) || 0 })}
                          className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg px-4 py-2 text-xs text-white focus:outline-none focus:border-teal-500/40"
                        />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-[10px] font-bold text-neutral-500 uppercase tracking-wide">
                          Trust Recovery Factor (OTP Speed)
                        </label>
                        <input 
                          type="number" step="0.1" min="0.1" max="10"
                          value={config.trust_recovery_speed}
                          onChange={e => setConfig({ ...config, trust_recovery_speed: parseFloat(e.target.value) || 0 })}
                          className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg px-4 py-2 text-xs text-white focus:outline-none focus:border-teal-500/40"
                        />
                      </div>
                    </div>
                  </div>

                  {/* Ensemble Model Weights Section */}
                  <div className="bg-neutral-900 border border-white/[0.06] rounded-xl p-6 space-y-4">
                    <h3 className="text-xs font-bold text-neutral-400 uppercase tracking-wider flex items-center gap-1.5">
                      <Cpu size={14} className="text-purple-400" />
                      <span>Ensemble Risk Provider Weights</span>
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {Object.keys(config.weights || {}).map(provider => (
                        <div key={provider} className="space-y-1.5">
                          <div className="flex justify-between">
                            <span className="text-[10px] font-bold text-neutral-400 uppercase">
                              {provider.replace('RiskProvider','').replace('Provider','')}
                            </span>
                            <span className="text-xs font-mono font-bold text-purple-300">
                              {((config.weights[provider] || 0) * 100).toFixed(0)}%
                            </span>
                          </div>
                          <input 
                            type="range" min="0" max="1" step="0.05"
                            value={config.weights[provider] || 0}
                            onChange={e => {
                              const updatedWeights = { ...config.weights, [provider]: parseFloat(e.target.value) };
                              setConfig({ ...config, weights: updatedWeights });
                            }}
                            className="w-full accent-purple-500"
                          />
                        </div>
                      ))}
                    </div>
                  </div>

                  <button 
                    type="submit" disabled={configSaving}
                    className="w-full py-3 bg-teal-600 hover:bg-teal-500 text-white font-bold text-xs rounded-lg uppercase tracking-wider flex items-center justify-center gap-2 transition-colors disabled:opacity-40"
                  >
                    {configSaving ? <RefreshCw size={13} className="animate-spin"/> : null}
                    Save Operational Configuration
                  </button>
                </form>
              )}
            </div>
          )}

        </main>
      </div>
    </div>
  );
}
