# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## How to work in this repo
- State assumptions explicitly; if uncertain, ask rather than guess.
- Minimum code that solves the problem — nothing speculative, no unrequested flexibility.
- Touch only what the task requires; match existing style; don't "improve" unrelated code.
- Turn every task into a verifiable goal (write a test, then make it pass) rather than "make it work."
- patches/ is gitignored: local patch files are scratch copies of changes already applied. There is no "commit review-evidence patches" routine in this repo -- CI now provides that evidence.

## Current state
POC1: extract_claim -> LangGraph -> judge_novelty, both test directions
pass. POC3: PDF/DOCX/TXT input via load_paper_text(), GitHub Actions CI
(loading tests pass, reasoning tests skip by design -- see below). Both
are done and unchanged by this increment. See README.md, CONTEXT.md,
test_loading.py, and test_rvos_poc.py.

## Completed increments
- POC1/POC2: the two-agent reasoning pipeline, orchestrated with
  LangGraph. Validated on both known directions (overlap, novel).
- POC3: PDF/DOCX/TXT input (load_paper_text, three format loaders) and
  GitHub Actions CI. 11 loading tests pass in CI; 4 reasoning tests skip
  there by design (NDA fixtures are gitignored, never reach GitHub).

## Current increment (UI)
A lightweight, single-page demo web app -- a PhD-researcher persona
testing the tool for the first time, not a production interface.
1. Frontend: plain HTML/CSS/vanilla JS. No Next.js, no React, no
   frontend build tooling of any kind.
2. Backend: FastAPI, one lightweight file.
3. The new file(s) import from rvos_poc.py; rvos_poc.py itself is not
   modified. Call build_graph().invoke(...) directly, not run() -- run()
   writes <name>_report.md next to the input file and returns nothing,
   but the web response needs the result back directly.
4. Upload a .pdf, .docx, or .txt file; display the same claim / method /
   result / related work / verdict a CLI run would produce.
5. No MCP anywhere in this increment.

## Explicit non-goals for this increment
- No production concerns: no auth, no multi-user handling, no
  deployment pipeline, no scalability work. This is a demo, not a
  release.
- No fix for the untested "insufficient evidence" verdict path --
  logged, deliberately deferred, decide later.
- No new agents, no batch/multi-paper processing.
- No change to extract_claim, search_openalex, judge_novelty, or
  load_paper_text's existing behaviour.

## Known constraint CI must respect
Docs/Test/* is gitignored (NDA fixtures in any format), not present in CI.
test_rvos_poc.py already skips cleanly (not crashes) when they're missing
(see its second skipif). CI will therefore show those four reasoning tests
SKIPPED, not PASSED — that's expected, not a bug. test_loading.py uses
synthetic files generated in tmp_path, so its tests PASS in CI. CI
verifies the code imports, lints cleanly, and loads PDF/DOCX/txt
correctly; it does not verify reasoning correctness. No ANTHROPIC_API_KEY
secret is set: the reasoning tests would skip without the NDA fixtures
anyway, and a public repo has no use for an idle credential.
