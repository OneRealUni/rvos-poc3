"""
Offline unit tests for rvos_poc.py: pure functions and mocked API calls only.

Unlike test_rvos_poc.py, nothing here needs ANTHROPIC_API_KEY, a network
connection, or the NDA paper fixtures, so these run on every push in CI --
see the fix plan, Patch 5 (F11).

Some tests below are marked xfail(strict=True): they encode a defect the
findings register already confirmed (F2 loader, F3, F4, F5) but that hasn't
been fixed yet -- that fix is scoped to Batch B, a later hand-over, because
it touches rvos_poc.py. strict=True means the test SUITE FAILS the moment
one of these starts passing unexpectedly, which is the point: it forces
whoever fixes the underlying bug to also remove the xfail marker in the
same change, rather than the fix landing silently with a stale marker left
behind.
"""

import json
import types

import pytest
import requests
from docx import Document

import rvos_poc as rp


def _fake_resp(text):
    """Build a fake Anthropic response with the shape _response_text expects."""
    return types.SimpleNamespace(content=[types.SimpleNamespace(type="text", text=text)])


# ---------------------------------------------------------------------------
# _response_text
# ---------------------------------------------------------------------------


def test_response_text_skips_a_leading_thinking_block():
    resp = types.SimpleNamespace(
        content=[
            types.SimpleNamespace(type="thinking", text=None),
            types.SimpleNamespace(type="text", text="  hello  "),
        ]
    )
    assert rp._response_text(resp) == "hello"


def test_response_text_raises_if_no_text_block_is_present():
    resp = types.SimpleNamespace(content=[types.SimpleNamespace(type="thinking", text=None)])
    with pytest.raises(ValueError):
        rp._response_text(resp)


# ---------------------------------------------------------------------------
# _reconstruct_abstract
# ---------------------------------------------------------------------------


def test_reconstruct_abstract_handles_empty_or_missing_index():
    assert rp._reconstruct_abstract(None) == ""
    assert rp._reconstruct_abstract({}) == ""


def test_reconstruct_abstract_rebuilds_word_order_from_positions():
    inverted = {"widgets": [2], "Selling": [0], "is": [1], "fun": [3]}
    assert rp._reconstruct_abstract(inverted) == "Selling is widgets fun"


# ---------------------------------------------------------------------------
# extract_claim -- already-working retry behaviour (I1 fix, POC2)
# ---------------------------------------------------------------------------


