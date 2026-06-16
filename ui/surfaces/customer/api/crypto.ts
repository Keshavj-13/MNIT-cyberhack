function base64ToUint8Array(base64: string): Uint8Array {
  const binaryString = window.atob(base64);
  const len = binaryString.length;
  const bytes = new Uint8Array(len);
  for (let i = 0; i < len; i++) {
    bytes[i] = binaryString.charCodeAt(i);
  }
  return bytes;
}

function uint8ArrayToBase64(uint8Array: Uint8Array): string {
  let binary = '';
  const len = uint8Array.byteLength;
  for (let i = 0; i < len; i++) {
    binary += String.fromCharCode(uint8Array[i]);
  }
  return window.btoa(binary);
}

// Compute HMAC-SHA256 in JS using Web Crypto API
async function hmacSha256(keyBytes: Uint8Array, dataBytes: Uint8Array): Promise<Uint8Array> {
  const cryptoKey = await window.crypto.subtle.importKey(
    'raw',
    keyBytes,
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );
  const sigBuffer = await window.crypto.subtle.sign('HMAC', cryptoKey, dataBytes);
  return new Uint8Array(sigBuffer);
}

// Derive keystream matching python counter block generation
async function deriveKeystream(keyBytes: Uint8Array, nonceBytes: Uint8Array, length: number): Promise<Uint8Array> {
  const keystream = new Uint8Array(length);
  let offset = 0;
  let counter = 0;
  
  while (offset < length) {
    // Construct counter bytes (4 bytes big-endian)
    const counterBytes = new Uint8Array(4);
    const view = new DataView(counterBytes.buffer);
    view.setUint32(0, counter, false);
    
    // nonce + counter
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

// Bitwise XOR between two byte arrays
function xorBytes(a: Uint8Array, b: Uint8Array): Uint8Array {
  const result = new Uint8Array(a.length);
  for (let i = 0; i < a.length; i++) {
    result[i] = a[i] ^ b[i];
  }
  return result;
}

export async function encryptData(plaintext: string, keyB64: string): Promise<{ ciphertext: string; nonce: string; tag: string }> {
  try {
    const keyBytes = base64ToUint8Array(keyB64);
    const nonceBytes = window.crypto.getRandomValues(new Uint8Array(16)); // Secure random 16-byte nonce
    const encoder = new TextEncoder();
    const plaintextBytes = encoder.encode(plaintext);
    
    const keystream = await deriveKeystream(keyBytes, nonceBytes, plaintextBytes.length);
    const ciphertextBytes = xorBytes(plaintextBytes, keystream);
    
    // Encrypt-then-MAC tag: HMAC(key, nonce + ciphertext)
    const macData = new Uint8Array(nonceBytes.length + ciphertextBytes.length);
    macData.set(nonceBytes, 0);
    macData.set(ciphertextBytes, nonceBytes.length);
    const macBytes = await hmacSha256(keyBytes, macData);
    
    return {
      ciphertext: uint8ArrayToBase64(ciphertextBytes),
      nonce: uint8ArrayToBase64(nonceBytes),
      tag: uint8ArrayToBase64(macBytes)
    };
  } catch (error) {
    console.error("Encryption failed:", error);
    throw error;
  }
}

export async function decryptData(ciphertextB64: string, nonceB64: string, tagB64: string, keyB64: string): Promise<string> {
  try {
    const keyBytes = base64ToUint8Array(keyB64);
    const nonceBytes = base64ToUint8Array(nonceB64);
    const tagBytes = base64ToUint8Array(tagB64);
    const ciphertextBytes = base64ToUint8Array(ciphertextB64);
    
    // Verify MAC (Encrypt-then-MAC prevents oracle attacks)
    const macData = new Uint8Array(nonceBytes.length + ciphertextBytes.length);
    macData.set(nonceBytes, 0);
    macData.set(ciphertextBytes, nonceBytes.length);
    const expectedMacBytes = await hmacSha256(keyBytes, macData);
    
    // Constant-time compare
    let valid = true;
    if (tagBytes.length !== expectedMacBytes.length) {
      valid = false;
    }
    for (let i = 0; i < tagBytes.length; i++) {
      if (tagBytes[i] !== expectedMacBytes[i]) {
        valid = false;
      }
    }
    
    if (!valid) {
      throw new Error("Cryptographic integrity check failed: Invalid signature tag");
    }
    
    const keystream = await deriveKeystream(keyBytes, nonceBytes, ciphertextBytes.length);
    const plaintextBytes = xorBytes(ciphertextBytes, keystream);
    
    const decoder = new TextDecoder();
    return decoder.decode(plaintextBytes);
  } catch (error) {
    console.error("Decryption failed:", error);
    throw error;
  }
}
