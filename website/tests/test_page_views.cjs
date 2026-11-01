const test = require('node:test');
const assert = require('node:assert/strict');
const counter = require('../assets/js/lab-page-views.js');

function fixture(overrides = {}, address = 'https://xiaoma2000.github.io/LogScience.github.io/news/?lang=zh') {
  const values = {value:{textContent:''}, note:{textContent:''}};
  const element = {
    dataset: {enabled:'true', siteCode:'logscience-test', repositoryViews:'15',
      allowedHosts:'["xiaoma2000.github.io"]', basePath:'/LogScience.github.io', ...overrides},
    hidden:true, title:'', querySelector:s => s.includes('value') ? values.value : values.note,
  };
  const scripts = [], pixels = [], requests = [], timers = new Map();
  const events = {}, windowEvents = {}; let timerId=0;
  const doc = {title:'News · LogScience Lab', hidden:false, querySelector:()=>element,
    addEventListener:(name,fn)=>events[name]=fn,
    createElement:()=>({style:{},addEventListener(){},setAttribute(k,v){this[k]=v;}}),
    head:{appendChild:s=>scripts.push(s)},body:{appendChild:p=>pixels.push(p)}};
  const win = {location:new URL(address), AbortController,
    addEventListener:(name,fn)=>windowEvents[name]=fn,
    setTimeout:(fn,delay)=>{timers.set(++timerId,{fn,delay}); return timerId;},
    clearTimeout:id=>timers.delete(id), fetch:async(url, options)=>{
      requests.push({url,options}); return {ok:true,json:async()=>({count:'1,234'})};
    }};
  const poll=async()=>{
    const next=[...timers].find(([,value])=>value.delay===30000);
    assert.ok(next,'a 30-second read must be scheduled');
    timers.delete(next[0]); await next[1].fn();
  };
  return {element, values, doc, win, scripts, pixels, requests, timers, events, windowEvents,poll};
}

test('local preview shows 15 and makes no tracking or counter requests', async()=>{
  for (const host of ['localhost','127.0.0.1','[::1]']) {
    const f=fixture({},`http://${host}:4000/`);
    await counter.mount(f.doc,f.win);
    assert.equal(f.values.value.textContent,'15');
    assert.equal(f.element.hidden,false);
    assert.equal(f.scripts.length,0); assert.equal(f.pixels.length,0); assert.equal(f.requests.length,0);
    assert.match(f.values.note.textContent,/Local preview/);
  }
});

test('production adds the repository total once to the service website total', async()=>{
  const f=fixture(); await counter.mount(f.doc,f.win);
  assert.equal(f.values.value.textContent,'1,249');
  assert.equal(f.requests[0].url,'https://logscience-test.goatcounter.com/counter/TOTAL.json');
  assert.equal(f.requests[0].options.credentials,'omit');
  assert.equal(f.scripts.length,0,'no third-party script can collect extra page data');
  assert.equal(f.pixels.length,1);
  const hit=new URL(f.pixels[0].src);
  assert.equal(hit.origin,'https://logscience-test.goatcounter.com');
  assert.equal(hit.pathname,'/count');
  assert.equal(hit.searchParams.get('p'),'/news/');
  assert.equal(hit.searchParams.get('r'),'');
  assert.deepEqual([...hit.searchParams.keys()].sort(),['p','r','rnd','t']);
  assert.equal(hit.searchParams.has('q'),false,'the actual transmitted hit excludes location.search');
  assert.equal(f.pixels[0].referrerPolicy,'no-referrer');
});

test('tracking only runs on the enabled approved HTTPS host and project path', async()=>{
  for (const [config,url] of [
    [{enabled:'false'},'https://xiaoma2000.github.io/LogScience.github.io/'],
    [{siteCode:''},'https://xiaoma2000.github.io/LogScience.github.io/'],
    [{siteCode:'https://other.invalid'},'https://xiaoma2000.github.io/LogScience.github.io/'],
    [{},'https://yilouisliu.github.io/'],
    [{},'https://xiaoma2000.github.io/another-project/'],
    [{},'https://xiaoma2000.github.io/LogScience.github.io-copy/'],
    [{},'http://xiaoma2000.github.io/LogScience.github.io/'],
  ]) {
    const f=fixture(config,url); await counter.mount(f.doc,f.win);
    assert.equal(f.element.hidden,true); assert.equal(f.scripts.length,0); assert.equal(f.pixels.length,0); assert.equal(f.requests.length,0);
  }
});

test('zero website views retains the starting 15 without inventing new views', async()=>{
  const f=fixture(); f.win.fetch=async()=>({ok:true,json:async()=>({count:'0'})});
  await counter.mount(f.doc,f.win); assert.equal(f.values.value.textContent,'15');
});

test('counter errors never masquerade as zero or a successful live total', async()=>{
  for (const response of [()=>Promise.reject(Error('offline')),
    async()=>({ok:false}),async()=>({ok:true,json:async()=>({count:'<script>'})})]) {
    const f=fixture(); f.win.fetch=response; await counter.mount(f.doc,f.win);
    assert.equal(f.values.value.textContent,'—'); assert.match(f.values.note.textContent,/unavailable/i);
  }
});

