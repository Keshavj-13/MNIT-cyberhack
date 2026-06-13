import { useState } from 'react';
import { Users, Plus, BadgeCheck, Sparkles } from 'lucide-react';

export interface Beneficiary {
  id: string;
  name: string;
  account: string;
  isNew: boolean;
}

interface BeneficiaryManagementProps {
  beneficiaries: Beneficiary[];
  onAdd: (b: Beneficiary) => void;
}

const BeneficiaryManagement = ({ beneficiaries, onAdd }: BeneficiaryManagementProps) => {
  const [name, setName] = useState('');
  const [account, setAccount] = useState('');

  const handleAdd = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim() || !account.trim()) return;
    onAdd({
      id: `b_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`,
      name: name.trim(),
      account: account.trim(),
      isNew: true,
    });
    setName('');
    setAccount('');
  };

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      <h2 className="text-lg font-bold text-white flex items-center space-x-2">
        <Users size={20} />
        <span>Beneficiary Management</span>
      </h2>

      <div className="space-y-2">
        {beneficiaries.map((b) => (
          <div key={b.id} className="flex items-center justify-between bg-slate-900 border border-slate-800 rounded-xl p-3">
            <div>
              <p className="text-sm text-slate-200">{b.name}</p>
              <p className="text-xs text-slate-500 font-mono">{b.account}</p>
            </div>
            {b.isNew ? (
              <span className="flex items-center space-x-1 text-xs text-amber-400 bg-amber-500/10 border border-amber-600/30 rounded-full px-2 py-1">
                <Sparkles size={12} />
                <span>New payee</span>
              </span>
            ) : (
              <span className="flex items-center space-x-1 text-xs text-emerald-400 bg-emerald-500/10 border border-emerald-600/30 rounded-full px-2 py-1">
                <BadgeCheck size={12} />
                <span>Trusted</span>
              </span>
            )}
          </div>
        ))}
      </div>

      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4">
        <h3 className="text-sm font-bold text-slate-400 uppercase mb-3">Add New Beneficiary</h3>
        <form onSubmit={handleAdd} className="space-y-3">
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="Beneficiary name"
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-600"
          />
          <input
            value={account}
            onChange={(e) => setAccount(e.target.value)}
            placeholder="Account number / UPI ID"
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm text-white focus:outline-none focus:ring-2 focus:ring-blue-600"
          />
          <button
            type="submit"
            className="w-full flex items-center justify-center space-x-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold py-2 rounded-lg transition-colors"
          >
            <Plus size={16} />
            <span>Add Beneficiary</span>
          </button>
        </form>
      </div>
    </div>
  );
};

export default BeneficiaryManagement;
