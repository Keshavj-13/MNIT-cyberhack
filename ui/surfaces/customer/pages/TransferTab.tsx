import React, { useState } from 'react';
import { CheckCircle, Shield } from 'lucide-react';
import { useAppContext } from '../context/AppContext';
import { initiateTransfer, confirmTransfer } from '../api';

export default function TransferTab() {
  const { cryptoState, animateKeyRotation, triggerKeyDesyncError, refreshData } = useAppContext();
  
  const [transferAmount, setTransferAmount] = useState('');
  const [targetBankingId, setTargetBankingId] = useState('');
  const [transferPassword, setTransferPassword] = useState('');
  const [pendingTxId, setPendingTxId] = useState(0);
  const [transferStatus, setTransferStatus] = useState<any>(null);
  const [isTransferring, setIsTransferring] = useState(false);
  const [smsNotification, setSmsNotification] = useState<string | null>(null);

  const [showOtpModal, setShowOtpModal] = useState(false);
  const [otpCode, setOtpCode] = useState('');
  const [otpError, setOtpError] = useState('');

  const handleTransferSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetBankingId || !transferAmount || !transferPassword) return;
    
    const amountNum = parseFloat(transferAmount);
    if (isNaN(amountNum) || amountNum <= 0) {
      alert("Invalid transfer amount");
      return;
    }

    setIsTransferring(true);
    setTransferStatus(null);

    try {
      const res = await initiateTransfer(cryptoState, amountNum, targetBankingId, transferPassword);
      
      if (res.key_rotated && res.new_key) {
        animateKeyRotation(res.new_key, res.new_key_version, res.risk_level);
      }

      setPendingTxId(res.transaction_id);
      setShowOtpModal(true);
      setSmsNotification(`OTP dispatched to your registered email for transferring $${amountNum}`);
      setTimeout(() => setSmsNotification(null), 10000);
      
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

  const handleOtpVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    if (otpCode.length < 6 || !pendingTxId) return;

    setOtpError('');
    try {
      await confirmTransfer(cryptoState, pendingTxId, otpCode);
      setShowOtpModal(false);
      setTransferStatus({ status: 'approved', message: "Transfer verified & completed successfully." });
      setTransferAmount('');
      setTargetBankingId('');
      setTransferPassword('');
      setOtpCode('');
      setPendingTxId(0);
      refreshData();
    } catch (err: any) {
      setOtpError(err.response?.data?.detail || 'Authentication rejected.');
    }
  };

  return (
    <>
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
            <label className="text-xs font-semibold text-neutral-400 uppercase tracking-wider">Recipient Banking ID</label>
            <input 
              type="text"
              placeholder="e.g. CBI-XXXXXXXX"
              value={targetBankingId}
              onChange={(e) => setTargetBankingId(e.target.value.toUpperCase())}
              className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-teal-500/50 font-mono tracking-widest"
            />
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
          
          <div className="space-y-1.5">
            <label className="text-xs font-semibold text-neutral-400 uppercase tracking-wider">Account Password</label>
            <input 
              type="password"
              placeholder="Enter your password to authorize"
              value={transferPassword}
              onChange={(e) => setTransferPassword(e.target.value)}
              className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:border-teal-500/50"
            />
          </div>

          <div className="bg-neutral-950 p-4 rounded-lg border border-white/[0.04] text-[11px] text-neutral-400 space-y-1">
            <span className="font-semibold text-neutral-300 block mb-1">Cryptographic Policy Notice</span>
            <p>Upon submission, this request payload is encrypted locally using the active session key (v{cryptoState.keyVersion}).</p>
            <p>In accordance with the Threat Engine, transaction evaluation will execute silently. An OTP step-up verification will be requested via Email.</p>
          </div>

          <button 
            type="submit"
            disabled={isTransferring || !targetBankingId || !transferAmount || !transferPassword}
            className="w-full py-3 bg-teal-500 hover:bg-teal-400 disabled:bg-neutral-800 disabled:text-neutral-500 text-black font-bold text-sm rounded-lg transition-colors flex items-center justify-center gap-2"
          >
            {isTransferring ? 'Encrypting & Dispatching...' : 'Secure Transfer'}
          </button>
        </form>
      </div>

      {smsNotification && (
        <div className="fixed bottom-6 right-6 bg-neutral-900 border border-white/[0.1] rounded-xl p-4 shadow-2xl z-50 flex items-start gap-4 max-w-sm animate-in slide-in-from-bottom-5">
          <div className="bg-teal-500/20 p-2 rounded-lg text-teal-400"><Shield size={20} /></div>
          <div className="space-y-1">
            <p className="text-sm font-bold text-white flex justify-between items-center">
              <span>SMS Notification</span>
              <span className="text-[10px] text-neutral-500 font-normal">Just now</span>
            </p>
            <p className="text-xs text-neutral-300 leading-relaxed font-mono">{smsNotification}</p>
          </div>
        </div>
      )}

      {showOtpModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center p-6 z-50">
          <div className="max-w-md w-full bg-neutral-900 border border-white/[0.08] rounded-xl p-6 shadow-2xl space-y-5 relative">
            <div className="flex items-center space-x-3 text-amber-400">
              <Shield size={22} />
              <h3 className="text-base font-bold text-white tracking-wide">Step-up Authentication Required</h3>
            </div>
            
            <p className="text-xs text-neutral-400 leading-relaxed">
              Moderate transaction risk has been signaled. To complete this transfer, please input the 6-digit confirmation code dispatched to your registered phone/email.
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
    </>
  );
}