test('mounting twice cannot double count the same page load', async()=>{
  const f=fixture(); await counter.mount(f.doc,f.win); await counter.mount(f.doc,f.win);
  assert.equal(f.pixels.length,1); assert.equal(f.requests.length,1);
});

test('invalid or overflowing totals are rejected',()=>{
  for(const value of [-1,1.5,'','1,2','NaN','<b>15</b>',Number.MAX_SAFE_INTEGER+1])
    assert.throws(()=>counter.parseCount(value));
  assert.throws(()=>counter.total(Number.MAX_SAFE_INTEGER,1));
});

const fastEndpoint='https://logscience-views.example.workers.dev/views';
test('a background-loaded page still completes the legacy one-time read when no Worker is configured',async()=>{
  const f=fixture(); f.doc.hidden=true;
  await counter.mount(f.doc,f.win);
  assert.equal(f.values.value.textContent,'1,249');
  assert.equal(f.element.dataset.state,'live');
  assert.equal(f.requests.length,1);
});

test('fast counter polls reads every 30 seconds without sending more page hits',async()=>{
  const f=fixture({counterEndpoint:fastEndpoint,refreshSeconds:'30'});
  let visits=6;
  f.win.fetch=async(url,options)=>{f.requests.push({url,options});return {ok:true,json:async()=>({count:visits++})};};
  await counter.mount(f.doc,f.win);
  assert.equal(f.values.value.textContent,'21');
  assert.equal(f.requests[0].url,fastEndpoint);
  assert.equal(f.requests[0].options.cache,'no-store');
  await f.poll(); assert.equal(f.values.value.textContent,'22');
  await f.poll(); assert.equal(f.values.value.textContent,'23');
  assert.equal(f.pixels.length,1,'reads must never inflate traffic');
});

test('fast counter suspends hidden pages and resumes reads after visibility or bfcache restoration',async()=>{
  const f=fixture({counterEndpoint:fastEndpoint}); await counter.mount(f.doc,f.win);
  f.doc.hidden=true; await f.events.visibilitychange();
  assert.equal(f.timers.size,0);
  f.doc.hidden=false; await f.events.visibilitychange();
  assert.equal(f.requests.length,2); assert.equal(f.pixels.length,1);
  await f.windowEvents.pagehide(); assert.equal(f.timers.size,0);
  await f.windowEvents.pageshow();
  assert.equal(f.requests.length,3); assert.equal(f.pixels.length,1);
});

test('fast counter preserves confirmed views during errors or an older lower response',async()=>{
  const f=fixture({counterEndpoint:fastEndpoint});
  f.win.fetch=async()=>({ok:true,json:async()=>({count:6})}); await counter.mount(f.doc,f.win);
  f.win.fetch=async()=>{throw Error('offline');}; await f.poll();
  assert.equal(f.values.value.textContent,'21'); assert.equal(f.element.dataset.state,'stale');
  f.win.fetch=async()=>({ok:true,json:async()=>({count:0})}); await f.poll();
  assert.equal(f.values.value.textContent,'21');
});

test('first fast-read failure can show the existing public counter then recover without losing views',async()=>{
  const f=fixture({counterEndpoint:fastEndpoint});
  f.win.fetch=async(url)=>{
    f.requests.push({url});
    if(url===fastEndpoint) throw Error('not ready');
    return {ok:true,json:async()=>({count:'6'})};
  };
  await counter.mount(f.doc,f.win);
  assert.equal(f.values.value.textContent,'21'); assert.equal(f.element.dataset.state,'delayed');
  f.win.fetch=async()=>({ok:true,json:async()=>({count:8})}); await f.poll();
  assert.equal(f.values.value.textContent,'23'); assert.equal(f.element.dataset.state,'live');
});

test('fast configuration never permits localhost traffic or unsafe read endpoints',async()=>{
  const local=fixture({counterEndpoint:fastEndpoint},'http://localhost:4000/');
  await counter.mount(local.doc,local.win);
  assert.equal(local.requests.length,0);assert.equal(local.timers.size,0);
  for(const endpoint of ['http://worker.workers.dev/views','https://evil.test/views',
    'https://worker.workers.dev/views?token=secret','https://user:secret@worker.workers.dev/views']) {
    const f=fixture({counterEndpoint:endpoint}); await counter.mount(f.doc,f.win);
    assert.equal(f.requests.length,0);assert.equal(f.pixels.length,0);
  }
});

const snapshotPath='/LogScience.github.io/metrics/page-views.json';
const confirmed={counterEndpoint:fastEndpoint,snapshotUrl:snapshotPath,
  websiteViews:'24',websiteUpdatedAt:'2026-11-01T14:15:48.963Z'};
function snapshot(repository=17,website=26) {
  return {schema:1,site_code:'logscience-test',repository_views:repository,website_views:website,
    total:repository+website,website_updated_at:'2026-11-01T14:20:00Z',updated_at:'2026-11-01T14:21:00Z'};
}

