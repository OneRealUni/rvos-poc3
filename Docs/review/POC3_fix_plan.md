# RVOS POC3 fix plan

- **Based on:** `POC3_findings_register.md` (Stage 4), repo `OneRealUni/rvos-poc3`, `main` = `8b2c730`
- **Rule:** small patches, one purpose each. Core files (`rvos_poc.py`, `test_rvos_poc.py`) are touched last, in Batch B.
- **Status of every patch:** NOT STARTED until the owner approves it.

## How each patch is delivered (the gate)

1. Drafted from a fresh clone of the current `main`, as a real `git diff` (no hand-typed shorthand).
2. Verified before hand-over: applies cleanly to a fresh clone, `ruff check .` passes, offline `pytest` passes.
3. Owner hands it to Claude Code CLI, runs the checks listed for that patch, and pushes.
4. Owner confirms the green tick on the new commit (or pastes the failure).
5. The register item is marked CLOSED, and the next patch is offered. Nothing is drafted ahead of approval.

## Hand-overs (approved by the owner)

Each patch is still its own commit. A hand-over is one delivery to Claude Code CLI plus one push.

| Hand-over | Patches | Status |
|---|---|---|
| 1 | 1, 2 (path fix, CI pin) | DONE. CI run `36464370180` on commit `b53dd4f`: success. Both action versions confirmed to declare `node24`. |
| 2 | 3, 4, 5 (pins, web errors, offline tests) | Part 1 (Patch 3) DONE. CI run `36494455239` on commit `addd53e`: success. Part 2 (Patches 4, 5) DRAFTED, gated on Part 1's confirmation. Owner decided: upper-bound pins (not a constraints file). |
| 3 | 6, 7 (core: validation, loader) | DRAFTED, verified on a fresh clone of `31680eb`. Sequenced loader first (Patch 7: F5, F2-CLI), reasoning second (Patch 8: F3, F4) -- lower risk before higher risk. Gated on tag `core-baseline-pre-handover3` being pushed first. Needs your live test run before/after to confirm reasoning is unchanged. |
| 4 | 8 (temperature, length) | F6's decision is taken (`RVOS_TEMPERATURE` env var, default `0.2`, used by both `extract_claim` and `judge_novelty`) but the owner deferred this patch to the next increment, not this hand-over. F7 (verdict length) still undecided. |
| 5 | 9 (regenerate log, close register) | NOT STARTED |

**Freeze tag:** `core-baseline-pre-handover3`, on commit `31680eb` -- the last commit before Hand-over 3 touches `rvos_poc.py`'s reasoning functions. `test_rvos_poc.py` was byte-identical to `rvos-poc2`'s validated core at that point; `rvos_poc.py` differed only by the PDF/DOCX loader added for POC3 (74 lines), not by anything in `extract_claim`, `search_openalex`, `judge_novelty` or `build_graph`. Rollback: `git checkout core-baseline-pre-handover3 -- rvos_poc.py test_rvos_poc.py`.

**Hand-over 1 facts (verified):** `actions/checkout` v6 and `actions/setup-python` v6 both declare `node24` in their `action.yml` (v4 and v5 declare `node20`). Newer majors (v7) also exist; v6 was chosen as the conservative step. The 2026-10-19 `ubuntu-latest` change and the Node 20 removal dates come from secondary sources (GitHub issues), not GitHub's own notice.

**Hand-over 2 is split into two independent parts**, verified separately and together on a fresh clone of `b53dd4f`:
- **Part 1 (Patch 3):** `requirements.txt` only. Upper bounds set one major above each package's actually-installed version at draft time (e.g. `reportlab>=4.0.0,<6.0.0` -- its floor was written for 4.x, but a clean install today already resolves to 5.0.1, which is exactly the drift F9 warned about). Verified alone: clean install, lint, 21 passed / 4 skipped.
- **Part 2 (Patches 4, 5):** `app.py`, `test_app.py`, and the new `test_pipeline_offline.py`. Verified alone (does not need Part 1) and stacked on Part 1: lint clean, 32 passed / 4 skipped / 5 xfailed.
- The two parts do not depend on each other and were confirmed to apply in either order.

## Decisions already taken

- **Git history:** the local path is removed from the working tree in Patch 1. Old commits keep it unless the owner later asks for a history rewrite (which would move the `poc3-stable` and `ui-demo` tags).
- **Corrupt or encrypted PDF (F2):** split in two. The web message is fixed in Patch 4 (`app.py`, not a core file). The CLI and loader fix goes in Patch 7 (core, last).
- **Deferred to POC4:** 12k-character truncation and retrieval relevance (D1, D2).

## Batch A - no core files

