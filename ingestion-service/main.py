from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
# from slowapi import _rate_limit_exceeded_handler
# from slowapi.errors import RateLimitExceeded
from contextlib  import asynccontextmanager
from src.core.database import engine, Base
from src.api.v2.router import api_router as v2_router
# from src.core.limiter import limiter
from src.core.redis import redis_manager
from src.core.logger import get_logger

logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup code: create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created successfully.")
    await redis_manager.init_redis()
    yield
    # Shutdown code (if needed)
    await engine.dispose()
    logger.info("Shutting down application...")


app = FastAPI(title="hey-auth", lifespan=lifespan,redirect_slashes=False)
# app.state.limiter = limiter
# app.add_exception_handler(RateLimitExceeded,_rate_limit_exceeded_handler)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(v2_router, prefix="/api/v2")

@app.get("/health")
def health():
    return {"status": "ok"}






