const test = require('node:test');
const assert = require('node:assert/strict');
const {pathToFileURL} = require('node:url');
const path = require('node:path');

const load = () => import(pathToFileURL(path.join(__dirname, '../services/view-counter/worker.mjs')));
const origin = 'https://xiaoma2000.github.io';
const env = {GOATCOUNTER_SITE_CODE:'logscience-lab', GOATCOUNTER_API_TOKEN:'unit-test-only',
  GOATCOUNTER_START:'2026-11-01T00:00:00Z', ALLOWED_ORIGINS:origin};

function fixture() {
  let time = Date.parse('2026-11-01T13:30:00Z');
  const entries = new Map(), calls = [];
  const cache = {match:async key => entries.get(key)?.clone(),
    put:async(key,response) => entries.set(key,response.clone())};
  const deps = {cache, now:()=>time, fetch:async(url,options)=>{
    calls.push({url,options});
    return Response.json({total:6,total_events:0,total_utc:6,stats:[]});
  }};
  return {deps,calls,advance:ms=>time+=ms};
}
const req = (url='https://logscience-views.example.workers.dev/views', options={}) =>
  new Request(url,{headers:{Origin:origin},...options});

test('the production adapter preserves the receiver required by the Cloudflare global fetch function',async(t)=>{
  const {default:worker}=await load(),f=fixture();
  const previousFetch=globalThis.fetch,previousCaches=globalThis.caches;
  t.after(()=>{globalThis.fetch=previousFetch;globalThis.caches=previousCaches;});
  globalThis.caches={default:f.deps.cache};
  globalThis.fetch=function(input,options){
    if(this!==globalThis) throw new TypeError('Illegal invocation: function called with incorrect this reference');
    if(options.redirect==='error') throw new TypeError('Unsupported redirect mode: error');
    return Promise.resolve(Response.json({total:6,total_events:0,total_utc:6,stats:[]}));
  };
  const response=await worker.fetch(req(),env);
  assert.equal(response.status,200);
  assert.equal((await response.json()).count,6);
});

test('Worker reads all accumulated page views with server-side authentication and reveals only the aggregate',async()=>{
  const {serveViews}=await load(), f=fixture();
  const response=await serveViews(req(),env,f.deps), body=await response.json();
  assert.equal(response.status,200);
  assert.deepEqual(body,{count:6,updated_at:'2026-11-01T13:30:00.000Z'});
  const api=new URL(f.calls[0].url);
  assert.equal(api.origin,'https://logscience-lab.goatcounter.com');
  assert.equal(api.pathname,'/api/v0/stats/total');
  assert.equal(api.searchParams.get('start'),'2026-11-01T00:00:00Z');
  assert.equal(api.searchParams.has('end'),false,'use current time, never round down and drop this hour');
  assert.equal(f.calls[0].options.headers.Authorization,'Bearer unit-test-only');
  assert.equal(f.calls[0].options.redirect,'manual');
  assert.equal(response.headers.get('access-control-allow-origin'),origin);
  assert.equal(response.headers.get('cache-control'),'no-store');
  assert.doesNotMatch(JSON.stringify(body),/unit-test-only|stats|total_events/);
});

test('Worker refreshes a cached number after 30 seconds instead of the four-hour public counter',async()=>{
  const {serveViews}=await load(),f=fixture();
  await serveViews(req(),env,f.deps);
  f.advance(29000); await serveViews(req(),env,f.deps);
  assert.equal(f.calls.length,1);
  f.advance(1000); await serveViews(req(),env,f.deps);
  assert.equal(f.calls.length,2);
});

test('Worker rejects arbitrary proxy paths, query strings, unsafe methods and unapproved browser origins before querying',async()=>{
  const {serveViews}=await load();
  for(const [request,status] of [
    [req('https://logscience-views.example.workers.dev/other'),404],
    [req('https://logscience-views.example.workers.dev/views?url=https://evil.test'),400],
    [req(undefined,{method:'POST'}),405],
    [req(undefined,{headers:{Origin:'https://evil.test'}}),403],
    [req(undefined,{headers:{Origin:'null'}}),403],
  ]) {
    const f=fixture(),response=await serveViews(request,env,f.deps);
    assert.equal(response.status,status); assert.equal(f.calls.length,0);
  }
  const f=fixture(),preflight=await serveViews(req(undefined,{method:'OPTIONS'}),env,f.deps);
  assert.equal(preflight.status,204); assert.equal(f.calls.length,0);
});

