# POC3 handover

Written 2026-09-30, replacing the 2026-09-25 version (that one only covered
PDF/DOCX loading + CI; everything below happened since). Read `CLAUDE.md`
(project rules), `CONTEXT.md` (glossary), and `Docs/review/POC3_findings_register.md`
+ `POC3_fix_plan.md` (the code-review audit trail) before touching anything.

## Where things stand

- Repo: https://github.com/OneRealUni/rvos-poc3 (public, branch `main`).
  HEAD `1e1aaf7`, pushed, CI green (`46 passed, 4 skipped`).
- Tags: `poc3-stable` (`da8f996`, pre-UI), `ui-demo` (`8b2c730`, UI landed),
  `core-baseline-pre-handover3` (`31680eb`, last commit before any Hand-over
  touched `rvos_poc.py`'s reasoning code -- rollback/diff base for that work).
- Three things are now fully built and verified: **(1)** a demo web UI on top
  of the unchanged reasoning core, **(2)** three "hand-over" rounds of an
  external code review that found and fixed real defects, **(3)** same-day
  discovery and fix of an OpenAlex reliability problem that blocked live
  testing for most of a session.
- `CLAUDE.md` still says "Current increment (UI)" -- that's stale now that
  three rounds of review/hardening have happened on top of it. Update it
  once the next real increment is chosen; I didn't touch it unprompted.
- Working tree is clean.

## The review workflow (important -- unusual, a fresh session needs this)

A **separate Claude session** (claude.ai/chat, no tool/network access) acts
as code reviewer. It drafts findings and patches, the user (HITL) pastes
them to me as `.docx` attachments, I verify independently, the user
approves each step, I execute.

- **The `.docx` files never carry the actual patch file contents** -- only
  filenames/type-badges survive the chat-to-docx export. The user always
  separately saves the real `.patch` files into `patches/` (gitignored) and
  any new docs into `Docs/review/`. Always check both before assuming
  something is missing.
- **I independently re-verify the other session's claims, not just apply
  them** -- it has no way to run code or hit a network. Examples this
  session: confirmed `actions/checkout@v6`/`setup-python@v6` really declare
  `node24` via `gh api`; confirmed a `Retry-After` header really exists on
  OpenAlex's `503`s via direct `curl`, contradicting a "correction" the
  other session proposed based on a third-party library's behaviour instead
  of a direct observation.
- **Every patch is dry-run (`git apply --check`) and usually fully applied
  + tested in a throwaway `git clone --local` to scratch, before touching
  the real working tree.**
- **The user is a hard gate before every push**, and often before every
  commit too. "Thumbs-up" / "push" / "run live tests" are the literal
  trigger phrases -- don't infer permission from adjacent context.
- **`Docs/review/*.md` is scanned for leak terms** (local path fragments,
  the Windows username) before every commit that touches it.

## What was built, in order

### UI increment (commits `81edb0a`..`8b2c730`)
- `app.py`: FastAPI, one file, `GET /` + `POST /analyse`. Calls
  `build_graph().invoke()` directly (not `run()`, which writes a file and
  returns nothing). Upload -> temp file -> `load_paper_text()` -> deleted in
  `finally`. `PaperLoadError` -> 400; upstream API errors -> 502; anything
  else -> 500. Never logs paper text or filenames. 10 MB cap. `127.0.0.1` only.
- `static/index.html`: plain HTML/CSS/JS, no framework. One button, disabled
  while running, inline error area, related-work items without an abstract
  greyed out with a note (the judge never saw them).
- `test_app.py`: `TestClient` + a fake graph, no API key needed.

### Hand-over 1 (commits `b1c8ff5`, `6894832`)
- Redacted a local path from `pytest_output.txt`.
- Pinned CI to `ubuntu-24.04` + `actions/checkout@v6`/`setup-python@v6`
  (Node 24, avoiding the 2026-10-19 `ubuntu-latest` -> Ubuntu 26 move and the
  Node 20 deprecation warnings -- confirmed gone via `gh api` annotations).

### Hand-over 2 (commits `addd53e`, `cd0a732`, `9ff2be1`, `b53dd4f`)
- Upper-bound pins on every dependency (`reportlab` had already silently
  drifted 4.x -> 5.0.1 -- exactly the risk this fixes).
- `app.py`'s loader-failure handling broadened to `except Exception` -> 400
  (was a bare 500 for a corrupt/protected PDF).
- New `test_pipeline_offline.py`: mocked, no-API tests for `extract_claim`
  validation, `search_openalex` retry, `_reconstruct_abstract`,
  `_response_text` -- with `xfail(strict=True)` markers for the confirmed-
  but-not-yet-fixed core defects (forces the marker to be removed in the
  same change that fixes the bug, or the suite fails).

### Hand-over 3 (commits `af24121`, `712c4e1`, `fc1789e` -- the first to touch `rvos_poc.py`)
- `_load_pdf` wraps any pdfplumber/pdfminer failure as `PaperLoadError`
  (same broad-catch design as the web fix, now in the loader itself).
- `_load_docx` reads table cells, not just paragraphs.
- `extract_claim` validates the model's response is a dict with a non-empty
  list of string `keywords`, retrying like any other bad sample instead of
  crashing with `AttributeError`.
- All 5 `xfail` markers from Hand-over 2 removed (the bugs they guarded are
  fixed) -- suite went from `32 passed/4 skipped/5 xfailed` to `37 passed/4 skipped`.
- Tagged `core-baseline-pre-handover3` on `31680eb` *before* any of this,
  specifically so `rvos_poc.py`/`test_rvos_poc.py` changes have a clean diff base.

### Same-day OpenAlex incident + fix (commits `c2fcac6`, `1e1aaf7` -- F16, F17)
This ran Step 6 of Hand-over 3 (the live reasoning tests) off the rails for
most of a session. Full story, in order:
1. Live tests failed 3 times with OpenAlex `503`/`504` -- the search
   cluster load-shedding **anonymous** (`mailto`-only) traffic. Diagnosed by
   direct `curl` probing outside the test suite: a short query with `mailto`
   succeeded once; the real, longer generated queries consistently failed.
   Not a Hand-over 3 regression -- `extract_claim` always completed first.
2. Root cause: `mailto` alone gets a much smaller daily budget than
   OpenAlex's documented free tier (`X-RateLimit-Limit-USD: 0.1` observed vs
   the documented `$1/day`). Fix: get a free OpenAlex API key (user did, at
   openalex.org -- costs nothing, takes minutes).
