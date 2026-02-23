import os
import re
import json
import unicodedata
from functools import lru_cache
from typing import Any, Dict, Optional, Tuple

try:
    import requests
except Exception:  # pragma: no cover - startup fallback when optional dependency is absent
    requests = None

# Env toggles
_WIKIDATA_ENABLED = (
    os.getenv("NAMEKANA_WIKIDATA", "1").lower() not in {"0", "false", "no", "off"}
    and os.getenv("NAMEKANA_DISABLE_WIKIDATA", "0").lower() not in {"1", "true", "yes", "on"}
)
_WIKIDATA_TIMEOUT = float(os.getenv("NAMEKANA_WIKIDATA_TIMEOUT", "6"))
_USER_AGENT = os.getenv("NAMEKANA_USER_AGENT", "NameKanaMVP/0.1")
_DICT_DIR = (os.getenv("NAMEKANA_DICT_DIR", "names") or "names").strip() or "names"
_DICTIONARY_DISABLED = os.getenv("NAMEKANA_DISABLE_DICTIONARY", "0").lower() in {"1", "true", "yes", "on"}
try:
    _WIKIDATA_MAX_CANDIDATES = max(1, int(os.getenv("NAMEKANA_WD_MAX_CANDIDATES", "8")))
except ValueError:
    _WIKIDATA_MAX_CANDIDATES = 8
_WIKIDATA_ALLOWED_P31 = {
    part.strip()
    for part in (os.getenv("NAMEKANA_WD_ALLOWED_P31", "Q5,Q202444,Q101352") or "").split(",")
    if part.strip()
}

# Katakana -> Hiragana
_KATA_START = 0x30A1
_KATA_END = 0x30F6
_KATA_TO_HIRA_OFFSET = 0x60

# Accept kana-like labels
_KANA_LIKE_RE = re.compile(r"^[\u3040-\u309F\u30A0-\u30FF\u30FC\u30FB\s＝=]+$")

_DICT_EXTENSIONS = {".txt", ".tsv", ".csv"}
_DICT_CACHE_SIGNATURE = None
_DICT_CACHE_MAP: Dict[str, str] = {}
_DICT_CACHE_FIRST_NAME_MAP: Dict[str, str] = {}
_DICT_CACHE_LAST_NAME_MAP: Dict[str, str] = {}
_COUNTRY_DICT_CACHE_SIGNATURE = None
_COUNTRY_DICT_CACHE_MAP: Dict[str, Dict[str, str]] = {}
_WD_QID_CACHE_MAX = 2048
_WD_QID_ALLOWED_CACHE: Dict[str, bool] = {}
_WD_QID_KANA_CACHE: Dict[str, Optional[str]] = {}

INVALID_COUNTRY_MESSAGE = "Please enter a valid country name."


class UnknownCountryError(ValueError):
    pass


def kata_to_hira(text: str) -> str:
    out = []
    for ch in text:
        code = ord(ch)
        if _KATA_START <= code <= _KATA_END:
            out.append(chr(code - _KATA_TO_HIRA_OFFSET))
        else:
            out.append(ch)
    return "".join(out)


def normalize_name(name: str) -> str:
    name = name.strip()
    name = name.replace("’", "'").replace("`", "'")
    name = re.sub(r"\s+", " ", name)
    return name


def split_tokens(name: str) -> list[str]:
    name = normalize_name(name)
    name = re.sub(r"[-._/]", " ", name)
    name = name.replace("'", " ")
    name = re.sub(r"\s+", " ", name).strip()
    return [t for t in name.split(" ") if t]


def dictionary_key(name: str) -> str:
    key = normalize_name(name).casefold()
    key = key.replace("’", "'").replace("`", "'")
    key = re.sub(r"[^\w\s'\-]", " ", key, flags=re.UNICODE)
    key = re.sub(r"[\s'\-]+", " ", key).strip()
    return key


def normalize_country_key(s: str) -> str:
    text = (s or "").strip().lower()
    if not text:
        return ""
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = re.sub(r"[^a-z0-9]", "", text)
    return text