test('Worker upstream errors or malformed counts never become zero or expose credentials',async()=>{
  const {serveViews}=await load();
  for(const fetch of [async()=>new Response('private upstream detail',{status:401}),
    async()=>Response.redirect('https://unapproved.example/credentials',302),
    async()=>Response.json({total:-1,total_events:0}),
    async()=>Response.json({total:6,total_events:7}),
    async()=>Response.json({total:6.5,total_events:0}),
    async()=>{throw Error('unit-test-only');}]) {
    const f=fixture(); f.deps.fetch=fetch;
    const response=await serveViews(req(),env,f.deps);
    assert.equal(response.status,503);
    assert.deepEqual(await response.json(),{error:'Counter temporarily unavailable'});
  }
});

test('authentication diagnostics report only the stage and HTTP status, never the upstream body or secret',async()=>{
  const {serveViews}=await load(),f=fixture(),reported=[];
  f.deps.report=event=>reported.push(event);
  f.deps.fetch=async()=>new Response('private token details',{status:401});
  const response=await serveViews(req(),env,f.deps);
  assert.equal(response.status,503);
  assert.deepEqual(reported,[{stage:'upstream',status:401}]);
});

test('runtime invocation errors produce a fixed safe diagnostic without the raw exception',async()=>{
  const {serveViews}=await load(),f=fixture(),reported=[];
  f.deps.report=event=>reported.push(event);
  f.deps.fetch=async()=>{throw new TypeError('Illegal invocation: function called with incorrect this reference');};
  await serveViews(req(),env,f.deps);
  assert.deepEqual(reported,[{stage:'upstream',reason:'illegal-invocation'}]);
});

test('request construction diagnostics classify unsafe header, redirect and runtime cache errors without raw text',async()=>{
  const {serveViews}=await load();
  for(const [message,reason] of [
    ['Invalid character in header value: private-token','invalid-header'],
    ['Unexpected redirect encountered','redirect'],
    ['Unsupported cache mode: no-store','unsupported-cache-option'],
  ]) {
    const f=fixture(),reported=[]; f.deps.report=event=>reported.push(event);
    f.deps.fetch=async()=>{throw new TypeError(message);};
    await serveViews(req(),env,f.deps);
    assert.deepEqual(reported,[{stage:'upstream',reason}]);
  }
});

test('Worker excludes events from page views and accepts a legitimate zero',async()=>{
  const {serveViews}=await load();
  for(const [total,events,expected] of [[9,3,6],[0,0,0]]) {
    const f=fixture(); f.deps.fetch=async()=>Response.json({total,total_events:events,total_utc:total,stats:[]});
    const response=await serveViews(req(),env,f.deps);
    assert.equal((await response.json()).count,expected);
  }
});

test('a transient edge-cache failure does not hide a valid upstream count',async()=>{
  const {serveViews}=await load();
  for(const method of ['match','put']) {
    const f=fixture(); f.deps.cache[method]=async()=>{throw Error('cache unavailable');};
    const response=await serveViews(req(),env,f.deps);
    assert.equal(response.status,200);
    assert.equal((await response.json()).count,6);
  }
});

test('Worker refuses missing or malformed configuration rather than requesting a different site',async()=>{
  const {serveViews}=await load();
  for(const update of [{GOATCOUNTER_API_TOKEN:''},{GOATCOUNTER_SITE_CODE:'https://evil.test'},
    {GOATCOUNTER_START:'not-a-date'},{GOATCOUNTER_START:'2026-12-01T00:00:00Z'},
    {ALLOWED_ORIGINS:'https://xiaoma2000.github.io.evil.test/path'}]) {
    const f=fixture(),response=await serveViews(req(),{...env,...update},f.deps);
    assert.equal(response.status,503); assert.equal(f.calls.length,0);
  }
});
