import { useState } from 'react';
import {
  Landmark, LayoutDashboard, MessageSquare, Users, Send, Gavel, History, LogOut, ArrowLeftCircle,
} from 'lucide-react';
import { getSessionId, resetSession } from './api';
import RiskHUD from './RiskHUD';
import LoginScreen from './LoginScreen';
import SmsInbox from './SmsInbox';
import PhishingPage from './PhishingPage';
import AccountDashboard from './AccountDashboard';
import BeneficiaryManagement, { Beneficiary } from './BeneficiaryManagement';
import TransferMoney from './TransferMoney';
import JudgeMode from './JudgeMode';
import Timeline from '../components/Timeline';
import { getTimeline } from './api';
import { useEffect } from 'react';

type Screen = 'login' | 'dashboard' | 'inbox' | 'phishing' | 'beneficiaries' | 'transfer' | 'judge' | 'timeline';

const DEFAULT_BENEFICIARIES: Beneficiary[] = [
  { id: 'b_default_1', name: 'Priya Sharma', account: 'XXXX-XXXX-4521', isNew: false },
  { id: 'b_default_2', name: 'Amit Verma', account: 'XXXX-XXXX-7788', isNew: false },
];

const NAV_ITEMS: { key: Screen; label: string; icon: any }[] = [
  { key: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { key: 'inbox', label: 'SMS Inbox', icon: MessageSquare },
  { key: 'beneficiaries', label: 'Beneficiaries', icon: Users },
  { key: 'transfer', label: 'Transfer Money', icon: Send },
  { key: 'timeline', label: 'Risk Timeline', icon: History },
  { key: 'judge', label: 'Judge Mode', icon: Gavel },
];

const BankSimulator = () => {
  const [mySessionId, setMySessionId] = useState(getSessionId());
  const [viewSessionId, setViewSessionId] = useState(mySessionId);
  const [screen, setScreen] = useState<Screen>('login');
  const [latestResult, setLatestResult] = useState<any>(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [phishingUrl, setPhishingUrl] = useState<string | null>(null);
  const [beneficiaries, setBeneficiaries] = useState<Beneficiary[]>(DEFAULT_BENEFICIARIES);
  const [scopedTimeline, setScopedTimeline] = useState<any[]>([]);

  const bumpRefresh = () => setRefreshKey((k) => k + 1);

  const handleResult = (result: any) => {
    setLatestResult(result);
    bumpRefresh();
  };

  const handleReset = () => {
    const fresh = resetSession();
    setMySessionId(fresh);
    setViewSessionId(fresh);
    setLatestResult(null);
    setBeneficiaries(DEFAULT_BENEFICIARIES);
    setPhishingUrl(null);
    setScreen('login');
    bumpRefresh();
  };

  const handleScenarioRun = (judgeSessionId: string, latest: any) => {
    setViewSessionId(judgeSessionId);
    setLatestResult(latest);
    bumpRefresh();
  };

  const returnToMySession = () => {
    setViewSessionId(mySessionId);
    bumpRefresh();
  };

  useEffect(() => {
    if (screen === 'timeline') {
      getTimeline(viewSessionId, 50).then(setScopedTimeline).catch(() => {});
    }
  }, [screen, viewSessionId, refreshKey]);

  if (screen === 'login') {
    return (
      <div className="flex h-screen bg-slate-950 font-sans">
        <div className="flex-1 overflow-y-auto">
          <LoginScreen
            sessionId={mySessionId}
            onResult={(r) => {
              setViewSessionId(mySessionId);
              handleResult(r);
            }}
            onLogin={() => setScreen('dashboard')}
          />
        </div>
        <RiskHUD sessionId={viewSessionId} latest={latestResult} onReset={handleReset} refreshKey={refreshKey} />
      </div>
    );
  }

  const renderScreen = () => {
    switch (screen) {
      case 'dashboard':
        return <AccountDashboard />;
      case 'inbox':
        return (
          <SmsInbox
            sessionId={mySessionId}
            onResult={(r) => {
              setViewSessionId(mySessionId);
              handleResult(r);
            }}
            onOpenLink={(url) => {
              setPhishingUrl(url);
              setScreen('phishing');
            }}
          />
        );
      case 'phishing':
        return (
          <PhishingPage
            sessionId={mySessionId}
            url={phishingUrl || 'secure-bank.com'}
            onResult={(r) => {
              setViewSessionId(mySessionId);
              handleResult(r);
            }}
            onBack={() => setScreen('inbox')}
          />
        );
      case 'beneficiaries':
        return (
          <BeneficiaryManagement
            beneficiaries={beneficiaries}
            onAdd={(b) => setBeneficiaries((prev) => [...prev, b])}
          />
        );
      case 'transfer':
        return (
          <TransferMoney
            sessionId={mySessionId}
            beneficiaries={beneficiaries}
            onResult={(r) => {
              setViewSessionId(mySessionId);
              handleResult(r);
            }}
          />
        );
      case 'judge':
        return <JudgeMode onScenarioRun={handleScenarioRun} />;
      case 'timeline':
        return (
          <div className="p-6 max-w-3xl mx-auto">
            <Timeline events={scopedTimeline} />
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="flex h-screen bg-slate-950 font-sans flex-col lg:flex-row">
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top bar */}
        <header className="border-b border-slate-800 px-4 py-3 flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-2 text-blue-500">
            <Landmark size={24} />
            <span className="font-bold text-lg text-white">SecureTrust Bank</span>
            <span className="text-xs text-slate-500 ml-2">BankSimulator Demo</span>
          </div>
          <button
            onClick={() => setScreen('login')}
            className="flex items-center space-x-1 text-xs text-slate-400 hover:text-white"
          >
            <LogOut size={14} />
            <span>Sign out</span>
          </button>
        </header>

        {/* Nav tabs */}
        <nav className="border-b border-slate-800 px-4 flex space-x-1 overflow-x-auto shrink-0">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.key}
                onClick={() => setScreen(item.key)}
                className={`flex items-center space-x-2 px-4 py-3 text-sm whitespace-nowrap border-b-2 transition-colors ${
                  screen === item.key
                    ? 'border-blue-500 text-blue-400'
                    : 'border-transparent text-slate-400 hover:text-slate-200'
                }`}
              >
                <Icon size={16} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        {viewSessionId !== mySessionId && (
          <div className="bg-amber-500/10 border-b border-amber-600/30 text-amber-300 text-xs px-4 py-2 flex items-center justify-between">
            <span>Viewing Judge Mode scenario session: <code>{viewSessionId}</code></span>
            <button onClick={returnToMySession} className="flex items-center space-x-1 hover:text-white">
              <ArrowLeftCircle size={14} />
              <span>Return to my session</span>
            </button>
          </div>
        )}

        <main className="flex-1 overflow-y-auto">{renderScreen()}</main>
      </div>

      <RiskHUD sessionId={viewSessionId} latest={latestResult} onReset={handleReset} refreshKey={refreshKey} />
    </div>
  );
};

export default BankSimulator;