def _country_dict_path() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_dir, "countries", "country_dictionary.json")


def _parse_country_dictionary_value(raw_value: Any) -> Optional[Dict[str, str]]:
    if isinstance(raw_value, str):
        value = raw_value.strip()
        if not value:
            return None
        return {"official": value, "display": value}

    if not isinstance(raw_value, dict):
        return None

    official = raw_value.get("official")
    display = raw_value.get("display")
    if not isinstance(official, str) or not isinstance(display, str):
        return None
    official = official.strip()
    display = display.strip()
    if not official or not display:
        return None
    return {"official": official, "display": display}


def _load_country_dictionary_if_needed() -> Dict[str, Dict[str, str]]:
    global _COUNTRY_DICT_CACHE_SIGNATURE, _COUNTRY_DICT_CACHE_MAP

    path = _country_dict_path()
    try:
        signature = (path, os.path.getmtime(path))
    except OSError:
        signature = None

    if signature == _COUNTRY_DICT_CACHE_SIGNATURE:
        return _COUNTRY_DICT_CACHE_MAP

    loaded: Dict[str, Dict[str, str]] = {}
    if signature is not None:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                payload = json.load(fh)
            if isinstance(payload, dict):
                for raw_key, raw_value in payload.items():
                    if not isinstance(raw_key, str):
                        continue
                    key = normalize_country_key(raw_key)
                    parsed = _parse_country_dictionary_value(raw_value)
                    if not key or not parsed:
                        continue
                    loaded[key] = parsed
        except Exception:
            loaded = {}

    _COUNTRY_DICT_CACHE_SIGNATURE = signature
    _COUNTRY_DICT_CACHE_MAP = loaded
    return _COUNTRY_DICT_CACHE_MAP


def dictionary_lookup_country(name: str) -> Optional[Dict[str, str]]:
    if _DICTIONARY_DISABLED:
        return None
    key = normalize_country_key(name)
    if not key:
        return None
    try:
        return _load_country_dictionary_if_needed().get(key)
    except Exception:
        return None


def _dict_dir_path() -> str:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.isabs(_DICT_DIR):
        return _DICT_DIR
    return os.path.join(base_dir, _DICT_DIR)


def _iter_dict_files() -> list[str]:
    root = _dict_dir_path()
    try:
        entries = os.listdir(root)
    except OSError:
        return []

    files: list[str] = []
    for entry in entries:
        path = os.path.join(root, entry)
        if not os.path.isfile(path):
            continue
        ext = os.path.splitext(entry)[1].lower()
        if ext in _DICT_EXTENSIONS:
            files.append(path)
    files.sort()
    return files


def _json_dict_paths() -> Tuple[str, str]:
    root = _dict_dir_path()
    return (
        os.path.join(root, "first_name_dictionary.json"),
        os.path.join(root, "last_name_dictionary.json"),
    )


def _parse_dict_line(line: str) -> Optional[Tuple[str, str]]:
    stripped = line.strip()
    if not stripped or stripped.startswith("#"):
        return None

    if "\t" in stripped:
        parts = stripped.split("\t")
        if len(parts) < 2:
            return None
        left = parts[0].strip()
        right = parts[1].strip()
        if not left or not right:
            return None
        return left, right

    parts = stripped.split(None, 1)
    if len(parts) < 2:
        return None
    left = parts[0].strip()
    right = parts[1].strip()
    if not left or not right:
        return None
    return left, right


def _load_json_map(path: str) -> Dict[str, str]:
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as fh:
            payload = json.load(fh)
    except Exception:
        return {}

    if not isinstance(payload, dict):
        return {}

    out: Dict[str, str] = {}
    for raw_key, raw_value in payload.items():
        if not isinstance(raw_key, str) or not isinstance(raw_value, str):
            continue
        key = dictionary_key(raw_key)
        value = raw_value.strip()
        if not key or not value:
            continue
        if key in out:
            continue
        out[key] = value
    return out


