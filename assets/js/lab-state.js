(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else root.LabState = factory();
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  const categories = ['all','research','recognition','fieldwork','opportunities','community'];
  function normalize(value) { return String(value || '').normalize('NFKD').toLowerCase().replace(/[\u0300-\u036f]/g, '').trim(); }
  function parse(search) {
    const p=new URLSearchParams(search), raw=p.get('page')||'1', n=/^\d+$/.test(raw)?Number(raw):1;
    return {page:Number.isSafeInteger(n)?Math.max(1,n):1, category:categories.includes(p.get('category'))?p.get('category'):'all', lang:p.get('lang')==='zh'?'zh':'en', q:(p.get('q')||'').trim().slice(0,160)};
  }
  function select(items, state, size) {
    const words=normalize(state.q).split(/\s+/).filter(Boolean);
    const filtered=items.filter(x=>(state.category==='all'||x.category===state.category)&&words.every(w=>normalize(x.searchText).includes(w)));
    const pages=Math.max(1,Math.ceil(filtered.length/size)), page=Math.min(pages,Math.max(1,state.page||1));
    return {items:filtered.slice((page-1)*size,page*size),total:filtered.length,pages,page};
  }
  function query(state, current) {
    const p=new URLSearchParams(current||'');
    for(const [key,value,empty] of [['page',String(state.page),'1'],['category',state.category,'all'],['lang',state.lang,'en'],['q',state.q,'']]) {
      if(value===empty)p.delete(key);else p.set(key,value);
    }
    return p.toString()?'?'+p.toString():'';
  }
  return {normalize,parse,select,query};
});
