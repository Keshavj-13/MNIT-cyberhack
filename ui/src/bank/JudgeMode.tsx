import { useState } from 'react';
import { Gavel, User, AlertTriangle, MessageSquare, UserX, Flame, Loader2 } from 'lucide-react';
import { runJudgeScenario } from './api';

const SCENARIOS = [
  { key: 'normal_customer', label: 'Normal Customer', icon: User, color: 'text-emerald-400 border-emerald-600/30 bg-emerald-600/10' },
  { key: 'elderly_victim', label: 'Elderly Victim', icon: AlertTriangle, color: 'text-amber-400 border-amber-600/30 bg-amber-600/10' },
  { key: 'smishing_victim', label: 'Smishing Victim', icon: MessageSquare, color: 'text-orange-400 border-orange-600/30 bg-orange-600/10' },
  { key: 'account_takeover', label: 'Account Takeover', icon: UserX, color: 'text-red-400 border-red-600/30 bg-red-600/10' },
  { key: 'full_fraud_chain', label: 'Full Fraud Chain', icon: Flame, color: 'text-red-400 border-red-600/30 bg-red-600/10' },
];

const LEVEL_TEXT = ['', 'text-emerald-400', 'text-amber-400', 'text-orange-400', 'text-red-400'];

interface JudgeModeProps {
  onScenarioRun: (sessionId: string, latest: any) => void;
}

const JudgeMode = ({ onScenarioRun }: JudgeModeProps) => {
  const [running, setRunning] = useState<string | null>(null);
  const [activeScenario, setActiveScenario] = useState<string | null>(null);
  const [steps, setSteps] = useState<any[]>([]);

  const run = async (key: string) => {
    setRunning(key);
    setActiveScenario(key);
    setSteps([]);
    try {
      const data = await runJudgeScenario(key);
      setSteps(data.steps);
      const last = data.steps[data.steps.length - 1]?.result;
      onScenarioRun(data.user_id, last);
    } catch (err) {
      console.error(err);
    } finally {
      setRunning(null);
    }
  };

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      <h2 className="text-lg font-bold text-white flex items-center space-x-2">
        <Gavel size={20} />
        <span>Judge Mode — Scripted Attack Chains</span>
      </h2>
      <p className="text-sm text-slate-400">
        Run a complete, server-scripted user journey through the Risk Engine in one click. Each scenario uses a
        fresh isolated session and replays through <code className="text-slate-300">/evaluate</code> step by step.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {SCENARIOS.map((s) => {
          const Icon = s.icon;
          return (
            <button
              key={s.key}
              onClick={() => run(s.key)}
              disabled={running !== null}
              className={`flex items-center space-x-3 border rounded-xl p-4 text-left transition-colors disabled:opacity-50 ${s.color} hover:brightness-125`}
            >
              {running === s.key ? <Loader2 className="animate-spin" size={20} /> : <Icon size={20} />}
              <span className="font-semibold">{s.label}</span>
            </button>
          );
        })}
      </div>

      {activeScenario && steps.length > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-bold text-slate-400 uppercase">
            Replay: {SCENARIOS.find((s) => s.key === activeScenario)?.label}
          </h3>
          {steps.map((step, i) => (
            <div key={i} className="bg-slate-900 border border-slate-800 rounded-xl p-3">
              <div className="flex items-center justify-between">
                <p className="text-sm text-slate-200">{step.label}</p>
                <span className={`text-xs font-mono font-bold ${LEVEL_TEXT[step.result.escalation_level]}`}>
                  {step.result.decision} ({(step.result.overall_risk * 100).toFixed(0)})
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-1">{step.result.why_decision}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default JudgeMode;
