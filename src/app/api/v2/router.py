from app.api.v2.endpoints import ingestion
from fastapi import APIRouter


api_router = APIRouter()

api_router.include_router(ingestion.router, prefix="/ingest", tags=["ingestion v2"])

