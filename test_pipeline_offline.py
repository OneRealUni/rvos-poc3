"""
Offline unit tests for rvos_poc.py: pure functions and mocked API calls only.

Unlike test_rvos_poc.py, nothing here needs ANTHROPIC_API_KEY, a network
connection, or the NDA paper fixtures, so these run on every push in CI --
see the fix plan, Patch 5 (F11).

Some tests below use xfail(strict=True): the pattern is, when a confirmed
defect needs a regression test before it's fixed, mark that test xfail so
strict=True fails the SUITE the moment it starts passing unexpectedly --
forcing whoever fixes the bug to remove the marker in the same change,
rather than the fix landing silently with a stale marker left behind.
Hand-over 3 fixed every defect this file had marked that way (F2's loader
half, F3, F4, F5), so none remain here for now.
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


def test_extract_claim_rejects_keywords_that_are_not_a_list(monkeypatch):
    monkeypatch.setattr(
        rp.client.messages,
        "create",
        lambda **k: _fake_resp('{"claim":"c","method":"m","result":"r","keywords":"not a list"}'),
    )
    with pytest.raises((ValueError, TypeError)):
        rp.extract_claim("paper text")


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
    def __init__(self, status_code, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload or {}
        self.headers = headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")

    def json(self):
        return self._payload


def test_search_openalex_retries_on_429_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def fake_get(url, params, timeout, headers=None):
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


def test_search_openalex_sends_api_key_as_authorization_header_when_set(monkeypatch):
    """OPENALEX_API_KEY, when set, must be sent as an Authorization: Bearer
    header, NOT a query param -- a query param ends up in request.raise_for_
    status()'s error message (`for url: ...`), which leaked the real key into
    a live test's traceback (see the findings register, F17 correction)."""
    monkeypatch.setenv("OPENALEX_API_KEY", "test-key-123")
    seen = {}

    def fake_get(url, params, timeout, headers=None):
        seen["params"] = params
        seen["headers"] = headers
        return _FakeHTTPResponse(200, {"results": []})

    monkeypatch.setattr(rp.requests, "get", fake_get)
    rp.search_openalex(["x"])
    assert seen["headers"].get("Authorization") == "Bearer test-key-123"
    assert "api_key" not in seen["params"]  # never in params -- see docstring


def test_search_openalex_omits_authorization_header_when_no_key(monkeypatch):
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    seen = {}

    def fake_get(url, params, timeout, headers=None):
        seen["headers"] = headers
        return _FakeHTTPResponse(200, {"results": []})

    monkeypatch.setattr(rp.requests, "get", fake_get)
    rp.search_openalex(["x"])
    assert "Authorization" not in seen["headers"]


def test_search_openalex_does_not_retry_a_genuinely_unretryable_error(monkeypatch):
    """404/401-class errors are not transient -- retrying cannot help.
    (500 moved to the retryable set below, per F16/F17: OpenAlex's own
    heavy-load 503s were observed alongside a Retry-After header, and
    PyAlex -- an established OpenAlex client -- treats 500 as transient too.)"""
    calls = {"n": 0}

    def fake_get(*a, **k):
        calls["n"] += 1
        return _FakeHTTPResponse(404)

    monkeypatch.setattr(rp.requests, "get", fake_get)
    with pytest.raises(requests.HTTPError):
        rp.search_openalex(["x"])
    assert calls["n"] == 1


def test_search_openalex_retries_on_503_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def fake_get(url, params, timeout, headers=None):
        calls["n"] += 1
        if calls["n"] < 3:
            return _FakeHTTPResponse(503)
        return _FakeHTTPResponse(200, {"results": []})

    monkeypatch.setattr(rp.requests, "get", fake_get)
    monkeypatch.setattr(rp.time, "sleep", lambda seconds: None)
    rp.search_openalex(["x"])
    assert calls["n"] == 3


