"""
Tests for load_paper_text() -- reading a paper file (.txt, .pdf, .docx)
into paper text (see CONTEXT.md: "load" is file -> text, no model involved).

Unlike test_rvos_poc.py these need no API key and no NDA fixtures: the
papers are tiny synthetic files generated in tmp_path, so they run (and
PASS) in CI as well as locally.
"""

import subprocess
import sys
from pathlib import Path

import pytest
from docx import Document
from reportlab.pdfgen import canvas

from rvos_poc import load_paper_text

REPO_DIR = Path(__file__).parent


def _make_docx(path: Path, paragraphs: list) -> Path:
    doc = Document()
    for p in paragraphs:
        doc.add_paragraph(p)
    doc.save(str(path))
    return path


def _make_pdf(path: Path, pages: list) -> Path:
    """One page per entry; an empty string makes a blank page."""
    c = canvas.Canvas(str(path))
    for text in pages:
        if text:
            c.drawString(72, 720, text)
        c.showPage()
    c.save()
    return path


def test_loads_docx(tmp_path):
    path = _make_docx(tmp_path / "paper.docx", ["Alpha claim sentence.", "Beta method sentence."])
    text = load_paper_text(str(path))
    assert "Alpha claim sentence." in text
    assert "Beta method sentence." in text


def test_loads_pdf_across_pages(tmp_path):
    path = _make_pdf(tmp_path / "paper.pdf", ["First page sentence.", "Second page sentence."])
    text = load_paper_text(str(path))
    assert "First page sentence." in text
    assert "Second page sentence." in text


def test_loads_txt_utf8(tmp_path):
    path = tmp_path / "paper.txt"
    path.write_text("Naïve résumé.", encoding="utf-8")
    assert load_paper_text(str(path)) == "Naïve résumé."


def test_loads_txt_cp1252_fallback(tmp_path):
    path = tmp_path / "paper.txt"
    path.write_bytes("Naïve résumé.".encode("cp1252"))
    assert load_paper_text(str(path)) == "Naïve résumé."


def test_extension_match_is_case_insensitive(tmp_path):
    path = _make_pdf(tmp_path / "PAPER.PDF", ["Uppercase extension sentence."])
    assert "Uppercase extension sentence." in load_paper_text(str(path))


@pytest.mark.parametrize("name", ["paper.rtf", "paper.md", "paper"])
def test_unsupported_extension_raises_naming_supported_formats(tmp_path, name):
    path = tmp_path / name
    path.write_text("some text", encoding="utf-8")
    with pytest.raises(ValueError) as excinfo:
        load_paper_text(str(path))
    message = str(excinfo.value)
    for ext in (".txt", ".pdf", ".docx"):
        assert ext in message


def test_blank_pdf_raises_no_extractable_text(tmp_path):
    path = _make_pdf(tmp_path / "scanned.pdf", [""])
    with pytest.raises(ValueError, match="no extractable text"):
        load_paper_text(str(path))


def test_whitespace_only_docx_raises_no_extractable_text(tmp_path):
    path = _make_docx(tmp_path / "empty.docx", ["   ", ""])
    with pytest.raises(ValueError, match="no extractable text"):
        load_paper_text(str(path))


def test_cli_reports_loading_error_without_traceback(tmp_path):
    path = tmp_path / "paper.rtf"
    path.write_text("some text", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "rvos_poc.py", str(path)],
        cwd=REPO_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert ".pdf" in result.stdout + result.stderr
    assert "Traceback" not in result.stderr
