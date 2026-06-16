import { useState } from 'react';
import { AlertOctagon, Lock, ChevronLeft } from 'lucide-react';
import { evaluate } from './api';

interface PhishingPageProps {
  sessionId: string;
  url: string;
  onResult: (result: any) => void;
  onBack: () => void;
}

const PhishingPage = ({ sessionId, url, onResult, onBack }: PhishingPageProps) => {
  const [submitted, setSubmitted] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    try {
      const result = await evaluate({ url }, sessionId);
      onResult(result);
      setSubmitted(true);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="p-6 max-w-md mx-auto">
      <button
        onClick={onBack}
        className="flex items-center space-x-1 text-sm text-neutral-400 hover:text-white mb-4"
      >
        <ChevronLeft size={16} />
        <span>Back</span>
      </button>

      <div className="mb-4 flex items-center space-x-2 text-amber-400 text-xs bg-amber-500/10 border border-amber-600/30 rounded-lg p-3">
        <AlertOctagon size={16} />
        <span>Demo only: this page simulates a cloned phishing site reached via the SMS link ({url}).</span>
      </div>

      <div className="bg-white rounded-2xl p-8 shadow-xl text-neutral-900">
        <div className="flex items-center justify-center mb-6 space-x-2">
          <div className="bg-red-600 rounded-xl p-2">
            <Lock className="text-white" size={22} />
          </div>
          <h1 className="text-xl font-bold">SecureTrust-Verify</h1>
        </div>
        <p className="text-center text-sm mb-6 font-semibold text-red-600">
          Your account is on hold. Verify your identity now to restore access.
        </p>

        {submitted ? (
          <div className="text-center text-sm text-neutral-700 space-y-2">
            <p className="font-semibold">"Verification" submitted.</p>
            <p>Check the Live Risk HUD — this interaction has been flagged as a HOOK event.</p>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="block text-xs font-medium text-neutral-600 mb-1">Account Username</label>
              <input className="w-full border border-neutral-300 rounded-lg px-3 py-2 text-sm" placeholder="rajesh.kumar" />
            </div>
            <div>
              <label className="block text-xs font-medium text-neutral-600 mb-1">Password</label>
              <input type="password" className="w-full border border-neutral-300 rounded-lg px-3 py-2 text-sm" placeholder="••••••••" />
            </div>
            <div>
              <label className="block text-xs font-medium text-neutral-600 mb-1">One-Time Passcode</label>
              <input className="w-full border border-neutral-300 rounded-lg px-3 py-2 text-sm" placeholder="123456" />
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-red-600 hover:bg-red-700 disabled:opacity-50 text-white font-semibold py-2 rounded-lg transition-colors"
            >
              {loading ? 'Verifying…' : 'Verify Account'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
};

export default PhishingPage;
