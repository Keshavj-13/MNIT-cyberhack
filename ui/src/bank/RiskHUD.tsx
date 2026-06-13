import { useEffect, useState } from 'react';
import { ShieldCheck, AlertCircle, ShieldAlert, Skull, RotateCcw } from 'lucide-react';
import { getTimeline } from './api';

const LEVELS = [
  { name: 'ALLOW', icon: ShieldCheck, badge: 'border-emerald-600/30 bg-emerald-600/10', text: 'text-emerald-400', bar: 'bg-emerald-500' },
  { name: 'CHALLENGE', icon: AlertCircle, badge: 'border-amber-600/30 bg-amber-600/10', text: 'text-amber-400', bar: 'bg-amber-500' },
  { name: 'RESTRICT', icon: ShieldAlert, badge: 'border-orange-600/30 bg-orange-600/10', text: 'text-orange-400', bar: 'bg-orange-500' },
  { name: 'CONTAIN', icon: Skull, badge: 'border-red-600/30 bg-red-600/10', text: 'text-red-400', bar: 'bg-red-500' },
];

interface RiskHUDProps {
  sessionId: string;
  latest: any | null;
  onReset: () => void;
  refreshKey: number;
}

const RiskHUD = ({ sessionId, latest, onReset, refreshKey }: RiskHUDProps) => {
  const [timeline, setTimeline] = useState<any[]>([]);

  useEffect(() => {
    getTimeline(sessionId, 8).then(setTimeline).catch(() => {});
  }, [sessionId, refreshKey]);

  const level = latest ? LEVELS[Math.max(0, Math.min(3, latest.escalation_level - 1))] : LEVELS[0];
  const Icon = level.icon;
  const risk = latest ? latest.overall_risk : 0;

  return (
    <div className="w-full lg:w-80 border-l border-slate-800 flex flex-col p-5 space-y-5 bg-slate-950/60 overflow-y-auto shrink-0">
      <div className="flex items-center justify-between">
        <h3 className="font-bold text-sm uppercase tracking-wide text-slate-400">Live Risk HUD</h3>
        <button
          onClick={onReset}
          className="flex items-center space-x-1 text-xs text-slate-500 hover:text-white transition-colors"
          title="Reset demo session"
        >
          <RotateCcw size={14} />
          <span>Reset</span>
        </button>
      </div>

      <div className={`rounded-xl border ${level.badge} p-4`}>
        <div className="flex items-center space-x-2">
          <Icon className={level.text} size={20} />
          <span className={`font-bold uppercase tracking-widest ${level.text}`}>{level.name}</span>
        </div>
        <div className="mt-3 w-full bg-slate-800 h-2 rounded-full overflow-hidden">
          <div
            className={`h-full ${level.bar} transition-all duration-700`}
            style={{ width: `${Math.round(risk * 100)}%` }}
          />
        </div>
        <div className="mt-1 text-xs text-slate-400 font-mono">
          Risk score: {(risk * 100).toFixed(1)} / 100
        </div>
        {latest && (
          <div className="mt-1 text-xs text-slate-400 font-mono">
            Confidence: {(latest.confidence * 100).toFixed(1)}%
          </div>
        )}
      </div>

      {latest && (
        <div className="text-sm text-slate-300 bg-slate-900 border border-slate-800 rounded-xl p-3 leading-relaxed">
          {latest.why_decision}
        </div>
      )}

      {latest && (
        <div className="text-xs text-slate-400 bg-slate-900 border border-slate-800 rounded-xl p-3">
          <div className="font-bold text-slate-500 uppercase mb-1">Recommendation</div>
          {latest.recommendation}
        </div>
      )}

      <div className="space-y-2">
        <h4 className="text-xs font-bold text-slate-500 uppercase">Attack Chain Timeline</h4>
        {timeline.length === 0 && (
          <div className="text-xs text-slate-600 italic">No activity yet. Start interacting with the bank app.</div>
        )}
        {timeline.map((e) => {
          const lvl = LEVELS[Math.max(0, Math.min(3, (e.level || 1) - 1))];
          return (
            <div key={e.id} className="text-xs border-l-2 pl-2 py-0.5" style={{ borderColor: 'currentColor' }}>
              <div className={`flex justify-between ${lvl.text}`}>
                <span className="text-slate-500">{new Date(e.timestamp).toLocaleTimeString()}</span>
                <span className="font-mono">{(e.overall_risk * 100).toFixed(0)}</span>
              </div>
              <div className="text-slate-300">
                {e.event_category} &rarr; <span className={lvl.text}>{e.decision}</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default RiskHUD;
