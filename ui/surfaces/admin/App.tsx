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

// Provider display metadata — no emoji, short label only
const PROVIDER_META: Record<string, { short: string }> = {
  BeaconBehavioralProvider:       { short: 'BEACON'      },
  AccountTakeoverProvider:        { short: 'ATO'         },
  TransactionRiskProvider:        { short: 'Transaction' },
  NetworkRiskProvider:            { short: 'Network'     },
  DeviceTrustProvider:            { short: 'Device'      },
  SocialEngineeringRiskProvider:  { short: 'Social'      },
  PhishingRiskProvider:           { short: 'Phishing'    },
};

const CUSTOMER_MSG: Record<number, { label: string; color: string; dot: string }> = {
  1: { label: 'Protected — Banking normally',       color: 'text-emerald-700 font-bold', dot: 'bg-emerald-500' },
  2: { label: 'OTP verification required',          color: 'text-amber-700 font-bold',   dot: 'bg-amber-500'  },
  3: { label: 'Sensitive operations restricted',    color: 'text-orange-700 font-bold',  dot: 'bg-orange-500' },
  4: { label: 'Session secured — forced re-login',  color: 'text-red-700 font-bold',     dot: 'bg-red-500'    },
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

  // Live session monitoring
  const [liveSessionId, setLiveSessionId] = useState<string | null>(null);
  const [liveData, setLiveData] = useState<any>(null);
  const [sessionTimeline, setSessionTimeline] = useState<any[]>([]);

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

  // Live session polling — 2s interval when a session is selected in Sessions tab
  useEffect(() => {
    if (!isAuthenticated || !liveSessionId) { setSessionTimeline([]); return; }
    async function fetchLive() {
      try {
        const [live, tl] = await Promise.all([
          axios.get(`${API_BASE}/admin/sessions/${liveSessionId}/live`),
          axios.get(`${API_BASE}/admin/sessions/${liveSessionId}/timeline`),
        ]);
        setLiveData(live.data);
        setSessionTimeline(tl.data);
      } catch (err) { /* session may have ended */ }
    }
    fetchLive();
    const iv = setInterval(fetchLive, 2000);
    return () => clearInterval(iv);
  }, [isAuthenticated, liveSessionId]);

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
    { name: 'MONITOR',   color: 'text-emerald-700 border-emerald-200 bg-emerald-50', icon: ShieldCheck },
    { name: 'CHALLENGE', color: 'text-amber-700   border-amber-200   bg-amber-50',   icon: AlertCircle },
    { name: 'RESTRICT',  color: 'text-orange-700  border-orange-200  bg-orange-50',  icon: ShieldAlert },
    { name: 'CONTAIN',   color: 'text-red-700     border-red-200     bg-red-50',     icon: Skull       },
  ];

  // ── LOGIN ─────────────────────────────────────────────────────────────────
  if (!isAuthenticated) {
    return (
      <div className="flex min-h-screen bg-slate-50 text-slate-800 font-sans items-center justify-center p-6">
        <div className="max-w-md w-full bg-white border border-slate-200 rounded-xl p-8 shadow-xl space-y-6">
          <div className="flex flex-col items-center space-y-2">
            <div className="w-12 h-12 rounded-xl bg-slate-100 border border-slate-200 text-slate-700 grid place-items-center mb-1">
              <Brain size={24} />
            </div>
            <h1 className="text-xl font-bold tracking-tight text-slate-900">AURA Security Operations</h1>
            <p className="text-sm text-slate-500 text-center font-medium">Fraud Intelligence &amp; Behavioral AI Console</p>
          </div>
          <form onSubmit={handleLogin} className="space-y-4">
            {error && <div className="p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">{error}</div>}
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Admin ID</label>
              <input type="text" placeholder="admin" value={username} onChange={e => setUsername(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 focus:outline-none focus:border-slate-400 font-sans" />
            </div>
            <div className="space-y-1.5">
              <label className="text-xs font-bold text-slate-500 uppercase tracking-wider">Password</label>
              <input type="password" placeholder="••••••••" value={password} onChange={e => setPassword(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 focus:outline-none focus:border-slate-400 font-sans" />
            </div>
            <button type="submit" disabled={loading}
              className="w-full py-2.5 bg-slate-900 hover:bg-slate-800 text-white font-bold text-sm rounded-lg transition-colors uppercase tracking-wider">
              {loading ? 'Verifying...' : 'Sign In To Dashboard'}
            </button>
          </form>
        </div>
      </div>
    );
  }

  // ── PIPELINE HELPER ───────────────────────────────────────────────────────
  const PipelineStage = ({ label, value, sub, active, color = 'neutral' }: any) => {
    const activeStyles: Record<string, string> = {
      neutral: 'border-slate-200 bg-slate-50 text-slate-600',
      teal:    'border-emerald-200 bg-emerald-50 text-emerald-700',
      amber:   'border-amber-200   bg-amber-50   text-amber-700',
      orange:  'border-orange-200  bg-orange-50  text-orange-700',
      red:     'border-red-200     bg-red-50     text-red-700',
      blue:    'border-blue-200    bg-blue-50    text-blue-700',
    };
    const valueCls: Record<string, string> = {
      neutral: 'text-slate-700', teal: 'text-emerald-700', amber: 'text-amber-700',
      orange: 'text-orange-700', red: 'text-red-700', blue: 'text-blue-700',
    };
    return (
      <div className={`flex-1 min-w-0 rounded-lg border py-3 px-4 text-center transition-all ${active ? activeStyles[color] || activeStyles.neutral : 'border-slate-100 bg-slate-50'}`}>
        <div className={`text-xs font-bold uppercase tracking-wider ${active ? (valueCls[color] || 'text-slate-500') : 'text-slate-400'}`}>{label}</div>
        <div className={`text-sm font-bold font-mono mt-0.5 truncate ${active ? (valueCls[color] || 'text-slate-700') : 'text-slate-400'}`}>{value}</div>
        {sub && <div className="text-xs text-slate-400 mt-0.5 truncate">{sub}</div>}
      </div>
    );
  };

  // ── PROVIDER ROW ──────────────────────────────────────────────────────────
  const ProviderRow = ({ name, data, weight }: any) => {
    const meta = PROVIDER_META[name] || { short: name.replace('Provider','').replace('Risk','') };
    const score = Math.round((data?.risk_score || 0) * 100);
    const triggered = score >= 60;
    const elevated = score >= 30 && score < 60;
    const barColor = score >= 60 ? 'bg-red-500' : score >= 30 ? 'bg-amber-400' : 'bg-emerald-500';
    const scoreColor = score >= 60 ? 'text-red-700' : score >= 30 ? 'text-amber-700' : 'text-emerald-700';
    const statusLabel = triggered ? 'TRIGGERED' : elevated ? 'elevated' : 'normal';
    const statusCls = triggered
      ? 'bg-red-50 text-red-700 border border-red-200'
      : elevated
        ? 'bg-amber-50 text-amber-700 border border-amber-200'
        : 'bg-emerald-50 text-emerald-700 border border-emerald-200';
    return (
      <div className="border-t border-slate-100 py-3 flex items-center gap-4">
        <span className="w-32 text-sm font-semibold text-slate-700 shrink-0">{meta.short}</span>
        <div className="flex-1 h-2 bg-slate-100 rounded-full overflow-hidden">
          <div className={`h-full rounded-full transition-all duration-500 ${barColor}`} style={{ width: `${score}%` }} />
        </div>
        <span className={`w-12 text-sm font-bold font-mono text-right ${scoreColor}`}>{score}%</span>
        <span className={`text-xs font-bold px-2 py-0.5 rounded uppercase ${statusCls}`}>{statusLabel}</span>
        {weight !== undefined && <span className="text-xs text-slate-400 font-mono w-16 text-right">w={Math.round(weight*100)}%</span>}
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
    <div className="flex h-screen bg-slate-50 text-slate-800 font-sans flex-col">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white px-6 py-3.5 flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-3">
          <div className="w-8 h-8 rounded-lg bg-slate-100 border border-slate-200 grid place-items-center">
            <Brain size={16} className="text-slate-700" />
          </div>
          <div>
            <h1 className="font-bold text-sm leading-tight text-slate-900">{t('header_title')}</h1>
            <p className="text-xs text-slate-400 font-semibold uppercase tracking-widest">{t('header_sub')}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs text-emerald-600 font-mono">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
            <span>LIVE · SQLite Active</span>
          </div>
          <button onClick={() => setRefreshTrigger(p => p+1)} className="p-2 text-slate-400 hover:text-slate-800 rounded-lg hover:bg-slate-100">
            <RefreshCw size={14} />
          </button>
          <div className="flex bg-slate-100 border border-slate-200 rounded-lg p-1 text-xs font-bold">
            <button onClick={() => pref.setLang('en')} className={`px-2 py-0.5 rounded ${pref.lang==='en'?'bg-slate-800 text-white':'text-slate-500 hover:text-slate-800'}`}>EN</button>
            <button onClick={() => pref.setLang('hi')} className={`px-2 py-0.5 rounded ${pref.lang==='hi'?'bg-slate-800 text-white':'text-slate-500 hover:text-slate-800'}`}>HI</button>
          </div>
          <button onClick={handleLogout} className="flex items-center gap-1.5 bg-slate-100 border border-slate-200 hover:bg-slate-200 text-slate-600 hover:text-slate-800 px-3 py-1.5 rounded-lg text-sm font-semibold">
            <LogOut size={13} /> {t('logout')}
          </button>
        </div>
      </header>

      {/* Critical alert banner */}
      {criticalAlert && (
        <div className="bg-red-50 border-b-2 border-red-500 p-3 flex items-center justify-between gap-4 shrink-0 text-red-800 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="p-1.5 bg-red-100 rounded-full border border-red-200 text-red-700 animate-bounce">
              <ShieldAlert size={16} />
            </div>
            <div className="text-left font-mono">
              <div className="text-red-700 font-bold uppercase tracking-widest text-xs flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-ping" /> CRITICAL — SESSION CONTAINED
              </div>
              <div className="text-slate-800 mt-0.5 text-sm font-sans">
                User <span className="text-red-700 font-semibold">{criticalAlert.user_id}</span> · Session revoked · Behavioral drift exceeded threshold
              </div>
            </div>
          </div>
          <div className="flex items-center gap-4 font-mono text-xs">
            <div><span className="text-slate-500">Key:</span> <span className="text-red-600 font-bold">kv{criticalAlert.key_version} (REVOKED)</span></div>
            <div><span className="text-slate-500">Policy:</span> <span className="text-red-600 font-bold">LEVEL 4 CONTAIN</span></div>
          </div>
          <button onClick={() => setCriticalAlert(null)} className="bg-red-700 hover:bg-red-800 text-white font-bold px-3 py-1.5 rounded-lg text-xs uppercase transition-colors">
            Acknowledge
          </button>
        </div>
      )}

      {/* Main layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar — 4 tabs */}
        <aside className="w-56 border-r border-slate-200 bg-white flex flex-col shrink-0 p-3 space-y-1">
          {([
            ['incident', t('tab_incident'),  Activity],
            ['aria',     t('tab_aria'),      Bot],
            ['sessions', t('tab_sessions'),  Database],
            ['settings', t('tab_settings'),  Sliders],
          ] as [string, string, any][]).map(([tab, label, Icon]) => {
            const isTabActive = activeTab === tab;
            const activeBg = tab === 'aria' ? 'bg-blue-50 text-blue-700' : 'bg-slate-100 text-slate-800';
            return (
              <button key={tab} onClick={() => setActiveTab(tab as any)}
                className={`w-full flex items-center gap-2.5 px-3 py-2.5 text-sm font-medium rounded-lg transition-colors ${
                  isTabActive ? `${activeBg} font-bold` : 'text-slate-600 hover:text-slate-900 hover:bg-slate-50'
                }`}
              >
                <Icon size={15} />
                <span className="flex-1 text-left">{label}</span>
                {tab === 'aria' && ariaInvestigations.filter(i => i.status === 'open').length > 0 && (
                  <span className="bg-blue-100 text-blue-700 text-xs font-bold px-1.5 py-0.5 rounded-full">
                    {ariaInvestigations.filter(i => i.status === 'open').length}
                  </span>
                )}
                {tab === 'sessions' && sessions.filter(s => s.is_active && s.risk_level > 1).length > 0 && (
                  <span className="bg-amber-100 text-amber-800 text-xs font-bold px-1.5 py-0.5 rounded-full">
                    {sessions.filter(s => s.is_active && s.risk_level > 1).length}
                  </span>
                )}
              </button>
            );
          })}
        </aside>

        {/* Content */}
        <main className="flex-1 overflow-hidden bg-slate-50 flex flex-col">

          {/* ══ INCIDENT CONSOLE ═══════════════════════════════════════════ */}
          {activeTab === 'incident' && (
            <div className="flex-1 flex overflow-hidden">
              {/* Left: event list — 250px */}
              <div className="w-64 border-r border-slate-200 bg-white flex flex-col shrink-0">
                <div className="p-3 border-b border-slate-200 space-y-2">
                  <div className="flex items-center gap-2">
                    <div className="flex items-center gap-1.5 text-xs text-emerald-600 font-mono font-bold">
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" /> LIVE · 6s
                    </div>
                    <span className="ml-auto text-xs text-slate-500 font-mono">{events.length} events</span>
                  </div>
                  <div className="relative">
                    <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-400" />
                    <input type="text" placeholder="Filter by user..." value={searchUserId}
                      onChange={e => setSearchUserId(e.target.value)}
                      className="w-full bg-slate-50 border border-slate-200 rounded-lg pl-7 pr-3 py-1.5 text-sm text-slate-800 focus:outline-none focus:border-slate-400 font-sans" />
                  </div>
                </div>
                <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
                  {events.map(e => {
                    const lvl = levels[(e.level || 1) - 1] || levels[0];
                    const isNew = (now - new Date(e.timestamp).getTime()) < 60000;
                    const isSelected = selectedEventId === e.id;
                    // derive left border color from risk level
                    const borderAccent = e.level >= 4 ? 'border-red-500' : e.level >= 3 ? 'border-orange-400' : e.level >= 2 ? 'border-amber-400' : 'border-emerald-400';
                    return (
                      <button key={e.id} onClick={() => setSelectedEventId(e.id)}
                        className={`w-full text-left p-3 hover:bg-slate-50 transition-colors border-l-4 ${
                          isSelected ? `bg-slate-100 ${borderAccent}` : 'border-transparent'
                        }`}
                      >
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-semibold text-slate-900 truncate max-w-[120px]">{e.user_id}</span>
                          <div className="flex items-center gap-1">
                            {isNew && <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />}
                            <span className="text-xs text-slate-500 font-mono">{new Date(e.timestamp).toLocaleTimeString()}</span>
                          </div>
                        </div>
                        <div className="flex items-center justify-between mb-1">
                          <span className={`text-xs font-bold px-2 py-1 rounded border uppercase ${lvl.color}`}>{lvl.name}</span>
                          <span className="text-sm font-mono font-bold text-slate-800">{Math.round((e.overall_risk||0)*100)}<span className="text-slate-400 text-xs">/100</span></span>
                        </div>
                        <p className="text-xs text-slate-500 truncate">{e.why_decision}</p>
                      </button>
                    );
                  })}
                  {events.length === 0 && (
                    <div className="p-6 text-center text-sm text-slate-400 font-mono">
                      No incidents yet. Run an attack scenario to populate.
                    </div>
                  )}
                </div>
              </div>

              {/* Right: incident investigation */}
              <div className="flex-1 overflow-y-auto">
                {!selectedEvent ? (
                  <div className="h-full flex flex-col items-center justify-center text-slate-400 space-y-3">
                    <Activity size={40} className="opacity-30" />
                    <p className="text-sm font-mono">Select an incident to begin investigation</p>
                  </div>
                ) : (
                  <div className="p-6 space-y-5 max-w-none">

                    {/* ── 1. BIG IDENTITY HEADER ──────────────────────── */}
                    {(() => {
                      const lvl = levels[(selectedEvent.level||1)-1] || levels[0];
                      const LvlIcon = lvl.icon;
                      // left border color
                      const borderAccent = selectedEvent.level >= 4 ? 'border-red-500' : selectedEvent.level >= 3 ? 'border-orange-400' : selectedEvent.level >= 2 ? 'border-amber-400' : 'border-emerald-500';
                      const riskScoreColor = selectedEvent.overall_risk>=0.7?'text-red-700':selectedEvent.overall_risk>=0.4?'text-orange-700':selectedEvent.overall_risk>=0.2?'text-amber-700':'text-emerald-700';
                      return (
                        <div className={`bg-white border border-slate-200 rounded-xl border-l-4 ${borderAccent} flex items-start justify-between px-6 py-4 shadow-sm`}>
                          <div className="flex items-start gap-5">
                            <div className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border ${lvl.color} shrink-0 mt-1`}>
                              <LvlIcon size={16} />
                              <span className="text-base font-bold uppercase">{lvl.name}</span>
                            </div>
                            <div>
                              <div className="text-3xl font-bold text-slate-900 leading-tight">{selectedEvent.user_id}</div>
                              <div className="text-xs text-slate-400 font-mono mt-1">{selectedEvent.session_id}</div>
                              <div className="text-xs text-slate-500 mt-1">
                                {new Date(selectedEvent.timestamp).toLocaleString()} · {selectedEvent.event_category || 'behavioral'}
                              </div>
                            </div>
                          </div>
                          <div className="flex items-start gap-8 text-right">
                            <div className="max-w-xs">
                              <div className="text-xs font-semibold text-slate-400 uppercase tracking-widest mb-1">Decision Reason</div>
                              <p className="text-sm text-slate-700 leading-snug text-left">{selectedEvent.why_decision}</p>
                            </div>
                            <div>
                              <div className="text-xs text-slate-400 uppercase tracking-widest mb-1">Risk Score</div>
                              <div className={`text-5xl font-bold font-mono leading-none ${riskScoreColor}`}>
                                {Math.round(selectedEvent.overall_risk*100)}
                              </div>
                              <div className="text-xs text-slate-400 mt-1">/100</div>
                              <div className="text-xl font-bold text-slate-600 mt-1">{Math.round(selectedEvent.confidence*100)}%</div>
                              <div className="text-xs text-slate-400">confidence</div>
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
                        <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                          <div className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-1.5">
                            <Zap size={12} className="text-slate-400" /> Decision Pipeline — Telemetry to Customer
                          </div>
                          <div className="flex items-stretch gap-1">
                            <PipelineStage label="Telemetry" value={telCount>0?`${telCount} events`:'collecting'} active={telCount>0} color="teal" />
                            <div className="flex items-center text-slate-300 text-sm font-bold px-0.5">›</div>
                            <PipelineStage label="Features" value={featCount>0?`${featCount} extracted`:'—'} active={featCount>0} color="teal" />
                            <div className="flex items-center text-slate-300 text-sm font-bold px-0.5">›</div>
                            <PipelineStage label="Models" value={`${provCount} providers`} sub="ensemble" active={provCount>0} color="teal" />
                            <div className="flex items-center text-slate-300 text-sm font-bold px-0.5">›</div>
                            <PipelineStage label="BEACON" value={beaconVal} sub="cosine sim" active={sim!=null||telCount>0} color={beaconColor as any} />
                            <div className="flex items-center text-slate-300 text-sm font-bold px-0.5">›</div>
                            <PipelineStage label="Fusion" value={fusionVal} sub="weighted avg" active color={fusionColor as any} />
                            <div className="flex items-center text-slate-300 text-sm font-bold px-0.5">›</div>
                            <PipelineStage label="Policy" value={selectedEvent.decision} sub={`Level ${selectedEvent.level}`} active color={policyColor as any} />
                            <div className="flex items-center text-slate-300 text-sm font-bold px-0.5">›</div>
                            <PipelineStage label="Crypto" value={`kv${cryptoKv}`} sub={matchedSession?.is_active===false?'revoked':'active'} active color={cryptoColor as any} />
                            <div className="flex items-center text-slate-300 text-sm font-bold px-0.5">›</div>
                            <PipelineStage label="Customer" value={custMsg.label.split('—')[0].trim()} sub={custMsg.label.includes('—')?custMsg.label.split('—')[1].trim():undefined} active color={custColor as any} />
                          </div>
                        </div>
                      );
                    })()}

                    {/* ── 3. AI REASONING ─────────────────────────────── */}
                    <div className="border-t border-slate-200 pt-4 mt-4">
                      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-1.5">
                        <Brain size={13} className="text-slate-400" /> AI Decision Reasoning
                        <span className="ml-auto text-xs text-slate-400 font-mono italic normal-case">{selectedEvent.recommendation}</span>
                      </h3>
                      <p className="text-sm text-slate-700 leading-relaxed">{selectedEvent.why_decision}</p>
                    </div>

                    {/* ── 4. TWO COLUMNS: PROVIDERS + EVIDENCE ───────── */}
                    <div className="grid grid-cols-5 gap-5">
                      {/* Provider rows — 3 cols */}
                      <div className="col-span-3">
                        <div className="border-t border-slate-200 pt-4">
                          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-1.5">
                            <Cpu size={12} className="text-slate-400" /> ML Provider Scores · {Object.keys(selectedEvent.breakdown||{}).length} models
                          </h3>
                          <div className="bg-white border border-slate-200 rounded-xl px-4 pb-2 shadow-sm">
                            {Object.entries(selectedEvent.breakdown || {}).map(([name, data]: [string, any]) => (
                              <ProviderRow key={name} name={name} data={data} weight={config?.weights?.[name]} />
                            ))}
                            {Object.keys(selectedEvent.breakdown || {}).length === 0 && (
                              <div className="text-center text-sm text-slate-400 py-8 border border-dashed border-slate-200 rounded-xl m-2">
                                No provider breakdown available for this event.
                              </div>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Evidence charts — 2 cols */}
                      <div className="col-span-2">
                        <div className="border-t border-slate-200 pt-4">
                          <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3 flex items-center gap-1.5">
                            <BarChart2 size={12} className="text-slate-400" /> Behavioral Evidence
                          </h3>
                          <div className="space-y-3">
                            {/* VarCNN IET */}
                            <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-sm">
                              <div className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-2">
                                Keystroke Timing · VarCNN Input (IET ms)
                                <span className="ml-1 text-slate-400 normal-case font-normal">LIVE</span>
                              </div>
                              <div className="h-28">
                                {selectedEvent.visuals?.sequence ? (
                                  <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={selectedEvent.visuals.sequence} margin={{top:0,right:0,left:-20,bottom:0}}>
                                      <XAxis dataKey="index" stroke="#94a3b8" fontSize={11} tickLine={false} />
                                      <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} />
                                      <Tooltip contentStyle={{background:'#fff',border:'1px solid #cbd5e1',fontSize:11,color:'#334155'}} />
                                      <Bar dataKey="iet" fill="#0284c7" radius={[1,1,0,0]} maxBarSize={8} />
                                    </BarChart>
                                  </ResponsiveContainer>
                                ) : (
                                  <div className="h-full flex items-center justify-center text-sm text-slate-500 font-mono text-center px-2">
                                    {(selectedEvent.visuals?.model_internals?.sequence_length||0) < 3
                                      ? 'Warmup: collecting telemetry (< 3 events)'
                                      : 'Insufficient events for IET sequence'}
                                  </div>
                                )}
                              </div>
                            </div>

                            {/* SHAP */}
                            <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-sm">
                              <div className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-2">
                                Feature Attribution · SHAP Impact
                                <span className="ml-1 text-slate-400 normal-case font-normal">DERIVED</span>
                              </div>
                              <div className="h-28">
                                {selectedEvent.visuals?.shap_attribution ? (
                                  <ResponsiveContainer width="100%" height="100%">
                                    <BarChart layout="vertical" data={selectedEvent.visuals.shap_attribution} margin={{top:0,right:10,left:0,bottom:0}}>
                                      <XAxis type="number" stroke="#94a3b8" fontSize={11} tickLine={false} />
                                      <YAxis type="category" dataKey="feature" stroke="#94a3b8" fontSize={11} width={80} tickLine={false} />
                                      <Tooltip contentStyle={{background:'#fff',border:'1px solid #cbd5e1',fontSize:11,color:'#334155'}} />
                                      <Bar dataKey="impact" fill="#64748b" radius={[0,2,2,0]} />
                                    </BarChart>
                                  </ResponsiveContainer>
                                ) : (
                                  <div className="h-full flex items-center justify-center text-sm text-slate-400 font-mono text-center px-2">
                                    SHAP unavailable — insufficient telemetry events
                                  </div>
                                )}
                              </div>
                            </div>

                            {/* Risk history */}
                            <div className="bg-white border border-slate-200 rounded-xl p-3 shadow-sm">
                              <div className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-2">
                                Session Risk Evolution
                                <span className="ml-1 text-slate-400 normal-case font-normal">LIVE</span>
                              </div>
                              <div className="h-28">
                                {selectedEvent.visuals?.temporal_confidence?.length > 0 ? (
                                  <ResponsiveContainer width="100%" height="100%">
                                    <LineChart data={selectedEvent.visuals.temporal_confidence} margin={{top:4,right:4,left:-20,bottom:0}}>
                                      <XAxis dataKey="batch" stroke="#94a3b8" fontSize={11} tickLine={false} />
                                      <YAxis stroke="#94a3b8" fontSize={11} tickLine={false} domain={[0,100]} />
                                      <Tooltip contentStyle={{background:'#fff',border:'1px solid #cbd5e1',fontSize:11,color:'#334155'}} />
                                      <Line type="monotone" dataKey="risk" stroke="#e11d48" strokeWidth={2} dot={false} name="Risk" />
                                      <Line type="monotone" dataKey="confidence" stroke="#0284c7" strokeWidth={1.5} dot={false} name="Confidence" strokeDasharray="4 2" />
                                    </LineChart>
                                  </ResponsiveContainer>
                                ) : (
                                  <div className="h-full flex items-center justify-center text-sm text-slate-400 font-mono">No history yet</div>
                                )}
                              </div>
                            </div>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* ── 5. OUTCOME STRIP ────────────────────────────── */}
                    <div className="border-t border-slate-200 pt-4 mt-4">
                      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-3">Outcome</h3>
                      <div className="grid grid-cols-3 gap-4">
                        {/* Crypto action */}
                        <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-2 shadow-sm">
                          <div className="flex items-center gap-2">
                            <Key size={13} className="text-slate-400" />
                            <span className="text-xs font-semibold text-slate-500 uppercase tracking-widest">Cryptographic Action</span>
                          </div>
                          {matchedSession ? (
                            <>
                              <div className="font-mono text-2xl font-bold text-slate-800">kv{matchedSession.key_version}</div>
                              <div className="text-sm text-slate-500">
                                {matchedSession.key_version > 1 ? `Key rotated ${matchedSession.key_version - 1}×` : 'No rotation (Level 1)'}
                                {!matchedSession.is_active && ' · Session revoked & purged'}
                              </div>
                              <div className="text-xs text-slate-400 font-mono">{new Date(matchedSession.updated_at).toLocaleTimeString()}</div>
                            </>
                          ) : (
                            <div className="text-sm text-slate-400">Session not in monitor scope</div>
                          )}
                        </div>

                        {/* Customer impact */}
                        <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-2 shadow-sm">
                          <div className="flex items-center gap-2">
                            <User size={13} className="text-slate-400" />
                            <span className="text-xs font-semibold text-slate-500 uppercase tracking-widest">Customer Impact</span>
                          </div>
                          {(() => {
                            const cm = CUSTOMER_MSG[selectedEvent.level] || CUSTOMER_MSG[1];
                            return (
                              <>
                                <div className="flex items-center gap-2">
                                  <span className={`w-2 h-2 rounded-full ${cm.dot}`} />
                                  <span className={`text-sm font-bold ${cm.color}`}>{cm.label}</span>
                                </div>
                                <div className="text-sm text-slate-500 leading-snug">
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
                        <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-2 shadow-sm">
                          <div className="flex items-center gap-2">
                            <Bot size={13} className="text-blue-600" />
                            <span className="text-xs font-semibold text-slate-500 uppercase tracking-widest">ARIA Autonomous Agent</span>
                          </div>
                          {relatedAria.length > 0 ? (
                            <>
                              <div className="text-sm font-bold text-slate-800">{relatedAria[0].hypothesis}</div>
                              <div className="text-sm text-slate-500">Investigation #{relatedAria[0].id} · {relatedAria[0].event_count} events · {Math.round(relatedAria[0].confidence*100)}% confidence</div>
                              <button onClick={() => setActiveTab('aria')}
                                className="text-xs text-blue-600 hover:text-blue-700 font-bold uppercase tracking-wider flex items-center gap-1">
                                View Investigation <ArrowRight size={10} />
                              </button>
                            </>
                          ) : (
                            <div className="text-sm text-slate-400">
                              No autonomous investigation triggered yet.
                              <br /><span className="text-xs">ARIA needs ≥3 events at risk ≥0.3 within 10 min.</span>
                            </div>
                          )}
                        </div>
                      </div>
                    </div>

                    {/* ── 6. EXPLAINABILITY (collapsible) ─────────────── */}
                    <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-3 shadow-sm">
                      <div className="flex items-center justify-between">
                        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-widest flex items-center gap-1.5">
                          <BarChart2 size={13} className="text-slate-400" /> Feature Explainability + VLM Analysis
                        </h3>
                        <div className="flex items-center gap-2">
                          <button onClick={() => fetchExplain(selectedEvent.id)} disabled={explainLoading}
                            className="flex items-center gap-1.5 text-xs font-bold uppercase bg-slate-100 border border-slate-200 text-slate-700 hover:bg-slate-200 px-2.5 py-1.5 rounded-lg">
                            <Eye size={11} /> {explainLoading ? 'Loading...' : 'Explain'}
                          </button>
                          {explainData && (
                            <button onClick={() => fetchAnalyze(selectedEvent.id)} disabled={analyzeLoading}
                              className="flex items-center gap-1.5 text-xs font-bold uppercase bg-blue-50 border border-blue-200 text-blue-700 hover:bg-blue-100 px-2.5 py-1.5 rounded-lg">
                              <Bot size={11} /> {analyzeLoading ? 'Asking Qwen…' : 'VLM Analysis'}
                            </button>
                          )}
                          {explainData && (
                            <button onClick={() => setShowExplain(v => !v)} className="text-slate-400 hover:text-slate-700">
                              {showExplain ? <ChevronUp size={14}/> : <ChevronDown size={14}/>}
                            </button>
                          )}
                        </div>
                      </div>
                      {!explainData && !explainLoading && (
                        <p className="text-sm text-slate-400">Click Explain to generate SHAP importance charts and Qwen3.5-0.8B visual analysis.</p>
                      )}
                      {showExplain && explainData && (
                        <div className="space-y-4">
                          {Object.entries(explainData).map(([name, pdata]: [string, any]) => (
                            <div key={name} className="space-y-1.5">
                              <div className="flex justify-between">
                                <span className="text-sm font-bold text-slate-800 uppercase">{name}</span>
                                <span className="text-sm text-slate-500 font-mono">{pdata.summary}</span>
                              </div>
                              {pdata.chart_png_b64 && (
                                <img src={`data:image/png;base64,${pdata.chart_png_b64}`} alt={`${name} feature importance`}
                                  className="w-full rounded-lg border border-slate-200" />
                              )}
                            </div>
                          ))}
                          {analyzeResult && (
                            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 space-y-2">
                              <p className="text-xs font-bold text-blue-700 uppercase tracking-wider flex items-center gap-1.5">
                                <Bot size={11}/> Qwen3.5-0.8B VLM Assessment
                              </p>
                              <p className="text-sm text-slate-700 leading-relaxed">{analyzeResult.assessment}</p>
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
              <div className="w-80 border-r border-slate-200 bg-white flex flex-col shrink-0">
                <div className="p-4 border-b border-slate-200 flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-500 uppercase tracking-widest flex items-center gap-1.5">
                    <Bot size={13} className="text-blue-600"/> ARIA Findings
                  </span>
                  <span className="text-xs text-slate-400 font-mono">auto-scans every 60s</span>
                </div>
                <div className="flex-1 overflow-y-auto divide-y divide-slate-100">
                  {invLoading && <p className="p-4 text-sm text-slate-400">Scanning...</p>}
                  {!invLoading && ariaInvestigations.length === 0 && (
                    <div className="p-6 text-center text-sm text-slate-400">
                      No investigations yet. ARIA needs ≥3 events above 0.3 risk from the same user within 10 minutes.
                    </div>
                  )}
                  {ariaInvestigations.map(inv => (
                    <button key={inv.id} onClick={() => setSelectedInv(inv)}
                      className={`w-full text-left p-4 hover:bg-slate-50 flex flex-col gap-1.5 transition-colors ${selectedInv?.id === inv.id ? 'bg-slate-100' : ''}`}>
                      <div className="flex items-center justify-between">
                        <span className={`text-xs font-bold px-2 py-0.5 rounded-full uppercase ${
                          inv.status==='open'?'bg-blue-100 text-blue-700':inv.status==='resolved'?'bg-emerald-100 text-emerald-800':'bg-slate-200 text-slate-600'
                        }`}>{inv.status}</span>
                        <span className="text-xs text-slate-500 font-mono">conf {(inv.confidence*100).toFixed(0)}%</span>
                      </div>
                      <p className="text-sm text-slate-800 font-semibold leading-snug">{inv.hypothesis}</p>
                      <p className="text-xs text-slate-500 font-mono">{inv.cluster_key} · {inv.event_count} events · cycle {inv.cycle}</p>
                    </button>
                  ))}
                </div>
              </div>
              <div className="flex-1 overflow-y-auto p-8 bg-slate-50">
                {selectedInv ? (
                  <div className="space-y-6 max-w-3xl">
                    <header className="flex justify-between items-start pb-4 border-b border-slate-200">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <Bot size={16} className="text-blue-600"/>
                          <h2 className="text-lg font-bold text-slate-900">Investigation #{selectedInv.id}</h2>
                          <span className="text-xs font-mono bg-slate-200 text-slate-700 px-2 py-0.5 rounded uppercase font-semibold">{selectedInv.classification}</span>
                        </div>
                        <p className="text-sm text-slate-600 font-medium">{selectedInv.hypothesis}</p>
                        <p className="text-xs text-slate-400 font-mono mt-1">User: {selectedInv.cluster_key} · {selectedInv.event_count} events · {selectedInv.cycle} scan cycles</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <button onClick={() => updateInvStatus(selectedInv.id, 'resolved')}
                          className="flex items-center gap-1 text-xs bg-emerald-50 border border-emerald-200 text-emerald-700 hover:bg-emerald-100 px-2.5 py-1.5 rounded-lg font-bold uppercase transition-colors">
                          <CheckCircle2 size={11}/> Resolve
                        </button>
                        <button onClick={() => updateInvStatus(selectedInv.id, 'fp_confirmed')}
                          className="flex items-center gap-1 text-xs bg-slate-100 border border-slate-200 text-slate-600 hover:bg-slate-200 px-2.5 py-1.5 rounded-lg font-bold uppercase transition-colors">
                          <XCircle size={11}/> False Positive
                        </button>
                      </div>
                    </header>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                        <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-2">Evidence Summary</p>
                        <p className="text-sm text-slate-700 leading-relaxed">{selectedInv.evidence_summary}</p>
                      </div>
                      <div className="bg-white border border-slate-200 rounded-xl p-4 shadow-sm">
                        <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest mb-2">Confidence</p>
                        <div className="flex items-baseline gap-1 font-mono">
                          <span className="text-3xl font-bold text-blue-600">{(selectedInv.confidence*100).toFixed(0)}%</span>
                        </div>
                        <div className="mt-2 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                          <div className="h-full bg-blue-500 rounded-full" style={{width:`${selectedInv.confidence*100}%`}}/>
                        </div>
                      </div>
                    </div>
                    {selectedInv.vlm_assessment && (
                      <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 space-y-2">
                        <p className="text-xs font-bold text-blue-700 uppercase tracking-wider flex items-center gap-1.5">
                          <Bot size={11}/> Qwen3.5-0.8B VLM Autonomous Analysis
                        </p>
                        <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">{selectedInv.vlm_assessment}</p>
                      </div>
                    )}
                    <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-2 shadow-sm">
                      <p className="text-xs font-semibold text-slate-500 uppercase tracking-widest">Related Events</p>
                      <div className="flex flex-wrap gap-2">
                        {(selectedInv.cluster_event_ids || []).map((id: number) => (
                          <button key={id} onClick={() => { setActiveTab('incident'); setSelectedEventId(id); }}
                            className="text-sm font-mono bg-slate-100 hover:bg-slate-200 text-slate-700 px-2 py-1 rounded transition-colors border border-slate-200">
                            #{id}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                ) : (
                  <div className="h-full flex flex-col items-center justify-center text-slate-400 space-y-3">
                    <Bot size={40} className="opacity-30"/>
                    <p className="text-sm font-mono">Select an investigation to view ARIA analysis</p>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* ══ SESSIONS TAB ════════════════════════════════════════════════ */}
          {activeTab === 'sessions' && (() => {
            const riskLabels = ['','ALLOW','CHALLENGE','RESTRICT','CONTAIN'];
            const riskBadge = ['','bg-emerald-100 text-emerald-800 border-emerald-300','bg-amber-100 text-amber-800 border-amber-300','bg-orange-100 text-orange-800 border-orange-300','bg-red-100 text-red-800 border-red-300'];
            const formatTelEvent = (t: any) => {
              const d = t.data || {};
              const ev = d.event || '';
              if (t.type === 'keystroke') return ev === 'dwell' ? `dwell ${d.dwellTime}ms` : `flight ${d.flightTime}ms`;
              if (t.type === 'mouse') return ev === 'move' ? `move v=${Number(d.velocity||0).toFixed(2)}` : `click (${d.x|0},${d.y|0})`;
              if (ev === 'paste') return `paste · ${d.hasDigits ? 'digits' : 'text'} · len=${d.length}`;
              if (ev === 'focus_change') return `focus ${d.state}`;
              if (ev === 'idle') return 'idle period';
              if (ev === 'scroll') return 'scroll';
              if (ev === 'visibility') return `tab ${d.state}`;
              if (ev === 'tab_change') return `tab → ${d.tab}`;
              if (ev === 'page_load') return 'page load';
              return ev || t.type;
            };
            const telColor = (t: any) => t.type === 'keystroke' ? 'text-blue-700' : t.type === 'mouse' ? 'text-slate-600' : (t.data?.event === 'paste' ? 'text-red-600 font-bold' : 'text-amber-700');
            const ariaForSession = liveData?.session ? ariaInvestigations.find(i => i.cluster_key === liveData.session.user_id && i.status === 'open') : null;

            return (
            <div className="flex-1 flex flex-col overflow-hidden">
              {/* Stats bar */}
              <div className="grid grid-cols-4 border-b border-slate-200 shrink-0">
                {[
                  { label: 'Active Sessions',     value: sessions.filter(s=>s.is_active).length,                     color: 'text-slate-900' },
                  { label: 'Currently Escalated', value: sessions.filter(s=>s.is_active&&s.risk_level>1).length,    color: 'text-amber-700' },
                  { label: 'Total Key Rotations', value: sessions.reduce((a,s)=>a+(s.key_version-1),0),            color: 'text-slate-900' },
                  { label: 'Contained / Revoked', value: sessions.filter(s=>s.risk_level>=4||!s.is_active).length, color: 'text-red-700'   },
                ].map((stat, i) => (
                  <div key={stat.label} className={`px-8 py-5 ${i<3?'border-r border-slate-200':''}`}>
                    <p className="text-sm font-semibold text-slate-500 uppercase tracking-wider mb-1">{stat.label}</p>
                    <p className={`text-5xl font-bold leading-none ${stat.color}`}>{stat.value}</p>
                  </div>
                ))}
              </div>

              {/* Split pane: session list LEFT | investigation panel RIGHT */}
              <div className="flex flex-1 overflow-hidden">

                {/* ── Session list (left pane) ── */}
                <div className={`flex flex-col border-r border-slate-200 overflow-hidden transition-all duration-200 ${liveSessionId ? 'w-80 shrink-0' : 'flex-1'}`}>
                  <div className="px-5 py-3 bg-slate-50 border-b border-slate-200 flex items-center justify-between shrink-0">
                    <p className="text-sm font-semibold text-slate-600">
                      {liveSessionId ? 'Sessions' : 'Click a row to investigate'}
                    </p>
                    <button onClick={() => setRefreshTrigger(p => p+1)} className="flex items-center gap-1 text-xs text-slate-500 hover:text-slate-800 font-semibold">
                      <RefreshCw size={11}/> Refresh
                    </button>
                  </div>
                  <div className="overflow-y-auto flex-1">
                    {sessions.length === 0 ? (
                      <div className="py-16 text-center text-slate-400 text-base px-4">No sessions yet. Log in to the Customer Portal.</div>
                    ) : (
                      <table className="w-full text-left">
                        {!liveSessionId && (
                          <thead>
                            <tr className="border-b-2 border-slate-200 bg-slate-50">
                              <th className="px-6 py-4 text-sm font-bold text-slate-600 uppercase tracking-wider">User</th>
                              <th className="px-4 py-4 text-sm font-bold text-slate-600 uppercase tracking-wider">Risk</th>
                              <th className="px-4 py-4 text-sm font-bold text-slate-600 uppercase tracking-wider">Key</th>
                              <th className="px-4 py-4 text-sm font-bold text-slate-600 uppercase tracking-wider">Status</th>
                            </tr>
                          </thead>
                        )}
                        <tbody className="divide-y divide-slate-100">
                          {sessions.map(s => {
                            const isSelected = liveSessionId === s.session_id;
                            const isFlashing = s.session_id === flashingSessionId;
                            const rl = Math.min(4, Math.max(1, s.risk_level));
                            const compact = !!liveSessionId;
                            return (
                              <tr key={s.session_id}
                                onClick={() => setLiveSessionId(isSelected ? null : s.session_id)}
                                className={`cursor-pointer transition-colors border-l-4 ${
                                  isSelected   ? 'bg-slate-900 border-slate-700' :
                                  isFlashing   ? 'bg-amber-50 border-amber-400 animate-pulse' :
                                  s.risk_level >= 4 ? 'hover:bg-red-50 border-red-200' :
                                  'hover:bg-slate-50 border-transparent'
                                }`}>
                                {compact ? (
                                  /* Compact mode when a session is selected */
                                  <td className="px-4 py-3 w-full">
                                    <div className={`text-sm font-bold truncate ${isSelected?'text-white':'text-slate-800'}`}>{s.user_id}</div>
                                    <div className="flex items-center gap-2 mt-0.5">
                                      <span className={`text-xs font-bold px-1.5 py-0.5 rounded ${
                                        rl===4?'bg-red-100 text-red-700':rl===3?'bg-orange-100 text-orange-700':rl===2?'bg-amber-100 text-amber-700':isSelected?'bg-slate-700 text-slate-200':'bg-slate-100 text-slate-500'
                                      }`}>L{rl}</span>
                                      <span className={`text-xs font-mono ${isSelected?'text-slate-400':'text-slate-400'}`}>v{s.key_version}</span>
                                      {s.is_active && s.risk_level < 4
                                        ? <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 ml-auto shrink-0"/>
                                        : <span className="w-1.5 h-1.5 rounded-full bg-slate-300 ml-auto shrink-0"/>}
                                    </div>
                                  </td>
                                ) : (
                                  /* Full table mode when no session selected */
                                  <>
                                    <td className="px-6 py-5">
                                      <div className="text-base font-bold text-slate-900">{s.user_id}
                                        {isFlashing && <span className="ml-2 text-xs bg-amber-100 text-amber-800 font-bold px-2 py-0.5 rounded uppercase">Key Rotated</span>}
                                      </div>
                                      <div className="text-sm font-mono text-slate-400 mt-0.5">{s.session_id.slice(0,24)}…</div>
                                    </td>
                                    <td className="px-4 py-5">
                                      <span className={`px-2.5 py-1 rounded text-sm font-bold uppercase border ${riskBadge[rl]}`}>L{rl}</span>
                                    </td>
                                    <td className="px-4 py-5 font-mono text-base font-bold text-slate-700">v{s.key_version}</td>
                                    <td className="px-4 py-5">
                                      {s.is_active && s.risk_level < 4
                                        ? <span className="flex items-center gap-1.5 text-sm font-bold text-emerald-700"><span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"/>Active</span>
                                        : <span className="flex items-center gap-1.5 text-sm font-bold text-slate-400"><span className="w-2 h-2 rounded-full bg-slate-400"/>Locked</span>}
                                    </td>
                                  </>
                                )}
                              </tr>
                            );
                          })}
                        </tbody>
                      </table>
                    )}
                  </div>
                </div>

                {/* ── Investigation panel (right pane) ── */}
                {liveSessionId && (
                  <div className="flex-1 flex flex-col overflow-hidden bg-white">
                    {/* Panel header */}
                    <div className="bg-slate-900 text-white px-6 py-4 flex items-center gap-4 shrink-0">
                      <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse shrink-0"/>
                      <div className="min-w-0 flex-1">
                        <div className="text-xl font-bold leading-tight truncate">
                          {liveData?.session?.user_id ?? sessions.find(s=>s.session_id===liveSessionId)?.user_id ?? '…'}
                        </div>
                        <div className="text-xs font-mono text-slate-400 mt-0.5 truncate">{liveSessionId}</div>
                      </div>
                      {liveData?.session && (() => {
                        const rl = liveData.session.risk_level || 1;
                        const bg = ['','bg-emerald-600','bg-amber-500','bg-orange-500','bg-red-600'];
                        return <span className={`px-3 py-1 rounded text-sm font-bold uppercase text-white shrink-0 ${bg[rl]||bg[1]}`}>L{rl} {riskLabels[rl]}</span>;
                      })()}
                      {liveData?.session && (
                        <span className="text-xs text-slate-400 font-mono shrink-0">
                          AES v{liveData.session.key_version}{liveData.session.is_active===false?' · REVOKED':''}
                        </span>
                      )}
                      <button onClick={() => { setLiveSessionId(null); setLiveData(null); }}
                        className="text-slate-400 hover:text-white text-xl font-bold ml-2 shrink-0 leading-none">✕</button>
                    </div>

                    {!liveData ? (
                      <div className="flex-1 flex items-center justify-center text-slate-400 text-base">
                        <RefreshCw size={18} className="animate-spin mr-3"/> Loading session data…
                      </div>
                    ) : (
                      /* 3-column investigation body */
                      <div className="flex-1 grid grid-cols-3 divide-x divide-slate-200 overflow-hidden">

                        {/* Col 1: Security event timeline */}
                        <div className="flex flex-col overflow-hidden">
                          <div className="px-5 py-3 border-b border-slate-100 shrink-0">
                            <p className="text-sm font-bold text-slate-500 uppercase tracking-wider">Security Timeline</p>
                          </div>
                          <div className="flex-1 overflow-y-auto p-5">
                            {sessionTimeline.length === 0
                              ? <p className="text-base text-slate-400 italic mt-4">No security events yet for this session.</p>
                              : sessionTimeline.map((ev: any, i: number) => {
                                  const rl = ev.escalation_level || 1;
                                  const dot = rl>=4?'bg-red-500':rl>=3?'bg-orange-500':rl>=2?'bg-amber-500':'bg-emerald-500';
                                  return (
                                    <div key={ev.id} className="flex gap-3 mb-5">
                                      <div className="flex flex-col items-center shrink-0">
                                        <span className={`w-3 h-3 rounded-full mt-1 ${dot}`}/>
                                        {i < sessionTimeline.length-1 && <div className="w-0.5 flex-1 bg-slate-200 mt-1 min-h-[16px]"/>}
                                      </div>
                                      <div className="pb-1 min-w-0">
                                        <div className="text-xs font-mono text-slate-400">{new Date(ev.timestamp).toLocaleTimeString()}</div>
                                        <div className={`text-base font-bold mt-0.5 ${rl>=4?'text-red-700':rl>=3?'text-orange-700':rl>=2?'text-amber-700':'text-slate-800'}`}>
                                          L{rl} {riskLabels[rl]} · {Math.round(ev.overall_risk*100)}%
                                        </div>
                                        {ev.action_context && <div className="text-sm text-slate-600 mt-0.5">{ev.action_context}</div>}
                                        {ev.top_provider && <div className="text-sm text-slate-400 mt-0.5">via {ev.top_provider} ({Math.round(ev.top_provider_score*100)}%)</div>}
                                      </div>
                                    </div>
                                  );
                                })
                            }
                          </div>
                        </div>

                        {/* Col 2: Live telemetry stream */}
                        <div className="flex flex-col overflow-hidden">
                          <div className="px-5 py-3 border-b border-slate-100 shrink-0 flex items-center justify-between">
                            <p className="text-sm font-bold text-slate-500 uppercase tracking-wider">Live Telemetry</p>
                            <span className="text-sm text-slate-400">{liveData.telemetry_count || 0} events</span>
                          </div>
                          <div className="flex-1 overflow-y-auto p-4">
                            {(!liveData.telemetry || liveData.telemetry.length === 0)
                              ? <p className="text-base text-slate-400 italic mt-4">Awaiting telemetry…</p>
                              : [...(liveData.telemetry || [])].reverse().map((t: any) => {
                                  const ts = t.timestamp ? new Date(t.timestamp).toLocaleTimeString() : '—';
                                  const typeLabel = t.type==='keystroke'?'KEY':t.type==='mouse'?'MSE':'SES';
                                  return (
                                    <div key={t.id} className="flex items-baseline gap-2 py-1.5 border-b border-slate-50 last:border-0">
                                      <span className="text-xs font-mono text-slate-400 w-18 shrink-0">{ts}</span>
                                      <span className={`text-xs font-bold uppercase w-9 shrink-0 ${t.type==='keystroke'?'text-blue-600':t.type==='mouse'?'text-slate-400':'text-amber-600'}`}>{typeLabel}</span>
                                      <span className={`text-sm font-mono truncate ${telColor(t)}`}>{formatTelEvent(t)}</span>
                                    </div>
                                  );
                                })
                            }
                          </div>
                        </div>

                        {/* Col 3: Model scores + ARIA */}
                        <div className="flex flex-col overflow-hidden">
                          <div className="px-5 py-3 border-b border-slate-100 shrink-0">
                            <p className="text-sm font-bold text-slate-500 uppercase tracking-wider">Model Assessment</p>
                          </div>
                          <div className="flex-1 overflow-y-auto p-5 space-y-5">
                            {/* Big risk number */}
                            {liveData.latest_event ? (() => {
                              const risk = liveData.latest_event.overall_risk;
                              const pct = Math.round(risk*100);
                              const c = risk>=0.7?'text-red-700':risk>=0.4?'text-orange-700':risk>=0.2?'text-amber-700':'text-emerald-700';
                              return (
                                <div className="text-center pb-5 border-b border-slate-100">
                                  <p className="text-xs font-bold text-slate-400 uppercase tracking-wider mb-1">Current Risk</p>
                                  <div className={`text-8xl font-bold font-mono leading-none ${c}`}>{pct}</div>
                                  <div className="text-sm text-slate-400 mt-1">/ 100</div>
                                </div>
                              );
                            })() : (
                              <p className="text-base text-slate-400 italic mt-4">No model evaluation yet for this session.</p>
                            )}

                            {/* Provider bars */}
                            {liveData.latest_event && (
                              <div className="space-y-3">
                                {Object.entries(liveData.latest_event.breakdown || {}).map(([name, res]: [string, any]) => {
                                  const short = PROVIDER_META[name]?.short || name.replace('Provider','').replace('Risk','');
                                  const pct = Math.round((res.risk_score||0)*100);
                                  const bar = pct>=60?'bg-red-500':pct>=30?'bg-amber-400':'bg-emerald-500';
                                  const sc  = pct>=60?'text-red-700':pct>=30?'text-amber-700':'text-emerald-700';
                                  return (
                                    <div key={name}>
                                      <div className="flex justify-between items-baseline mb-1">
                                        <span className="text-base font-semibold text-slate-700">{short}</span>
                                        <span className={`text-base font-bold font-mono ${sc}`}>{pct}%</span>
                                      </div>
                                      <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
                                        <div className={`h-full rounded-full transition-all duration-500 ${bar}`} style={{width:`${pct}%`}}/>
                                      </div>
                                    </div>
                                  );
                                })}
                              </div>
                            )}

                            {/* ARIA */}
                            {ariaForSession && (
                              <div className="border-t border-slate-200 pt-4">
                                <div className="flex items-center gap-2 mb-2">
                                  <Bot size={15} className="text-blue-600 shrink-0"/>
                                  <span className="text-sm font-bold text-blue-700 uppercase tracking-wider">ARIA</span>
                                  <span className="text-xs text-slate-400 font-mono ml-auto">{Math.round(ariaForSession.confidence*100)}% conf</span>
                                </div>
                                <p className="text-sm font-semibold text-slate-700 mb-1">{ariaForSession.hypothesis}</p>
                                <p className="text-sm text-slate-600 leading-relaxed whitespace-pre-line">{ariaForSession.vlm_assessment}</p>
                              </div>
                            )}
                          </div>
                        </div>

                      </div>
                    )}
                  </div>
                )}

                {/* Placeholder when nothing selected */}
                {!liveSessionId && sessions.length > 0 && (
                  <div className="hidden"/>
                )}
              </div>
            </div>
            );
          })()}

          {/* ══ SETTINGS TAB ════════════════════════════════════════════════ */}
          {activeTab === 'settings' && (
            <div className="flex-1 overflow-y-auto p-8 space-y-6">
              <header className="pb-4 border-b border-slate-200">
                <h2 className="text-xl font-bold text-slate-900 flex items-center gap-2">
                  <Sliders size={20} className="text-slate-700" /> Risk Policy Configuration
                </h2>
                <p className="text-sm text-slate-500 mt-1">
                  Fine-tune escalation thresholds, transfer limits, and provider weights live during operation.
                </p>
              </header>
              {configLoading && (
                <div className="h-48 flex items-center justify-center text-slate-700 gap-2 font-mono text-sm">
                  <RefreshCw size={16} className="animate-spin"/> Loading configuration...
                </div>
              )}
              {config && !configLoading && (
                <form onSubmit={saveConfig} className="max-w-4xl space-y-6">
                  <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4 shadow-sm">
                    <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-widest flex items-center gap-1.5">
                      <ShieldAlert size={14} className="text-amber-600"/> Policy Escalation Thresholds
                    </h3>
                    <div className="grid grid-cols-3 gap-4">
                      {[
                        ['threshold_challenge', 'Challenge (L2)'],
                        ['threshold_restrict',  'Restrict (L3)'],
                        ['threshold_contain',   'Contain (L4)'],
                      ].map(([key, label]) => (
                        <div key={key} className="space-y-1.5">
                          <label className="text-xs font-semibold text-slate-400 uppercase tracking-widest">{label}</label>
                          <input type="number" step="0.05" min="0" max="1" value={config[key]}
                            onChange={e => setConfig({...config, [key]: parseFloat(e.target.value)||0})}
                            className="w-full bg-slate-50 border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 focus:outline-none focus:border-slate-400 font-sans" />
                        </div>
                      ))}
                    </div>
                  </div>
                  <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4 shadow-sm">
                    <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-widest flex items-center gap-1.5">
                      <Database size={14} className="text-slate-600"/> Operational Parameters
                    </h3>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-1.5">
                        <label className="text-xs font-semibold text-slate-400 uppercase tracking-widest">Max Transfer Limit (₹)</label>
                        <input type="number" min="1" value={config.max_transfer_limit}
                          onChange={e => setConfig({...config, max_transfer_limit: parseInt(e.target.value)||0})}
                          className="w-full bg-slate-50 border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 focus:outline-none focus:border-slate-400 font-sans" />
                      </div>
                      <div className="space-y-1.5">
                        <label className="text-xs font-semibold text-slate-400 uppercase tracking-widest">Trust Recovery Factor</label>
                        <input type="number" step="0.1" min="0.1" max="10" value={config.trust_recovery_speed}
                          onChange={e => setConfig({...config, trust_recovery_speed: parseFloat(e.target.value)||0})}
                          className="w-full bg-slate-50 border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-800 focus:outline-none focus:border-slate-400 font-sans" />
                      </div>
                    </div>
                  </div>
                  <div className="bg-white border border-slate-200 rounded-xl p-6 space-y-4 shadow-sm">
                    <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-widest flex items-center gap-1.5">
                      <Cpu size={14} className="text-slate-600"/> Provider Ensemble Weights
                    </h3>
                    <div className="grid grid-cols-2 gap-4">
                      {Object.keys(config.weights || {}).map(provider => (
                        <div key={provider} className="space-y-1.5">
                          <div className="flex justify-between">
                            <span className="text-xs font-semibold text-slate-500 uppercase tracking-widest">{provider.replace('RiskProvider','').replace('Provider','').replace('Risk','')}</span>
                            <span className="text-sm font-mono font-bold text-slate-700">{((config.weights[provider]||0)*100).toFixed(0)}%</span>
                          </div>
                          <input type="range" min="0" max="1" step="0.05" value={config.weights[provider]||0}
                            onChange={e => setConfig({...config, weights:{...config.weights,[provider]:parseFloat(e.target.value)}})}
                            className="w-full accent-slate-700" />
                        </div>
                      ))}
                    </div>
                  </div>
                  <button type="submit" disabled={configSaving}
                    className="w-full py-3 bg-slate-900 hover:bg-slate-800 text-white font-bold text-sm rounded-lg uppercase tracking-wider flex items-center justify-center gap-2 transition-colors disabled:opacity-40">
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
