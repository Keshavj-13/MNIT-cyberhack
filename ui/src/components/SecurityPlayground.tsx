import { useState, useEffect } from 'react';
import axios from 'axios';
import { Send, Play, Zap, ShieldAlert, Ghost, UserCheck, Terminal } from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_BASE || "http://localhost:8080";

const SecurityPlayground = ({ onEvaluate }: { onEvaluate: (res: any) => void }) => {
  const [scenarios, setScenarios] = useState<any>({});
  const [payload, setPayload] = useState<any>({
    amount: 0,
    url: "",
    sms_text: "",
    login_anomaly: false,
    new_device: false,
    failed_attempts: 0,
    is_new_beneficiary: false,
    vpn_detected: false,
    rooted: false
  });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    axios.get(`${API_BASE}/scenarios`).then(res => setScenarios(res.data));
  }, []);

  const handleInputChange = (field: string, value: any) => {
    setPayload({ ...payload, [field]: value });
  };

  const runEvaluation = async (currentPayload = payload) => {
    setLoading(true);
    try {
      const res = await axios.post(`${API_BASE}/evaluate`, currentPayload);
      onEvaluate(res.data);
    } catch (err) {
      console.error(err);
      alert("Evaluation failed. Is the backend running?");
    } finally {
      setLoading(false);
    }
  };

  const loadScenario = (name: string) => {
    const s = scenarios[name];
    if (s) {
      const newPayload = { ...payload, ...s };
      setPayload(newPayload);
      runEvaluation(newPayload);
    }
  };

  return (
    <div className="space-y-8 animate-in slide-in-from-bottom-4 duration-500">
      <header>
        <h1 className="text-3xl font-bold">Security Playground</h1>
        <p className="text-slate-400 mt-1">Simulate attack vectors and test risk accumulation.</p>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Scenario Selection */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
            <h2 className="text-lg font-bold mb-4 flex items-center space-x-2">
              <Zap size={20} className="text-yellow-500" />
              <span>Quick Scenarios</span>
            </h2>
            <div className="space-y-3">
              <button 
                onClick={() => loadScenario('normal')}
                className="w-full flex items-center justify-between p-4 bg-slate-950 border border-slate-800 rounded-xl hover:border-emerald-500/50 transition group"
              >
                <div className="flex items-center space-x-3">
                  <UserCheck className="text-emerald-500" size={20} />
                  <span className="font-medium text-slate-200">Normal User</span>
                </div>
                <Play size={16} className="text-slate-600 group-hover:text-emerald-500" />
              </button>
              
              <button 
                onClick={() => loadScenario('suspicious_tx')}
                className="w-full flex items-center justify-between p-4 bg-slate-950 border border-slate-800 rounded-xl hover:border-amber-500/50 transition group"
              >
                <div className="flex items-center space-x-3">
                  <ShieldAlert className="text-amber-500" size={20} />
                  <span className="font-medium text-slate-200">Suspicious Transfer</span>
                </div>
                <Play size={16} className="text-slate-600 group-hover:text-amber-500" />
              </button>

              <button 
                onClick={() => loadScenario('smishing')}
                className="w-full flex items-center justify-between p-4 bg-slate-950 border border-slate-800 rounded-xl hover:border-orange-500/50 transition group"
              >
                <div className="flex items-center space-x-3">
                  <Ghost className="text-orange-500" size={20} />
                  <span className="font-medium text-slate-200">Smishing Attack</span>
                </div>
                <Play size={16} className="text-slate-600 group-hover:text-orange-500" />
              </button>

              <button 
                onClick={() => loadScenario('full_attack')}
                className="w-full flex items-center justify-between p-4 bg-slate-950 border border-red-900/30 rounded-xl hover:border-red-500 transition group"
              >
                <div className="flex items-center space-x-3">
                  <ShieldAlert className="text-red-500" size={20} />
                  <span className="font-medium text-slate-200 text-red-100">Full Attack Chain</span>
                </div>
                <Play size={16} className="text-slate-600 group-hover:text-red-500" />
              </button>
            </div>
          </div>
        </div>

        {/* Manual Controls */}
        <div className="lg:col-span-2 bg-slate-900 border border-slate-800 rounded-2xl p-8">
          <h2 className="text-xl font-bold mb-6 flex items-center space-x-2">
            <Terminal size={24} className="text-blue-500" />
            <span>Manual Vector Injection</span>
          </h2>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-6">
            <div className="space-y-4">
               <div>
                 <label className="block text-xs font-bold text-slate-500 uppercase mb-2">Transaction Amount ($)</label>
                 <input 
                   type="number" 
                   value={payload.amount}
                   onChange={(e) => handleInputChange('amount', e.target.value)}
                   className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2 focus:border-blue-500 outline-none transition"
                 />
               </div>
               <div>
                 <label className="block text-xs font-bold text-slate-500 uppercase mb-2">Incoming SMS Content</label>
                 <textarea 
                   rows={3}
                   value={payload.sms_text}
                   onChange={(e) => handleInputChange('sms_text', e.target.value)}
                   className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2 focus:border-blue-500 outline-none transition text-sm"
                   placeholder="Enter message text..."
                 />
               </div>
               <div>
                 <label className="block text-xs font-bold text-slate-500 uppercase mb-2">Visited URL</label>
                 <input 
                   type="text" 
                   value={payload.url}
                   onChange={(e) => handleInputChange('url', e.target.value)}
                   className="w-full bg-slate-950 border border-slate-800 rounded-lg px-4 py-2 focus:border-blue-500 outline-none transition text-sm"
                   placeholder="e.g. bank-verify.com"
                 />
               </div>
            </div>

            <div className="space-y-4">
              <label className="block text-xs font-bold text-slate-500 uppercase">Risk Indicators</label>
              
              <div className="space-y-3">
                {[
                  { id: 'login_anomaly', label: 'Login Anomaly (Geo-jump)' },
                  { id: 'new_device', label: 'Unrecognized Device' },
                  { id: 'is_new_beneficiary', label: 'New Beneficiary Target' },
                  { id: 'vpn_detected', label: 'VPN Usage Detected' },
                  { id: 'rooted', label: 'Device is Rooted/Compromised' }
                ].map(flag => (
                  <label key={flag.id} className="flex items-center space-x-3 cursor-pointer group">
                    <input 
                      type="checkbox" 
                      checked={payload[flag.id]}
                      onChange={(e) => handleInputChange(flag.id, e.target.checked)}
                      className="w-5 h-5 rounded border-slate-800 bg-slate-950 text-blue-600 focus:ring-blue-500 focus:ring-offset-slate-950" 
                    />
                    <span className="text-slate-300 group-hover:text-white transition">{flag.label}</span>
                  </label>
                ))}
              </div>

              <div className="pt-4">
                 <label className="block text-xs font-bold text-slate-500 uppercase mb-2">Failed Login Attempts</label>
                 <input 
                   type="range" min="0" max="10"
                   value={payload.failed_attempts}
                   onChange={(e) => handleInputChange('failed_attempts', parseInt(e.target.value))}
                   className="w-full accent-blue-500"
                 />
                 <div className="text-right text-sm text-slate-400 mt-1 font-mono">{payload.failed_attempts}</div>
              </div>
            </div>
          </div>

          <div className="mt-12 flex justify-end">
            <button 
              disabled={loading}
              onClick={() => runEvaluation()}
              className="bg-blue-600 hover:bg-blue-500 text-white font-bold py-4 px-10 rounded-xl flex items-center space-x-3 shadow-lg shadow-blue-900/20 transition-all disabled:opacity-50"
            >
              <Send size={20} />
              <span>{loading ? 'ANALYZING...' : 'RUN RISK EVALUATION'}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default SecurityPlayground;
