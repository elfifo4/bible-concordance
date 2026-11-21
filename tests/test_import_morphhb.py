import tempfile
import unittest
from pathlib import Path

from scripts.import_morphhb import iter_tokens, run


class MorphHBImportTests(unittest.TestCase):
    REV = "a" * 40

    def test_milestone_verses_and_words(self):
        xml = """<osis xmlns="http://www.bibletechnologies.net/2003/OSIS/namespace">
        <verse osisID="Gen.1.1" sID="Gen.1.1"/>
        <w id="01abc" lemma="7225" morph="HNcfsa">בְּרֵאשִׁית</w>
        <w id="01def" lemma="1254" morph="HVqp3ms">בָּרָא</w>
        <verse eID="Gen.1.1"/>
        </osis>"""
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "Gen.xml"
            path.write_text(xml, encoding="utf-8")
            items = list(iter_tokens(path, self.REV))
            self.assertEqual(len(items), 2)
            self.assertEqual([i["tokenPosition"] for i in items], [1, 2])
            self.assertEqual(items[0]["verseId"], "Gen.1.1")
            self.assertEqual(items[0]["tokenId"], "01abc")
            output = Path(d) / "tokens.jsonl"
            run(Path(d), output, self.REV, expected_books=1)
            self.assertEqual(len(output.read_text(encoding="utf-8").splitlines()), 2)

    def test_incomplete_corpus_preserves_output(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "Gen.xml"
            path.write_text('<osis><verse osisID="Gen.1.1" sID="Gen.1.1"/><w id="01abc">א</w><verse eID="Gen.1.1"/></osis>')
            output = Path(d) / "tokens.jsonl"
            output.write_text("previous")
            with self.assertRaisesRegex(ValueError, "Expected 39"):
                run(Path(d), output, self.REV)
            self.assertEqual(output.read_text(), "previous")

    def test_mismatched_verse_preserves_output(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "Gen.xml"
            path.write_text('<osis><verse osisID="Gen.1.1" sID="Gen.1.1"/><w id="01abc">א</w><verse eID="Gen.1.2"/></osis>')
            output = Path(d) / "tokens.jsonl"
            output.write_text("previous")
            with self.assertRaisesRegex(ValueError, "unmatched verse"):
                run(Path(d), output, self.REV, expected_books=1)
            self.assertEqual(output.read_text(), "previous")

    def test_word_outside_verse(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "Gen.xml"
            path.write_text('<osis><w id="01abc">א</w></osis>')
            with self.assertRaisesRegex(ValueError, "outside verse"):
                list(iter_tokens(path, self.REV))

    def test_qere_does_not_count_as_extra_written_word(self):
        xml = ('<osis><verse osisID="Ruth.1.8" sID="Ruth.1.8"/>'
               '<w id="08abc" type="x-ketiv" lemma="6213">יעשה</w>'
               '<note type="variant"><catchWord>יעשה</catchWord>'
               '<rdg type="x-qere"><w lemma="6213">יַעַשׂ</w></rdg></note>'
               '<w id="08def" lemma="3068">יהוה</w>'
               '<verse eID="Ruth.1.8"/></osis>')
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "Ruth.xml"
            path.write_text(xml, encoding="utf-8")
            stats = {}
            items = list(iter_tokens(path, self.REV, stats))
            self.assertEqual(len(items), 2)
            self.assertEqual([i["tokenPosition"] for i in items], [1, 2])
            self.assertEqual(items[0]["readingType"], "ketiv")
            self.assertEqual(stats["ketivWords"], 1)
            self.assertEqual(stats["qereWords"], 1)

    def test_rejects_unpinned_revision(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "40-character"):
                run(Path(d), Path(d) / "out.jsonl", "main")


if __name__ == "__main__":
    unittest.main()
