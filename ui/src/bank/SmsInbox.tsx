import { useState } from 'react';
import { MessageSquare, AlertTriangle, ExternalLink, ChevronLeft } from 'lucide-react';
import { evaluate } from './api';

export const SMISHING_SMS =
  "URGENT: Verify your identity at secure-bank.com immediately or your account will be suspended.";
export const PHISHING_URL = "secure-bank.com";

const MESSAGES = [
  {
    id: 1,
    from: 'SecureTrust Bank',
    time: 'Today, 09:14',
    text: 'Your monthly e-statement is now available. Log in to the app to view it.',
    suspicious: false,
  },
  {
    id: 2,
    from: 'SecureTrust-Alert',
    time: 'Today, 09:42',
    text: SMISHING_SMS,
    suspicious: true,
  },
];

interface SmsInboxProps {
  sessionId: string;
  onResult: (result: any) => void;
  onOpenLink: (url: string) => void;
}

const SmsInbox = ({ sessionId, onResult, onOpenLink }: SmsInboxProps) => {
  const [openId, setOpenId] = useState<number | null>(null);
  const [evaluated, setEvaluated] = useState<Set<number>>(new Set());

  const openMessage = async (msg: typeof MESSAGES[number]) => {
    setOpenId(msg.id);
    if (msg.suspicious && !evaluated.has(msg.id)) {
      try {
        const result = await evaluate({ sms_text: msg.text }, sessionId);
        onResult(result);
      } catch (err) {
        console.error(err);
      }
      setEvaluated((prev) => new Set(prev).add(msg.id));
    }
  };

  const open = MESSAGES.find((m) => m.id === openId);

  if (open) {
    return (
      <div className="p-6 max-w-2xl mx-auto">
        <button
          onClick={() => setOpenId(null)}
          className="flex items-center space-x-1 text-sm text-neutral-400 hover:text-white mb-4"
        >
          <ChevronLeft size={16} />
          <span>Back to inbox</span>
        </button>
        <div className="bg-neutral-900 border border-white/5 rounded-xl p-5">
          <div className="flex items-center justify-between mb-3">
            <span className="font-semibold text-white">{open.from}</span>
            <span className="text-xs text-neutral-500">{open.time}</span>
          </div>
          <p className="text-neutral-200 leading-relaxed">{open.text}</p>

          {open.suspicious && (
            <>
              <div className="mt-4 flex items-center space-x-2 text-amber-400 text-xs bg-amber-500/10 border border-amber-600/30 rounded-lg p-3">
                <AlertTriangle size={16} />
                <span>This message was just analyzed by the Risk Engine — check the Live Risk HUD.</span>
              </div>
              <button
                onClick={() => onOpenLink(PHISHING_URL)}
                className="mt-4 w-full flex items-center justify-center space-x-2 bg-red-600/20 hover:bg-red-600/30 border border-red-600/40 text-red-300 font-medium py-2 rounded-lg transition-colors"
              >
                <ExternalLink size={16} />
                <span>Open link: {PHISHING_URL}</span>
              </button>
            </>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="p-6 max-w-2xl mx-auto">
      <h2 className="text-lg font-bold text-white mb-4 flex items-center space-x-2">
        <MessageSquare size={20} />
        <span>SMS Inbox</span>
      </h2>
      <div className="space-y-2">
        {MESSAGES.map((msg) => (
          <button
            key={msg.id}
            onClick={() => openMessage(msg)}
            className={`w-full text-left bg-neutral-900 border rounded-xl p-4 transition-colors hover:border-neutral-600 ${
              msg.suspicious ? 'border-amber-600/40' : 'border-white/5'
            }`}
          >
            <div className="flex items-center justify-between mb-1">
              <span className="font-semibold text-white flex items-center space-x-1">
                {msg.suspicious && <AlertTriangle size={14} className="text-amber-400" />}
                <span>{msg.from}</span>
              </span>
              <span className="text-xs text-neutral-500">{msg.time}</span>
            </div>
            <p className="text-sm text-neutral-400 truncate">{msg.text}</p>
          </button>
        ))}
      </div>
    </div>
  );
};

export default SmsInbox;