def _load_dictionary_if_needed() -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
    global _DICT_CACHE_SIGNATURE, _DICT_CACHE_MAP, _DICT_CACHE_FIRST_NAME_MAP, _DICT_CACHE_LAST_NAME_MAP

    files = _iter_dict_files()
    first_json_path, last_json_path = _json_dict_paths()
    signature_parts = []
    for path in (first_json_path, last_json_path):
        if not os.path.isfile(path):
            continue
        try:
            signature_parts.append((path, os.path.getmtime(path)))
        except OSError:
            continue
    for path in files:
        try:
            signature_parts.append((path, os.path.getmtime(path)))
        except OSError:
            continue
    signature = tuple(signature_parts)

    if signature == _DICT_CACHE_SIGNATURE:
        return _DICT_CACHE_MAP, _DICT_CACHE_FIRST_NAME_MAP, _DICT_CACHE_LAST_NAME_MAP

    loaded: Dict[str, str] = {}
    first_name_loaded = _load_json_map(first_json_path)
    last_name_loaded = _load_json_map(last_json_path)

    for key, value in first_name_loaded.items():
        if key not in loaded:
            loaded[key] = value
    for key, value in last_name_loaded.items():
        if key not in loaded:
            loaded[key] = value

    for path, _ in signature:
        if path in {first_json_path, last_json_path}:
            continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as fh:
                for raw_line in fh:
                    parsed = _parse_dict_line(raw_line)
                    if not parsed:
                        continue
                    name_raw, katakana = parsed
                    key = dictionary_key(name_raw)
                    if not key:
                        continue
                    if key in loaded:
                        continue
                    loaded[key] = katakana
        except OSError:
            continue

    _DICT_CACHE_SIGNATURE = signature
    _DICT_CACHE_MAP = loaded
    _DICT_CACHE_FIRST_NAME_MAP = first_name_loaded
    _DICT_CACHE_LAST_NAME_MAP = last_name_loaded
    return _DICT_CACHE_MAP, _DICT_CACHE_FIRST_NAME_MAP, _DICT_CACHE_LAST_NAME_MAP


def dictionary_lookup_name(raw_name: str) -> Optional[str]:
    if _DICTIONARY_DISABLED:
        return None
    key = dictionary_key(raw_name)
    if not key:
        return None
    try:
        merged_map, first_name_map, last_name_map = _load_dictionary_if_needed()

        if key in first_name_map:
            return first_name_map[key]
        if key in last_name_map:
            return last_name_map[key]
        if key in merged_map:
            return merged_map[key]

        tokens = key.split()
        if len(tokens) < 2:
            return None

        kana_tokens = []
        last_index = len(tokens) - 1
        for idx, token in enumerate(tokens):
            kana = None
            if idx == 0:
                kana = first_name_map.get(token) or last_name_map.get(token)
            elif idx == last_index:
                kana = last_name_map.get(token) or first_name_map.get(token)
            else:
                kana = first_name_map.get(token) or last_name_map.get(token)
            if not kana:
                return None
            kana_tokens.append(kana)

        return " ".join(kana_tokens)
    except Exception:
        return None


def _safe_get_json(url: str, params: Dict[str, Any]) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if requests is None:
        return None, "requests_unavailable"
    try:
        r = requests.get(
            url,
            params=params,
            timeout=_WIKIDATA_TIMEOUT,
            headers={
                "User-Agent": _USER_AGENT,
                "Accept": "application/json",
            },
        )
    except requests.RequestException as e:
        return None, f"request_exception:{type(e).__name__}"

    if r.status_code != 200:
        return None, f"http_status:{r.status_code}"

    content_type = (r.headers.get("content-type") or "").lower()
    if "json" not in content_type:
        return None, f"non_json_content_type:{content_type}"

    if not r.text or not r.text.strip():
        return None, "empty_body"

    try:
        return r.json(), None
    except ValueError:
        return None, "json_decode_error"


def _wd_cache_get(cache: Dict[str, Any], key: str) -> Tuple[bool, Any]:
    if key not in cache:
        return False, None
    value = cache.pop(key)
    cache[key] = value
    return True, value


