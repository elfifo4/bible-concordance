const assert=require("node:assert/strict");
const fs=require("node:fs");
const data=JSON.parse(fs.readFileSync("data/alphabet/ו.json","utf8"));
const html=fs.readFileSync("docs/index.html","utf8");
assert.equal(data.letter,"ו");
assert.equal(data.entries.length,10);
assert.equal(data.entries.reduce((sum,e)=>sum+e.occurrenceCount,0),31);
assert.equal(data.definitionPilot.reviewedByHuman,false);
for(const entry of data.entries){
  assert(entry.definitionHe&&entry.definitionEn,entry.headword+" missing bilingual definition");
  assert.equal(entry.definitionReviewStatus,"source-checked-pending-editorial-review");
  assert(["high","uncertain","disputed"].includes(entry.definitionConfidence));
  assert.equal(entry.definitionVerification.editoriallyApproved,false);
  assert.equal(entry.definitionSource.strongNumber,entry.strongNumber);
  assert(entry.definitionSource.strongUrl.endsWith("/"+entry.strongNumber+".htm"));
  assert(!entry.definitionHe.includes(entry.headword),"Circular definition: "+entry.headword);
}
assert(html.includes('e.definitionReviewStatus==="source-checked-pending-editorial-review"'));
assert(html.includes("e.definitionSource?.strongUrl"));
console.log("Vav pilot: 10 definitions, 31 occurrences, attribution and review flags verified");
