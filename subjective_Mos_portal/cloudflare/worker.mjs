/* HTTPS front door. Only the tunnel address lives in KV; study records remain local. */
async function validToken(provided, expected) {
  const encoder = new TextEncoder();
  const [left, right] = await Promise.all([
    crypto.subtle.digest('SHA-256', encoder.encode(provided)),
    crypto.subtle.digest('SHA-256', encoder.encode(expected)),
  ]);
  return crypto.subtle.timingSafeEqual(left, right);
}
function json(data,status=200) {return Response.json(data,{status,headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});}
export default {
  async fetch(request,env) {
    const publicURL = new URL(request.url);
    if (publicURL.protocol !== 'https:') {publicURL.protocol='https:';return Response.redirect(publicURL.toString(),308);}
    if (!['GET','HEAD','POST'].includes(request.method)) return json({detail:'Method not allowed.'},405);
    if (publicURL.pathname === '/__portal/origin') {
      if (request.method !== 'POST') return json({detail:'Not found.'},404);
      if (!await validToken(request.headers.get('Authorization') || '', 'Bearer '+env.ORIGIN_KEY)) return json({detail:'Unauthorized.'},401);
      if (Number(request.headers.get('content-length') || 0)>2048) return json({detail:'Request too large.'},413);
      try {
        const body=await request.json();
        if (typeof body.origin !== 'string' || !/^https:\/\/[a-z0-9-]+\.trycloudflare\.com$/.test(body.origin)) return json({detail:'Invalid tunnel origin.'},400);
        await env.ROUTING.put('origin',body.origin);
        return json({updated:true});
      } catch {return json({detail:'Invalid request.'},400);}
    }
    if (publicURL.pathname.startsWith('/.')) return json({detail:'Not found.'},404);
    try {
      const origin = await env.ROUTING.get('origin',{cacheTtl:60}) || env.INITIAL_ORIGIN;
      if (!/^https:\/\/[a-z0-9-]+\.trycloudflare\.com$/.test(origin)) throw new Error('Origin unavailable');
      const target=new URL(origin);
      target.pathname=publicURL.pathname; target.search=publicURL.search;
      const upstreamRequest=new Request(target.toString(),request);
      upstreamRequest.headers.delete('Host');
      upstreamRequest.headers.set('X-MOS-Origin-Key',env.ORIGIN_KEY);
      upstreamRequest.headers.set('X-MOS-Client-IP',request.headers.get('CF-Connecting-IP') || 'unknown');
      upstreamRequest.headers.set('X-Forwarded-Proto','https');
      upstreamRequest.headers.set('X-Forwarded-Host',publicURL.host);
      const upstream=await fetch(upstreamRequest,{redirect:'manual',cf:{cacheTtl:0,cacheEverything:false}});
      const response=new Response(upstream.body,upstream);
      const location=response.headers.get('Location');
      if (location) {
        const destination=new URL(location,origin);
        if(destination.origin===origin) response.headers.set('Location',publicURL.origin+destination.pathname+destination.search);
      }
      if(publicURL.pathname.startsWith('/api/'))response.headers.set('Cache-Control','no-store');
      response.headers.set('Referrer-Policy','no-referrer');
      response.headers.set('X-Content-Type-Options','nosniff');
      response.headers.set('X-Frame-Options','DENY');
      return response;
    } catch(error) {
      console.error(JSON.stringify({event:'portal_origin_unavailable',type:error?.name || 'Error'}));
      if(request.headers.get('Accept')?.includes('text/html')) return new Response('<!doctype html><html lang="en"><meta name="viewport" content="width=device-width"><title>Listening study temporarily unavailable</title><main><h1>The study is temporarily unavailable.</h1><p>Your saved responses remain on the research server. Please return shortly.</p><a href="/">Try again</a></main></html>',{status:503,headers:{'Content-Type':'text/html;charset=utf-8','Cache-Control':'no-store','Retry-After':'60'}});
      return json({detail:'The study server is temporarily unavailable. Saved responses are safe. Please try again shortly.'},503);
    }
  },
};
