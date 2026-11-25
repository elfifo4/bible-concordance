import json
import tempfile
import unittest
from pathlib import Path

from scripts import concordance as cli
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


STRONG_XML = ('<?xml version="1.0"?>\r\n<lexicon>\r\n<entry id="H2053">\r\n\t<w pos="n-m" xml:lang="heb">וָו</w>\r\n'
              '\t<source>probably a <def>hook</def>;</source>\r\n\t<meaning>a <def>hook</def></meaning>\r\n'
              '\t<usage>hook.</usage>\r\n</entry>\r\n<entry id="H5921">\r\n\t<w pos="prep">עַל</w>\r\n'
              '\t<meaning><def>above</def></meaning>\r\n\t<usage>above, upon.</usage>\r\n</entry>\r\n</lexicon>\r\n')
BDB_XML = ('<?xml version="1.0"?>\r\n<lexicon>\r\n<entry id="f.aa.ab"><w>וָו</w> <pos>n.m.</pos>\r\n'
           '<def>hook</def>, <def>peg</def>.<status p="255">done</status></entry>\r\n</lexicon>\r\n')


def letter_doc():
    occ = lambda tid, lemma, morph: {"tokenId": tid, "verseId": "Exod.1.1", "tokenPosition": 1, "form": "x",
                                     "readingType": "standard", "lemmaRaw": lemma, "morphRaw": morph, "source": "s"}
    return {"letter": "ו", "status": "x", "summary": {}, "entries": [
        {"strongNumber": "2053", "lexiconEntryId": "del", "headword": "וָו", "occurrenceCount": 2,
         "occurrences": [occ("t2", "c/2053", "HC/Ncmsa"), occ("t9", "2053", "HNcmpa")]},
        {"strongNumber": "5921", "lexiconEntryId": "frj", "headword": "עֹל", "occurrenceCount": 1,
         "occurrences": [occ("t4", "5921 b", "HNcmsa")]}]}


class EnrichLintTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        root = Path(self.tmp.name)
        lex = root / "build" / "sources" / f"hebrewlexicon-{cli.LEXICON_REV}"
        lex.mkdir(parents=True)
        (lex / "LexicalIndex.xml").write_text(LEXICAL_INDEX, encoding="utf-8")
        (lex / "AugIndex.xml").write_text(AUG_INDEX, encoding="utf-8")
        for name, text in (("HebrewStrong.xml", STRONG_XML), ("BrownDriverBriggs.xml", BDB_XML)):
            with (lex / name).open("w", encoding="utf-8", newline="") as fh:
                fh.write(text)
        self.build = root / "build"
        self.letter_file = root / "ו.json"
        self.letter_file.write_text(json.dumps(letter_doc(), ensure_ascii=False), encoding="utf-8")
        self._orig = cli.letter_path
        cli.letter_path = lambda letter: self.letter_file
        self.drafts = root / "drafts.txt"
        self.drafts.write_text("# comment\n2053|del|קרס או יתד לתליית יריעות המשכן.\n5921|frj|מוט עץ על צוואר בהמת משא.\n",
                               encoding="utf-8")

    def tearDown(self):
        cli.letter_path = self._orig
        self.tmp.cleanup()

    def run_cli(self, *argv):
        return cli.main(["--build", str(self.build), *argv])

    def test_morph_pos_uses_the_segment_of_the_strong_number(self):
        o = {"lemmaRaw": "c/2053", "morphRaw": "HC/Ncmsa"}
        self.assertEqual(cli.morph_pos(o, "2053"), "Nc")
        self.assertEqual(cli.morph_pos({"lemmaRaw": "b/5432", "morphRaw": "HR/Vqc"}, "5432"), "Vq")
        self.assertEqual(cli.morph_pos({"lemmaRaw": "5433 b", "morphRaw": "HNpm"}, "5433"), "Npm")
        self.assertEqual(cli.morph_pos({"lemmaRaw": "5922", "morphRaw": "ANcmsa"}, "5922"), "A:Nc")

    def test_worksheet_has_one_line_per_entry(self):
        self.run_cli("worksheet", "--letter", "ו")
        rows = (self.build / "worksheets" / "ו.tsv").read_text(encoding="utf-8").splitlines()
        self.assertEqual(len(rows), 3)
        cols = rows[1].split("\t")
        self.assertEqual(cols[:5], ["2053", "del", "וָו", "Nc|n-m", "2"])
        self.assertEqual(cols[5], "a hook")
        self.assertEqual(cols[7], "וָו n.m. hook, peg.")
        self.assertEqual(rows[2].split("\t")[7], "")       # frj has no BDB xref

    def test_parse_drafts_reports_malformed_and_duplicates(self):
        self.drafts.write_text("2053|del|א\nbad line\n2053|del|ב\n", encoding="utf-8")
        drafts, errors = cli.parse_drafts(self.drafts)
        self.assertEqual(drafts, {("2053", "del"): "ב"})
        self.assertEqual(len(errors), 2)

    def test_enrich_fills_fields_byte_exact_and_flags_only_found_sources(self):
        before = json.loads(self.letter_file.read_text(encoding="utf-8"))
        self.run_cli("enrich", "--letter", "ו", "--drafts", str(self.drafts))
        d = json.loads(self.letter_file.read_text(encoding="utf-8"))
        vav, ol = d["entries"]
        self.assertEqual([e["occurrences"] for e in d["entries"]], [e["occurrences"] for e in before["entries"]])
        self.assertEqual(vav["definitionHe"], "קרס או יתד לתליית יריעות המשכן.")
        self.assertEqual(vav["definitionReviewStatus"], "source-checked-pending-editorial-review")
        self.assertEqual(vav["definitionOriginalEnglish"]["strong"]["meaningXml"], "a <def>hook</def>")
        self.assertEqual(vav["definitionOriginalEnglish"]["bdb"]["entryBodyXml"],
                         "<w>וָו</w> <pos>n.m.</pos>\r\n<def>hook</def>, <def>peg</def>.")
        v = vav["definitionVerification"]
        self.assertEqual((v["strongSourceChecked"], v["bdbSourceChecked"], v["editoriallyApproved"],
                          v["occurrenceCountChecked"]), (True, True, False, False))   # no audit report yet
        w = ol["definitionVerification"]
        self.assertEqual((w["strongSourceChecked"], w["bdbSourceChecked"]), (True, False))
        self.assertEqual(ol["definitionReviewStatus"], "draft")
        self.assertIn("no mapping was invented", ol["definitionNote"])
        rep = json.loads((self.build / "reports" / "enrich-ו.json").read_text(encoding="utf-8"))
        self.assertEqual(rep["exceptions"][0]["missing"], ["BDB"])

    def test_enrich_marks_occurrences_checked_only_after_a_passing_audit(self):
        (self.build / "reports").mkdir(parents=True)
        (self.build / "reports" / "audit-ו.json").write_text(json.dumps({"pass": True, "checkedOccurrences": 3}))
        self.run_cli("enrich", "--letter", "ו", "--drafts", str(self.drafts))
        d = json.loads(self.letter_file.read_text(encoding="utf-8"))
        self.assertTrue(all(e["definitionVerification"]["occurrenceCountChecked"] for e in d["entries"]))

    def test_enrich_refuses_drafts_for_unknown_entries(self):
        self.drafts.write_text("9999|nope|משהו\n", encoding="utf-8")
        with self.assertRaises(SystemExit):
            self.run_cli("enrich", "--letter", "ו", "--drafts", str(self.drafts))
        self.assertNotIn("definitionHe", json.loads(self.letter_file.read_text(encoding="utf-8"))["entries"][0])

    def test_lint_rules(self):
        e = {"strongNumber": "5483", "headword": "סוּס", "occurrences": [{"lemmaRaw": "5483", "morphRaw": "HNcmsa"}]}
        self.assertEqual(cli.lint_entry(dict(e)), ["missing"])
        self.assertEqual(cli.lint_entry(dict(e, definitionHe="בעל חיים לרכיבה ולמלחמה.")), [])
        self.assertEqual(cli.lint_entry(dict(e, definitionHe="סוס; בעל חיים.")), ["repeats-headword"])
        self.assertEqual(cli.lint_entry(dict(e, definitionHe="רוכב על הסוסים.")), [])          # plural is not the headword
        self.assertEqual(cli.lint_entry(dict(e, definitionHe="רוכב והסוס.")), ["repeats-headword"])  # prefixes stripped
        self.assertIn("more-than-two-sentences", cli.lint_entry(dict(e, definitionHe="א. ב. ג.")))
        self.assertIn("over-160-chars", cli.lint_entry(dict(e, definitionHe="מילה " * 40)))
        name = {"strongNumber": "5482", "headword": "סְוֵנֵה", "occurrences": [{"lemmaRaw": "5482", "morphRaw": "HNpl"}]}
        self.assertEqual(cli.lint_entry(dict(name, definitionHe="שם מקום.")), ["proper-name-without-context"])
        self.assertEqual(cli.lint_entry(dict(name, definitionHe="עיר בגבול הדרומי של מצרים.")), [])


if __name__ == "__main__":
    unittest.main()
