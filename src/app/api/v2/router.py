from app.api.v2.endpoints import ingest
from fastapi import APIRouter


api_router = APIRouter()

api_router.include_router(ingest.router, prefix="/ingest", tags=["ingestion v2"])

