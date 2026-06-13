import { ShieldAlert, ShieldCheck, AlertCircle, Skull, Activity } from 'lucide-react';

const RiskDashboard = ({ result }: { result: any }) => {
  if (!result) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-slate-500 space-y-4">
        <Activity size={64} className="opacity-20 animate-pulse" />
        <p className="text-lg">No active evaluation. Use the Playground to simulate an event.</p>
      </div>
    );
  }

  const levels = [
    { name: 'MONITOR', color: 'bg-emerald-500', icon: ShieldCheck },
    { name: 'CHALLENGE', color: 'bg-amber-500', icon: AlertCircle },
    { name: 'RESTRICT', color: 'bg-orange-600', icon: ShieldAlert },
    { name: 'CONTAINMENT', color: 'bg-red-600', icon: Skull }
  ];

  const currentLevel = levels[result.escalation_level - 1];
  const Icon = currentLevel.icon;

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      <header className="flex justify-between items-start">
        <div>
          <h1 className="text-3xl font-bold">Risk Assessment</h1>
          <p className="text-slate-400 mt-1">Real-time fraud analysis and escalation status.</p>
        </div>
        <div className={`flex items-center space-x-3 px-6 py-3 rounded-xl border ${currentLevel.color.replace('bg-', 'border-')} ${currentLevel.color}/10`}>
          <Icon className={currentLevel.color.replace('bg-', 'text-')} size={24} />
          <span className="font-bold text-xl uppercase tracking-widest">{currentLevel.name}</span>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl">
          <span className="text-slate-400 text-sm font-medium">Overall Risk Score</span>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-5xl font-bold text-white">{(result.overall_risk * 100).toFixed(1)}</span>
            <span className="text-slate-600">/ 100</span>
          </div>
          <div className="mt-4 w-full bg-slate-800 h-2 rounded-full overflow-hidden">
             <div 
               className={`h-full transition-all duration-1000 ${currentLevel.color}`} 
               style={{ width: `${result.overall_risk * 100}%` }}
             ></div>
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl">
          <span className="text-slate-400 text-sm font-medium">Confidence Level</span>
          <div className="mt-2 flex items-baseline space-x-2">
            <span className="text-5xl font-bold text-white">{(result.confidence * 100).toFixed(1)}%</span>
          </div>
          <p className="mt-4 text-xs text-slate-500 uppercase tracking-tighter">Model Agreement across providers</p>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-6 rounded-2xl">
          <span className="text-slate-400 text-sm font-medium">Decision</span>
          <div className="mt-2 text-2xl font-bold flex items-center space-x-2">
             <span className={result.decision === 'ALLOW' ? 'text-emerald-400' : 'text-rose-400'}>{result.decision}</span>
          </div>
          <p className="mt-2 text-sm text-slate-300 font-medium italic">"{result.recommendation}"</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
          <h2 className="text-lg font-bold mb-4">Provider Breakdown</h2>
          <div className="space-y-4">
            {Object.entries(result.provider_breakdown).map(([name, data]: [string, any]) => (
              <div key={name} className="flex items-center justify-between p-3 border-b border-slate-800/50 last:border-0">
                <div>
                  <div className="font-medium">{name}</div>
                  <div className="text-xs text-slate-500">{data.explanations[0] || 'No specific threat detected.'}</div>
                </div>
                <div className="flex flex-col items-end">
                   <span className={`text-sm font-mono ${data.risk_score > 0.5 ? 'text-orange-400' : 'text-slate-400'}`}>
                     {(data.risk_score * 100).toFixed(0)}
                   </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
          <h2 className="text-lg font-bold mb-4 flex items-center space-x-2">
            <ShieldAlert size={20} className="text-blue-500" />
            <span>Reason for Decision</span>
          </h2>
          <div className="p-4 bg-slate-950/50 rounded-xl border border-slate-800 text-slate-300 leading-relaxed">
            {result.why_decision}
          </div>
          <div className="mt-6 space-y-2">
            <span className="text-xs font-bold text-slate-600 uppercase">Top Risk Factors</span>
            <div className="flex flex-wrap gap-2 pt-1">
              {Object.values(result.provider_breakdown).flatMap((p: any) => p.explanations).filter(e => !e.includes("active")).map((e, idx) => (
                <span key={idx} className="bg-blue-900/20 text-blue-400 border border-blue-800/30 px-3 py-1 rounded-full text-xs font-medium">
                  {e}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default RiskDashboard;
