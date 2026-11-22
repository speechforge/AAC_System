/* Full native browser playback against the isolated QA database on port 8012. */
const {chromium}=require('../../.runtime/browser/node_modules/playwright');
const fs=require('node:fs'),assert=require('node:assert/strict'),path=require('node:path');
const ROOT=path.resolve(__dirname,'..');
(async()=>{
 const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args:['--no-sandbox']});
 try{
  const context=await browser.newContext({viewport:{width:1440,height:1050},reducedMotion:'reduce'});
  const page=await context.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
  await page.goto('http://127.0.0.1:8012/');
  await page.screenshot({path:ROOT+'/evidence/participant-registration.png',fullPage:true});
  await page.locator('[name=name]').fill('QA Browser Listener');await page.locator('[name=email]').fill('qa-'+Date.now()+'@example.test');
  await page.locator('[name=age]').fill('28');await page.locator('[name=gender]').selectOption('Female');await page.locator('#understand-instructions').click();await page.locator('[name=mother_tongue]').fill('Gujarati');await page.locator('[name=organization]').fill('QA fixture — not a real participant');await page.locator('[name=consent]').check();
  await page.locator('#registration-form button[type=submit]').click();await page.locator('#return-card').waitFor({state:'visible'});
  const pid=await page.locator('#saved-participant').innerText();
  await page.locator('#begin-trials').click();
  const expected={en:5,gu:3,hi:4,mr:2};const attempts=[];
  for(let i=0;i<20;i++){
   await page.locator('#study').waitFor({state:'visible'});
   const state=await context.request.get('http://127.0.0.1:8012/api/me').then(r=>r.json());const clip=state.current;
   assert.equal(state.participant.trials_completed,i);assert(await page.locator('#submit-rating').isDisabled());
   await page.locator('#play-audio').click();
   await page.locator('#rating-field:not([disabled])').waitFor({state:'visible',timeout:20000});
   assert.equal(await page.locator('#trial-error').innerText(),'');
   await page.locator(`label.score-${expected[clip.language]}`).click();
   if(i===2)await page.screenshot({path:ROOT+'/evidence/participant-rating.png',fullPage:true});
   const saved=page.waitForResponse(r=>r.url().endsWith('/api/rate')&&r.request().method()==='POST');
   await page.locator('#submit-rating').click();assert.equal((await saved).status(),200);
   attempts.push({clip:clip.id,language:clip.language,score:expected[clip.language],native_audio:true});
   if(i===3){await page.reload();await page.locator('#study').waitFor({state:'visible'});}
   console.log('Native playback and saved rating',i+1,'/20',clip.language);
  }
  await page.locator('#complete').waitFor({state:'visible'});await page.screenshot({path:ROOT+'/evidence/participant-complete.png',fullPage:true});
  const state=await context.request.get('http://127.0.0.1:8012/api/me').then(r=>r.json());assert.equal(state.participant.trials_completed,20);
  assert(Object.values(state.language_progress).every(n=>n===5));
  const admin=await browser.newContext({viewport:{width:1440,height:1050},reducedMotion:'reduce'});const a=await admin.newPage();a.on('pageerror',e=>errors.push(e.message));
  assert.equal((await admin.request.get('http://127.0.0.1:8012/api/admin/export/participants')).status(),401);
  await a.goto('http://127.0.0.1:8012/admin');
  const creds=fs.readFileSync(ROOT+'/.state/ADMIN_CREDENTIALS.txt','utf8');const password=creds.split('\n').find(x=>x.startsWith('Password: ')).slice(10);
  await a.locator('[name=username]').fill('mos_admin');await a.locator('[name=password]').fill(password);await a.locator('#admin-login-form button[type=submit]').click();await a.locator('#admin-dashboard').waitFor({state:'visible'});
  await a.locator('#subject-filter').selectOption(pid);await a.locator('#summary-cards').getByText('20 ratings in this view',{exact:true}).waitFor({state:'visible'});
  const report=await admin.request.get('http://127.0.0.1:8012/api/admin/dashboard?participant_id='+pid).then(r=>r.json());
  assert.equal(report.overall.mos,3.5);for(const row of report.languages){assert.equal(row.mos,expected[row.language]);assert.equal(row.n,5);}
  await a.screenshot({path:ROOT+'/evidence/admin-dashboard-qa.png',fullPage:true});
  await a.locator(`[data-person="${pid}"]`).click();await a.locator('#participant-dialog').waitFor({state:'visible'});assert.equal(await a.locator('#participant-details tbody tr').count(),20);
  await a.locator('#exclude-person').check();await a.locator('#exclusion-reason').fill('Automated QA fixture; isolated test database only.');await a.locator('#exclusion-form button[type=submit]').click();await a.locator('#participant-dialog').waitFor({state:'hidden'});
  const exported=await admin.request.get('http://127.0.0.1:8012/api/admin/export/participants');assert.equal(exported.status(),200);assert((await exported.text()).startsWith('\ufeffparticipant_id,name,email,age,gender,mother_tongue,organization,registered_iso,is_excluded,trials_completed'));
  const mobile=await browser.newContext({viewport:{width:390,height:844},reducedMotion:'reduce'});const m=await mobile.newPage();await m.goto('http://127.0.0.1:8012/');assert(await m.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));await m.screenshot({path:ROOT+'/evidence/mobile-registration.png',fullPage:true});
  await a.setViewportSize({width:390,height:844});await a.locator('#excluded-filter').check();await a.screenshot({path:ROOT+'/evidence/mobile-admin-qa.png',fullPage:true});assert(await a.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  assert.deepEqual(errors,[]);fs.writeFileSync(ROOT+'/evidence/browser-qa.json',JSON.stringify({database:'isolated .state/qa-data; not production',synthetic_participant:true,ratings:attempts,complete:true,per_language:expected,overall:3.5,resume_after_reload:true,admin_auth:true,exclusion:true,csv_schema:true,mobile_width:390,page_errors:errors},null,2));
  console.log('PASS 20 real audio playbacks, saved ratings, resume, language MOS, admin login, exclusion, CSV and mobile views.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
