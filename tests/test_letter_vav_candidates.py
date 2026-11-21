import unittest
from scripts.letter_vav_candidates import candidates

class LetterVavCandidateTests(unittest.TestCase):
    def test_conjunction_is_not_headword(self):
        rows = [
            {"lemmaRaw": "c/0559", "verseId": "Gen.1.1"},
            {"lemmaRaw": "b/c/0559", "verseId": "Gen.1.2"},
            {"lemmaRaw": "0559", "verseId": "Gen.1.3"},
        ]
        entries = candidates(rows)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["strongNumber"], "0559")
        self.assertEqual(entries[0]["tokenCount"], 3)
        self.assertEqual(entries[0]["conjunctionPrefixTokens"], 2)
        self.assertIsNone(entries[0]["headword"])
        self.assertEqual(entries[0]["reviewStatus"], "needs-lexicon-join")

    def test_unknown_and_multiple_lemmas(self):
        entries = candidates([
            {"lemmaRaw": None, "verseId": "Gen.1.1"},
            {"lemmaRaw": "c/0123 0456", "verseId": "Gen.1.2"},
            {"lemmaRaw": "unknown", "verseId": "Gen.1.3"},
        ])
        self.assertEqual([e["strongNumber"] for e in entries], ["0123", "0456"])
        self.assertEqual(entries[0]["conjunctionPrefixTokens"], 1)
        self.assertEqual(entries[1]["conjunctionPrefixTokens"], 0)

if __name__ == "__main__":
    unittest.main()