3. **First version of the fix sent the key as an `api_key` query param.**
   This leaked the real key into a live pytest traceback in this
   conversation, because `requests`' own error message includes the full
   request URL. Caught immediately; confirmed via `grep`/`git grep` that it
   never touched any file or git-tracked location -- exposure was contained
   to the chat transcript. **Corrected same session**: the key is now sent
   as an `Authorization: Bearer` header (OpenAlex documents both methods;
   only the header form can't leak this way). `OPENALEX_MAILTO` stays a
   query param -- it was never secret.
   **Open action for the user: rotate the exposed key at OpenAlex, out of
   caution** (free-tier key, low real-world stakes, but correct practice
   regardless of severity). Not confirmed done as of this writing.
4. While fixing this, also discovered `search_openalex`'s retry loop only
   covered `429` -- a `503`, `500` or `504` raised immediately with zero
   retry, even though a real `503` response was observed carrying a genuine
   `Retry-After: 60` header. Broadened retry to `429/500/503/504`, honoring
   `Retry-After` when present (capped at 30s -- don't trust an arbitrarily
   large value), falling back to fixed exponential backoff otherwise.
   **First draft of this only covered `429/500/503`** (following a
   third-party OpenAlex client library's precedent) and still failed live on
   a `504` -- caught and corrected before commit, not after.
5. Final live re-run after both fixes: **4 passed, clean, no leak.**

`PyAlex` (a real OpenAlex Python client) was referenced only as precedent
for which status codes are worth retrying -- it is **not** a dependency of
this project and there's no current reason to adopt it. Logged as `W5` in
the findings register for when it would actually pay for itself (multi-page
result walking, complex filters, citation-graph traversal).

## Findings register state (`Docs/review/POC3_findings_register.md`)

`F1` through `F17` exist. **Closed:** F1, F2, F3, F4, F5, F8, F9, F10, F16,
F17. **Open/deferred:** F6 (temperature -- decided as `RVOS_TEMPERATURE` env
var, default `0.2`, deferred to next increment, not yet implemented), F7
(verdict length), F12 (insufficient-evidence path, deliberately deferred),
F14 (browser check of a UI copy artefact), F15 (citation-numbering logic
duplicated between `run()` and `app.py`, no shared source of truth). `F11`
(offline test coverage) closed via Hand-over 2's new test file. `F13`
(live tests skip in CI) is by design, not a defect. `D1`/`D2` deferred to
POC4/RAG. One still-pending doc cleanup, deferred to a Hand-over 5
wrap-up: `Patch 10`-style correction of leftover stale text (this one:
stale text was already fixed inline, nothing outstanding here now).

## Gotchas for the next session

- **`.docx` attachments from the reviewer never carry embedded file
  content** -- always check `patches/` and `Docs/review/` for the real
  files before assuming a review round-trip is incomplete. Reading a
  `.docx` needs `python-docx` directly (`pandoc` isn't installed here);
  redirect stdout to a file with UTF-8 encoding first if the text has
  non-ASCII characters (an em dash crashed a direct console print once via
  `cp1252`).
- **Any unscoped `pytest` (`pytest -v`, no filenames) runs the 4 live
  reasoning tests too**, because this machine's `.env` has a real
  `ANTHROPIC_API_KEY` and `Docs/Test/*` fixtures are present locally -- CI
  has neither, so it always skips them, but local runs don't unless you
  name files explicitly (`pytest -v test_loading.py test_app.py
  test_pipeline_offline.py`). This caused real confusion and unintended
  live-API spend more than once. Always ask "does this need to be scoped?"
  before running bare `pytest` locally.
- **The Bash/PowerShell tool occasionally returns a transient "auto mode
  classifier gave no verdict" error** -- read-only operations still work via
  Read/Grep/Glob in the meantime; retry the shell command once after.
- **OpenAlex specifics**: `api.openalex.org` (not the marketing site) is
  what to probe for real status. `mailto` alone is not enough for reliable
  access under load -- get a free API key. Send it as an `Authorization:
  Bearer` header, never a query param (leaks into error messages that print
  the URL). Retry on `429/500/503/504`; honor `Retry-After` when present,
  cap it.
- **`gh run watch <id> --exit-status`** prints check-run annotations
  directly (e.g. Node-20 deprecation warnings) -- no need to separately
  query `gh api .../check-runs/.../annotations` unless you want a clean,
  separately-quotable JSON block.
- Git still prints LF/CRLF warnings on this machine. Harmless.
- `mattpocock-skills:grill-with-docs` and `mattpocock-skills:handoff` are
  both user-invocation-only (`disable-model-invocation: true`). The user
  must type the `/` command; I cannot invoke either myself.

## Open items

- **Rotate the exposed OpenAlex key** (F17) -- recommended, not confirmed done.
- `CLAUDE.md`'s "Current increment (UI)" section is stale; update when the
  next increment is chosen.
- F6 (temperature) and F7 (verdict length) decisions are recorded but not
  yet implemented -- deferred to the next increment on purpose.
- F15 (citation-numbering duplication between `run()` and `app.py`) --
  logged, no increment assigned.
- Six "Anticipated problems" are recorded in `POC3_fix_plan.md` (written
  2026-09-30, given the project is about to scale features rapidly, not
  just traffic): secret sprawl across providers, the resilience-gap pattern
  recurring with every new external integration, review-ceremony-vs-
  velocity tension as feature count grows, D1/D2 (12k-char truncation,
  retrieval relevance) getting worse not better with richer documents, zero
  reasoning coverage in CI ever, and the findings register itself not
  scaling past a certain size (already F1-F17 after three hand-overs on one
  increment -- close it out at the planned Hand-over 5 wrap-up before the
  next big push, not after).

## How to run

```bash
python -m venv venv
venv\Scripts\activate            # Windows
pip install -r requirements.txt
cp .env.example .env             # Anthropic key, OPENALEX_MAILTO, OPENALEX_API_KEY
python rvos_poc.py "Docs/Test/Bocken.pdf"    # CLI -- or .docx / .txt
uvicorn app:app --host 127.0.0.1 --port 8000 # UI -- open the printed address
ruff check .
pytest -v test_loading.py test_app.py test_pipeline_offline.py  # offline, no cost
pytest -v test_rvos_poc.py                   # live, costs a little, needs .env + fixtures
```
