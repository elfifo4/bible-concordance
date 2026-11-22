const assert=require("node:assert/strict");
const fs=require("node:fs");
const vm=require("node:vm");
const html=fs.readFileSync("docs/index.html","utf8");
const start=html.indexOf("function normWord(");
const end=html.indexOf("async function renderVerse(",start);
assert(start>=0&&end>start,"highlight functions not found");
const ctx={
  plain:s=>String(s||"").normalize("NFD").replace(/[\u0591-\u05c7]/g,"").replace(/[ךםןףץ]/g,c=>({ך:"כ",ם:"מ",ן:"נ",ף:"פ",ץ:"צ"}[c])),
  clear:e=>{e.children=[];e.textContent="";},
  node:(tag,text)=>({tag,text}),
  document:{createTextNode:text=>({text})}
};
vm.createContext(ctx);
vm.runInContext(html.slice(start,end),ctx);
function highlight(verse,form,headword,strongNumber){
  const el={children:[],append(...nodes){this.children.push(...nodes);}};
  const ok=ctx.highlightVerse(el,verse,{form,tokenPosition:1},headword,strongNumber);
  return {ok,marked:el.children.filter(n=>n.tag==="mark").map(n=>n.text)};
}
assert.deepEqual(highlight("לֹא דְבָר","דְבָר","לֹא דָבָר"),{ok:true,marked:["לֹא דְבָר"]});
assert.deepEqual(highlight("מִלֹּא דְבָר","דְבָר","לֹא דָבָר"),{ok:true,marked:["מִלֹּא דְבָר"]});
assert.deepEqual(highlight("לֹא־דְבָר","דְבָר","לֹא דָבָר"),{ok:true,marked:["לֹא־דְבָר"]});
assert.deepEqual(highlight("דָבָר אַחֵר","דָבָר","לֹא דָבָר"),{ok:false,marked:[]});
assert.deepEqual(highlight("לֹא דְבָר וְלֹא דְבָר","דְבָר","לֹא דָבָר"),{ok:false,marked:[]});
assert.deepEqual(highlight("תְּהֹמוֹת","תְּהוֹמוֹת","תְּהוֹמוֹת"),{ok:true,marked:["תְּהֹמוֹת"]});
// 2 Samuel 9:4-5 uses לו דבר; 17:27 uses מלוא דבר.
assert.deepEqual(highlight("הוּא בֵּית מָכִיר בֶּן־עַמִּיאֵל בְּלוֹ דְבָר׃","דְבָר","לֹא דָבָר","3810"),{ok:true,marked:["לוֹ דְבָר"]});
assert.deepEqual(highlight("וַיִּקָּחֵהוּ מִבֵּית מָכִיר בֶּן־עַמִּיאֵל מִלּוֹ דְבָר׃","דְבָר","לֹא דָבָר","3810"),{ok:true,marked:["מִלּוֹ דְבָר"]});
assert.deepEqual(highlight("וּמָכִיר בֶּן־עַמִּיאֵל מִלֹּא דְבָר","דְבָר","לֹא דָבָר","3810"),{ok:true,marked:["מִלֹּא דְבָר"]});
assert.deepEqual(highlight("לוֹ דְבָר","דְבָר","לֹא דָבָר","9999"),{ok:false,marked:[]});
console.log("Multiword and spelling highlight tests passed");
