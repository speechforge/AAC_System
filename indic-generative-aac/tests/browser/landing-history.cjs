const {chromium}=require('../../../.runtime/browser/node_modules/playwright');
const assert=require('assert');
(async()=>{
const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
const errors=[];
try{
const context=await browser.newContext();const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
for(const [width,height] of [[1440,900],[1280,720],[1024,768],[768,1024],[390,844],[375,667],[320,568],[844,390],[667,375]]){
 await page.setViewportSize({width,height});await page.goto('http://localhost:8000/welcome');await page.waitForSelector('.primary-cta');assert.equal(await page.locator('a[href="/login"]').count(),1);
 await page.evaluate(()=>document.fonts.ready);
 const layout=await page.evaluate(()=>{const d=document.documentElement,b=document.body;return {height:innerHeight,scrollHeight:Math.max(d.scrollHeight,b.scrollHeight),width:innerWidth,scrollWidth:Math.max(d.scrollWidth,b.scrollWidth),hero:document.querySelector('.hero').getBoundingClientRect().toJSON()}});
 assert(layout.scrollHeight<=height,`Vertical overflow ${width}x${height}: ${JSON.stringify(layout)}`);assert(layout.scrollWidth<=width,`Horizontal overflow ${width}x${height}`);
 for(const selector of ['.primary-cta','.secondary-cta','footer','.languages','.feature-grid']){
 const box=await page.locator(selector).boundingBox();assert(box.y>=0&&box.y+box.height<=height+.5,`${selector} outside viewport at ${width}x${height}: ${JSON.stringify(box)}`);
 }
 const overlap=await page.evaluate(()=>{const a=document.querySelector('.hero-actions').getBoundingClientRect(),b=document.querySelector('.everyday').getBoundingClientRect();return a.bottom>b.top});assert(!overlap,'Actions overlap features');
 await page.mouse.wheel(0,900);assert.equal(await page.evaluate(()=>scrollY),0);
 await page.screenshot({path:`.runtime/reports/landing-${width}x${height}.png`});console.log('PASS single viewport',width,height);
}
await page.setViewportSize({width:1440,height:900});await page.goto('http://localhost:8000/welcome');await page.locator('#motion-toggle').click();assert.equal(await page.locator('html').getAttribute('data-motion'),'off');
await page.emulateMedia({reducedMotion:'reduce'});await page.waitForFunction(()=>document.querySelector('#motion-toggle').disabled);assert(await page.locator('#motion-toggle').isDisabled());
await page.locator('.primary-cta').click();await page.waitForURL('**/login');assert.equal(await page.locator('h1').innerText(),'Welcome back');await page.locator('#password').fill('examplepass');await page.locator('#toggle-password').click();assert.equal(await page.locator('#password').getAttribute('type'),'text');
await page.locator('#username').fill('demo');await page.locator('#password').fill('AACdemo@2026');await page.locator('button[type=submit]').click();await page.waitForURL('http://localhost:8000/');await page.waitForSelector('.history-trigger');
assert.equal(await page.locator('#core-panel,.board-history-bar').count(),0);assert(await page.locator('.header-controls button').nth(1).evaluate(e=>e.classList.contains('history-trigger')));await page.locator('.history-trigger').click();await page.waitForSelector('#history-panel');await page.keyboard.press('Escape');assert.equal(await page.locator('#history-panel').count(),0);assert(await page.locator('.history-trigger').evaluate(e=>e===document.activeElement));
await page.route('**/api/tts',route=>route.fulfill({status:200,contentType:'application/json',body:JSON.stringify({audio_kind:'f5tts',audio_b64:'test',sample_rate:24000})}));
await page.evaluate(()=>{window.Audio=class {play(){return Promise.resolve()}pause(){}}});
await page.locator('.quick-express button').first().click();await page.locator('.history-trigger').click();await page.waitForSelector('.history-list li');const message=await page.locator('.history-message span').first().innerText();assert(message.length>0);await page.reload();await page.waitForSelector('.history-trigger');await page.locator('.history-trigger').click();await page.waitForSelector('.history-list li');assert.equal(await page.locator('.history-message span').first().innerText(),message);
await page.keyboard.press('Escape');
for(const lang of ['hi','gu','mr','en']){await page.locator('.language-select').selectOption(lang);await page.locator('.history-trigger').click();await page.waitForSelector('#history-panel');await page.keyboard.press('Escape')}
console.log('PASS login, password visibility, history persistence, four languages, dismissal and focus restoration');
await page.setViewportSize({width:390,height:844});await page.locator('.history-trigger').click();await page.screenshot({path:'.runtime/reports/history-mobile.png'});assert.deepEqual(errors,[]);await context.close();
}finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