def _wd_cache_put(cache: Dict[str, Any], key: str, value: Any) -> None:
    if key in cache:
        cache.pop(key)
    cache[key] = value
    if len(cache) > _WD_QID_CACHE_MAX:
        cache.pop(next(iter(cache)))


def _wd_entity_allowed(entity: Dict[str, Any]) -> bool:
    claims = entity.get("claims", {})
    p31_claims = claims.get("P31", []) if isinstance(claims, dict) else []
    for claim in p31_claims:
        if not isinstance(claim, dict):
            continue
        mainsnak = claim.get("mainsnak", {})
        datavalue = mainsnak.get("datavalue", {}) if isinstance(mainsnak, dict) else {}
        value = datavalue.get("value", {}) if isinstance(datavalue, dict) else {}
        qid = value.get("id") if isinstance(value, dict) else None
        if isinstance(qid, str) and qid in _WIKIDATA_ALLOWED_P31:
            return True
    return False


def _wd_entity_kana(entity: Dict[str, Any]) -> Optional[str]:
    labels = entity.get("labels", {}) if isinstance(entity, dict) else {}
    ja = labels.get("ja", {}).get("value") if isinstance(labels, dict) else None
    if isinstance(ja, str) and _KANA_LIKE_RE.match(ja):
        return ja
    return None


@lru_cache(maxsize=10_000)
def wikidata_kana_label(query: str) -> Optional[str]:
    if not _WIKIDATA_ENABLED:
        return None

    q = query.strip()
    if not q:
        return None

    search_json, _ = _safe_get_json(
        "https://www.wikidata.org/w/api.php",
        {
            "action": "wbsearchentities",
            "search": q,
            "language": "en",
            "format": "json",
            "limit": 5,
        },
    )
    if not search_json:
        return None

    candidate_qids = []
    for item in search_json.get("search", []):
        qid = item.get("id")
        if not qid:
            continue
        if qid in candidate_qids:
            continue
        candidate_qids.append(qid)
        if len(candidate_qids) >= _WIKIDATA_MAX_CANDIDATES:
            break

    if not candidate_qids:
        return None

    qids_to_fetch = []
    for qid in candidate_qids:
        has_allowed, _ = _wd_cache_get(_WD_QID_ALLOWED_CACHE, qid)
        has_kana, _ = _wd_cache_get(_WD_QID_KANA_CACHE, qid)
        if not (has_allowed and has_kana):
            qids_to_fetch.append(qid)

    if qids_to_fetch:
        ent_json, _ = _safe_get_json(
            "https://www.wikidata.org/w/api.php",
            {
                "action": "wbgetentities",
                "ids": "|".join(qids_to_fetch),
                "props": "claims|labels",
                "languages": "ja",
                "format": "json",
            },
        )

        entities = ent_json.get("entities", {}) if isinstance(ent_json, dict) else {}
        for qid in qids_to_fetch:
            ent = entities.get(qid, {}) if isinstance(entities, dict) else {}
            allowed = _wd_entity_allowed(ent) if isinstance(ent, dict) else False
            kana = _wd_entity_kana(ent) if isinstance(ent, dict) else None
            _wd_cache_put(_WD_QID_ALLOWED_CACHE, qid, allowed)
            _wd_cache_put(_WD_QID_KANA_CACHE, qid, kana)

    for qid in candidate_qids:
        _, is_allowed = _wd_cache_get(_WD_QID_ALLOWED_CACHE, qid)
        _, kana = _wd_cache_get(_WD_QID_KANA_CACHE, qid)
        if is_allowed and kana:
            return kana

    return None


def transliterate_name(name: str) -> Dict[str, Any]:
    raw = normalize_name(name)

    country = dictionary_lookup_country(raw)
    if country:
        katakana = country["display"]
        hiragana = kata_to_hira(katakana) if re.search(r"[\u30A0-\u30FF]", katakana) else katakana
        return {
            "input": raw,
            "katakana": katakana,
            "hiragana": hiragana,
            "official_name": country["official"],
            "source": "dictionary",
            "candidates": [],
            "warning": None,
        }

    raise UnknownCountryError(INVALID_COUNTRY_MESSAGE)