def test_extract_claim_retries_on_malformed_json_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def fake_create(**kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return _fake_resp("not json")
        return _fake_resp('{"claim":"c","method":"m","result":"r","keywords":["a"]}')

    monkeypatch.setattr(rp.client.messages, "create", fake_create)
    result = rp.extract_claim("paper text")
    assert result["keywords"] == ["a"]
    assert calls["n"] == 2


def test_extract_claim_retries_when_a_required_key_is_missing(monkeypatch):
    calls = {"n": 0}

    def fake_create(**kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return _fake_resp('{"claim":"c","method":"m","result":"r"}')  # no keywords
        return _fake_resp('{"claim":"c","method":"m","result":"r","keywords":["a"]}')

    monkeypatch.setattr(rp.client.messages, "create", fake_create)
    result = rp.extract_claim("paper text")
    assert result["keywords"] == ["a"]
    assert calls["n"] == 2


def test_extract_claim_gives_up_after_three_bad_samples(monkeypatch):
    monkeypatch.setattr(rp.client.messages, "create", lambda **k: _fake_resp("not json"))
    with pytest.raises(json.JSONDecodeError):
        rp.extract_claim("paper text")


# ---------------------------------------------------------------------------
# extract_claim -- confirmed defects, not yet fixed (F3, F4)
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="F3: a JSON array (or other non-object) crashes with AttributeError "
    "instead of being retried like any other bad sample",
)
def test_extract_claim_retries_when_response_is_not_a_json_object(monkeypatch):
    calls = {"n": 0}

    def fake_create(**kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return _fake_resp("[]")
        return _fake_resp('{"claim":"c","method":"m","result":"r","keywords":["a"]}')

    monkeypatch.setattr(rp.client.messages, "create", fake_create)
    result = rp.extract_claim("paper text")
    assert result["keywords"] == ["a"]


@pytest.mark.xfail(
    strict=True,
    reason="F4: extract_claim accepts a keywords value that isn't a list at all",
)
def test_extract_claim_rejects_keywords_that_are_not_a_list(monkeypatch):
    monkeypatch.setattr(
        rp.client.messages,
        "create",
        lambda **k: _fake_resp('{"claim":"c","method":"m","result":"r","keywords":"not a list"}'),
    )
    with pytest.raises((ValueError, TypeError)):
        rp.extract_claim("paper text")


@pytest.mark.xfail(
    strict=True,
    reason="F4: extract_claim accepts an empty keywords list, which OpenAlex "
    "then receives as an empty search query",
)
def test_extract_claim_rejects_an_empty_keywords_list(monkeypatch):
    monkeypatch.setattr(
        rp.client.messages,
        "create",
        lambda **k: _fake_resp('{"claim":"c","method":"m","result":"r","keywords":[]}'),
    )
    with pytest.raises(ValueError):
        rp.extract_claim("paper text")


# ---------------------------------------------------------------------------
# search_openalex -- already-working 429 backoff
# ---------------------------------------------------------------------------


class _FakeHTTPResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")

    def json(self):
        return self._payload


def test_search_openalex_retries_on_429_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def fake_get(url, params, timeout):
        calls["n"] += 1
        if calls["n"] < 3:
            return _FakeHTTPResponse(429)
        payload = {
            "results": [
                {
                    "title": "A paper",
                    "publication_year": 2020,
                    "id": "https://openalex.org/W1",
                    "abstract_inverted_index": None,
                }
            ]
        }
        return _FakeHTTPResponse(200, payload)

    monkeypatch.setattr(rp.requests, "get", fake_get)
    monkeypatch.setattr(rp.time, "sleep", lambda seconds: None)  # don't really wait
    result = rp.search_openalex(["circular", "economy"])
    assert calls["n"] == 3
    assert result[0]["title"] == "A paper"


def test_search_openalex_raises_after_persistent_429(monkeypatch):
    monkeypatch.setattr(rp.requests, "get", lambda *a, **k: _FakeHTTPResponse(429))
    monkeypatch.setattr(rp.time, "sleep", lambda seconds: None)
    with pytest.raises(requests.HTTPError):
        rp.search_openalex(["x"])


def test_search_openalex_does_not_retry_a_non_429_error(monkeypatch):
    calls = {"n": 0}

    def fake_get(*a, **k):
        calls["n"] += 1
        return _FakeHTTPResponse(500)

    monkeypatch.setattr(rp.requests, "get", fake_get)
    with pytest.raises(requests.HTTPError):
        rp.search_openalex(["x"])
    assert calls["n"] == 1


# ---------------------------------------------------------------------------
# load_paper_text -- confirmed defects, not yet fixed (F2 loader, F5)
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    strict=True,
    reason="F2 (loader): a corrupt PDF raises pdfminer's own exception, "
    "not PaperLoadError -- app.py now papers over this (Patch 4), but the "
    "CLI does not",
)
def test_load_paper_text_wraps_a_corrupt_pdf_as_paper_load_error(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf")
    with pytest.raises(rp.PaperLoadError):
        rp.load_paper_text(str(bad))


@pytest.mark.xfail(
    strict=True,
    reason="F5: load_paper_text only reads DOCX paragraphs, not table cells",
)
def test_load_paper_text_reads_docx_table_cells():
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as d:
        path = Path(d) / "table_only.docx"
        doc = Document()
        table = doc.add_table(rows=1, cols=1)
        table.rows[0].cells[0].text = "Real paper text in a table"
        doc.save(str(path))
        text = rp.load_paper_text(str(path))
    assert "Real paper text in a table" in text
