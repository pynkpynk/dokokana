# KanaMe Work Order Template

## Objective

- What user-visible outcome is required?
- What problem does it solve now?

## Acceptance Criteria

- [ ] Behavior is correct for stated scenarios.
- [ ] External lookup failures degrade gracefully to local transliteration.
- [ ] Bulk conversion caps are enforced.
- [ ] Privacy/logging rules are followed (no raw-name production logging where possible).
- [ ] Tests and checks pass.

## Constraints

- Minimal diffs only.
- No unrelated refactors or formatting-only changes.
- No dependency additions unless explicitly approved.
- Do not change application code unless required by scope.

## File-level Change Plan

- Files to edit:
- For each file: why this file, expected change size, and risk level.
- Files explicitly out of scope:

## Validation Plan

- Local commands to run (target: `make preflight` when available).
- Expected test coverage updates.
- Manual checks (if UI/API behavior changes).

## Security Checklist

- [ ] Input validation limits preserved or improved.
- [ ] External call timeout/content-type/error handling preserved or improved.
- [ ] No debug endpoint exposes tokens or env values.
- [ ] No new user-provided URL fetch paths (SSRF risk).
- [ ] Logging remains privacy-safe for personal names.

## Done Definition

- [ ] Acceptance criteria met.
- [ ] Validation completed and results recorded.
- [ ] Diff reviewed for minimal scope and no unrelated churn.
