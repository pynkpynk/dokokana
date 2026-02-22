# KanaMe Guardrails

This folder defines project-specific engineering and product rules for KanaMe.
Use these docs for planning, implementation, review, and release checks.

## How to use

1. Start each task with `WORK_ORDER_TEMPLATE.md`.
2. Confirm architecture choices against `ARCHITECTURE.md`.
3. Apply safety and data handling rules from `SECURITY_PRIVACY.md`.
4. Verify merge readiness with `QUALITY_GATES.md`.
5. Keep user-facing wording aligned with `PRODUCT_COPY_GUIDE.md`.
6. Before release, run `templates/RELEASE_CHECKLIST.md`.

## Key docs

- `ARCHITECTURE.md`
- `SECURITY_PRIVACY.md`
- `QUALITY_GATES.md`
- `PRODUCT_COPY_GUIDE.md`
- `WORK_ORDER_TEMPLATE.md`
- `templates/frontend.env.example`
- `templates/backend.env.example`
- `templates/RELEASE_CHECKLIST.md`

## Notes

- Keep diffs minimal. Avoid unrelated refactors or formatting-only edits.
- Existing generic templates in `guardrails/docs/` remain available for broader cross-project guidance.
