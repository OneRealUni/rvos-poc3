"""
Regression tests for rvos_poc.py, per the plan in README.md's
"Next stage: TDD, not more manual runs" section.

These run the real two-agent pipeline (live Anthropic + OpenAlex calls)
against the two known test papers and check the same two properties that
were originally verified by hand:
- Bocken.txt is a near-duplicate of a published paper -> verdict must
  flag overlap, not conclude novelty.
- The ISPIM paper is the author's own unpublished work -> verdict must
  not flag direct overlap with retrieved work.
- Any overlap claim, in either verdict, must cite a specific numbered
  source -- no vague unattributed claims.
- The three properties above are checked against the agent functions
  directly and never touch build_graph()/run(). A fourth test,
  test_report_citation_numbers_match_related_work_list, runs the pipeline
  end-to-end through run() instead, so the LangGraph wiring and the
  written report file are both actually covered.

Requires ANTHROPIC_API_KEY in the environment (.env). Each run costs a
small amount (see README.md) and results can vary between runs since
they depend on live model output -- that's the tradeoff this suite
accepts in exchange for testing real behavior instead of mocks.
"""

import os
import re
from pathlib import Path

import pytest

from rvos_poc import extract_claim, judge_novelty, run, search_openalex

BASE_DIR = Path(__file__).parent / "Docs" / "Test"
BOCKEN_PATH = BASE_DIR / "Bocken.txt"
ISPIM_PATH = BASE_DIR / "Radha Tucci ISPIM25.txt"

pytestmark = [
    pytest.mark.skipif(
        not os.environ.get("ANTHROPIC_API_KEY"),
        reason="ANTHROPIC_API_KEY not set -- these tests call the live Anthropic API",
    ),
    pytest.mark.skipif(
        not (BOCKEN_PATH.exists() and ISPIM_PATH.exists()),
        reason="NDA test fixtures not present locally -- these files are gitignored "
        "and must be provided outside git (see README.md)",
    ),
]


def _read_paper(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="cp1252")


def _run_pipeline(path: Path) -> str:
    paper_text = _read_paper(path)
    extracted = extract_claim(paper_text)
    related = search_openalex(extracted["keywords"])
    return judge_novelty(extracted, related)


def _paragraphs(text: str):
    return [p for p in re.split(r"\n\s*\n", text) if p.strip()]


def _sentences(text: str):
    return re.split(r"(?<=[.!?])\s+", text)


_HEDGE_WORDS = re.compile(
    r"\b(no|not|n't|without|insufficient|rather than|thin|tangential|"
    r"unclear|unlikely|lack(?:s|ing)?|minimal|little|none|nothing|"
    r"absen(?:ce|t))\b",
    re.IGNORECASE,
)


def _asserts_overlap(sentence: str) -> bool:
    """True for a sentence that affirmatively claims overlap, as opposed to
    one that raises and then rules overlap out (e.g. "thin and tangential
    rather than directly overlapping", "insufficient evidence of overlap")."""
    return "overlap" in sentence.lower() and not _HEDGE_WORDS.search(sentence)


@pytest.fixture(scope="module")
def bocken_verdict():
    return _run_pipeline(BOCKEN_PATH)


@pytest.fixture(scope="module")
def ispim_verdict():
    return _run_pipeline(ISPIM_PATH)


def test_bocken_flags_overlap_not_novel(bocken_verdict):
    # A raw "overlap" in verdict_lower substring check also passes for
    # "no overlap found" -- use the same affirmative-claim check the
    # citation test already relies on, so a hedged/negated sentence
    # can't accidentally satisfy this assertion.
    verdict_lower = bocken_verdict.lower()
    assert any(_asserts_overlap(s) for s in _sentences(bocken_verdict)), (
        f"Expected Bocken verdict to affirmatively flag overlap, got: {bocken_verdict!r}"
    )
    assert not re.search(r"\b(appears|is)\s+novel\b", verdict_lower), (
        f"Bocken verdict should not conclude novelty, got: {bocken_verdict!r}"
    )


def test_ispim_does_not_flag_direct_overlap(ispim_verdict):
    verdict_lower = ispim_verdict.lower()
    assert not re.search(r"overlaps?\s+(significantly|directly)\b", verdict_lower), (
        f"ISPIM verdict should not flag direct overlap, got: {ispim_verdict!r}"
    )


def test_overlap_claims_cite_a_numbered_source(bocken_verdict, ispim_verdict):
    # Checked per-paragraph rather than per-sentence: a paragraph often
    # elaborates on one overlap claim across several sentences, citing the
    # numbered source once and then referring back to it. Sentences that
    # raise and then rule out overlap (hedge words like "insufficient",
    # "rather than", "thin") don't need a citation -- only affirmative
    # overlap claims do.
    for verdict in (bocken_verdict, ispim_verdict):
        for paragraph in _paragraphs(verdict):
            if any(_asserts_overlap(s) for s in _sentences(paragraph)):
                assert re.search(r"\[\d+\]", paragraph), (
                    f"Overlap claim without a numbered source citation: {paragraph!r}"
                )


def test_report_citation_numbers_match_related_work_list(tmp_path):
    """End-to-end regression test for the I2 defect (fixed in dea739d) and
    for the LangGraph wiring itself.

    The three tests above call extract_claim/search_openalex/judge_novelty
    directly, so they never exercise build_graph() or run() -- meaning
    neither the graph wiring nor the report file's numbering was covered by
    any existing test. This test runs the real pipeline end-to-end via
    run() and checks that every [n] the verdict cites actually appears in
    the report's own numbered "Related work retrieved" list, so a
    regression like I2 (verdict cites [2], report shows an unnumbered
    bullet list) would fail here instead of shipping silently.

    Writes into tmp_path rather than next to the tracked NDA fixture, since
    run() writes its report beside whatever input path it's given.
    """
    paper_copy = tmp_path / "Bocken.txt"
    paper_copy.write_text(_read_paper(BOCKEN_PATH), encoding="utf-8")

    run(str(paper_copy))

    report_path = tmp_path / "Bocken_report.md"
    assert report_path.exists(), "run() did not write a report file"
    report_text = report_path.read_text(encoding="utf-8")

    assert "## Related work retrieved" in report_text, (
        f"Report is missing the related-work section: {report_text!r}"
    )
    assert "## Novelty verdict" in report_text, (
        f"Report is missing the verdict section: {report_text!r}"
    )
    related_section, verdict_section = report_text.split("## Novelty verdict", 1)

    cited_numbers = {int(n) for n in re.findall(r"\[(\d+)\]", verdict_section)}
    assert cited_numbers, (
        f"Expected the verdict to cite at least one numbered source, got: "
        f"{verdict_section!r}"
    )

    listed_numbers = {int(n) for n in re.findall(r"^\[(\d+)\]", related_section, re.MULTILINE)}
    missing = cited_numbers - listed_numbers
    assert not missing, (
        f"Verdict cites source(s) {sorted(missing)} that don't appear in the "
        f"report's numbered related-work list -- the two are out of sync "
        f"again. Full report:\n{report_text}"
    )
