/* Real Chromium clipboard and pointer/keyboard actions against the regular communicator. */
const {chromium}=require('../../../.runtime/browser/node_modules/playwright');
const assert=require('node:assert/strict');
const fs=require('node:fs');
(async()=>{
  const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
  try{
    const context=await browser.newContext({viewport:{width:1280,height:900},permissions:['clipboard-read','clipboard-write'],reducedMotion:'reduce'});
    await context.route('**/firebase*-compat.js',route=>route.abort());
    await context.addInitScript(()=>{
      localStorage.setItem('aac_studio_cache_v1',JSON.stringify({language:'en',autoSpeakOnSelect:false}));
      localStorage.setItem('aac_access_v1',JSON.stringify({mode:'offline',vibration:false}));
    });
    const page=await context.newPage();
    const errors=[];page.on('pageerror',e=>errors.push(e.message));
    let speechCalls=0;page.on('request',r=>{if(r.url().endsWith('/api/tts'))speechCalls++});
    await page.goto('http://localhost:8000/');
    const input=page.locator('.sentence-strip input');await input.waitFor();
    const chips=()=>page.locator('.sentence-strip .token-speak>span:last-child').allTextContents();
    const paste=async text=>{await input.focus();await page.evaluate(text=>navigator.clipboard.writeText(text),text);await input.press('Control+V')};
    await paste('water, food, help');
    await page.waitForFunction(()=>document.querySelectorAll('.sentence-strip .token-speak').length===3);
    assert.deepEqual(await chips(),['water','food','help']);assert.equal(await input.inputValue(),'');
    await paste(' , orange juice, Alex, પાણી, मदद, पाणी, ,');
    await page.waitForFunction(()=>document.querySelectorAll('.sentence-strip .token-speak').length===8);
    assert.deepEqual(await chips(),['water','food','help','orange juice','Alex','પાણી','मदद','पाणी']);
    await paste('a single phrase');
    await page.waitForFunction(()=>document.querySelector('.sentence-strip input').value==='a single phrase');
    assert.equal((await chips()).length,8);
    await input.fill('keep old end');
    await input.evaluate(el=>el.setSelectionRange(5,8));
    await paste('new, next');
    await page.waitForFunction(()=>document.querySelectorAll('.sentence-strip .token-speak').length===10);
    assert.deepEqual((await chips()).slice(-2),['keep new','next end']);
    const menu=page.locator('.canvas-menu'),summary=menu.locator('summary');
    await summary.click();assert.equal(await menu.getAttribute('open'),'');
    await menu.locator('button').first().hover();assert.equal(await menu.getAttribute('open'),'','Moving into popup must keep it open');
    await page.locator('#intended-sentence').hover();assert.equal(await menu.getAttribute('open'),null,'Leaving menu closes it');
    await summary.focus();await summary.press('Enter');assert.equal(await menu.getAttribute('open'),'');
    await summary.press('Tab');await page.keyboard.press('Escape');
    assert.equal(await menu.getAttribute('open'),null);assert(await summary.evaluate(el=>el===document.activeElement));
    await summary.click();await menu.getByRole('button',{name:'Delete Last',exact:true}).click();
    assert.equal((await chips()).length,9);assert.equal(await menu.getAttribute('open'),null);
    await page.setViewportSize({width:390,height:844});
    await summary.click();await menu.locator('button').first().hover();
    const box=await menu.locator('.canvas-menu-actions').boundingBox();
    assert(box.x>=0 && box.x+box.width<=390,'Mobile menu must fit viewport');
    assert(await summary.isVisible());
    assert.equal(await page.evaluate(()=>document.documentElement.scrollHeight>innerHeight),false);
    await page.screenshot({path:'docs/aac-redesign/evidence/canvas-paste-menu-mobile.png'});
    assert.equal(speechCalls,0,'Bulk editing must not start speech');assert.deepEqual(errors,[]);
    fs.writeFileSync('docs/aac-redesign/evidence/canvas-paste-menu.json',JSON.stringify({clipboard:'native Chromium clipboard',inputOrder:true,emptySegmentsIgnored:true,multiwordLabels:true,IndicLabels:true,singlePasteUnchanged:true,selectionReplacement:true,hoverOutCloses:true,popupHoverStaysOpen:true,escapeFocusRestored:true,menuActionWorks:true,mobileWidth:390,verticalPageScroll:false,ttsCalls:speechCalls,pageErrors:errors},null,2));
    console.log('PASS comma paste, Indic labels, phrases, selection replacement, native single paste, hover-out, keyboard Escape/focus, action close, mobile menu and no page scroll.');
  }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
