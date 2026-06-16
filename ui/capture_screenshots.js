import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

async function capture() {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1440, height: 900 } });

  const docsDir = path.join(process.cwd(), '..', 'screenshots');
  if (!fs.existsSync(docsDir)) {
    fs.mkdirSync(docsDir, { recursive: true });
  }

  console.log("Navigating to app...");
  await page.goto('http://localhost:3000');
  await page.waitForTimeout(1000);

  console.log("Generating risk events via Bank Simulator...");
  await page.click('button:has-text("Bank Simulator")');
  await page.waitForTimeout(500);
  await page.click('button:has-text("Sign In")');
  await page.waitForTimeout(1000);

  await page.click('text=SMS Inbox');
  await page.waitForTimeout(500);
  await page.click('text=SecureTrust-Alert');
  await page.waitForTimeout(1500);

  console.log("Capturing Bank Simulator...");
  await page.click('nav.border-b >> text=Dashboard');
  await page.waitForTimeout(800);
  await page.screenshot({ path: path.join(docsDir, 'playground.png'), fullPage: true });

  console.log("Capturing risk dashboard...");
  await page.click('button[title="Expand sidebar"]').catch(() => {});
  await page.click('aside >> text=Dashboard');
  await page.waitForTimeout(800);
  await page.screenshot({ path: path.join(docsDir, 'dashboard.png'), fullPage: true });

  console.log("Capturing timeline...");
  await page.click('aside >> text=Timeline');
  await page.waitForTimeout(800);
  await page.screenshot({ path: path.join(docsDir, 'timeline.png'), fullPage: true });

  await browser.close();
  console.log("Screenshots captured successfully.");
}

capture().catch(err => {
  console.error("Capture failed:", err);
  process.exit(1);
});
