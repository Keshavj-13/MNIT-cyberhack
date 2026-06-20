import React, { useState, useEffect, useRef } from 'react';
import { 
  Shield, Landmark, LogOut, LayoutDashboard, Send, Users, 
  FileText, HelpCircle, Key, RefreshCw, AlertTriangle, CheckCircle, Lock, Info, Smartphone, X, ChevronDown, ChevronRight, Globe, Phone, Search, Menu
} from 'lucide-react';
import { 
  loginCustomer, logoutCustomer, getAccountDetails, 
  getStatements, getBeneficiaries, addBeneficiary, initiateTransfer, confirmTransfer,
  registerCustomer, sendOTP, verifyOTP, getMe
} from './api';
import { useTelemetry } from './hooks/useTelemetry';
import { usePreferences } from './Preferences';
import cyberFraudImg from '../../images/cyber-fraud.jfif';

import { useAppContext } from './context/AppContext';
const DashboardTab = React.lazy(() => import('./pages/DashboardTab'));
const TransferTab = React.lazy(() => import('./pages/TransferTab'));
const BeneficiariesTab = React.lazy(() => import('./pages/BeneficiariesTab'));
const StatementsTab = React.lazy(() => import('./pages/StatementsTab'));
const SupportTab = React.lazy(() => import('./pages/SupportTab'));

import digitalBankingImg from '../../images/digital-banking.jfif';
import homeLoanImg from '../../images/home-loan.jfif';
import agriGoldLoanImg from '../../images/agri-gold-loan.jfif';
import educationLoanImg from '../../images/education-loan.png';

const T: Record<string, any> = {
  en: {
    lang_en: 'English',
    lang_hi: 'हिंदी',
    toll_free: 'Toll Free: 1800 30 30 - for all',
    toll_free_pen: '18002031911 - Exclusively for Pensioner',
    cyber_crime: 'National Cyber Crime Helpline - 1930',
    home: 'Home',
    about: 'About Us',
    branch: 'Branch/ATM/BC Locator',
    contact: 'Contact Us',
    career: 'Career with us',
    investor: 'Investor Relations',
    login_btn: 'Proceed to Dashboard',
  },
  hi: {
    lang_en: 'English',
    lang_hi: 'हिंदी',
    toll_free: 'टोल फ्री: 1800 30 30 - सभी के लिए',
    toll_free_pen: '18002031911 - विशेष रूप से पेंशनभोगी के लिए',
    cyber_crime: 'राष्ट्रीय साइबर अपराध हेल्पलाइन - 1930',
    home: 'होम',
    about: 'हमारे बारे में',
    branch: 'शाखा/एटीएम',
    contact: 'संपर्क करें',
    career: 'करियर',
    investor: 'निवेशक संबंध',
    login_btn: 'डैशबोर्ड पर आगे बढ़ें',
  }
};

