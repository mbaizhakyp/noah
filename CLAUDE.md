# CLAUDE.md — Noah

Claude Code loads this file automatically. Keep it short; the detail lives in `docs/`.

## Read before every task (in this order)
1. `docs/01-PROJECT_OVERVIEW.md` — what Noah is, who it serves, locked decisions
2. `docs/02-ARCHITECTURE.md` — components, repo layout, **data contracts (frozen)**
3. `docs/03-CODE_STANDARDS.md` — language, style, units, CRS, testing
4. `docs/04-AI_WORKFLOW_RULES.md` — how you (the AI) must work in this repo
5. `docs/05-PROGRESS.md` — what's done, who owns what, the clock
6. `docs/06-CURRENT_ISSUES.md` — open risks, blockers, parking lot
7. The spec for your task in `specs/` — **no spec with `Status: Approved` → no code**

## Non-negotiables
- **Sync first, every time.** Two people push to `main`. Before starting any change *and* again right before every commit, run `git fetch && git status -sb`. If it says `behind`, run `git pull --rebase` first, re-read any changed doc or spec that affects your task, and only then edit or commit. Push right after committing. Details: `docs/03-CODE_STANDARDS.md` §Git.
- Spec first. Implement only what the approved spec says. Ideas outside it go to the parking lot in `docs/06-CURRENT_ISSUES.md`.
- Data contracts in `docs/02-ARCHITECTURE.md` §4 change only when both humans agree.
- Stay in your owner's directories (see `docs/05-PROGRESS.md` §Owners).
- No user-facing text may say a road is "safe", "clear" or "passable". Use the frozen vocabulary in `docs/02-ARCHITECTURE.md` §5.
- Never invent data or results. If code didn't produce the number, the number doesn't exist.
- Secrets live in `.env` only. Large data lives in `data/` (gitignored).
- After each task: run tests and lint, update `docs/05-PROGRESS.md` and `docs/06-CURRENT_ISSUES.md`, and commit with the spec ID.

## Hard deadline
Submission is due Sun Oct 11, 2026 at 9:00 AM ET. Our internal deadline is **7:00 AM**. Features freeze at **Sun 00:00**.
