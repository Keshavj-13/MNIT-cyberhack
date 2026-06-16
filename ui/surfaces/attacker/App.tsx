import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Flame, Gavel, User, AlertTriangle, MessageSquare, UserX, 
  Loader2, LogOut, ShieldAlert, Cpu, Terminal, Play, Plus, RefreshCw, Sliders
} from 'lucide-react';

axios.defaults.withCredentials = true;
const API_BASE = 'http://localhost:8003';

const SCENARIOS = [
  { key: 'normal_customer', label: 'Normal Customer', icon: User, color: 'text-emerald-400 border-emerald-600/30 bg-emerald-600/10 hover:bg-emerald-600/20' },
  { key: 'elderly_victim', label: 'Elderly Victim', icon: AlertTriangle, color: 'text-amber-400 border-amber-600/30 bg-amber-600/10 hover:bg-amber-600/20' },
  { key: 'smishing_victim', label: 'Smishing Victim', icon: MessageSquare, color: 'text-orange-400 border-orange-600/30 bg-orange-600/10 hover:bg-orange-600/20' },
  { key: 'account_takeover', label: 'Account Takeover', icon: UserX, color: 'text-red-400 border-red-600/30 bg-red-600/10 hover:bg-red-600/20' },
  { key: 'full_fraud_chain', label: 'Full Fraud Chain', icon: Flame, color: 'text-red-400 border-red-600/30 bg-red-600/10 hover:bg-red-600/20' },
];

