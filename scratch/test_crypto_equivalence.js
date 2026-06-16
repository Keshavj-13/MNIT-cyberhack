import { webcrypto } from 'crypto';
import fs from 'fs';

function base64ToUint8Array(base64) {
  return Uint8Array.from(Buffer.from(base64, 'base64'));
}

function uint8ArrayToBase64(uint8Array) {
  return Buffer.from(uint8Array).toString('base64');
}

async function hmacSha256(keyBytes, dataBytes) {
  const cryptoKey = await webcrypto.subtle.importKey(
    'raw',
    keyBytes,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  const sigBuffer = await webcrypto.subtle.sign('HMAC', cryptoKey, dataBytes);
  return new Uint8Array(sigBuffer);
}

async function deriveKeystream(keyBytes, nonceBytes, length) {
  const keystream = new Uint8Array(length);
  let offset = 0;
  let counter = 0;
  
  while (offset < length) {
    const counterBytes = new Uint8Array(4);
    const view = new DataView(counterBytes.buffer);
    view.setUint32(0, counter, false);
    
    const blockData = new Uint8Array(nonceBytes.length + 4);
    blockData.set(nonceBytes, 0);
    blockData.set(counterBytes, nonceBytes.length);
    
    const block = await hmacSha256(keyBytes, blockData);
    
    const bytesToWrite = Math.min(block.length, length - offset);
    keystream.set(block.slice(0, bytesToWrite), offset);
    
    offset += bytesToWrite;
    counter += 1;
  }
  
  return keystream;
}

function xorBytes(a, b) {
  const result = new Uint8Array(a.length);
  for (let i = 0; i < a.length; i++) {
    result[i] = a[i] ^ b[i];
  }
  return result;
}

async function run() {
  const keyBytes = webcrypto.getRandomValues(new Uint8Array(32));
  const nonceBytes = webcrypto.getRandomValues(new Uint8Array(16));
  const keyB64 = uint8ArrayToBase64(keyBytes);
  
  const plaintext = "Hello from Web Crypto Subtle API!";
  const plaintextBytes = new TextEncoder().encode(plaintext);
  
  const keystream = await deriveKeystream(keyBytes, nonceBytes, plaintextBytes.length);
  const ciphertextBytes = xorBytes(plaintextBytes, keystream);
  
  // Tag: HMAC(key, nonce + ciphertext)
  const macData = new Uint8Array(nonceBytes.length + ciphertextBytes.length);
  macData.set(nonceBytes, 0);
  macData.set(ciphertextBytes, nonceBytes.length);
  const macBytes = await hmacSha256(keyBytes, macData);
  
  const data = {
    plaintext,
    key_b64: keyB64,
    ciphertext_b64: uint8ArrayToBase64(ciphertextBytes),
    nonce_b64: uint8ArrayToBase64(nonceBytes),
    tag_b64: uint8ArrayToBase64(macBytes)
  };
  
  fs.writeFileSync('scratch/crypto_exchange.json', JSON.stringify(data, null, 2));
  console.log("Web Crypto encryption complete. Output written to scratch/crypto_exchange.json");
}

run();
