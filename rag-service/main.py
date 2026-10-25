from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib  import asynccontextmanager
from src.core.database import engine, Base
from src.api.v1.router import api_router as v1_router
from src.core.logger import get_logger

logger = get_logger(__name__)



@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code: create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully.")
  
    yield
    # Shutdown code (if needed)
    await engine.dispose()
    logger.info("Shutting down application...")


app = FastAPI(title="hey-rag", lifespan=lifespan,redirect_slashes=False)
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






