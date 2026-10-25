from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import  DeclarativeBase
from src.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    pool_recycle=300, 
    pool_pre_ping=True,
    connect_args={"timeout": 10},
    )

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

class Base(DeclarativeBase):
    pass

async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:

            raise
        finally:
            await session.close()

