# Security and Privacy Guardrails

Names are personal data. Collect and retain the minimum needed for conversion.

## Input validation

- Normalize Unicode input (NFKC or equivalent) before processing.
- Enforce server-side length caps:
  - single input: max characters per name
  - bulk input: max lines/items and max total payload size
- Allowlist expected characters for name fields where practical (letters, separators, apostrophes, spaces, common diacritics).
- Reject control characters and malformed encodings.

## External call safety

- External calls must use explicit short timeouts.
- Validate response content-type before parsing JSON.
- Handle non-JSON, `429`, `403`, and upstream network failures without crashing.
- Set a descriptive `User-Agent` from config.
- Apply per-request retry rules conservatively (small bounded retry count only where safe).

## Logging and redaction

- Do not log raw names in production where possible.
- Prefer hashes, truncation, or masked forms for diagnostics.
- Never log tokens, API keys, or full upstream payloads containing personal data.
- Keep debug logging disabled in production builds.

## Abuse prevention

- Enforce request rate limits per IP/user/token at the backend edge.
- Enforce hard bulk limits (items/lines and payload bytes).
- Return clear validation errors for over-limit input; do not attempt partial processing beyond safe limits.

## Secure API behavior

- No debug/test endpoints that return secrets, env values, or auth tokens.
- Do not support user-provided arbitrary URLs for fetches (avoid SSRF class risk).
- Keep dependency updates regular and review security advisories.

## Threats to explicitly review

- DoS via very large inputs or excessive bulk conversions.
- Upstream dependency or package vulnerabilities.
- Leakage of personal names through logs or analytics payloads.
