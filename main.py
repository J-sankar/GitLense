from fastapi import FastAPI
from app.models.db import User, Repo, Job, Query
from contextlib  import asynccontextmanager
from app.core.database import engine, Base, get_db




@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code: create tables
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")
    yield
    # Shutdown code (if needed)
    print("Shutting down application...")

app = FastAPI(title="GitLense API", lifespan=lifespan)

@app.get("/health")
def health():
    return {"status": "ok"}






