# Handoff: RVOS POC3 maintenance

Written for a fresh agent. Focus of the next session: **resume POC3 maintenance**
(no specific task chosen yet; ask the user).

## Hard constraints from the user (do not break these)
- **Do not change the reasoning core**: `extract_claim`, `search_openalex`,
  `judge_novelty`, their prompts, and the LangGraph wiring in `rvos_poc.py`.
  POC3 was plumbing only.
- **Never commit anything under `Docs/Test/`.** It holds NDA papers (`.txt`, `.pdf`,
  `.docx`) and is blanket-ignored by `.gitignore`. The repo is **public**.
- **Explain the exact git/GitHub command sequence before running it**, and wait
  for approval before any commit, push, visibility change, or publish.
- Stage files by name. Never `git add .` or sweep in untracked files.
- Verify every push on GitHub afterwards (`gh api` / `gh run view`), not just local output.
- Do not add an `ANTHROPIC_API_KEY` repo secret (decided: reasoning tests skip in CI anyway).

## Where things stand
- Repo: `origin` of the current directory, https://github.com/OneRealUni/rvos-poc3
  (public, branch `main`). HEAD `f1f8f0a`, pushed and in sync.
- Working tree: clean except untracked `handover.md`. The user has **not decided**
  whether to commit it (it holds local paths and session details). Leave it alone
  unless told.
- CI (GitHub Actions `RVOS tests`) is green: `ruff check .` clean, 11 passed and
  4 skipped. The 4 skips are the live reasoning tests; expected without NDA
  fixtures or an API key, not a bug.
- Locally (with `.env` and fixtures): 15 passed, all live API calls for the 4 reasoning tests.
- Nothing is in flight.

## Read these instead of asking the user to re-explain
| Need | Where |
|---|---|
| Rules for working in this repo | `CLAUDE.md` |
| Glossary (load vs extract, paper text, verdict, ...) | `CONTEXT.md` |
| Full session history, decisions and reasons, gotchas, open items, run commands | `handover.md` (untracked, local) |
| What POC3 changed and why | `git log --stat` (4 commits: `1970910`, `43df0f1`, `6271232`, `f1f8f0a`) |
| Latest local test evidence | `pytest_output.txt` |
| CI workflow | `.github/workflows/tests.yml` |
| Sibling project's handoff, for format | https://github.com/OneRealUni/rvos-poc2/blob/main/handoff-rvos-poc2-maintenance.md |

Do not restate `handover.md`; follow it.

## How this user wants to work
- Short, direct answers; a small diagram beats long prose when it fits the question.
- Honest assessments, including pushback when a premise is off.
- They will correct mistakes plainly (they renamed the repo `rvos-poc` to `rvos-poc3` mid-task).
- They confirm before anything outward-facing (public repo, push, token scopes).

## Things learned the hard way
- Git Bash on this Windows machine has no `tee`, `tail` or `grep`. Use PowerShell or
  the dedicated tools. PowerShell 5.1 `Tee-Object` writes UTF-16; write output files
  with `[IO.File]::WriteAllLines(path, lines, UTF8Encoding($false))`.
- The harness blocked a PowerShell command that had a regex-looking string next to
  `Remove-Item`. Avoid deletes; use fresh directory names instead.
- Pushing `.github/workflows/*` needs the `workflow` scope on the `gh` token. It was
  added on 2026-09-25 via `gh auth refresh -h github.com -s workflow`.
- `load_dotenv()` runs at import, so local pytest hits the live APIs even with no
  shell variable set, and costs a little per run. CI has no `.env`, so those tests skip.
- Ruff here flagged `subprocess.run` without `check=`; CI runs `ruff check .`, so
  run it locally before pushing.
- Git prints LF/CRLF warnings on this machine. Harmless.

## Unverified, so do not treat as fact
- The user half-remembers an on-screen "10 pound offer if I do /something". It was
  never said in this session (transcript checked). Its source is unknown. Do not
  act on it; if they bring the exact wording, read what the command does first.
- Whether CI stays green after the Node 20 deprecation (`actions/checkout@v4`,
  `actions/setup-python@v5` are being forced to Node 24) and the `ubuntu-latest`
  move to Ubuntu 26 on 2026-10-19. Not tested; pinning `ubuntu-24.04` would avoid it.
- How PDF/DOCX loading behaves on two-column layouts, DOCX tables, headers/footers.
  Deliberately plain extraction; only the first 12,000 characters reach the model.
- The "insufficient evidence" verdict path is still untested (deferred in `CLAUDE.md`).

## Open decisions for the user
- Commit `handover.md` or keep it local (POC2 kept its equivalent local).
- Update `CLAUDE.md`'s "Current increment" section, which still describes POC3 as
  in progress. Only when the user picks the next increment.

## Suggested skills
Call the Skill tool for these when the situation fits:
- `mattpocock-skills:diagnosing-bugs`: if a test fails or the pipeline misbehaves.
  Rerun once first, since the reasoning tests depend on live model output.
- `mattpocock-skills:tdd`: if the user asks for a test-first fix or feature.
- `mattpocock-skills:code-review`: to review a diff before it is committed.
- `mattpocock-skills:domain-modeling`: only if `CONTEXT.md` terms need changing.

Not invocable by the agent (user must type them): `mattpocock-skills:grill-with-docs`,
`mattpocock-skills:handoff`. Do not run `init` (it would rewrite `CLAUDE.md`).

## First moves
1. `git status --short`, `git log --oneline -5`, `gh auth status`.
2. Read `CLAUDE.md`, `CONTEXT.md`, then `handover.md`.
3. Ask the user which maintenance task they want. Do not assume one.
