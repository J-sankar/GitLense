
from app.api.v1.endpoints import ingest, auth,query,repo
from fastapi import APIRouter

api_router = APIRouter()

api_router.include_router(ingest.router, prefix="/ingest", tags=["ingestion"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(query.router, prefix="/query", tags=["query"])
api_router.include_router(repo.router, prefix="/repos", tags=["repos"])
