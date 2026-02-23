#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import re
from collections import Counter
from typing import Any, Dict, Tuple

COUNTRY_DICT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "countries", "country_dictionary.json")

SUFFIXES = [
    "ミンシュキョウワコク",
    "ジンミンキョウワコク",
    "キョウワコク",
    "オウコク",
    "ゴウシュウコク",
    "レンポウ",
    "トクベツギョウセイク",
    "コク",
]

EXCEPTION_DISPLAY_OVERRIDES = {
    "china": "チュウゴク",
    "southkorea": "カンコク",
    "korea": "カンコク",
    "northkorea": "キタチョウセン",
    "japan": "ニホン",
    "hongkong": "ホンコン",
    "hongkongsarchina": "ホンコン",
    "macao": "マカオ",
    "macaosarchina": "マカオ",
    "macau": "マカオ",
    "unitedstates": "アメリカ",
    "usa": "アメリカ",
    "us": "アメリカ",
    "unitedstatesofamerica": "アメリカ",
    "russia": "ロシア",
    "russianfederation": "ロシア",
}

KANJI_READING_MAP = {
    "中華人民共和国": "チュウカジンミンキョウワコク",
    "特別行政区": "トクベツギョウセイク",
    "人民共和国": "ジンミンキョウワコク",
    "民主共和国": "ミンシュキョウワコク",
    "共和国": "キョウワコク",
    "合衆国": "ゴウシュウコク",
    "首長国": "シュチョウコク",
    "連邦": "レンポウ",
    "王国": "オウコク",
    "自治区": "ジチク",
    "領有": "リョウユウ",
    "諸島": "ショトウ",
    "列島": "レットウ",
    "北朝鮮": "キタチョウセン",
    "韓国": "カンコク",
    "中国": "チュウゴク",
    "日本": "ニホン",
    "台湾": "タイワン",
    "中華": "チュウカ",
    "人民": "ジンミン",
    "民主": "ミンシュ",
    "中央": "チュウオウ",
    "赤道": "セキドウ",
    "南": "ミナミ",
    "北": "キタ",
    "東": "ヒガシ",
    "西": "ニシ",
    "仏": "フツ",
    "英": "エイ",
    "米": "ベイ",
    "領": "リョウ",
    "島": "シマ",
    "国": "コク",
    "市": "シ",
    "区": "ク",
    "及び": "オヨビ",
    "小": "ショウ",
    "離": "リ",
    "極": "キョク",
}


def parse_entry_value(raw_value: Any) -> Tuple[str, str]:
    if isinstance(raw_value, str):
        val = raw_value.strip()
        return val, val
    if isinstance(raw_value, dict):
        official = str(raw_value.get("official", "")).strip()
        display = str(raw_value.get("display", "")).strip()
        return official, display
    return "", ""


def _pykakasi_converter():
    try:
        from pykakasi import kakasi  # type: ignore

        kk = kakasi()
        conv = kk.getConverter()
        return conv.do
    except Exception:
        return None


def _fallback_katakana(text: str) -> str:
    out = text
    for src in sorted(KANJI_READING_MAP.keys(), key=len, reverse=True):
        out = out.replace(src, KANJI_READING_MAP[src])

    out = out.replace("（", "").replace("）", "").replace("(", "").replace(")", "")
    out = re.sub(r"\s+", "", out)

    # keep Katakana, prolonged sound mark, middle dot, ASCII letters/digits and common separators.
    out = re.sub(r"[^\u30A0-\u30FFー・A-Za-z0-9\-]", "", out)
    return out


def katakanaize_official(official: str) -> str:
    converter = _pykakasi_converter()
    if converter is not None:
        converted = converter(official)
        converted = converted.replace("（", "").replace("）", "").replace("(", "").replace(")", "")
        converted = re.sub(r"\s+", "", converted)
        return converted
    return _fallback_katakana(official)


def build_display_candidate(full_katakana_official: str) -> str:
    if not full_katakana_official:
        return ""

    if "シマ" in full_katakana_official or "ショトウ" in full_katakana_official or "レットウ" in full_katakana_official:
        return full_katakana_official

    for suffix in SUFFIXES:
        if full_katakana_official.endswith(suffix) and len(full_katakana_official) > len(suffix):
            return full_katakana_official[: -len(suffix)]

    return full_katakana_official


def rewrite_dictionary(raw: Dict[str, Any]) -> Dict[str, Any]:
    entries: Dict[str, Dict[str, Any]] = {}

    for key, value in raw.items():
        official, display = parse_entry_value(value)
        if not official:
            continue
        entries[key] = {
            "official": official,
            "display": display or official,
            "was_object": isinstance(value, dict),
        }

    # required additional aliases
    entries.setdefault("korea", {"official": "韓国", "display": "韓国", "was_object": True})
    entries.setdefault("russianfederation", {"official": "ロシア", "display": "ロシア", "was_object": True})

    full_kata: Dict[str, str] = {}
    candidate: Dict[str, str] = {}
    for key, info in entries.items():
        full = katakanaize_official(info["official"])
        full_kata[key] = full
        candidate[key] = build_display_candidate(full)

    # collision avoidance for non-exception keys
    non_exception = {k: v for k, v in candidate.items() if k not in EXCEPTION_DISPLAY_OVERRIDES}
    counts = Counter(non_exception.values())

    resolved_display: Dict[str, str] = {}
    for key in entries.keys():
        if key in EXCEPTION_DISPLAY_OVERRIDES:
            resolved_display[key] = EXCEPTION_DISPLAY_OVERRIDES[key]
            continue
        cand = candidate[key]
        if cand and counts[cand] > 1:
            resolved_display[key] = full_kata[key]
        else:
            resolved_display[key] = cand or full_kata[key] or entries[key]["official"]

    out: Dict[str, Any] = {}
    for key in sorted(entries.keys()):
        official = entries[key]["official"]
        display = resolved_display[key]
        force_object = key in EXCEPTION_DISPLAY_OVERRIDES or key in {"korea", "russianfederation"}
        if entries[key]["was_object"] or force_object or official != display:
            out[key] = {"official": official, "display": display}
        else:
            out[key] = official

    return out


def main() -> int:
    with open(COUNTRY_DICT_PATH, "r", encoding="utf-8") as fh:
        payload = json.load(fh)

    if not isinstance(payload, dict):
        raise SystemExit("country dictionary must be a JSON object")

    rewritten = rewrite_dictionary(payload)
    with open(COUNTRY_DICT_PATH, "w", encoding="utf-8") as fh:
        json.dump(rewritten, fh, ensure_ascii=False, indent=2, sort_keys=True)
        fh.write("\n")

    print(f"rewrote {len(rewritten)} entries: {COUNTRY_DICT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
