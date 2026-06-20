import re

with open('ui/surfaces/customer/context/AppContext.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Add incomingNotification to AppContextType
if 'incomingNotification: any;' not in content:
    content = content.replace(
        '  triggerKeyDesyncError: () => void;',
        '  triggerKeyDesyncError: () => void;\n  incomingNotification: any;\n  setIncomingNotification: React.Dispatch<React.SetStateAction<any>>;'
    )

# 2. Add incomingNotification state to AppProvider
if 'const [incomingNotification, setIncomingNotification]' not in content:
    content = content.replace(
        '  const [keyRotatedAnim, setKeyRotatedAnim] = useState(false);',
        '  const [keyRotatedAnim, setKeyRotatedAnim] = useState(false);\n  const [incomingNotification, setIncomingNotification] = useState<any>(null);'
    )

# 3. Add WebSocket connection logic inside AppProvider
ws_logic = """
  useEffect(() => {
    let ws: WebSocket;
    if (isAuthenticated && cryptoState.sessionId) {
      ws = new WebSocket(`ws://localhost:8001/customer/ws?session_id=${cryptoState.sessionId}`);
      
      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === "INCOMING_TRANSFER") {
            setIncomingNotification(data);
            refreshData(); // automatically refresh balances and ledger
            setTimeout(() => setIncomingNotification(null), 8000);
          }
        } catch (e) {
          console.error("Failed to parse websocket message");
        }
      };

      ws.onclose = () => {
        console.log("WebSocket disconnected");
      };
    }

    return () => {
      if (ws) {
        ws.close();
      }
    };
  }, [isAuthenticated, cryptoState.sessionId]);
"""

if 'ws = new WebSocket' not in content:
    content = content.replace(
        '  const triggerKeyDesyncError = () => {',
        ws_logic + '\n  const triggerKeyDesyncError = () => {'
    )

# 4. Expose incomingNotification in Provider value
if 'incomingNotification, setIncomingNotification' not in content:
    content = content.replace(
        '      triggerKeyDesyncError',
        '      triggerKeyDesyncError,\n      incomingNotification, setIncomingNotification'
    )

with open('ui/surfaces/customer/context/AppContext.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