export default function App() {
  const pref = usePreferences();
  const t = (key: string) => T[pref.lang][key] || key;

  const { 
    cryptoState, setCryptoState, isAuthenticated, setIsAuthenticated, username, setUsername,
    keyRotationInfo, showCryptoModal, setShowCryptoModal, keyRotatedAnim,
    incomingNotification,
    refreshData 
  } = useAppContext();

  // Login UI state
  const [password, setPassword] = useState('');
  const [authError, setAuthError] = useState('');
  const [loading, setLoading] = useState(false);

  // Navigation UI state
  const [activeTab, setActiveTab] = useState('dashboard');
  const [showLoginModal, setShowLoginModal] = useState(false);
  const [currentSlide, setCurrentSlide] = useState(0);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  // Registration / Sign-up state
  const [authModalTab, setAuthModalTab] = useState<'signin' | 'signup'>('signin');
  const [regStep, setRegStep] = useState(1); // 1=details, 2=email OTP, 3=phone OTP, 4=success
  const [regUsername, setRegUsername] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPhone, setRegPhone] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regConfirmPassword, setRegConfirmPassword] = useState('');
  const [regError, setRegError] = useState('');
  const [regLoading, setRegLoading] = useState(false);
  // OTP verification state for registration
  const [regEmailOtp, setRegEmailOtp] = useState('');
  const [regPhoneOtp, setRegPhoneOtp] = useState('');
  const [regOtpError, setRegOtpError] = useState('');
  const [regBankingId, setRegBankingId] = useState('');
  const [regOtpLoading, setRegOtpLoading] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);

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
    setShowCryptoModal(false);
  };

  // --- Registration Handlers ---
  const passwordChecks = (pw: string) => ({
    minLength: pw.length >= 14,
    hasUpper: /[A-Z]/.test(pw),
    hasLower: /[a-z]/.test(pw),
    hasDigit: /[0-9]/.test(pw),
    hasSpecial: /[!@#$%^&*()_+\-=\[\]{};':"\\|,.<>\/?`~]/.test(pw),
  });

  const isPasswordStrong = (pw: string) => {
    const c = passwordChecks(pw);
    return c.minLength && c.hasUpper && c.hasLower && c.hasDigit && c.hasSpecial;
  };

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setRegError('');
    if (!regUsername || !regEmail || !regPhone || !regPassword) {
      setRegError('All fields are required.');
      return;
    }
    if (regPassword !== regConfirmPassword) {
      setRegError('Passwords do not match.');
      return;
    }
    if (!isPasswordStrong(regPassword)) {
      setRegError('Password does not meet all strength requirements.');
      return;
    }
    setRegLoading(true);
    try {
      const regRes = await registerCustomer(regUsername, regEmail, regPhone, regPassword);
      setRegBankingId(regRes.banking_id);
      // Auto-send email OTP
      await sendOTP(regEmail, 'email');
      setRegStep(2);
      startResendCooldown();
    } catch (err: any) {
      setRegError(err.response?.data?.detail || 'Registration failed.');
    } finally {
      setRegLoading(false);
    }
  };

  const handleSendRegOtp = async (channel: 'email' | 'phone') => {
    setRegOtpError('');
    const identifier = channel === 'email' ? regEmail : regPhone;
    try {
      await sendOTP(identifier, channel);
      startResendCooldown();
    } catch (err: any) {
      setRegOtpError(err.response?.data?.detail || 'Failed to send code.');
    }
  };

  const handleVerifyRegOtp = async (channel: 'email' | 'phone') => {
    setRegOtpError('');
    setRegOtpLoading(true);
    const identifier = channel === 'email' ? regEmail : regPhone;
    const code = channel === 'email' ? regEmailOtp : regPhoneOtp;
    try {
      await verifyOTP(identifier, code, channel);
      if (channel === 'email') {
        // Move to phone verification — auto-send phone OTP
        await sendOTP(regPhone, 'phone');
        setRegStep(3);
        startResendCooldown();
      } else {
        // Both verified — go to success
        setRegStep(4);
      }
    } catch (err: any) {
      setRegOtpError(err.response?.data?.detail || 'Verification failed.');
    } finally {
      setRegOtpLoading(false);
    }
  };

  const startResendCooldown = () => {
    setResendCooldown(60);
    const timer = setInterval(() => {
      setResendCooldown(prev => {
        if (prev <= 1) { clearInterval(timer); return 0; }
        return prev - 1;
      });
    }, 1000);
  };

  const resetRegState = () => {
    setRegStep(1);
    setRegUsername(''); setRegEmail(''); setRegPhone('');
    setRegPassword(''); setRegConfirmPassword('');
    setRegError(''); setRegOtpError('');
    setRegEmailOtp(''); setRegPhoneOtp('');
    setRegBankingId('');
    setResendCooldown(0);
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

  // CBI Homepage Banner Slides
  const bannerSlides = [
    { alt: 'Cyber Fraud Awareness', image: cyberFraudImg, gradient: 'from-red-700 to-red-900', text: 'Beware of Cyber Fraud\n1930 - National Cyber Crime Helpline', icon: '🛡️' },
    { alt: 'Digital Banking', image: digitalBankingImg, gradient: 'from-blue-700 to-blue-900', text: 'Digital Banking\nInternet Banking | Mobile Banking | UPI', icon: '💻' },
    { alt: 'Home Loans', image: homeLoanImg, gradient: 'from-emerald-700 to-emerald-900', text: 'Cent Home Loan\nMake Your Dream Home a Reality', icon: '🏠' },
    { alt: 'Gold Loan Scheme', image: agriGoldLoanImg, gradient: 'from-amber-700 to-amber-900', text: 'Cent Agri Gold Loan\nQuick & Easy Processing', icon: '✨' },
    { alt: 'Education Loan', image: educationLoanImg, gradient: 'from-purple-700 to-purple-900', text: 'Vidyarthi Education Loan\nInvest in Your Future', icon: '🎓' },
  ];

  // Auto-rotate slides
  useEffect(() => {
    if (isAuthenticated) return;
    const timer = setInterval(() => {
      setCurrentSlide(prev => (prev + 1) % bannerSlides.length);
    }, 4000);
    return () => clearInterval(timer);
  }, [isAuthenticated]);

  // Whats New items
  const whatsNewItems = [
    { text: 'CardRate 18.06.2026', link: '#' },
    { text: 'Cent rewards platform now available via centrewardz.centralbank.bank.in', link: '#' },
    { text: 'Form 15G/15H replaced by Form 121; Form 60 replaced by Form 97 w.e.f. 01.04.2026', link: '#' },
    { text: 'Block lost card: SMS to 917738002672 from registered mobile', link: '#' },
    { text: 'Online DEAF Claim Settlement Portal', link: '#' },
    { text: 'Notice to Customers on Continuous Clearing', link: '#' },
    { text: 'SoundBox with QR code available for eligible customers', link: '#' },
  ];

  // Login Screen — CBI Homepage Recreation
  if (!isAuthenticated) {
    return (
      <>
        <style>{`
          /* ===== CBI HOMEPAGE STYLES ===== */
          @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
          
          .cbi-page { font-family: 'Inter', Arial, sans-serif; background: #fff; color: #333; min-height: 100vh; overflow-x: hidden; }
          
          /* Top Header */
          .cbi-top-header { background: linear-gradient(90deg, #003893 0%, #002266 100%); color: white; font-size: 12px; padding: 6px 0; }
          .cbi-top-header .container { max-width: 1240px; margin: 0 auto; padding: 0 16px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 6px; }
          .cbi-toll-free { display: flex; gap: 16px; flex-wrap: wrap; align-items: center; }
          .cbi-toll-free span { opacity: 0.9; font-size: 11px; }
          .cbi-top-links { display: flex; gap: 12px; align-items: center; }
          .cbi-top-links a { color: white; text-decoration: none; font-size: 11px; opacity: 0.85; transition: opacity 0.2s; }
          .cbi-top-links a:hover { opacity: 1; text-decoration: underline; }
          
          /* Main Header */
          .cbi-header { background: #fff; border-bottom: 3px solid #ce0f3d; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
          .cbi-header .container { max-width: 1240px; margin: 0 auto; padding: 10px 16px; display: flex; align-items: center; justify-content: space-between; }
          .cbi-logo-section { display: flex; align-items: center; gap: 12px; }
          .cbi-logo-img { width: 60px; height: 60px; background: linear-gradient(135deg, #003893, #001f5c); border-radius: 8px; display: grid; place-items: center; color: white; font-weight: 800; font-size: 14px; text-align: center; line-height: 1.1; flex-shrink: 0; }
          .cbi-bank-name { display: flex; flex-direction: column; }
          .cbi-bank-name h1 { font-size: 22px; font-weight: 800; color: #003893; margin: 0; line-height: 1.2; letter-spacing: -0.3px; }
          .cbi-bank-name p { font-size: 11px; color: #ce0f3d; font-weight: 600; margin: 2px 0 0; letter-spacing: 0.5px; }
          .cbi-right-logo { width: 60px; height: 60px; background: linear-gradient(135deg, #ce0f3d, #a00b2e); border-radius: 8px; display: grid; place-items: center; color: white; font-weight: 800; font-size: 10px; text-align: center; line-height: 1.2; }
          
          /* Header Auth Buttons */
          .cbi-auth-btn-group { display: flex; gap: 12px; align-items: center; }
          .cbi-header-auth-btn { padding: 8px 16px; border-radius: 6px; font-size: 13px; font-weight: 700; cursor: pointer; transition: all 0.2s; display: flex; align-items: center; gap: 6px; border: none; }
          .cbi-header-auth-btn.signin { background: #f0f4ff; color: #003893; border: 1px solid #d0ddf5; }
          .cbi-header-auth-btn.signin:hover { background: #e0e8f5; }
          .cbi-header-auth-btn.signup { background: #ce0f3d; color: white; box-shadow: 0 4px 10px rgba(206, 15, 61, 0.2); }
          .cbi-header-auth-btn.signup:hover { background: #a00b2e; transform: translateY(-1px); box-shadow: 0 6px 14px rgba(206, 15, 61, 0.3); }

          /* Top Menu */
          .cbi-top-menu { background: #f8f8f8; border-bottom: 1px solid #e8e8e8; }
          .cbi-top-menu .container { max-width: 1240px; margin: 0 auto; padding: 0 16px; display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; }
          .cbi-top-menu-links { display: flex; gap: 0; list-style: none; margin: 0; padding: 0; }
          .cbi-top-menu-links li a { display: block; padding: 10px 14px; font-size: 13px; color: #333; text-decoration: none; font-weight: 500; transition: all 0.2s; border-bottom: 2px solid transparent; }
          .cbi-top-menu-links li a:hover { color: #003893; background: #f0f4ff; border-bottom-color: #003893; }
          .cbi-font-controls { display: flex; gap: 4px; align-items: center; }
          .cbi-font-controls button { width: 28px; height: 28px; border: 1px solid #ccc; border-radius: 4px; background: white; cursor: pointer; font-size: 12px; font-weight: 600; color: #555; transition: all 0.2s; }
          .cbi-font-controls button:hover { border-color: #003893; color: #003893; }
          
          /* Main Navigation */
          .cbi-main-nav { background: linear-gradient(180deg, #003893 0%, #002870 100%); position: relative; z-index: 100; }
          .cbi-main-nav .container { max-width: 1240px; margin: 0 auto; padding: 0 16px; display: flex; align-items: stretch; }
          .cbi-nav-list { display: flex; list-style: none; margin: 0; padding: 0; flex: 1; }
          .cbi-nav-list > li { position: relative; }
          .cbi-nav-list > li > a { display: flex; align-items: center; gap: 6px; padding: 12px 14px; color: white; text-decoration: none; font-size: 13px; font-weight: 500; transition: all 0.2s; white-space: nowrap; border-bottom: 2px solid transparent; }
          .cbi-nav-list > li > a:hover, .cbi-nav-list > li:hover > a { background: rgba(255,255,255,0.1); border-bottom-color: #ce0f3d; }
          .cbi-nav-list > li > a .nav-icon { font-size: 14px; }
          
          /* Dropdown Cards */
          .cbi-dropdown-card { position: absolute; top: 100%; left: 0; min-width: 280px; background: white; border-radius: 0 0 8px 8px; box-shadow: 0 10px 25px rgba(0,0,0,0.15); border-top: 3px solid #ce0f3d; padding: 16px; opacity: 0; visibility: hidden; transform: translateY(10px); transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); z-index: 200; pointer-events: none; }
          .cbi-nav-list > li:hover .cbi-dropdown-card { opacity: 1; visibility: visible; transform: translateY(0); pointer-events: auto; }
          .cbi-dropdown-card h4 { color: #003893; font-size: 14px; font-weight: 700; margin: 0 0 10px 0; border-bottom: 1px solid #eee; padding-bottom: 6px; }
          .cbi-dropdown-card ul { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 8px; }
          .cbi-dropdown-card ul li { display: flex; align-items: flex-start; gap: 8px; font-size: 12px; color: #555; line-height: 1.4; }
          .cbi-dropdown-card ul li::before { content: "•"; color: #ce0f3d; font-weight: bold; }
          .cbi-dropdown-card ul li a { color: #555; text-decoration: none; transition: color 0.2s; }
          .cbi-dropdown-card ul li a:hover { color: #003893; text-decoration: underline; }
          
          /* Sub Header */
          .cbi-sub-header { background: #f0f4ff; border-bottom: 1px solid #d8e4f8; }
          .cbi-sub-header .container { max-width: 1240px; margin: 0 auto; padding: 0 16px; display: flex; align-items: center; gap: 20px; }
          .cbi-sub-header a { display: block; padding: 8px 0; font-size: 12px; color: #003893; text-decoration: none; font-weight: 500; transition: color 0.2s; }
          .cbi-sub-header a:hover { color: #ce0f3d; }
          .cbi-cyber-btn { background: linear-gradient(to bottom, #2b8cff, #0072e5); color: white !important; padding: 6px 14px !important; border-radius: 5px; font-size: 12px !important; cursor: pointer; }
          
          /* Hero Section */
          .cbi-hero { max-width: 1240px; margin: 0 auto; padding: 20px 16px; display: grid; grid-template-columns: 1fr 340px; gap: 20px; }
          @media (max-width: 900px) { .cbi-hero { grid-template-columns: 1fr; } }
          
          /* Slider */
          .cbi-slider { position: relative; border-radius: 12px; overflow: hidden; aspect-ratio: 1080/562; background: #001133; border: 2px solid #e0e8f5; box-shadow: 0 8px 24px rgba(0,0,0,0.1); }
          .cbi-slide { position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: flex-end; text-align: center; transition: opacity 0.8s ease-in-out, transform 0.8s ease; opacity: 0; transform: scale(1.02); }
          .cbi-slide.active { opacity: 1; transform: scale(1); }
          .cbi-slide img { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: cover; z-index: 0; }
          .cbi-slide-content { position: relative; z-index: 1; background: linear-gradient(to top, rgba(0,0,0,0.9) 0%, rgba(0,0,0,0.6) 60%, transparent 100%); width: 100%; padding: 40px 20px 30px; border-top: 1px solid rgba(255,255,255,0.1); }
          .cbi-slide-icon { font-size: 32px; margin-bottom: 8px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3)); display: inline-block; }
          .cbi-slide-text { color: white; font-size: 18px; font-weight: 700; line-height: 1.4; text-shadow: 0 2px 6px rgba(0,0,0,0.8); white-space: pre-line; }
          .cbi-slider-dots { position: absolute; bottom: 12px; left: 50%; transform: translateX(-50%); display: flex; gap: 8px; z-index: 2; }
          .cbi-slider-dot { width: 8px; height: 8px; border-radius: 50%; background: rgba(255,255,255,0.4); cursor: pointer; transition: all 0.3s; border: none; box-shadow: 0 1px 3px rgba(0,0,0,0.5); }
          .cbi-slider-dot.active { background: white; transform: scale(1.4); }
          .cbi-slider-nav { position: absolute; top: 50%; transform: translateY(-50%); background: rgba(0,0,0,0.4); color: white; border: 1px solid rgba(255,255,255,0.2); padding: 12px 14px; cursor: pointer; font-size: 18px; z-index: 2; transition: all 0.2s; border-radius: 8px; backdrop-filter: blur(4px); }
          .cbi-slider-nav:hover { background: rgba(0,0,0,0.7); border-color: rgba(255,255,255,0.5); }
          .cbi-slider-nav.prev { left: 16px; }
          .cbi-slider-nav.next { right: 16px; }
          
          /* Right Sidebar */
          .cbi-sidebar { display: flex; flex-direction: column; gap: 16px; }
          
          /* What's Looking For */
          .cbi-looking { background: #f0f4ff; border: 1px solid #d0ddf5; border-radius: 10px; padding: 16px; }
          .cbi-looking h3 { font-size: 14px; font-weight: 700; color: #003893; margin: 0 0 10px; }
          .cbi-looking select { width: 100%; padding: 8px 10px; border: 1px solid #c0d0e8; border-radius: 6px; font-size: 13px; background: white; color: #333; margin-bottom: 8px; outline: none; }
          .cbi-looking select:focus { border-color: #003893; }
          .cbi-looking-btns { display: flex; gap: 8px; }
          .cbi-looking-btns button { flex: 1; padding: 8px; border: none; border-radius: 6px; font-size: 12px; font-weight: 600; cursor: pointer; transition: all 0.2s; }
          .cbi-looking-btns .search-btn { background: #003893; color: white; }
          .cbi-looking-btns .search-btn:hover { background: #002870; }
          .cbi-looking-btns .apply-btn { background: #ce0f3d; color: white; }
          .cbi-looking-btns .apply-btn:hover { background: #a00b2e; }
          
          /* What's New */
          .cbi-whats-new { background: white; border: 1px solid #e8e8e8; border-radius: 10px; padding: 0; overflow: hidden; }
          .cbi-whats-new h3 { font-size: 14px; font-weight: 700; color: #003893; margin: 0; padding: 12px 16px; background: linear-gradient(90deg, #f0f4ff, #fff); border-bottom: 1px solid #e0e8f5; }
          .cbi-whats-new-list { max-height: 140px; overflow-y: auto; padding: 0; margin: 0; list-style: none; }
          .cbi-whats-new-list li { padding: 8px 16px; border-bottom: 1px solid #f0f0f0; font-size: 12px; transition: background 0.15s; }
          .cbi-whats-new-list li:last-child { border-bottom: none; }
          .cbi-whats-new-list li:hover { background: #f8f9fc; }
          .cbi-whats-new-list li a { color: #003893; text-decoration: none; line-height: 1.4; }
          .cbi-whats-new-list li a:hover { color: #ce0f3d; text-decoration: underline; }
          
          /* Online Banking Links */
          .cbi-online-links { background: white; border: 1px solid #e8e8e8; border-radius: 10px; overflow: hidden; }
          .cbi-online-links-grid { display: flex; flex-direction: column; }
          .cbi-online-link { display: flex; align-items: center; gap: 10px; padding: 10px 16px; text-decoration: none; color: #333; font-size: 13px; font-weight: 500; border-bottom: 1px solid #f0f0f0; transition: all 0.2s; cursor: pointer; border: none; background: none; text-align: left; width: 100%; }
          .cbi-online-link:last-child { border-bottom: none; }
          .cbi-online-link:hover { background: #f0f4ff; color: #003893; padding-left: 20px; }
          .cbi-online-link .link-icon { width: 32px; height: 32px; border-radius: 6px; display: grid; place-items: center; color: white; font-size: 14px; flex-shrink: 0; }
          .cbi-online-link .link-icon.blue { background: linear-gradient(135deg, #003893, #0052cc); }
          .cbi-online-link .link-icon.red { background: linear-gradient(135deg, #ce0f3d, #ff1744); }
          .cbi-online-link .link-icon.green { background: linear-gradient(135deg, #00875a, #00c853); }
          .cbi-online-link .link-icon.purple { background: linear-gradient(135deg, #6b21a8, #9333ea); }
          .cbi-online-link .link-icon.orange { background: linear-gradient(135deg, #c2410c, #ea580c); }
          
          /* Main Content Section */
          .cbi-content-section { max-width: 1240px; margin: 0 auto; padding: 24px 16px; }
          
          /* Quick Service Cards */
          .cbi-services-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 24px; }
          .cbi-service-card { background: white; border: 1px solid #e8e8e8; border-radius: 12px; padding: 24px 20px; text-align: center; transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1); cursor: pointer; position: relative; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.03); }
          .cbi-service-card::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 4px; background: var(--card-color, #003893); opacity: 0.8; transition: height 0.3s; }
          .cbi-service-card:hover { transform: translateY(-6px); box-shadow: 0 12px 28px rgba(0,0,0,0.08); border-color: var(--card-color, #003893); }
          .cbi-service-card:hover::before { height: 100%; opacity: 0.03; }
          .cbi-service-card .card-icon { width: 56px; height: 56px; border-radius: 14px; display: grid; place-items: center; margin: 0 auto 16px; font-size: 26px; box-shadow: 0 4px 10px rgba(0,0,0,0.05); border: 1px solid rgba(0,0,0,0.05); }
          .cbi-service-card h4 { font-size: 15px; font-weight: 700; color: #333; margin: 0 0 6px; transition: color 0.3s; }
          .cbi-service-card:hover h4 { color: var(--card-color, #003893); }
          .cbi-service-card p { font-size: 12px; color: #666; margin: 0; line-height: 1.4; }
          @media (max-width: 768px) { .cbi-services-grid { grid-template-columns: repeat(2, 1fr); } }
          @media (max-width: 480px) { .cbi-services-grid { grid-template-columns: 1fr; } }
          
          /* Fixed Sidebar */
          .cbi-fixed-sidebar { position: fixed; left: 0; top: 50%; transform: translateY(-50%); z-index: 90; display: flex; flex-direction: column; gap: 2px; }
          .cbi-fixed-sidebar a { display: flex; align-items: center; justify-content: center; width: 42px; height: 42px; background: linear-gradient(135deg, #003893, #001f5c); color: white; text-decoration: none; font-size: 16px; transition: all 0.2s; border-radius: 0 6px 6px 0; }
          .cbi-fixed-sidebar a:hover { width: 52px; background: linear-gradient(135deg, #ce0f3d, #a00b2e); }
          @media (max-width: 900px) { .cbi-fixed-sidebar { display: none; } }
          
          /* Right Fixed Sidebar */
          .cbi-fixed-right { position: fixed; right: 0; top: 50%; transform: translateY(-50%); z-index: 90; display: flex; flex-direction: column; gap: 2px; }
          .cbi-fixed-right a { display: flex; align-items: center; justify-content: center; width: 38px; height: 38px; color: white; text-decoration: none; font-size: 14px; transition: all 0.2s; border-radius: 6px 0 0 6px; }
          .cbi-fixed-right a:hover { width: 48px; }
          @media (max-width: 900px) { .cbi-fixed-right { display: none; } }
          
          /* Footer */
          .cbi-footer-tabs { background: #f0f4ff; border-top: 3px solid #003893; }
          .cbi-footer-tabs .container { max-width: 1240px; margin: 0 auto; padding: 0 16px; }
          .cbi-footer-tab-nav { display: flex; gap: 0; list-style: none; margin: 0; padding: 0; border-bottom: 1px solid #d0ddf5; overflow-x: auto; }
          .cbi-footer-tab-nav li button { padding: 12px 16px; border: none; background: transparent; font-size: 12px; font-weight: 600; color: #003893; cursor: pointer; transition: all 0.2s; white-space: nowrap; border-bottom: 2px solid transparent; }
          .cbi-footer-tab-nav li button:hover, .cbi-footer-tab-nav li button.active { background: white; border-bottom-color: #ce0f3d; color: #ce0f3d; }
          .cbi-footer-content { padding: 16px 0; }
          .cbi-footer-links { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 8px; }
          .cbi-footer-links a { font-size: 12px; color: #003893; text-decoration: none; padding: 4px 0; transition: color 0.2s; }
          .cbi-footer-links a:hover { color: #ce0f3d; text-decoration: underline; }
          
          /* Bottom Footer */
          .cbi-bottom-footer { background: linear-gradient(90deg, #003893, #001f5c); color: white; }
          .cbi-bottom-footer .container { max-width: 1240px; margin: 0 auto; padding: 14px 16px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }
          .cbi-bottom-footer p { margin: 0; font-size: 12px; opacity: 0.85; }
          .cbi-bottom-footer a { color: #7db6dc; text-decoration: none; }
          .cbi-bottom-footer a:hover { text-decoration: underline; }
          
          /* Footer Quick Links Row */
          .cbi-footer-quick { background: #ce0f3d; }
          .cbi-footer-quick .container { max-width: 1240px; margin: 0 auto; padding: 0 16px; display: flex; flex-wrap: wrap; gap: 0; }
          .cbi-footer-quick a { display: block; padding: 10px 14px; color: white; text-decoration: none; font-size: 12px; font-weight: 500; transition: background 0.2s; }
          .cbi-footer-quick a:hover { background: rgba(0,0,0,0.15); }
          
          /* Login Modal */
          .cbi-login-overlay { position: fixed; inset: 0; background: rgba(0,0,0,0.55); backdrop-filter: blur(4px); z-index: 9999; display: flex; align-items: center; justify-content: center; padding: 20px; animation: cbiModalFadeIn 0.3s ease; }
          @keyframes cbiModalFadeIn { from { opacity: 0; } to { opacity: 1; } }
          .cbi-login-modal { background: white; border-radius: 16px; max-width: 440px; width: 100%; box-shadow: 0 24px 48px rgba(0,0,0,0.2), 0 0 0 1px rgba(0,56,147,0.1); animation: cbiModalSlideIn 0.3s ease; overflow: hidden; }
          @keyframes cbiModalSlideIn { from { opacity: 0; transform: translateY(20px) scale(0.97); } to { opacity: 1; transform: translateY(0) scale(1); } }
          .cbi-login-modal-header { background: linear-gradient(135deg, #003893, #001f5c); padding: 24px; display: flex; align-items: center; justify-content: space-between; }
          .cbi-login-modal-header .header-left { display: flex; align-items: center; gap: 12px; }
          .cbi-login-modal-header .logo-box { width: 44px; height: 44px; background: rgba(255,255,255,0.15); border-radius: 10px; display: grid; place-items: center; color: white; font-weight: 800; font-size: 11px; text-align: center; line-height: 1.1; border: 1px solid rgba(255,255,255,0.2); }
          .cbi-login-modal-header h2 { color: white; font-size: 18px; font-weight: 700; margin: 0; line-height: 1.2; }
          .cbi-login-modal-header p { color: rgba(255,255,255,0.7); font-size: 11px; margin: 2px 0 0; font-weight: 500; }
          .cbi-login-modal-header .close-btn { background: rgba(255,255,255,0.1); border: 1px solid rgba(255,255,255,0.2); border-radius: 8px; color: white; cursor: pointer; width: 32px; height: 32px; display: grid; place-items: center; transition: all 0.2s; }
          .cbi-login-modal-header .close-btn:hover { background: rgba(255,255,255,0.2); }
          .cbi-login-modal-body { padding: 24px; }
          .cbi-login-modal-body .field-group { margin-bottom: 16px; }
          .cbi-login-modal-body label { display: block; font-size: 11px; font-weight: 700; color: #003893; text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 6px; }
          .cbi-login-modal-body input { width: 100%; padding: 12px 14px; border: 1.5px solid #d0ddf5; border-radius: 8px; font-size: 14px; color: #333; background: #f8faff; outline: none; transition: all 0.2s; box-sizing: border-box; }
          .cbi-login-modal-body input:focus { border-color: #003893; background: white; box-shadow: 0 0 0 3px rgba(0,56,147,0.08); }
          .cbi-login-modal-body input::placeholder { color: #a0b0c8; }
          .cbi-login-submit { width: 100%; padding: 13px; border: none; border-radius: 8px; background: linear-gradient(135deg, #003893, #0052cc); color: white; font-size: 14px; font-weight: 700; cursor: pointer; transition: all 0.2s; margin-top: 4px; }
          .cbi-login-submit:hover { background: linear-gradient(135deg, #002870, #003893); transform: translateY(-1px); box-shadow: 0 4px 12px rgba(0,56,147,0.3); }
          .cbi-login-submit:disabled { opacity: 0.6; cursor: not-allowed; transform: none; box-shadow: none; }
          .cbi-login-error { padding: 10px 14px; background: #fff0f0; border: 1px solid #fdd; border-radius: 8px; color: #c00; font-size: 12px; display: flex; align-items: center; gap: 8px; margin-bottom: 16px; }
          .cbi-login-footer { padding: 16px 24px; background: #f8faff; border-top: 1px solid #e8eef8; text-align: center; }
          .cbi-login-footer span { font-size: 11px; color: #8899aa; display: flex; align-items: center; justify-content: center; gap: 6px; font-weight: 500; }
          
          /* Auth Modal Tabs */
          .cbi-auth-tabs { display: flex; border-bottom: 1px solid #e8eef8; }
          .cbi-auth-tab { flex: 1; padding: 14px; border: none; background: transparent; font-size: 13px; font-weight: 600; color: #8899aa; cursor: pointer; transition: all 0.2s; border-bottom: 2px solid transparent; }
          .cbi-auth-tab.active { color: #003893; border-bottom-color: #003893; background: #f8faff; }
          .cbi-auth-tab:hover:not(.active) { color: #003893; background: #fafbff; }
          
          /* Password Strength */
          .pwd-rules { display: flex; flex-direction: column; gap: 4px; margin-top: 8px; }
          .pwd-rule { display: flex; align-items: center; gap: 6px; font-size: 11px; color: #999; transition: color 0.2s; }
          .pwd-rule.pass { color: #00875a; }
          .pwd-rule .dot { width: 6px; height: 6px; border-radius: 50%; background: #ddd; transition: background 0.2s; flex-shrink: 0; }
          .pwd-rule.pass .dot { background: #00875a; }
          
          /* OTP Input */
          .otp-input-group { display: flex; gap: 8px; justify-content: center; margin: 16px 0; }
          .otp-input-group input { width: 44px; height: 52px; text-align: center; font-size: 20px; font-weight: 700; border: 2px solid #d0ddf5; border-radius: 10px; outline: none; transition: all 0.2s; color: #003893; background: #f8faff; }
          .otp-input-group input:focus { border-color: #003893; box-shadow: 0 0 0 3px rgba(0,56,147,0.08); background: white; }
          
          /* Registration Steps */
          .reg-step-indicator { display: flex; align-items: center; justify-content: center; gap: 8px; padding: 16px 24px; background: #f8faff; border-bottom: 1px solid #e8eef8; }
          .reg-step-dot { width: 28px; height: 28px; border-radius: 50%; display: grid; place-items: center; font-size: 12px; font-weight: 700; border: 2px solid #d0ddf5; color: #999; background: white; transition: all 0.3s; }
          .reg-step-dot.active { border-color: #003893; color: white; background: #003893; }
          .reg-step-dot.done { border-color: #00875a; color: white; background: #00875a; }
          .reg-step-line { width: 24px; height: 2px; background: #d0ddf5; transition: background 0.3s; }
          .reg-step-line.done { background: #00875a; }
          
          /* Resend button */
          .resend-btn { background: none; border: none; color: #003893; font-size: 12px; font-weight: 600; cursor: pointer; padding: 4px 0; transition: color 0.2s; }
          .resend-btn:disabled { color: #999; cursor: not-allowed; }
          .resend-btn:hover:not(:disabled) { color: #ce0f3d; text-decoration: underline; }
          
          /* Success animation */
          .reg-success-icon { width: 64px; height: 64px; border-radius: 50%; background: #e6f9ee; border: 3px solid #00875a; display: grid; place-items: center; margin: 0 auto 16px; animation: successPop 0.5s ease; }
          @keyframes successPop { 0% { transform: scale(0); } 60% { transform: scale(1.2); } 100% { transform: scale(1); } }
          
          /* Mobile menu button */
          .cbi-mobile-menu-btn { display: none; background: none; border: none; color: white; font-size: 22px; cursor: pointer; padding: 8px; }
          @media (max-width: 900px) {
            .cbi-nav-list { display: none; }
            .cbi-mobile-menu-btn { display: block; }
            .cbi-nav-list.open { display: flex; flex-direction: column; position: absolute; top: 100%; left: 0; right: 0; background: #003893; z-index: 200; box-shadow: 0 8px 24px rgba(0,0,0,0.2); }
            .cbi-top-menu-links { flex-wrap: wrap; }
          }
        `}</style>
        
        <div className="cbi-page">
          {/* ===== TOP HEADER BAR ===== */}
          <div className="cbi-top-header">
            <div className="container">
              <div className="cbi-toll-free">
                <span>📞 {t('toll_free')}</span>
                <span>📞 {t('toll_free_pen')}</span>
                <span>🛡️ {t('cyber_crime')}</span>
              </div>
              <div className="cbi-top-links" style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                <div style={{ display: 'flex', gap: '4px', borderRight: '1px solid #fff', paddingRight: '12px' }}>
                  <button onClick={() => pref.setFontSize('dec')} style={{ background: 'transparent', color: 'white', border: '1px solid rgba(255,255,255,0.3)', padding: '2px 6px', fontSize: '10px', borderRadius: '4px' }}>A-</button>
                  <button onClick={() => pref.setFontSize('reset')} style={{ background: 'transparent', color: 'white', border: '1px solid rgba(255,255,255,0.3)', padding: '2px 6px', fontSize: '10px', borderRadius: '4px' }}>A</button>
                  <button onClick={() => pref.setFontSize('inc')} style={{ background: 'transparent', color: 'white', border: '1px solid rgba(255,255,255,0.3)', padding: '2px 6px', fontSize: '10px', borderRadius: '4px' }}>A+</button>
                </div>
                <button onClick={() => pref.setLang('en')} style={{ background: 'transparent', border: 'none', color: pref.lang === 'en' ? '#fff' : 'rgba(255,255,255,0.5)', fontWeight: pref.lang === 'en' ? 'bold' : 'normal', cursor: 'pointer' }}>{t('lang_en')}</button>
                <button onClick={() => pref.setLang('hi')} style={{ background: 'transparent', border: 'none', color: pref.lang === 'hi' ? '#fff' : 'rgba(255,255,255,0.5)', fontWeight: pref.lang === 'hi' ? 'bold' : 'normal', cursor: 'pointer' }}>{t('lang_hi')}</button>
              </div>
            </div>
          </div>

          {/* ===== MAIN HEADER ===== */}
          <div className="cbi-header">
            <div className="container">
              <div className="cbi-logo-section">
                <div className="cbi-logo-img">CBI</div>
                <div className="cbi-bank-name">
                  <h1>Central Bank of India</h1>
                  <p>ESTABLISHED IN 1911 • GOVERNMENT OF INDIA UNDERTAKING</p>
                </div>
              </div>
              <div className="cbi-auth-btn-group">
                <button 
                  className="cbi-header-auth-btn signin" 
                  onClick={() => { setShowLoginModal(true); setAuthModalTab('signin'); }}
                >
                  🔒 Sign In
                </button>
                <button 
                  className="cbi-header-auth-btn signup" 
                  onClick={() => { setShowLoginModal(true); setAuthModalTab('signup'); }}
                >
                  📝 Sign Up
                </button>
                <div className="cbi-right-logo">केन्द्रीय<br/>बैंक</div>
              </div>
            </div>
          </div>

          {/* ===== TOP MENU ===== */}
          <div className="cbi-top-menu">
            <div className="container">
              <ul className="cbi-top-menu-links">
                <li><a href="#">{t('home')}</a></li>
                <li><a href="#">{t('about')}</a></li>
                <li><a href="#">{t('branch')}</a></li>
                <li><a href="#">{t('contact')}</a></li>
                <li><a href="#">{t('career')}</a></li>
                <li><a href="#">{t('investor')}</a></li>
              </ul>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <div className="cbi-font-controls">
                  <button>A+</button>
                  <button>A-</button>
                </div>
                <span style={{ fontSize: '11px', color: '#003893', fontWeight: 600 }}>
                  RTI ACT 2005 | RBI Kehta Hai
                </span>
              </div>
            </div>
          </div>

          {/* ===== MAIN NAVIGATION ===== */}
          <div className="cbi-main-nav">
            <div className="container">
              <button className="cbi-mobile-menu-btn" onClick={() => setMobileMenuOpen(!mobileMenuOpen)}>
                <Menu size={22} />
              </button>
              <ul className={`cbi-nav-list ${mobileMenuOpen ? 'open' : ''}`}>
                <li>
                  <a href="#"><span className="nav-icon">🏦</span> Digital Banking</a>
                  <div className="cbi-dropdown-card">
                    <h4>Digital Banking Services</h4>
                    <ul>
                      <li><a href="#" onClick={(e) => { e.preventDefault(); setShowLoginModal(true); setAuthModalTab('signin'); }}>Internet Banking Login</a></li>
                      <li><a href="#">Mobile Banking App (Cent eeZ)</a></li>
                      <li><a href="#">UPI & BHIM Services</a></li>
                      <li><a href="#">WhatsApp Banking Info</a></li>
                      <li><a href="#">NEFT / RTGS / IMPS Limits</a></li>
                    </ul>
                  </div>
                </li>
                <li>
                  <a href="#"><span className="nav-icon">💰</span> Deposits</a>
                  <div className="cbi-dropdown-card">
                    <h4>Deposit Schemes</h4>
                    <ul>
                      <li><a href="#">Savings Accounts Overview</a></li>
                      <li><a href="#">Current Accounts for Business</a></li>
                      <li><a href="#">Fixed Deposits (FD) Rates</a></li>
                      <li><a href="#">Recurring Deposits (RD)</a></li>
                      <li><a href="#">Tax Saver Schemes</a></li>
                    </ul>
                  </div>
                </li>
                <li>
                  <a href="#"><span className="nav-icon">📊</span> Retail Loans</a>
                  <div className="cbi-dropdown-card">
                    <h4>Retail Loan Products</h4>
                    <ul>
                      <li><a href="#">Cent Home Loan Options</a></li>
                      <li><a href="#">Vehicle Loans</a></li>
                      <li><a href="#">Personal Loans for Salaried</a></li>
                      <li><a href="#">Education Loans (Vidyarthi)</a></li>
                      <li><a href="#">Loan Against Property</a></li>
                    </ul>
                  </div>
                </li>
                <li>
                  <a href="#"><span className="nav-icon">🌾</span> Agriculture</a>
                  <div className="cbi-dropdown-card">
                    <h4>Agri Finance</h4>
                    <ul>
                      <li><a href="#">Cent Agri Gold Loan</a></li>
                      <li><a href="#">Kisan Credit Card (KCC)</a></li>
                      <li><a href="#">Tractor & Machinery Loans</a></li>
                      <li><a href="#">SHG & JLG Financing</a></li>
                      <li><a href="#">Agriculture Infrastructure Fund</a></li>
                    </ul>
                  </div>
                </li>
                <li>
                  <a href="#"><span className="nav-icon">🏭</span> MSME</a>
                  <div className="cbi-dropdown-card">
                    <h4>MSME Banking</h4>
                    <ul>
                      <li><a href="#">MUDRA Loans</a></li>
                      <li><a href="#">CGTMSE Coverage</a></li>
                      <li><a href="#">Working Capital Limits</a></li>
                      <li><a href="#">Term Loans for Machinery</a></li>
                      <li><a href="#">Export/Import Finance</a></li>
                    </ul>
                  </div>
                </li>
                <li>
                  <a href="#"><span className="nav-icon">🏛️</span> Govt./Business</a>
                  <div className="cbi-dropdown-card">
                    <h4>Govt & Business</h4>
                    <ul>
                      <li><a href="#">Public Financial Management</a></li>
                      <li><a href="#">Direct Benefit Transfer (DBT)</a></li>
                      <li><a href="#">Tax Collection Services</a></li>
                      <li><a href="#">Corporate Salary Accounts</a></li>
                    </ul>
                  </div>
                </li>
              </ul>
            </div>
          </div>

          {/* ===== SUB HEADER ===== */}
          <div className="cbi-sub-header">
            <div className="container">
              <a href="#">DigiSaathi - 24x7 Helpline</a>
              <a href="#">राजभाषा</a>
              <a href="#" className="cbi-cyber-btn">Cyber Crime Awareness</a>
            </div>
          </div>

          {/* ===== HERO SECTION ===== */}
          <div className="cbi-hero">
            {/* Slider */}
            <div className="cbi-slider">
              {bannerSlides.map((slide, idx) => (
                <div key={idx} className={`cbi-slide bg-gradient-to-br ${slide.gradient} ${idx === currentSlide ? 'active' : ''}`}>
                  {slide.image && <img src={slide.image} alt={slide.alt} />}
                  <div className="cbi-slide-content">
                    <div className="cbi-slide-icon">{slide.icon}</div>
                    <div className="cbi-slide-text">{slide.text}</div>
                  </div>
                </div>
              ))}
              <button className="cbi-slider-nav prev" onClick={() => setCurrentSlide(prev => prev === 0 ? bannerSlides.length - 1 : prev - 1)}>❮</button>
              <button className="cbi-slider-nav next" onClick={() => setCurrentSlide(prev => (prev + 1) % bannerSlides.length)}>❯</button>
              <div className="cbi-slider-dots">
                {bannerSlides.map((_, idx) => (
                  <button key={idx} className={`cbi-slider-dot ${idx === currentSlide ? 'active' : ''}`} onClick={() => setCurrentSlide(idx)} />
                ))}
              </div>
            </div>

            {/* Right Sidebar */}
            <div className="cbi-sidebar">
              {/* What are you looking for */}
              <div className="cbi-looking">
                <h3>What are you looking for?</h3>
                <select defaultValue="34">
                  <option value="34">Deposits</option>
                  <option value="20">Cards</option>
                  <option value="28">Loans</option>
                  <option value="96">FASTag</option>
                  <option value="97">Insurance</option>
                  <option value="98">Lockers</option>
                </select>
                <select defaultValue="35">
                  <option value="37">Saving Deposit</option>
                  <option value="35">Fixed Deposit</option>
                  <option value="36">Recurring Deposit</option>
                </select>
                <div className="cbi-looking-btns">
                  <button className="search-btn">Search</button>
                  <button className="apply-btn">Apply Now</button>
                </div>
              </div>

              {/* What's New */}
              <div className="cbi-whats-new">
                <h3>What's New</h3>
                <ul className="cbi-whats-new-list">
                  {whatsNewItems.map((item, idx) => (
                    <li key={idx}><a href={item.link}>{item.text}</a></li>
                  ))}
                </ul>
              </div>

              {/* Online Banking Links */}
              <div className="cbi-online-links">
                <div className="cbi-online-links-grid">
                  <button className="cbi-online-link" onClick={() => { setShowLoginModal(true); setAuthError(''); }}>
                    <span className="link-icon blue">🌐</span>
                    <span style={{ fontWeight: 600, color: '#003893' }}>Internet Banking</span>
                    <ChevronRight size={14} style={{ marginLeft: 'auto', color: '#003893' }} />
                  </button>
                  <button className="cbi-online-link" onClick={() => { setShowLoginModal(true); setAuthError(''); }}>
                    <span className="link-icon blue">📱</span>
                    <span>Cent eeZ</span>
                  </button>
                  <a className="cbi-online-link" href="#">
                    <span className="link-icon blue">📱</span>
                    <span>Cent eeZ – Vyapaar Saathi</span>
                  </a>
                  <a className="cbi-online-link" href="#">
                    <span className="link-icon green">💳</span>
                    <span>Pay Direct Taxes</span>
                  </a>
                  <a className="cbi-online-link" href="#">
                    <span className="link-icon red">🆕</span>
                    <span>New Product</span>
                  </a>
                  <a className="cbi-online-link" href="#">
                    <span className="link-icon purple">🎥</span>
                    <span>Open Savings Account via Video KYC</span>
                  </a>
                  <a className="cbi-online-link" href="#">
                    <span className="link-icon orange">💰</span>
                    <span>Digital Loans</span>
                  </a>
                  <a className="cbi-online-link" href="#">
                    <span className="link-icon green">🛡️</span>
                    <span>Safe Online Banking Tips</span>
                  </a>
                </div>
              </div>
            </div>
          </div>

          {/* ===== QUICK SERVICES SECTION ===== */}
          <div className="cbi-content-section">
            <div className="cbi-services-grid">
              {[
                { icon: '🏦', title: 'SB Accounts', desc: 'Secure your savings with our feature-rich accounts.', bg: '#f0f4ff', color: '#0052cc' },
                { icon: '💳', title: 'Debit Cards', desc: 'Global acceptance with zero liability protection.', bg: '#fff0f3', color: '#ce0f3d' },
                { icon: '📲', title: 'Mobile Banking', desc: 'Your bank in your pocket. 24x7 secure access.', bg: '#f0fff4', color: '#00875a' },
                { icon: '📈', title: 'Fixed Deposits', desc: 'Assured returns with flexible tenure options.', bg: '#fffbf0', color: '#ea580c' },
                { icon: '🏠', title: 'Home Loans', desc: 'Low interest rates to build your dream home.', bg: '#f5f0ff', color: '#6b21a8' },
                { icon: '🎓', title: 'Education Loans', desc: 'Empowering futures with quick disbursements.', bg: '#f0fcff', color: '#0284c7' },
              ].map((s, i) => (
                <div key={i} className="cbi-service-card" style={{ '--card-color': s.color } as React.CSSProperties}>
                  <div className="card-icon" style={{ background: s.bg, color: s.color }}>{s.icon}</div>
                  <h4>{s.title}</h4>
                  <p>{s.desc}</p>
                </div>
              ))}
            </div>
          </div>

          {/* ===== FIXED LEFT SIDEBAR ===== */}
          <div className="cbi-fixed-sidebar">
            <a href="#" onClick={(e) => { e.preventDefault(); setShowLoginModal(true); setAuthError(''); }} title="Internet Banking">🌐</a>
            <a href="#" title="Cent eeZ" onClick={(e) => { e.preventDefault(); setShowLoginModal(true); setAuthError(''); }}>📱</a>
            <a href="#" title="Mobile Banking">📲</a>
            <a href="#" title="Debit Card">💳</a>
            <a href="#" title="EMI Calculator">🧮</a>
          </div>

          {/* ===== FIXED RIGHT SIDEBAR ===== */}
          <div className="cbi-fixed-right">
            <a href="#" style={{ background: '#1877f2' }} title="Facebook">f</a>
            <a href="#" style={{ background: '#1da1f2' }} title="Twitter/X">𝕏</a>
            <a href="#" style={{ background: 'linear-gradient(45deg, #f09433, #e6683c, #dc2743, #cc2366, #bc1888)' }} title="Instagram">📷</a>
            <a href="#" style={{ background: '#0077b5' }} title="LinkedIn">in</a>
            <a href="#" style={{ background: '#ff0000' }} title="YouTube">▶</a>
            <a href="#" style={{ background: '#25d366' }} title="WhatsApp">💬</a>
          </div>

          {/* ===== FOOTER TABS ===== */}
          <div className="cbi-footer-tabs">
            <div className="container">
              <ul className="cbi-footer-tab-nav">
                {['General Information', 'Policies & Procedures', 'Financial Inclusion', 'Pradhan Mantri Yojana', 'Important Links', 'Other Services'].map((tab, i) => (
                  <li key={i}><button className={i === 0 ? 'active' : ''}>{tab}</button></li>
                ))}
              </ul>
              <div className="cbi-footer-content">
                <div className="cbi-footer-links">
                  {['Interest Rates', 'Service Charges', 'RBI Circulars', 'Customer Charter', 'Grievance Redressal', 'Banking Ombudsman', 'Unclaimed Deposits', 'Do\'s & Don\'ts', 'Safe Banking Tips', 'Citizen Charter', 'Customer Rights', 'DICGC'].map((link, i) => (
                    <a key={i} href="#">{link}</a>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* ===== FOOTER QUICK LINKS ===== */}
          <div className="cbi-footer-quick">
            <div className="container">
              {['Live Tenders', 'Tenders Awarded', 'Auction', 'E-Auction', 'Press Release', 'Public Notices', 'Complaints', 'Cyber Fraud'].map((link, i) => (
                <a key={i} href="#">{link}</a>
              ))}
            </div>
          </div>

          {/* ===== BOTTOM FOOTER ===== */}
          <div className="cbi-bottom-footer">
            <div className="container">
              <p>© 2020 Central Bank of India. All rights reserved</p>
              <p>Designed & Maintained by <a href="#">Cyfuture</a></p>
            </div>
          </div>

          {/* ===== AUTH MODAL (SIGN IN / CREATE ACCOUNT) ===== */}
          {showLoginModal && (
            <div className="cbi-login-overlay" onClick={(e) => { if (e.target === e.currentTarget) { setShowLoginModal(false); resetRegState(); } }}>
              <div className="cbi-login-modal">
                <div className="cbi-login-modal-header">
                  <div className="header-left">
                    <div className="logo-box">CBI</div>
                    <div>
                      <h2>Internet Banking</h2>
                      <p>Central Bank of India • {authModalTab === 'signin' ? 'Secure Login' : 'New Account'}</p>
                    </div>
                  </div>
                  <button className="close-btn" onClick={() => { setShowLoginModal(false); resetRegState(); }}>
                    <X size={16} />
                  </button>
                </div>

                {/* Tabs */}
                <div className="cbi-auth-tabs">
                  <button className={`cbi-auth-tab ${authModalTab === 'signin' ? 'active' : ''}`} onClick={() => { setAuthModalTab('signin'); setAuthError(''); }}>Sign In</button>
                  <button className={`cbi-auth-tab ${authModalTab === 'signup' ? 'active' : ''}`} onClick={() => { setAuthModalTab('signup'); setRegError(''); setRegOtpError(''); }}>Create Account</button>
                </div>

                {/* SIGN IN TAB */}
                {authModalTab === 'signin' && (
                  <div className="cbi-login-modal-body">
                    {authError && (
                      <div className="cbi-login-error">
                        <AlertTriangle size={14} />
                        <span>{authError}</span>
                      </div>
                    )}
                    <form onSubmit={handleLogin}>
                      <div className="field-group">
                        <label>Username</label>
                        <input type="text" placeholder="e.g. john_doe" value={username} onChange={(e) => setUsername(e.target.value)} />
                      </div>
                      <div className="field-group">
                        <label>Password</label>
                        <input type="password" placeholder="Enter your password" value={password} onChange={(e) => setPassword(e.target.value)} />
                      </div>
                      <button type="submit" disabled={loading} className="cbi-login-submit">
                        {loading ? 'Authenticating...' : 'Secure Login'}
                      </button>
                    </form>
                    <div style={{ textAlign: 'center', marginTop: '16px' }}>
                      <span style={{ fontSize: '12px', color: '#888' }}>Don't have an account? </span>
                      <button onClick={() => { setAuthModalTab('signup'); setAuthError(''); }} style={{ background: 'none', border: 'none', color: '#003893', fontWeight: 600, fontSize: '12px', cursor: 'pointer' }}>Create one</button>
                    </div>
                  </div>
                )}

                {/* CREATE ACCOUNT TAB */}
                {authModalTab === 'signup' && (
                  <>
                    {/* Step Indicator */}
                    {regStep < 4 && (
                      <div className="reg-step-indicator">
                        <div className={`reg-step-dot ${regStep === 1 ? 'active' : regStep > 1 ? 'done' : ''}`}>{regStep > 1 ? '✓' : '1'}</div>
                        <div className={`reg-step-line ${regStep > 1 ? 'done' : ''}`}></div>
                        <div className={`reg-step-dot ${regStep === 2 ? 'active' : regStep > 2 ? 'done' : ''}`}>{regStep > 2 ? '✓' : '2'}</div>
                        <div className={`reg-step-line ${regStep > 2 ? 'done' : ''}`}></div>
                        <div className={`reg-step-dot ${regStep === 3 ? 'active' : regStep > 3 ? 'done' : ''}`}>{regStep > 3 ? '✓' : '3'}</div>
                      </div>
                    )}

                    <div className="cbi-login-modal-body">
                      {/* STEP 1: Account Details */}
                      {regStep === 1 && (
                        <form onSubmit={handleRegister}>
                          {regError && (
                            <div className="cbi-login-error">
                              <AlertTriangle size={14} />
                              <span>{regError}</span>
                            </div>
                          )}
                          <div className="field-group">
                            <label>Username</label>
                            <input type="text" placeholder="Choose a username" value={regUsername} onChange={(e) => setRegUsername(e.target.value)} />
                          </div>
                          <div className="field-group">
                            <label>Email Address</label>
                            <input type="email" placeholder="name@example.com" value={regEmail} onChange={(e) => setRegEmail(e.target.value)} />
                          </div>
                          <div className="field-group">
                            <label>Phone Number</label>
                            <input type="tel" placeholder="+91 9876543210" value={regPhone} onChange={(e) => setRegPhone(e.target.value)} />
                          </div>
                          <div className="field-group">
                            <label>Password</label>
                            <input type="password" placeholder="Min. 14 characters" value={regPassword} onChange={(e) => setRegPassword(e.target.value)} />
                            {regPassword && (() => {
                              const c = passwordChecks(regPassword);
                              return (
                                <div className="pwd-rules">
                                  <div className={`pwd-rule ${c.minLength ? 'pass' : ''}`}><span className="dot"></span> At least 14 characters</div>
                                  <div className={`pwd-rule ${c.hasUpper ? 'pass' : ''}`}><span className="dot"></span> One uppercase letter (A-Z)</div>
                                  <div className={`pwd-rule ${c.hasLower ? 'pass' : ''}`}><span className="dot"></span> One lowercase letter (a-z)</div>
                                  <div className={`pwd-rule ${c.hasDigit ? 'pass' : ''}`}><span className="dot"></span> One digit (0-9)</div>
                                  <div className={`pwd-rule ${c.hasSpecial ? 'pass' : ''}`}><span className="dot"></span> One special character (!@#$...)</div>
                                </div>
                              );
                            })()}
                          </div>
                          <div className="field-group">
                            <label>Confirm Password</label>
                            <input type="password" placeholder="Re-enter password" value={regConfirmPassword} onChange={(e) => setRegConfirmPassword(e.target.value)} />
                            {regConfirmPassword && regPassword !== regConfirmPassword && (
                              <div style={{ fontSize: '11px', color: '#c00', marginTop: '4px' }}>Passwords do not match</div>
                            )}
                          </div>
                          <button type="submit" disabled={regLoading} className="cbi-login-submit">
                            {regLoading ? 'Creating Account...' : 'Create Account & Verify'}
                          </button>
                        </form>
                      )}

                      {/* STEP 2: Email OTP */}
                      {regStep === 2 && (
                        <div style={{ textAlign: 'center' }}>
                          <div style={{ fontSize: '32px', marginBottom: '8px' }}>📧</div>
                          <h3 style={{ color: '#003893', fontSize: '16px', fontWeight: 700, margin: '0 0 8px' }}>Verify Your Email</h3>
                          <p style={{ fontSize: '12px', color: '#666', margin: '0 0 16px' }}>
                            We've sent a 6-digit code to <strong>{regEmail}</strong>
                          </p>
                          {regOtpError && (
                            <div className="cbi-login-error">
                              <AlertTriangle size={14} />
                              <span>{regOtpError}</span>
                            </div>
                          )}
                          <div className="field-group">
                            <input
                              type="text"
                              maxLength={6}
                              placeholder="Enter 6-digit code"
                              value={regEmailOtp}
                              onChange={(e) => setRegEmailOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                              style={{ textAlign: 'center', fontSize: '20px', fontWeight: 700, letterSpacing: '8px', color: '#003893' }}
                            />
                          </div>
                          <button
                            disabled={regOtpLoading || regEmailOtp.length !== 6}
                            className="cbi-login-submit"
                            onClick={() => handleVerifyRegOtp('email')}
                          >
                            {regOtpLoading ? 'Verifying...' : 'Verify Email'}
                          </button>
                          <div style={{ marginTop: '12px' }}>
                            <button className="resend-btn" disabled={resendCooldown > 0} onClick={() => handleSendRegOtp('email')}>
                              {resendCooldown > 0 ? `Resend in ${resendCooldown}s` : 'Resend Code'}
                            </button>
                          </div>
                        </div>
                      )}

                      {/* STEP 3: Phone OTP */}
                      {regStep === 3 && (
                        <div style={{ textAlign: 'center' }}>
                          <div style={{ fontSize: '32px', marginBottom: '8px' }}>📱</div>
                          <h3 style={{ color: '#003893', fontSize: '16px', fontWeight: 700, margin: '0 0 8px' }}>Verify Your Phone</h3>
                          <p style={{ fontSize: '12px', color: '#666', margin: '0 0 16px' }}>
                            We've sent a 6-digit code to <strong>{regPhone}</strong>
                          </p>
                          {regOtpError && (
                            <div className="cbi-login-error">
                              <AlertTriangle size={14} />
                              <span>{regOtpError}</span>
                            </div>
                          )}
                          <div className="field-group">
                            <input
                              type="text"
                              maxLength={6}
                              placeholder="Enter 6-digit code"
                              value={regPhoneOtp}
                              onChange={(e) => setRegPhoneOtp(e.target.value.replace(/\D/g, '').slice(0, 6))}
                              style={{ textAlign: 'center', fontSize: '20px', fontWeight: 700, letterSpacing: '8px', color: '#003893' }}
                            />
                          </div>
                          <button
                            disabled={regOtpLoading || regPhoneOtp.length !== 6}
                            className="cbi-login-submit"
                            onClick={() => handleVerifyRegOtp('phone')}
                          >
                            {regOtpLoading ? 'Verifying...' : 'Verify Phone'}
                          </button>
                          <div style={{ marginTop: '12px' }}>
                            <button className="resend-btn" disabled={resendCooldown > 0} onClick={() => handleSendRegOtp('phone')}>
                              {resendCooldown > 0 ? `Resend in ${resendCooldown}s` : 'Resend Code'}
                            </button>
                          </div>
                        </div>
                      )}

                      {/* STEP 4: Success */}
                      {regStep === 4 && (
                        <div style={{ textAlign: 'center', padding: '8px 0' }}>
                          <div className="reg-success-icon">
                            <CheckCircle size={32} style={{ color: '#00875a' }} />
                          </div>
                          <h3 style={{ color: '#003893', fontSize: '18px', fontWeight: 700, margin: '0 0 8px' }}>Account Verified!</h3>
                          <p style={{ fontSize: '13px', color: '#666', margin: '0 0 20px', lineHeight: 1.5 }}>
                            Your account has been created successfully.<br/>
                            Your secure Banking ID is: <strong style={{ fontSize: '16px', color: '#003893' }}>{regBankingId}</strong><br/>
                            Please use your credentials to sign in.
                          </p>
                          <button
                            className="cbi-login-submit"
                            onClick={() => {
                              setAuthModalTab('signin');
                              setUsername(regUsername);
                              resetRegState();
                            }}
                          >
                            Go to Sign In
                          </button>
                        </div>
                      )}
                    </div>
                  </>
                )}

                <div className="cbi-login-footer">
                  <span>
                    🔒 Session secured via AES-256-GCM & HS256 JWT
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>
      </>
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
          
          <React.Suspense fallback={<div className="flex justify-center items-center h-64 text-neutral-500 font-mono animate-pulse">Decrypting module payload...</div>}>
            {activeTab === 'dashboard' && <DashboardTab />}
            {activeTab === 'transfer' && <TransferTab />}
            {activeTab === 'beneficiaries' && <BeneficiariesTab />}
            {activeTab === 'statements' && <StatementsTab />}
            {activeTab === 'support' && <SupportTab />}
          </React.Suspense>

        </main>
      </div>


      
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
