# Quality Gates

Before merge, the change must pass all configured checks for this repo.

## Required gates

- Lint passes (frontend + backend if both are touched).
- Type checks pass (TypeScript and Python typing checks where configured).
- Tests pass for affected areas.
- No unrelated refactors or formatting-only churn in the diff.

## Preflight command philosophy

- Standardize on one local command: `make preflight`.
- `make preflight` should run all required local gates in deterministic order.
- If `Makefile` does not exist yet, keep equivalent commands documented in PR/work order until added.

## Minimal test expectations

- Transliteration unit tests:
  - common Western name cases
  - edge cases (diacritics, apostrophes, spacing, normalization)
- API contract tests:
  - success response shape for single/bulk conversion
  - fallback behavior when external lookup fails
  - validation errors for over-limit input
- UI smoke checks:
  - single conversion render
  - bulk conversion flow
  - copy action availability

## CI guidance (documentation only)

- CI should run lint/typecheck/tests on every PR.
- Include at least one backend test path covering external lookup failure fallback.
- Keep CI config aligned with these gates; do not weaken gates without doc updates and rationale.
