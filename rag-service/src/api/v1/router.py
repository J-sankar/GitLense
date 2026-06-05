
from src.api.v1.endpoints import query
from fastapi import APIRouter

api_router = APIRouter()

api_router.include_router(query.router, prefix="/query", tags=["query"])

