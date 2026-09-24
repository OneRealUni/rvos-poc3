# RVOS POC3 -- status and how to run it

Carried over from POC2 (validated, both test directions pass -- see
CLAUDE.md). This increment adds PDF/DOCX input and CI. The reasoning
pipeline itself is unchanged.

## What's new in POC3
- Input can now be a .pdf, .docx, or .txt file (previously .txt only)
- GitHub Actions runs lint + tests on every push (see
  .github/workflows/tests.yml) -- tests SKIP in CI, they don't PASS,
  since the NDA fixtures aren't present there. See CLAUDE.md.

## Setup (about 5 minutes)

```bash
python -m venv venv
source venv/bin/activate        # on Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Open `.env` and paste in your real Anthropic API key.

## Run it

```bash
python rvos_poc.py "Docs/Test/Bocken.txt"        # .txt, as before
python rvos_poc.py "Docs/Test/some_paper.pdf"     # new
python rvos_poc.py "Docs/Test/some_paper.docx"    # new
```

## Everything else

Setup, known limitations, corrections history, and troubleshooting are
otherwise unchanged from POC2 -- see the full README history in git log
if needed. This file will be filled in properly once PDF/DOCX support
is actually implemented; right now it's the POC3 starting point, not a
finished document.
