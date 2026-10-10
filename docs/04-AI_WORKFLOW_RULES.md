# 04 — AI Workflow Rules

These rules apply to every AI agent working in this repo (Claude Code for both Margulan and Priyanshu). They override the agent's default habits.

## The loop (spec-driven development)
```
pick task (05-PROGRESS) → read context (CLAUDE.md order) → read spec
   → spec missing / vague / Draft?  → write or fix spec, ask human to approve, STOP
   → spec Approved?                 → implement exactly the spec
→ run its acceptance checks + tests + ruff
→ update 05-PROGRESS (your section) + 06-CURRENT_ISSUES
→ commit "[spec-NNN] ..." → pull --rebase → push
```

## Rules
1. **No code without an approved spec.** A spec is approved when its header says `Status: Approved`, and only a human sets that. If the spec is ambiguous, ask one specific question; don't guess. Small mechanical fixes (a typo, a lint error, a broken import) don't need a spec.
2. **Implement the spec, the whole spec, and nothing but the spec.** No extra endpoints, options, refactors or "while I'm here" changes. Ideas go to the parking lot in `06-CURRENT_ISSUES.md`.
3. **Contracts are frozen.** Never change a file format, column, property, endpoint or state name in `02-ARCHITECTURE.md` §4–5 on your own. If one is wrong, log it in `06-CURRENT_ISSUES.md` as `CONTRACT CHANGE PROPOSAL` and ask your human. Both humans must agree before it changes.
4. **Stay in your lane.** Margulan's agent edits `noah/pipeline/`, `tests/test_<pipeline modules>`, `web/data/`. Priyanshu's agent edits `noah/api/`, `bot/`, `web/index.html`, `fixtures/`, `tests/test_<api modules>`. Shared files need a heads-up: `noah/config.py`, `pyproject.toml`, `docs/`, `README.md`.
5. **Don't block on the other lane.** Priyanshu builds against `fixtures/`, which must follow the contracts exactly. When real data lands, swapping it in must need zero code changes.
6. **Time-box every task.** Each spec has a time box. At 1.5× the box, stop. Write what's blocking you and which fallback the spec names into `06-CURRENT_ISSUES.md`, then tell your human. Don't keep digging.
7. **Never fabricate.** Don't invent data, results, validation numbers, API behavior or library functions. If you aren't sure an API exists in the installed version, check the installed package or its docs. Numbers in the pitch, README or Devpost must come from a command we actually ran, and that command gets recorded in `05-PROGRESS.md`.
8. **Verify before claiming done.** "Done" means the spec's acceptance criteria were run and passed, with output shown. If something was skipped, say so.
9. **Safety wording.** Any string a user can see (agent reply, API message, map label, README demo text) follows `02-ARCHITECTURE.md` §5. Never write "safe", "clear" or "passable" about a road. When in doubt, choose the more conservative state.
10. **Data hygiene.** Downloads go to `data/raw/` (gitignored). Don't run code from downloaded archives. Never commit anything over 20 MB.
11. **Secrets.** Read secrets from `.env` via `python-dotenv` / `process.env`. Never echo them, log them, or put them in code or URLs.
12. **Disclosure.** If you copy or adapt more than a few lines from external code, docs or examples, add a line under "Disclosures" in `README.md` (source + what was used). The hackathon requires disclosing pre-existing material.
13. **Keep the docs true.** If what you built differs from a doc, fix the doc in the same commit (except contracts; see rule 3).
14. **Output style.** Summaries back to the human are short: what changed, how it was verified, what's next or blocked. No feature tours.

## Writing a spec (when asked or when one is missing)
- Copy `specs/000-TEMPLATE.md` to `specs/NNN-short-name.md` using the next free number.
- Fill every section. Acceptance criteria must be **checkable by running something**, e.g. "`uv run pytest tests/test_x.py` passes" or "`curl .../health` returns `ok: true`", never "works well".
- Set `Status: Draft`, then ask the human to review. Do not set `Approved` yourself.

## Updating the tracker files
- `05-PROGRESS.md`: edit only **your human's section** plus the milestone checkboxes. This avoids merge conflicts between the two agents.
- `06-CURRENT_ISSUES.md`: add new items at the top of the relevant table with your owner tag and time (ET). Move resolved items to "Resolved", with one line on how.

## Session start prompt (humans: paste this when you open Claude Code)
```
Read CLAUDE.md and follow its read order. I'm <Margulan|Priyanshu>.
Then tell me: my next task from docs/05-PROGRESS.md, its spec status, and any blocker in docs/06-CURRENT_ISSUES.md that affects it. Don't write code yet.
```
