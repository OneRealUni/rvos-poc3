# POC3 handover

Written 2026-09-25 so a fresh session can continue without this conversation.
Read `CLAUDE.md` (project rules) and `CONTEXT.md` (glossary) first.

## Where things stand

POC3 is **done and pushed**. Both increments in CLAUDE.md are complete:

1. PDF/DOCX input: `load_paper_text()` in `rvos_poc.py`.
2. GitHub Actions CI running lint + tests on every push.

- Repo: https://github.com/OneRealUni/rvos-poc3 (public, default branch `main`)
- First CI run (id 36078144049) passed: `ruff check .` clean, **11 passed, 4 skipped**.
  The 4 skips are the live reasoning tests; they skip in CI because the NDA
  fixtures and API key are absent. That is expected (see CLAUDE.md), not a bug.
- Local run (with `.env` key and fixtures): **15 passed** in about 65 s.
  Output is saved in `pytest_output.txt` (committed).
- The reasoning core (`extract_claim`, `search_openalex`, `judge_novelty`,
  their prompts, the LangGraph wiring) is **unchanged** from POC2.
- Working tree was clean after the push. This file and
  `handoff-rvos-poc3-maintenance.md` were committed afterwards (2026-09-26).

## Commits (fresh history, no POC2 history carried over)

| Commit | What |
|---|---|
| `1970910` | Baseline: POC2 reasoning core + POC3 starting point (8 files) |
| `43df0f1` | Add `CONTEXT.md`; blanket-ignore `Docs/Test/*` in `.gitignore` |
| `6271232` | PDF/DOCX loading, `test_loading.py`, `reportlab` dev dependency, README/CLAUDE.md updates |
| `f1f8f0a` | Add `pytest_output.txt` |

## What was built

In `rvos_poc.py`:
- `load_paper_text(path)` picks a reader by extension, case-insensitive:
  `.txt` (utf-8, cp1252 fallback, as before), `.pdf` (`pdfplumber`, page text
  joined by newlines), `.docx` (`python-docx`, body paragraphs only).
- `PaperLoadError(ValueError)` is raised for an unsupported extension (message
  names `.txt`, `.pdf`, `.docx`) and for a file with no extractable text
  (e.g. a scanned PDF; no OCR).
- `run()` calls `load_paper_text()`. `__main__` catches only `PaperLoadError`,
  prints `Error: ...` to stderr and exits 1. Other exceptions still traceback.
- Usage string and module docstring mention `.txt|.pdf|.docx`.

In `test_loading.py` (new, 11 tests, no API key or NDA files needed):
synthetic DOCX (python-docx) and PDF (reportlab) built in `tmp_path`; covers
docx, multi-page pdf, txt utf-8 and cp1252, upper-case extension, three
unsupported names (`.rtf`, `.md`, no extension), blank PDF, whitespace-only
DOCX, and the CLI error path (exit 1, no traceback).

## Decisions made (grill-with-docs session) and why

- Loader lives in `rvos_poc.py`, not a new module (minimum code; tests already import from it).
- Unsupported extension is an error, with no text fallback. A silent fallback
  would feed binary junk to the model and yield a confident but meaningless verdict.
- No usable text is an error, not a warning. OCR is out of scope.
- Plain extraction with no cleanup (no PDF header/footer stripping, no DOCX
  tables). Only the first 12,000 characters reach the model anyway. If a real
  paper extracts badly, make that its own increment with a failing test.
- Loading tests are synthetic and separate, so CI has something that actually
  PASSES. CLAUDE.md's "Known constraint" section was updated to say so.
- Vocabulary (see `CONTEXT.md`): **load** = file to paper text; **extract** is
  reserved for the model pulling out the claim. Other terms: Paper, Paper text,
  Claim, Related work, Verdict, Report.
- `Docs/Test/*` is blanket-ignored. The three NDA papers exist locally as
  `.txt`, `.pdf` and `.docx` (`Bocken`, `Radha Tucci ISPIM25`, `Tucci`).
  The old per-filename ignore list did not cover PDF/DOCX; the blanket rule does.
