# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## How to work in this repo
- State assumptions explicitly; if uncertain, ask rather than guess.
- Minimum code that solves the problem — nothing speculative, no unrequested flexibility.
- Touch only what the task requires; match existing style; don't "improve" unrelated code.
- Turn every task into a verifiable goal (write a test, then make it pass) rather than "make it work."

## Current state
This repo is copied from the validated POC2 (extract_claim -> LangGraph ->
judge_novelty, both test directions pass). See README.md and
test_rvos_poc.py for how it works. The reasoning core is unchanged from
POC2 — POC3 does not touch it.

## Current increment (POC3)
Two things, both plumbing, neither touching the reasoning:
1. Accept PDF and DOCX input, not just plain .txt — load paper text, then
   feed the existing pipeline unchanged. ("Load" = file to text; "extract"
   is reserved for the model pulling out the claim. See CONTEXT.md.)
2. Add GitHub Actions CI running lint + the test suite on every push.

## Explicit non-goals for this increment
- No UI / test website — a separate, later, dedicated increment.
- No fix for the untested "insufficient evidence" verdict path — logged,
  deliberately deferred, decide later.
- No new agents, no batch/multi-paper processing.
- No change to extract_claim, search_openalex, or judge_novelty's
  reasoning or prompts.

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
