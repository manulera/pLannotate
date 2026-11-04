"""Optional FastAPI web service (requires the ``api`` extra)."""

import io
import os
import re
from typing import Annotated

from Bio import SeqIO
from Bio.SeqRecord import SeqRecord
from fastapi import FastAPI, File, HTTPException, Query, Response, UploadFile
from fastapi.responses import RedirectResponse

from . import __version__
from .models import Construct
from .validation import (
    VALID_FASTA_EXTS,
    VALID_GENBANK_EXTS,
    InvalidSequenceError,
    get_name_ext,
    validate_sequence,
)

MAX_SEQUENCE_LENGTH = int(os.environ.get("MAX_SEQUENCE_LENGTH", 20000))
CORES = int(os.environ.get("PLANNOTATE_CORES", 1))
SNAPGENE_EXTS = [".dna"]

app = FastAPI(title="pLannotate", version=__version__)


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    return RedirectResponse(url="/docs")


def _read_record(filename: str, contents: bytes) -> SeqRecord:
    """Parse an uploaded file into a single record, raising HTTP 400 on failure."""
    _, ext = get_name_ext(filename)
    if ext in VALID_GENBANK_EXTS:
        file_format = "genbank"
    elif ext in VALID_FASTA_EXTS:
        file_format = "fasta"
    elif ext in SNAPGENE_EXTS:
        file_format = "snapgene"
    else:
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid file type, only "
                f"{', '.join(VALID_GENBANK_EXTS + VALID_FASTA_EXTS + SNAPGENE_EXTS)} "
                "are supported"
            ),
        )
    try:
        handle = (
            io.BytesIO(contents)
            if file_format == "snapgene"
            else io.StringIO(contents.decode())
        )
        # read() raises unless the file holds exactly one record
        return SeqIO.read(handle, file_format)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Error reading file") from exc


# NOTE: deliberately async while annotation blocks. The blocked event loop stops
# the worker heartbeat, which is what lets gunicorn --timeout kill a stuck request;
# a threadpool (plain def) would never trip it. Each worker serves one annotation
# at a time, so concurrency is the worker count.
@app.post(
    "/annotate",
    response_class=Response,
    responses={200: {"content": {"text/plain": {}}, "description": "GenBank file"}},
)
async def annotate_sequence(
    file: Annotated[UploadFile, File()],
    circular: Annotated[bool, Query()] = False,
    fast: Annotated[
        bool,
        Query(description="faster, lower-coverage search (snapgene and fpbase only)"),
    ] = False,
) -> Response:
    filename = file.filename or ""
    record = _read_record(filename, await file.read())

    circular = circular or record.annotations.get("topology") == "circular"
    sequence = str(record.seq)
    try:
        validate_sequence(sequence, MAX_SEQUENCE_LENGTH)
    except InvalidSequenceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    construct = Construct(sequence, linear=not circular, fast=fast, cores=CORES)
    # the upload name is user-controlled, so keep it header-safe
    stem = re.sub(r"[^A-Za-z0-9._-]", "_", get_name_ext(filename)[0]) or "construct"
    return Response(
        content=construct.to_genbank(),
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{stem}.gbk"'},
    )
