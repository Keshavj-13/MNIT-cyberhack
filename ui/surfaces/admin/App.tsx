import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import {
  ShieldAlert, ShieldCheck, AlertCircle, Skull, Activity, Cpu,
  Database, LogOut, RefreshCw, Layers, Bell, Clock, Search, Terminal,
  Bot, BarChart2, Eye, CheckCircle2, XCircle, HelpCircle, ChevronDown, ChevronUp,
  Sliders, Key, User, ArrowRight, Zap, Brain
} from 'lucide-react';
import { usePreferences } from './Preferences';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, LineChart, Line, Legend } from 'recharts';

const T: Record<string, any> = {
  en: {
    header_title: 'AURA Security Operations',
    header_sub: 'Real-Time Fraud Intelligence Console',
    logout: 'Sign Out',
    tab_incident: 'Incident Console',
    tab_aria: 'ARIA Investigations',
    tab_sessions: 'Session Monitor',
    tab_settings: 'Configuration',
  },
  hi: {
    header_title: 'AURA सुरक्षा संचालन',
    header_sub: 'रीयल-टाइम थ्रेट कंसोल',
    logout: 'साइन आउट',
    tab_incident: 'घटना कंसोल',
    tab_aria: 'ARIA जांच',
    tab_sessions: 'सत्र मॉनिटर',
    tab_settings: 'कॉन्फ़िगरेशन',
  }
};

axios.defaults.withCredentials = true;
const API_BASE = `${window.location.protocol}//${window.location.hostname}:8002`;

// Provider display metadata
const PROVIDER_META: Record<string, { short: string; icon: string; color: string }> = {
  BeaconBehavioralProvider:       { short: 'BEACON',      icon: '🧠', color: 'purple' },
  AccountTakeoverProvider:        { short: 'ATO',         icon: '🔐', color: 'amber' },
  TransactionRiskProvider:        { short: 'Transaction', icon: '💳', color: 'blue' },
  NetworkRiskProvider:            { short: 'Network',     icon: '🌐', color: 'teal' },
  DeviceTrustProvider:            { short: 'Device',      icon: '📱', color: 'neutral' },
  SocialEngineeringRiskProvider:  { short: 'Social',      icon: '🎣', color: 'orange' },
  PhishingRiskProvider:           { short: 'Phishing',    icon: '🎣', color: 'orange' },
};

const CUSTOMER_MSG: Record<number, { label: string; color: string; dot: string }> = {
  1: { label: 'Protected — Banking normally',       color: 'text-emerald-400', dot: 'bg-emerald-400' },
  2: { label: 'OTP verification required',          color: 'text-yellow-400',  dot: 'bg-yellow-400'  },
  3: { label: 'Sensitive operations restricted',    color: 'text-orange-400',  dot: 'bg-orange-400'  },
  4: { label: 'Session secured — forced re-login',  color: 'text-red-400',     dot: 'bg-red-400'     },
};

