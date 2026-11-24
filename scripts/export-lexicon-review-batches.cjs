#!/usr/bin/env node
'use strict';
const fs = require('node:fs');
const assert = require('node:assert/strict');
const base = 'https://raw.githubusercontent.com/openscriptures/HebrewLexicon/21c9add13bc727d3a951361778e97e3ff7afd1ce/';
const letter = process.argv[2] || 'ק';
const batch = Number(process.argv[3] || 25);
assert(/^[א-ת]$/.test(letter) && Number.isInteger(batch) && batch > 0 && batch <= 100);
const data = JSON.parse(fs.readFileSync('data/alphabet/' + letter + '.json', 'utf8'));
const output = 'data/lexicon-review/' + letter;
async function get(file) {
  const response = await fetch(base + file);
  if (!response.ok) throw Error('HTTP ' + response.status + ': ' + file);
  return response.text();
}
function entries(xml) {
  return new Map([...xml.matchAll(/<entry\b[^>]*\bid="([^"]+)"[^>]*>([\s\S]*?)<\/entry>/g)].map(m => [m[1], m[2]]));
}
function field(xml, tag) {
  return xml.match(new RegExp('<' + tag + '(?:\\s[^>]*)?>([\\s\\S]*?)<\\/' + tag + '>'))?.[1] || '';
}
async function main() {
  const [strong, index, bdb] = (await Promise.all(['HebrewStrong.xml','LexicalIndex.xml','BrownDriverBriggs.xml'].map(get))).map(entries);
  const links = new Map();
  for (const body of index.values()) {
    const id = body.match(/\bstrong="(\d+)"/)?.[1];
    const bid = body.match(/<xref[^>]*\bbdb="([^"]+)"/)?.[1];
    if (id && bid && !links.has(id)) links.set(id, bid);
  }
  const records = data.entries.map(e => {
    const id = String(e.strongNumber);
    const s = strong.get('H' + id);
    const bid = links.get(id);
    const b = bdb.get(bid);
    assert(s && b, 'Missing source H' + id);
    return {strongNumber:id,headword:e.headword,occurrenceCount:e.occurrenceCount,
      examples:e.occurrences.slice(0,e.occurrenceCount <= 5 ? 5 : 3).map(o=>({verseId:o.verseId,form:o.form})),
      strong:{source:field(s,'source'),meaning:field(s,'meaning'),usage:field(s,'usage')},
      bdb:{entryId:bid,excerpt:b.split(/<status\b/)[0].trim()}};
  });
  assert.equal(records.length,data.entryCount);
  fs.mkdirSync(output,{recursive:true});
  for(let i=0;i<records.length;i+=batch) {
    fs.writeFileSync(output+'/'+String(1+i/batch).padStart(2,'0')+'.json',JSON.stringify(records.slice(i,i+batch),null,2)+'\n');
  }
  console.log('Extracted '+records.length+' source records in '+Math.ceil(records.length/batch)+' batches; no corpus changes.');
}
main().catch(e=>{console.error(e.stack);process.exitCode=1});
