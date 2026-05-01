const { chromium } = require('playwright');
const fs = require('fs');
const path = require('path');

(async () => {
  const storagePath = path.resolve(__dirname, 'storageState.json');
  const target = 'https://ai-talent-finder-production-ed09.up.railway.app/';
  console.log('Using storage state:', storagePath);
  const browser = await chromium.launch();
  const context = await browser.newContext({ storageState: storagePath });
  const page = await context.newPage();
  let response = null;
  try {
    response = await page.goto(target, { waitUntil: 'networkidle', timeout: 30000 });
  } catch (err) {
    console.error('Navigation error:', err.message);
  }
  if (response) {
    console.log('HTTP status:', response.status());
    console.log('Final URL:', page.url());
    const headers = response.headers();
    console.log('Content-Type:', headers['content-type'] || 'unknown');
    try {
      const title = await page.title();
      console.log('Page title:', title || '(none)');
    } catch (e) {
      console.log('Could not read title:', e.message);
    }
    try {
      const text = await response.text();
      console.log('--- Begin content snippet ---');
      const snippet = text.slice(0, 2000);
      console.log(snippet.replace(/\n/g, '\\n'));
      console.log('--- End content snippet ---');
    } catch (e) {
      console.log('Could not read response body:', e.message);
    }
  } else {
    console.log('No response received for navigation.');
  }
  const screenshotPath = path.resolve(__dirname, 'check_prod_screenshot.png');
  try {
    await page.screenshot({ path: screenshotPath, fullPage: true });
    console.log('Saved screenshot to', screenshotPath);
  } catch (e) {
    console.log('Screenshot failed:', e.message);
  }
  await browser.close();
})().catch(err => {
  console.error('Script error:', err);
  process.exit(2);
});
