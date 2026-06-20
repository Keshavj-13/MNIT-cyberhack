import React, { useState } from 'react';
import { Search } from 'lucide-react';
import { useAppContext } from '../context/AppContext';

export default function StatementsTab() {
  const { transactions } = useAppContext();
  const [statementFilter, setStatementFilter] = useState('');

  const filteredTx = transactions.filter((tx: any) => 
    tx.description.toLowerCase().includes(statementFilter.toLowerCase()) ||
    (tx.amount.toString().includes(statementFilter))
  );

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-white/[0.06]">
        <h2 className="text-xl font-bold tracking-tight">Statements</h2>
        <span className="text-xs text-neutral-500 font-mono">Immutable Ledger</span>
      </div>

      <div className="bg-neutral-900 border border-white/[0.06] rounded-xl p-6">
        <div className="flex flex-col sm:flex-row items-center gap-4 mb-6">
          <div className="relative flex-1 w-full">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-500" size={16} />
            <input 
              type="text" 
              placeholder="Search ledger entries..."
              value={statementFilter}
              onChange={(e) => setStatementFilter(e.target.value)}
              className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg pl-10 pr-4 py-2 text-sm focus:outline-none focus:border-teal-500/50"
            />
          </div>
          <button className="whitespace-nowrap px-4 py-2 bg-neutral-800 hover:bg-neutral-700 text-xs font-semibold rounded-lg transition-colors border border-white/[0.04]">
            Download PDF
          </button>
        </div>

        <div className="divide-y divide-white/[0.06] overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="text-neutral-500 border-b border-white/[0.06]">
                <th className="pb-3 font-semibold uppercase">Txn ID</th>
                <th className="pb-3 font-semibold uppercase">Date</th>
                <th className="pb-3 font-semibold uppercase">Description</th>
                <th className="pb-3 font-semibold uppercase text-right">Amount</th>
                <th className="pb-3 font-semibold uppercase text-right">Balance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-white/[0.04] font-mono">
              {filteredTx.map((tx: any) => (
                <tr key={tx.id} className="hover:bg-white/[0.01]">
                  <td className="py-3 text-neutral-500">#{tx.id}</td>
                  <td className="py-3 text-neutral-400">{new Date(tx.date).toLocaleString()}</td>
                  <td className="py-3 text-white font-sans">{tx.description}</td>
                  <td className={`py-3 text-right font-bold ${tx.amount > 0 ? 'text-teal-400' : 'text-neutral-300'}`}>
                    {tx.amount > 0 ? `+$${tx.amount.toFixed(2)}` : `-$${Math.abs(tx.amount).toFixed(2)}`}
                  </td>
                  <td className="py-3 text-right text-neutral-400">
                    ${tx.running_balance !== undefined ? tx.running_balance.toFixed(2) : '-'}
                  </td>
                </tr>
              ))}
              {filteredTx.length === 0 && (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-neutral-500 font-sans">
                    No ledger entries found
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