| # | Register items | Files touched | Change | Verify | Owner action |
|---|---|---|---|---|---|
| 1 | F1 | `pytest_output.txt` | Replace the two local-path lines (2 and 4) with `<repo>`. Add a stamp: generated at commit `<sha>`, predates `test_app.py`, regenerated in Patch 9. | Searching the working tree for the old folder names finds nothing. | Push, check tick. |
| 2 | F8, F10 | `.github/workflows/tests.yml`, `CLAUDE.md` | Pin `ubuntu-24.04` (before 19 Oct 2026). Check the action versions against the Node 20 deprecation warning (current versions verified at build time). Make the workflow and `CLAUDE.md` agree about the API-key secret. | Actions run is green. | Push, check tick, note any warnings still shown. |
| 3 | F9 | `requirements.txt` (and possibly a constraints file) | Stop CI installing whatever is newest. **Decision at this step:** upper-bound pins, or a constraints file generated from a tested install. | Clean-venv install, `ruff`, offline `pytest`, CI green. | Choose the option. |
| 4 | F2 (web) | `app.py`, `test_app.py` | Revised from the original plan: catching specific library exceptions (pdfminer, python-docx) would leak their internals into app.py, which shouldn't need to know what library load_paper_text uses. Instead, broaden the existing `except PaperLoadError` to also catch `Exception`, and return the same generic 400. Add one test. | New test passes, existing 10 still pass. | Push, check tick. |
| 5 | F11 | new `test_pipeline_offline.py` | Mocked, no-API tests for `extract_claim` retry and validation, `search_openalex` 429 backoff, `_reconstruct_abstract` and `_response_text`. Tests for behaviour not yet fixed (F2 CLI, F3, F4, F5) are marked `xfail(strict=True)`, so they turn into failures the moment a fix lands unflagged. `test_rvos_poc.py` is not touched. | Offline run shows passes plus expected xfails. | Push, check tick. |

## Batch B - core files (each needs your live test run)

| # | Register items | Files touched | Change | Verify | Owner action |
|---|---|---|---|---|---|
| 6 | F3, F4 | `rvos_poc.py` | In `extract_claim`, treat a non-object result and a bad or empty `keywords` as a bad sample and retry. Nothing else changes. **DRAFTED as Hand-over 3 Patch 8** (applied second, after the loader patch). | The F3 and F4 xfails are removed and pass -- confirmed offline (37 passed, 0 xfailed) and by re-running the original Stage 3 probes directly. Live tests still needed from you. | Run live `pytest`, push, check tick. |
| 7 | F2 (CLI), F5 | `rvos_poc.py` | Loader raises `PaperLoadError` for corrupt or protected PDFs (same broad-catch design as Patch 4, for the same reason). DOCX loading reads table cells too. **DRAFTED as Hand-over 3 Patch 7** (applied first). Patch 4 in `app.py` is not simplified -- its `except PaperLoadError` branch now catches this case directly, giving a more specific message than its `except Exception` fallback did; both stay, one is now a safety net for the genuinely unexpected. | The F2-CLI and F5 xfails are removed and pass -- confirmed offline and via the original Stage 3 probes (a corrupt PDF now raises `PaperLoadError` through the real web route too, not just the CLI). | Run live `pytest`, push, check tick. |
| 8 | F6, F7 | `rvos_poc.py` | Add a `temperature` to the Claude calls and tighten the verdict length wording. **Before drafting:** confirm the API accepts `temperature` for `claude-sonnet-5`. **Decisions at this step:** the value, and whether the length range is tightened or relaxed. This is the only patch that changes model behaviour, so it goes last and can be reverted alone. | Run the live tests 3 times and compare verdict wording on both fixtures before and after. | Live runs (costs a few pence each) and your reading of the verdicts. |

## Wrap-up

| # | Register items | Files touched | Change | Verify | Owner action |
|---|---|---|---|---|---|
| 9 | F1 (final), register | `pytest_output.txt`, `CLAUDE.md`, register | Regenerate the log from a full local run (25 tests), stamped with the commit. Update `CLAUDE.md` completed increments. Mark register items CLOSED, DEFERRED or WATCH. | Log shows the current test count and no local path. CI green. | Run `pytest -v`, push. |

## Not planned as patches

- **F12** (untested "insufficient evidence" path): stays deferred per `CLAUDE.md`. Revisit after Patch 8.
- **F13** (live tests skip in CI): by design.
- **F14** (browser check of item [4] link): a two-minute manual check, no patch.
- **W1-W4:** watch only.

## Rollback

Every patch is its own commit, so any one can be reverted with `git revert <sha>` without touching the others. Patch 8 is the one most likely to need it.
