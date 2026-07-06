import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import {
  Flame, User, AlertTriangle, Mail, UserX, Loader2, LogOut,
  ShieldAlert, ShieldCheck, ShieldOff, Play, Target,
  Zap, Lock, Unlock, TrendingUp, Activity, Sliders
} from 'lucide-react';
import { usePreferences } from './Preferences';

axios.defaults.withCredentials = true;
const API_BASE = '';

const T: Record<string, any> = {
  en: { header_title: 'MNIT Threat Simulator', header_sub: 'Adversarial Operations Console', logout: 'Close Console' },
  hi: { header_title: 'एमएनआईटी थ्रेट सिम्युलेटर', header_sub: 'प्रतिकूल संचालन कंसोल', logout: 'कंसोल बंद करें' },
};

const SCENARIOS = [
  { key: 'normal_customer',  label: 'Normal Customer',    icon: User,           accent: 'emerald', desc: 'Baseline: no attack.' },
  { key: 'elderly_victim',   label: 'Elderly Victim',     icon: AlertTriangle,  accent: 'amber',   desc: 'Phishing link → fraudulent transfer.' },
  { key: 'phishing_victim',  label: 'Phishing Victim',    icon: Mail,           accent: 'orange',  desc: 'Phishing link → credential harvest.' },
  { key: 'account_takeover', label: 'Account Takeover',   icon: UserX,          accent: 'red',     desc: 'Impossible travel → device exploit.' },
  { key: 'full_fraud_chain', label: 'Full Fraud Chain',   icon: Flame,          accent: 'red',     desc: 'Complete LURE→HOOK→EXPLOIT→MONETIZE.' },
];

const PHASE_COLORS: Record<string, string> = {
  LURE: 'text-amber-400 bg-amber-500/10 border-amber-500/20',
  HOOK: 'text-orange-400 bg-orange-500/10 border-orange-500/20',
  EXPLOIT: 'text-red-400 bg-red-500/10 border-red-500/20',
  MONETIZE: 'text-red-500 bg-red-600/10 border-red-600/30',
  NEUTRAL: 'text-slate-600 bg-slate-100 border-slate-200',
};

const LEVEL_META = [
  { label: 'ALLOW',      color: 'text-emerald-400', bg: 'bg-emerald-500/10 border-emerald-500/20', Icon: ShieldCheck },
  { label: 'CHALLENGE',  color: 'text-amber-400',   bg: 'bg-amber-500/10 border-amber-500/20',    Icon: ShieldAlert },
  { label: 'RESTRICT',   color: 'text-orange-400',  bg: 'bg-orange-500/10 border-orange-500/20',  Icon: ShieldAlert },
  { label: 'CONTAIN',    color: 'text-red-400',      bg: 'bg-red-500/10 border-red-500/20',        Icon: ShieldOff },
];

function RiskBar({ value, max = 1 }: { value: number; max?: number }) {
  const pct = Math.min(100, (value / max) * 100);
  const color = pct > 70 ? 'bg-red-500' : pct > 40 ? 'bg-orange-400' : pct > 20 ? 'bg-amber-400' : 'bg-emerald-400';
  return (
    <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
      <div className={`h-full ${color} rounded-full transition-all duration-700`} style={{ width: `${pct}%` }} />
    </div>
  );
}

