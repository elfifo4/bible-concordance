import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path

from scripts import app_export as ax

# Gen 1 in the app's format: header line, {..} markers, verse numerals, maqaf, paseq,
# a bare ketiv followed by its qere in parentheses, and an unpointed short ketiv ("ב")
# that must not be read as verse 2 because it does not follow a sof pasuq.
GEN_1 = "\ufeffבראשית פרק א \r\n\r\n{1} א אָב ב (בּוֹ) כִּי־טוֹב ׀ גַּם׃ {פ}\r\n{ל} ב דָּג הוצא (הַיְצֵא) עַל־הָאָרֶץ׃\r\n"
# Gen 2 in the app numbers MorphHB's Gen 1:3 as 2:1, spells שָׁלוֹם plene, and joins two
# MorphHB words into one; MorphHB's Gen 1:4 (right after the joined word) is not in the app.
GEN_2 = "\ufeffבראשית פרק ב \r\n\r\nא שָׁלוֹם טוֹב פְּדָהצוּר׃\r\n"

MHB = [  # (verseId, position, form) - MorphHB written stream
    ("Gen.1.1", 1, "אָב"), ("Gen.1.1", 2, "ב"), ("Gen.1.1", 3, "כִּי"), ("Gen.1.1", 4, "טֽוֹב"),
    ("Gen.1.1", 5, "גַּם"),
    ("Gen.1.2", 1, "דָּג"), ("Gen.1.2", 2, "הוצא"), ("Gen.1.2", 3, "עַל"), ("Gen.1.2", 4, "הָ/אָֽרֶץ"),
    ("Gen.1.3", 1, "שָׁלֹם"), ("Gen.1.3", 2, "טוֹב"), ("Gen.1.3", 3, "פְּדָה"), ("Gen.1.3", 4, "צוּר"),
    ("Gen.1.4", 1, "חֵסֶר"),
]


