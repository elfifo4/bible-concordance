import json
import unittest
from pathlib import Path
from scripts.verify_letter_vav import compare

class VerifiedVavTests(unittest.TestCase):
    def test_checked_file_is_complete_and_unique(self):
        data = json.loads(Path("data/letter-vav-verified.json").read_text(encoding="utf-8"))
        self.assertEqual(len(data["entries"]), 10)
        self.assertEqual([e["strongNumber"] for e in data["entries"]],
                         [str(n) for n in range(2051, 2061)])
        self.assertTrue(all(e["headword"].startswith("ו") for e in data["entries"]))
        self.assertEqual(sum(e["tokenCount"] for e in data["entries"]), 31)

    def test_mismatch_fails(self):
        row = {"strongNumber": "2053", "headword": "וָו", "tokenCount": 13,
               "exampleVerse": "Exod.26.32", "lexiconEntryId": "del"}
        generated = {"entries": [{**row, "joinMethod": "aug-index",
                                  "conjunctionPrefixTokens": 0}]}
        self.assertEqual(compare(generated, {"entries": [row]}), 1)
        with self.assertRaises(ValueError):
            compare({"entries": [{**generated["entries"][0], "tokenCount": 14}]},
                    {"entries": [row]})

if __name__ == "__main__":
    unittest.main()
