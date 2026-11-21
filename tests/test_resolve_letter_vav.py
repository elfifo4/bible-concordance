import tempfile
import unittest
from pathlib import Path
from scripts.resolve_letter_vav import load_lexicon, resolve

NS = "http://openscriptures.github.com/morphhb/namespace"

class VavLexiconTests(unittest.TestCase):
    def test_aug_join_and_conjunction_exclusion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "LexicalIndex.xml").write_text(
                f'<index xmlns="{NS}"><part><entry id="aaa"><w>וָו</w>'
                '<xref strong="2053"/></entry><entry id="bbb"><w>אָמַר</w>'
                '<xref strong="559"/></entry></part></index>', encoding="utf-8")
            (root / "AugIndex.xml").write_text(
                f'<index xmlns="{NS}"><w aug="2053">aaa</w>'
                '<w aug="559">bbb</w></index>', encoding="utf-8")
            entries, strong, aug = load_lexicon(root)
            rows = [
                {"strongNumber": "2053", "conjunctionPrefixTokens": 0},
                {"strongNumber": "0559", "conjunctionPrefixTokens": 5},
            ]
            result = resolve(rows, entries, strong, aug)
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0]["headword"], "וָו")
            self.assertEqual(result[0]["joinMethod"], "aug-index")
            self.assertEqual(result[0]["reviewStatus"], "needs-human-review")

    def test_ambiguous_strong_not_guessed(self):
        entries = {"one": "וָו", "two": "וְ"}
        strong = {"1": {"one", "two"}}
        self.assertEqual(resolve([{"strongNumber": "1"}], entries, strong, {}), [])

if __name__ == "__main__":
    unittest.main()
