const {chromium}=require('../../.runtime/browser/node_modules/playwright');
const assert=require('node:assert/strict'),fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..');
(async()=>{const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});try{
 const page=await browser.newPage({viewport:{width:1280,height:1000}});
 const url=process.env.MOS_CHECK_URL||'http://127.0.0.1:8011';
 let ready=false;for(let i=0;i<12;i++){try{await page.goto(url,{timeout:10000});await page.locator('#understand-instructions').waitFor({state:'visible',timeout:3000});ready=true;break;}catch(e){console.log('Waiting for portal route',i+1);await page.waitForTimeout(3000)}}assert(ready);
 assert.equal(await page.locator('a[href*="admin"]').count(),0);
 assert.equal(await page.locator('footer').count(),0);
 const mother=page.locator('[name=mother_tongue]');assert(await mother.isDisabled());
 assert((await page.locator('.instruction-checkpoint').innerText()).includes('You do not need to speak or understand these languages fluently'));
 await page.locator('#understand-instructions').click();assert(await mother.isEnabled());await mother.fill('Gujarati');
 assert.equal(await page.locator('#understand-instructions').getAttribute('aria-pressed'),'true');
 await page.screenshot({path:root+'/evidence/instructions-checkpoint-'+(url.startsWith('https')?'public':'local')+'.png',fullPage:true});
 console.log('PASS no participant admin link/footer; mother tongue locked until acknowledgement; naturalness instructions visible. URL:',url);
}finally{await browser.close()}})().catch(e=>{console.error(e);process.exitCode=1});
