const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');

async function main() {
  const screenshotsDir = path.join(__dirname, 'screenshots');
  if (!fs.existsSync(screenshotsDir)) {
    fs.mkdirSync(screenshotsDir, { recursive: true });
  }

  console.log("Launching headless browser...");
  const browser = await chromium.launch({ headless: true });
  const context = await browser.newContext({
    viewport: { width: 1440, height: 900 }
  });

  // 1. Showcase UI (http://localhost:3004)
  console.log("1. Capturing Showcase UI...");
  const pageShowcase = await context.newPage();
  try {
    await pageShowcase.goto('http://localhost:3004', { waitUntil: 'networkidle', timeout: 10000 });
    await pageShowcase.screenshot({ path: path.join(screenshotsDir, 'showcase_dashboard.png') });
    console.log("Saved showcase_dashboard.png");
  } catch (err) {
    console.error("Failed showcase UI:", err.message);
  }
  await pageShowcase.close();

  // 2. Attacker UI (http://localhost:3003)
  console.log("2. Capturing Attacker UI...");
  const pageAttacker = await context.newPage();
  try {
    await pageAttacker.goto('http://localhost:3003', { waitUntil: 'networkidle', timeout: 10000 });
    
    // Perform login
    await pageAttacker.fill('input[placeholder="attacker"]', 'attacker');
    await pageAttacker.fill('input[type="password"]', 'attack123');
    await pageAttacker.click('button[type="submit"]');
    await pageAttacker.waitForTimeout(3000); // Wait for transition

    await pageAttacker.screenshot({ path: path.join(screenshotsDir, 'attacker_dashboard.png') });
    console.log("Saved attacker_dashboard.png");
  } catch (err) {
    console.error("Failed attacker UI:", err.message);
  }
  await pageAttacker.close();

  // 3. Customer UI Login & Pages (using keshavj for normal state)
  console.log("3. Capturing Customer Portal (Normal Session with keshavj)...");
  const pageCustomer = await context.newPage();
  try {
    await pageCustomer.goto('http://localhost:3001', { waitUntil: 'networkidle', timeout: 10000 });
    await pageCustomer.screenshot({ path: path.join(screenshotsDir, 'customer_login.png') });
    console.log("Saved customer_login.png");

    // Open Login Modal
    console.log("Opening login modal...");
    await pageCustomer.click('button.signin');
    await pageCustomer.waitForTimeout(1000);

    // Perform Login as normal user keshavj
    await pageCustomer.fill('input[placeholder="e.g. john_doe"]', 'keshavj');
    await pageCustomer.fill('input[placeholder="Enter your password"]', 'DemoPass@Mnit2026!');
    await pageCustomer.click('button.cbi-login-submit');
    await pageCustomer.waitForTimeout(3000); // Wait for transition

    await pageCustomer.screenshot({ path: path.join(screenshotsDir, 'customer_dashboard.png') });
    console.log("Saved customer_dashboard.png");

    // Navigate to Transfer
    await pageCustomer.click('text=Transfer Money');
    await pageCustomer.waitForTimeout(1500);
    await pageCustomer.screenshot({ path: path.join(screenshotsDir, 'customer_transfer.png') });
    console.log("Saved customer_transfer.png");

    // Navigate to Beneficiaries
    await pageCustomer.click('text=Beneficiaries');
    await pageCustomer.waitForTimeout(1500);
    await pageCustomer.screenshot({ path: path.join(screenshotsDir, 'customer_beneficiaries.png') });
    console.log("Saved customer_beneficiaries.png");

    // Navigate to Statements
    await pageCustomer.click('text=Statements');
    await pageCustomer.waitForTimeout(1500);
    await pageCustomer.screenshot({ path: path.join(screenshotsDir, 'customer_statements.png') });
    console.log("Saved customer_statements.png");

    // Navigate to Security Card
    await pageCustomer.click('text=Security Card');
    await pageCustomer.waitForTimeout(1500);
    await pageCustomer.screenshot({ path: path.join(screenshotsDir, 'customer_security_card.png') });
    console.log("Saved customer_security_card.png");

  } catch (err) {
    console.error("Failed customer UI:", err.message);
  }
  await pageCustomer.close();

  // 3b. Customer UI Locked (demo_keshav)
  console.log("3b. Capturing Customer Portal (Locked Session with demo_keshav)...");
  const pageCustomerLocked = await context.newPage();
  try {
    await pageCustomerLocked.goto('http://localhost:3001', { waitUntil: 'networkidle', timeout: 10000 });
    await pageCustomerLocked.click('button.signin');
    await pageCustomerLocked.waitForTimeout(1000);
    await pageCustomerLocked.fill('input[placeholder="e.g. john_doe"]', 'demo_keshav');
    await pageCustomerLocked.fill('input[placeholder="Enter your password"]', 'DemoPass@Mnit2026!');
    await pageCustomerLocked.click('button.cbi-login-submit');
    await pageCustomerLocked.waitForTimeout(3000); // Wait for transition
    await pageCustomerLocked.screenshot({ path: path.join(screenshotsDir, 'customer_contained_lockout.png') });
    console.log("Saved customer_contained_lockout.png");
  } catch (err) {
    console.error("Failed customer locked UI:", err.message);
  }
  await pageCustomerLocked.close();

  // 4. Admin UI Login & Pages (http://localhost:3002)
  console.log("4. Capturing Admin Portal...");
  const pageAdmin = await context.newPage();
  try {
    await pageAdmin.goto('http://localhost:3002', { waitUntil: 'networkidle', timeout: 10000 });
    await pageAdmin.screenshot({ path: path.join(screenshotsDir, 'admin_login.png') });
    console.log("Saved admin_login.png");

    // Perform Login
    await pageAdmin.fill('input[type="text"]', 'admin');
    await pageAdmin.fill('input[type="password"]', 'admin123');
    await pageAdmin.click('button[type="submit"]');
    await pageAdmin.waitForTimeout(3000); // Wait for transition

    await pageAdmin.screenshot({ path: path.join(screenshotsDir, 'admin_incident.png') });
    console.log("Saved admin_incident.png");

    // Navigate to ARIA
    await pageAdmin.click('text=ARIA Investigations');
    await pageAdmin.waitForTimeout(1500);
    await pageAdmin.screenshot({ path: path.join(screenshotsDir, 'admin_aria.png') });
    console.log("Saved admin_aria.png");

    // Navigate to Session Monitor
    await pageAdmin.click('text=Session Monitor');
    await pageAdmin.waitForTimeout(3000); // Allow list to load

    // Click the top session in the table to display telemetry
    const firstRow = await pageAdmin.locator('table tbody tr').first();
    if (await firstRow.isVisible()) {
      await firstRow.click();
      await pageAdmin.waitForTimeout(3000); // Wait for live model assessment to populate on-the-fly!
    }
    await pageAdmin.screenshot({ path: path.join(screenshotsDir, 'admin_sessions.png') });
    console.log("Saved admin_sessions.png");

    // Navigate to Configuration
    await pageAdmin.click('text=Configuration');
    await pageAdmin.waitForTimeout(1500);
    await pageAdmin.screenshot({ path: path.join(screenshotsDir, 'admin_config.png') });
    console.log("Saved admin_config.png");

  } catch (err) {
    console.error("Failed admin UI:", err.message);
  }
  await pageAdmin.close();

  await browser.close();
  console.log("Screenshot capturing completed successfully!");
}

main().catch(console.error);
