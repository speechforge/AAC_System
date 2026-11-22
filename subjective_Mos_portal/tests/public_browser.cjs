/* Live read/authentication checks. Does not create participant or rating records. */
const {chromium}=require('../../.runtime/browser/node_modules/playwright');
const fs=require('node:fs'),path=require('node:path'),assert=require('node:assert/strict');
const ROOT=path.resolve(__dirname,'..');
(async()=>{
 const url=JSON.parse(fs.readFileSync(ROOT+'/config/deployment.json','utf8')).public_url;
 const resolver=process.env.MOS_TEST_HOST_IP;
 const args=['--no-sandbox'];if(resolver)args.push(`--host-resolver-rules=MAP ${new URL(url).hostname} ${resolver}`);
 const browser=await chromium.launch({executablePath:'/usr/bin/google-chrome',headless:true,args});
 try{
  const context=await browser.newContext({viewport:{width:1440,height:1050},reducedMotion:'reduce'});
  const page=await context.newPage();const errors=[];page.on('pageerror',error=>errors.push(error.message));
  await page.goto(url,{waitUntil:'networkidle',timeout:60000});await page.locator('#registration-form').waitFor({state:'visible'});
  await page.screenshot({path:ROOT+'/evidence/public-listener-form.png',fullPage:true});
  await page.setViewportSize({width:320,height:700});assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth));
  await page.screenshot({path:ROOT+'/evidence/public-mobile-form.png',fullPage:true});
  await page.setViewportSize({width:1440,height:1050});await page.goto(url+'/admin');
  const password=fs.readFileSync(ROOT+'/.state/ADMIN_CREDENTIALS.txt','utf8').split('\n').find(x=>x.startsWith('Password: ')).slice(10);
  await page.locator('[name=username]').fill('mos_admin');await page.locator('[name=password]').fill(password);
  await page.locator('#admin-login-form button[type=submit]').click();await page.locator('#admin-dashboard').waitFor({state:'visible',timeout:30000});
  await page.locator('#summary-cards .summary-card').first().waitFor({state:'visible'});
  await page.screenshot({path:ROOT+'/evidence/public-admin-live.png',fullPage:true});
  const cookies=await context.cookies(url);assert(cookies.some(cookie=>cookie.name==='mos_admin'&&cookie.httpOnly&&cookie.secure));
  const downloaded=page.waitForEvent('download');await page.getByRole('link',{name:'Participants CSV ↓',exact:true}).click();
  const download=await downloaded;await download.saveAs(ROOT+'/.state/public-participants-check.csv');
  assert(fs.readFileSync(ROOT+'/.state/public-participants-check.csv','utf8').replace(/^\uFEFF/,'').startsWith('participant_id,name,email,age,gender,mother_tongue,organization,registered_iso,is_excluded,trials_completed'));
  await page.locator('#admin-logout').click();await page.locator('#admin-login').waitFor({state:'visible'});
  assert.deepEqual(errors,[]);
  fs.writeFileSync(ROOT+'/evidence/public-browser.json',JSON.stringify({url,normal_tls_verification:true,resolver_choice:resolver||'system resolver',listener_form:true,width_320_no_horizontal_overflow:true,admin_login:true,secure_http_only_cookie:true,csv_download:true,logout:true,created_test_participants:false,page_errors:errors},null,2));
  console.log('PASS public HTTPS listener form, 320px layout, real admin login, Secure HttpOnly cookie, CSV download and logout.');
 }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
