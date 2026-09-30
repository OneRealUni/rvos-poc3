# RVOS POC3 findings register

- **Repo / commit reviewed:** `OneRealUni/rvos-poc3`, `main` = `8b2c730` (tags `poc3-stable` = `da8f996`, `ui-demo` = `8b2c730`)
- **Date:** 28 September 2026
- **Stage:** 4 of 5 (findings). Nothing here has been patched yet. Stage 5 turns it into a fix plan.
- **Status of every item:** OPEN unless stated.
- **Suggested home in the repo:** `Docs/review/poc3-findings-register.md` (not under `Docs/Test/`, which is git-ignored)

## What was and was not checked

| Checked | Method |
|---|---|
| Clean install, `ruff check .`, offline tests (21 passed, 4 skipped) | Sandbox, Python 3.12 (CI uses 3.11) |
| CI on `main` | Green tick next to `8b2c730` on the repo page (screenshot) |
| Behaviour on awkward inputs | Mocked-model probes, no API calls |
| One live UI run (ISPIM PDF) | User-supplied DOCX of the on-screen report |
| `test_rvos_poc.py` vs POC2 `b30e186` | Identical |

**Not checked:** live reasoning tests, `static/index.html` in a real browser (skimmed only), individual CI step logs, and the accuracy of the doc contents (headings only, plus a search for stale phrases; none found).

## Ranked findings

Core file = touches `rvos_poc.py` or `test_rvos_poc.py`. Those are changed last, per the agreed rule.

### P1 - Fix first (privacy, requested)

| ID | Severity | Finding | Evidence | Core file? | Suggested fix |
|---|---|---|---|---|---|
| F1 | High | **CLOSED (`b1c8ff5`).** `pytest_output.txt` in a **public** repo contains the author's full local Windows folder path (lines 2 and 4). It is also stale: it lists 15 tests and predates `test_app.py` (25 tests now). | Search of the working tree: only this file. History: only commit `f1f8f0a`. | No | Replace the two path lines with `<repo>` placeholders, add a "Generated at commit" stamp, regenerate from a full local run. See decision Q1 about git history. |

### P2 - Wrong or misleading output, confusing errors

