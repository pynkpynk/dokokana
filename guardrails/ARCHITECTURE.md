# KanaMe Architecture

## High-level shape

- Frontend: Next.js app deployed on Vercel.
- Backend: FastAPI service deployed separately (Render/Fly/Railway or equivalent).
- Data flow: browser -> Next.js -> Vercel API route proxy -> FastAPI.

## API proxy pattern

- Frontend clients should call a Next.js API route, not FastAPI directly.
- Proxy route handles backend base URL, auth headers, and normalized error mapping.
- Goal: avoid browser CORS issues and keep backend origin/private details out of client code.

## External lookup policy

- External sources (for example Wikidata) are optional enrichments.
- All external lookups must be best-effort:
  - strict timeout
  - content-type validation before JSON parse
  - graceful handling of `429`, `403`, invalid payloads, and transient failures
- On failure, return local transliteration output and warning metadata instead of failing the request.

## Environment variable strategy

- Do not hardcode product name in code. Use config/env (`NEXT_PUBLIC_APP_NAME`) so renaming is easy.
- Frontend env (build/runtime, Vercel):
  - public values only via `NEXT_PUBLIC_*`
  - backend origin for proxy routing via non-public server env
- Backend env (runtime):
  - external lookup toggle, timeout, user-agent, and rate-limit settings
  - secrets remain backend-only and never exposed to frontend bundles

## Reliability guardrails

- Bulk conversion endpoints must enforce hard caps on item count and input length.
- Keep transliteration deterministic for the same normalized input.
- Treat "preferred kana override" as future roadmap behavior (documented, not required now).
