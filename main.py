from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from contextlib  import asynccontextmanager
from app.core.database import engine, Base
from app.api.routes.ingest import router as ingest_router
from app.api.routes.query import router as query_router
from app.api.routes.repo import router as repo_router
from app.api.routes.auth import router as auth_router
from app.core.limiter import limiter




@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code: create tables
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully.")
    yield
    # Shutdown code (if needed)
    print("Shutting down application...")


app = FastAPI(title="GitLense API", lifespan=lifespan,redirect_slashes=False)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded,_rate_limit_exceeded_handler)
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
app.include_router(auth_router)

@app.get("/health")
def health():
    return {"status": "ok"}






