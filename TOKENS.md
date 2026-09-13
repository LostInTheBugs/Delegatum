# Token usage tracking — Delegatum

LLM token usage for this project, tallied session by session.

## Cumulative tally (2026-09-13)

| Metric | Value |
|---|---|
| Dev sessions (Hermes) | 29 |
| Scripted agent sessions (API) | 1 |
| Models | deepseek-v4-flash, deepseek-v4-pro, gemini-3.6-flash |
| Messages | 6 807 |
| API calls | 5 315 |
| Input tokens | 9 199 640 |
| Output tokens | 2 553 867 |
| Of which reasoning | 932 585 |
| Cache read (cache_read) | 925 132 160 |
| Cache write (cache_write) | 0 |
| **Total (input + output)** | **11 753 507** |
| Estimated cost | ≈ 6.02 USD |

Per model:

- deepseek-v4-flash — 3 204 calls / 7 214 314 in / 1 750 100 out / ≈ 3.09 USD
- deepseek-v4-pro — 2 079 calls / 1 954 919 in / 780 158 out / ≈ 2.77 USD
- gemini-3.6-flash — 20 calls / 23 221 in / 16 211 out / ≈ 0.16 USD
- deepseek-flash — 12 calls / 7 186 in / 7 398 out / ≈ 0.00 USD

## Notes

- Tally taken from `~/.hermes/state.db` (`sessions`, `session_model_usage`)
  — real runtime counters, refreshed 2026-09-13 by re-summing all
  identified sessions (2026-07-22 bootstrap → 2026-09-12). The earlier
  partial tally's cumulative figures are superseded by this recount.
- Sessions attributed by content (repo path `staff-delegation` / app
  names, first user message + dominant mentions); cross-project sessions
  (cloudfr.net portal, multi-app audits/branding, off-peak crons,
  token-accounting) are not attributed to any single app.
- The 2026-09-13 session (macOS desktop port) is not yet flushed to the
  database: its tours will land on the next tally.
- `reasoning_tokens` is probably included in `output_tokens`
  (to be confirmed with the provider).
