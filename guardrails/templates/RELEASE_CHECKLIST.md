# Release Checklist

- [ ] Confirm no debug/test endpoint exposes tokens, env values, or internal secrets.
- [ ] Confirm production logging avoids raw names where possible.
- [ ] Confirm required env vars are set for frontend and backend.
- [ ] Confirm `NEXT_PUBLIC_APP_NAME` is used instead of hardcoded product name strings.
- [ ] Confirm frontend uses API proxy routes instead of direct browser calls to backend.
- [ ] Confirm external lookup fallback works (timeouts, non-JSON, `429`, `403` -> local transliteration).
- [ ] Confirm bulk conversion hard caps are enforced.
- [ ] Confirm rate limits are enabled for conversion endpoints.
- [ ] Confirm lint/typecheck/tests pass for release commit.
