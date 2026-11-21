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
            run(Path(d), output, self.REV)
            self.assertEqual(len(output.read_text(encoding="utf-8").splitlines()), 2)

    def test_rejects_unpinned_revision(self):
        with tempfile.TemporaryDirectory() as d:
            with self.assertRaisesRegex(ValueError, "40-character"):
                run(Path(d), Path(d) / "out.jsonl", "main")


if __name__ == "__main__":
    unittest.main()
