// Browser storage flow against localhost. TTS is stubbed here; speech has separate tests.
const {chromium}=require('../../../.runtime/browser/node_modules/playwright');
const assert=require('assert');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROME_BIN||'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 const errors=[];
 async function open(){
  const context=await browser.newContext();
  await context.route('**/firebase*-compat.js',route=>route.abort());
  await context.route('**/api/tts',route=>route.fulfill({status:503,contentType:'application/json',body:JSON.stringify({detail:'Speech disabled in storage browser test'})}));
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://localhost:8000/');await page.waitForSelector('#personal-dashboard');
  await page.waitForFunction(()=>document.querySelector('#personal-dashboard [role=status]')?.textContent.includes('खाते')||document.querySelector('#personal-dashboard [role=status]')?.textContent.includes('સંગ્રહિત')||document.querySelector('#personal-dashboard [role=status]')?.textContent.includes('सहेजा'));
  return {context,page};
 }
 try{
  const a=await open();const page=a.page;
  await page.locator('select').first().selectOption('gu');
  await page.locator('#symbolBoard button').filter({hasText:'જોઈએ'}).first().click();
  await page.waitForFunction(()=>document.querySelector('#frequent-words').textContent.includes('જોઈએ'));
  await page.reload();await page.waitForSelector('#frequent-words button');
  assert((await page.locator('#frequent-words').innerText()).includes('જોઈએ'));
  await page.locator('select').first().selectOption('mr');
  await page.waitForTimeout(400);
  assert.equal(await page.locator('#frequent-words button').count(),0);
  await page.locator('#symbolBoard button').filter({hasText:'पाहिजे'}).first().click();
  await page.waitForFunction(()=>document.querySelector('#frequent-words').textContent.includes('पाहिजे'));
  await page.getByText('मदत करा!',{exact:true}).first().click();
  await page.waitForSelector('#recent-conversations li');
  await page.locator('#recent-conversations li').first().locator('button').last().click();
  await page.waitForSelector('#account-bookmarks li');
  const saved=await page.locator('#account-bookmarks').innerText();
  await page.reload();await page.waitForSelector('#account-bookmarks li');
  assert.equal(await page.locator('#account-bookmarks').innerText(),saved);
  const b=await open();await b.page.locator('select').first().selectOption('mr');await b.page.waitForTimeout(400);
  assert.equal(await b.page.locator('#frequent-words button').count(),0);
  assert.equal(await b.page.locator('#recent-conversations li').count(),0);
  assert.equal(await b.page.locator('#account-bookmarks li').count(),0);
  await page.locator('#account-bookmarks li').first().locator('button').last().click();
  await page.waitForFunction(()=>document.querySelectorAll('#account-bookmarks li').length===0);
  const old=(await a.context.cookies()).find(c=>c.name==='aac_session').value;
  await page.getByText('सत्र समाप्त करा',{exact:true}).click();
  await page.waitForTimeout(700);
  const current=(await a.context.cookies()).find(c=>c.name==='aac_session').value;
  assert.notEqual(old,current);
  await page.waitForSelector('#frequent-words button');
  await page.screenshot({path:process.cwd()+'/.runtime/reports/personal-marathi.png',fullPage:true});
  assert.deepEqual(errors,[]);
  console.log('PASS: Gujarati/Marathi word tracking; recents; bookmark save/delete; reload persistence; guest isolation; logout rotation; no browser errors.');
 }finally{await browser.close()}
})().catch(err=>{console.error(err);process.exitCode=1});
