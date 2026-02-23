import unittest

import namekana
from scripts import build_country_dictionary_from_cldr as builder


class CountryNormalizationTests(unittest.TestCase):
    def test_normalize_country_key_strips_diacritics_and_punctuation(self) -> None:
        self.assertEqual(namekana.normalize_country_key("Côte d'Ivoire"), "cotedivoire")
        self.assertEqual(namekana.normalize_country_key("  U.S.A.  "), "usa")
        self.assertEqual(namekana.normalize_country_key("Türkiye"), "turkiye")
        self.assertEqual(namekana.normalize_country_key("Czech-Republic"), "czechrepublic")


class CountryLookupTests(unittest.TestCase):
    def setUp(self) -> None:
        namekana._COUNTRY_DICT_CACHE_SIGNATURE = None
        namekana._COUNTRY_DICT_CACHE_MAP = {}

    def test_parse_country_dictionary_value_string_and_object(self) -> None:
        parsed_string = namekana._parse_country_dictionary_value("アメリカ")
        self.assertEqual(parsed_string, {"official": "アメリカ", "display": "アメリカ"})

        parsed_object = namekana._parse_country_dictionary_value(
            {"official": "アメリカ合衆国", "display": "アメリカ"}
        )
        self.assertEqual(parsed_object, {"official": "アメリカ合衆国", "display": "アメリカ"})

        self.assertIsNone(namekana._parse_country_dictionary_value({"official": "", "display": "アメリカ"}))
        self.assertIsNone(namekana._parse_country_dictionary_value({"official": "アメリカ合衆国"}))

    def test_lookup_returns_display_and_official(self) -> None:
        us = namekana.dictionary_lookup_country("United States")
        self.assertIsNotNone(us)
        self.assertEqual(us["display"], "アメリカ")
        self.assertEqual(us["official"], "アメリカ合衆国")
        self.assertEqual(namekana.dictionary_lookup_country("usa"), us)
        self.assertEqual(namekana.dictionary_lookup_country("U.S."), us)

        hk = namekana.dictionary_lookup_country("hong kong")
        self.assertIsNotNone(hk)
        self.assertEqual(hk["display"], "ホンコン")
        self.assertEqual(hk["official"], "中華人民共和国香港特別行政区")

        mo = namekana.dictionary_lookup_country("macau")
        self.assertIsNotNone(mo)
        self.assertEqual(mo["display"], "マカオ")
        self.assertEqual(mo["official"], "中華人民共和国マカオ特別行政区")

    def test_unknown_country_raises_error(self) -> None:
        with self.assertRaises(namekana.UnknownCountryError) as cm:
            namekana.transliterate_name("zzzzzz")
        self.assertEqual(str(cm.exception), namekana.INVALID_COUNTRY_MESSAGE)


class GeneratorTests(unittest.TestCase):
    def test_build_dictionary_from_mock_cldr_payloads(self) -> None:
        en_payload = {
            "main": {
                "en": {
                    "localeDisplayNames": {
                        "territories": {
                            "US": "United States",
                            "GB": "United Kingdom",
                            "TR": "Turkey",
                            "CI": "Côte d'Ivoire",
                            "CZ": "Czechia",
                        }
                    }
                }
            }
        }
        ja_payload = {
            "main": {
                "ja": {
                    "localeDisplayNames": {
                        "territories": {
                            "US": "アメリカ合衆国",
                            "GB": "イギリス",
                            "TR": "トルコ",
                            "CI": "コートジボワール",
                            "CZ": "チェコ",
                        }
                    }
                }
            }
        }

        en_map = builder.extract_territories(en_payload)
        ja_map = builder.extract_territories(ja_payload)
        out = builder.build_country_dictionary(en_map, ja_map)

        self.assertEqual(out["unitedstates"], "アメリカ合衆国")
        self.assertEqual(out["usa"], "アメリカ合衆国")
        self.assertEqual(out["uk"], "イギリス")
        self.assertEqual(out["turkiye"], "トルコ")
        self.assertEqual(out["cotedivoire"], "コートジボワール")
        self.assertEqual(out["czechrepublic"], "チェコ")


if __name__ == "__main__":
    unittest.main()
