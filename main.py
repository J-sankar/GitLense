from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from contextlib  import asynccontextmanager
from app.core.database import engine, Base
from app.api.v1.router import api_router as v1_router
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

app.include_router(v1_router, prefix="/api/v1")

@app.get("/health")
def health():
    return {"status": "ok"}






