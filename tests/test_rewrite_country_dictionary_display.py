import unittest

from scripts import rewrite_country_dictionary_display as rewrite


class RewriteCountryDictionaryDisplayTests(unittest.TestCase):
    def test_island_terms_are_preserved_and_suffixes_are_removed(self) -> None:
        self.assertEqual(rewrite.build_display_candidate("ミクロネシアレンポウ"), "ミクロネシア")
        self.assertEqual(rewrite.build_display_candidate("マーシャルショトウ"), "マーシャルショトウ")
        self.assertEqual(rewrite.build_display_candidate("ノーフォークシマ"), "ノーフォークシマ")

    def test_exception_overrides_are_applied(self) -> None:
        fixture = {
            "china": "中国",
            "japan": "日本",
            "usa": {"official": "アメリカ合衆国", "display": "アメリカ合衆国"},
            "hongkong": {"official": "中華人民共和国香港特別行政区", "display": "中華人民共和国香港特別行政区"},
        }
        out = rewrite.rewrite_dictionary(fixture)

        self.assertEqual(out["china"], {"official": "中国", "display": "チュウゴク"})
        self.assertEqual(out["japan"], {"official": "日本", "display": "ニホン"})
        self.assertEqual(out["usa"], {"official": "アメリカ合衆国", "display": "アメリカ"})
        self.assertEqual(out["hongkong"], {"official": "中華人民共和国香港特別行政区", "display": "ホンコン"})
        self.assertIn("korea", out)
        self.assertIn("russianfederation", out)

    def test_collision_reverts_to_full_official_katakana(self) -> None:
        fixture = {
            "alpha_republic": "アルファ共和国",
            "alpha_kingdom": "アルファ王国",
        }
        out = rewrite.rewrite_dictionary(fixture)

        self.assertNotEqual(out["alpha_republic"], "アルファ")
        self.assertNotEqual(out["alpha_kingdom"], "アルファ")
        self.assertNotEqual(out["alpha_republic"], out["alpha_kingdom"])


if __name__ == "__main__":
    unittest.main()