| ID | Severity | Finding | Evidence | Core file? | Suggested fix |
|---|---|---|---|---|---|
| F2 | Medium | **CLOSED (web: `cd0a732`; CLI/loader: `af24121`).** A corrupt or password-protected PDF raised `PdfminerException`, not `PaperLoadError`. The web route returned a bare 500 ("Something went wrong. Please try again") even though retrying cannot help. The CLI only caught `PaperLoadError`, so a traceback was likely (inferred, not run before the fix). | Probes W1, W2, P5, P6 | Web fix: no. CLI fix: yes | Web: broadened `except PaperLoadError` to also catch `Exception` in `app.py`, returning the same generic 400 -- not per-library exception types, which would leak loader internals into the web layer. CLI/loader: `_load_pdf` wraps any pdfplumber/pdfminer failure as `PaperLoadError`, the same broad-catch design, so the CLI's existing `except PaperLoadError` now actually catches it too. |
| F3 | Medium | **CLOSED (Hand-over 3 Patch 8).** If the model returns valid JSON that is not an object (for example `[]`), `extract_claim` raises `AttributeError` on `.keys()`. The retry loop does not catch it, so there is no retry. | Probes P1, W3 | Yes | Treat a non-dict result like a bad sample and retry. |
| F4 | Medium | **CLOSED (Hand-over 3 Patch 8).** `keywords` is checked for presence only. A string is accepted and reaches OpenAlex as `c i r c u l a r`. An empty list is also accepted. | Probes P2, P3 | Yes | Require a non-empty list of strings. |
| F5 | Low-Medium | **CLOSED (Hand-over 3 Patch 7).** DOCX loading reads paragraphs only. Text inside tables is dropped, and a table-only file fails with a misleading "no extractable text" message. | Probe P4 | Yes | Read table cells too, or say tables are not read. |
| F6 | Medium | **Decision taken, deferred to the next increment (not this hand-over).** No `temperature` is set on either Claude call, so verdicts can vary between runs and the live regression tests are inherently noisy. Owner decided: `RVOS_TEMPERATURE` env var, default `0.2`, used by both `extract_claim` and `judge_novelty` in `rvos_poc.py` so the CLI and the UI stay consistent (they share the same functions). | Code search (`temperature` absent) | Yes | Decide a value for `judge_novelty` (and `extract_claim`) and record it. |
| F15 | Low | **Logged, no increment assigned.** `app.py`'s `/analyse` response rebuilds the citation numbering itself (`"n": i + 1` over `enumerate(result["related"])`), duplicating the same convention `run()` uses for the report's numbered list. Nothing checks the two stay in sync -- this is the same class of defect as I2, in a second location. | Reading `app.py` directly during the Hand-over 3 discussion | No | Possible future refactor: a shared helper in `rvos_poc.py` that both `run()` and `app.py` call for the numbered list, so there is one source of truth. |
| F7 | Low | The verdict came out at about 264 words against the prompt's 150-250. | One live UI run | Yes | Tighten the prompt wording, or accept and relax the stated range. |
| F16 | Low-Medium | **CLOSED (uncommitted, this session).** `search_openalex`'s retry loop backed off on `429` only; a `503`, `500` or `504` raised immediately with no retry. All three were directly observed live on 2026-09-30 (see "External blockers" below), including a real `Retry-After: 60` header on a `503` -- confirmed from the raw response, not inferred. Now retries on `429/500/503/504`, honoring `Retry-After` when present (capped at 30s), falling back to fixed exponential backoff otherwise. `504` was added after the first version of this fix (which only covered `429/500/503`, following PyAlex's precedent) still failed live on a `504` -- an evidence gap in the first draft, corrected before commit. | Live probes during Hand-over 3 Step 6, three separate failures + two offline test rounds | Yes | Done: 6 new offline tests covering `503`/`500`/`504` retry, `Retry-After` honored/absent/capped/unparseable. |
| F17 | High (was blocking) | **CLOSED (uncommitted, this session).** Root cause of F16's live trigger: anonymous OpenAlex access (`mailto` only) gets a far smaller daily budget than documented (`X-RateLimit-Limit-USD: 0.1` observed, vs the documented $1/day free-tier) and is the first traffic OpenAlex sheds under load ("Anonymous search is paused... use a free API key"). Owner obtained a free OpenAlex API key. **First version sent it as an `api_key` query param -- this leaked the real key into a live test's traceback** (`requests`' own error message includes the full request URL). Caught immediately, confirmed not written to any file or git-tracked location, corrected same session: the key is now sent as an `Authorization: Bearer` header instead (OpenAlex documents both methods; only the header form can't leak via a URL-printing error). `mailto` stays a query param -- it isn't secret. Verified three ways: (1) a redacted direct request with the key returned `200` with the keyed `$1/day` budget active, both before and after the header change; (2) Step 6 re-run with the query-param version: **4 passed** (before the leak was discovered on the *next* failing run); (3) Step 6 re-run again after the header fix: **4 passed**, no key in any output. | Redacted live probes (key never logged/printed) + two Step 6 re-runs, 2026-09-30 | Yes | Done: `search_openalex` sends the key via header; 2 offline tests rewritten to assert on `headers`, not `params`; `.env.example` updated. No change to `test_rvos_poc.py`. **Owner action recommended:** rotate the exposed key at OpenAlex, out of caution (free-tier key, low real-world risk, but correct practice regardless of severity). |

### P3 - CI and dependencies

