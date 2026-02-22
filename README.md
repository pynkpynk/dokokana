# KanaMe

KanaMe is a beginner-friendly web app for converting one Western name at a time into Japanese Kana (Katakana and Hiragana).

## Environment variables

- `NAMEKANA_API_URL` (server-only): Base URL for the FastAPI backend used by Next.js API proxy routes.
- `NEXT_PUBLIC_APP_NAME` (public): App display name shown in the UI and metadata.
- `NAMEKANA_DICT_DIR` (optional, backend): Dictionary folder path (default `names`).
- `NAMEKANA_DISABLE_DICTIONARY` (optional, backend): Disable dictionary fallback when set to true-like values.
- `NAMEKANA_WD_MAX_CANDIDATES` (optional, backend): Max Wikidata candidates inspected (default `8`).
- `NAMEKANA_WD_ALLOWED_P31` (optional, backend): Allowed Wikidata `P31` values (default `Q5,Q202444,Q101352`).

Wikidata adoption is restricted to human / given-name / family-name entities before dictionary and e2k fallback.

Dictionary files in `names/` can be JSON maps:
- `first_name_dictionary.json`
- `last_name_dictionary.json`
Format: `{ "normalized_key": "カタカナ", ... }`

TSV/TXT dictionary files with `<name><TAB><katakana>` are also supported; lines with only one column are ignored safely.

## Local run

1. Install dependencies.
2. Set the required environment variables.
3. Start the Next.js dev server.
