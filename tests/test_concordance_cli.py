import json
import tempfile
import unittest
from pathlib import Path

from scripts.concordance import lemma_refs, resolve, generate_all, merge_letter, letter_status
from scripts.import_morphhb import run as import_run

LEXICAL_INDEX = """<?xml version="1.0"?><index xmlns="http://openscriptures.github.com/morphhb/namespace">
<part id="a">
<entry id="jkq"><w xlit="al">עַל</w><xref strong="5921" bdb="j.ab.ac"/></entry>
<entry id="frj"><w xlit="ol">עֹל</w><xref strong="5921" bdb="j.ab.ad"/></entry>
<entry id="del"><w xlit="vav">וָו</w><xref strong="2053" bdb="f.aa.ab"/></entry>
<entry id="zzz"><w xlit="aramaic">מִלָּה</w><xref strong="4406"/></entry>
</part></index>"""
AUG_INDEX = """<?xml version="1.0"?><index xmlns="http://openscriptures.github.com/morphhb/namespace">
<w aug="5921a">jkq</w><w aug="5921b">frj</w><w aug="2053">del</w></index>"""
WLC = """<?xml version="1.0"?><osis xmlns="http://www.bibletechnologies.net/2003/OSIS/namespace">
<osisText><div type="book" osisID="Exod"><chapter osisID="Exod.1">
<verse osisID="Exod.1.1">
<w lemma="5921 a" morph="HR" id="t1">עַל</w>
<note type="variant"><catchWord>x</catchWord><rdg type="x-qere"><w lemma="5921 a" id="q1">עַל</w></rdg></note>
<w lemma="c/2053" morph="HC/Ncmsa" id="t2">וְ/וָו</w>
<w lemma="l" morph="HR" id="t3">לְ</w>
<w lemma="5921 b" morph="HNcmsa" id="t4">עֹל</w>
<w lemma="4406" morph="HNcfsa" id="t5">מִלָּה</w>
</verse></chapter></div></osisText></osis>"""


class LemmaRefsTest(unittest.TestCase):
    def test_suffix_is_kept_as_aug_key(self):
        self.assertEqual(lemma_refs("5921 a"), [("5921", "5921a")])
        self.assertEqual(lemma_refs("c/5921 a"), [("5921", "5921a")])
        self.assertEqual(lemma_refs("c/d/1121"), [("1121", "1121")])
        self.assertEqual(lemma_refs("1961 a/3068"), [("1961", "1961a"), ("3068", "3068")])

    def test_prefix_only_lemmas_have_no_strong(self):
        self.assertEqual(lemma_refs("l"), [])
        self.assertEqual(lemma_refs(""), [])
        self.assertEqual(lemma_refs(None), [])


class ResolveTest(unittest.TestCase):
    entries = {"jkq": "עַל", "frj": "עֹל", "del": "וָו"}
    strong_index = {"5921": {"jkq", "frj"}, "2053": {"del"}}
    aug = {"5921a": "jkq", "5921b": "frj", "2053": "del"}

    def test_homograph_suffix_resolves_through_aug_index(self):
        self.assertEqual(resolve("5921a", "5921", self.entries, self.strong_index, self.aug), ("jkq", "aug-index"))
        self.assertEqual(resolve("5921b", "5921", self.entries, self.strong_index, self.aug), ("frj", "aug-index"))

    def test_bare_number_without_aug_is_ambiguous(self):
        self.assertEqual(resolve("5921", "5921", self.entries, self.strong_index, {}), (None, "ambiguous-strong"))

    def test_unique_strong_fallback(self):
        self.assertEqual(resolve("2053", "2053", self.entries, self.strong_index, {}), ("del", "unique-strong-fallback"))


class GenerateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        (root / "wlc").mkdir()
        (root / "wlc" / "Exod.xml").write_text(WLC, encoding="utf-8")
        (root / "lex").mkdir()
        (root / "lex" / "LexicalIndex.xml").write_text(LEXICAL_INDEX, encoding="utf-8")
        (root / "lex" / "AugIndex.xml").write_text(AUG_INDEX, encoding="utf-8")
        self.tokens = root / "tokens.jsonl"
        import_run(root / "wlc", self.tokens, "d" * 40, expected_books=1)
        self.lex = root / "lex"

    def tearDown(self):
        self.tmp.cleanup()

    def test_written_stream_positions_skip_qere(self):
        positions = {t["tokenId"]: t["tokenPosition"] for t in map(json.loads, self.tokens.read_text().splitlines())}
        # q1 (Qere) takes no position: t2 follows t1 directly.
        self.assertEqual(positions, {"t1": 1, "t2": 2, "t3": 3, "t4": 4, "t5": 5})

    def test_homographs_land_in_their_letter_with_distinct_entries(self):
        by_letter, unresolved, stats = generate_all(self.tokens, self.lex)
        ayin = {(e["strongNumber"], e["lexiconEntryId"]): e for e in by_letter["ע"]}
        self.assertEqual(set(ayin), {("5921", "jkq"), ("5921", "frj")})
        self.assertEqual([o["tokenId"] for o in ayin[("5921", "jkq")]["occurrences"]], ["t1"])
        self.assertEqual(by_letter["ו"][0]["occurrences"][0]["tokenPosition"], 2)
        self.assertEqual(stats["tokensWithoutStrong"], 1)       # lemma "l"
        self.assertEqual(stats["headwordWithoutHebrewInitial"], 0)
        self.assertEqual(unresolved, {})                        # 4406 resolves by unique-strong fallback
        self.assertEqual(by_letter["מ"][0]["joinMethod"], "unique-strong-fallback")

    def test_merge_preserves_definitions_and_reports_delta(self):
        by_letter, _, _ = generate_all(self.tokens, self.lex)
        existing = {"letter": "ו", "status": "x", "definitionPilot": {"keep": True}, "entries": [{
            "strongNumber": "2053", "lexiconEntryId": "del", "headword": "וָו", "joinMethod": "aug-index",
            "reviewStatus": "needs-human-review", "occurrenceCount": 1, "definitionHe": "קרס.",
            "definitionVerification": {"editoriallyApproved": False, "strongSourceChecked": True, "bdbSourceChecked": True},
            "occurrences": [{"tokenId": "t2", "verseId": "Exod.1.1", "tokenPosition": 3, "form": "וְ/וָו"}]}]}
        merged, delta = merge_letter("ו", by_letter["ו"], existing)
        self.assertEqual(merged["entries"][0]["definitionHe"], "קרס.")
        self.assertEqual(merged["definitionPilot"], {"keep": True})
        self.assertEqual(merged["entries"][0]["occurrences"][0]["tokenPosition"], 2)
        self.assertEqual(delta["positionChanges"], [{"tokenId": "t2", "verseId": "Exod.1.1", "old": 3, "new": 2}])
        self.assertEqual(delta["entriesAdded"], [])
        self.assertEqual(merged["status"], "source-cross-checked-pending-editorial-review")
        self.assertEqual(list(merged)[-1], "entries")

    def test_status_ladder(self):
        s = {"entries": 2, "withDefinitionHe": 1, "strongSourceChecked": 0, "bdbSourceChecked": 0, "occurrenceCountChecked": 0, "editoriallyApproved": 0}
        self.assertEqual(letter_status(s), "partially-defined-needs-human-review")
        s.update(withDefinitionHe=2)
        self.assertEqual(letter_status(s), "hebrew-glosses-drafted-pending-source-and-editorial-review")
        s.update(editoriallyApproved=2)
        self.assertEqual(letter_status(s), "editorially-approved")


if __name__ == "__main__":
    unittest.main()
