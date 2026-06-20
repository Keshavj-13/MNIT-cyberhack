import React, { createContext, useContext, useState, useEffect } from 'react';
import { getMe, getAccountDetails, getStatements, getBeneficiaries } from '../api';

interface AppContextType {
  cryptoState: any;
  setCryptoState: React.Dispatch<React.SetStateAction<any>>;
  isAuthenticated: boolean;
  setIsAuthenticated: React.Dispatch<React.SetStateAction<boolean>>;
  username: string;
  setUsername: React.Dispatch<React.SetStateAction<string>>;
  balances: any;
  setBalances: React.Dispatch<React.SetStateAction<any>>;
  transactions: any[];
  setTransactions: React.Dispatch<React.SetStateAction<any[]>>;
  beneficiaries: any[];
  setBeneficiaries: React.Dispatch<React.SetStateAction<any[]>>;
  refreshData: () => Promise<void>;
  keyRotationInfo: any;
  setKeyRotationInfo: React.Dispatch<React.SetStateAction<any>>;
  showCryptoModal: boolean;
  setShowCryptoModal: React.Dispatch<React.SetStateAction<boolean>>;
  keyRotatedAnim: boolean;
  setKeyRotatedAnim: React.Dispatch<React.SetStateAction<boolean>>;
  animateKeyRotation: (newKey: string, newVersion: number, newRisk: number) => void;
  triggerKeyDesyncError: () => void;
  incomingNotification: any;
  setIncomingNotification: React.Dispatch<React.SetStateAction<any>>;
}

const AppContext = createContext<AppContextType | null>(null);

export function AppProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(() => sessionStorage.getItem('cbi_crypto_state') !== null);
  const [username, setUsername] = useState(() => sessionStorage.getItem('cbi_username') || '');
  
  const [cryptoState, setCryptoState] = useState(() => {
    const saved = sessionStorage.getItem('cbi_crypto_state');
    if (saved) {
      try { return JSON.parse(saved); } catch (e) {}
    }
    return { aesKey: '', keyVersion: 1, sessionId: '', riskLevel: 1 };
  });

  const [balances, setBalances] = useState<any>({ checking: { balance: 0 }, savings: { balance: 0 } });
  const [transactions, setTransactions] = useState<any[]>([]);
  const [beneficiaries, setBeneficiaries] = useState<any[]>([]);
  
  const [keyRotationInfo, setKeyRotationInfo] = useState<any>(null);
  const [showCryptoModal, setShowCryptoModal] = useState(false);
  const [keyRotatedAnim, setKeyRotatedAnim] = useState(false);
  const [incomingNotification, setIncomingNotification] = useState<any>(null);

  useEffect(() => {
    if (isAuthenticated && cryptoState.aesKey) {
      sessionStorage.setItem('cbi_crypto_state', JSON.stringify(cryptoState));
      sessionStorage.setItem('cbi_username', username);
    } else if (!isAuthenticated) {
      sessionStorage.removeItem('cbi_crypto_state');
      sessionStorage.removeItem('cbi_username');
    }
  }, [cryptoState, isAuthenticated, username]);

  useEffect(() => {
    async function verifySession() {
      if (isAuthenticated) {
        try {
          const me = await getMe();
          if (me.session_id === cryptoState.sessionId) {
            setCryptoState((prev: any) => ({
              ...prev,
              keyVersion: me.key_version,
              riskLevel: me.risk_level
            }));
          } else {
            setIsAuthenticated(false);
          }
        } catch (err) {
          setIsAuthenticated(false);
        }
      }
    }
    verifySession();
  }, [isAuthenticated]);

  const refreshData = async () => {
    if (!isAuthenticated || !cryptoState.aesKey) return;
    try {
      const [acc, stmt, ben] = await Promise.all([
        getAccountDetails(cryptoState),
        getStatements(cryptoState),
        getBeneficiaries(cryptoState)
      ]);
      if (acc.checking) setBalances(acc);
      if (Array.isArray(stmt)) setTransactions(stmt);
      if (Array.isArray(ben)) setBeneficiaries(ben);
    } catch (err) {
      console.error('Failed to sync state with backend');
    }
  };

  useEffect(() => {
    if (isAuthenticated && cryptoState.aesKey) {
      refreshData();
    }
  }, [isAuthenticated, cryptoState.aesKey, cryptoState.keyVersion]);

  const animateKeyRotation = (newKey: string, newVersion: number, newRisk: number) => {
    setKeyRotationInfo({ version: newVersion, riskLevel: newRisk });
    setKeyRotatedAnim(true);
    setTimeout(() => {
      setCryptoState((prev: any) => ({ ...prev, aesKey: newKey, keyVersion: newVersion, riskLevel: newRisk }));
      setKeyRotatedAnim(false);
      refreshData();
    }, 2500);
  };


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

  const triggerKeyDesyncError = () => {
    setShowCryptoModal(true);
    setIsAuthenticated(false);
  };

  return (
    <AppContext.Provider value={{
      cryptoState, setCryptoState,
      isAuthenticated, setIsAuthenticated,
      username, setUsername,
      balances, setBalances,
      transactions, setTransactions,
      beneficiaries, setBeneficiaries,
      refreshData,
      keyRotationInfo, setKeyRotationInfo,
      showCryptoModal, setShowCryptoModal,
      keyRotatedAnim, setKeyRotatedAnim,
      animateKeyRotation,
      triggerKeyDesyncError
    }}>
      {children}
    </AppContext.Provider>
  );
}

export function useAppContext() {
  const context = useContext(AppContext);
  if (!context) {
    throw new Error('useAppContext must be used within an AppProvider');
  }
  return context;
}