- Fixture **file names** appear in tracked files (`test_rvos_poc.py`,
  `README.md`). The user checked the NDA terms and confirmed this is fine to publish.
- No `ANTHROPIC_API_KEY` repo secret. The reasoning tests would skip without
  the NDA fixtures anyway, and the repo is public.
- No ADRs written: nothing met all three criteria (hard to reverse, surprising, real trade-off).
- The repo is `rvos-poc3` (the user first said `rvos-poc`, then corrected it).

## Things I did that were not explicitly agreed

- The "no extractable text" check runs for **every** format, so an empty `.txt`
  now errors too (it used to go to the model). One uniform check was simpler than a special case.
- Added the `PaperLoadError` subclass so the CLI doesn't swallow unrelated `ValueError`s.
- Fixed a ruff finding in my own test (`subprocess.run(..., check=False)`); CI would have failed on it.

## Verified

- Loader read all three real NDA files locally (Bocken.pdf ~121k chars, ISPIM pdf ~29k, Tucci.docx ~6k).
- Live end-to-end CLI run on `Bocken.pdf`: verdict flagged near-verbatim
  overlap with source [2], correct direction. The report file is clean UTF-8;
  the mojibake seen in the PowerShell console was display only.
- Clean-clone CI rehearsal (no `.env`, no `Docs/`, fresh venv, empty API key): 11 passed, 4 skipped.
- Pre-push scan of all commits for key-like strings: none. Tracked files: exactly
  the code and docs plus `.env.example`; nothing from `Docs/`, `.env`, `venv/`.

## Gotchas for the next session

- **Shell:** this Windows box has no `tee`, `tail` or `grep` in Git Bash.
  Use PowerShell or the dedicated tools. PowerShell 5.1's `Tee-Object` writes
  UTF-16; write files with `[IO.File]::WriteAllLines(..., UTF8Encoding($false))`.
  `pytest_output.txt` was produced this way. `Remove-Item` with a regex-looking
  string in the command was blocked by the harness.
- **Tokens:** `gh` is logged in as `OneRealUni`. Scopes are now
  `gist, read:org, repo, workflow`. `workflow` was added on 2026-09-25 (via
  `gh auth refresh -h github.com -s workflow`) because pushing
  `.github/workflows/tests.yml` needs it. Revoke it if you no longer want it.
- **`.env`** holds the real key locally (gitignored). `load_dotenv()` runs at
  import, so local pytest runs the live tests even without the shell variable set.
- **Live tests** call Anthropic and OpenAlex and cost a little per run; results vary slightly.
- Git prints LF/CRLF warnings on this machine. Harmless.
- `grill-with-docs` (Matt Pocock's plugin, v1.2.3) is installed and enabled, but has
  `disable-model-invocation: true`. The user must type
  `/mattpocock-skills:grill-with-docs`; I cannot invoke it myself.

## Open items and not-done (all explicitly out of scope for POC3)

- The "insufficient evidence" verdict path is still untested (logged and deferred in CLAUDE.md).
- UI / test website is a later, separate increment.
- No OCR for scanned PDFs. No DOCX table extraction or PDF header/footer cleanup.
- CI housekeeping, optional: GitHub warns that `actions/checkout@v4` and
  `actions/setup-python@v5` target Node 20 (currently forced to Node 24), and
  that `ubuntu-latest` moves to Ubuntu 26 on 2026-10-19 (pin `ubuntu-24.04` to avoid a surprise).
- `CLAUDE.md` still describes POC3 as the "current increment". Update it when the next increment is chosen.
- This file is committed to the public repo (the user's choice, 2026-09-26). It was
  scanned first: no local paths, keys or email addresses.
- The user half-remembers an on-screen "10 pound offer if I do /something" and will
  report the exact wording if seen. I never said it (checked the transcript).
  Treat it as unverified until it is confirmed against an official source.

## How to run

```bash
python -m venv venv
venv\Scripts\activate            # Windows
pip install -r requirements.txt
cp .env.example .env             # then put the real Anthropic key in .env
python rvos_poc.py "Docs/Test/Bocken.pdf"    # or .docx / .txt
ruff check .
pytest -v
```
