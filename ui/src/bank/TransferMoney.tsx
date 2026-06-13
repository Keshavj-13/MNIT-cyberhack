import { useState } from 'react';
import { Send, CheckCircle2, ShieldAlert, Ban, KeyRound } from 'lucide-react';
import { evaluate } from './api';
import type { Beneficiary } from './BeneficiaryManagement';

interface TransferMoneyProps {
  sessionId: string;
  beneficiaries: Beneficiary[];
  onResult: (result: any) => void;
}

const TransferMoney = ({ sessionId, beneficiaries, onResult }: TransferMoneyProps) => {
  const [amount, setAmount] = useState('5000');
  const [beneficiaryId, setBeneficiaryId] = useState(beneficiaries[0]?.id ?? '');
  const [loading, setLoading] = useState(false);
  const [outcome, setOutcome] = useState<any | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const beneficiary = beneficiaries.find((b) => b.id === beneficiaryId);
    if (!beneficiary) return;

    setLoading(true);
    setOutcome(null);
    try {
      const result = await evaluate(
        { amount: parseFloat(amount) || 0, is_new_beneficiary: beneficiary.isNew },
        sessionId
      );
      onResult(result);
      setOutcome(result);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  const renderOutcome = () => {
    if (!outcome) return null;
    const level = outcome.escalation_level;
    if (level >= 3) {
      return (
        <div className="mt-4 flex items-start space-x-2 bg-red-500/10 border border-red-600/30 rounded-lg p-3 text-red-300 text-sm">
          <Ban size={18} className="shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Transfer blocked.</p>
            <p className="text-xs mt-1">{outcome.recommendation}</p>
          </div>
        </div>
      );
    }
    if (level === 2) {
      return (
        <div className="mt-4 flex items-start space-x-2 bg-amber-500/10 border border-amber-600/30 rounded-lg p-3 text-amber-300 text-sm">
          <KeyRound size={18} className="shrink-0 mt-0.5" />
          <div>
            <p className="font-semibold">Step-up verification required.</p>
            <p className="text-xs mt-1">{outcome.recommendation}</p>
          </div>
        </div>
      );
    }
    return (
      <div className="mt-4 flex items-start space-x-2 bg-emerald-500/10 border border-emerald-600/30 rounded-lg p-3 text-emerald-300 text-sm">
        <CheckCircle2 size={18} className="shrink-0 mt-0.5" />
        <div>
          <p className="font-semibold">Transfer completed successfully.</p>
          <p className="text-xs mt-1">{outcome.recommendation}</p>
        </div>
      </div>
    );
  };

  return (
    <div className="p-6 max-w-md mx-auto">
      <h2 className="text-lg font-bold text-white mb-4 flex items-center space-x-2">
        <Send size={20} />
        <span>Transfer Money</span>
      </h2>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 space-y-4">
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">Beneficiary</label>
          <select
            value={beneficiaryId}
            onChange={(e) => setBeneficiaryId(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-600"
          >
            {beneficiaries.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name} ({b.account}){b.isNew ? ' — New payee' : ''}
              </option>
            ))}
          </select>
        </div>
        <div>
          <label className="block text-xs font-medium text-slate-400 mb-1">Amount (₹)</label>
          <input
            type="number"
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-600"
          />
        </div>

        {beneficiaries.find((b) => b.id === beneficiaryId)?.isNew && (
          <div className="flex items-center space-x-2 text-xs text-amber-400 bg-amber-500/10 border border-amber-600/30 rounded-lg p-2">
            <ShieldAlert size={14} />
            <span>This is a newly added beneficiary — transfers carry additional risk weight.</span>
          </div>
        )}

        <button
          onClick={handleSubmit}
          disabled={loading || !beneficiaryId}
          className="w-full flex items-center justify-center space-x-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white font-semibold py-2 rounded-lg transition-colors"
        >
          <Send size={16} />
          <span>{loading ? 'Processing…' : 'Send Transfer'}</span>
        </button>

        {renderOutcome()}
      </div>
    </div>
  );
};

export default TransferMoney;
