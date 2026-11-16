/* UI-only checks use a test Audio object and intercepted synthesis responses. */
const {chromium}=require('../../../.runtime/browser/node_modules/playwright');
const assert=require('assert');
function linear(n){n/=255;return n<=.04045?n/12.92:((n+.055)/1.055)**2.4}
function contrast(a,b){let L=c=>{const m=c.match(/[\d.]+/g).slice(0,3).map(Number);return .2126*linear(m[0])+.7152*linear(m[1])+.0722*linear(m[2])};const x=L(a),y=L(b);return(Math.max(x,y)+.05)/(Math.min(x,y)+.05)}
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 const errors=[],ratios=[];
 async function open(width,height){
  const context=await browser.newContext({viewport:{width,height},reducedMotion:'reduce'});
  await context.route('**/firebase*-compat.js',r=>r.abort());
  await context.route('**/api/tts',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify({audio_kind:'f5tts',audio_b64:'test-audio',sample_rate:24000})}));
  await context.route('**/generate',r=>r.fulfill({status:200,contentType:'application/json',body:JSON.stringify({text:'I want water.',outcome:'sentence_template',audio_kind:'f5tts',audio_b64:'test-audio',metrics:{t_total:0}})}));
  await context.addInitScript(()=>{
   if(!localStorage.getItem('aac_studio_cache_v1'))localStorage.setItem('aac_studio_cache_v1',JSON.stringify({language:'en',autoSpeakOnSelect:true}));
   window.__played=[];
   window.Audio=class {constructor(src){this.src=src;this.playbackRate=1;window.__lastAudio=this}pause(){}play(){window.__played.push({rate:this.playbackRate,pitch:this.preservesPitch});this.onplay?.();return Promise.resolve()}};
  });
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));await page.goto('http://localhost:8000/');await page.waitForSelector('.symbol-grid');await page.evaluate(()=>document.fonts.ready);
  await page.waitForFunction(()=>document.querySelector('#personal-dashboard [role=status]')?.textContent==='Saved to your account');return{context,page};
 }
 async function communicationPositions(page){return page.locator('.history-trigger').evaluate(el=>{const r=el.getBoundingClientRect();return{x:Math.round(r.x+scrollX),y:Math.round(r.y+scrollY)}})}
 async function settings(page){await page.getByRole('button',{name:'Preferences',exact:true}).click();await page.waitForSelector('.settings-drawer')}
 try{
  for(const [width,height] of [[320,740],[390,844],[600,960],[768,1024],[1024,768],[1440,900]]){
   const{context,page}=await open(width,height);
   assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Horizontal page overflow at ${width}`);
   const overlap=await page.locator('.header-controls').evaluate(el=>{const rs=[...el.children].map(e=>e.getBoundingClientRect());return rs.some((a,i)=>rs.slice(i+1).some(b=>Math.min(a.right,b.right)-Math.max(a.left,b.left)>1&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>1))});
   assert(!overlap,`Header overlap at ${width}`);
   const baseline=await communicationPositions(page);
   for(const category of ['food','feelings','actions','places']){
    await page.locator(`[data-category="${category}"]`).first().click();assert.deepEqual(await communicationPositions(page),baseline,`History control shifted at ${width}/${category}`);
   }
   for(const language of ['hi','gu','mr','en']){
    await page.locator('.language-select').selectOption(language);assert.equal(await page.locator('.app-brand-name').innerText(),'Indic AAC Studio');
    assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),`Language overflow ${width}/${language}`);
   }
   await page.locator('.language-select').selectOption('en');await settings(page);
   const drawer=await page.locator('.settings-drawer').boundingBox();assert(drawer.x>=0&&drawer.x+drawer.width<=width+.5);
   await page.keyboard.press('Escape');await page.screenshot({path:process.cwd()+`/.runtime/reports/responsive-${width}.png`,fullPage:true});
   console.log('PASS viewport',width,height,'brand, layout, stable history control, settings');
   await context.close();
  }
  const{context,page}=await open(390,844);await settings(page);
  assert.equal(await page.locator('[data-theme-choice]').count(),12);
  for(const dark of [false,true]){
   if(dark){await page.getByRole('button',{name:'Night Mode',exact:true}).click();await page.waitForFunction(()=>document.documentElement.classList.contains('dark'));}
   const body=await page.evaluate(()=>getComputedStyle(document.body).backgroundColor);
   for(const button of await page.locator('[data-theme-choice]').all()){
    await button.click();const name=await button.getAttribute('data-theme-choice');
    assert.equal(await page.evaluate(()=>getComputedStyle(document.body).backgroundColor),body,'Button palette changed page background');
    for(const selector of ['.symbol-grid button','.category-tabs button[aria-pressed=true]']){
     const colors=await page.locator(selector).first().evaluate(el=>({fg:getComputedStyle(el).color,bg:getComputedStyle(el).backgroundColor}));
     const ratio=contrast(colors.fg,colors.bg);assert(ratio>=4.5,`${name} dark=${dark} contrast=${ratio}`);ratios.push(ratio);
    }
   }
  }
  const baseline=await communicationPositions(page);
  for(const style of ['line','contrast','photo','text','emoji']){
   await page.locator(`[data-style-choice="${style}"]`).click();assert.deepEqual(await communicationPositions(page),baseline,'Visual style shifted history toolbar');
   if(style==='text')assert.equal(await page.locator('.symbol-grid .symbol-emoji,.symbol-grid .symbol-drawing,.symbol-grid img').count(),0);
  }
  await page.locator('[data-style-choice="photo"]').click();await page.locator('#photo-concept').selectOption('WATER');
  await page.locator('#symbol-photo-upload').setInputFiles(process.cwd()+'/indic-generative-aac/frontend/photos/water.jpg');
  await page.waitForSelector('.photo-preview');assert((await page.locator('.photo-preview').getAttribute('src')).startsWith('data:image/jpeg'));
  await page.keyboard.press('Escape');await page.locator('[data-category="food"]').first().click();
  await page.waitForSelector('[data-symbol-id="WATER"] img');assert((await page.locator('[data-symbol-id="WATER"] img').getAttribute('src')).startsWith('data:image/jpeg'));
  await page.reload();await page.waitForSelector('.symbol-grid');await settings(page);await page.waitForSelector('.photo-preview');
  for(const rate of [.25,.5,.75,1,1.25,1.5,1.75,2,3]){
   await page.locator(`[data-speed="${rate}"]`).click();await page.keyboard.press('Escape');
   const before=await page.evaluate(()=>window.__played.length);
   await page.locator('.symbol-grid button').first().click();await page.waitForFunction(n=>window.__played.length>n,before);
   let last=await page.evaluate(()=>window.__played.at(-1));assert.equal(last.rate,rate);assert.equal(last.pitch,true);
   await page.getByRole('button',{name:'AI Polish & Speak',exact:true}).click();await page.waitForSelector('#result-sentence');
   last=await page.evaluate(()=>window.__played.at(-1));assert.equal(last.rate,rate);
   await page.getByRole('button',{name:'Replay Voice',exact:true}).click();last=await page.evaluate(()=>window.__played.at(-1));assert.equal(last.rate,rate);
   await settings(page);
  }
  await page.locator('[data-speed="1.75"]').click();await page.keyboard.press('Escape');await page.reload();await page.waitForSelector('.symbol-grid');await settings(page);
  assert.equal(await page.locator('[data-speed="1.75"]').getAttribute('aria-pressed'),'true','Speed did not survive reload in the same session');
  await page.keyboard.press('Escape');await page.getByText('End session',{exact:true}).click();await page.waitForTimeout(500);await settings(page);
  assert.equal(await page.locator('[data-speed="1"]').getAttribute('aria-pressed'),'true','New session did not reset speed');
  assert.deepEqual(errors,[]);console.log('PASS 12 button palettes in light/dark; minimum text contrast',Math.min(...ratios).toFixed(2));
  console.log('PASS five symbol styles, photo upload/persistence, all nine speeds on word/generated/replay speech, session speed restore/reset.');
  await context.close();
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
