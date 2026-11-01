(function () {
  'use strict';
  document.documentElement.classList.add('js-ready');
  const menu=document.querySelector('[data-menu-button]'), nav=document.querySelector('#primary-nav');
  if(menu&&nav){
    menu.hidden=false;
    const close=()=>{menu.setAttribute('aria-expanded','false');nav.classList.remove('is-open');menu.querySelector('.sr-only').textContent='Open navigation';};
    menu.addEventListener('click',()=>{const open=menu.getAttribute('aria-expanded')!=='true';menu.setAttribute('aria-expanded',String(open));nav.classList.toggle('is-open',open);menu.querySelector('.sr-only').textContent=open?'Close navigation':'Open navigation';});
    document.addEventListener('keydown',e=>{if(e.key==='Escape'&&menu.getAttribute('aria-expanded')==='true'){close();menu.focus();}});
    document.addEventListener('click',e=>{if(!e.target.closest('.site-header'))close();});
    nav.addEventListener('click',e=>{if(e.target.closest('a'))close();});
    window.matchMedia('(max-width: 1100px)').addEventListener('change',close);
  }
  if(!window.LabState)return;
  const S=window.LabState;
  const news=document.querySelector('[data-news]');
  if(news){
    const records=[...news.querySelectorAll('[data-news-item]')].map(el=>({el,category:el.dataset.category,searchText:el.textContent}));
    const controls=news.querySelector('[data-news-controls]'), form=news.querySelector('[data-news-search]'), input=form.querySelector('input'), status=news.querySelector('[data-news-status]'), pagination=news.querySelector('[data-news-pagination]'), empty=news.querySelector('[data-news-empty]');
    let state=S.parse(location.search);
    const labels={en:{all:'All',research:'Research',recognition:'Recognition',fieldwork:'Fieldwork',opportunities:'Opportunities',community:'Community'},zh:{all:'全部',research:'研究成果',recognition:'荣誉与项目',fieldwork:'野外科考',opportunities:'招聘',community:'学术与团队'}};
    const button=(text,page,disabled,current)=>{const el=document.createElement(disabled?'span':'a');el.textContent=text;if(!disabled){const next={...state,page};el.href=location.pathname+S.query(next,location.search)+location.hash;el.dataset.newsPage=String(page);if(current)el.setAttribute('aria-current','page');}else el.setAttribute('aria-disabled','true');return el;};
    function update(mode,move){
      const result=S.select(records,state,10);state.page=result.page;
      const visible=new Set(result.items),zh=state.lang==='zh';
      records.forEach(record=>{
        record.el.hidden=!visible.has(record);
        record.el.querySelectorAll('[data-lang-text]').forEach(el=>el.hidden=el.dataset.langText!==state.lang);
        record.el.querySelector('[data-news-link]').setAttribute('aria-labelledby',record.el.dataset.newsId+'-'+state.lang);
        record.el.querySelector('[data-card-category]').textContent=labels[state.lang][record.category]||labels[state.lang].community;
        record.el.querySelector('[data-source-label]').textContent=record.el.dataset.internalStory ? (zh?'阅读完整报道':'Read the full story') : (zh?'在新标签页阅读原文':'Read the original article in a new tab');
      });
      input.value=state.q;input.placeholder=zh?'搜索中文或英文新闻':'Search news in English or Chinese';input.setAttribute('aria-label',zh?'搜索新闻':'Search news');
      news.querySelector('[data-search-label]').textContent=zh?'搜索':'Search';
      news.querySelectorAll('[data-category]').forEach(el=>{if(el.tagName==='BUTTON'){el.setAttribute('aria-pressed',String(el.dataset.category===state.category));el.textContent=labels[state.lang][el.dataset.category];}});
      news.querySelectorAll('[data-news-language]').forEach(el=>el.setAttribute('aria-pressed',String(el.dataset.newsLanguage===state.lang)));
      status.textContent=zh?'共 '+result.total+' 条新闻 · 第 '+result.page+' / '+result.pages+' 页':result.total+' '+(result.total===1?'article':'articles')+' · Page '+result.page+' of '+result.pages;
      empty.hidden=result.total!==0;news.querySelector('[data-empty-title]').textContent=zh?'没有找到相关新闻':'No matching articles';news.querySelector('[data-empty-description]').textContent=zh?'请尝试其他关键词或分类。':'Try a different search or category.';news.querySelector('[data-news-clear]').textContent=zh?'清除筛选':'Clear filters';
      pagination.textContent='';pagination.hidden=result.pages<=1;
      if(result.pages>1){pagination.append(button(zh?'上一页':'Previous',result.page-1,result.page===1,false));for(let p=1;p<=result.pages;p++)pagination.append(button(String(p),p,false,p===result.page));pagination.append(button(zh?'下一页':'Next',result.page+1,result.page===result.pages,false));}
      if(mode){const next=location.pathname+S.query(state,location.search)+location.hash;if(next!==location.pathname+location.search+location.hash)history[mode+'State'](null,'',next);}
      if(move){news.querySelector('[data-news-start]').focus({preventScroll:true});window.scrollTo({top:Math.max(0,news.getBoundingClientRect().top+scrollY-115),behavior:'auto'});}
    }
    controls.hidden=false;update('replace',false);
    form.addEventListener('submit',e=>{e.preventDefault();state.q=input.value.trim().slice(0,160);state.page=1;update('push',false);});
    input.addEventListener('search',()=>{if(!input.value){state.q='';state.page=1;update('push',false);}});
    news.querySelectorAll('button[data-category]').forEach(el=>el.addEventListener('click',()=>{state.category=el.dataset.category;state.page=1;update('push',false);}));
    news.querySelectorAll('[data-news-language]').forEach(el=>el.addEventListener('click',()=>{state.lang=el.dataset.newsLanguage;update('push',false);}));
    news.querySelector('[data-news-clear]').addEventListener('click',()=>{state={...state,page:1,q:'',category:'all'};update('push',false);input.focus();});
    pagination.addEventListener('click',e=>{const a=e.target.closest('a[data-news-page]');if(!a||e.button!==0||e.metaKey||e.ctrlKey||e.shiftKey||e.altKey)return;e.preventDefault();state.page=Number(a.dataset.newsPage);update('push',true);});
    window.addEventListener('popstate',()=>{state=S.parse(location.search);update('replace',false);});
  }
  const publications=document.querySelector('[data-publications]');
  if(publications){
    const form=publications.querySelector('[data-pub-search]'),input=form.querySelector('input'),records=[...publications.querySelectorAll('[data-pub-item]')],status=publications.querySelector('[data-pub-status]');
    function render(){const q=S.normalize(new URLSearchParams(location.search).get('q')||'');input.value=new URLSearchParams(location.search).get('q')||'';let count=0;const words=q.split(/\s+/).filter(Boolean);records.forEach(el=>{el.hidden=!words.every(w=>S.normalize(el.textContent+' '+(el.dataset.pubNames||'')).includes(w));if(!el.hidden)count++;});publications.querySelectorAll('[data-pub-year]').forEach(section=>{section.hidden=![...section.querySelectorAll('[data-pub-item]')].some(el=>!el.hidden);const link=publications.querySelector('[data-year-link="'+section.dataset.pubYear+'"]');if(link)link.hidden=section.hidden;});publications.querySelector('[data-pub-empty]').hidden=count!==0;status.textContent=count+' '+(count===1?'publication':'publications')+(q?' matching your search':' in the group collection');}
    function search(value){const p=new URLSearchParams(location.search);if(value)p.set('q',value);else p.delete('q');const next=location.pathname+(p.toString()?'?'+p.toString():'')+location.hash;if(next!==location.pathname+location.search+location.hash)history.pushState(null,'',next);render();}
    form.hidden=false;render();form.addEventListener('submit',e=>{e.preventDefault();search(input.value.trim().slice(0,160));});input.addEventListener('search',()=>{if(!input.value)search('');});publications.querySelector('[data-pub-clear]').addEventListener('click',()=>{search('');input.focus();});window.addEventListener('popstate',render);
  }
})();
