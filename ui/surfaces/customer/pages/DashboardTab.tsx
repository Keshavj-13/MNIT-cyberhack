import React from 'react';
import { Landmark } from 'lucide-react';
import { useAppContext } from '../context/AppContext';

export default function DashboardTab() {
  const { cryptoState, balances, transactions } = useAppContext();

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-white/[0.06]">
        <h2 className="text-xl font-bold tracking-tight">Account Summary</h2>
        <span className="text-xs text-neutral-500 font-mono">Decrypted under session key v{cryptoState.keyVersion}</span>
      </div>

      {/* Balances */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-gradient-to-br from-neutral-900 to-neutral-950 border border-white/[0.06] rounded-xl p-6 relative overflow-hidden">
          <div className="absolute top-0 right-0 p-4 opacity-5"><Landmark size={120} /></div>
          <p className="text-xs font-semibold text-neutral-400 uppercase tracking-wider">Secure Checking</p>
          <p className="text-xs font-mono text-neutral-500 mt-1">{balances?.checking?.account_number || 'TR-XXXXXXXXXXX'}</p>
          <p className="text-3xl font-bold mt-4 tracking-tight">${balances?.checking?.balance?.toLocaleString(undefined, { minimumFractionDigits: 2 })}</p>
        </div>
        <div className="bg-gradient-to-br from-neutral-900 to-neutral-950 border border-white/[0.06] rounded-xl p-6 relative overflow-hidden">
          <p className="text-xs font-semibold text-neutral-400 uppercase tracking-wider">Secure Savings</p>
          <p className="text-xs font-mono text-neutral-500 mt-1">{balances?.savings?.account_number || 'TR-XXXXXXXXXXX'}</p>
          <p className="text-3xl font-bold mt-4 tracking-tight">${balances?.savings?.balance?.toLocaleString(undefined, { minimumFractionDigits: 2 })}</p>
        </div>
      </div>

      {/* Recent Ledger */}
      <div className="bg-neutral-900 border border-white/[0.06] rounded-xl p-6 space-y-4">
        <h3 className="text-sm font-semibold tracking-wide text-white">Recent Statement Ledger</h3>
        <div className="divide-y divide-white/[0.06] overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="text-neutral-500 border-b border-white/[0.06]">
                <th className="pb-3 font-semibold uppercase">Date</th>
                <th className="pb-3 font-semibold uppercase">Description</th>
                <th className="pb-3 font-semibold uppercase text-right">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04] font-mono">
              {transactions.map((tx: any) => (
                <tr key={tx.id} className="hover:bg-white/[0.01]">
                  <td className="py-3 text-neutral-400">{new Date(tx.date).toLocaleDateString()}</td>
                  <td className="py-3 text-white font-sans">{tx.description}</td>
                  <td className={`py-3 text-right font-bold ${tx.amount > 0 ? 'text-teal-400' : 'text-neutral-300'}`}>
                    {tx.amount > 0 ? `+$${tx.amount.toFixed(2)}` : `-$${Math.abs(tx.amount).toFixed(2)}`}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
