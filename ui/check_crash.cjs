const puppeteer = require('puppeteer');

(async () => {
  try {
    const browser = await puppeteer.launch({
      headless: true,
      args: ['--no-sandbox']
    });
    
    const page = await browser.newPage();
    page.on('console', msg => console.log('CONSOLE:', msg.text()));
    
    console.log('Navigating to Attacker UI...');
    await page.goto('http://127.0.0.1:3003', { waitUntil: 'networkidle2' });
    console.log('Page loaded');
    
    // Login
    await page.type('input[placeholder="attacker"]', 'attacker');
    await page.type('input[placeholder="••••••••"]', 'attack123'); 
    await page.click('button[type="submit"]');
    
    await new Promise(r => setTimeout(r, 2000));
    console.log('Logged in to Attacker UI');
    
    // Toggle Live Mode
    console.log('Toggling LIVE mode...');
    await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const simBtn = buttons.find(b => b.innerText.includes('SIM') || b.innerText.includes('LIVE'));
      if(simBtn) simBtn.click();
    });
    
    await new Promise(r => setTimeout(r, 1000));
    
    console.log('Clicking Account Takeover...');
    // We need to find the scenario button with text "Account Takeover"
    await page.evaluate(() => {
      const buttons = Array.from(document.querySelectorAll('button'));
      const btn = buttons.find(b => b.innerText.includes('Account Takeover'));
      if(btn) btn.click();
    });
    
    console.log('Waiting for attack to finish (10s)...');
    await new Promise(r => setTimeout(r, 10000));
    
    const html = await page.content();
    console.log("HTML LENGTH AFTER ATTACK:", html.length);
    console.log("CONTAINS LIVE TARGET?:", html.includes("LIVE TARGET: keshav"));
    console.log("CONTAINS ERROR?:", html.includes("Failed"));
    
    await browser.close();
  } catch (err) {
    console.error('Script error:', err);
    process.exit(1);
  }
})();
