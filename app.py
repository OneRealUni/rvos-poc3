"""
RVOS demo web app: upload a paper, get the Report back on screen.

A thin wrapper around rvos_poc.py, which is not modified here. Calls
build_graph().invoke() directly rather than run(), because run() writes a
file and returns nothing. Demo only: no auth, no storage, one user.

Run:
    uvicorn app:app --host 127.0.0.1 --port 8000
"""

import logging
import os
import tempfile
from pathlib import Path

import anthropic
import requests
from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse

from rvos_poc import PaperLoadError, build_graph, load_paper_text

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
INDEX_PAGE = Path(__file__).parent / "static" / "index.html"

log = logging.getLogger("uvicorn.error")
app = FastAPI(title="RVOS demo")


@app.get("/")
def index():
    return FileResponse(INDEX_PAGE)


@app.post("/analyse")
def analyse(file: UploadFile):
    """Load the uploaded paper, run the pipeline, return the Report as JSON.

    The paper is written to a temp file only because load_paper_text() takes
    a path; the file is deleted before the response is built. Paper text and
    filenames are never logged, and errors sent to the browser are generic
    except for the loader's own message."""
    data = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(413, f"File is larger than {MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")

    display_name = os.path.basename(file.filename or "upload")
    ext = os.path.splitext(display_name)[1]
    fd, tmp_path = tempfile.mkstemp(suffix=ext)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        try:
            paper_text = load_paper_text(tmp_path)
        except PaperLoadError as e:
            raise HTTPException(400, str(e).replace(tmp_path, display_name)) from e
        except Exception as e:
            # A library failure inside the loader (corrupt or password-
            # protected PDF, a malformed DOCX) is a bad file, not a server
            # crash -- see the fix plan, F2. This is deliberately broad: we
            # don't enumerate every PDF/DOCX library's exception types here,
            # since that knowledge belongs in load_paper_text, not this app.
            log.error("Loader failed unexpectedly: %s", type(e).__name__)
            raise HTTPException(
                400,
                "Could not read this file. It may be corrupted, "
                "password-protected, or in an unsupported format.",
            ) from e
    finally:
        os.unlink(tmp_path)

    try:
        result = build_graph().invoke({"paper_text": paper_text})
    except (anthropic.APIError, requests.RequestException, ValueError) as e:
        # ValueError covers extract_claim giving up on malformed model JSON
        # (json.JSONDecodeError is a ValueError) or missing keys.
        log.error("Analysis service failed: %s", type(e).__name__)
        raise HTTPException(502, "The analysis service failed. Please try again.") from e
    except Exception as e:
        log.error("Unexpected failure: %s", type(e).__name__)
        raise HTTPException(500, "Something went wrong. Please try again.") from e

    extracted = result["extracted"]
    return {
        "claim": extracted["claim"],
        "method": extracted["method"],
        "result": extracted["result"],
        "related": [
            {
                "n": i + 1,
                "title": w["title"],
                "year": w["year"],
                "url": w["id"],
                "has_abstract": bool(w["abstract"]),
            }
            for i, w in enumerate(result["related"])
        ],
        "verdict": result["verdict"],
    }
