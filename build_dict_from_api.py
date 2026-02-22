#!/usr/bin/env python3
"""
Build a KanaMe custom dictionary (english_name -> katakana) by calling your running backend API.

Assumes FastAPI endpoint:
  GET {API_BASE}/transliterate?name=...

Outputs a tab-separated file:
  <original_name>\t<katakana>

Usage:
  python build_dict_from_api.py --names names.txt --out dict_additions.txt --api http://127.0.0.1:8000

Optional:
  --existing dictionary_katakana.txt  (to skip already-present keys)
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlencode

import requests


def norm_key(s: str) -> str:
    s = s.strip().casefold()
    s = re.sub(r"\s+", " ", s)
    # Normalize common punctuation (keep basic letters/spaces)
    s = s.replace("’", "'").replace("＝", "=")
    s = re.sub(r"[·•]", " ", s)
    s = re.sub(r"[^\w\s'\-]", "", s, flags=re.UNICODE)
    s = re.sub(r"[-'\s]+", " ", s).strip()
    return s


def load_existing(path: Path) -> set[str]:
    existing: set[str] = set()
    if not path.exists():
        return existing
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if len(parts) < 2:
            parts = line.split()
        if not parts:
            continue
        existing.add(norm_key(parts[0]))
    return existing


def call_api(api_base: str, name: str, timeout: float) -> dict:
    url = api_base.rstrip("/") + "/transliterate"
    params = {"name": name}
    full = url + "?" + urlencode(params)
    resp = requests.get(full, timeout=timeout, headers={"Accept": "application/json"})
    resp.raise_for_status()
    try:
        return resp.json()
    except json.JSONDecodeError:
        raise RuntimeError(f"Non-JSON response for {name!r}: {resp.text[:120]!r}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--names", required=True, help="Path to names list (one per line)")
    ap.add_argument("--out", required=True, help="Output TSV path")
    ap.add_argument("--api", default="http://127.0.0.1:8000", help="Backend base URL")
    ap.add_argument("--timeout", type=float, default=3.0, help="HTTP timeout seconds")
    ap.add_argument("--existing", default="", help="Existing dict TSV to skip duplicates")
    args = ap.parse_args()

    names_path = Path(args.names)
    out_path = Path(args.out)

    if not names_path.exists():
        print(f"names file not found: {names_path}", file=sys.stderr)
        return 2

    existing = load_existing(Path(args.existing)) if args.existing else set()

    out_lines = []
    skipped = 0
    failed = 0

    for raw in names_path.read_text(encoding="utf-8").splitlines():
        name = raw.strip()
        if not name or name.startswith("#"):
            continue
        key = norm_key(name)
        if key in existing:
            skipped += 1
            continue
        try:
            data = call_api(args.api, name=name, timeout=args.timeout)
            katakana = (data.get("katakana") or "").strip()
            if not katakana:
                failed += 1
                continue
            out_lines.append(f"{name}\t{katakana}")
        except Exception:
            failed += 1

    out_path.write_text("\n".join(out_lines) + ("\n" if out_lines else ""), encoding="utf-8")
    print(f"Wrote: {out_path} ({len(out_lines)} entries). Skipped: {skipped}. Failed: {failed}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
