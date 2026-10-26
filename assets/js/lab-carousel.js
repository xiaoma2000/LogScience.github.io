(function (root, factory) {
  if (typeof module === 'object' && module.exports) module.exports = factory();
  else factory().mount(document);
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';
  class CarouselPolicy {
    constructor(count, reducedMotion=false, {autoplay=false}={}) {
      this.count=Math.max(0,Number(count)||0); this.index=0; this.autoplay=autoplay; this.paused=reducedMotion&&!autoplay;
      this.flags={pageHidden:false,offscreen:false,hover:false,focus:false};
    }
    get playing() { return this.count>1 && !this.paused && !Object.values(this.flags).some(Boolean); }
    set(flag,value) { this.flags[flag]=Boolean(value); }
    pause() { this.paused=true; }
    play() { this.paused=false; }
    reduceMotion(value) { if(value&&!this.autoplay)this.pause(); }
    move(delta) { this.index=this.count ? (this.index+delta+this.count)%this.count : 0; return this.index; }
    next() { if(!this.autoplay)this.pause(); return this.move(1); }
    previous() { if(!this.autoplay)this.pause(); return this.move(-1); }
    goTo(index) { if(Number.isInteger(index)&&index>=0&&index<this.count)this.index=index; if(!this.autoplay)this.pause(); return this.index; }
    tick() { return this.playing ? this.move(1) : this.index; }
  }
  function updateSlides(slides,index,fade=false) {
    slides.forEach((slide,i)=>{
      const active=i===index;
      slide.hidden=!active&&!fade;
      slide.classList.toggle('is-current',active);
      slide.setAttribute('aria-hidden',String(!active));
      slide.inert=!active;
    });
  }
  function mount(doc) {
    const motion=window.matchMedia('(prefers-reduced-motion: reduce)');
    doc.querySelectorAll('[data-carousel]').forEach(el=>{
      const slides=[...el.querySelectorAll('[data-carousel-slide]')], controls=el.querySelector('[data-carousel-controls]');
      if(slides.length<2)return;
      const autoplay=el.dataset.autoplay==='true';
      const fade=el.classList.contains('photo-carousel--fade');
      const policy=new CarouselPolicy(slides.length,motion.matches,{autoplay}), count=el.querySelector('[data-carousel-count]'), toggle=el.querySelector('[data-carousel-toggle]'), dots=[...el.querySelectorAll('[data-carousel-dot]')];
      const interval=Number(el.dataset.interval)||6500;
      el.classList.add('is-enhanced');
      if(fade)el.classList.add('is-initializing');
      controls.hidden=false;
      function render(announce=false) {
        updateSlides(slides,policy.index,fade);
        if(count){count.setAttribute('aria-live',announce?'polite':'off');count.textContent=(policy.index+1)+' / '+slides.length;count.setAttribute('aria-label','Photo '+(policy.index+1)+' of '+slides.length);}
        if(toggle){toggle.textContent=policy.paused?'Play':'Pause';toggle.setAttribute('aria-label',policy.paused?'Play slideshow':'Pause slideshow');}
        dots.forEach((dot,i)=>dot.setAttribute('aria-pressed',String(i===policy.index)));
        if(autoplay){const upcoming=slides[(policy.index+1)%slides.length].querySelector('img');if(upcoming)upcoming.loading='eager';}
      }
      function visible() { policy.set('pageHidden',doc.hidden); policy.set('offscreen',!el.getClientRects().length || !!el.closest('[hidden]')); }
      el.querySelector('[data-carousel-prev]')?.addEventListener('click',()=>{policy.previous();render(true);});
      el.querySelector('[data-carousel-next]')?.addEventListener('click',()=>{policy.next();render(true);});
      toggle?.addEventListener('click',()=>{if(policy.paused)policy.play();else policy.pause();render();});
      dots.forEach((dot,i)=>dot.addEventListener('click',()=>{policy.goTo(i);render(true);}));
      el.addEventListener('mouseenter',()=>policy.set('hover',true));
      el.addEventListener('mouseleave',()=>policy.set('hover',false));
      el.addEventListener('focusin',e=>policy.set('focus',!autoplay||e.target.matches(':focus-visible')));
      el.addEventListener('focusout',e=>policy.set('focus',!!(e.relatedTarget&&el.contains(e.relatedTarget)&&(!autoplay||e.relatedTarget.matches(':focus-visible')))));
      el.addEventListener('keydown',e=>{if(e.target.closest('input,textarea'))return;if(e.key==='ArrowRight'||e.key==='ArrowLeft'){e.preventDefault();if(e.key==='ArrowRight')policy.next();else policy.previous();render(true);}});
      doc.addEventListener('visibilitychange',visible);
      motion.addEventListener('change',e=>{policy.reduceMotion(e.matches);render();});
      if('IntersectionObserver' in window)new IntersectionObserver(entries=>{policy.set('offscreen',!entries[0].isIntersecting);},{threshold:0.1}).observe(el);
      render();
      if(fade){el.getBoundingClientRect();el.classList.remove('is-initializing');}
      window.setInterval(()=>{visible();const rect=el.getBoundingClientRect();policy.set('offscreen',policy.flags.offscreen||rect.bottom<=0||rect.top>=window.innerHeight);if(policy.playing){policy.tick();render();}},interval);
    });
  }
  return {CarouselPolicy,updateSlides,mount};
});
