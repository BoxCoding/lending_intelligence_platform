"""AA ingestion endpoints."""
from fastapi import APIRouter, HTTPException

from app.schemas.models import AAPayload, CustomerProfile
from app.services.pipeline import process_aa_payload

router = APIRouter(tags=["Account Aggregator"])


@router.post("/aa/upload", response_model=CustomerProfile, summary="Ingest AA JSON and run full scoring pipeline")
def upload_aa(payload: AAPayload) -> CustomerProfile:
    if not payload.accounts or not any(a.transactions for a in payload.accounts):
        raise HTTPException(status_code=422, detail="Payload contains no transactions")
    try:
        return process_aa_payload(payload)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Pipeline failure: {exc}") from exc
