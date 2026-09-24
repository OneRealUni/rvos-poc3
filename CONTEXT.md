# RVOS

A pipeline that takes a research paper, pulls out what it claims, and judges whether that claim is novel against published related work.

## Language

**Paper**:
The input document under assessment, supplied as a `.txt`, `.pdf` or `.docx` file.
_Avoid_: Submission, manuscript, document

**Paper text**:
The plain text of a paper after loading. The only form of the paper that later steps see.
_Avoid_: Content, raw text

**Load**:
Read a paper file of any supported format into paper text. Involves no model.
_Avoid_: Extract (reserved below), parse, ingest

**Extract**:
Have a model pull the claim, method, result and search keywords out of paper text. Never used for file reading.
_Avoid_: Load, parse

**Claim**:
The core contribution a paper asserts, as stated by extraction. Extraction also yields the paper's method and stated result.
_Avoid_: Thesis, finding

**Related work**:
Previously published works retrieved as evidence for judging a claim.
_Avoid_: Prior art, sources, references

**Verdict**:
The written novelty judgment of a claim against related work: novel, overlapping a specific numbered related work, or insufficient evidence.
_Avoid_: Score, rating, result (the paper's own stated result is a different thing)

**Report**:
The written output for one paper: its claim, method, stated result, related work list, and verdict.
_Avoid_: Output, summary
