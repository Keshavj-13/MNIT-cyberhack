const puppeteer = require('puppeteer');
const axios = require('axios');

(async () => {
  const browser = await puppeteer.launch();
  const page = await browser.newPage();
  page.on('console', msg => console.log('PAGE LOG:', msg.text()));
  page.on('pageerror', error => console.log('PAGE ERROR:', error.message));
  
  await page.goto('http://127.0.0.1:3001');
  await new Promise(r => setTimeout(r, 2000));
  
  // Login
  const inputs = await page.$$('input');
  if (inputs.length > 0) {
    await inputs[0].type('keshav');
    await inputs[1].type('DemoPass@Mnit2026!');
    await page.click('button');
    await new Promise(r => setTimeout(r, 4000));
  }
  
  let bodyText = await page.evaluate(() => document.body.innerText);
  console.log('BODY BEFORE ATTACK:', bodyText.substring(0, 100).replace(/\n/g, ' '));
  
  // Launch attack!
  console.log('LAUNCHING ATTACK...');
  try {
    await axios.post('http://127.0.0.1:8003/attacker/scenarios/phishing_victim/run-live', { target_username: 'keshav' }, {
      headers: { Authorization: `Bearer ATTACKER_TOKEN_HERE` }
    });
    console.log('ATTACK LAUNCHED');
  } catch (err) {
    console.log('ATTACK ERR:', err.message);
  }
  
  // Wait 15 seconds for the attack to finish and the frontend to poll and crash!
  await new Promise(r => setTimeout(r, 15000));
  
  bodyText = await page.evaluate(() => document.body.innerText);
  console.log('BODY AFTER ATTACK LENGTH:', bodyText.length);
  if (bodyText.length < 10) console.log('BODY IS EMPTY (WHITE SCREEN)');
  else console.log('BODY AFTER ATTACK:', bodyText.substring(0, 100).replace(/\n/g, ' '));
  
  await browser.close();
})();
