import { chromium } from 'playwright';
import fs from 'fs';
import path from 'path';

async function capture() {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  // Create screenshots directory
  const docsDir = path.join(process.cwd(), '..', 'screenshots');
  if (!fs.existsSync(docsDir)) {
    fs.mkdirSync(docsDir, { recursive: true });
  }

  console.log("Navigating to dashboard...");
  await page.goto('http://localhost:3000');
  await page.waitForTimeout(5000); // Wait for animations
  await page.screenshot({ path: path.join(docsDir, 'dashboard.png'), fullPage: true });

  console.log("Capturing playground...");
  await page.click('button:has-text("Playground")');
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(docsDir, 'playground.png'), fullPage: true });

  console.log("Capturing timeline...");
  await page.click('button:has-text("Timeline")');
  await page.waitForTimeout(2000);
  await page.screenshot({ path: path.join(docsDir, 'timeline.png'), fullPage: true });

  await browser.close();
  console.log("Screenshots captured successfully.");
}

capture().catch(err => {
  console.error("Capture failed:", err);
  process.exit(1);
});
