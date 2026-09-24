# RVOS POC3 -- status and how to run it

Carried over from POC2 (validated, both test directions pass -- see
CLAUDE.md). This increment adds PDF/DOCX input and CI. The reasoning
pipeline itself is unchanged.

## What's new in POC3
- Input can now be a .pdf, .docx, or .txt file (previously .txt only)
- GitHub Actions runs lint + tests on every push (see
  .github/workflows/tests.yml). The loading tests (test_loading.py) PASS
  in CI; the four reasoning tests SKIP, since the NDA fixtures and API
  key aren't there. See CLAUDE.md.

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

The report is written next to the input file as `<name>_report.md`.

Loading is plain text extraction, no cleanup: PDFs give each page's text
(two-column layouts may interleave), DOCX gives body paragraphs only
(tables, headers and footers are skipped). Only the first 12,000
characters reach the model, as before. The run stops with an error
(exit status 1) for any other file type, and for a file with no
extractable text -- e.g. a scanned, image-only PDF, since OCR is not
supported.

## Tests

```bash
ruff check .
pytest -v
```

`test_loading.py` needs no API key or NDA files (it generates tiny
PDF/DOCX files on the fly). `test_rvos_poc.py` calls the live Anthropic
and OpenAlex APIs and needs `Docs/Test/Bocken.txt` and
`Docs/Test/Radha Tucci ISPIM25.txt` locally; it skips if they or the API
key are missing. `Docs/Test/*` is gitignored -- never commit NDA papers.

## Everything else

Setup, known limitations, corrections history, and troubleshooting are
otherwise unchanged from POC2. Terminology (load vs. extract, paper text,
verdict) is defined in CONTEXT.md.
