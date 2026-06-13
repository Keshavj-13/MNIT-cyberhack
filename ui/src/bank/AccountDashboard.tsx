import { Wallet, ArrowDownLeft, ArrowUpRight, CreditCard } from 'lucide-react';

const TRANSACTIONS = [
  { id: 1, label: 'Salary Credit - Infosys Ltd', amount: 85000, type: 'credit', date: 'Jun 12' },
  { id: 2, label: 'Electricity Bill - BSES', amount: -2140, type: 'debit', date: 'Jun 11' },
  { id: 3, label: 'Transfer to Priya Sharma', amount: -5000, type: 'debit', date: 'Jun 09' },
  { id: 4, label: 'Grocery - BigBasket', amount: -1875, type: 'debit', date: 'Jun 08' },
  { id: 5, label: 'Interest Credit', amount: 412, type: 'credit', date: 'Jun 01' },
];

const AccountDashboard = () => {
  const balance = 248930.5;

  return (
    <div className="p-6 max-w-2xl mx-auto space-y-6">
      <div className="bg-gradient-to-br from-blue-700 to-blue-900 rounded-2xl p-6 text-white shadow-lg">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-blue-200 text-xs uppercase tracking-wide">Savings Account · **** 7421</p>
            <p className="text-3xl font-bold mt-1">₹{balance.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</p>
          </div>
          <Wallet size={36} className="text-blue-200" />
        </div>
        <div className="mt-4 flex items-center space-x-1 text-xs text-blue-200">
          <CreditCard size={14} />
          <span>Rajesh Kumar · SecureTrust Bank</span>
        </div>
      </div>

      <div>
        <h2 className="text-sm font-bold text-slate-400 uppercase mb-3">Recent Activity</h2>
        <div className="space-y-2">
          {TRANSACTIONS.map((tx) => (
            <div key={tx.id} className="flex items-center justify-between bg-slate-900 border border-slate-800 rounded-xl p-3">
              <div className="flex items-center space-x-3">
                <div className={`rounded-full p-2 ${tx.type === 'credit' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-slate-800 text-slate-400'}`}>
                  {tx.type === 'credit' ? <ArrowDownLeft size={16} /> : <ArrowUpRight size={16} />}
                </div>
                <div>
                  <p className="text-sm text-slate-200">{tx.label}</p>
                  <p className="text-xs text-slate-500">{tx.date}</p>
                </div>
              </div>
              <span className={`text-sm font-semibold ${tx.type === 'credit' ? 'text-emerald-400' : 'text-slate-300'}`}>
                {tx.type === 'credit' ? '+' : ''}₹{Math.abs(tx.amount).toLocaleString('en-IN')}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default AccountDashboard;
