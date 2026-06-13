import { Clock, CheckCircle, XCircle, AlertTriangle } from 'lucide-react';

const Timeline = ({ events }: { events: any[] }) => {
  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-3xl font-bold">Decision Timeline</h1>
        <p className="text-slate-400 mt-1">Audit log of system evaluations and escalations.</p>
      </header>

      <div className="bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="bg-slate-950/50 border-b border-slate-800">
              <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase">Timestamp</th>
              <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase">Risk</th>
              <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase">Decision</th>
              <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase">Level</th>
              <th className="px-6 py-4 text-xs font-bold text-slate-500 uppercase">Recommendation</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/50">
            {events.map((e, idx) => (
              <tr key={e.id} className="hover:bg-slate-800/20 transition group">
                <td className="px-6 py-4">
                  <div className="flex items-center space-x-2 text-slate-400 text-sm">
                    <Clock size={14} />
                    <span>{new Date(e.timestamp).toLocaleTimeString()}</span>
                  </div>
                </td>
                <td className="px-6 py-4">
                  <span className={`font-mono font-bold ${e.overall_risk > 0.7 ? 'text-red-400' : e.overall_risk > 0.4 ? 'text-orange-400' : 'text-emerald-400'}`}>
                    {(e.overall_risk * 100).toFixed(1)}
                  </span>
                </td>
                <td className="px-6 py-4">
                   <div className="flex items-center space-x-2">
                     {e.decision === 'ALLOW' ? <CheckCircle size={16} className="text-emerald-500" /> : e.decision === 'CONTAIN' ? <XCircle size={16} className="text-red-500" /> : <AlertTriangle size={16} className="text-amber-500" />}
                     <span className={`font-bold text-sm ${e.decision === 'ALLOW' ? 'text-emerald-500' : e.decision === 'CONTAIN' ? 'text-red-500' : 'text-amber-500'}`}>
                       {e.decision}
                     </span>
                   </div>
                </td>
                <td className="px-6 py-4">
                   <div className="flex items-center space-x-1">
                     {[1,2,3,4].map(l => (
                       <div key={l} className={`h-1.5 w-4 rounded-full ${l <= e.level ? (e.level === 4 ? 'bg-red-500' : e.level === 3 ? 'bg-orange-500' : e.level === 2 ? 'bg-amber-500' : 'bg-emerald-500') : 'bg-slate-800'}`}></div>
                     ))}
                   </div>
                </td>
                <td className="px-6 py-4 text-sm text-slate-300">
                  {e.recommendation}
                </td>
              </tr>
            ))}
            {events.length === 0 && (
              <tr>
                <td colSpan={5} className="px-6 py-12 text-center text-slate-500 italic">
                  No events logged in the database yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default Timeline;
