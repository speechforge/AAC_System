const {chromium}=require('../../../.runtime/browser/node_modules/playwright');
const fs=require('fs');
(async()=>{
const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true});
for(const mobile of [false,true]){
 const ctx=await browser.newContext({viewport:{width:mobile?390:1280,height:900},isMobile:mobile,hasTouch:mobile});
 const response=await ctx.request.post('http://localhost:8000/api/auth/login',{data:{username:'demo',password:'AACdemo@2026'}});if(response.status()!==200)throw Error('Login failed');
 const page=await ctx.newPage();page.setDefaultTimeout(15000);let errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.route('https://**/*',r=>{const u=r.request().url();if(u.startsWith('https://unpkg.com/'))return r.fulfill({path:'.runtime/portable/vendor/'+(u.includes('react-dom')?'react-dom.js':u.includes('babel')?'babel.js':'react.js'),contentType:'application/javascript'});if(u.includes('tailwindcss'))return r.fulfill({body:'window.tailwind={config:{}};const css=document.createElement("style");css.textContent='+JSON.stringify(fs.readFileSync('.runtime/portable/vendor/tailwind.css','utf8'))+';document.head.append(css);',contentType:'application/javascript'});return r.abort()});
 await page.goto('http://localhost:8000/',{waitUntil:'domcontentloaded'});await page.locator('[aria-controls="settings-drawer"]').click();await page.locator('#settings-drawer').waitFor();await page.locator('.color-picker summary').click();
 const swatches=page.locator('.theme-swatch');if(await swatches.count()!==12)throw Error('Missing colors');
 const shape=await swatches.first().evaluate(n=>({w:n.offsetWidth,h:n.offsetHeight,r:getComputedStyle(n).borderRadius}));if(shape.w!==44||shape.h!==44||shape.r!=='50%')throw Error('Swatches are not circles: '+JSON.stringify(shape));
 await page.locator('[data-theme-choice="rose"]').click();await page.waitForFunction(()=>document.querySelector('.aac-app').dataset.buttonTheme==='rose');
 for(const [id,value] of [['settings-symbol-style','text'],['settings-playback-speed','0.5'],['settings-display','night-contrast'],['settings-card-size','large'],['settings-ai-mode','single']])await page.locator('#'+id).selectOption(value);
 if(await page.locator('#settings-playback-speed option').count()!==9)throw Error('Missing playback speeds');
 if(await page.locator('.aac-app').getAttribute('data-symbol-style')!=='text')throw Error('Symbol style not applied');
 if(await page.locator('.symbol-grid').getAttribute('data-density')!=='large')throw Error('Card size not applied');
 if(!await page.locator('html').evaluate(n=>n.classList.contains('dark')))throw Error('Night mode not applied');
 const drawer=await page.locator('#settings-drawer').boundingBox();if(drawer.x<0||drawer.x+drawer.width>(mobile?390:1280)+1)throw Error('Drawer exceeds viewport');
 await page.locator('#settings-drawer').evaluate(n=>n.scrollTop=0);
 if(mobile){await page.mouse.move(0,50);if(!await page.locator('#settings-drawer').isVisible())throw Error('Touch drawer closed on mouse move');await page.locator('.settings-overlay').tap({position:{x:5,y:50}});}
 else {await page.mouse.move(drawer.x+50,100);await page.mouse.move(drawer.x-25,100);}
 await page.locator('#settings-drawer').waitFor({state:'detached'});
 await page.locator('[aria-controls="settings-drawer"]').click();await page.keyboard.press('Escape');await page.locator('#settings-drawer').waitFor({state:'detached'});
 if(errors.length)throw Error(errors.join('\n'));console.log('PASS '+(mobile?'mobile':'desktop')+': circles, dropdowns, state updates, closing, Escape, width.');await ctx.close();
}
await browser.close();
})().catch(e=>{console.error(e);process.exit(1)});