test('TLS failure reads confirmed same-origin data instead of the old public zero',async()=>{
  const f=fixture(confirmed);
  f.win.fetch=async(url)=>{
    f.requests.push({url});
    if(url===fastEndpoint) throw Error('ERR_CERT_COMMON_NAME_INVALID');
    assert.equal(new URL(url).pathname,snapshotPath);
    return {ok:true,json:async()=>snapshot()};
  };
  await counter.mount(f.doc,f.win);
  assert.equal(f.values.value.textContent,'43');
  assert.equal(f.element.dataset.state,'cached');
  assert.match(f.element.title,/hourly|last confirmed/i);
  assert.equal(f.pixels.length,1);
});

test('all network failures preserve the verified initial total, never revert to repository-only 15',async()=>{
  const f=fixture(confirmed);
  f.win.fetch=async()=>{throw Error('offline');};
  await counter.mount(f.doc,f.win);
  assert.equal(f.values.value.textContent,'39');
  assert.equal(f.element.dataset.state,'cached');
  await f.poll(); assert.equal(f.values.value.textContent,'39');
});

test('initially hidden fast pages finish their first read without waiting for a visibility event',async()=>{
  const f=fixture(confirmed); f.doc.hidden=true;
  f.win.fetch=async(url)=>{f.requests.push({url});return {ok:true,json:async()=>
    url===fastEndpoint ? {count:27} : snapshot()};};
  await counter.mount(f.doc,f.win);
  assert.equal(f.values.value.textContent,'44');
  assert.equal(f.element.dataset.state,'live');
  assert.equal(f.requests.length,2); assert.equal(f.timers.size,0);
  f.doc.hidden=false; await f.events.visibilitychange();
  assert.equal(f.pixels.length,1);
});

test('an ignored abort signal cannot strand initial loading or block later polling',async()=>{
  const f=fixture(confirmed);
  f.win.fetch=async(url)=> url===fastEndpoint ? new Promise(()=>{}) : {ok:true,json:async()=>snapshot()};
  const mounting=counter.mount(f.doc,f.win);
  // Let the reachable snapshot settle while the fast read remains pending.
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(f.values.value.textContent,'43');
  const timeout=[...f.timers].find(([,timer])=>timer.delay===6000);
  assert.ok(timeout); timeout[1].fn();
  await mounting;
  assert.equal(f.element.dataset.state,'cached');
  assert.ok([...f.timers.values()].some(t=>t.delay===30000));
});

test('a blocked tracking pixel cannot prevent a confirmed count from being displayed',async()=>{
  const f=fixture(confirmed); f.doc.body.appendChild=()=>{throw Error('blocked');};
  f.win.fetch=async(url)=>({ok:true,json:async()=>url===fastEndpoint ? {count:27} : snapshot()});
  await counter.mount(f.doc,f.win);
  assert.equal(f.values.value.textContent,'44');
  assert.equal(f.element.dataset.state,'live');
});

test('a slower older snapshot cannot replace a live result or subtract known views',async()=>{
  const f=fixture(confirmed); let finishSnapshot;
  f.win.fetch=async(url)=>url===fastEndpoint ? {ok:true,json:async()=>({count:29})} :
    new Promise(resolve=>{finishSnapshot=resolve;});
  const mounting=counter.mount(f.doc,f.win);
  await new Promise(resolve=>setImmediate(resolve));
  assert.equal(f.values.value.textContent,'44');
  finishSnapshot({ok:true,json:async()=>snapshot(17,20)});
  await mounting;
  assert.equal(f.values.value.textContent,'46');
  assert.equal(f.element.dataset.state,'live');
});

test('foreign, malformed or cross-origin snapshots cannot replace the confirmed seed',async()=>{
  for(const bad of [{...snapshot(),site_code:'another-site'},{...snapshot(),total:999},
    {...snapshot(),website_views:-1}]) {
    const f=fixture(confirmed);
    f.win.fetch=async(url)=>{if(url===fastEndpoint) throw Error('offline');return {ok:true,json:async()=>bad};};
    await counter.mount(f.doc,f.win);
    assert.equal(f.values.value.textContent,'39');
  }
  const f=fixture({...confirmed,snapshotUrl:'https://evil.test/metrics/page-views.json'});
  await counter.mount(f.doc,f.win);
  assert.equal(f.requests.length,0); assert.equal(f.pixels.length,0);
});

test('a retained higher Worker value keeps its actual confirmation time on later failure',async()=>{
  const f=fixture(confirmed);
  f.win.fetch=async(url)=>({ok:true,json:async()=>url===fastEndpoint ?
    {count:29,updated_at:'2026-11-01T14:40:00Z'} : snapshot(15,24)});
  await counter.mount(f.doc,f.win);
  f.win.fetch=async(url)=>{if(url===fastEndpoint) throw Error('offline');
    return {ok:true,json:async()=>snapshot(15,24)};};
  await f.poll();
  assert.equal(f.values.value.textContent,'44');
  assert.match(f.element.title,/2026-11-01T14:40:00Z/);
  assert.doesNotMatch(f.element.title,/2026-11-01T14:15:48/);
});
