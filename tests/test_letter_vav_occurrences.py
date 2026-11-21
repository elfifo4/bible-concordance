import json
import tempfile
import unittest
from pathlib import Path
from scripts.build_letter_vav_occurrences import build, lemma_numbers

class OccurrenceTests(unittest.TestCase):
    def test_lemma_parsing(self):
        self.assertEqual(lemma_numbers("c/2053 b/559"), {"2053", "559"})
        self.assertEqual(lemma_numbers(None), set())

    def test_complete_occurrences_and_provenance(self):
        inventory = {"source": {"morphhbRevision": "x"}, "entries": [
            {"strongNumber": "2053", "headword": "וָו", "tokenCount": 2,
             "exampleVerse": "Exod.26.32", "lexiconEntryId": "del"}]}
        rows = [
            {"tokenId": "a", "verseId": "Exod.26.32", "tokenPosition": 1,
             "form": "וָו", "readingType": "standard", "lemmaRaw": "2053",
             "morphRaw": "HN", "source": {"sourceTokenId": "a"}},
            {"tokenId": "b", "verseId": "Exod.26.33", "tokenPosition": 2,
             "form": "וָו", "readingType": "ketiv", "lemmaRaw": "2053",
             "morphRaw": "HN", "source": {"sourceTokenId": "b"}}]
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "tokens.jsonl"
            path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
            result = build(path, inventory)
            self.assertEqual(result["totalOccurrences"], 2)
            self.assertEqual([o["tokenId"] for o in result["entries"][0]["occurrences"]], ["a", "b"])
            with self.assertRaisesRegex(ValueError, "expected 3"):
                build(path, {**inventory, "entries": [{**inventory["entries"][0], "tokenCount": 3}]})

if __name__ == "__main__":
    unittest.main()