export default function App() {
  const pref = usePreferences();
  const t = (key: string) => T[pref.lang][key] || key;

  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const [events, setEvents] = useState<any[]>([]);
  const [selectedEventId, setSelectedEventId] = useState<number | null>(null);
  const [selectedEvent, setSelectedEvent] = useState<any>(null);
  const [providers, setProviders] = useState<any[]>([]);
  const [sessions, setSessions] = useState<any[]>([]);
  const [searchUserId, setSearchUserId] = useState('');
  const [refreshTrigger, setRefreshTrigger] = useState(0);
  const [config, setConfig] = useState<any>(null);
  const [configLoading, setConfigLoading] = useState(false);
  const [configSaving, setConfigSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<'incident' | 'aria' | 'sessions' | 'settings'>('incident');

  const [criticalAlert, setCriticalAlert] = useState<any>(null);
  const [flashingSessionId, setFlashingSessionId] = useState<string | null>(null);
  const prevKeyVersions = useRef<Record<string, number>>({});

  const [explainData, setExplainData] = useState<any>(null);
  const [explainLoading, setExplainLoading] = useState(false);
  const [analyzeResult, setAnalyzeResult] = useState<any>(null);
  const [analyzeLoading, setAnalyzeLoading] = useState(false);
  const [showExplain, setShowExplain] = useState(false);

  const [ariaInvestigations, setAriaInvestigations] = useState<any[]>([]);
  const [selectedInv, setSelectedInv] = useState<any>(null);
  const [invLoading, setInvLoading] = useState(false);

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) return;
    setLoading(true); setError('');
    try {
      await axios.post(`${API_BASE}/admin/auth/login`, { username, password });
      setIsAuthenticated(true); setActiveTab('incident');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid admin credentials');
    } finally { setLoading(false); }
  };

  const handleLogout = async () => {
    try { await axios.post(`${API_BASE}/admin/auth/logout`); } catch (e) {}
    setIsAuthenticated(false); setUsername(''); setPassword('');
    setSelectedEvent(null); setSelectedEventId(null);
  };

  useEffect(() => {
    axios.get(`${API_BASE}/admin/auth/me`)
      .then(() => setIsAuthenticated(true))
      .catch(() => setIsAuthenticated(false));
  }, []);

  useEffect(() => {
    if (!isAuthenticated) return;
    async function fetchAdminData() {
      try {
        const [evRes, prRes, sessRes] = await Promise.all([
          axios.get(`${API_BASE}/admin/events`, { params: searchUserId ? { user_id: searchUserId } : {} }),
          axios.get(`${API_BASE}/admin/providers`),
          axios.get(`${API_BASE}/admin/sessions`),
        ]);
        setEvents(evRes.data);
        if (evRes.data.length > 0 && !selectedEventId) setSelectedEventId(evRes.data[0].id);
        setProviders(prRes.data.providers || []);
        setSessions(sessRes.data);
        sessRes.data.forEach((s: any) => {
          const old = prevKeyVersions.current[s.session_id];
          if (old !== undefined && s.key_version > old) {
            setFlashingSessionId(s.session_id);
            setTimeout(() => setFlashingSessionId(null), 3000);
          }
          prevKeyVersions.current[s.session_id] = s.key_version;
        });
        const contained = sessRes.data.find((s: any) => s.risk_level >= 4 && s.is_active === false);
        setCriticalAlert(contained || null);
      } catch (err) { console.error('Admin fetch failed', err); }
    }
    fetchAdminData();
    const iv = setInterval(fetchAdminData, 6000);
    return () => clearInterval(iv);
  }, [isAuthenticated, searchUserId, refreshTrigger]);

  useEffect(() => {
    if (!selectedEventId || !isAuthenticated) return;
    axios.get(`${API_BASE}/admin/events/${selectedEventId}`)
      .then(res => setSelectedEvent(res.data))
      .catch(err => console.error('Event detail fetch failed', err));
    setExplainData(null); setAnalyzeResult(null); setShowExplain(false);
  }, [selectedEventId, isAuthenticated]);

  useEffect(() => {
    if (!isAuthenticated || activeTab !== 'aria') return;
    setInvLoading(true);
    axios.get(`${API_BASE}/admin/aria/investigations`)
      .then(res => setAriaInvestigations(res.data))
      .catch(() => {})
      .finally(() => setInvLoading(false));
  }, [isAuthenticated, activeTab, refreshTrigger]);

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
      alert('Configuration saved.');
    } catch { alert('Save failed.'); } finally { setConfigSaving(false); }
  };

  const fetchExplain = async (id: number) => {
    setExplainLoading(true); setExplainData(null);
    try { const r = await axios.get(`${API_BASE}/admin/events/${id}/explain`); setExplainData(r.data); }
    catch (e) { console.error(e); } finally { setExplainLoading(false); setShowExplain(true); }
  };

  const fetchAnalyze = async (id: number) => {
    setAnalyzeLoading(true); setAnalyzeResult(null);
    try { const r = await axios.post(`${API_BASE}/admin/events/${id}/analyze`); setAnalyzeResult(r.data); }
    catch (e) { console.error(e); } finally { setAnalyzeLoading(false); }
  };

  const updateInvStatus = async (id: number, status: string) => {
    await axios.patch(`${API_BASE}/admin/aria/investigations/${id}/status`, { status });
    setAriaInvestigations(prev => prev.map(i => i.id === id ? { ...i, status } : i));
    if (selectedInv?.id === id) setSelectedInv((p: any) => ({ ...p, status }));
  };

  const levels = [
    { name: 'MONITOR',     color: 'text-emerald-400 border-emerald-500/20 bg-emerald-500/10', icon: ShieldCheck },
    { name: 'CHALLENGE',   color: 'text-amber-400   border-amber-500/20   bg-amber-500/10',   icon: AlertCircle },
    { name: 'RESTRICT',    color: 'text-orange-400  border-orange-500/20  bg-orange-500/10',  icon: ShieldAlert },
    { name: 'CONTAIN',     color: 'text-red-400     border-red-500/20     bg-red-500/10',     icon: Skull },
  ];

  // ── LOGIN ─────────────────────────────────────────────────────────────────
  if (!isAuthenticated) {
    return (
      <div className="flex min-h-screen bg-neutral-950 text-white font-sans items-center justify-center p-6">
        <div className="max-w-md w-full bg-neutral-900 border border-white/[0.06] rounded-xl p-8 shadow-2xl space-y-6">
          <div className="flex flex-col items-center space-y-2">
            <div className="w-12 h-12 rounded-xl bg-teal-500/10 border border-teal-500/20 text-teal-400 grid place-items-center mb-1">
              <Brain size={24} />
            </div>
            <h1 className="text-xl font-bold tracking-tight text-white">AURA Security Operations</h1>
            <p className="text-xs text-neutral-400 text-center">Fraud Intelligence & Behavioral AI Console</p>
          </div>
          <form onSubmit={handleLogin} className="space-y-4">
            {error && <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-400">{error}</div>}
            <div className="space-y-1.5">
              <label className="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Admin ID</label>
              <input type="text" placeholder="admin" value={username} onChange={e => setUsername(e.target.value)}
                className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg px-4 py-2 text-xs text-white focus:outline-none focus:border-teal-500/50" />
            </div>
            <div className="space-y-1.5">
              <label className="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Password</label>
              <input type="password" placeholder="••••••••" value={password} onChange={e => setPassword(e.target.value)}
                className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg px-4 py-2 text-xs text-white focus:outline-none focus:border-teal-500/50" />
            </div>
            <button type="submit" disabled={loading}
              className="w-full py-2.5 bg-teal-500 hover:bg-teal-400 text-black font-bold text-xs rounded-lg transition-colors">
              {loading ? 'Verifying...' : 'Sign In To Dashboard'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  // ── PIPELINE HELPER ───────────────────────────────────────────────────────
  const PipelineStage = ({ label, value, sub, active, color = 'neutral' }: any) => {
    const colors: Record<string, string> = {
      neutral: 'border-white/[0.08] bg-neutral-900',
      teal:    'border-teal-500/30   bg-teal-500/10',
      amber:   'border-amber-500/30  bg-amber-500/10',
      orange:  'border-orange-500/30 bg-orange-500/10',
      red:     'border-red-500/30    bg-red-500/10',
      purple:  'border-purple-500/30 bg-purple-500/10',
    };
    const textColors: Record<string, string> = {
      neutral: 'text-neutral-400', teal: 'text-teal-300', amber: 'text-amber-300',
      orange: 'text-orange-300', red: 'text-red-300', purple: 'text-purple-300',
    };
    return (
      <div className={`flex-1 min-w-0 rounded-lg border px-3 py-2 text-center transition-all ${active ? colors[color] : 'border-white/[0.04] bg-neutral-950'}`}>
        <div className={`text-[8px] font-bold uppercase tracking-wider ${active ? textColors[color] : 'text-neutral-600'}`}>{label}</div>
        <div className={`text-[11px] font-bold font-mono mt-0.5 truncate ${active ? textColors[color] : 'text-neutral-700'}`}>{value}</div>
        {sub && <div className="text-[8px] text-neutral-600 mt-0.5 truncate">{sub}</div>}
      </div>
    );
  };

  // ── PROVIDER CARD ─────────────────────────────────────────────────────────
  const ProviderCard = ({ name, data, weight }: any) => {
    const meta = PROVIDER_META[name] || { short: name.replace('Provider','').replace('Risk',''), icon: '⚡', color: 'neutral' };
    const score = Math.round((data?.risk_score || 0) * 100);
    const triggered = score > 40;
    const explanation = data?.explanations?.[0] || 'No anomaly detected';
    const barColors: Record<string, string> = {
      neutral: 'bg-neutral-500', teal: 'bg-teal-500', amber: 'bg-amber-500',
      orange: 'bg-orange-500', red: 'bg-red-500', purple: 'bg-purple-500', blue: 'bg-blue-500',
    };
    const barColor = score >= 60 ? 'bg-red-500' : score >= 40 ? 'bg-orange-500' : score >= 20 ? 'bg-amber-500' : 'bg-teal-500';
    return (
      <div className={`bg-neutral-900 border rounded-xl p-4 space-y-2.5 transition-all ${triggered ? 'border-orange-500/20' : 'border-white/[0.04]'}`}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-base">{meta.icon}</span>
            <span className="text-xs font-bold text-white">{meta.short}</span>
          </div>
          <div className="flex items-center gap-1.5">
            {triggered && <span className="text-[8px] font-bold bg-orange-500/20 text-orange-300 px-1.5 py-0.5 rounded uppercase">Triggered</span>}
            {weight !== undefined && <span className="text-[9px] text-neutral-500 font-mono">w={Math.round(weight*100)}%</span>}
          </div>
        </div>
        <div className="space-y-1">
          <div className="flex justify-between items-center">
            <span className="text-[9px] text-neutral-500 uppercase font-bold">Risk Score</span>
            <span className={`text-sm font-bold font-mono ${score >= 60 ? 'text-red-400' : score >= 40 ? 'text-orange-400' : score >= 20 ? 'text-amber-400' : 'text-teal-400'}`}>{score}/100</span>
          </div>
          <div className="h-1.5 bg-neutral-800 rounded-full overflow-hidden">
            <div className={`h-full rounded-full transition-all duration-500 ${barColor}`} style={{ width: `${score}%` }} />
          </div>
        </div>
        <p className="text-[10px] text-neutral-400 leading-tight">{explanation}</p>
      </div>
    );
  };

  // ── SELECTED EVENT DERIVED ────────────────────────────────────────────────
  const matchedSession = selectedEvent
    ? sessions.find(s => s.session_id === selectedEvent.session_id) || null
    : null;
  const relatedAria = selectedEvent
    ? ariaInvestigations.filter(i => i.cluster_key === selectedEvent.user_id)
    : [];

  const now = Date.now();

  // ── MAIN RENDER ───────────────────────────────────────────────────────────
  return (
    <div className="flex h-screen bg-neutral-950 text-white font-sans flex-col">
      {/* Header */}
      <header className="border-b border-white/[0.06] bg-neutral-950 px-6 py-3.5 flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-teal-500/10 border border-teal-500/20 grid place-items-center">
            <Brain size={16} className="text-teal-400" />
          </div>
          <div>
            <h1 className="font-bold text-sm leading-tight text-white">{t('header_title')}</h1>
            <p className="text-[9px] text-neutral-500 font-semibold uppercase tracking-widest">{t('header_sub')}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-[10px] text-emerald-400 font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
            <span>LIVE · SQLite Active</span>
          </div>
          <button onClick={() => setRefreshTrigger(p => p+1)} className="p-2 text-neutral-500 hover:text-white rounded-lg hover:bg-white/[0.04]">
            <RefreshCw size={14} />
          </button>
          <div className="flex bg-neutral-900 border border-white/[0.06] rounded-lg p-1 text-[10px] font-bold">
            <button onClick={() => pref.setLang('en')} className={`px-2 py-0.5 rounded ${pref.lang==='en'?'bg-teal-500 text-black':'text-neutral-400 hover:text-white'}`}>EN</button>
            <button onClick={() => pref.setLang('hi')} className={`px-2 py-0.5 rounded ${pref.lang==='hi'?'bg-teal-500 text-black':'text-neutral-400 hover:text-white'}`}>HI</button>
          </div>
          <button onClick={handleLogout} className="flex items-center gap-1.5 bg-neutral-900 border border-white/[0.06] hover:bg-neutral-800 text-neutral-400 hover:text-white px-3 py-1.5 rounded-lg text-xs">
            <LogOut size={13} /> {t('logout')}
          </button>
        </div>
      </header>

      {/* Critical alert banner */}
      {criticalAlert && (
        <div className="bg-gradient-to-r from-red-950 via-black to-red-950 border-b-2 border-red-500 p-3 text-center animate-pulse flex items-center justify-between gap-4 text-xs shrink-0">
          <div className="flex items-center gap-3">
            <div className="p-1.5 bg-red-500/20 rounded-full border border-red-500/30 animate-bounce">
              <ShieldAlert className="text-red-400" size={16} />
            </div>
            <div className="text-left font-mono">
              <div className="text-red-400 font-bold uppercase tracking-widest text-[9px] flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-red-400 animate-ping" /> CRITICAL — SESSION CONTAINED
              </div>
              <div className="text-white mt-0.5">
                User <span className="text-red-300">{criticalAlert.user_id}</span> · Session revoked · Behavioral drift exceeded threshold
              </div>
            </div>
          </div>
          <div className="flex items-center gap-4 font-mono text-[10px]">
            <div><span className="text-neutral-500">Key:</span> <span className="text-teal-400 font-bold">kv{criticalAlert.key_version} (REVOKED)</span></div>
            <div><span className="text-neutral-500">Policy:</span> <span className="text-red-400 font-bold">LEVEL 4 CONTAIN</span></div>
          </div>
          <button onClick={() => setCriticalAlert(null)} className="bg-red-600 hover:bg-red-500 text-white font-bold px-3 py-1.5 rounded-lg text-[10px] uppercase">
            Acknowledge
          </button>
        </div>
      )}

      {/* Main layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar — 4 tabs */}
        <aside className="w-56 border-r border-white/[0.06] bg-neutral-950 flex flex-col shrink-0 p-3 space-y-1">
          {([
            ['incident', t('tab_incident'),  Activity],
            ['aria',     t('tab_aria'),      Bot],
            ['sessions', t('tab_sessions'),  Database],
            ['settings', t('tab_settings'),  Sliders],
          ] as [string, string, any][]).map(([tab, label, Icon]) => (
            <button key={tab} onClick={() => setActiveTab(tab as any)}
              className={`w-full flex items-center gap-2.5 px-3 py-2.5 text-xs font-medium rounded-lg transition-colors ${
                activeTab === tab
                  ? (tab === 'aria' ? 'bg-purple-500/10 text-purple-300' : 'bg-teal-500/10 text-teal-300')
                  : 'text-neutral-400 hover:text-white hover:bg-white/[0.04]'
              }`}
            >
              <Icon size={15} />
              <span className="flex-1 text-left">{label}</span>
              {tab === 'aria' && ariaInvestigations.filter(i => i.status === 'open').length > 0 && (
                <span className="bg-purple-500/20 text-purple-300 text-[8px] font-bold px-1.5 py-0.5 rounded-full">
                  {ariaInvestigations.filter(i => i.status === 'open').length}
                </span>
              )}
              {tab === 'sessions' && sessions.filter(s => s.is_active && s.risk_level > 1).length > 0 && (
                <span className="bg-amber-500/20 text-amber-300 text-[8px] font-bold px-1.5 py-0.5 rounded-full">
                  {sessions.filter(s => s.is_active && s.risk_level > 1).length}
                </span>
              )}
            </button>
          ))}
        </aside>

        {/* Content */}
        <main className="flex-1 overflow-hidden bg-neutral-950 flex flex-col">

          {/* ══ INCIDENT CONSOLE ═══════════════════════════════════════════ */}
          {activeTab === 'incident' && (
            <div className="flex-1 flex overflow-hidden">
              {/* Left: event list */}
              <div className="w-72 border-r border-white/[0.06] flex flex-col shrink-0">
                <div className="p-3 border-b border-white/[0.06] space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="flex items-center gap-1.5 text-[9px] text-emerald-400 font-mono">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" /> LIVE · 6s refresh
                    </div>
                    <span className="ml-auto text-[9px] text-neutral-500">{events.length} events</span>
                  </div>
                  <div className="relative">
                    <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-neutral-500" />
                    <input type="text" placeholder="Filter by user..." value={searchUserId}
                      onChange={e => setSearchUserId(e.target.value)}
                      className="w-full bg-neutral-900 border border-white/[0.06] rounded-lg pl-7 pr-3 py-1.5 text-[11px] focus:outline-none focus:border-teal-500/40" />
                  </div>
                </div>
                <div className="flex-1 overflow-y-auto divide-y divide-white/[0.03]">
                  {events.map(e => {
                    const lvl = levels[(e.level || 1) - 1] || levels[0];
                    const Icon = lvl.icon;
                    const isNew = (now - new Date(e.timestamp).getTime()) < 60000;
                    return (
                      <button key={e.id} onClick={() => setSelectedEventId(e.id)}
                        className={`w-full text-left p-3 hover:bg-white/[0.02] transition-colors ${
                          selectedEventId === e.id ? 'bg-white/[0.03] border-l-2 border-teal-500' : 'border-l-2 border-transparent'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-[10px] font-mono text-neutral-300 font-semibold truncate max-w-[120px]">{e.user_id}</span>
                          <div className="flex items-center gap-1">
                            {isNew && <span className="w-1.5 h-1.5 rounded-full bg-teal-400 animate-pulse" />}
                            <span className="text-[9px] text-neutral-600 font-mono">{new Date(e.timestamp).toLocaleTimeString()}</span>
                          </div>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded border uppercase ${lvl.color}`}>{lvl.name}</span>
                          <span className="text-xs font-mono font-bold text-neutral-300">{Math.round((e.overall_risk||0)*100)}<span className="text-neutral-600">/100</span></span>
                        </div>
                        <p className="text-[9px] text-neutral-500 truncate mt-1">{e.why_decision}</p>
                      </button>
                    );
                  })}
                  {events.length === 0 && (
                    <div className="p-6 text-center text-[10px] text-neutral-600 font-mono">
                      No incidents yet. Run an attack scenario to populate.
                    </div>
                  )}
                </div>
              </div>

              {/* Right: incident investigation */}
              <div className="flex-1 overflow-y-auto">
                {!selectedEvent ? (
                  <div className="h-full flex flex-col items-center justify-center text-neutral-600 space-y-3">
                    <Activity size={40} className="opacity-20" />
                    <p className="text-xs font-mono">Select an incident to begin investigation</p>
                  </div>
                ) : (
                  <div className="p-6 space-y-5 max-w-none">

                    {/* ── 1. IDENTITY BAR ─────────────────────────────── */}
                    {(() => {
                      const lvl = levels[(selectedEvent.level||1)-1] || levels[0];
                      const LvlIcon = lvl.icon;
                      return (
                        <div className="bg-neutral-900 border border-white/[0.06] rounded-xl px-5 py-3 flex items-center justify-between">
                          <div className="flex items-center gap-4">
                            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border ${lvl.color}`}>
                              <LvlIcon size={14} />
                              <span className="text-xs font-bold uppercase">{lvl.name}</span>
                            </div>
                            <div>
                              <div className="flex items-center gap-2">
                                <span className="text-sm font-bold text-white">{selectedEvent.user_id}</span>
                                <span className="text-[10px] text-neutral-500 font-mono">·</span>
                                <span className="text-[10px] text-neutral-500 font-mono truncate max-w-[160px]">{selectedEvent.session_id}</span>
                              </div>
                              <div className="text-[10px] text-neutral-500 mt-0.5">
                                {new Date(selectedEvent.timestamp).toLocaleString()} · {selectedEvent.event_category || 'behavioral'}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center gap-6 text-right">
                            <div>
                              <div className="text-[9px] text-neutral-500 uppercase font-bold">Risk Score</div>
                              <div className={`text-2xl font-bold font-mono ${
                                selectedEvent.overall_risk>=0.7?'text-red-400':selectedEvent.overall_risk>=0.4?'text-orange-400':selectedEvent.overall_risk>=0.2?'text-amber-400':'text-teal-400'
                              }`}>{Math.round(selectedEvent.overall_risk*100)}<span className="text-sm text-neutral-600">/100</span></div>
                            </div>
                            <div>
                              <div className="text-[9px] text-neutral-500 uppercase font-bold">Confidence</div>
                              <div className="text-lg font-bold font-mono text-neutral-200">{Math.round(selectedEvent.confidence*100)}%</div>
                            </div>
                          </div>
                        </div>
                      );
                    })()}

                    {/* ── 2. PIPELINE STRIP ───────────────────────────── */}
                    {(() => {
                      const mi = selectedEvent.visuals?.model_internals || {};
                      const telCount = mi.sequence_length || 0;
                      const featCount = Object.keys(selectedEvent.input_payload || {}).length;
                      const provCount = Object.keys(selectedEvent.breakdown || {}).length;
                      const sim = mi.embedding_similarity;
                      const beaconScore = selectedEvent.breakdown?.BeaconBehavioralProvider?.risk_score;
                      const beaconVal = sim != null ? sim.toFixed(3) : (telCount < 64 ? 'warmup' : '—');
                      const beaconColor = sim != null ? (sim < 0.97 ? 'red' : sim < 0.99 ? 'amber' : 'teal') : 'neutral';
                      const fusionVal = `${Math.round(selectedEvent.overall_risk*100)}/100`;
                      const fusionColor = selectedEvent.overall_risk>=0.7?'red':selectedEvent.overall_risk>=0.4?'orange':selectedEvent.overall_risk>=0.2?'amber':'teal';
                      const policyColor = selectedEvent.level>=4?'red':selectedEvent.level>=3?'orange':selectedEvent.level>=2?'amber':'teal';
                      const cryptoKv = matchedSession?.key_version ?? (selectedEvent.level > 1 ? '≥2' : '1');
                      const cryptoColor = (matchedSession?.key_version ?? 1) > 1 ? 'amber' : 'neutral';
                      const custMsg = CUSTOMER_MSG[selectedEvent.level] || CUSTOMER_MSG[1];
                      const custColor = selectedEvent.level>=4?'red':selectedEvent.level>=3?'orange':selectedEvent.level>=2?'amber':'teal';
                      return (
                        <div className="bg-neutral-900 border border-white/[0.06] rounded-xl p-4">
                          <div className="text-[9px] text-neutral-500 uppercase font-bold tracking-wider mb-3 flex items-center gap-1.5">
                            <Zap size={10} className="text-teal-400" /> Decision Pipeline — Telemetry to Customer
                          </div>
                          <div className="flex items-stretch gap-1">
                            <PipelineStage label="Telemetry" value={telCount>0?`${telCount} events`:'collecting'} active={telCount>0} color="teal" />
                            <div className="flex items-center text-neutral-600 text-xs px-0.5">›</div>
                            <PipelineStage label="Features" value={featCount>0?`${featCount} extracted`:'—'} active={featCount>0} color="teal" />
                            <div className="flex items-center text-neutral-600 text-xs px-0.5">›</div>
                            <PipelineStage label="Models" value={`${provCount} providers`} sub="ensemble" active={provCount>0} color="teal" />
                            <div className="flex items-center text-neutral-600 text-xs px-0.5">›</div>
                            <PipelineStage label="BEACON" value={beaconVal} sub="cosine sim" active={sim!=null||telCount>0} color={beaconColor as any} />
                            <div className="flex items-center text-neutral-600 text-xs px-0.5">›</div>
                            <PipelineStage label="Fusion" value={fusionVal} sub="weighted avg" active color={fusionColor as any} />
                            <div className="flex items-center text-neutral-600 text-xs px-0.5">›</div>
                            <PipelineStage label="Policy" value={selectedEvent.decision} sub={`Level ${selectedEvent.level}`} active color={policyColor as any} />
                            <div className="flex items-center text-neutral-600 text-xs px-0.5">›</div>
                            <PipelineStage label="Crypto" value={`kv${cryptoKv}`} sub={matchedSession?.is_active===false?'revoked':'active'} active color={cryptoColor as any} />
                            <div className="flex items-center text-neutral-600 text-xs px-0.5">›</div>
                            <PipelineStage label="Customer" value={custMsg.label.split('—')[0].trim()} sub={custMsg.label.includes('—')?custMsg.label.split('—')[1].trim():undefined} active color={custColor as any} />
                          </div>
                        </div>
                      );
                    })()}

                    {/* ── 3. AI REASONING ─────────────────────────────── */}
                    <div className="bg-neutral-900 border border-white/[0.06] rounded-xl p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <Brain size={13} className="text-teal-400" />
                        <span className="text-[10px] font-bold text-neutral-400 uppercase tracking-wider">AI Decision Reasoning</span>
                        <span className="ml-auto text-[9px] text-neutral-600 font-mono italic">{selectedEvent.recommendation}</span>
                      </div>
                      <p className="text-xs text-neutral-300 leading-relaxed">{selectedEvent.why_decision}</p>
                    </div>

                    {/* ── 4. TWO COLUMNS: PROVIDERS + EVIDENCE ───────── */}
                    <div className="grid grid-cols-5 gap-5">
                      {/* Provider cards — 3 cols */}
                      <div className="col-span-3 space-y-3">
                        <div className="text-[10px] font-bold text-neutral-400 uppercase tracking-wider flex items-center gap-1.5">
                          <Cpu size={12} className="text-purple-400" /> ML Provider Intelligence · {Object.keys(selectedEvent.breakdown||{}).length} models evaluated
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                          {Object.entries(selectedEvent.breakdown || {}).map(([name, data]: [string, any]) => (
                            <ProviderCard key={name} name={name} data={data} weight={config?.weights?.[name]} />
                          ))}
                          {Object.keys(selectedEvent.breakdown || {}).length === 0 && (
                            <div className="col-span-2 text-center text-xs text-neutral-600 py-8 border border-dashed border-white/[0.06] rounded-xl">
                              No provider breakdown available for this event.
                            </div>
                          )}
                        </div>
                      </div>

                      {/* Evidence charts — 2 cols */}
                      <div className="col-span-2 space-y-3">
                        <div className="text-[10px] font-bold text-neutral-400 uppercase tracking-wider flex items-center gap-1.5">
                          <BarChart2 size={12} className="text-teal-400" /> Behavioral Evidence
                        </div>

                        {/* VarCNN IET */}
                        <div className="bg-neutral-900 border border-white/[0.04] rounded-xl p-3">
                          <div className="text-[9px] text-neutral-500 uppercase font-bold mb-1">
                            Keystroke Timing · VarCNN Input (IET ms)
                            <span className="ml-1 text-neutral-600 normal-case font-normal">LIVE</span>
                          </div>
                          <div className="h-28">
                            {selectedEvent.visuals?.sequence ? (
                              <ResponsiveContainer width="100%" height="100%">
                                <BarChart data={selectedEvent.visuals.sequence} margin={{top:0,right:0,left:-20,bottom:0}}>
                                  <XAxis dataKey="index" stroke="#404040" fontSize={7} tickLine={false} />
                                  <YAxis stroke="#404040" fontSize={7} tickLine={false} />
                                  <Tooltip contentStyle={{background:'#171717',border:'1px solid #262626',fontSize:9}} />
                                  <Bar dataKey="iet" fill="#2dd4bf" radius={[1,1,0,0]} maxBarSize={8} />
                                </BarChart>
                              </ResponsiveContainer>
                            ) : (
                              <div className="h-full flex items-center justify-center text-[10px] text-neutral-600 font-mono text-center px-2">
                                {(selectedEvent.visuals?.model_internals?.sequence_length||0) < 3
                                  ? 'Warmup: collecting telemetry (< 3 events)'
                                  : 'Insufficient events for IET sequence'}
                              </div>
                            )}
                          </div>
                        </div>

                        {/* SHAP */}
                        <div className="bg-neutral-900 border border-white/[0.04] rounded-xl p-3">
                          <div className="text-[9px] text-neutral-500 uppercase font-bold mb-1">
                            Feature Attribution · SHAP Impact
                            <span className="ml-1 text-neutral-600 normal-case font-normal">DERIVED</span>
                          </div>
                          <div className="h-28">
                            {selectedEvent.visuals?.shap_attribution ? (
                              <ResponsiveContainer width="100%" height="100%">
                                <BarChart layout="vertical" data={selectedEvent.visuals.shap_attribution} margin={{top:0,right:10,left:0,bottom:0}}>
                                  <XAxis type="number" stroke="#404040" fontSize={7} tickLine={false} />
                                  <YAxis type="category" dataKey="feature" stroke="#404040" fontSize={7} width={80} tickLine={false} />
                                  <Tooltip contentStyle={{background:'#171717',border:'1px solid #262626',fontSize:9}} />
                                  <Bar dataKey="impact" fill="#a855f7" radius={[0,2,2,0]} />
                                </BarChart>
                              </ResponsiveContainer>
                            ) : (
                              <div className="h-full flex items-center justify-center text-[10px] text-neutral-600 font-mono text-center px-2">
                                SHAP unavailable — insufficient telemetry events
                              </div>
                            )}
                          </div>
                        </div>

                        {/* Risk history */}
                        <div className="bg-neutral-900 border border-white/[0.04] rounded-xl p-3">
                          <div className="text-[9px] text-neutral-500 uppercase font-bold mb-1">
                            Session Risk Evolution
                            <span className="ml-1 text-neutral-600 normal-case font-normal">LIVE</span>
                          </div>
                          <div className="h-28">
                            {selectedEvent.visuals?.temporal_confidence?.length > 0 ? (
                              <ResponsiveContainer width="100%" height="100%">
                                <LineChart data={selectedEvent.visuals.temporal_confidence} margin={{top:4,right:4,left:-20,bottom:0}}>
                                  <XAxis dataKey="batch" stroke="#404040" fontSize={7} tickLine={false} />
                                  <YAxis stroke="#404040" fontSize={7} tickLine={false} domain={[0,100]} />
                                  <Tooltip contentStyle={{background:'#171717',border:'1px solid #262626',fontSize:9}} />
                                  <Line type="monotone" dataKey="risk" stroke="#f43f5e" strokeWidth={2} dot={false} name="Risk" />
                                  <Line type="monotone" dataKey="confidence" stroke="#2dd4bf" strokeWidth={1.5} dot={false} name="Confidence" strokeDasharray="4 2" />
                                </LineChart>
                              </ResponsiveContainer>
                            ) : (
                              <div className="h-full flex items-center justify-center text-[10px] text-neutral-600 font-mono">No history yet</div>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* ── 5. OUTCOME STRIP ────────────────────────────── */}
                    <div className="grid grid-cols-3 gap-4">
                      {/* Crypto action */}
                      <div className="bg-neutral-900 border border-white/[0.06] rounded-xl p-4 space-y-2">
                        <div className="flex items-center gap-2">
                          <Key size={13} className="text-teal-400" />
                          <span className="text-[10px] font-bold text-neutral-400 uppercase tracking-wider">Cryptographic Action</span>
                        </div>
                        {matchedSession ? (
                          <>
                            <div className="font-mono text-sm font-bold text-teal-300">kv{matchedSession.key_version}</div>
                            <div className="text-[10px] text-neutral-400">
                              {matchedSession.key_version > 1 ? `Key rotated ${matchedSession.key_version - 1}×` : 'No rotation (Level 1)'}
                              {!matchedSession.is_active && ' · Session revoked & purged'}
                            </div>
                            <div className="text-[9px] text-neutral-600 font-mono">{new Date(matchedSession.updated_at).toLocaleTimeString()}</div>
                          </>
                        ) : (
                          <div className="text-[10px] text-neutral-600">Session not in monitor scope</div>
                        )}
                      </div>

                      {/* Customer impact */}
                      <div className="bg-neutral-900 border border-white/[0.06] rounded-xl p-4 space-y-2">
                        <div className="flex items-center gap-2">
                          <User size={13} className="text-amber-400" />
                          <span className="text-[10px] font-bold text-neutral-400 uppercase tracking-wider">Customer Impact</span>
                        </div>
                        {(() => {
                          const cm = CUSTOMER_MSG[selectedEvent.level] || CUSTOMER_MSG[1];
                          return (
                            <>
                              <div className="flex items-center gap-2">
                                <span className={`w-2 h-2 rounded-full ${cm.dot}`} />
                                <span className={`text-xs font-bold ${cm.color}`}>{cm.label}</span>
                              </div>
                              <div className="text-[10px] text-neutral-400 leading-snug">
                                {selectedEvent.level === 1 && 'No friction. Customer banking normally.'}
                                {selectedEvent.level === 2 && 'OTP sent to registered mobile. Transfer pending verification.'}
                                {selectedEvent.level === 3 && 'High-value transfers and beneficiary additions blocked.'}
                                {selectedEvent.level === 4 && 'Session immediately invalidated. Customer shown "Session Secured" screen.'}
                              </div>
                            </>
                          );
                        })()}
                      </div>

                      {/* ARIA */}
                      <div className="bg-neutral-900 border border-white/[0.06] rounded-xl p-4 space-y-2">
                        <div className="flex items-center gap-2">
                          <Bot size={13} className="text-purple-400" />
                          <span className="text-[10px] font-bold text-neutral-400 uppercase tracking-wider">ARIA Autonomous Agent</span>
                        </div>
                        {relatedAria.length > 0 ? (
                          <>
                            <div className="text-xs font-bold text-purple-300">{relatedAria[0].hypothesis}</div>
                            <div className="text-[10px] text-neutral-400">Investigation #{relatedAria[0].id} · {relatedAria[0].event_count} events · {Math.round(relatedAria[0].confidence*100)}% confidence</div>
                            <button onClick={() => setActiveTab('aria')}
                              className="text-[9px] text-purple-400 hover:text-purple-300 font-bold uppercase tracking-wider flex items-center gap-1">
                              View Investigation <ArrowRight size={10} />
                            </button>
                          </>
                        ) : (
                          <div className="text-[10px] text-neutral-600">
                            No autonomous investigation triggered yet.
                            <br /><span className="text-[9px]">ARIA needs ≥3 events at risk ≥0.3 within 10 min.</span>
                          </div>
                        )}
                      </div>
                    </div>

                    {/* ── 6. EXPLAINABILITY (collapsible) ─────────────── */}
                    <div className="bg-neutral-900 border border-white/[0.04] rounded-xl p-4 space-y-3">
                      <div className="flex items-center justify-between">
                        <h3 className="text-[10px] font-bold text-neutral-400 uppercase tracking-wider flex items-center gap-1.5">
                          <BarChart2 size={13} className="text-teal-400" /> Feature Explainability + VLM Analysis
                        </h3>
                        <div className="flex items-center gap-2">
                          <button onClick={() => fetchExplain(selectedEvent.id)} disabled={explainLoading}
                            className="flex items-center gap-1.5 text-[10px] font-bold uppercase bg-teal-500/10 border border-teal-500/20 text-teal-300 hover:bg-teal-500/20 px-2.5 py-1.5 rounded-lg">
                            <Eye size={11} /> {explainLoading ? 'Loading...' : 'Explain'}
                          </button>
                          {explainData && (
                            <button onClick={() => fetchAnalyze(selectedEvent.id)} disabled={analyzeLoading}
                              className="flex items-center gap-1.5 text-[10px] font-bold uppercase bg-purple-500/10 border border-purple-500/20 text-purple-300 hover:bg-purple-500/20 px-2.5 py-1.5 rounded-lg">
                              <Bot size={11} /> {analyzeLoading ? 'Asking Qwen…' : 'VLM Analysis'}
                            </button>
                          )}
                          {explainData && (
                            <button onClick={() => setShowExplain(v => !v)} className="text-neutral-500 hover:text-white">
                              {showExplain ? <ChevronUp size={14}/> : <ChevronDown size={14}/>}
                            </button>
                          )}
                        </div>
                      </div>
                      {!explainData && !explainLoading && (
                        <p className="text-[10px] text-neutral-600">Click Explain to generate SHAP importance charts and Qwen3.5-0.8B visual analysis.</p>
                      )}
                      {showExplain && explainData && (
                        <div className="space-y-4">
                          {Object.entries(explainData).map(([name, pdata]: [string, any]) => (
                            <div key={name} className="space-y-1.5">
                              <div className="flex justify-between">
                                <span className="text-[10px] font-bold text-neutral-300 uppercase">{name}</span>
                                <span className="text-[10px] text-neutral-500 font-mono">{pdata.summary}</span>
                              </div>
                              {pdata.chart_png_b64 && (
                                <img src={`data:image/png;base64,${pdata.chart_png_b64}`} alt={`${name} feature importance`}
                                  className="w-full rounded-lg border border-white/[0.04]" />
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
                    </div>

                  </div>
                )}
              </div>
            </div>
          )}

          {/* ══ ARIA TAB ════════════════════════════════════════════════════ */}
          {activeTab === 'aria' && (
            <div className="flex-1 flex overflow-hidden">
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
                      No investigations yet. ARIA needs ≥3 events above 0.3 risk from the same user within 10 minutes.
                    </div>
                  )}
                  {ariaInvestigations.map(inv => (
                    <button key={inv.id} onClick={() => setSelectedInv(inv)}
                      className={`w-full text-left p-4 hover:bg-white/[0.02] flex flex-col gap-1.5 ${selectedInv?.id === inv.id ? 'bg-white/[0.02]' : ''}`}>
                      <div className="flex items-center justify-between">
                        <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full uppercase ${
                          inv.status==='open'?'bg-purple-500/20 text-purple-300':inv.status==='resolved'?'bg-teal-500/20 text-teal-400':'bg-neutral-700 text-neutral-400'
                        }`}>{inv.status}</span>
                        <span className="text-[9px] text-neutral-500 font-mono">conf {(inv.confidence*100).toFixed(0)}%</span>
                      </div>
                      <p className="text-xs text-neutral-200 font-medium leading-snug">{inv.hypothesis}</p>
                      <p className="text-[10px] text-neutral-500 font-mono">{inv.cluster_key} · {inv.event_count} events · cycle {inv.cycle}</p>
                    </button>
                  ))}
                </div>
              </div>
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
                        <button onClick={() => updateInvStatus(selectedInv.id, 'resolved')}
                          className="flex items-center gap-1 text-[10px] bg-teal-500/10 border border-teal-500/20 text-teal-400 hover:bg-teal-500/20 px-2.5 py-1.5 rounded-lg font-bold uppercase">
                          <CheckCircle2 size={11}/> Resolve
                        </button>
                        <button onClick={() => updateInvStatus(selectedInv.id, 'fp_confirmed')}
                          className="flex items-center gap-1 text-[10px] bg-neutral-700 border border-white/[0.06] text-neutral-400 hover:text-white px-2.5 py-1.5 rounded-lg font-bold uppercase">
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
                          <span className="text-2xl font-bold text-purple-300">{(selectedInv.confidence*100).toFixed(0)}%</span>
                        </div>
                        <div className="mt-2 h-1.5 bg-neutral-800 rounded-full overflow-hidden">
                          <div className="h-full bg-purple-500 rounded-full" style={{width:`${selectedInv.confidence*100}%`}}/>
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
                      <p className="text-[10px] text-neutral-500 uppercase font-bold">Related Events</p>
                      <div className="flex flex-wrap gap-2">
                        {(selectedInv.cluster_event_ids || []).map((id: number) => (
                          <button key={id} onClick={() => { setActiveTab('incident'); setSelectedEventId(id); }}
                            className="text-[10px] font-mono bg-neutral-800 hover:bg-neutral-700 text-neutral-300 px-2 py-1 rounded">
                            #{id}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-neutral-600 space-y-3">
                    <Bot size={40} className="opacity-30"/>
                    <p className="text-xs font-mono">Select an investigation to view ARIA analysis</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ══ SESSIONS TAB ════════════════════════════════════════════════ */}
          {activeTab === 'sessions' && (
            <div className="flex-1 overflow-y-auto p-8 space-y-6">
              <header className="pb-4 border-b border-white/[0.06] flex items-center justify-between">
                <div>
                  <h2 className="text-xl font-bold text-white flex items-center gap-2">
                    <Database size={20} className="text-teal-400" /> Session Monitor
                  </h2>
                  <p className="text-xs text-neutral-500 mt-1">
                    Live cryptographic session state — key versions, escalation levels, rotation history.
                  </p>
                </div>
                <button onClick={() => setRefreshTrigger(p => p+1)}
                  className="flex items-center gap-2 text-xs text-neutral-400 hover:text-white bg-neutral-900 border border-white/[0.06] hover:bg-neutral-800 px-3 py-1.5 rounded-lg">
                  <RefreshCw size={12}/> Refresh
                </button>
              </header>

              {/* Stats */}
              <div className="grid grid-cols-4 gap-4">
                {[
                  { label: 'Active Sessions',    value: sessions.filter(s=>s.is_active).length,                      color: 'text-white' },
                  { label: 'Escalated',           value: sessions.filter(s=>s.is_active&&s.risk_level>1).length,     color: 'text-amber-400' },
                  { label: 'Total Key Rotations', value: sessions.reduce((a,s)=>a+(s.key_version-1),0),             color: 'text-teal-400' },
                  { label: 'Contained',           value: sessions.filter(s=>s.risk_level>=4||!s.is_active).length,  color: 'text-red-400' },
                ].map(stat => (
                  <div key={stat.label} className="bg-neutral-900 border border-white/[0.04] rounded-xl p-4">
                    <p className="text-[10px] text-neutral-500 uppercase font-bold mb-1">{stat.label}</p>
                    <p className={`text-2xl font-bold ${stat.color}`}>{stat.value}</p>
                  </div>
                ))}
              </div>

              {/* Sessions table */}
              <div className="bg-neutral-900 border border-white/[0.06] rounded-xl overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-left">
                    <thead>
                      <tr className="border-b border-white/[0.06] bg-neutral-950 text-[10px] font-bold text-neutral-400 uppercase tracking-wider">
                        <th className="px-5 py-3">User / Session</th>
                        <th className="px-5 py-3">Risk Level</th>
                        <th className="px-5 py-3">Key Version</th>
                        <th className="px-5 py-3">AES Key (masked)</th>
                        <th className="px-5 py-3">Updated</th>
                        <th className="px-5 py-3">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-white/[0.04] text-xs">
                      {sessions.length === 0 ? (
                        <tr><td colSpan={6} className="text-center py-8 text-neutral-500 font-mono text-xs">No sessions yet. Login to the Customer Portal to create one.</td></tr>
                      ) : sessions.map(s => {
                        const riskLabels = ['','L1: ALLOW','L2: CHALLENGE','L3: RESTRICT','L4: CONTAIN'];
                        const riskColors = ['','bg-emerald-500/10 text-emerald-400 border-emerald-500/20','bg-amber-500/10 text-amber-400 border-amber-500/20','bg-orange-500/10 text-orange-400 border-orange-500/20','bg-red-500/10 text-red-400 border-red-500/20'];
                        const isFlashing = s.session_id === flashingSessionId;
                        return (
                          <tr key={s.session_id}
                            className={`transition-all border-l-2 ${isFlashing?'bg-purple-950/30 border-purple-500 animate-pulse':'hover:bg-white/[0.01] border-transparent'}`}>
                            <td className="px-5 py-3.5">
                              <div className="font-semibold text-white flex items-center gap-2">
                                {s.user_id}
                                {isFlashing && <span className="text-[8px] bg-purple-500/20 text-purple-300 font-bold px-1.5 py-0.5 rounded uppercase animate-bounce">KEY ROTATED</span>}
                              </div>
                              <div className="text-[10px] text-neutral-500 font-mono mt-0.5">{s.session_id}</div>
                            </td>
                            <td className="px-5 py-3.5">
                              <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase border ${riskColors[s.risk_level]||riskColors[1]}`}>
                                {riskLabels[s.risk_level]||riskLabels[1]}
                              </span>
                            </td>
                            <td className={`px-5 py-3.5 font-mono font-bold transition-all ${isFlashing?'text-purple-400 text-sm':'text-teal-400'}`}>
                              v{s.key_version}
                            </td>
                            <td className="px-5 py-3.5 font-mono text-neutral-400 text-[10px]">{s.aes_key}</td>
                            <td className="px-5 py-3.5 font-mono text-neutral-500 text-[10px]">{new Date(s.updated_at).toLocaleTimeString()}</td>
                            <td className="px-5 py-3.5">
                              {s.is_active && s.risk_level < 4 ? (
                                <span className="flex items-center gap-1.5 text-emerald-400 font-semibold text-[10px] uppercase">
                                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"/>Active
                                </span>
                              ) : (
                                <span className="flex items-center gap-1.5 text-neutral-500 font-semibold text-[10px] uppercase">
                                  <span className="w-1.5 h-1.5 rounded-full bg-neutral-600"/>Locked
                                </span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          )}

          {/* ══ SETTINGS TAB ════════════════════════════════════════════════ */}
          {activeTab === 'settings' && (
            <div className="flex-1 overflow-y-auto p-8 space-y-6">
              <header className="pb-4 border-b border-white/[0.06]">
                <h2 className="text-xl font-bold text-white flex items-center gap-2">
                  <Sliders size={20} className="text-teal-400" /> Risk Policy Configuration
                </h2>
                <p className="text-xs text-neutral-500 mt-1">
                  Fine-tune escalation thresholds, transfer limits, and provider weights live during operation.
                </p>
              </header>
              {configLoading && (
                <div className="h-48 flex items-center justify-center text-teal-400 gap-2 font-mono text-xs">
                  <RefreshCw size={16} className="animate-spin"/> Loading configuration...
                </div>
              )}
              {config && !configLoading && (
                <form onSubmit={saveConfig} className="max-w-4xl space-y-6">
                  <div className="bg-neutral-900 border border-white/[0.06] rounded-xl p-6 space-y-4">
                    <h3 className="text-xs font-bold text-neutral-400 uppercase tracking-wider flex items-center gap-1.5">
                      <ShieldAlert size={14} className="text-amber-400"/> Policy Escalation Thresholds
                    </h3>
                    <div className="grid grid-cols-3 gap-4">
                      {[
                        ['threshold_challenge', 'Challenge (L2)'],
                        ['threshold_restrict',  'Restrict (L3)'],
                        ['threshold_contain',   'Contain (L4)'],
                      ].map(([key, label]) => (
                        <div key={key} className="space-y-1.5">
                          <label className="text-[10px] font-bold text-neutral-500 uppercase tracking-wide">{label}</label>
                          <input type="number" step="0.05" min="0" max="1" value={config[key]}
                            onChange={e => setConfig({...config, [key]: parseFloat(e.target.value)||0})}
                            className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg px-4 py-2 text-xs text-white focus:outline-none focus:border-teal-500/40" />
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="bg-neutral-900 border border-white/[0.06] rounded-xl p-6 space-y-4">
                    <h3 className="text-xs font-bold text-neutral-400 uppercase tracking-wider flex items-center gap-1.5">
                      <Database size={14} className="text-teal-400"/> Operational Parameters
                    </h3>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1.5">
                        <label className="text-[10px] font-bold text-neutral-500 uppercase tracking-wide">Max Transfer Limit ($)</label>
                        <input type="number" min="1" value={config.max_transfer_limit}
                          onChange={e => setConfig({...config, max_transfer_limit: parseInt(e.target.value)||0})}
                          className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg px-4 py-2 text-xs text-white focus:outline-none focus:border-teal-500/40" />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-[10px] font-bold text-neutral-500 uppercase tracking-wide">Trust Recovery Factor</label>
                        <input type="number" step="0.1" min="0.1" max="10" value={config.trust_recovery_speed}
                          onChange={e => setConfig({...config, trust_recovery_speed: parseFloat(e.target.value)||0})}
                          className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg px-4 py-2 text-xs text-white focus:outline-none focus:border-teal-500/40" />
                      </div>
                    </div>
                  </div>
                  <div className="bg-neutral-900 border border-white/[0.06] rounded-xl p-6 space-y-4">
                    <h3 className="text-xs font-bold text-neutral-400 uppercase tracking-wider flex items-center gap-1.5">
                      <Cpu size={14} className="text-purple-400"/> Provider Ensemble Weights
                    </h3>
                    <div className="grid grid-cols-2 gap-4">
                      {Object.keys(config.weights || {}).map(provider => (
                        <div key={provider} className="space-y-1.5">
                          <div className="flex justify-between">
                            <span className="text-[10px] font-bold text-neutral-400 uppercase">{provider.replace('RiskProvider','').replace('Provider','').replace('Risk','')}</span>
                            <span className="text-xs font-mono font-bold text-purple-300">{((config.weights[provider]||0)*100).toFixed(0)}%</span>
                          </div>
                          <input type="range" min="0" max="1" step="0.05" value={config.weights[provider]||0}
                            onChange={e => setConfig({...config, weights:{...config.weights,[provider]:parseFloat(e.target.value)}})}
                            className="w-full accent-purple-500" />
                        </div>
                      ))}
                    </div>
                  </div>
                  <button type="submit" disabled={configSaving}
                    className="w-full py-3 bg-teal-600 hover:bg-teal-500 text-white font-bold text-xs rounded-lg uppercase tracking-wider flex items-center justify-center gap-2 transition-colors disabled:opacity-40">
                    {configSaving ? <RefreshCw size={13} className="animate-spin"/> : null}
                    Save Configuration
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
