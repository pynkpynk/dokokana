#!/usr/bin/env python3
"""
Build DokoKana country dictionary (normalized English key -> Japanese name).

Primary source:
- CLDR territories JSON from unicode-org/cldr-json raw URLs

Fallback for offline environments:
- Node Intl.DisplayNames (CLDR/ICU-backed) for region names

Note:
- By default this script keeps Japanese names as provided (kanji/katakana mixed).
- If `pykakasi` is installed and `--katakana-only` is passed, it converts Japanese
  names to katakana output in this build step only.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import unicodedata
import urllib.request
from typing import Any, Dict, Mapping, Optional

CLDR_EN_URL = (
    "https://raw.githubusercontent.com/unicode-org/cldr-json/main/"
    "cldr-json/cldr-localenames-full/main/en/territories.json"
)
CLDR_JA_URL = (
    "https://raw.githubusercontent.com/unicode-org/cldr-json/main/"
    "cldr-json/cldr-localenames-full/main/ja/territories.json"
)

# Codes returned by CLDR/Intl that are not part of the active ISO-3166-1 alpha-2 set.
EXCLUDED_REGION_CODES = {
    "AC",
    "AN",
    "BU",
    "CP",
    "CQ",
    "CS",
    "DD",
    "DG",
    "DY",
    "EA",
    "EU",
    "EZ",
    "FX",
    "HV",
    "IC",
    "NH",
    "QO",
    "RH",
    "SU",
    "TA",
    "TP",
    "UK",
    "UN",
    "VD",
    "XA",
    "XB",
    "XK",
    "YD",
    "YU",
    "ZR",
    "ZZ",
}

MAJOR_ALIASES_TO_CODE = {
    "usa": "US",
    "us": "US",
    "unitedstates": "US",
    "unitedstatesofamerica": "US",
    "u.s.": "US",
    "u.s.a.": "US",
    "uk": "GB",
    "greatbritain": "GB",
    "unitedkingdom": "GB",
    "britain": "GB",
    "uae": "AE",
    "unitedarabemirates": "AE",
    "turkiye": "TR",
    "turkey": "TR",
    "ivorycoast": "CI",
    "cotedivoire": "CI",
    "cote d'ivoire": "CI",
    "czechrepublic": "CZ",
    "czechia": "CZ",
}


def normalize_country_key(s: str) -> str:
    text = (s or "").strip().lower()
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]", "", text)


def fetch_json(url: str, timeout: float = 20.0) -> Dict[str, Any]:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "DokoKanaCountryBuilder/1.0",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def extract_territories(payload: Mapping[str, Any]) -> Dict[str, str]:
    if not isinstance(payload, Mapping):
        return {}
    main = payload.get("main")
    if not isinstance(main, Mapping) or not main:
        return {}

    locale_data = next(iter(main.values()))
    if not isinstance(locale_data, Mapping):
        return {}

    territories = (
        locale_data.get("localeDisplayNames", {}).get("territories", {})
        if isinstance(locale_data.get("localeDisplayNames"), Mapping)
        else {}
    )
    if not isinstance(territories, Mapping):
        return {}

    out: Dict[str, str] = {}
    for code, name in territories.items():
        if not isinstance(code, str) or not isinstance(name, str):
            continue
        code = code.upper()
        if not re.fullmatch(r"[A-Z]{2}", code):
            continue
        if code in EXCLUDED_REGION_CODES:
            continue
        clean_name = name.strip()
        if not clean_name:
            continue
        out[code] = clean_name
    return out


def _katakana_converter(enabled: bool):
    if not enabled:
        return None
    try:
        from pykakasi import kakasi  # type: ignore
    except Exception:
        return None

    kk = kakasi()
    conv = kk.getConverter()

    def to_katakana(text: str) -> str:
        return conv.do(text)

    return to_katakana


def _build_from_intl_fallback() -> Dict[str, Dict[str, str]]:
    js = r"""
const excluded = new Set(JSON.parse(process.argv[1]));
const en = new Intl.DisplayNames(['en'], { type: 'region' });
const ja = new Intl.DisplayNames(['ja'], { type: 'region' });
const out = {};
for (let i = 65; i <= 90; i++) {
  for (let j = 65; j <= 90; j++) {
    const code = String.fromCharCode(i) + String.fromCharCode(j);
    if (excluded.has(code)) continue;
    let enName;
    let jaName;
    try {
      enName = en.of(code);
      jaName = ja.of(code);
    } catch {
      continue;
    }
    if (!enName || !jaName) continue;
    if (enName === code && jaName === code) continue;
    out[code] = { en: enName, ja: jaName };
  }
}
process.stdout.write(JSON.stringify(out));
"""
    proc = subprocess.run(
        ["node", "-e", js, json.dumps(sorted(EXCLUDED_REGION_CODES))],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(proc.stdout)
    if not isinstance(payload, dict):
        raise RuntimeError("Intl fallback produced invalid payload")
    return payload


def build_country_dictionary(
    en_territories: Mapping[str, str],
    ja_territories: Mapping[str, str],
    katakana_only: bool = False,
) -> Dict[str, str]:
    converter = _katakana_converter(katakana_only)
    out: Dict[str, str] = {}
    code_to_kana: Dict[str, str] = {}

    codes = sorted(set(en_territories).intersection(ja_territories))
    for code in codes:
        en_name = en_territories.get(code, "").strip()
        ja_name = ja_territories.get(code, "").strip()
        if not en_name or not ja_name:
            continue

        key = normalize_country_key(en_name)
        if not key:
            continue

        value = converter(ja_name) if converter else ja_name
        out[key] = value
        code_to_kana[code] = value

    seed_major_aliases(out, code_to_kana)
    return out


def seed_major_aliases(out: Dict[str, str], code_to_kana: Mapping[str, str]) -> None:
    for alias, code in MAJOR_ALIASES_TO_CODE.items():
        key = normalize_country_key(alias)
        value = code_to_kana.get(code)
        if key and value:
            out[key] = value


def write_dictionary(path: str, mapping: Mapping[str, str]) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(dict(sorted(mapping.items())), fh, ensure_ascii=False, indent=2)
        fh.write("\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build countries/country_dictionary.json from CLDR")
    parser.add_argument("--out", default="countries/country_dictionary.json")
    parser.add_argument("--katakana-only", action="store_true")
    parser.add_argument("--no-intl-fallback", action="store_true")
    args = parser.parse_args()

    en_map: Dict[str, str]
    ja_map: Dict[str, str]

    try:
        en_payload = fetch_json(CLDR_EN_URL)
        ja_payload = fetch_json(CLDR_JA_URL)
        en_map = extract_territories(en_payload)
        ja_map = extract_territories(ja_payload)
    except Exception:
        if args.no_intl_fallback:
            raise
        intl = _build_from_intl_fallback()
        en_map = {k: v["en"] for k, v in intl.items() if isinstance(v, dict) and "en" in v and "ja" in v}
        ja_map = {k: v["ja"] for k, v in intl.items() if isinstance(v, dict) and "en" in v and "ja" in v}

    dictionary = build_country_dictionary(en_map, ja_map, katakana_only=args.katakana_only)
    write_dictionary(args.out, dictionary)
    print(f"wrote {len(dictionary)} entries to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
