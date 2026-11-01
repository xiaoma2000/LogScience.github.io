// Aggregate-only reader. GOATCOUNTER_API_TOKEN is a Cloudflare secret, never a source file.
const CACHE_MS = 30_000;
const pending = new Map();

function integer(value) {
  if (!Number.isSafeInteger(value) || value < 0) throw Error('Invalid count');
  return value;
}

function config(env, now) {
  const site = env.GOATCOUNTER_SITE_CODE || '';
  const start = env.GOATCOUNTER_START || '';
  const origins = (env.ALLOWED_ORIGINS || '').split(',').map(s=>s.trim()).filter(Boolean);
  if (!/^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(site) ||
      !env.GOATCOUNTER_API_TOKEN?.trim() ||
      !/^\d{4}-\d{2}-\d{2}T\d{2}:00:00Z$/.test(start) ||
      !Number.isFinite(Date.parse(start)) || Date.parse(start) > now || !origins.length ||
      origins.some(s=>{const u=new URL(s); return u.protocol!=='https:' || u.origin!==s;})) {
    throw Error('Invalid configuration');
  }
  return {site,start,origins};
}

function reply(body, status, origin) {
  const headers = {'Content-Type':'application/json; charset=utf-8',
    'Cache-Control':'no-store', 'X-Content-Type-Options':'nosniff', 'Vary':'Origin'};
  if (origin) headers['Access-Control-Allow-Origin'] = origin;
  return new Response(body === null ? null : JSON.stringify(body),{status,headers});
}

export async function serveViews(request, env, deps) {
  const now = (deps.now || Date.now)();
  let settings;
  try { settings = config(env,now); }
  catch (_) {
    deps.report?.({stage:'configuration'});
    return reply({error:'Counter temporarily unavailable'},503);
  }
  const url = new URL(request.url), origin = request.headers.get('Origin');
  if (origin && !settings.origins.includes(origin)) return reply({error:'Origin not allowed'},403);
  if (url.pathname !== '/views') return reply({error:'Not found'},404,origin);
  if (url.search) return reply({error:'Query parameters are not supported'},400,origin);
  if (!['GET','OPTIONS'].includes(request.method)) return reply({error:'Method not allowed'},405,origin);
  if (request.method === 'OPTIONS') {
    const response = reply(null,204,origin);
    response.headers.set('Access-Control-Allow-Methods','GET, OPTIONS');
    response.headers.set('Access-Control-Max-Age','300');
    return response;
  }

  const key = new URL('/views',url);
  key.search = new URLSearchParams({site:settings.site,start:settings.start}).toString();
  const cacheKey = key.toString();
  let diagnostic = {stage:'read'};
  try {
    try {
      const cached = await deps.cache.match(cacheKey);
      if (cached) {
        const payload = await cached.json();
        const age = now - Date.parse(payload.updated_at);
        integer(payload.count);
        if (age >= 0 && age < CACHE_MS) return reply(payload,200,origin);
      }
    } catch (_) { /* Cache outages are misses, not missing statistics. */ }

    // Coalesce concurrent misses within an isolate; the edge cache handles subsequent readers.
    if (!pending.has(cacheKey)) {
      const reading = (async()=>{
        const api = new URL(`https://${settings.site}.goatcounter.com/api/v0/stats/total`);
        api.searchParams.set('start',settings.start);
        diagnostic = {stage:'upstream'};
        // Leave end at the API default, which includes the current incomplete day/hour.
        const response = await deps.fetch(api.toString(),{
          headers:{Authorization:`Bearer ${env.GOATCOUNTER_API_TOKEN}`,
            'Content-Type':'application/json',Accept:'application/json'},
          // Workers supports manual/follow, not the standard error mode.
          // A 3xx is rejected below, without forwarding credentials anywhere else.
          redirect:'manual',cache:'no-store',signal:AbortSignal.timeout(5000),
        });
        if (!response.ok) {
          diagnostic.status = response.status;
          throw Error('Upstream unavailable');
        }
        diagnostic = {stage:'upstream-payload'};
        const data = await response.json();
        const count = integer(integer(data.total) - integer(data.total_events));
        const payload = {count,updated_at:new Date((deps.now || Date.now)()).toISOString()};
        try {
          await deps.cache.put(cacheKey,new Response(JSON.stringify(payload),{
            headers:{'Content-Type':'application/json','Cache-Control':'public, max-age=30'},
          }));
        } catch (_) { /* A valid upstream count remains usable without edge caching. */ }
        return payload;
      })();
      pending.set(cacheKey,reading);
      reading.finally(()=>pending.delete(cacheKey)).catch(()=>{});
    }
    return reply(await pending.get(cacheKey),200,origin);
  } catch (error) {
    // Deliberately do not return upstream messages, credentials, or fabricated zeroes.
    if (diagnostic.stage === 'upstream' && !diagnostic.status) {
      const message = String(error?.message || '');
      diagnostic.reason = message.includes('Illegal invocation') ? 'illegal-invocation' :
        /cache/i.test(message) && /not implemented|unsupported/i.test(message) ? 'unsupported-cache-option' :
        /header|ByteString|character/i.test(message) ? 'invalid-header' :
        /redirect/i.test(message) ? 'redirect' :
        error?.name === 'AbortError' || error?.name === 'TimeoutError' ? 'timeout' : 'network';
    }
    deps.report?.(diagnostic);
    return reply({error:'Counter temporarily unavailable'},503,origin);
  }
}

export default {
  fetch(request,env) {
    return serveViews(request,env,{fetch:(input,init)=>globalThis.fetch(input,init),cache:caches.default,
      report:event=>console.warn('View counter unavailable',event)});
  },
};
