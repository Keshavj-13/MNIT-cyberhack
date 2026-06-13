import { useState } from 'react';
import { Lock, ShieldQuestion, Smartphone, Globe, RefreshCcw, AlertTriangle } from 'lucide-react';
import { evaluate } from './api';

interface LoginScreenProps {
  sessionId: string;
  onResult: (result: any) => void;
  onLogin: () => void;
}

const LoginScreen = ({ sessionId, onResult, onLogin }: LoginScreenProps) => {
  const [username, setUsername] = useState('rajesh.kumar');
  const [password, setPassword] = useState('••••••••••');
  const [loading, setLoading] = useState(false);
  const [advanced, setAdvanced] = useState(false);

  const [loginAnomaly, setLoginAnomaly] = useState(false);
  const [newDevice, setNewDevice] = useState(false);
  const [vpnDetected, setVpnDetected] = useState(false);
  const [rooted, setRooted] = useState(false);
  const [failedAttempts, setFailedAttempts] = useState(0);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const payload: Record<string, any> = {};
      if (loginAnomaly) payload.login_anomaly = true;
      if (newDevice) payload.new_device = true;
      if (vpnDetected) payload.vpn_detected = true;
      if (rooted) payload.rooted = true;
      if (failedAttempts > 0) payload.failed_attempts = failedAttempts;

      const result = await evaluate(payload, sessionId);
      onResult(result);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
      onLogin();
    }
  };

  return (
    <div className="flex items-center justify-center min-h-[70vh] p-6">
      <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-2xl p-8 shadow-xl">
        <div className="flex items-center justify-center mb-6 space-x-2">
          <div className="bg-blue-600 rounded-xl p-2">
            <Lock className="text-white" size={22} />
          </div>
          <h1 className="text-xl font-bold text-white">SecureTrust Bank</h1>
        </div>
        <p className="text-center text-slate-400 text-sm mb-6">Sign in to access your account</p>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Username</label>
            <input
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
          </div>
          <div>
            <label className="block text-xs font-medium text-slate-400 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-600"
            />
          </div>

          <button
            type="button"
            onClick={() => setAdvanced(!advanced)}
            className="flex items-center space-x-1 text-xs text-slate-500 hover:text-slate-300"
          >
            <ShieldQuestion size={14} />
            <span>{advanced ? 'Hide' : 'Show'} session diagnostics (demo controls)</span>
          </button>

          {advanced && (
            <div className="bg-slate-950 border border-slate-800 rounded-lg p-3 space-y-2 text-xs text-slate-400">
              <p className="text-slate-500">
                Simulate signals an attacker session might exhibit (impossible travel, new/rooted device, VPN).
              </p>
              <label className="flex items-center space-x-2">
                <input type="checkbox" checked={loginAnomaly} onChange={(e) => setLoginAnomaly(e.target.checked)} />
                <span className="flex items-center space-x-1"><Globe size={12} /><span>Login anomaly (impossible travel)</span></span>
              </label>
              <label className="flex items-center space-x-2">
                <input type="checkbox" checked={newDevice} onChange={(e) => setNewDevice(e.target.checked)} />
                <span className="flex items-center space-x-1"><Smartphone size={12} /><span>New / unrecognized device</span></span>
              </label>
              <label className="flex items-center space-x-2">
                <input type="checkbox" checked={vpnDetected} onChange={(e) => setVpnDetected(e.target.checked)} />
                <span className="flex items-center space-x-1"><RefreshCcw size={12} /><span>VPN detected</span></span>
              </label>
              <label className="flex items-center space-x-2">
                <input type="checkbox" checked={rooted} onChange={(e) => setRooted(e.target.checked)} />
                <span className="flex items-center space-x-1"><AlertTriangle size={12} /><span>Rooted / jailbroken device</span></span>
              </label>
              <label className="flex items-center justify-between">
                <span>Failed login attempts</span>
                <input
                  type="number"
                  min={0}
                  max={10}
                  value={failedAttempts}
                  onChange={(e) => setFailedAttempts(parseInt(e.target.value) || 0)}
                  className="w-16 bg-slate-800 border border-slate-700 rounded px-2 py-1 text-white"
                />
              </label>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-semibold py-2 rounded-lg transition-colors"
          >
            {loading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>
      </div>
    </div>
  );
};

export default LoginScreen;