def write_fixture(root):
    app = root / "allChapters"
    app.mkdir()
    (app / "_1_bereshit-01.txt").write_text(GEN_1, encoding="utf-16")
    (app / "_1_bereshit-02.txt").write_text(GEN_2, encoding="utf-16")
    (root / "verses_per_chapter.csv").write_text(
        "filename,verses\r\n_1_bereshit-01.txt,2\r\n_1_bereshit-02.txt,1\r\n", encoding="utf-16")
    tokens = root / "tokens.jsonl"
    tokens.write_text("".join(json.dumps({"verseId": v, "tokenPosition": p, "form": f}, ensure_ascii=False) + "\n"
                              for v, p, f in MHB), encoding="utf-8")
    alphabet = root / "alphabet"
    alphabet.mkdir()

    def occ(v, p):
        return {"verseId": v, "tokenPosition": p, "form": dict(((a, b), c) for a, b, c in MHB)[(v, p)]}

    letters = {
        "א": [{"lexiconEntryId": "aaa", "strongNumber": "1", "headword": "אָב", "definitionHe": "אבא.",
               "definitionReviewStatus": "pending", "occurrenceCount": 1, "occurrences": [occ("Gen.1.1", 1)]}],
        "צ": [{"lexiconEntryId": "ccc", "strongNumber": "2", "headword": "צוּר", "definitionHe": "סלע.",
               "definitionReviewStatus": "pending", "occurrenceCount": 3,
               "occurrences": [occ("Gen.1.3", 3), occ("Gen.1.3", 4), occ("Gen.1.4", 1)]}],
        "ע": [{"lexiconEntryId": "bbb", "strongNumber": "3", "headword": "עַל", "definitionHe": None,
               "definitionReviewStatus": "pending", "occurrenceCount": 1, "occurrences": [occ("Gen.1.2", 3)]}],
    }
    manifest = {"status": "test", "sourceRevisions": {"morphhb": "x"},
                "letters": [{"letter": k} for k in letters]}
    (alphabet / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    for letter, entries in letters.items():
        (alphabet / f"{letter}.json").write_text(json.dumps({"entries": entries}, ensure_ascii=False), encoding="utf-8")
    return app, tokens, alphabet


class ParseAppChapterTest(unittest.TestCase):
    def test_words_markers_qere_and_short_ketiv(self):
        verses = ax.parse_app_chapter(GEN_1)
        self.assertEqual(verses[1], ["אָב", "ב", "כִּי", "טוֹב", "גַּם"])
        self.assertEqual(verses[2], ["דָּג", "הוצא", "עַל", "הָאָרֶץ"])

    def test_inverted_nun_after_sof_pasuq_keeps_next_verse_number(self):
        # Num 10:34-36 in the app: "…׃ {ס} ׆ {ס} לה …" must still start verse 35
        chapter = "h\n" + "א אָב׃ ב בַּת׃ {ס} ׆ {ס} ג גַּם׃ ׆ ד דָּג׃"
        self.assertEqual(ax.parse_app_chapter(chapter), {1: ["אָב"], 2: ["בַּת"], 3: ["גַּם"], 4: ["דָּג"]})

    def test_nbsp_and_maqaf_separate_words_zwj_stays(self):
        chapter = "h\nא הַ\u00a0לְיְהֹוָה עַל־פְּנֵי עֲו\u200dֹן׃"
        self.assertEqual(ax.parse_app_chapter(chapter)[1], ["הַ", "לְיְהֹוָה", "עַל", "פְּנֵי", "עֲו\u200dֹן"])

    def test_lone_sof_pasuq_after_qere_ends_the_verse(self):
        chapter = "h\nא אָב הוצא (הַיְצֵא)׃ ב גַּם׃"
        self.assertEqual(ax.parse_app_chapter(chapter), {1: ["אָב", "הוצא"], 2: ["גַּם"]})

    def test_crlf_header_and_bom(self):
        self.assertEqual(ax.parse_app_chapter("\ufeffבראשית פרק א\r\nא אָב׃\r\n"), {1: ["אָב"]})

    def test_gematria_needs_unpointed_letters(self):
        self.assertEqual(ax.gematria("טז"), 16)
        self.assertIsNone(ax.gematria("טָז"))
        self.assertIsNone(ax.gematria("x"))


class AlignTest(unittest.TestCase):
    def test_spelling_renumbering_joined_and_missing(self):
        with tempfile.TemporaryDirectory() as d:
            app_dir, tokens, _ = write_fixture(Path(d))
            mapping, stats = ax.align(ax.morphhb_written_tokens(tokens), ax.read_app_text(app_dir, 2))
        self.assertEqual(mapping[((1, 1, 1), 4)], ((1, 1, 1), 4))            # טֽוֹב / טוֹב
        self.assertEqual(mapping[((1, 1, 3), 1)], ((1, 2, 1), 1))            # spelling variant + renumbered
        self.assertEqual(mapping[((1, 1, 3), 3)], ((1, 2, 1), 3))            # joined in the app
        self.assertEqual(mapping[((1, 1, 3), 4)], ((1, 2, 1), 3))
        self.assertIsNone(mapping[((1, 1, 4), 1)])                           # verse not in the app
        self.assertEqual(stats["unmapped"], 1)
        self.assertEqual(stats["joined-in-app"], 2)

    def test_check_alignment_report(self):
        with tempfile.TemporaryDirectory() as d:
            app_dir, tokens, _ = write_fixture(Path(d))
            r = ax.check_alignment(tokens, app_dir, expected_chapters=2)
        self.assertEqual(r["tokens"], len(MHB))
        self.assertEqual(r["mapped"], len(MHB) - 1)
        self.assertEqual(r["verses"]["onlyInMorphhb"], ["Gen.1.3", "Gen.1.4"])
        self.assertEqual(r["verses"]["onlyInApp"], ["Gen.2.1"])
        self.assertEqual(r["verseCountMismatches"], [])


class ExportTest(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            app_dir, tokens, alphabet = write_fixture(Path(d))
            summary = ax.export_app(alphabet, tokens, app_dir, Path(d) / "out", 2, min_mapped_pct=0)
            bin_bytes = (Path(d) / "out" / "occurrences.bin").read_bytes()
            doc = json.loads((Path(d) / "out" / "entries.json").read_text(encoding="utf-8"))
            occ = ax.read_occurrences((Path(d) / "out" / "occurrences.bin").read_bytes())
        self.assertEqual(doc["format"], ax.FORMAT)
        self.assertFalse(doc["meta"]["editoriallyApproved"])
        self.assertEqual(doc["meta"]["occurrencesBytes"], len(bin_bytes))
        self.assertEqual(doc["meta"]["occurrencesSha256"], hashlib.sha256(bin_bytes).hexdigest())
        self.assertEqual([e[0] for e in doc["entries"]], ["aaa", "ccc", "bbb"])
        self.assertEqual(doc["meta"]["occurrenceCount"], 5)
        by_id = {e[0]: (e, locs) for e, locs in zip(doc["entries"], occ)}
        self.assertEqual([ax.unpack_location(x) for x in by_id["aaa"][1]], [(1, 1, 1, 1)])
        self.assertEqual([ax.unpack_location(x) for x in by_id["bbb"][1]], [(1, 1, 2, 3)])
        # two MorphHB tokens of one entry written as one app word -> one location
        self.assertEqual([ax.unpack_location(x) for x in by_id["ccc"][1]], [(1, 2, 1, 3)])
        self.assertEqual(by_id["ccc"][0][6], 3)
        self.assertEqual(by_id["ccc"][0][7], ["Gen.1.4#1"])
        self.assertEqual(summary["unplaced"], 1)
        self.assertEqual(summary["joinedSameEntry"], 1)

    def test_varint_and_location_packing(self):
        for n in (0, 1, 127, 128, 300, 2 ** 31):
            data = ax.MAGIC + ax.varint(1) + ax.varint(n)
            self.assertEqual(ax.read_occurrences(data), [[n]])
        loc = ax.pack_location(39, 36, 23, 43)
        self.assertEqual(ax.unpack_location(loc), (39, 36, 23, 43))


class GuardsTest(unittest.TestCase):
    def test_missing_or_wrong_app_dir_fails_loudly(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaises(ValueError):
                ax.read_app_text(Path(d) / "nope")
            app_dir, _, _ = write_fixture(Path(d))
            with self.assertRaises(ValueError):          # 2 files, 929 expected
                ax.read_app_text(app_dir)
            (app_dir / "_2_bereshit-01.txt").write_text(GEN_1, encoding="utf-16")
            with self.assertRaises(ValueError):          # book 2 is shemot
                ax.read_app_text(app_dir, 3)

    def test_export_refuses_wrong_verse_counts_and_low_mapping(self):
        with tempfile.TemporaryDirectory() as d:
            app_dir, tokens, alphabet = write_fixture(Path(d))
            with self.assertRaises(ValueError):          # fixture maps 13/14 < 99.98%
                ax.export_app(alphabet, tokens, app_dir, Path(d) / "out", 2)
            (Path(d) / "verses_per_chapter.csv").write_text(
                "filename,verses\r\n_1_bereshit-01.txt,3\r\n_1_bereshit-02.txt,1\r\n", encoding="utf-16")
            with self.assertRaises(ValueError):
                ax.export_app(alphabet, tokens, app_dir, Path(d) / "out", 2, min_mapped_pct=0)

    def test_best_join_needs_the_run_to_spell_the_word(self):
        m = [(None, 0, "פדה"), (None, 0, "צור"), (None, 0, "חסר")]
        self.assertEqual(ax.best_join(m, 0, 3, "פדהצור"), range(0, 2))
        self.assertEqual(ax.best_join(m, 0, 3, "שלום"), range(0))

    def test_pack_location_rejects_out_of_range(self):
        for bad in ((0, 1, 1, 1), (40, 1, 1, 1), (1, 1, 1, 0), (1, 1, 1, 256)):
            with self.assertRaises(ValueError):
                ax.pack_location(*bad)


APP_TEXT = Path(os.environ.get("APP_TEXT", Path.home() / "AndroidStudioProjects/BibleContestMultiPlatformApp"
                                "/shared/src/commonMain/moko-resources/assets/allChapters"))


@unittest.skipUnless(APP_TEXT.is_dir(), "the app's allChapters directory is not on this machine")
class RealAppTextTest(unittest.TestCase):
    """Golden check on the real app text: every chapter parses to the app's own verse count."""

    def test_verse_counts_match_the_apps_csv(self):
        self.assertEqual(ax.verse_count_mismatches(APP_TEXT, ax.read_app_text(APP_TEXT)), [])


if __name__ == "__main__":
    unittest.main()
