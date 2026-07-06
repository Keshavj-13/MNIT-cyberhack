import axios from 'axios';
import { encryptData, decryptData } from './crypto';

const API_BASE = `${window.location.protocol}//${window.location.hostname}:8001`;

// Enable cookie credentials
axios.defaults.withCredentials = true;

// Inject sessionStorage token if present to support tab-level isolation
axios.interceptors.request.use((config) => {
  const token = sessionStorage.getItem('cbi_auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
}, (error) => {
  return Promise.reject(error);
});

export interface EncryptedPayload {
  session_id: string;
  key_version: int;
  ciphertext: string;
  nonce: string;
  tag: string;
}

export interface CryptoState {
  aesKey: string;
  keyVersion: number;
  sessionId: string;
  riskLevel: number;
}

// Helper to encrypt body and construct the EncryptedPayload
async function makeEncryptedRequest(
  endpoint: string,
  body: Record<string, any>,
  cryptoState: CryptoState
): Promise<any> {
  const plaintext = JSON.stringify(body);
  const encrypted = await encryptData(plaintext, cryptoState.aesKey);
  
  const payload: EncryptedPayload = {
    session_id: cryptoState.sessionId,
    key_version: cryptoState.keyVersion,
    ciphertext: encrypted.ciphertext,
    nonce: encrypted.nonce,
    tag: encrypted.tag
  };

  const res = await axios.post(`${API_BASE}${endpoint}`, payload);
  const data = res.data;

  // Decrypt response
  const decryptedStr = await decryptData(data.ciphertext, data.nonce, data.tag, cryptoState.aesKey);
  return JSON.parse(decryptedStr);
}

export async function registerCustomer(username: string, email: string, phone: string, password: string): Promise<any> {
  const res = await axios.post(`${API_BASE}/customer/auth/register`, {
    username, email, phone, password
  });
  return res.data;
}

export async function sendOTP(identifier: string, channel: 'email' | 'phone'): Promise<any> {
  const res = await axios.post(`${API_BASE}/customer/auth/send-otp`, {
    identifier, channel
  });
  return res.data;
}

export async function verifyOTP(identifier: string, otp: string, channel: 'email' | 'phone'): Promise<any> {
  const res = await axios.post(`${API_BASE}/customer/auth/verify-otp`, {
    identifier, otp, channel
  });
  return res.data;
}

export async function loginCustomer(username: string, pin: string): Promise<any> {
  const res = await axios.post(`${API_BASE}/customer/auth/login`, {
    username,
    password: pin
  });
  return res.data;
}

export async function logoutCustomer(): Promise<any> {
  const res = await axios.post(`${API_BASE}/customer/auth/logout`);
  return res.data;
}

export async function getMe(): Promise<any> {
  const res = await axios.get(`${API_BASE}/customer/auth/me`);
  return res.data;
}

// --- Escalation recovery (plaintext; auth via Bearer/cookie) ---
export async function recoverySendOtp(): Promise<any> {
  const res = await axios.post(`${API_BASE}/customer/auth/recovery/send-otp`, {});
  return res.data;
}

export async function challengeOtp(otp: string): Promise<any> {
  const res = await axios.post(`${API_BASE}/customer/auth/challenge-otp`, { otp });
  return res.data;
}

export async function passwordReset(otp: string, newPassword: string): Promise<any> {
  const res = await axios.post(`${API_BASE}/customer/auth/password-reset`, { otp, new_password: newPassword });
  return res.data;
}

export async function cardChallenge(): Promise<any> {
  const res = await axios.post(`${API_BASE}/customer/auth/card-challenge`, {});
  return res.data;
}

export async function tier4Verify(otp: string, answers: Record<string, string>, newPassword: string): Promise<any> {
  const res = await axios.post(`${API_BASE}/customer/auth/tier4-verify`, { otp, answers, new_password: newPassword });
  return res.data;
}

export async function getAccountDetails(cryptoState: CryptoState): Promise<any> {
  return makeEncryptedRequest('/customer/account', {}, cryptoState);
}

export async function getStatements(cryptoState: CryptoState): Promise<any> {
  return makeEncryptedRequest('/customer/statements', {}, cryptoState);
}

export async function getBeneficiaries(cryptoState: CryptoState): Promise<any> {
  return makeEncryptedRequest('/customer/beneficiaries', {}, cryptoState);
}

export async function addBeneficiary(
  cryptoState: CryptoState,
  name: string,
  accountNumber: string,
  bankName: string
): Promise<any> {
  return makeEncryptedRequest(
    '/customer/beneficiaries',
    { name, account_number: accountNumber, bank_name: bankName },
    cryptoState
  );
}

export async function transferMoney(
  cryptoState: CryptoState,
  amount: number,
  beneficiaryId: any,
  isNew: boolean,
  beneficiaryName?: string,
  accountNumber?: string
): Promise<any> {
  return makeEncryptedRequest(
    '/customer/transfer',
    {
      amount,
      beneficiary_id: beneficiaryId,
      is_new_beneficiary: isNew,
      ...(beneficiaryName ? { beneficiary_name: beneficiaryName } : {}),
      ...(accountNumber ? { account_number: accountNumber } : {}),
    },
    cryptoState
  );
}

export async function sendTelemetry(
  sessionId: string,
  keyVersion: number,
  aesKey: string,
  events: any[]
): Promise<any> {
  try {
    const plaintext = JSON.stringify({ events });
    const encrypted = await encryptData(plaintext, aesKey);
    const payload = {
      session_id: sessionId,
      key_version: keyVersion,
      ciphertext: encrypted.ciphertext,
      nonce: encrypted.nonce,
      tag: encrypted.tag
    };
    const res = await axios.post(`${API_BASE}/customer/telemetry`, payload);
    return res.data;
  } catch (error) {
    console.error('Silent telemetry send failed:', error);
    // Standard failover: send unencrypted if keys are desynced to ensure telemetry is captured
    try {
      const res = await axios.post(`${API_BASE}/customer/telemetry`, {
        session_id: sessionId,
        events
      });
      return res.data;
    } catch (e) {
      return null;
    }
  }
}

export async function sendTelemetryBeacon(
  sessionId: string,
  keyVersion: number,
  aesKey: string,
  events: any[]
): Promise<void> {
  try {
    const plaintext = JSON.stringify({ events });
    const encrypted = await encryptData(plaintext, aesKey);
    const payload = {
      session_id: sessionId,
      key_version: keyVersion,
      ciphertext: encrypted.ciphertext,
      nonce: encrypted.nonce,
      tag: encrypted.tag
    };
    fetch(`${API_BASE}/customer/telemetry`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      keepalive: true
    });
  } catch (error) {
    fetch(`${API_BASE}/customer/telemetry`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId, events }),
      keepalive: true
    });
  }
}

export async function getRecoveryCard(): Promise<any> {
  const res = await axios.get(`${API_BASE}/customer/auth/recovery-card`);
  return res.data;
}
