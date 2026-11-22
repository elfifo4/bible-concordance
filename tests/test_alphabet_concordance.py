import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from scripts.build_alphabet_concordance import LETTERS, generate

class AlphabetTests(unittest.TestCase):
    def test_alphabet_has_22_letters(self):
        self.assertEqual(len(LETTERS), 22)
        self.assertEqual(len(set(LETTERS)), 22)

    def test_aug_join_prefixes_and_unmapped_reporting(self):
        rows=[
            {"tokenId":"t1","verseId":"Gen.1.1","tokenPosition":1,"form":"וָו","readingType":"standard","lemmaRaw":"c/2053","morphRaw":"HC","source":{"sourceTokenId":"t1"}},
            {"tokenId":"t2","verseId":"Gen.1.2","tokenPosition":1,"form":"אב","readingType":"standard","lemmaRaw":"9999","morphRaw":"HN","source":{"sourceTokenId":"t2"}}
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/"tokens.jsonl"
            path.write_text("".join(json.dumps(x,ensure_ascii=False)+"\n" for x in rows),encoding="utf-8")
            with patch("scripts.build_alphabet_concordance.load_lexicon",return_value=({"del":"וָו"},{},{"2053":"del"})):
                data,unresolved=generate(path,Path(tmp),"ו")
            self.assertEqual(data["entryCount"],1)
            self.assertEqual(data["totalOccurrences"],1)
            self.assertEqual(data["entries"][0]["occurrences"][0]["tokenId"],"t1")
            self.assertEqual(unresolved["9999"]["reason"],"unmapped-strong")
            with patch("scripts.build_alphabet_concordance.load_lexicon",return_value=({"del":"וָו"},{},{"2053":"del"})):
                other,_=generate(path,Path(tmp),"א")
            self.assertEqual(other["entryCount"],0)

if __name__=="__main__":
    unittest.main()
