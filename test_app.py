"""
Tests for the demo web app (app.py): upload a paper, get a Report back.

Like test_loading.py these need no API key or NDA files. build_graph is
replaced with a fake, so the routes, upload handling and error mapping are
tested here and PASS in CI; the reasoning itself stays covered by the live
tests in test_rvos_poc.py.
"""

import os

import pytest
import requests
from docx import Document
from fastapi.testclient import TestClient

import app as app_module
import rvos_poc

FAKE_STATE = {
    "extracted": {
        "claim": "A claim.",
        "method": "A method.",
        "result": "A result.",
        "keywords": ["one", "two"],
    },
    "related": [
        {"title": "Paper A", "year": 2020, "id": "https://openalex.org/W1", "abstract": "Has one."},
        {"title": "Paper B", "year": 2021, "id": "https://openalex.org/W2", "abstract": ""},
    ],
    "verdict": "Overlaps with [1].",
}


class FakeGraph:
    def invoke(self, state):
        self.seen = state
        return FAKE_STATE


@pytest.fixture
def client(monkeypatch):
    monkeypatch.setattr(app_module, "build_graph", lambda: FakeGraph())
    return TestClient(app_module.app)


def _upload(client, name, data):
    return client.post("/analyse", files={"file": (name, data)})


def test_txt_upload_returns_report(client):
    r = _upload(client, "paper.txt", b"Some paper text.")
    assert r.status_code == 200
    body = r.json()
    assert body["claim"] == "A claim."
    assert body["method"] == "A method."
    assert body["result"] == "A result."
    assert body["verdict"] == "Overlaps with [1]."
    assert "keywords" not in body


def test_related_work_is_numbered_and_flags_missing_abstracts(client):
    body = _upload(client, "paper.txt", b"Some paper text.").json()
    assert body["related"] == [
        {"n": 1, "title": "Paper A", "year": 2020, "url": "https://openalex.org/W1", "has_abstract": True},
        {"n": 2, "title": "Paper B", "year": 2021, "url": "https://openalex.org/W2", "has_abstract": False},
    ]


def test_docx_upload_is_loaded_and_fed_to_the_pipeline(client, tmp_path, monkeypatch):
    seen = {}

    class Recording(FakeGraph):
        def invoke(self, state):
            seen.update(state)
            return FAKE_STATE

    monkeypatch.setattr(app_module, "build_graph", lambda: Recording())
    path = tmp_path / "paper.docx"
    doc = Document()
    doc.add_paragraph("Docx paragraph text.")
    doc.save(str(path))
    r = _upload(client, "paper.docx", path.read_bytes())
    assert r.status_code == 200
    assert "Docx paragraph text." in seen["paper_text"]


def test_unsupported_type_is_400_with_user_readable_message(client):
    r = _upload(client, "paper.rtf", b"some text")
    assert r.status_code == 400
    detail = r.json()["detail"]
    for ext in (".txt", ".pdf", ".docx"):
        assert ext in detail
    assert "paper.rtf" in detail
    assert "tmp" not in detail.lower()


def test_empty_file_is_400_no_extractable_text(client):
    r = _upload(client, "paper.txt", b"")
    assert r.status_code == 400
    assert "no extractable text" in r.json()["detail"]


def test_oversized_upload_is_413(client, monkeypatch):
    monkeypatch.setattr(app_module, "MAX_UPLOAD_BYTES", 10)
    r = _upload(client, "paper.txt", b"x" * 11)
    assert r.status_code == 413


def test_upstream_failure_is_502_with_generic_message(client, monkeypatch):
    class Failing:
        def invoke(self, state):
            raise requests.ConnectionError("secret-host:1234 refused")

    monkeypatch.setattr(app_module, "build_graph", lambda: Failing())
    r = _upload(client, "paper.txt", b"Some paper text.")
    assert r.status_code == 502
    assert "secret-host" not in r.text


def test_unexpected_failure_is_500_with_generic_message(client, monkeypatch):
    class Broken:
        def invoke(self, state):
            raise RuntimeError("internal detail Some paper text")

    monkeypatch.setattr(app_module, "build_graph", lambda: Broken())
    r = _upload(client, "paper.txt", b"Some paper text.")
    assert r.status_code == 500
    assert "internal detail" not in r.text
    assert "Traceback" not in r.text


def test_temp_file_is_deleted_after_success_and_after_failure(client, monkeypatch):
    paths = []
    real_load = rvos_poc.load_paper_text

    def spy(path):
        paths.append(path)
        return real_load(path)

    monkeypatch.setattr(app_module, "load_paper_text", spy)
    _upload(client, "paper.txt", b"Some paper text.")
    _upload(client, "paper.rtf", b"some text")
    assert len(paths) == 2
    assert not any(os.path.exists(p) for p in paths)


def test_index_page_is_served(client):
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