| ID | Severity | Finding | Evidence | Core file? | Suggested fix |
|---|---|---|---|---|---|
| F8 | Medium (dated) | **CLOSED (`6894832`).** Confirmed by CI run `36464370180`, conclusion success, on the pinned runner. Workflow uses `ubuntu-latest`, which moves to Ubuntu 26 on **19 October 2026** (from the RVOS All v0.1 thread; not verified against GitHub's notice). Node 20 deprecation warnings on the action versions were also noted there. | `.github/workflows/tests.yml` | No | Pin `ubuntu-24.04` before 19 October. Review the action versions. |
| F9 | Low-Medium | **CLOSED (`addd53e`, CI run `36494455239`: success).** `requirements.txt` had lower bounds only and no lock file, so every CI run installed the newest versions (at draft time: `anthropic` 1.8.0, `langgraph` 1.2.12, `fastapi` 0.141.1, and `reportlab` had already silently drifted from its 4.x floor to 5.0.1). Now upper-bound pinned. | Clean-install output | No | Add a constraints or lock file, or upper pins. |
| F10 | Low | **CLOSED (`6894832`).** Workflow passes `secrets.ANTHROPIC_API_KEY`, but `CLAUDE.md` says no such secret is set. Harmless, but the two disagree. The client is created at import time, and in the SDK version tested it did not fail without a key (behaviour may differ across versions). | Workflow vs `CLAUDE.md`; test run with no key | No | Make docs and workflow agree. |

### P4 - Test gaps

| ID | Severity | Finding | Core file? | Suggested fix |
|---|---|---|---|---|
| F11 | Medium | No offline tests for `extract_claim` retry and validation, `search_openalex` 429 backoff, `_reconstruct_abstract` or `_response_text`. | No (new test file) | Add a new mocked test file. `test_rvos_poc.py` stays untouched. |
| F12 | Low | The "insufficient evidence" verdict path is untested. `CLAUDE.md` records this as a deliberate deferral. | Yes | Keep deferred, or add a mocked test. |
| F13 | Info | The four live reasoning tests skip in CI by design, so a green CI tick does not prove reasoning quality. Documented in `CLAUDE.md`. | No | Optional later: a manual workflow with a secret. |
| F14 | Low | `index.html` has no browser-level test. In the live run, related item [4] showed no link and no "no abstract" note; this may just be a copy artefact. | No | Check once in a real browser. |

### Deferred to POC4 (agreed)

| ID | Finding |
|---|---|
| D1 | `extract_claim` silently cuts the paper at 12,000 characters. Plan: RAG in POC4. The report and UI do not currently say when truncation happened. |
| D2 | Retrieval relevance: keywords are joined into one query, and in the live run the judge called 3 of 8 results unrelated. One run only, so this is a hypothesis. Investigate alongside RAG. |

### Watch only (no action proposed)

| ID | Note |
|---|---|
| W1 | `app.py` compiles a new graph on every request. Fine for a demo. |
| W2 | The demo has no authentication (documented non-goal). Keep it on `127.0.0.1`, because it spends Anthropic credit. |
| W3 | The judge prompt skips the number of a paper with no abstract, so the list can start at `[2]`. It stays consistent with the report. |
| W4 | The repo has no description, topics or formal Release. Cosmetic. |
| W5 | PyAlex (github.com/J535D165/pyalex) is a real Python wrapper around OpenAlex's REST API -- not used here, and not needed: `search_openalex` is one GET, parsed directly, and switching would mean a new dependency plus rewriting both the function and its mocks for no current benefit. Its retry-code list informed F16 as precedent, nothing more. Worth it later if a feature needs what it's actually good for: multi-page result walking, complex filter queries, or citation-graph traversal -- not before then. |

## External blockers (not code defects)

- **2026-09-30, Hand-over 3 Step 6 (live reasoning tests): OpenAlex 503, twice.** Both attempts at `pytest -v test_rvos_poc.py` failed with `503 Service Unavailable` from `api.openalex.org`, in `search_openalex`, after `extract_claim` completed successfully both times. Diagnosed with direct `curl` probes, outside the test suite: OpenAlex's search cluster is load-shedding full-text search from anonymous (no-API-key) callers -- `mailto` alone doesn't prevent it; a short 3-word query with the same `mailto` succeeded once, but the longer, real generated queries got `503` twice in a row, seconds apart, with the message *"Anonymous search is paused while the search cluster recovers from heavy load... use a free API key for uninterrupted access."* status.openalex.org stayed green throughout, since it tracks uptime, not search-cluster capacity. **This is not a Hand-over 3 regression** -- the failure is entirely inside OpenAlex's response, not in `extract_claim`'s new validation. Independently reproduced the same way through the UI: the owner's own local run of `app.py` logged `Extracting claim...` / `Searching OpenAlex for related work...` / `ERROR: Analysis service failed: HTTPError` / `POST /analyse HTTP/1.1 502 Bad Gateway` -- the identical failure point (`search_openalex`), not specific to the CLI test path. A direct `curl` recheck minutes later got `200 OK` but with `db_response_time_ms: 4678`, so the cluster was recovering, not yet healthy.
- **2026-09-30, third attempt: worse, not better.** A third `pytest -v test_rvos_poc.py` run, requested after the owner saw `api.openalex.org` respond `200 OK` to a direct probe, still failed -- but this time two calls got `503` and the third got `504 Gateway Timeout` (Cloudflare gave up waiting on OpenAlex's own backend), a step worse than a deliberate `503` rejection. Confirms the cluster was fluctuating under load, not simply down or up.
- **RESOLVED, same day, once the actual cause was found.** All three failures trace to the same thing: anonymous (`mailto`-only) access has a much smaller budget than OpenAlex's documented free tier and is the first traffic shed under load (see F17). The owner obtained a free OpenAlex API key; `search_openalex` was extended to send it (F17, test-first, 2 new offline tests, `ruff` clean). Verified with a redacted direct probe (key never printed) against the exact query that previously failed: `200 OK`, `X-RateLimit-Limit-USD: 1` (10x the anonymous budget). **Step 6 re-run immediately after: 4 passed, in 54.01s** -- `test_bocken_flags_overlap_not_novel`, `test_ispim_does_not_flag_direct_overlap`, `test_overlap_claims_cite_a_numbered_source`, `test_report_citation_numbers_match_related_work_list` all green. Live-test confirmation for F3/F4 is now **DONE**: real papers, real model calls, same verdicts as before (`Bocken` flags overlap with `[2]`, `ISPIM` does not), proving Hand-over 3's validation changes did not alter reasoning behaviour. **F16 (no retry on 5xx) stays open** -- the key reduces the odds of hitting this, it doesn't fix the missing retry logic.

## Decisions needed from the owner (for Stage 5)

- **Q1 - Git history.** The path stays in old commits even after F1 is fixed: `f1f8f0a` in POC3, and `5d38b11` and `58a0223` in POC2 (both public). Removing it means rewriting history and force-pushing, which would also move the `poc3-stable` and `ui-demo` tags. Recommendation: fix the file, leave history, since it is a folder path and not a credential. Your call.
- **Q2 - Where F2's web fix lives.** `app.py` (not a core file, web only) or the loader in `rvos_poc.py` (fixes web and CLI, but is a core file and so goes last).

## Positives recorded (so the review stays balanced)

- The browser renders with `textContent` and only links `https://` URLs, so the page avoids script injection from paper text.
- Uploads are capped at 10 MB, temp files are always deleted (and a test proves it), and paper text is never logged.
- Errors sent to the browser are generic, with the loader's own message as the only exception.
- The web layer is tested with a fake graph, and the loader with synthetic files, so both run in CI without secrets or NDA papers.
- Lint is clean, CI is green on `main`, and the reasoning core matches POC2 (`test_rvos_poc.py` identical).
- Citation numbers in the live UI report all match the related-work list.
- No key-like strings anywhere in the repo, and the NDA papers are not in the public repo.
- `CONTEXT.md`, the handover note and the agent handoff note give the next session a clear starting point.

## Suggested patch batches (to confirm in Stage 5)

- **Batch A (no core files):** F1, F8, F9, F10, F11 (new test file), F2 web fix, F14 check.
- **Batch B (core files, last):** F3, F4, F5, F6, F7, F2 CLI fix, and optionally F12.
