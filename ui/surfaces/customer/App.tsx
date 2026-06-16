import React, { useState, useEffect, useRef } from 'react';
import { 
  Shield, Landmark, LogOut, LayoutDashboard, Send, Users, 
  FileText, HelpCircle, Key, RefreshCw, AlertTriangle, CheckCircle, Lock, Info, Smartphone
} from 'lucide-react';
import { 
  loginCustomer, logoutCustomer, getAccountDetails, 
  getStatements, getBeneficiaries, addBeneficiary, transferMoney 
} from './api';
import { useTelemetry } from './hooks/useTelemetry';

export default function App() {
  // Authentication & Cryptography State
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [authError, setAuthError] = useState('');
  const [loading, setLoading] = useState(false);

  // Cryptographic Session Variables
  const [cryptoState, setCryptoState] = useState({
    aesKey: '',
    keyVersion: 1,
    sessionId: '',
    riskLevel: 1
  });

  // UI state
  const [activeTab, setActiveTab] = useState('dashboard');
  const [showCryptoModal, setShowCryptoModal] = useState(false);
  const [keyRotatedAnim, setKeyRotatedAnim] = useState(false);
  const [keyRotationInfo, setKeyRotationInfo] = useState<any>(null);
  
  // Banking data
  const [balances, setBalances] = useState<any>({ checking: { balance: 0 }, savings: { balance: 0 } });
  const [transactions, setTransactions] = useState<any[]>([]);
  const [beneficiaries, setBeneficiaries] = useState<any[]>([]);
  const [refreshTrigger, setRefreshTrigger] = useState(0);

  // Transfer form state
  const [transferAmount, setTransferAmount] = useState('');
  const [selectedBeneficiaryId, setSelectedBeneficiaryId] = useState('');
  const [transferStatus, setTransferStatus] = useState<any>(null); // { status: string, message: string }
  const [isTransferring, setIsTransferring] = useState(false);
  
  // OTP step-up verification modal state
  const [showOtpModal, setShowOtpModal] = useState(false);
  const [otpCode, setOtpCode] = useState('');
  const [otpError, setOtpError] = useState('');
  const [simulatedSmsCode, setSimulatedSmsCode] = useState<string | null>(null);
  const [smsNotification, setSmsNotification] = useState<string | null>(null);

  // Add Beneficiary form state
  const [newPayeeName, setNewPayeeName] = useState('');
  const [newPayeeAccount, setNewPayeeAccount] = useState('');
  const [newPayeeBank, setNewPayeeBank] = useState('');
  const [addPayeeStatus, setAddPayeeStatus] = useState<string | null>(null);
  const [isAddingPayee, setIsAddingPayee] = useState(false);

  // Support state
  const [supportTopic, setSupportTopic] = useState('general');
  const [supportMessage, setSupportMessage] = useState('');
  const [supportSuccess, setSupportSuccess] = useState(false);

  // Active session timer
  const [sessionTtl, setSessionTtl] = useState(1800); // 30 minutes countdown

  // Active telemetry hook (silent background telemetry)
  useTelemetry(activeTab, cryptoState.sessionId, cryptoState.keyVersion, cryptoState.aesKey);

  // Decrement session timer
  useEffect(() => {
    if (!isAuthenticated) return;
    const interval = setInterval(() => {
      setSessionTtl((prev) => {
        if (prev <= 1) {
          handleLogout();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, [isAuthenticated]);

  // Fetch account data
  useEffect(() => {
    if (!isAuthenticated || !cryptoState.aesKey) return;
    
    async function fetchData() {
      try {
        const acc = await getAccountDetails(cryptoState);
        setBalances(acc);
        
        const tx = await getStatements(cryptoState);
        setTransactions(tx);
        
        const ben = await getBeneficiaries(cryptoState);
        setBeneficiaries(ben);
      } catch (err: any) {
        console.error("Cryptographic fetch failed:", err);
        if (err.response?.status === 409) {
          // Cryptographic desync detected (key was shuffled by server in background)
          triggerKeyDesyncError();
        } else if (err.response?.status === 401) {
          setIsAuthenticated(false);
        }
      }
    }
    fetchData();
  }, [isAuthenticated, cryptoState.keyVersion, refreshTrigger]);

  const triggerKeyDesyncError = () => {
    alert("Cryptographic integrity check failed: Session keys have desynchronized. Security audit initiated.");
    handleLogout();
  };

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!username.trim() || !password.trim()) {
      setAuthError('Username and PIN are required');
      return;
    }
    setLoading(true);
    setAuthError('');
    try {
      const data = await loginCustomer(username, password);
      setCryptoState({
        aesKey: data.aes_key,
        keyVersion: data.key_version,
        sessionId: data.session_id,
        riskLevel: data.risk_level
      });
      setSessionTtl(1800);
      setIsAuthenticated(true);
    } catch (err: any) {
      setAuthError(err.response?.data?.detail || 'Authentication failed. Please verify credentials.');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = async () => {
    try {
      await logoutCustomer();
    } catch (e) {}
    setIsAuthenticated(false);
    setCryptoState({ aesKey: '', keyVersion: 1, sessionId: '', riskLevel: 1 });
    setUsername('');
    setPassword('');
    setTransferStatus(null);
    setTransferAmount('');
    setSelectedBeneficiaryId('');
    setSimulatedSmsCode(null);
    setSmsNotification(null);
    setShowCryptoModal(false);
    setShowOtpModal(false);
  };

  // Triggers key shuffle visual indicator
  const animateKeyRotation = (newKey: string, newVersion: number, newRisk: number) => {
    setKeyRotatedAnim(true);
    setKeyRotationInfo({
      oldKey: cryptoState.aesKey,
      newKey: newKey,
      oldVersion: cryptoState.keyVersion,
      newVersion: newVersion,
      riskLevel: newRisk
    });
    
    // Play sound or vibration if needed, then update state after animation delay
    setTimeout(() => {
      setCryptoState(prev => ({
        ...prev,
        aesKey: newKey,
        keyVersion: newVersion,
        riskLevel: newRisk
      }));
      setKeyRotatedAnim(false);
      setRefreshTrigger(prev => prev + 1);
    }, 2500);
  };

  const handleTransferSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedBeneficiaryId || !transferAmount) return;
    
    const amountNum = parseFloat(transferAmount);
    if (isNaN(amountNum) || amountNum <= 0) {
      alert("Invalid transfer amount");
      return;
    }

    setIsTransferring(true);
    setTransferStatus(null);

    // Find if payee is new in this session
    const selectedPayee = beneficiaries.find(b => String(b.id) === String(selectedBeneficiaryId));
    const isNew = selectedPayee ? selectedPayee.id > 2 : false; // Mock new payees added during simulation

    try {
      const res = await transferMoney(cryptoState, amountNum, selectedBeneficiaryId, isNew);
      
      // Check if key shuffled
      if (res.key_rotated && res.new_key) {
        animateKeyRotation(res.new_key, res.new_key_version, res.risk_level);
      }

      if (res.status === 'challenged') {
        // Step-up challenge required. Generate OTP and notify.
        const code = Math.floor(100000 + Math.random() * 900000).toString();
        setSimulatedSmsCode(code);
        setShowOtpModal(true);
        // Display toast to simulate SMS arrival
        setSmsNotification(`OTP Code: ${code} - Verification for transfer request of $${amountNum}`);
        setTimeout(() => setSmsNotification(null), 10000);
      } else if (res.status === 'blocked') {
        setCryptoState(prev => ({ ...prev, riskLevel: 4 }));
      } else {
        setTransferStatus({ status: 'approved', message: res.message });
        setTransferAmount('');
        setSelectedBeneficiaryId('');
        setRefreshTrigger(prev => prev + 1);
      }
    } catch (err: any) {
      console.error(err);
      if (err.response?.status === 409) {
        triggerKeyDesyncError();
      } else {
        alert(err.response?.data?.detail || "Transfer rejected");
      }
    } finally {
      setIsTransferring(false);
    }
  };

  const handleOtpVerify = (e: React.FormEvent) => {
    e.preventDefault();
    if (otpCode === simulatedSmsCode) {
      setShowOtpModal(false);
      setTransferStatus({ status: 'approved', message: "Transfer verified & completed successfully via Step-up OTP." });
      setTransferAmount('');
      setSelectedBeneficiaryId('');
      setOtpCode('');
      setOtpError('');
      setRefreshTrigger(prev => prev + 1);
    } else {
      setOtpError('Invalid cryptographic code. Authentication rejected.');
    }
  };

  const handleAddPayee = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPayeeName || !newPayeeAccount || !newPayeeBank) return;

    setIsAddingPayee(true);
    setAddPayeeStatus(null);
    try {
      const res = await addBeneficiary(cryptoState, newPayeeName, newPayeeAccount, newPayeeBank);
      
      // Check if key shuffled due to payee addition risk
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
        setRefreshTrigger(prev => prev + 1);
      }
    } catch (err: any) {
      console.error(err);
      if (err.response?.status === 409) {
        triggerKeyDesyncError();
      } else {
        alert("Action rejected by threat engine");
      }
    } finally {
      setIsAddingPayee(false);
    }
  };

  const handleSupportSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!supportMessage.trim()) return;
    setSupportSuccess(true);
    setSupportMessage('');
    setTimeout(() => setSupportSuccess(false), 5000);
  };

  const formatTtl = (seconds: number) => {
    const m = Math.floor(seconds / 60);
    const s = seconds % 60;
    return `${m}:${s < 10 ? '0' : ''}${s}`;
  };

  // MASK key string for security dashboard
  const formatKey = (keyBase64: string) => {
    if (!keyBase64) return '';
    return keyBase64.slice(0, 8) + ' •••••••••••••••• ' + keyBase64.slice(-8);
  };

  // RISK containment level (Level 4) Lockout Screen
  if (cryptoState.riskLevel >= 4) {
    return (
      <div className="flex h-screen bg-neutral-950 text-white font-sans items-center justify-center p-6">
        <div className="max-w-md w-full bg-neutral-900 border border-red-500/20 rounded-xl p-8 shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 left-0 right-0 h-1.5 bg-red-600 animate-pulse"></div>
          <div className="flex flex-col items-center text-center space-y-5">
            <div className="grid place-items-center w-16 h-16 rounded-full bg-red-500/10 border border-red-500/30 text-red-500 animate-bounce">
              <Lock size={32} />
            </div>
            <h1 className="text-xl font-bold tracking-tight text-white">Cryptographic Lockout</h1>
            <p className="text-sm text-neutral-400">
              The Security Threat Detection Engine has activated Level 4 containment protocol (Session Revocation).
            </p>
            <div className="w-full bg-neutral-950 p-4 border border-white/[0.04] rounded-lg text-left text-xs font-mono space-y-2">
              <div><span className="text-neutral-500">SESSION_ID:</span> <span className="text-red-400">{cryptoState.sessionId}</span></div>
              <div><span className="text-neutral-500">KEYS:</span> <span className="text-red-400">REVOKED & PURGED</span></div>
              <div><span className="text-neutral-500">ALGORITHM:</span> <span className="text-neutral-500">AES-256-GCM (Terminated)</span></div>
              <div><span className="text-neutral-500">RISK_LEVEL:</span> <span className="text-red-500 font-bold">CONTAINMENT (CRITICAL)</span></div>
            </div>
            <p className="text-xs text-neutral-500 italic">
              Your cryptographic keys have been purged from database cache. To unlock your account, please verify identity in person.
            </p>
            <button 
              onClick={handleLogout}
              className="w-full py-2.5 rounded-lg bg-white text-black font-semibold text-sm hover:bg-neutral-200 transition-colors"
            >
              Reset Session
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Visual Key Shuffling Overlay (plays when key rotates)
  if (keyRotatedAnim && keyRotationInfo) {
    return (
      <div className="flex h-screen bg-neutral-950 text-white font-sans items-center justify-center p-6">
        <div className="max-w-md w-full bg-neutral-900 border border-teal-500/20 rounded-xl p-8 shadow-2xl relative text-center space-y-6">
          <div className="grid place-items-center w-16 h-16 rounded-full bg-teal-500/10 border border-teal-500/30 text-teal-400 mx-auto animate-spin">
            <RefreshCw size={32} />
          </div>
          <h2 className="text-lg font-bold text-white tracking-wide">SHUFFLING SESSION KEYS</h2>
          <p className="text-sm text-neutral-400">
            Threat levels shifted. Re-negotiating symmetric cryptographic keys to isolate session state...
          </p>
          <div className="bg-neutral-950 p-4 rounded-lg border border-white/[0.04] text-left text-xs font-mono space-y-2">
            <div>
              <span className="text-neutral-500">KEY_VERSION:</span>{' '}
              <span className="text-neutral-300">v{keyRotationInfo.oldVersion}</span>
              <span className="text-teal-400"> → v{keyRotationInfo.newVersion}</span>
            </div>
            <div>
              <span className="text-neutral-500">RISK_LEVEL:</span>{' '}
              <span className="text-neutral-300">Level {cryptoState.riskLevel}</span>
              <span className="text-teal-400"> → Level {keyRotationInfo.riskLevel}</span>
            </div>
            <div className="truncate">
              <span className="text-neutral-500">OLD_KEY:</span>{' '}
              <span className="text-neutral-400 text-[10px]">{formatKey(keyRotationInfo.oldKey)}</span>
            </div>
            <div className="truncate">
              <span className="text-teal-400 font-semibold">NEW_KEY:</span>{' '}
              <span className="text-teal-300 text-[10px]">{formatKey(keyRotationInfo.newKey)}</span>
            </div>
          </div>
          <div className="w-full h-1 bg-neutral-800 rounded-full overflow-hidden">
            <div className="h-full bg-teal-500 animate-[pulse_1.5s_infinite] w-full"></div>
          </div>
        </div>
      </div>
    );
  }

  // Login Screen
  if (!isAuthenticated) {
    return (
      <div className="flex min-h-screen bg-neutral-950 text-white font-sans items-center justify-center p-6">
        <div className="max-w-md w-full bg-neutral-900 border border-white/[0.06] rounded-xl p-8 shadow-2xl space-y-6">
          <div className="flex flex-col items-center space-y-2">
            <div className="w-12 h-12 rounded-xl bg-teal-500/10 border border-teal-500/20 text-teal-400 grid place-items-center mb-1">
              <Landmark size={24} />
            </div>
            <h1 className="text-2xl font-bold tracking-tight text-white">SecureTrust Portal</h1>
            <p className="text-sm text-neutral-400 text-center">
              A secure, end-to-end cryptographic banking platform.
            </p>
          </div>

          <form onSubmit={handleLogin} className="space-y-4">
            {authError && (
              <div className="p-3.5 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-400 flex items-center gap-2">
                <AlertTriangle size={14} className="shrink-0" />
                <span>{authError}</span>
              </div>
            )}
            
            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-neutral-400 uppercase tracking-wider">Account ID</label>
              <input 
                type="text" 
                placeholder="e.g. mnit_customer"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg px-4 py-2.5 text-sm text-white focus:outline-none focus:border-teal-500/50 transition-colors"
              />
            </div>

            <div className="space-y-1.5">
              <label className="text-xs font-semibold text-neutral-400 uppercase tracking-wider">Security PIN</label>
              <input 
                type="password" 
                placeholder="••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg px-4 py-2.5 text-sm text-white focus:outline-none focus:border-teal-500/50 transition-colors"
              />
            </div>

            <button 
              type="submit" 
              disabled={loading}
              className="w-full py-3 bg-teal-500 hover:bg-teal-400 text-black font-bold text-sm rounded-lg transition-colors flex items-center justify-center gap-2"
            >
              {loading ? 'Decrypting Session...' : 'Authenticate Secure Session'}
            </button>
          </form>

          <div className="pt-4 border-t border-white/[0.06] text-center">
            <span className="text-[11px] text-neutral-500 flex items-center justify-center gap-1.5 font-mono">
              <Shield size={12} />
              Session secured via AES-256-GCM & HS256 JWT
            </span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-neutral-950 text-white font-sans flex-col">
      {/* Top Header */}
      <header className="border-b border-white/[0.06] bg-neutral-950 px-6 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center space-x-3 text-teal-400">
          <div className="w-9 h-9 rounded-lg bg-teal-500/10 border border-teal-500/20 grid place-items-center">
            <Landmark size={20} />
          </div>
          <div>
            <h1 className="font-bold text-base leading-tight text-white">SecureTrust Bank</h1>
            <p className="text-[10px] text-neutral-500 font-semibold uppercase tracking-widest font-mono">Retail Banking</p>
          </div>
        </div>

        {/* Cryptographic Badges */}
        <div className="flex items-center space-x-3">
          <button 
            onClick={() => setShowCryptoModal(true)}
            className="flex items-center gap-2 bg-teal-500/10 hover:bg-teal-500/15 border border-teal-500/20 text-teal-300 px-3 py-1.5 rounded-full text-xs font-mono transition-all group"
          >
            <span className="w-2 h-2 rounded-full bg-teal-400 group-hover:animate-ping"></span>
            <span>AES-256-GCM: active</span>
            <Key size={13} className="opacity-70" />
          </button>
          
          <div className="bg-neutral-900 border border-white/[0.06] px-3 py-1.5 rounded-full text-xs font-mono text-neutral-400 flex items-center gap-1.5">
            <span>TTL:</span>
            <span className="text-white font-semibold">{formatTtl(sessionTtl)}</span>
          </div>

          <button 
            onClick={handleLogout}
            className="p-2 text-neutral-500 hover:text-white hover:bg-white/[0.04] rounded-lg transition-colors"
            title="Disconnect Cryptographic Session"
          >
            <LogOut size={16} />
          </button>
        </div>
      </header>

      {/* Main Container */}
      <div className="flex-1 flex overflow-hidden">
        {/* Navigation Sidebar */}
        <aside className="w-60 border-r border-white/[0.06] bg-neutral-950 flex flex-col shrink-0 p-4 space-y-1">
          <button 
            onClick={() => setActiveTab('dashboard')}
            className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
              activeTab === 'dashboard' ? 'bg-teal-500/10 text-teal-300' : 'text-neutral-400 hover:text-white hover:bg-white/[0.04]'
            }`}
          >
            <LayoutDashboard size={18} />
            <span>Account Summary</span>
          </button>
          <button 
            onClick={() => setActiveTab('transfer')}
            className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
              activeTab === 'transfer' ? 'bg-teal-500/10 text-teal-300' : 'text-neutral-400 hover:text-white hover:bg-white/[0.04]'
            }`}
          >
            <Send size={18} />
            <span>Send Funds</span>
          </button>
          <button 
            onClick={() => setActiveTab('beneficiaries')}
            className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
              activeTab === 'beneficiaries' ? 'bg-teal-500/10 text-teal-300' : 'text-neutral-400 hover:text-white hover:bg-white/[0.04]'
            }`}
          >
            <Users size={18} />
            <span>Manage Payees</span>
          </button>
          <button 
            onClick={() => setActiveTab('statements')}
            className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
              activeTab === 'statements' ? 'bg-teal-500/10 text-teal-300' : 'text-neutral-400 hover:text-white hover:bg-white/[0.04]'
            }`}
          >
            <FileText size={18} />
            <span>Statement Ledger</span>
          </button>
          <button 
            onClick={() => setActiveTab('support')}
            className={`w-full flex items-center gap-3 px-4 py-3 text-sm font-medium rounded-lg transition-colors ${
              activeTab === 'support' ? 'bg-teal-500/10 text-teal-300' : 'text-neutral-400 hover:text-white hover:bg-white/[0.04]'
            }`}
          >
            <HelpCircle size={18} />
            <span>Support Desk</span>
          </button>

          <div className="flex-1"></div>

          {/* Secure indicator */}
          <div className="bg-neutral-900 border border-white/[0.04] p-3 rounded-lg text-center space-y-1.5">
            <div className="flex items-center justify-center gap-1.5 text-xs text-neutral-400 font-semibold uppercase tracking-wider">
              <Shield size={12} className="text-teal-400" />
              <span>Hardened Security</span>
            </div>
            <div className="text-[10px] text-neutral-500 font-mono">
              Key Version: v{cryptoState.keyVersion}<br/>
              Security Level: {cryptoState.riskLevel === 1 ? 'L1: Nominal' : cryptoState.riskLevel === 2 ? 'L2: step-up' : 'L3: Restricted'}
            </div>
          </div>
        </aside>

        {/* Content Panel */}
        <main className="flex-1 overflow-y-auto p-8 bg-neutral-950">
          
          {/* Dashboard Tab */}
          {activeTab === 'dashboard' && (
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
          )}

          {/* Transfer Tab */}
          {activeTab === 'transfer' && (
            <div className="max-w-xl mx-auto space-y-6">
              <div className="flex items-center justify-between pb-4 border-b border-white/[0.06]">
                <h2 className="text-xl font-bold tracking-tight">Send Funds</h2>
                <span className="text-xs text-neutral-500 font-mono">AES-256 encrypted payload</span>
              </div>

              {transferStatus && (
                <div className="p-4 bg-teal-500/10 border border-teal-500/25 rounded-lg flex items-center gap-3 text-sm text-teal-300">
                  <CheckCircle size={18} className="shrink-0" />
                  <span>{transferStatus.message}</span>
                </div>
              )}

              <form onSubmit={handleTransferSubmit} className="bg-neutral-900 border border-white/[0.06] rounded-xl p-6 space-y-4 shadow-xl">
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-neutral-400 uppercase tracking-wider">Select Payee</label>
                  <select 
                    value={selectedBeneficiaryId}
                    onChange={(e) => setSelectedBeneficiaryId(e.target.value)}
                    className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-teal-500/50"
                  >
                    <option value="">-- Choose a Beneficiary --</option>
                    {beneficiaries.map((b: any) => (
                      <option key={b.id} value={b.id}>{b.name} ({b.bank_name})</option>
                    ))}
                  </select>
                </div>

                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-neutral-400 uppercase tracking-wider">Transfer Amount ($)</label>
                  <input 
                    type="number"
                    step="0.01"
                    placeholder="0.00"
                    value={transferAmount}
                    onChange={(e) => setTransferAmount(e.target.value)}
                    className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-teal-500/50 font-mono"
                  />
                </div>

                <div className="bg-neutral-950 p-4 rounded-lg border border-white/[0.04] text-[11px] text-neutral-400 space-y-1">
                  <span className="font-semibold text-neutral-300 block mb-1">Cryptographic Policy Notice</span>
                  <p>Upon submission, this request payload is encrypted locally using the active session key (v{cryptoState.keyVersion}).</p>
                  <p>In accordance with the Threat Engine, transaction evaluation will execute silently. Risk levels may trigger immediate session key shuffling.</p>
                </div>

                <button 
                  type="submit"
                  disabled={isTransferring || !selectedBeneficiaryId || !transferAmount}
                  className="w-full py-3 bg-teal-500 hover:bg-teal-400 disabled:bg-neutral-800 disabled:text-neutral-500 text-black font-bold text-sm rounded-lg transition-colors flex items-center justify-center gap-2"
                >
                  {isTransferring ? 'Encrypting & Dispatching...' : 'Secure Transfer'}
                </button>
              </form>
            </div>
          )}

          {/* Beneficiaries Tab */}
          {activeTab === 'beneficiaries' && (
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
                    <label className="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Account Number (IBAN)</label>
                    <input 
                      type="text"
                      placeholder="e.g. TR-XXXXXXXXXXX"
                      value={newPayeeAccount}
                      onChange={(e) => setNewPayeeAccount(e.target.value)}
                      className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg px-3.5 py-2 text-xs focus:outline-none focus:border-teal-500/50 font-mono"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Bank Name</label>
                    <input 
                      type="text"
                      placeholder="e.g. Chase Bank"
                      value={newPayeeBank}
                      onChange={(e) => setNewPayeeBank(e.target.value)}
                      className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg px-3.5 py-2 text-xs focus:outline-none focus:border-teal-500/50 font-sans"
                    />
                  </div>

                  <button 
                    type="submit"
                    disabled={isAddingPayee || !newPayeeName || !newPayeeAccount || !newPayeeBank}
                    className="w-full py-2.5 bg-teal-500 hover:bg-teal-400 disabled:bg-neutral-800 disabled:text-neutral-500 text-black font-bold text-xs rounded-lg transition-colors"
                  >
                    {isAddingPayee ? 'Registering Payee...' : 'Register Payee'}
                  </button>
                </form>

                {/* Payees List */}
                <div className="lg:col-span-3 bg-neutral-900 border border-white/[0.06] rounded-xl p-6 space-y-4">
                  <h3 className="text-sm font-semibold tracking-wide text-white">Registered Payee List</h3>
                  <div className="divide-y divide-white/[0.06]">
                    {beneficiaries.map((b: any) => (
                      <div key={b.id} className="py-3 flex items-center justify-between first:pt-0 last:pb-0">
                        <div className="space-y-0.5">
                          <p className="text-xs font-semibold text-white">{b.name}</p>
                          <p className="text-[10px] text-neutral-500 font-mono">{b.account}</p>
                        </div>
                        <span className="text-[10px] bg-white/[0.04] text-neutral-400 border border-white/[0.06] px-2.5 py-1 rounded-full font-sans font-medium">
                          {b.bank_name}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Statements Tab */}
          {activeTab === 'statements' && (
            <div className="max-w-xl mx-auto space-y-6">
              <div className="flex items-center justify-between pb-4 border-b border-white/[0.06]">
                <h2 className="text-xl font-bold tracking-tight">Statement Ledger</h2>
                <span className="text-xs text-neutral-500 font-mono">Vault Storage</span>
              </div>

              <div className="bg-neutral-900 border border-white/[0.06] rounded-xl divide-y divide-white/[0.06] overflow-hidden">
                {[
                  { month: "May 2026", date: "June 01, 2026", size: "2.4 MB" },
                  { month: "April 2026", date: "May 01, 2026", size: "2.3 MB" },
                  { month: "March 2026", date: "April 01, 2026", size: "2.5 MB" },
                  { month: "February 2026", date: "March 01, 2026", size: "2.1 MB" },
                ].map((item, index) => (
                  <div key={index} className="p-4 flex items-center justify-between hover:bg-white/[0.01] transition-colors">
                    <div className="flex items-center space-x-3.5">
                      <div className="w-8 h-8 rounded bg-teal-500/10 border border-teal-500/20 text-teal-400 grid place-items-center">
                        <FileText size={16} />
                      </div>
                      <div>
                        <p className="text-xs font-bold text-white">{item.month} statement.pdf</p>
                        <p className="text-[10px] text-neutral-500 mt-0.5">Published {item.date}</p>
                      </div>
                    </div>
                    <button 
                      onClick={() => alert("Statement decrypted and opened in secure viewport.")}
                      className="text-[11px] text-teal-400 font-semibold hover:underline font-mono"
                    >
                      Retrieve ({item.size})
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Support Tab */}
          {activeTab === 'support' && (
            <div className="max-w-3xl mx-auto space-y-6">
              <div className="flex items-center justify-between pb-4 border-b border-white/[0.06]">
                <h2 className="text-xl font-bold tracking-tight">Support Desk</h2>
                <span className="text-xs text-neutral-500">Security & Help</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-5 gap-6">
                {/* FAQs */}
                <div className="md:col-span-3 bg-neutral-900 border border-white/[0.06] rounded-xl p-6 space-y-4">
                  <h3 className="text-sm font-semibold tracking-wide text-white">Security & Policy FAQ</h3>
                  
                  <div className="space-y-4">
                    <div className="space-y-1.5">
                      <h4 className="text-xs font-bold text-teal-400">What is cryptographic session key rotation?</h4>
                      <p className="text-[11px] text-neutral-400 leading-relaxed">
                        To protect your account details from theft and hijacking, our system continuously monitors threats. If anomaly indicators are triggered, symmetric AES-256 session keys are shuffled in real-time, isolating past payloads from upcoming ones.
                      </p>
                    </div>

                    <div className="space-y-1.5">
                      <h4 className="text-xs font-bold text-teal-400">Why am I prompted for step-up verification?</h4>
                      <p className="text-[11px] text-neutral-400 leading-relaxed">
                        Step-up Verification (OTP) is activated during moderate-risk states (such as new payees or VPN usage). Enter the code sent to your registered device to verify the transfer's cryptographic signature.
                      </p>
                    </div>

                    <div className="space-y-1.5">
                      <h4 className="text-xs font-bold text-teal-400">What happens if a session enters lockout?</h4>
                      <p className="text-[11px] text-neutral-400 leading-relaxed">
                        If extreme risk is flagged (Level 4), session containment executes immediately. All active session keys are revoked and blacklisted globally, logging out the active browser immediately to freeze account activity.
                      </p>
                    </div>
                  </div>
                </div>

                {/* Ticket Form */}
                <div className="md:col-span-2">
                  <form onSubmit={handleSupportSubmit} className="bg-neutral-900 border border-white/[0.06] rounded-xl p-6 space-y-4">
                    <h3 className="text-sm font-semibold tracking-wide text-white">Submit Secure Ticket</h3>
                    
                    {supportSuccess && (
                      <div className="p-3 bg-teal-500/10 border border-teal-500/25 rounded-lg text-[11px] text-teal-300 flex items-center gap-2">
                        <CheckCircle size={14} />
                        <span>Ticket submitted and encrypted. Reference #ST-{Math.floor(100000 + Math.random()*900000)}</span>
                      </div>
                    )}

                    <div className="space-y-1.5">
                      <label className="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Inquiry Category</label>
                      <select 
                        value={supportTopic} 
                        onChange={(e) => setSupportTopic(e.target.value)}
                        className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-teal-500/50"
                      >
                        <option value="general">General Support</option>
                        <option value="security">Security Alert Concern</option>
                        <option value="dispute">Dispute Transaction</option>
                      </select>
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Detailed Message</label>
                      <textarea 
                        rows={4}
                        placeholder="Write support details here..."
                        value={supportMessage}
                        onChange={(e) => setSupportMessage(e.target.value)}
                        className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-teal-500/50"
                      ></textarea>
                    </div>

                    <button 
                      type="submit" 
                      disabled={!supportMessage.trim()}
                      className="w-full py-2 bg-teal-500 hover:bg-teal-400 disabled:bg-neutral-800 disabled:text-neutral-500 text-black font-semibold text-xs rounded-lg transition-colors"
                    >
                      Encrypt & Send
                    </button>
                  </form>
                </div>
              </div>
            </div>
          )}

        </main>
      </div>

      {/* Simulated SMS Notification Popup (To display step-up verification codes) */}
      {smsNotification && (
        <div className="fixed bottom-6 right-6 max-w-sm w-full bg-neutral-900 border-l-4 border-teal-500 rounded-lg p-4 shadow-2xl flex items-start space-x-3.5 z-50 animate-bounce">
          <div className="grid place-items-center w-8 h-8 rounded-full bg-teal-500/10 border border-teal-500/20 text-teal-400 shrink-0 mt-0.5">
            <Smartphone size={16} />
          </div>
          <div className="flex-1 space-y-1">
            <p className="text-xs font-bold text-white flex items-center justify-between">
              <span>SMS Notification</span>
              <span className="text-[10px] text-neutral-500 font-normal">Just now</span>
            </p>
            <p className="text-xs text-neutral-300 leading-relaxed font-mono">{smsNotification}</p>
          </div>
        </div>
      )}

      {/* Step-up Authentication (OTP) Modal */}
      {showOtpModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-6 z-50">
          <div className="max-w-md w-full bg-neutral-900 border border-white/[0.08] rounded-xl p-6 shadow-2xl space-y-5 relative">
            <div className="flex items-center space-x-3 text-amber-400">
              <Shield size={22} />
              <h3 className="text-base font-bold text-white tracking-wide">Step-up Authentication Required</h3>
            </div>
            
            <p className="text-xs text-neutral-400 leading-relaxed">
              Moderate transaction risk has been signaled. To complete this transfer, please input the 6-digit confirmation code dispatched to your registered phone.
            </p>

            {otpError && (
              <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-xs text-red-400">
                {otpError}
              </div>
            )}

            <form onSubmit={handleOtpVerify} className="space-y-4">
              <input 
                type="text" 
                maxLength={6}
                placeholder="000000"
                value={otpCode}
                onChange={(e) => setOtpCode(e.target.value)}
                className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg py-3 text-center text-lg font-bold font-mono text-white tracking-[0.4em] focus:outline-none focus:border-teal-500/50"
              />

              <button 
                type="submit"
                disabled={otpCode.length < 6}
                className="w-full py-2.5 bg-teal-500 hover:bg-teal-400 disabled:bg-neutral-800 disabled:text-neutral-500 text-black font-bold text-xs rounded-lg transition-colors"
              >
                Verify Cryptographic Code
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Cryptographic Details Inspector Modal */}
      {showCryptoModal && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center p-6 z-50">
          <div className="max-w-lg w-full bg-neutral-900 border border-white/[0.08] rounded-xl p-6 shadow-2xl space-y-5">
            <div className="flex items-center justify-between pb-3 border-b border-white/[0.06]">
              <div className="flex items-center space-x-2 text-teal-400">
                <Key size={18} />
                <h3 className="text-sm font-bold text-white uppercase tracking-wider">Cryptographic Parameters</h3>
              </div>
              <button 
                onClick={() => setShowCryptoModal(false)}
                className="text-xs text-neutral-500 hover:text-white"
              >
                Close
              </button>
            </div>

            <div className="space-y-4 text-xs">
              <div className="grid grid-cols-3 gap-2 py-1.5 border-b border-white/[0.04]">
                <span className="text-neutral-500">Session ID:</span>
                <span className="col-span-2 font-mono text-neutral-300 break-all">{cryptoState.sessionId}</span>
              </div>
              <div className="grid grid-cols-3 gap-2 py-1.5 border-b border-white/[0.04]">
                <span className="text-neutral-500">Active Cipher:</span>
                <span className="col-span-2 font-mono font-bold text-teal-400">AES-256-GCM (Galois/Counter Mode)</span>
              </div>
              <div className="grid grid-cols-3 gap-2 py-1.5 border-b border-white/[0.04]">
                <span className="text-neutral-500">Key Version:</span>
                <span className="col-span-2 font-mono text-neutral-300">Version {cryptoState.keyVersion} (Active)</span>
              </div>
              <div className="grid grid-cols-3 gap-2 py-1.5 border-b border-white/[0.04]">
                <span className="text-neutral-500">Active Symmetric Key:</span>
                <span className="col-span-2 font-mono text-neutral-400 select-all break-all">{formatKey(cryptoState.aesKey)}</span>
              </div>
              <div className="grid grid-cols-3 gap-2 py-1.5 border-b border-white/[0.04]">
                <span className="text-neutral-500">Session JWT Token:</span>
                <span className="col-span-2 font-mono text-[10px] text-neutral-500 break-all truncate">Signed (HS256, HTTP-Only Cookie)</span>
              </div>
              <div className="grid grid-cols-3 gap-2 py-1.5">
                <span className="text-neutral-500">Key Shuffling Rule:</span>
                <span className="col-span-2 text-neutral-400 leading-relaxed">
                  Upon risk escalation (L1 → L2, L2 → L3), the backend shuffles the active session key, invalidating past key versions and forcing local storage update. On L4, keys are purged.
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
