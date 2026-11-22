#!/usr/bin/env node
'use strict';
const fs=require('node:fs');
const assert=require('node:assert/strict');
const data=JSON.parse(fs.readFileSync('data/alphabet/ו.json','utf8'));
const base='https://raw.githubusercontent.com';
const norm=s=>s.normalize('NFD').replace(/[\u0591-\u05BD\u05BF-\u05C7]/g,'').normalize('NFC');
const fail=(msg)=>{throw new Error(msg)};
async function get(url){const r=await fetch(url);if(!r.ok)fail('HTTP '+r.status+' '+url);return r.text()}
function entry(xml,id){const re=new RegExp('<entry\\b[^>]*\\bid="'+id+'"[^>]*>([\\s\\S]*?)<\\/entry>');const m=xml.match(re);if(!m)fail('Missing dictionary entry '+id);return m[1]}
function field(body,tag){const m=body.match(new RegExp('<'+tag+'(?:\\s[^>]*)?>([\\s\\S]*?)<\\/'+tag+'>'));return m?m[1]:null}
function decode(s){return s.replace(/&amp;/g,'&').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&quot;/g,'"').replace(/&#(\d+);/g,(_,n)=>String.fromCodePoint(+n))}
function plain(s){return decode(s.replace(/<[^>]*>/g,'')).trim()}
function verse(xml,ref){const match=xml.match(new RegExp('<verse\\s+osisID="'+ref.replace(/\./g,'\\.')+'"[^>]*>([\\s\\S]*?)<\\/verse>'));if(!match)fail('Missing verse '+ref);return match[1]}
const tokens=s=>[...s.matchAll(/<w\b([^>]*)>([\s\S]*?)<\/w>/g)].map(m=>({attrs:m[1],form:decode(m[2])}));
const attr=(s,name)=>{const m=s.match(new RegExp('\\b'+name+'="([^"]*)"'));return m?.[1]};
(async()=>{
assert.equal(data.entries.length,10);
assert.equal(data.entries.reduce((n,e)=>n+e.occurrences.length,0),31);
const revision=data.source.hebrewLexiconRevision;
const morphRev=data.source.morphhbRevision;
const [strongXml,bdbXml]=await Promise.all([
get(base+'/openscriptures/HebrewLexicon/'+revision+'/HebrewStrong.xml'),
get(base+'/openscriptures/HebrewLexicon/'+revision+'/BrownDriverBriggs.xml')
]);
const books=[...new Set(data.entries.flatMap(e=>e.occurrences.map(o=>o.verseId.split('.')[0])))];
const files=Object.fromEntries(await Promise.all(books.map(async book=>[book,await get(base+'/openscriptures/morphhb/'+morphRev+'/wlc/'+book+'.xml')])));
let checked=0;
for(const e of data.entries){
const id='H'+e.strongNumber,orig=e.definitionOriginalEnglish.strong;
const source=entry(strongXml,id);
for(const tag of ['source','meaning','usage']){
const original=field(source,tag);
assert.notEqual(original,null,id+' '+tag+' missing in XML');
assert.equal(orig[tag+'Xml'],original,id+' '+tag+' XML differs from source');
assert.equal(orig[tag],plain(original),id+' '+tag+' plain text differs from source');
}
const bdb=e.definitionOriginalEnglish.bdb;
const bdbEntry=entry(bdbXml,bdb.entryId).split(/<status\b/)[0].trim();
assert.equal(bdb.entryBodyXml,bdbEntry,id+' BDB excerpt differs from source');
assert.equal(e.definitionVerification.editoriallyApproved,false);
for(const occ of e.occurrences){
const book=occ.verseId.split('.')[0];
const list=tokens(verse(files[book],occ.verseId));
const tok=list.find(t=>attr(t.attrs,'id')===occ.tokenId);
assert(tok,'Token '+occ.tokenId+' not in '+occ.verseId);
assert.equal(list.indexOf(tok)+1,occ.tokenPosition,occ.tokenId+' position mismatch in '+occ.verseId+': stored='+occ.tokenPosition+', actual='+(list.indexOf(tok)+1));
assert.equal(tok.form,occ.form,occ.tokenId+' form mismatch');
assert.equal(attr(tok.attrs,'lemma'),occ.lemmaRaw,occ.tokenId+' lemma mismatch');
assert.equal(attr(tok.attrs,'morph'),occ.morphRaw,occ.tokenId+' morphology mismatch');
assert(norm(tok.form).startsWith(norm(e.headword).slice(0,1)),occ.tokenId+' unexpected form');
checked++;
}
console.log('PASS '+id+' '+e.headword+' '+e.occurrences.length+' occurrence(s)');
}
console.log('PASS 10 Strong exact entries, 10 BDB exact excerpts, '+checked+'/31 occurrence tokens checked against pinned MorphHB revision.');
})().catch(e=>{console.error(e.stack);process.exitCode=1});
