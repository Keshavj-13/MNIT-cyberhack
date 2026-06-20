import re

with open('ui/surfaces/customer/App.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add incomingNotification to useAppContext destructuring
if 'incomingNotification' not in content:
    content = content.replace(
        'keyRotationInfo, showCryptoModal, setShowCryptoModal, keyRotatedAnim,',
        'keyRotationInfo, showCryptoModal, setShowCryptoModal, keyRotatedAnim,\n    incomingNotification,'
    )

# 2. Add the Toast notification JSX before the Cryptographic Details Inspector Modal
toast_jsx = """
      {/* Real-time Incoming Transfer Notification Toast */}
      {incomingNotification && (
        <div className="fixed top-6 right-6 max-w-sm w-full bg-neutral-900 border-l-4 border-emerald-500 rounded-lg p-4 shadow-2xl flex items-start space-x-3.5 z-[60] animate-[slideIn_0.5s_ease-out]">
          <div className="grid place-items-center w-8 h-8 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 shrink-0 mt-0.5">
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg>
          </div>
          <div className="flex-1 space-y-1">
            <p className="text-xs font-bold text-white flex items-center justify-between">
              <span>Incoming Transfer</span>
              <span className="text-[10px] text-neutral-500 font-normal">Just now</span>
            </p>
            <p className="text-xs text-neutral-300 leading-relaxed font-mono">
              You received <span className="text-emerald-400 font-bold">${incomingNotification.amount?.toLocaleString()}</span> from {incomingNotification.sender}.
            </p>
          </div>
        </div>
      )}
"""

if 'Real-time Incoming Transfer Notification Toast' not in content:
    content = content.replace(
        '{/* Cryptographic Details Inspector Modal */}',
        toast_jsx + '\n      {/* Cryptographic Details Inspector Modal */}'
    )

with open('ui/surfaces/customer/App.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
