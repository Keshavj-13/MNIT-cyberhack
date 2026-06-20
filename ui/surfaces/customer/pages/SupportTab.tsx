import React, { useState } from 'react';
import { CheckCircle } from 'lucide-react';

export default function SupportTab() {
  const [supportTopic, setSupportTopic] = useState('general');
  const [supportMessage, setSupportMessage] = useState('');
  const [supportSuccess, setSupportSuccess] = useState(false);

  const handleSupportSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!supportMessage) return;
    setSupportSuccess(true);
    setTimeout(() => {
      setSupportSuccess(false);
      setSupportMessage('');
    }, 4000);
  };

  return (
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
              <div className="p-3 bg-teal-500/10 border border-teal-500/25 rounded-lg flex items-center gap-2 text-xs text-teal-300">
                <CheckCircle size={14} />
                <span>Ticket submitted successfully via secure channel.</span>
              </div>
            )}

            <div className="space-y-1.5">
              <label className="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Topic</label>
              <select 
                value={supportTopic}
                onChange={(e) => setSupportTopic(e.target.value)}
                className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-teal-500/50 appearance-none"
              >
                <option value="general">General Inquiry</option>
                <option value="security">Report Suspicious Activity</option>
                <option value="technical">Technical Error</option>
                <option value="transfer">Transfer Dispute</option>
              </select>
            </div>

            <div className="space-y-1.5">
              <label className="text-[10px] font-semibold text-neutral-400 uppercase tracking-wider">Message</label>
              <textarea 
                rows={4}
                value={supportMessage}
                onChange={(e) => setSupportMessage(e.target.value)}
                placeholder="Describe your issue securely..."
                className="w-full bg-neutral-950 border border-white/[0.08] rounded-lg px-3 py-2 text-xs focus:outline-none focus:border-teal-500/50 resize-none"
              ></textarea>
            </div>

            <button 
              type="submit"
              disabled={!supportMessage}
              className="w-full py-2 bg-neutral-100 hover:bg-white text-black font-bold text-xs rounded-lg transition-colors disabled:opacity-50"
            >
              Submit Ticket
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
