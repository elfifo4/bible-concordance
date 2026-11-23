#!/usr/bin/env node
'use strict';
const fs=require('node:fs');
const assert=require('node:assert/strict');
const base='https://raw.githubusercontent.com';
const revision='21c9add13bc727d3a951361778e97e3ff7afd1ce';
const morphRev='db6c5c9b46b8f39346f10915ddb1a70dcd429901';
const path='data/alphabet/כ.json';
const data=JSON.parse(fs.readFileSync(path,'utf8'));
const drafts=Object.fromEntries(fs.readFileSync('data/kaf-hebrew-drafts.txt','utf8').split(/\r?\n/).filter(s=>/^\d+\|/.test(s)).map(s=>{const i=s.indexOf('|');return [s.slice(0,i),s.slice(i+1)]}));
function decode(s){return s.replace(/&amp;/g,'&').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&quot;/g,'"').replace(/&#(\d+);/g,(_,n)=>String.fromCodePoint(+n))}
function plain(s){return decode(s.replace(/<[^>]*>/g,'')).replace(/\s+/g,' ').trim()}
function field(s,t){return s.match(new RegExp('<'+t+'(?:\\s[^>]*)?>([\\s\\S]*?)<\\/'+t+'>'))?.[1]??''}
function entry(xml,id){const re=new RegExp('<entry\\b[^>]*\\bid="'+id+'"[^>]*>([\\s\\S]*?)<\\/entry>');const m=xml.match(re);assert(m,'Missing dictionary entry '+id);return m[1]}
async function get(url){const r=await fetch(url);if(!r.ok)throw Error('HTTP '+r.status+' '+url);return r.text()}
const attr=(s,name)=>s.match(new RegExp('\\b'+name+'="([^"]*)"'))?.[1];
async function main(){
 assert.equal(data.entries.length,273);
 assert.equal(data.entries.reduce((n,e)=>n+e.occurrences.length,0),11708);
 assert.equal(Object.keys(drafts).length,273);
 const [strong,index,bdb]=await Promise.all(['HebrewStrong.xml','LexicalIndex.xml','BrownDriverBriggs.xml'].map(f=>get(base+'/openscriptures/HebrewLexicon/'+revision+'/'+f)));
 const indexEntries=[...index.matchAll(/<entry id="([^"]+)">([\s\S]*?)<\/entry>/g)];
 const books=[...new Set(data.entries.flatMap(e=>e.occurrences.map(o=>o.verseId.split('.')[0])))];
 const morphFiles=Object.fromEntries(await Promise.all(books.map(async b=>[b,await get(base+'/openscriptures/morphhb/'+morphRev+'/wlc/'+b+'.xml')])));
 const verses={};
 for(const [book,xml] of Object.entries(morphFiles)){
  for(const m of xml.matchAll(/<verse\s+osisID="([^"]+)"[^>]*>([\s\S]*?)<\/verse>/g)){
   verses[m[1]]=[...m[2].matchAll(/<w\b([^>]*)>([\s\S]*?)<\/w>/g)].map((w,i)=>({attrs:w[1],form:decode(w[2]),position:i+1}));
  }
 }
 const ids=data.entries.map(e=>String(e.strongNumber));
 assert.equal(new Set(ids).size,273,'Duplicate dictionary IDs');
 assert.deepEqual(Object.keys(drafts).sort(),ids.sort(),'Draft IDs differ from dictionary IDs');
 const seenTokens=new Set();
 let corrected=0,checked=0;
 for(const e of data.entries){
  const id=e.strongNumber, source=entry(strong,'H'+id);
  const indexStrong=id; // Exact mapping only; fail on missing references.
  const idx=indexEntries.find(m=>new RegExp('strong="'+indexStrong+'"(?=[\\s/>])').test(m[2]));
  assert(idx,'No index for H'+id);
  const bid=idx[2].match(/<xref[^>]*bdb="([^"]+)"/)?.[1];
  assert(bid,'No BDB index for H'+id);
  const bdbExcerpt=entry(bdb,bid).split(/<status\b/)[0].trim();
  const f=Object.fromEntries(['source','meaning','usage'].map(t=>[t,field(source,t)]));
  assert(drafts[id],'No Hebrew draft H'+id);
  e.definitionHe=drafts[id];e.definitionEn=plain(f.meaning)||plain(f.usage);
  e.definitionSource={name:'Strong’s Hebrew Dictionary (via Open Scriptures HebrewLexicon)',url:'https://github.com/openscriptures/HebrewLexicon',strongUrl:'https://biblehub.com/hebrew/'+id+'.htm',strongNumber:id};
  e.definitionReviewStatus='source-checked-pending-editorial-review';e.definitionConfidence='source-based';
  e.definitionVerification={sources:[e.definitionSource.strongUrl],dictionaries:['Strong','Brown-Driver-Briggs'],method:'Strong and BDB XML matched against pinned revisions; Hebrew definitions are drafts pending editorial review. MorphHB token fields checked directly.',editoriallyApproved:false,strongSourceChecked:true,bdbSourceChecked:true,occurrenceCountChecked:true};
  e.definitionOriginalEnglish={strong:{source:plain(f.source),meaning:plain(f.meaning),usage:plain(f.usage),sourceUrl:base+'/openscriptures/HebrewLexicon/'+revision+'/HebrewStrong.xml',entryId:'H'+id,license:'CC BY 4.0',format:'plain-text extraction of XML source, meaning and usage nodes',verifiedAgainstSource:true,sourceXml:f.source,meaningXml:f.meaning,usageXml:f.usage,sourceRevision:revision},bdb:{entryId:bid,entryBodyXml:bdbExcerpt,sourceUrl:base+'/openscriptures/HebrewLexicon/'+revision+'/BrownDriverBriggs.xml',license:'CC BY 4.0',verifiedAgainstSource:true,sourceFormat:'BDB XML entry body excluding status tag',sourceRevision:revision,verificationNote:'Matched pinned LexicalIndex and BDB source excerpt.',scope:'lexical-opening-excerpt'}};
  for(const o of e.occurrences){
   assert(!seenTokens.has(o.tokenId),'Duplicate token '+o.tokenId);seenTokens.add(o.tokenId);
   const list=verses[o.verseId];assert(list,'Missing verse '+o.verseId);
   const tok=list.find(t=>attr(t.attrs,'id')===o.tokenId);assert(tok,'Missing token '+o.tokenId);
   assert.equal(tok.form,o.form,o.tokenId+' form');
   assert.equal(attr(tok.attrs,'lemma'),o.lemmaRaw,o.tokenId+' lemma');
   assert.equal(attr(tok.attrs,'morph'),o.morphRaw,o.tokenId+' morphology');
   if(tok.position!==o.tokenPosition){o.tokenPosition=tok.position;corrected++}
   checked++;
  }
 }
 assert.equal(checked,11708);
 data.status='source-cross-checked-pending-editorial-review';
 if(!process.argv.includes('--check-only')) {
  fs.writeFileSync(path+'.tmp',JSON.stringify(data,null,2)+'\n');
  fs.renameSync(path+'.tmp',path);
 }
 console.log('PASS 273 Hebrew drafts; 273 Strong XML entries; 273 BDB excerpts; '+checked+' MorphHB tokens; '+corrected+' token positions corrected across '+books.length+' books.');
}
main().catch(e=>{console.error(e.stack);process.exitCode=1});
