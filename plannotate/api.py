"""Optional FastAPI web service (requires the ``api`` extra)."""

import io
import os
from typing import Annotated

from Bio import SeqIO
from Bio.SeqRecord import SeqRecord
from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

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


class ReportRow(BaseModel):
    sseqid: str
    start_location: int
    end_location: int
    strand: int
    percent_identity: float
    full_length_of_feature_in_db: int
    length_of_found_feature: int
    percent_match_length: float
    fragment: bool
    database: str
    Feature: str
    Type: str
    Description: str
    sequence: str


class AnnotateResponse(BaseModel):
    gb_file: str
    report: list[ReportRow]
    version: str


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
@app.post("/annotate", response_model=AnnotateResponse)
async def annotate_sequence(
    file: Annotated[UploadFile, File()],
    circular: Annotated[bool, Query()] = False,
    fast: Annotated[
        bool,
        Query(description="faster, lower-coverage search (snapgene and fpbase only)"),
    ] = False,
) -> AnnotateResponse:
    record = _read_record(file.filename or "", await file.read())

    circular = circular or record.annotations.get("topology") == "circular"
    sequence = str(record.seq)
    try:
        validate_sequence(sequence, MAX_SEQUENCE_LENGTH)
    except InvalidSequenceError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    construct = Construct(sequence, linear=not circular, fast=fast, cores=CORES)
    report = [
        {key.replace(" ", "_"): value for key, value in row.items()}
        for row in construct.to_csv().to_dict(orient="records")
    ]
    return AnnotateResponse(
        gb_file=construct.to_genbank(),
        report=[ReportRow(**row) for row in report],
        version=__version__,
    )
