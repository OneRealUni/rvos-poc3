# Handoff: RVOS POC3, post-UI-and-review

Written for a fresh agent. Focus of the next session: not yet chosen -- the
user has said they want to move to "MVP" soon, with feature/functionality
scaling rather than traffic scaling, but has not scoped what that actually
means yet. Do not assume; ask.

## Hard constraints from the user (do not break these)

- **Explain the exact git/GitHub command sequence before running it, and
  wait for explicit approval before every commit and especially every
  push.** Trigger phrases actually used: "yes", "push", "thumbs-up", "run
  live tests". Do not infer permission from adjacent conversation context.
- **Stage files by name. Never `git add .`** or sweep in untracked files.
- **Verify every push on GitHub afterwards** (`gh run list` / `gh api
  .../check-runs`), not just local output.
- **Never commit anything under `Docs/Test/`** -- NDA papers, blanket
  gitignored. The repo is public.
- **Scan any `Docs/review/*.md` change for leak terms** (local path
  fragments, the Windows username) before staging it.
- **Get a "thumbs-up" before kicking off anything costly or core-touching**,
  even mid-task. The user said this explicitly after I acted on an urgent
  fix without asking first -- treat it as a standing preference, not a
  one-off complaint about that instance.
- **Redact secrets in live output, not just in files.** A real API key
  leaked into a live test's traceback this session because it was sent as a
  URL query param and `requests`' own error message printed the full URL.
  When verifying anything with a real secret, read it from `.env` and never
  print it -- and design the code itself so a failure can't print it either
  (header, not query param, for anything actually secret).

## Where things stand

Full technical state, commit history, and gotchas are in `HANDOVER.md`
(rewritten 2026-09-30) -- read that, don't ask the user to re-explain it.
Headline: repo `OneRealUni/rvos-poc3`, HEAD `68c388f`, **3 commits ahead of
`origin/main`, not yet pushed** (last pushed commit `1e1aaf7` has CI green,
`46 passed, 4 skipped`), tags `poc3-stable`/`ui-demo`/`core-baseline-pre-handover3`.
Working tree is clean -- but don't assume push state from that; check plain
`git status` for the ahead-of-origin line.

## Read these instead of asking the user to re-explain

| Need | Where |
|---|---|
| Rules for working in this repo | `CLAUDE.md` |
| Glossary (load vs extract, paper text, verdict, ...) | `CONTEXT.md` |
| Full technical history, commits, gotchas, how to run | `HANDOVER.md` |
| Code-review audit trail: findings F1-F17, decisions, open items | `Docs/review/POC3_findings_register.md`, `POC3_fix_plan.md` |
| Sibling project's handoff, for format | https://github.com/OneRealUni/rvos-poc2/blob/main/handoff-rvos-poc2-maintenance.md |

Do not restate any of the above; follow it.

## How this user works

- Wants **crystal-clear, bullet-point answers** -- said explicitly "we are
  getting too verbose" at one point. Keep responses tight by default.
- Wants **genuine technical opinions, not just execution**. Explicitly asked
  for pushback, an honest "lead dev/MLOps/DevOps/Tech Lead" assessment, and
  independent verification of claims -- including the *other* Claude
  session's claims (see below). Being right and catching the other
  session's mistakes is valued, not treated as friction.
- Sometimes asks for a **"grilling" style**: forcing, decision-converging
  questions rather than a menu of options, when a real decision is needed.
- Runs a **separate claude.ai/chat session as an independent code
  reviewer**, and plays HITL/arbiter between it and this session. Its
  `.docx` attachments never carry embedded patch-file content -- only
  filenames/type-badges survive the export -- but the real files always
  turn up separately in `patches/` and `Docs/review/`. Check both before
  assuming anything is missing.
- Delegates process decisions once trust is established (e.g. let me
  combine two small fixes into one round-trip instead of two, once I gave a
  reasoned case for it being safe) -- but always wants the reasoning stated
  plainly first, not just the outcome.

## Lessons learned the hard way, this session (beyond `HANDOVER.md`'s Gotchas)

- **Cross-check the external reviewer's claims against your own direct
  evidence from earlier in the same conversation, not just its citations.**
  Caught twice: it claimed OpenAlex's `Retry-After` header "isn't
  documented anywhere" (true of their docs, false of the actual response --
  I'd captured it directly with `curl`); its suggested retry-status list
  omitted `504`, which I had *also* already observed directly and should
  have caught before implementing, not after a second live failure.
- **A fix's first draft matching a cited precedent (a third-party library,
  a review session's patch) doesn't mean it matches your own prior
  evidence.** Always reconcile against what you've personally verified in
  the current conversation before calling something done.

## Unverified -- don't treat as fact

- Whether the user has rotated the exposed OpenAlex key. Recommended, not
  confirmed as of this handoff.
- OpenAlex's pricing/rate-limit figures (free tier `$1/day`, paid tiers
  starting `$5,000/year`) were verified live against `help.openalex.org` on
  2026-09-30. Reasonably current then; OpenAlex could change this without
  notice. Don't assume stale, but don't re-verify without a reason to.
- Whether `CLAUDE.md`'s "Current increment (UI)" section has been updated
  by the time you read this -- check fresh.

## Open decisions for the user

- Rotate the OpenAlex key, or accept the low residual risk.
- What the next increment/MVP scope actually is -- mentioned, never scoped.
- F6 (temperature, decided as `0.2` via `RVOS_TEMPERATURE`, not yet
  implemented -- deliberately deferred), F7 (verdict length), F15 (citation
  numbering duplicated between `run()` and `app.py`) -- all logged in the
  register, none scheduled to an increment.
- The findings register's own planned Hand-over 5 wrap-up (regenerate
  `pytest_output.txt`, close out F1-F17) hasn't started. The user's own
  "anticipated problems" note in `POC3_fix_plan.md` recommends doing this
  *before* the next big feature push, not after -- worth raising early.

## Suggested skills

Call the Skill tool for these when the situation fits:
- `mattpocock-skills:grilling`: if the next session needs to nail down MVP
  scope with the user -- this exact discipline was used heavily and well
  received this session.
- `mattpocock-skills:tdd`: this project is strict about test-first on every
  `rvos_poc.py`/`test_rvos_poc.py` change; keep doing that, not just when asked.
- `mattpocock-skills:diagnosing-bugs`: if a new external dependency (another
  LLM provider, a vector store, anything else) starts failing the way
  OpenAlex did -- the diagnostic pattern (probe directly, don't trust a
  status page, check what's actually being sent) transfers directly.
- `mattpocock-skills:code-review`: worth a self-review pass before handing
  work to the external claude.ai reviewer session, so it isn't the one
  finding simple things.
- `mattpocock-skills:domain-modeling`: only if `CONTEXT.md` terms need
  extending for new MVP features.

Not invocable by the agent (user must type them): `mattpocock-skills:grill-with-docs`,
`mattpocock-skills:handoff`.

## First moves

1. `git status` (plain, not `--short` -- only the plain form shows an
   "ahead of origin" line; as of this writing there are 3 unpushed commits),
   `git log --oneline -5`, `gh auth status`.
2. Read `CLAUDE.md`, `CONTEXT.md`, then `HANDOVER.md` in full.
3. If `git status` shows `HANDOVER.md` modified, ask the user whether to
   commit it now before doing anything else.
4. Ask the user what they actually want to work on next -- "MVP" was
   mentioned but never scoped in this conversation. Do not assume.
