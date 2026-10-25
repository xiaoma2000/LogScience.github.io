const test = require('node:test');
const assert = require('node:assert/strict');
const state = require('../assets/js/lab-state.js');
test('normalizes accents and retains Chinese search', () => {
  assert.equal(state.normalize('  Café 氮循环  '), 'cafe 氮循环');
});
test('invalid parameters fall back safely', () => {
  assert.deepEqual(state.parse('?page=-2&category=unknown&lang=xx'), {page:1,category:'all',lang:'en',q:''});
});
test('category and bilingual text combine before pagination', () => {
  const rows = [{category:'research',searchText:'carbon 氮循环'}, {category:'research',searchText:'microplastic'}, {category:'fieldwork',searchText:'carbon'}];
  const r = state.select(rows,{page:99,category:'research',q:'氮循环',lang:'en'},10);
  assert.equal(r.total,1); assert.equal(r.page,1); assert.equal(r.items[0],rows[0]);
});
test('empty and final pages remain valid', () => {
  const rows=Array.from({length:25},(_,i)=>({searchText:String(i),category:'research'}));
  assert.equal(state.select(rows,{page:3,q:'',category:'all'},10).items.length,5);
  assert.deepEqual(state.select(rows,{page:3,q:'missing',category:'all'},10),{items:[],total:0,pages:1,page:1});
});
test('URL state retains unrelated parameters and removes defaults', () => {
  const s=state.query({page:2,category:'research',lang:'zh',q:'氮'},'?utm_source=lab');
  const p=new URLSearchParams(s); assert.equal(p.get('utm_source'),'lab'); assert.equal(p.get('page'),'2'); assert.equal(p.get('q'),'氮');
  const cleared=state.query({page:1,category:'all',lang:'en',q:''},s);
  assert.equal(cleared,'?utm_source=lab');
});
