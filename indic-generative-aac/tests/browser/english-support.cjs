const {chromium}=require('../../../.runtime/browser/node_modules/playwright');
const assert=require('assert');
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 try {
  const context=await browser.newContext();
  await context.route('**/firebase*-compat.js',r=>r.abort());
  await context.route('**/api/tts',r=>r.fulfill({status:503,contentType:'application/json',body:'{"detail":"Speech disabled in storage test"}'}));
  const page=await context.newPage(),errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://localhost:8000/');await page.waitForSelector('select');
  await page.locator('select').first().selectOption('en');
  await page.waitForFunction(()=>document.querySelector('#personal-dashboard [role=status]')?.textContent==='Saved to your account');
  assert.equal(await page.locator('html').getAttribute('lang'),'en');
  assert.equal(await page.locator('select').first().locator('option').count(),4);
  await page.locator('#symbolBoard button').filter({hasText:'Want'}).first().click();
  await page.waitForFunction(()=>document.querySelector('#frequent-words').textContent.includes('Want'));
  await page.getByText('Water',{exact:true}).first().click();
  await page.waitForFunction(()=>document.querySelector('#recent-conversations').textContent.includes('I want water.'));
  await page.locator('#recent-conversations li').first().locator('button').last().click();
  await page.waitForSelector('#account-bookmarks li');
  await page.reload();await page.waitForSelector('#account-bookmarks li');
  assert((await page.locator('#account-bookmarks').innerText()).includes('I want water.'));
  await page.locator('select').first().selectOption('gu');await page.waitForTimeout(400);
  assert.equal(await page.locator('#account-bookmarks li').count(),0);
  assert(!/[A-Za-z]/.test(await page.locator('#frequent-words').innerText()));
  await page.locator('select').first().selectOption('en');await page.waitForSelector('#account-bookmarks li');
  assert.deepEqual(errors,[]);
  await page.screenshot({path:process.cwd()+'/.runtime/reports/english-ui.png',fullPage:true});
  console.log('PASS: English selection, interface, word tracking, recents, bookmarks, reload persistence and language isolation.');
 } finally {await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
