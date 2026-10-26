const test=require('node:test');
const assert=require('node:assert/strict');
let Policy;
try { Policy=require('../assets/js/lab-carousel.js').CarouselPolicy; } catch (_) {}
test('carousel policy exists',()=>assert.equal(typeof Policy,'function'));
test('arrows wrap in both directions and manual navigation pauses rotation',()=>{
  assert.ok(Policy,'missing carousel policy');
  const c=new Policy(2); assert.equal(c.previous(),1); assert.equal(c.playing,false);
  assert.equal(c.next(),0); c.play(); assert.equal(c.playing,true);
  assert.equal(c.tick(),1); assert.equal(c.tick(),0);
});
test('hidden page, hidden card, hover and keyboard focus suppress rotation without losing user pause',()=>{
  assert.ok(Policy,'missing carousel policy');
  const c=new Policy(5);
  for(const flag of ['pageHidden','offscreen','hover','focus']) {
    c.set(flag,true); assert.equal(c.playing,false); assert.equal(c.tick(),0);
    c.set(flag,false); assert.equal(c.playing,true);
  }
  c.pause(); c.set('hover',true); c.set('hover',false); assert.equal(c.playing,false);
});
test('reduced motion starts paused and later enabling it stops playback',()=>{
  assert.ok(Policy,'missing carousel policy');
  const c=new Policy(2,true); assert.equal(c.playing,false); assert.equal(c.tick(),0);
  c.play(); assert.equal(c.playing,true); c.reduceMotion(true); assert.equal(c.playing,false);
});
test('single photo and zero photos never rotate',()=>{
  assert.ok(Policy,'missing carousel policy');
  for(const count of [0,1]) { const c=new Policy(count); assert.equal(c.playing,false);assert.equal(c.next(),0);assert.equal(c.tick(),0); }
});

test('automatic dot navigation keeps rotating and wraps through six photos',()=>{
  const c=new Policy(6,true,{autoplay:true});
  assert.equal(c.playing,true,'the explicitly automatic home slideshow starts playing');
  assert.equal(c.goTo(4),4); assert.equal(c.playing,true);
  assert.equal(c.tick(),5); assert.equal(c.tick(),0);
  c.reduceMotion(true); assert.equal(c.playing,true);
  c.set('focus',true); assert.equal(c.tick(),0);
  c.set('focus',false); assert.equal(c.tick(),1);
  c.previous(); assert.equal(c.playing,true);
});

test('dot selection validates its target and retains manual pause for other carousels',()=>{
  const c=new Policy(2);
  assert.equal(c.goTo(1),1); assert.equal(c.playing,false);
  for(const bad of [-1,2,NaN,0.5]) assert.equal(c.goTo(bad),1);
});
