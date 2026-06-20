import React, { useState } from 'react';
import { AlertTriangle, CheckCircle } from 'lucide-react';
import { useAppContext } from '../context/AppContext';
import { addBeneficiary } from '../api';

export default function BeneficiariesTab() {
  const { cryptoState, animateKeyRotation, triggerKeyDesyncError, refreshData, beneficiaries } = useAppContext();
  
  const [newPayeeName, setNewPayeeName] = useState('');
  const [newPayeeAccount, setNewPayeeAccount] = useState('');
  const [newPayeeBank, setNewPayeeBank] = useState('');
  const [addPayeeStatus, setAddPayeeStatus] = useState<string | null>(null);
  const [isAddingPayee, setIsAddingPayee] = useState(false);

  const handleAddPayee = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPayeeName || !newPayeeAccount || !newPayeeBank) return;

    setIsAddingPayee(true);
    setAddPayeeStatus(null);
    try {
      const res = await addBeneficiary(cryptoState, newPayeeName, newPayeeAccount, newPayeeBank);
      
      if (res.key_rotated && res.new_key) {
        animateKeyRotation(res.new_key, res.new_key_version, res.risk_level);
      }

      if (res.transfer_status === 'challenged') {
        setAddPayeeStatus('verification_required');
      } else {
        setAddPayeeStatus('added');
        setNewPayeeName('');
        setNewPayeeAccount('');
        setNewPayeeBank('');
        refreshData();
      }
    } catch (err: any) {
      console.error(err);
      if (err.response?.status === 409) {
        triggerKeyDesyncError();
      } else {
        alert("Action rejected by the threat engine.");
      }
    } finally {
      setIsAddingPayee(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-white/[0.06]">
        <h2 className="text-xl font-bold tracking-tight">Manage Payees</h2>
        <span className="text-xs text-neutral-500 font-mono font-semibold">Active Session: {cryptoState.sessionId}</span>
      </div>

      {addPayeeStatus === 'added' && (
        <div className="p-4 bg-teal-500/10 border border-teal-500/25 rounded-lg flex items-center gap-3 text-sm text-teal-300">
          <CheckCircle size={18} />
          <span>Beneficiary added and registered with the threat monitoring grid successfully.</span>
        </div>
      )}

      {addPayeeStatus === 'verification_required' && (
        <div className="p-4 bg-amber-500/10 border border-amber-500/25 rounded-lg flex items-center gap-3 text-sm text-amber-300">
          <AlertTriangle size={18} />
          <span>Payee addition flagged. Key shuffled and step-up confirmation required on next transfer.</span>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 items-start">
        {/* Add Payee Form */}
        <form onSubmit={handleAddPayee} className="lg:col-span-2 bg-neutral-900 border border-white/[0.06] rounded-xl p-6 space-y-4">
          <h3 className="text-sm font-semibold tracking-wide text-white">Add New Payee</h3>
          
          <div className="space-y-1.5">
            <label className="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Full Name</label>
            <input 
              type="text"
              placeholder="e.g. Priyan Sharma"
              value={newPayeeName}
              onChange={(e) => setNewPayeeName(e.target.value)}
              className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg px-3.5 py-2 text-xs focus:outline-none focus:border-teal-500/50"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Banking ID / Account #</label>
            <input 
              type="text"
              placeholder="e.g. CBI-12345678"
              value={newPayeeAccount}
              onChange={(e) => setNewPayeeAccount(e.target.value)}
              className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg px-3.5 py-2 text-xs focus:outline-none focus:border-teal-500/50 font-mono"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Bank Name</label>
            <input 
              type="text"
              placeholder="e.g. CoreBank India"
              value={newPayeeBank}
              onChange={(e) => setNewPayeeBank(e.target.value)}
              className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg px-3.5 py-2 text-xs focus:outline-none focus:border-teal-500/50"
            />
          </div>

          <button 
            type="submit"
            disabled={isAddingPayee || !newPayeeName || !newPayeeAccount || !newPayeeBank}
            className="w-full mt-2 py-2.5 bg-white hover:bg-neutral-200 text-black font-bold text-xs rounded-lg transition-colors disabled:opacity-50"
          >
            {isAddingPayee ? 'Encrypting...' : 'Add Payee'}
          </button>
        </form>

        {/* List */}
        <div className="lg:col-span-3 bg-neutral-900 border border-white/[0.06] rounded-xl p-6">
          <h3 className="text-sm font-semibold tracking-wide text-white mb-4">Saved Beneficiaries</h3>
          <div className="divide-y divide-white/[0.06]">
            {beneficiaries.map((b: any) => (
              <div key={b.id} className="py-3 flex items-center justify-between hover:bg-white/[0.01]">
                <div>
                  <p className="text-sm font-semibold text-neutral-200">{b.name}</p>
                  <p className="text-xs text-neutral-500 mt-0.5">{b.bank_name}</p>
                </div>
                <div className="text-right">
                  <p className="text-xs font-mono text-neutral-400">{b.account_number}</p>
                  <button className="text-[10px] text-teal-500 hover:text-teal-400 font-semibold mt-1 uppercase tracking-wide">
                    Transfer
                  </button>
                </div>
              </div>
            ))}
            {beneficiaries.length === 0 && (
              <div className="py-8 text-center text-neutral-500 text-xs">
                No payees saved yet.
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
