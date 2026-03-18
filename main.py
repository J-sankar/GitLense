from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.models.db import User, Repo, Job, Query
from contextlib  import asynccontextmanager
from app.core.database import engine, Base, get_db
from app.api.routes.ingest import router as ingest_router
from app.api.routes.query import router as query_router
from app.api.routes.repo import router as repo_router





@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code: create tables
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")
    yield
    # Shutdown code (if needed)
    print("Shutting down application...")

app = FastAPI(title="GitLense API", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",    # React dev server
        "http://localhost:5173",    # Vite dev server
        "http://localhost:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(ingest_router)
app.include_router(query_router)
app.include_router(repo_router)

@app.get("/health")
def health():
    return {"status": "ok"}






