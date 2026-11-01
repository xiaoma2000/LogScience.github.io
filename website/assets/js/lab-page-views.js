(function (factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else factory().mount(document, window);
})(function () {
  'use strict';

  function parseCount(value) {
    if (typeof value === 'string') {
      value = value.trim();
      if (!/^(?:\d+|\d{1,3}(?:,\d{3})+)$/.test(value)) throw Error('Invalid view count');
      value = Number(value.replace(/,/g, ''));
    }
    if (!Number.isSafeInteger(value) || value < 0) throw Error('Invalid view count');
    return value;
  }

  function total(repository, website) {
    return parseCount(parseCount(repository) + parseCount(website));
  }

  function plan(data, location) {
    const repository = parseCount(data.repositoryViews);
    const local = ['localhost', '127.0.0.1', '[::1]', '::1'].includes(location.hostname);
    if (local) return {mode:'preview', repository};
    const hosts = JSON.parse(data.allowedHosts || '[]');
    const base = (data.basePath || '').replace(/\/$/, '');
    const inside = !base || location.pathname === base || location.pathname.startsWith(base + '/');
    if (data.enabled !== 'true' || location.protocol !== 'https:' || location.port ||
        !Array.isArray(hosts) || !hosts.includes(location.hostname) || !inside ||
        !/^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$/.test(data.siteCode || '')) return {mode:'disabled'};
    let endpoint = data.counterEndpoint || '';
    if (endpoint) {
      const url = new URL(endpoint);
      if (url.protocol !== 'https:' || !url.hostname.endsWith('.workers.dev') ||
          url.port || url.username || url.password || url.pathname !== '/views' ||
          url.search || url.hash) throw Error('Invalid counter endpoint');
      endpoint = url.href;
    }
    let snapshot = '';
    if (data.snapshotUrl) {
      const url = new URL(data.snapshotUrl,location.href);
      if (url.origin !== location.origin || url.pathname !== base + '/metrics/page-views.json' ||
          url.username || url.password || url.search || url.hash) throw Error('Invalid snapshot endpoint');
      snapshot = url.href;
    }
    const website = data.websiteViews === undefined ? null : parseCount(data.websiteViews);
    return {mode:'live', repository, origin:'https://' + data.siteCode + '.goatcounter.com',
      endpoint, snapshot, website, siteCode:data.siteCode, websiteUpdatedAt:data.websiteUpdatedAt || '',
      refreshMs:Math.max(30,Number(data.refreshSeconds) || 30) * 1000,
      path:location.pathname.slice(base.length) || '/'};
  }

  async function mount(doc, win) {
    const element = doc.querySelector('[data-page-views]');
    if (!element || element.dataset.pageViewsMounted) return;
    element.dataset.pageViewsMounted = 'true';
    const value = element.querySelector('[data-page-views-value]');
    const note = element.querySelector('[data-page-views-note]');
    let config;
    try { config = plan(element.dataset, win.location); }
    catch (_) { return; }
    if (config.mode === 'disabled') return;
    element.hidden = false;
    if (config.mode === 'preview') {
      value.textContent = config.repository.toLocaleString('en-US');
      note.textContent = 'Local preview: starting total only. Local browsing is not recorded. ' + note.textContent;
      element.title = note.textContent;
      element.dataset.state = 'preview';
      return;
    }

    const originalNote = note.textContent;
    let lastWebsite = config.website, repository = config.repository;
    let sourceTime = config.websiteUpdatedAt, reading = false, pollTimer, suspended = false;
    function display(state) {
      value.textContent = total(repository,lastWebsite).toLocaleString('en-US');
      element.dataset.state = state;
      note.textContent = originalNote;
      element.title = originalNote + (state === 'live' && config.endpoint ?
        ' Website views are checked about every 30 seconds while this page is visible.' :
        config.snapshot ? ' Showing the last confirmed total. The website backup is published hourly.' +
          (sourceTime ? ' Website count confirmed at ' + sourceTime + '.' : '') :
          ' Counter updates can be delayed by caching.');
    }
    function accept(website,repo,stamp) {
      website = parseCount(website);
      const nextWebsite = Math.max(lastWebsite === null ? 0 : lastWebsite,website);
      const nextRepository = Math.max(repository,parseCount(repo));
      total(nextRepository,nextWebsite);
      const validStamp = typeof stamp === 'string' &&
        /^20\d\d-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d{1,6})?Z$/.test(stamp) && Number.isFinite(Date.parse(stamp));
      if (lastWebsite === null || website > lastWebsite) sourceTime = validStamp ? stamp : '';
      else if (website === lastWebsite && validStamp &&
               (!sourceTime || Date.parse(stamp) > Date.parse(sourceTime))) sourceTime = stamp;
      lastWebsite = nextWebsite;
      repository = nextRepository;
    }
    if (lastWebsite !== null) display('cached');
    else { value.textContent = '…'; element.dataset.state = 'loading'; }
    // GoatCounter's documented pixel API keeps the transmitted fields explicit.
    // Per-load counting is configured in the account (Sessions disabled).
    try {
    const tracker = doc.createElement('img');
    tracker.width = 1;
    tracker.height = 1;
    tracker.alt = '';
    tracker.setAttribute('aria-hidden','true');
    tracker.referrerPolicy = 'no-referrer';
    tracker.style.position = 'absolute';
    tracker.style.opacity = '0';
    tracker.style.pointerEvents = 'none';
    const params = new URLSearchParams({p:config.path,t:doc.title || '',r:'',
      rnd:Math.random().toString(36).slice(2)});
    if (win.navigator && win.navigator.webdriver) params.set('b','153');
    tracker.src = config.origin + '/count?' + params;
    const remove = () => { if (tracker.parentNode) tracker.parentNode.removeChild(tracker); };
    tracker.addEventListener('load',remove,{once:true});
    tracker.addEventListener('error',remove,{once:true});
    doc.body.appendChild(tracker);
    } catch (_) { /* Recording blocked by a browser must not block the visible count. */ }

    async function read(endpoint) {
      const controller = win.AbortController ? new win.AbortController() : null;
      let timer;
      const timeout = new Promise((resolve,reject)=>{
        timer = win.setTimeout(()=>{
          reject(Error('Counter timed out'));
          if (controller) controller.abort();
        },6000);
      });
      try {
        const request = (async()=>{
          const response = await win.fetch(endpoint,{
            credentials:'omit',referrerPolicy:'no-referrer',cache:'no-store',
            signal:controller ? controller.signal : undefined,
          });
          if (!response.ok) throw Error('Counter unavailable');
          return response.json();
        })();
        return await Promise.race([request,timeout]);
      } finally { win.clearTimeout(timer); }
    }
    function acceptSnapshot(data) {
      if (data.schema !== 1 || data.site_code !== config.siteCode ||
          total(data.repository_views,data.website_views) !== parseCount(data.total) ||
          !Number.isFinite(Date.parse(data.website_updated_at))) throw Error('Invalid view snapshot');
      accept(data.website_views,data.repository_views,data.website_updated_at);
    }
    async function refresh(initial) {
      if (reading || suspended || (!initial && config.endpoint && doc.hidden)) return;
      reading = true;
      win.clearTimeout(pollTimer);
      let live = false;
      try {
        const fast = (async()=>{
          try {
            const data = await read(config.endpoint || config.origin + '/counter/TOTAL.json');
            accept(data.count,repository,data.updated_at);
            live = true;
            display('live');
          } catch (_) {
            // Legacy markup keeps its public-counter fallback; current pages use
            // their own verified snapshot instead of GoatCounter's four-hour cache.
            if (config.snapshot || lastWebsite !== null || !config.endpoint) return;
            try {
              accept((await read(config.origin + '/counter/TOTAL.json')).count,repository);
              display('delayed');
            } catch (_) { /* Retain confirmed values if both legacy reads fail. */ }
          }
        })();
        const cached = config.snapshot ? (async()=>{
          try {
            acceptSnapshot(await read(config.snapshot));
            display(live ? 'live' : 'cached');
          } catch (_) { /* The built-in confirmed count remains usable offline. */ }
        })() : Promise.resolve();
        await Promise.all([fast,cached]);
        if (!live && lastWebsite !== null && config.snapshot) display('cached');
        else if (!live && lastWebsite !== null && element.dataset.state !== 'delayed') {
          display('stale');
          element.title = originalNote + ' Showing the last available total; retrying shortly.';
        } else if (lastWebsite === null) {
          value.textContent = '—';
          element.dataset.state = 'unavailable';
          note.textContent = 'The view count is temporarily unavailable. ' + originalNote;
          element.title = note.textContent;
        }
      } finally {
        reading = false;
        if (config.endpoint && !suspended && !doc.hidden) {
          pollTimer = win.setTimeout(()=>refresh(false),config.refreshMs);
        }
      }
    }
    if (config.endpoint) {
      doc.addEventListener('visibilitychange',()=>{
        win.clearTimeout(pollTimer);
        if (!doc.hidden) return refresh();
      });
      win.addEventListener('pagehide',()=>{suspended=true;win.clearTimeout(pollTimer);});
      win.addEventListener('pageshow',()=>{suspended=false;return refresh();});
    }
    await refresh(true);
  }

  return {parseCount, total, plan, mount};
});
