import { test, expect, chromium } from '@playwright/test';
import fs from 'fs';
import path from 'path';

test('Full Fraud Chain LIVE Demonstration', async () => {
  test.setTimeout(120000); // 2 minutes timeout

  // Create evidence directories
  const evidenceDir = path.join(process.cwd(), '..', 'demo_evidence');
  if (!fs.existsSync(evidenceDir)) fs.mkdirSync(evidenceDir, { recursive: true });

  const browser = await chromium.launch({ headless: true });
  
  // Contexts for isolation
  const customerContext = await browser.newContext();
  const adminContext = await browser.newContext();
  const attackerContext = await browser.newContext();

  const customerPage = await customerContext.newPage();
  const adminPage = await adminContext.newPage();
  const attackerPage = await attackerContext.newPage();

  // 1. Customer Login
  console.log('Customer logging in...');
  await customerPage.goto('http://127.0.0.1:3001');
  
  // Open the Sign In modal first
  await customerPage.click('button:has-text("Sign In"), a:has-text("Sign In")');
  
  // Need to find the login inputs
  await customerPage.fill('input[type="text"], input[placeholder*="sername"]', 'demo_keshav');
  await customerPage.fill('input[type="password"]', 'DemoPass@Mnit2026!');
  await customerPage.click('button:has-text("Secure Login")');
  
  await expect(customerPage.locator('text=Account Summary').or(customerPage.locator('text=Welcome')).first()).toBeVisible({ timeout: 10000 });
  console.log('Customer logged in successfully.');

  const customerSession = await customerPage.evaluate(() => {
    return JSON.parse(sessionStorage.getItem('cbi_crypto_state') || '{}');
  });
  console.log('Customer Session:', customerSession);

  // 2. Admin Login
  console.log('Admin logging in...');
  await adminPage.goto('http://127.0.0.1:3002');
  await adminPage.fill('input[type="text"], input[placeholder*="sername"]', 'admin');
  await adminPage.fill('input[type="password"]', 'admin123');
  await adminPage.click('button:has-text("Sign In"), button:has-text("Login")');
  await expect(adminPage.locator('text=Sign Out').or(adminPage.locator('text=Logout')).or(adminPage.locator('text=Admin')).first()).toBeVisible({ timeout: 10000 });
  console.log('Admin logged in successfully.');

  // 3. Attacker Login
  console.log('Attacker logging in...');
  await attackerPage.goto('http://127.0.0.1:3003');
  await attackerPage.fill('input[placeholder="attacker"]', 'attacker');
  await attackerPage.fill('input[type="password"]', 'attack123');
  await attackerPage.click('button:has-text("Establish Connection")');
  await expect(attackerPage.locator('text=Threat Simulator').first()).toBeVisible({ timeout: 10000 });
  console.log('Attacker loaded successfully.');

  // 4. Enable LIVE Mode in Attacker Console
  console.log('Enabling LIVE mode...');
  const liveToggle = attackerPage.locator('button:has-text("SIM")');
  if (await liveToggle.isVisible()) {
    await liveToggle.click();
    console.log('LIVE mode toggled.');
  }

  // 5. Execute Full Fraud Chain
  console.log('Running Full Fraud Chain scenario...');
  const runBtn = attackerPage.locator('button:has-text("Full Fraud Chain")');
  await runBtn.click();

  // Wait 15s for the scenario to finish
  console.log('Waiting for scenario to complete (15s)...');
  await attackerPage.waitForTimeout(15000);

  // 6. Capture Screenshots
  console.log('Capturing screenshots...');
  await customerPage.screenshot({ path: path.join(evidenceDir, 'customer_post_attack.png'), fullPage: true });
  await adminPage.screenshot({ path: path.join(evidenceDir, 'admin_post_attack.png'), fullPage: true });
  await attackerPage.screenshot({ path: path.join(evidenceDir, 'attacker_post_attack.png'), fullPage: true });

  // 7. Verify Synchronization Audit
  console.log('Performing Synchronization Audit...');
  const customerSessionAfter = await customerPage.evaluate(() => {
    return JSON.parse(sessionStorage.getItem('cbi_crypto_state') || '{}');
  });
  
  const adminSessionsResponse = await adminPage.evaluate(async () => {
    const res = await fetch('http://127.0.0.1:8002/admin/sessions', {credentials: 'include'});
    return res.json();
  });
  
  const adminTargetSession = adminSessionsResponse.find((s: any) => s.session_id === customerSessionAfter.sessionId);
  
  fs.writeFileSync(path.join(evidenceDir, 'synchronization_audit.json'), JSON.stringify({
    customerState: customerSessionAfter,
    adminObservedState: adminTargetSession
  }, null, 2));

  if (!adminTargetSession) {
    throw new Error('Admin did not observe the session!');
  }
  
  if (adminTargetSession.key_version !== customerSessionAfter.keyVersion) {
    console.error('Mismatch in key_version!', adminTargetSession.key_version, customerSessionAfter.keyVersion);
  }
  if (adminTargetSession.risk_level !== customerSessionAfter.riskLevel) {
    console.error('Mismatch in risk_level!', adminTargetSession.risk_level, customerSessionAfter.riskLevel);
  }
  
  // 8. Generate Trace (Timeline)
  console.log('Extracting Execution Trace...');
  const adminTimelineResponse = await adminPage.evaluate(async () => {
    const res = await fetch('http://127.0.0.1:8002/admin/timeline', {credentials: 'include'});
    return res.json();
  });
  
  const traceOutput = adminTimelineResponse
    .filter((e: any) => e.session_id === customerSessionAfter.sessionId)
    .sort((a: any, b: any) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime())
    .map((e: any) => `[${e.timestamp}] Risk: ${e.overall_risk.toFixed(2)} | Level: ${e.level} | Decision: ${e.decision} | Category: ${e.event_category} | Reason: ${e.why_decision}`)
    .join('\n');
    
  fs.writeFileSync(path.join(evidenceDir, 'timeline.txt'), traceOutput);
  
  console.log('Playwright script completed successfully.');
});