export default function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  // Simulation State
  const [activeTab, setActiveTab] = useState('scenarios');
  const [runningScenario, setRunningScenario] = useState<string | null>(null);
  const [scenarioSteps, setScenarioSteps] = useState<any[]>([]);
  const [activeScenarioKey, setActiveScenarioKey] = useState<string | null>(null);

  // Custom Simulator State
  const [customPayload, setCustomPayload] = useState({
    user_id: 'sim_target',
    session_id: 'sim_sess_xyz',
    amount: 0,
    is_new_beneficiary: false,
    sms_text: '',
    url: '',
    login_anomaly: false,
    failed_attempts: 0,
    new_device: false,
    rooted: false,
    vpn_detected: false,
  });

  const [evaluationResult, setEvaluationResult] = useState<any>(null);
  const [telemetryMessage, setTelemetryMessage] = useState<string | null>(null);
  const [isEvaluating, setIsEvaluating] = useState(false);

  // Authenticate Attacker
  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username || !password) return;
    setLoading(true);
    setError('');
    try {
      await axios.post(`${API_BASE}/attacker/auth/login`, { username, password });
      setIsAuthenticated(true);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Invalid simulator credentials');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await axios.post(`${API_BASE}/attacker/auth/logout`);
    } catch (e) {}
    setIsAuthenticated(false);
    setUsername('');
    setPassword('');
    setScenarioSteps([]);
    setEvaluationResult(null);
  };

  // Check initial session
  useEffect(() => {
    axios.get(`${API_BASE}/attacker/auth/me`)
      .then(() => setIsAuthenticated(true))
      .catch(() => setIsAuthenticated(false));
  }, []);

  const runScenario = async (key: string) => {
    setRunningScenario(key);
    setActiveScenarioKey(key);
    setScenarioSteps([]);
    try {
      const res = await axios.post(`${API_BASE}/attacker/scenarios/${key}/run`);
      setScenarioSteps(res.data.steps || []);
    } catch (err) {
      console.error(err);
      alert("Scenario simulation failed");
    } finally {
      setRunningScenario(null);
    }
  };

  const handleCustomSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsEvaluating(true);
    setEvaluationResult(null);
    try {
      // Direct Evaluation returns the full model outputs
      const res = await axios.post(`${API_BASE}/attacker/evaluate/raw`, customPayload);
      setEvaluationResult(res.data);
    } catch (err) {
      console.error(err);
      alert("Evaluation failed");
    } finally {
      setIsEvaluating(false);
    }
  };

  const handleTelemetryInject = async (type: string, data: any) => {
    setTelemetryMessage(null);
    try {
      await axios.post(`${API_BASE}/attacker/simulate/event`, {
        type,
        data,
        session_id: customPayload.session_id
      });
      setTelemetryMessage(`Telemetry type '${type}' injected successfully.`);
      setTimeout(() => setTelemetryMessage(null), 5000);
    } catch (err) {
      console.error(err);
      alert("Telemetry injection failed");
    }
  };

  const LEVEL_TEXT = ['', 'text-emerald-400', 'text-amber-400', 'text-orange-400', 'text-red-500 font-bold'];

  if (!isAuthenticated) {
    return (
      <div className="flex min-h-screen bg-neutral-950 text-white font-sans items-center justify-center p-6">
        <div className="max-w-md w-full bg-neutral-900 border border-white/[0.06] rounded-xl p-8 shadow-2xl space-y-6">
          <div className="flex flex-col items-center space-y-2">
            <div className="w-12 h-12 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 grid place-items-center mb-1 animate-pulse">
              <Flame size={24} />
            </div>
            <h1 className="text-xl font-bold tracking-tight text-white uppercase">Controlled Attack Console</h1>
            <p className="text-xs text-neutral-400 text-center">
              Internal Simulation Console for Triggering Adversarial Threat Scenarios
            </p>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            {error && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-400">
                {error}
              </div>
            )}
            
            <div className="space-y-1.5">
              <label className="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Simulator ID</label>
              <input 
                type="text" 
                placeholder="attacker"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg px-4 py-2 text-xs text-white focus:outline-none focus:border-red-500/50"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Passkey</label>
              <input 
                type="password" 
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg px-4 py-2 text-xs text-white focus:outline-none focus:border-red-500/50"
              />
            </div>

            <button 
              type="submit" 
              disabled={loading}
              className="w-full py-2.5 bg-red-600 hover:bg-red-500 text-white font-bold text-xs rounded-lg transition-colors"
            >
              {loading ? 'Decrypting Console...' : 'Establish Connection'}
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
        <div className="flex items-center space-x-3 text-red-400">
          <div className="w-9 h-9 rounded-lg bg-red-500/10 border border-red-500/20 grid place-items-center">
            <Flame size={20} />
          </div>
          <div>
            <h1 className="font-bold text-base leading-tight text-white font-mono">MNIT Threat Simulator</h1>
            <p className="text-[10px] text-neutral-500 font-semibold uppercase tracking-widest font-mono">Adversarial Operations</p>
          </div>
        </div>

        <div className="flex items-center space-x-4">
          <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-3 py-1.5 rounded-full text-xs font-mono font-bold">
            Sim Namespace: Isolation Enforced (sim_*)
          </div>

          <button 
            onClick={handleLogout}
            className="flex items-center gap-1.5 bg-neutral-900 border border-white/[0.06] hover:bg-neutral-800 text-neutral-400 hover:text-white px-3 py-1.5 rounded-lg text-xs"
          >
            <LogOut size={13} />
            <span>Close Console</span>
          </button>
        </div>
      </header>

      {/* Main Container */}
      <div className="flex-1 flex overflow-hidden">
        {/* Navigation Sidebar */}
        <aside className="w-60 border-r border-white/[0.06] bg-neutral-950 flex flex-col shrink-0 p-4 space-y-1">
          <button 
            onClick={() => setActiveTab('scenarios')}
            className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
              activeTab === 'scenarios' ? 'bg-red-500/10 text-red-400' : 'text-neutral-400 hover:text-white hover:bg-white/[0.04]'
            }`}
          >
            <Gavel size={18} />
            <span>Scripted Playback</span>
          </button>
          <button 
            onClick={() => setActiveTab('custom')}
            className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
              activeTab === 'custom' ? 'bg-red-500/10 text-red-400' : 'text-neutral-400 hover:text-white hover:bg-white/[0.04]'
            }`}
          >
            <Sliders size={18} />
            <span>Custom Vectors</span>
          </button>
        </aside>

        {/* Content Panel */}
        <main className="flex-1 overflow-y-auto p-8 bg-neutral-950">
          
          {/* SCRIPTED SCENARIOS TAB */}
          {activeTab === 'scenarios' && (
            <div className="max-w-4xl mx-auto space-y-6">
              <header className="pb-4 border-b border-white/[0.06]">
                <h2 className="text-xl font-bold tracking-tight">Scripted Attack Playback</h2>
                <p className="text-xs text-neutral-500 mt-1">
                  Trigger multi-stage threat sequences. Each run registers simulation IDs to isolate threat signatures.
                </p>
              </header>

              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                {SCENARIOS.map((s) => {
                  const Icon = s.icon;
                  return (
                    <button
                      key={s.key}
                      onClick={() => runScenario(s.key)}
                      disabled={runningScenario !== null}
                      className={`flex items-center space-x-3 border rounded-xl p-4 text-left transition-colors disabled:opacity-40 border-white/[0.06] bg-neutral-900/40 text-neutral-300 ${s.color}`}
                    >
                      {runningScenario === s.key ? (
                        <Loader2 className="animate-spin text-red-500" size={20} />
                      ) : (
                        <Icon size={20} />
                      )}
                      <span className="font-semibold text-xs tracking-wider uppercase">{s.label}</span>
                    </button>
                  );
                })}
              </div>

              {activeScenarioKey && scenarioSteps.length > 0 && (
                <div className="space-y-4">
                  <h3 className="text-xs font-bold text-neutral-400 uppercase tracking-wider">
                    Replay Log: {SCENARIOS.find((s) => s.key === activeScenarioKey)?.label}
                  </h3>
                  
                  <div className="space-y-3">
                    {scenarioSteps.map((step, i) => (
                      <div key={i} className="bg-neutral-900 border border-white/[0.04] rounded-xl p-4 space-y-2">
                        <div className="flex items-center justify-between">
                          <p className="text-xs font-bold text-white">{step.label}</p>
                          <span className={`text-xs font-mono font-bold ${LEVEL_TEXT[step.result.escalation_level]}`}>
                            {step.result.decision} ({(step.result.overall_risk * 100).toFixed(0)})
                          </span>
                        </div>
                        <p className="text-xs text-neutral-400">{step.result.why_decision}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* CUSTOM ATTACK SIMULATOR */}
          {activeTab === 'custom' && (
            <div className="max-w-6xl mx-auto space-y-6">
              <header className="pb-4 border-b border-white/[0.06]">
                <h2 className="text-xl font-bold tracking-tight font-mono">Custom Threat Vector Compiler</h2>
                <p className="text-xs text-neutral-500 mt-1">
                  Compile custom payloads containing mixed vectors to analyze how the models weight threat parameters.
                </p>
              </header>

              {telemetryMessage && (
                <div className="p-4 bg-red-500/10 border border-red-500/25 rounded-lg text-xs text-red-400">
                  {telemetryMessage}
                </div>
              )}

              <div className="grid grid-cols-1 lg:grid-cols-5 gap-8 items-start">
                
                {/* Vector Compiler Panel */}
                <form onSubmit={handleCustomSubmit} className="lg:col-span-2 bg-neutral-900 border border-white/[0.06] p-6 rounded-xl space-y-4 shadow-2xl">
                  <h3 className="text-xs font-bold text-neutral-400 uppercase tracking-wider">Threat Parameters</h3>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <label className="text-[9px] font-semibold text-neutral-500 uppercase">Target User ID</label>
                      <input 
                        type="text"
                        value={customPayload.user_id}
                        onChange={(e) => setCustomPayload({ ...customPayload, user_id: e.target.value })}
                        className="w-full bg-neutral-950 border border-white/[0.08] rounded px-3 py-1.5 text-xs text-white focus:outline-none focus:border-red-500/30 font-mono"
                      />
                    </div>
                    <div className="space-y-1">
                      <label className="text-[9px] font-semibold text-neutral-500 uppercase">Target Session ID</label>
                      <input 
                        type="text"
                        value={customPayload.session_id}
                        onChange={(e) => setCustomPayload({ ...customPayload, session_id: e.target.value })}
                        className="w-full bg-neutral-950 border border-white/[0.08] rounded px-3 py-1.5 text-xs text-white focus:outline-none focus:border-red-500/30 font-mono"
                      />
                    </div>
                  </div>

                  {/* Transaction info */}
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-1">
                      <label className="text-[9px] font-semibold text-neutral-500 uppercase">Amount ($)</label>
                      <input 
                        type="number"
                        value={customPayload.amount}
                        onChange={(e) => setCustomPayload({ ...customPayload, amount: parseFloat(e.target.value) || 0 })}
                        className="w-full bg-neutral-950 border border-white/[0.08] rounded px-3 py-1.5 text-xs text-white focus:outline-none focus:border-red-500/30 font-mono"
                      />
                    </div>
                    <div className="flex items-center space-x-2 pt-5">
                      <input 
                        type="checkbox"
                        id="is_new"
                        checked={customPayload.is_new_beneficiary}
                        onChange={(e) => setCustomPayload({ ...customPayload, is_new_beneficiary: e.target.checked })}
                        className="rounded border-white/[0.08] bg-neutral-950 text-red-600 focus:ring-0"
                      />
                      <label htmlFor="is_new" className="text-[10px] font-semibold text-neutral-400 uppercase select-none">New Payee</label>
                    </div>
                  </div>

                  {/* Telemetry flags */}
                  <div className="pt-2 border-t border-white/[0.04] space-y-2">
                    <span className="text-[9px] font-bold text-neutral-500 uppercase block">Telemetry/Fingerprint Vectors</span>
                    
                    <div className="grid grid-cols-2 gap-2">
                      {[
                        { key: 'login_anomaly', label: 'Login Anomaly' },
                        { key: 'new_device', label: 'New Device' },
                        { key: 'rooted', label: 'Rooted Device' },
                        { key: 'vpn_detected', label: 'VPN Detected' },
                      ].map((item) => (
                        <div key={item.key} className="flex items-center space-x-2">
                          <input 
                            type="checkbox"
                            id={item.key}
                            checked={(customPayload as any)[item.key]}
                            onChange={(e) => setCustomPayload({ ...customPayload, [item.key]: e.target.checked })}
                            className="rounded border-white/[0.08] bg-neutral-950 text-red-600 focus:ring-0"
                          />
                          <label htmlFor={item.key} className="text-[10px] font-semibold text-neutral-400 uppercase select-none">{item.label}</label>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Text inputs for smishing / phishing */}
                  <div className="pt-2 border-t border-white/[0.04] space-y-3">
                    <div className="space-y-1">
                      <label className="text-[9px] font-semibold text-neutral-500 uppercase block">Smishing SMS Payload</label>
                      <div className="flex gap-2">
                        <input 
                          type="text"
                          placeholder="e.g. URGENT: verify account at..."
                          value={customPayload.sms_text}
                          onChange={(e) => setCustomPayload({ ...customPayload, sms_text: e.target.value })}
                          className="flex-1 bg-neutral-950 border border-white/[0.08] rounded px-3 py-1.5 text-xs text-white focus:outline-none focus:border-red-500/30"
                        />
                        <button 
                          type="button"
                          disabled={!customPayload.sms_text}
                          onClick={() => handleTelemetryInject('session', { type: 'sms_received', sms_text: customPayload.sms_text })}
                          className="px-2.5 bg-neutral-800 border border-white/[0.06] hover:bg-neutral-700 text-neutral-300 rounded text-[10px] uppercase font-bold"
                          title="Inject telemetry log directly"
                        >
                          Inject
                        </button>
                      </div>
                    </div>

                    <div className="space-y-1">
                      <label className="text-[9px] font-semibold text-neutral-500 uppercase block">Phishing URL Clicked</label>
                      <div className="flex gap-2">
                        <input 
                          type="text"
                          placeholder="e.g. secure-bank.com"
                          value={customPayload.url}
                          onChange={(e) => setCustomPayload({ ...customPayload, url: e.target.value })}
                          className="flex-1 bg-neutral-950 border border-white/[0.08] rounded px-3 py-1.5 text-xs text-white focus:outline-none focus:border-red-500/30"
                        />
                        <button 
                          type="button"
                          disabled={!customPayload.url}
                          onClick={() => handleTelemetryInject('session', { type: 'link_clicked', url: customPayload.url })}
                          className="px-2.5 bg-neutral-800 border border-white/[0.06] hover:bg-neutral-700 text-neutral-300 rounded text-[10px] uppercase font-bold"
                        >
                          Inject
                        </button>
                      </div>
                    </div>
                  </div>

                  <button 
                    type="submit"
                    disabled={isEvaluating}
                    className="w-full py-3 bg-red-600 hover:bg-red-500 text-white font-bold text-xs rounded-lg transition-colors uppercase tracking-wider flex items-center justify-center gap-1.5"
                  >
                    {isEvaluating ? (
                      <>
                        <Loader2 className="animate-spin" size={14} />
                        <span>Evaluating...</span>
                      </>
                    ) : (
                      <>
                        <Play size={12} />
                        <span>Evaluate Threat Payload</span>
                      </>
                    )}
                  </button>
                </form>

                {/* Response Inspection Output */}
                <div className="lg:col-span-3 bg-neutral-900 border border-white/[0.06] p-6 rounded-xl space-y-4 shadow-2xl flex flex-col h-full min-h-[500px]">
                  <h3 className="text-xs font-bold text-neutral-400 uppercase tracking-wider flex items-center gap-1.5">
                    <Terminal size={14} className="text-red-400" />
                    <span>Raw Model Outputs & Explanation</span>
                  </h3>
                  
                  {evaluationResult ? (
                    <div className="flex-1 flex flex-col space-y-4 overflow-hidden">
                      <div className="grid grid-cols-3 gap-4 font-mono text-center">
                        <div className="bg-neutral-950 p-3 rounded border border-white/[0.02]">
                          <span className="text-[9px] text-neutral-500 uppercase block">Threat Index</span>
                          <span className="text-base font-bold text-red-400">{(evaluationResult.overall_risk * 100).toFixed(1)}/100</span>
                        </div>
                        <div className="bg-neutral-950 p-3 rounded border border-white/[0.02]">
                          <span className="text-[9px] text-neutral-500 uppercase block">Agreement</span>
                          <span className="text-base font-bold text-neutral-300">{(evaluationResult.confidence * 100).toFixed(0)}%</span>
                        </div>
                        <div className="bg-neutral-950 p-3 rounded border border-white/[0.02]">
                          <span className="text-[9px] text-neutral-500 uppercase block">Escalation</span>
                          <span className="text-base font-bold text-red-500">v{evaluationResult.escalation_level}</span>
                        </div>
                      </div>

                      <div className="bg-neutral-950 p-3.5 border border-white/[0.02] rounded-lg text-xs font-sans space-y-1">
                        <span className="text-[10px] font-bold text-neutral-500 uppercase">Risk Narrative</span>
                        <p className="text-neutral-300 italic">"{evaluationResult.why_decision}"</p>
                      </div>

                      <pre className="flex-1 bg-neutral-950 p-4 border border-white/[0.02] rounded-lg font-mono text-[10px] text-red-400 overflow-auto select-all">
                        {JSON.stringify(evaluationResult, null, 2)}
                      </pre>
                    </div>
                  ) : (
                    <div className="flex-1 flex flex-col items-center justify-center border border-dashed border-white/[0.04] rounded-xl text-neutral-500 text-xs">
                      No active evaluations loaded. Compile vectors and trigger direct evaluation.
                    </div>
                  )}

                </div>

              </div>
            </div>
          )}

        </main>
      </div>
    </div>
  );
}
