#!/usr/bin/env python3
"""
Build KanaMe last-name dictionary JSON from a seed list by calling a running KanaMe backend.

Inputs:
  - names file: one surname per line (UTF-8). Lines starting with # are ignored.
  - optional existing dictionary JSON (normalize_key -> katakana) to skip already-known keys.

Outputs:
  - pretty JSON (normalize_key -> katakana)
  - optional JSONL (one object per line)
  - markdown report (duplicates/conflicts, failures)

Example:
  ./.venv/bin/python tools/build_last_name_dictionary_from_api.py \
    --names names/last_name_seed_5000.txt \
    --api http://127.0.0.1:8000 \
    --out data/last_name_dictionary.compiled.pretty.json \
    --jsonl data/last_name_dictionary.compiled.jsonl \
    --report data/last_name_dictionary.report.md
"""
from __future__ import annotations

import argparse
import concurrent.futures as futures
import json
import re
import sys
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import requests


def strip_diacritics(s: str) -> str:
    return "".join(ch for ch in unicodedata.normalize("NFKD", s) if not unicodedata.combining(ch))


_key_re = re.compile(r"[^a-z]")


def normalize_key(name: str) -> str:
    s = strip_diacritics(name).lower()
    s = _key_re.sub("", s)
    return s


def iter_names(path: Path) -> Iterable[str]:
    for raw in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        yield line


@dataclass(frozen=True)
class Result:
    input_name: str
    key: str
    katakana: Optional[str]
    ok: bool
    source: Optional[str] = None
    warning: Optional[str] = None
    error: Optional[str] = None


def call_api(api_base: str, name: str, timeout: float) -> Result:
    key = normalize_key(name)
    if not key:
        return Result(input_name=name, key="", katakana=None, ok=False, error="empty_normalized_key")
    url = f"{api_base.rstrip('/')}/transliterate"
    try:
        r = requests.get(url, params={"name": name}, timeout=timeout)
        r.raise_for_status()
        data = r.json()
        kata = data.get("katakana")
        if not isinstance(kata, str) or not kata.strip():
            return Result(input_name=name, key=key, katakana=None, ok=False, error="missing_katakana")
        return Result(
            input_name=name,
            key=key,
            katakana=kata.strip(),
            ok=True,
            source=data.get("source"),
            warning=data.get("warning"),
        )
    except requests.RequestException as e:
        return Result(input_name=name, key=key, katakana=None, ok=False, error=f"request_error:{type(e).__name__}")
    except ValueError:
        return Result(input_name=name, key=key, katakana=None, ok=False, error="json_decode_error")


def load_existing(path: Optional[Path]) -> Dict[str, str]:
    if not path:
        return {}
    if not path.exists():
        return {}
    try:
        obj = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(obj, dict):
            out = {}
            for k, v in obj.items():
                if isinstance(k, str) and isinstance(v, str) and k and v:
                    out[k] = v
            return out
    except Exception:
        return {}
    return {}


def write_pretty_json(path: Path, mapping: Dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(mapping, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_jsonl(path: Path, mapping: Dict[str, str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for k in sorted(mapping.keys()):
            f.write(json.dumps({"key": k, "katakana": mapping[k]}, ensure_ascii=False) + "\n")


def write_report(path: Path, *, total: int, ok: int, failed: List[Result], conflicts: List[Tuple[str, str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: List[str] = []
    lines.append("# Last-name dictionary build report")
    lines.append("")
    lines.append(f"- Total input lines: {total}")
    lines.append(f"- Successful: {ok}")
    lines.append(f"- Failed: {len(failed)}")
    lines.append(f"- Conflicts (same key, different katakana): {len(conflicts)}")
    lines.append("")
    if conflicts:
        lines.append("## Conflicts")
        lines.append("")
        lines.append("| key | kept | dropped |")
        lines.append("|---|---|---|")
        for key, kept, dropped in conflicts[:200]:
            lines.append(f"| `{key}` | {kept} | {dropped} |")
        if len(conflicts) > 200:
            lines.append("")
            lines.append(f"... ({len(conflicts)-200} more conflicts omitted)")
        lines.append("")
    if failed:
        lines.append("## Failures")
        lines.append("")
        lines.append("| input | key | error |")
        lines.append("|---|---|---|")
        for r in failed[:400]:
            lines.append(f"| `{r.input_name}` | `{r.key}` | `{r.error}` |")
        if len(failed) > 400:
            lines.append("")
            lines.append(f"... ({len(failed)-400} more failures omitted)")
        lines.append("")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--names", required=True, help="Path to surnames list (one per line).")
    ap.add_argument("--api", required=True, help="KanaMe backend base URL, e.g. http://127.0.0.1:8000")
    ap.add_argument("--timeout", type=float, default=8.0, help="Per-request timeout seconds.")
    ap.add_argument("--workers", type=int, default=24, help="Concurrent request workers.")
    ap.add_argument("--out", required=True, help="Output pretty JSON path (normalize_key -> katakana).")
    ap.add_argument("--jsonl", default="", help="Optional output JSONL path.")
    ap.add_argument("--report", default="", help="Optional output report markdown path.")
    ap.add_argument("--existing", default="", help="Optional existing pretty JSON to skip keys already present.")
    ap.add_argument("--max", type=int, default=5000, help="Maximum number of unique keys to include.")
    args = ap.parse_args()

    names_path = Path(args.names)
    if not names_path.exists():
        print(f"names file not found: {names_path}", file=sys.stderr)
        return 2

    existing = load_existing(Path(args.existing)) if args.existing else {}
    mapping: Dict[str, str] = dict(existing)

    seen_inputs = 0
    pending: List[str] = []
    for nm in iter_names(names_path):
        seen_inputs += 1
        k = normalize_key(nm)
        if not k:
            continue
        if k in mapping:
            continue
        pending.append(nm)

    # Respect max unique keys
    remaining = max(0, args.max - len(mapping))
    if remaining <= 0:
        write_pretty_json(Path(args.out), mapping)
        if args.jsonl:
            write_jsonl(Path(args.jsonl), mapping)
        if args.report:
            write_report(Path(args.report), total=seen_inputs, ok=len(mapping), failed=[], conflicts=[])
        print(f"Wrote: {args.out} ({len(mapping)} entries). Nothing to do.")
        return 0
    pending = pending[:remaining]

    failed: List[Result] = []
    conflicts: List[Tuple[str, str, str]] = []

    t0 = time.time()
    with futures.ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        futs = [ex.submit(call_api, args.api, nm, args.timeout) for nm in pending]
        for fut in futures.as_completed(futs):
            r = fut.result()
            if not r.ok or not r.key or not r.katakana:
                failed.append(r)
                continue
            if r.key in mapping and mapping[r.key] != r.katakana:
                conflicts.append((r.key, mapping[r.key], r.katakana))
                continue
            mapping[r.key] = r.katakana

    dt = time.time() - t0
    out_path = Path(args.out)
    write_pretty_json(out_path, mapping)

    if args.jsonl:
        write_jsonl(Path(args.jsonl), mapping)
    if args.report:
        write_report(Path(args.report), total=seen_inputs, ok=len(mapping), failed=failed, conflicts=conflicts)

    print(f"Wrote: {out_path} ({len(mapping)} entries) in {dt:.1f}s. Failed: {len(failed)}. Conflicts: {len(conflicts)}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
