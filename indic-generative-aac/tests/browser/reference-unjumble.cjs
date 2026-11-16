/* Backend integration through the unchanged existing canvas; no response fixtures. */
const {chromium}=require('../../../.runtime/browser/node_modules/playwright');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:1280,height:900},reducedMotion:'reduce'});
  await page.route('**/firebase*-compat.js',route=>route.abort());
  await page.addInitScript(()=>{
   localStorage.setItem('aac_studio_cache_v1',JSON.stringify({language:'en',autoSpeakOnSelect:false}));
   localStorage.setItem('aac_access_v1',JSON.stringify({mode:'online'}));
  });
  const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://localhost:8000/login');
  await page.locator('#username').fill('demo');await page.locator('#password').fill('AACdemo@2026');
  await page.locator('button[type=submit]').click();await page.waitForURL('http://localhost:8000/');
  const input=page.locator('.sentence-strip input');await input.waitFor();
  await input.evaluate(el=>{
   const data=new DataTransfer();data.setData('text/plain','share, AAC, clearly, students, the, helps, system, thoughts, their');
   el.dispatchEvent(new ClipboardEvent('paste',{clipboardData:data,bubbles:true,cancelable:true}));
  });
  const chips=()=>page.locator('.sentence-strip .token-speak>span:last-child').allTextContents();
  await page.waitForFunction(()=>document.querySelectorAll('.sentence-strip .token-speak').length===9);
  assert.deepEqual(await chips(),['share','AAC','clearly','students','the','helps','system','thoughts','their']);
  const responsePromise=page.waitForResponse(r=>r.url().endsWith('/api/unjumble')&&r.request().method()==='POST');
  await page.locator('.canvas-menu summary').click();
  await page.locator('.canvas-menu').getByRole('button',{name:'Un-Jumble',exact:true}).click();
  const response=await responsePromise;assert.equal(response.status(),200);
  assert.equal((await response.json()).status,'suggested');
  await page.waitForFunction(()=>document.querySelector('#intended-sentence').textContent==='the AAC system helps students share their thoughts clearly');
  assert.deepEqual(await chips(),['the','AAC','system','helps','students','share','their','thoughts','clearly']);
  assert.equal(await page.locator('.canvas-menu').getAttribute('open'),null);
  assert.equal(await page.locator('button').filter({hasText:'Use this order'}).count(),0,'GUI must retain existing direct application');
  assert.deepEqual(errors,[]);
  await page.screenshot({path:'docs/aac-redesign/evidence/unjumble-current-gui.png'});
  console.log('PASS unchanged current canvas -> nine pasted chips -> existing Un-Jumble -> correct order from live backend; no UI preview added.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