def test_search_openalex_retries_on_504_then_succeeds(monkeypatch):
    """504 Gateway Timeout was directly observed from OpenAlex under load
    (see the findings register, F16) -- Cloudflare timing out waiting on
    OpenAlex's own backend, a step worse than a deliberate 503 rejection."""
    calls = {"n": 0}

    def fake_get(url, params, timeout, headers=None):
        calls["n"] += 1
        if calls["n"] < 2:
            return _FakeHTTPResponse(504)
        return _FakeHTTPResponse(200, {"results": []})

    monkeypatch.setattr(rp.requests, "get", fake_get)
    monkeypatch.setattr(rp.time, "sleep", lambda seconds: None)
    rp.search_openalex(["x"])
    assert calls["n"] == 2


def test_search_openalex_retries_on_500_then_succeeds(monkeypatch):
    calls = {"n": 0}

    def fake_get(url, params, timeout, headers=None):
        calls["n"] += 1
        if calls["n"] < 2:
            return _FakeHTTPResponse(500)
        return _FakeHTTPResponse(200, {"results": []})

    monkeypatch.setattr(rp.requests, "get", fake_get)
    monkeypatch.setattr(rp.time, "sleep", lambda seconds: None)
    rp.search_openalex(["x"])
    assert calls["n"] == 2


def test_search_openalex_honors_retry_after_header_when_present(monkeypatch):
    """Directly observed on a real OpenAlex 503 (see the findings register,
    F16): 'Retry-After: 60', also listed in access-control-expose-headers --
    a real, deliberate part of their response, not just inferred from a
    third-party client's behaviour."""
    slept = []

    def fake_get(url, params, timeout, headers=None):
        return _FakeHTTPResponse(503, headers={"Retry-After": "5"}) if not slept \
            else _FakeHTTPResponse(200, {"results": []})

    monkeypatch.setattr(rp.requests, "get", fake_get)
    monkeypatch.setattr(rp.time, "sleep", lambda seconds: slept.append(seconds))
    rp.search_openalex(["x"])
    assert slept == [5.0]


def test_search_openalex_falls_back_to_backoff_without_retry_after(monkeypatch):
    calls = {"n": 0}
    slept = []

    def fake_get(url, params, timeout, headers=None):
        calls["n"] += 1
        if calls["n"] < 2:
            return _FakeHTTPResponse(503)  # no Retry-After header
        return _FakeHTTPResponse(200, {"results": []})

    monkeypatch.setattr(rp.requests, "get", fake_get)
    monkeypatch.setattr(rp.time, "sleep", lambda seconds: slept.append(seconds))
    rp.search_openalex(["x"])
    assert slept == [1.0]  # 2 ** 0, the existing exponential pattern


def test_search_openalex_caps_retry_after_at_30_seconds(monkeypatch):
    slept = []

    def fake_get(url, params, timeout, headers=None):
        return _FakeHTTPResponse(503, headers={"Retry-After": "3600"}) if not slept \
            else _FakeHTTPResponse(200, {"results": []})

    monkeypatch.setattr(rp.requests, "get", fake_get)
    monkeypatch.setattr(rp.time, "sleep", lambda seconds: slept.append(seconds))
    rp.search_openalex(["x"])
    assert slept == [30.0]


def test_search_openalex_ignores_unparseable_retry_after(monkeypatch):
    """Retry-After can legally be an HTTP-date per spec; we only support the
    delay-seconds form. An unparseable value falls back to backoff rather
    than crashing."""
    calls = {"n": 0}
    slept = []

    def fake_get(url, params, timeout, headers=None):
        calls["n"] += 1
        if calls["n"] < 2:
            return _FakeHTTPResponse(503, headers={"Retry-After": "Wed, 30 Sep 2026 17:00:00 GMT"})
        return _FakeHTTPResponse(200, {"results": []})

    monkeypatch.setattr(rp.requests, "get", fake_get)
    monkeypatch.setattr(rp.time, "sleep", lambda seconds: slept.append(seconds))
    rp.search_openalex(["x"])
    assert slept == [1.0]


# ---------------------------------------------------------------------------
# load_paper_text -- confirmed defects, not yet fixed (F2 loader, F5)
# ---------------------------------------------------------------------------


def test_load_paper_text_wraps_a_corrupt_pdf_as_paper_load_error(tmp_path):
    bad = tmp_path / "bad.pdf"
    bad.write_bytes(b"not a pdf")
    with pytest.raises(rp.PaperLoadError):
        rp.load_paper_text(str(bad))


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