export default function App() {
  const pref = usePreferences();
  const t = (k: string) => T[pref.lang][k] || k;

  const [auth, setAuth] = useState(false);
  const [user, setUser] = useState(''); const [pass, setPass] = useState('');
  const [err, setErr] = useState(''); const [loading, setLoading] = useState(false);

  const [activeTab, setActiveTab] = useState<'chain' | 'custom'>('chain');
  const [running, setRunning] = useState<string | null>(null);
  const [result, setResult] = useState<{ scenarioKey: string; steps: any[]; userId: string } | null>(null);
  const [animStep, setAnimStep] = useState(-1);
  const bottomRef = useRef<HTMLDivElement>(null);

  // Custom
  const [cp, setCp] = useState({
    user_id: 'sim_target', session_id: 'sim_custom',
    amount: 0, is_new_beneficiary: false,
    current_url: '', login_anomaly: false,
    new_device: false, rooted: false, vpn_detected: false,
  });
  const [customResult, setCustomResult] = useState<any>(null);
  const [evalLoading, setEvalLoading] = useState(false);

  useEffect(() => {
    axios.get(`${API_BASE}/attacker/auth/me`).then(() => setAuth(true)).catch(() => setAuth(false));
  }, []);

  const login = async (e: React.FormEvent) => {
    e.preventDefault(); setLoading(true); setErr('');
    try { await axios.post(`${API_BASE}/attacker/auth/login`, { username: user, password: pass }); setAuth(true); }
    catch (ex: any) { setErr(ex.response?.data?.detail || 'Invalid credentials'); }
    finally { setLoading(false); }
  };

  const logout = async () => {
    try { await axios.post(`${API_BASE}/attacker/auth/logout`); } catch {}
    setAuth(false); setUser(''); setPass('');
  };

  const [liveMode, setLiveMode] = useState(false);
  const [targetUser, setTargetUser] = useState('keshav');
  const [availableUsers, setAvailableUsers] = useState<any[]>([]);

  useEffect(() => {
    if (auth) {
      axios.get(`${API_BASE}/attacker/users`)
        .then(res => setAvailableUsers(res.data))
        .catch(() => setAvailableUsers([{username: 'keshav'}]));
    }
  }, [auth]);

  const runScenario = async (key: string) => {
    setRunning(key); setResult(null); setAnimStep(-1);
    const endpoint = liveMode
      ? `${API_BASE}/attacker/scenarios/${key}/run-live?target_user=${targetUser}`
      : `${API_BASE}/attacker/scenarios/${key}/run`;
    try {
      const res = await axios.post(endpoint);
      const steps = res.data.steps || [];
      setResult({ scenarioKey: key, steps, userId: res.data.user_id, live: res.data.live });
      for (let i = 0; i < steps.length; i++) {
        await new Promise(r => setTimeout(r, 600));
        setAnimStep(i);
      }
    } catch (e: any) {
      alert(e.response?.data?.detail || 'Scenario failed');
    }
    finally { setRunning(null); }
  };

  const evalCustom = async (e: React.FormEvent) => {
    e.preventDefault(); setEvalLoading(true); setCustomResult(null);
    try {
      const res = await axios.post(`${API_BASE}/attacker/evaluate/raw`, cp);
      setCustomResult(res.data);
    } catch { alert('Evaluation failed'); }
    finally { setEvalLoading(false); }
  };

  if (!auth) return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6">
      <div className="w-full max-w-sm bg-white border border-slate-200 rounded-xl p-8 space-y-6">
        <div className="flex flex-col items-center gap-2">
          <div className="w-12 h-12 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 grid place-items-center animate-pulse">
            <Flame size={24} />
          </div>
          <h1 className="text-lg font-bold text-slate-900 uppercase tracking-tight">Controlled Attack Console</h1>
          <p className="text-xs text-slate-500 text-center">Adversarial simulation for MNIT threat model validation</p>
        </div>
        <form onSubmit={login} className="space-y-4">
          {err && <p className="text-xs text-red-400 bg-red-500/10 border border-red-500/20 rounded-lg p-3">{err}</p>}
          <div className="space-y-1.5">
            <label className="text-sm font-bold text-slate-500 uppercase tracking-wider">Simulator ID</label>
            <input value={user} onChange={e => setUser(e.target.value)} placeholder="attacker"
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-4 py-2 text-xs text-slate-900 focus:outline-none focus:border-red-500/40" />
          </div>
          <div className="space-y-1.5">
            <label className="text-sm font-bold text-slate-500 uppercase tracking-wider">Passkey</label>
            <input type="password" value={pass} onChange={e => setPass(e.target.value)} placeholder="••••••••"
              className="w-full bg-slate-50 border border-slate-200 rounded-lg px-4 py-2 text-xs text-slate-900 focus:outline-none focus:border-red-500/40" />
          </div>
          <button disabled={loading} type="submit"
            className="w-full py-2.5 bg-red-600 hover:bg-red-500 text-slate-900 font-bold text-xs rounded-lg transition-colors uppercase tracking-wider">
            {loading ? 'Connecting...' : 'Establish Connection'}
          </button>
        </form>
      </div>
    </div>
  );

  const scenarioMeta = result ? SCENARIOS.find(s => s.key === result.scenarioKey) : null;
  const maxRisk = result ? Math.max(...result.steps.map(s => s.result.overall_risk)) : 0;
  const finalStep = result?.steps[result.steps.length - 1];
  const breached = finalStep && finalStep.result.escalation_level <= 2;

  return (
    <div className="flex h-screen bg-slate-50 text-slate-900 flex-col">
      {/* Header */}
      <header className="border-b border-slate-200 px-6 py-3 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-red-500/10 border border-red-500/20 grid place-items-center text-red-400">
            <Flame size={16} />
          </div>
          <div>
            <h1 className="font-bold text-sm text-slate-900">{t('header_title')}</h1>
            <p className="text-xs text-slate-500 uppercase tracking-widest font-mono">{t('header_sub')}</p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-sm font-mono bg-red-500/10 border border-red-500/20 text-red-400 px-3 py-1 rounded-full">sim_* namespace isolated</span>
          <div className="flex bg-white border border-slate-200 rounded-lg p-1 text-xs font-bold">
            {['en','hi'].map(l => (
              <button key={l} onClick={() => pref.setLang(l)} className={`px-2 py-0.5 rounded uppercase ${pref.lang===l?'bg-red-600 text-slate-900':'text-slate-600 hover:text-slate-900'}`}>{l}</button>
            ))}
          </div>
          <button onClick={logout} className="flex items-center gap-1.5 text-xs text-slate-600 hover:text-slate-900 bg-white border border-slate-200 hover:bg-slate-100 px-3 py-1.5 rounded-lg">
            <LogOut size={12}/>{t('logout')}
          </button>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <aside className="w-52 border-r border-slate-200 flex flex-col shrink-0 p-3 gap-1">
          {[
            { id: 'chain', icon: Target, label: 'Kill Chain' },
            { id: 'custom', icon: Sliders, label: 'Custom Vector' },
          ].map(({ id, icon: Icon, label }) => (
            <button key={id} onClick={() => setActiveTab(id as any)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-sm font-medium rounded-lg transition-colors ${
                activeTab === id ? 'bg-red-500/10 text-red-400' : 'text-slate-600 hover:text-slate-900 hover:bg-white/[0.04]'
              }`}>
              <Icon size={16}/><span>{label}</span>
            </button>
          ))}
        </aside>

        {/* Kill Chain Tab */}
        {activeTab === 'chain' && (
          <div className="flex-1 flex overflow-hidden">
            {/* Scenario picker */}
            <div className="w-64 border-r border-slate-200 flex flex-col shrink-0 p-4 gap-2 overflow-y-auto">
              <div className="flex items-center justify-between mb-2">
                <p className="text-xs text-slate-500 uppercase font-bold tracking-wider">Select Scenario</p>
                <button
                  onClick={() => setLiveMode(v => !v)}
                  className={`text-xs font-bold px-2 py-1 rounded border uppercase tracking-wider transition-all ${
                    liveMode
                      ? 'bg-red-600 border-red-500 text-slate-900 animate-pulse'
                      : 'bg-slate-100 border-white/[0.1] text-slate-600 hover:text-slate-900'
                  }`}
                  title={liveMode ? `LIVE: targets real ${targetUser} session` : 'ISOLATED: uses sim_* session'}
                >
                  {liveMode ? '⚡ LIVE' : 'SIM'}
                </button>
              </div>
              {liveMode && (
                <div className="mb-2">
                  <label className="text-xs font-bold text-slate-500 uppercase block mb-1">Target Account</label>
                  <select
                    value={targetUser}
                    onChange={(e) => setTargetUser(e.target.value)}
                    className="w-full bg-white border border-slate-200 rounded px-2 py-2 text-xs text-slate-900 focus:outline-none focus:border-red-500/40"
                  >
                    {availableUsers.map(u => (
                      <option key={u.username} value={u.username}>{u.username} (Live User)</option>
                    ))}
                    <option value="sim_target">sim_target (Sandbox)</option>
                  </select>
                </div>
              )}
              {SCENARIOS.map(s => {
                const Icon = s.icon;
                const isRunning = running === s.key;
                const isDone = result?.scenarioKey === s.key;
                return (
                  <button key={s.key} onClick={() => !running && runScenario(s.key)} disabled={!!running}
                    className={`w-full text-left p-3 rounded-xl border transition-all ${
                      isDone ? 'border-red-500/30 bg-red-500/5' :
                      'border-slate-200 bg-white/40 hover:bg-slate-100/60'
                    } disabled:opacity-40`}>
                    <div className="flex items-center gap-2 mb-1">
                      {isRunning ? <Loader2 size={14} className="animate-spin text-red-400"/> : <Icon size={14} className={`text-${s.accent}-400`}/>}
                      <span className={`text-xs font-bold text-${s.accent}-300`}>{s.label}</span>
                    </div>
                    <p className="text-sm text-slate-500 leading-snug break-words">{s.desc}</p>
                  </button>
                );
              })}
            </div>

            {/* Kill chain results */}
            <div className="flex-1 overflow-y-auto p-6 space-y-6">
              {!result && !running && (
                <div className="h-full flex flex-col items-center justify-center text-slate-600 gap-3">
                  <Target size={40} className="opacity-20"/>
                  <p className="text-xs font-mono">Select a scenario to simulate an attack chain</p>
                </div>
              )}

              {running && !result && (
                <div className="h-full flex flex-col items-center justify-center gap-3 text-red-400">
                  <Loader2 size={32} className="animate-spin"/>
                  <p className="text-xs font-mono">Executing attack scenario...</p>
                </div>
              )}

              {result && (
                <>
                  {/* Header */}
                  <div className="flex items-center justify-between pb-4 border-b border-slate-200">
                    <div>
                      <h2 className="text-lg font-bold text-slate-900">{scenarioMeta?.label}</h2>
                      <p className="text-sm font-mono mt-0.5">
          {(result as any).live
            ? <span className="text-red-400 font-bold">LIVE TARGET: {result.userId} · {result.steps.length} steps · real session</span>
            : <span className="text-slate-500">DEMO SESSION · {result.steps.length} steps · isolated namespace</span>
          }
        </p>
                    </div>
                    {finalStep && (
                      <div className={`flex items-center gap-2 px-4 py-2 rounded-xl border text-sm font-bold ${
                        breached ? 'bg-red-500/10 border-red-500/30 text-red-400' : 'bg-teal-500/10 border-teal-500/30 text-teal-400'
                      }`}>
                        {breached ? <Unlock size={16}/> : <Lock size={16}/>}
                        {breached ? 'DEFENSES BREACHED' : 'ATTACK CONTAINED'}
                      </div>
                    )}
                  </div>

                  {/* Risk escalation bar */}
                  <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-3">
                    <div className="flex items-center justify-between">
                      <span className="text-sm font-bold text-slate-600 uppercase tracking-wider flex items-center gap-1.5">
                        <TrendingUp size={11}/> Risk Escalation Across Steps
                      </span>
                      <span className="text-xs font-mono text-slate-600">peak {(maxRisk * 100).toFixed(0)}/100</span>
                    </div>
                    <div className="flex items-end gap-1.5 h-16">
                      {result.steps.map((s, i) => {
                        const h = Math.max(8, s.result.overall_risk * 100);
                        const color = s.result.overall_risk > 0.7 ? 'bg-red-500' : s.result.overall_risk > 0.4 ? 'bg-orange-400' : s.result.overall_risk > 0.2 ? 'bg-amber-400' : 'bg-emerald-400';
                        return (
                          <div key={i} className="flex-1 flex flex-col items-center gap-1">
                            <span className="text-sm font-mono text-slate-500">{(s.result.overall_risk * 100).toFixed(0)}</span>
                            <div className={`w-full rounded-t-sm transition-all duration-700 ${color} ${i <= animStep ? 'opacity-100' : 'opacity-10'}`} style={{ height: `${h}%` }}/>
                          </div>
                        );
                      })}
                    </div>
                    <div className="flex gap-1.5">
                      {result.steps.map((_, i) => (
                        <div key={i} className="flex-1 text-center text-sm text-slate-600 font-mono">S{i+1}</div>
                      ))}
                    </div>
                  </div>

                  {/* Step-by-step kill chain */}
                  <div className="space-y-3">
                    {result.steps.map((step, i) => {
                      const lvl = LEVEL_META[Math.min(step.result.escalation_level - 1, 3)];
                      const LvlIcon = lvl.Icon;
                      const visible = i <= animStep;
                      const cat = step.result.provider_breakdown
                        ? Object.values(step.result.provider_breakdown).find((p: any) => p.event_category !== 'NEUTRAL')
                        : null;
                      const phase = (cat as any)?.event_category || 'NEUTRAL';

                      return (
                        <div key={i} className={`transition-all duration-500 ${visible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}`}>
                          <div className="flex gap-3">
                            {/* Step indicator */}
                            <div className="flex flex-col items-center">
                              <div className={`w-7 h-7 rounded-full border-2 flex items-center justify-center text-sm font-bold font-mono shrink-0 ${
                                visible ? `${lvl.bg} border-current` : 'border-slate-700 text-slate-700'
                              } ${lvl.color}`}>
                                {i + 1}
                              </div>
                              {i < result.steps.length - 1 && (
                                <div className={`w-0.5 flex-1 mt-1 min-h-[1.5rem] ${visible ? 'bg-white/[0.08]' : 'bg-white/[0.02]'}`}/>
                              )}
                            </div>

                            {/* Card */}
                            <div className={`flex-1 mb-2 bg-white border rounded-xl p-4 space-y-3 ${visible ? 'border-slate-200' : 'border-slate-200'}`}>
                              <div className="flex items-start justify-between gap-2">
                                <div className="flex-1">
                                  <p className="text-xs font-semibold text-slate-900 leading-snug">{step.label}</p>
                                  <p className="text-sm text-slate-500 mt-0.5 italic">"{step.result.why_decision}"</p>
                                </div>
                                <div className="flex items-center gap-2 shrink-0">
                                  {phase !== 'NEUTRAL' && (
                                    <span className={`text-xs font-bold px-2 py-0.5 rounded border uppercase ${PHASE_COLORS[phase]}`}>{phase}</span>
                                  )}
                                  <div className={`flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-sm font-bold ${lvl.bg} ${lvl.color}`}>
                                    <LvlIcon size={11}/>
                                    {lvl.label}
                                  </div>
                                </div>
                              </div>

                              {/* Risk bar */}
                              <div className="space-y-1">
                                <div className="flex justify-between text-xs font-mono text-slate-500">
                                  <span>risk</span><span>{(step.result.overall_risk * 100).toFixed(1)}/100</span>
                                </div>
                                <RiskBar value={step.result.overall_risk}/>
                              </div>

                              {/* Provider mini-grid */}
                              {step.result.provider_breakdown && (
                                <div className="grid grid-cols-3 gap-1.5 pt-1 border-t border-slate-200">
                                  {Object.entries(step.result.provider_breakdown).map(([name, d]: [string, any]) => (
                                    <div key={name} className={`rounded-lg px-2 py-1.5 ${d.risk_score > 0.5 ? 'bg-red-500/10 border border-red-500/20' : 'bg-slate-50'}`}>
                                      <p className="text-sm text-slate-500 truncate">{name.replace('Provider','').replace('RiskProvider','').replace('Risk','')}</p>
                                      <p className={`text-sm font-mono font-bold ${d.risk_score > 0.7 ? 'text-red-400' : d.risk_score > 0.4 ? 'text-amber-400' : 'text-slate-500'}`}>
                                        {(d.risk_score * 100).toFixed(0)}
                                      </p>
                                    </div>
                                  ))}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Final verdict */}
                  {animStep >= result.steps.length - 1 && finalStep && (
                    <div className={`rounded-2xl p-5 border ${breached ? 'bg-red-500/5 border-red-500/20' : 'bg-teal-500/5 border-teal-500/20'}`}>
                      <div className="flex items-center gap-3 mb-3">
                        {breached ? <Unlock size={20} className="text-red-400"/> : <Lock size={20} className="text-teal-400"/>}
                        <div>
                          <p className={`text-sm font-bold ${breached ? 'text-red-300' : 'text-teal-300'}`}>
                            {breached ? 'Attack Partially Succeeded' : 'Attack Successfully Contained'}
                          </p>
                          <p className="text-sm text-slate-500 mt-0.5">{finalStep.result.recommendation}</p>
                        </div>
                      </div>
                      <div className="grid grid-cols-3 gap-3 font-mono text-center">
                        <div className="bg-slate-50/50 rounded-lg p-2">
                          <p className="text-xs text-slate-500 uppercase">Peak Risk</p>
                          <p className="text-lg font-bold text-slate-900">{(maxRisk * 100).toFixed(0)}</p>
                        </div>
                        <div className="bg-slate-50/50 rounded-lg p-2">
                          <p className="text-xs text-slate-500 uppercase">Final Decision</p>
                          <p className={`text-sm font-bold ${breached ? 'text-red-400' : 'text-teal-400'}`}>{finalStep.result.decision}</p>
                        </div>
                        <div className="bg-slate-50/50 rounded-lg p-2">
                          <p className="text-xs text-slate-500 uppercase">Escalation</p>
                          <p className={`text-lg font-bold ${LEVEL_META[Math.min(finalStep.result.escalation_level-1,3)].color}`}>
                            L{finalStep.result.escalation_level}
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                  <div ref={bottomRef}/>
                </>
              )}
            </div>
          </div>
        )}

        {/* Custom Vector Tab */}
        {activeTab === 'custom' && (
          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-5xl mx-auto space-y-6">
              <header className="pb-4 border-b border-slate-200">
                <h2 className="text-lg font-bold">Custom Threat Vector</h2>
                <p className="text-xs text-slate-500 mt-1">Compose any combination of attack signals and see which ML models fire.</p>
              </header>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 items-start">
                <form onSubmit={evalCustom} className="bg-white border border-slate-200 rounded-xl p-5 space-y-4">
                  <h3 className="text-sm font-bold text-slate-600 uppercase tracking-wider">Attack Parameters</h3>

                  <div className="grid grid-cols-2 gap-3">
                    {[['user_id','User ID'],['session_id','Session ID']].map(([k,l]) => (
                      <div key={k} className="space-y-1">
                        <label className="text-xs text-slate-500 font-bold uppercase">{l}</label>
                        <input value={(cp as any)[k]} onChange={e => setCp({...cp,[k]:e.target.value})}
                          className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-900 font-mono focus:outline-none focus:border-red-500/30"/>
                      </div>
                    ))}
                  </div>

                  <div className="grid grid-cols-2 gap-3">
                    <div className="space-y-1">
                      <label className="text-xs text-slate-500 font-bold uppercase">Amount ($)</label>
                      <input type="number" value={cp.amount} onChange={e => setCp({...cp, amount: parseFloat(e.target.value)||0})}
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-900 font-mono focus:outline-none focus:border-red-500/30"/>
                    </div>
                    <div className="space-y-1">
                      <label className="text-xs text-slate-500 font-bold uppercase">Phishing URL</label>
                      <input value={cp.current_url} onChange={e => setCp({...cp, current_url: e.target.value})}
                        placeholder="http://secure-bank.phish.ru/..."
                        className="w-full bg-slate-50 border border-slate-200 rounded-lg px-3 py-1.5 text-xs text-slate-900 font-mono focus:outline-none focus:border-red-500/30"/>
                    </div>
                  </div>

                  <div className="border-t border-slate-200 pt-3 space-y-2">
                    <p className="text-xs font-bold text-slate-500 uppercase">Attack Flags</p>
                    <div className="grid grid-cols-2 gap-2">
                      {[
                        ['is_new_beneficiary','New Payee'],['login_anomaly','Login Anomaly'],
                        ['new_device','New Device'],['rooted','Rooted Device'],['vpn_detected','VPN Active'],
                      ].map(([k,l]) => (
                        <label key={k} className="flex items-center gap-2 cursor-pointer">
                          <input type="checkbox" checked={(cp as any)[k]} onChange={e => setCp({...cp,[k]:e.target.checked})}
                            className="rounded border-slate-200 bg-slate-50 text-red-600 focus:ring-0"/>
                          <span className="text-sm text-slate-600 font-semibold uppercase select-none">{l}</span>
                        </label>
                      ))}
                    </div>
                  </div>

                  <button type="submit" disabled={evalLoading}
                    className="w-full py-2.5 bg-red-600 hover:bg-red-500 text-slate-900 font-bold text-xs rounded-lg uppercase tracking-wider flex items-center justify-center gap-2 transition-colors">
                    {evalLoading ? <><Loader2 size={13} className="animate-spin"/> Evaluating...</> : <><Zap size={13}/> Evaluate Threat Vector</>}
                  </button>
                </form>

                {/* Result */}
                <div className="bg-white border border-slate-200 rounded-xl p-5 space-y-4 min-h-[300px] flex flex-col">
                  <h3 className="text-sm font-bold text-slate-600 uppercase tracking-wider flex items-center gap-1.5">
                    <Activity size={12} className="text-red-400"/> Live Model Response
                  </h3>

                  {!customResult && !evalLoading && (
                    <div className="flex-1 flex items-center justify-center border border-dashed border-slate-200 rounded-xl text-slate-600 text-xs">
                      Compose vectors and fire evaluation
                    </div>
                  )}

                  {evalLoading && (
                    <div className="flex-1 flex items-center justify-center text-red-400 gap-2">
                      <Loader2 size={20} className="animate-spin"/> Running models...
                    </div>
                  )}

                  {customResult && !evalLoading && (() => {
                    const lvl = LEVEL_META[Math.min((customResult.escalation_level||1)-1,3)];
                    const LvlIcon = lvl.Icon;
                    return (
                      <div className="space-y-4">
                        <div className={`flex items-center gap-3 p-3 rounded-xl border ${lvl.bg} ${lvl.color}`}>
                          <LvlIcon size={20}/>
                          <div>
                            <p className="font-bold text-sm">{customResult.decision} — Level {customResult.escalation_level}</p>
                            <p className="text-sm opacity-70">{customResult.recommendation}</p>
                          </div>
                          <span className="ml-auto font-mono font-bold text-xl">{((customResult.overall_risk||0)*100).toFixed(0)}</span>
                        </div>

                        <div className="space-y-1">
                          <RiskBar value={customResult.overall_risk||0}/>
                          <p className="text-sm text-slate-500 italic">"{customResult.why_decision}"</p>
                        </div>

                        <div className="space-y-1.5">
                          <p className="text-xs font-bold text-slate-500 uppercase">Provider Scores</p>
                          {Object.entries(customResult.provider_breakdown||{}).map(([name, d]: [string,any]) => (
                            <div key={name} className="flex items-center gap-3">
                              <span className="text-xs text-slate-600 w-36 truncate">{name.replace('Provider','').replace('Risk','')}</span>
                              <div className="flex-1"><RiskBar value={d.risk_score||0}/></div>
                              <span className={`text-sm font-mono font-bold w-8 text-right ${d.risk_score>0.5?'text-red-400':'text-slate-500'}`}>
                                {((d.risk_score||0)*100).toFixed(0)}
                              </span>
                            </div>
                          ))}
                        </div>
                      </div>
                    );
                  })()}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
