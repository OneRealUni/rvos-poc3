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
1. Accept PDF and DOCX input, not just plain .txt — extract text, then
   feed the existing pipeline unchanged.
2. Add GitHub Actions CI running lint + the test suite on every push.

## Explicit non-goals for this increment
- No UI / test website — a separate, later, dedicated increment.
- No fix for the untested "insufficient evidence" verdict path — logged,
  deliberately deferred, decide later.
- No new agents, no batch/multi-paper processing.
- No change to extract_claim, search_openalex, or judge_novelty's
  reasoning or prompts.

## Known constraint CI must respect
Docs/Test/*.txt are gitignored NDA fixtures, not present in CI. The test
suite already skips cleanly (not crashes) when they're missing (see
test_rvos_poc.py's second skipif). CI will therefore show tests
SKIPPED, not PASSED — that's expected, not a bug. CI verifies the code
imports and lints cleanly; it does not verify reasoning correctness
without the real fixtures and a real API key as a repo secret.
