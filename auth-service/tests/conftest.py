# tests/conftest.py
import os
import uuid
import pytest
import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.core.database import Base, get_db
from src.core.security import create_access_token, hash_password
from src.models.db import User
from src.core.redis import redis_manager
from main import app

TEST_DB_URL = os.getenv("TEST_DATABASE_URL")

# --- REMOVE any global engine or TestSession variables from here ---

@pytest.fixture(scope="session")
def event_loop():
    """Provides a single unified asyncio loop context across the testing session"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_engine(event_loop):
    """Creates the async engine strictly inside the active test loop context"""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest.fixture(scope="function")
async def db(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """Provides a completely isolated, savepoint-backed transactional session per test function"""
    local_sessionmaker = async_sessionmaker(
        bind=test_engine, class_=AsyncSession, expire_on_commit=False
    )
    
    # 1. Spin up a fresh session instance
    async with local_sessionmaker() as session:
        # 2. Start a real root transaction (we don't use 'async with' here to prevent auto-committing)
        await session.begin()
        
        # 3. Create a nested SAVEPOINT transaction strictly local to this test function
        nested_trans = await session.begin_nested()
        
        yield session
        
        if nested_trans.is_active:
            await nested_trans.rollback()
            
        # 4. Clean out the underlying connection roots safely 🔄
        if session.in_transaction():
            await session.rollback()
        
        # 6. Close the session explicitly to return the channel to the pool cleanly
        await session.close()

@pytest.fixture(scope="function")
async def client(db: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Async Client that overrides get_db dependency and executes lifespan hooks"""
    
    async def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
        
    app.dependency_overrides.clear()


@pytest.fixture(scope="function")
async def test_user(db)->User:
    user = User(
        id=uuid.uuid4(),
        username="testuser",
        email="test@test.com",
        password_hash=hash_password("test1234"),
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


@pytest.fixture(scope="function")
def auth_headers(test_user):
    token = create_access_token(str(test_user.id))
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture(autouse=True)
async def mock_redis(monkeypatch):
    """
    Autouse Mock Fixture: Intercepts redis_manager.publish_event 
    and replaces it with a dead fake call so tests don't require a real Redis container.
    """
    fake_publish = AsyncMock(return_value="mocked_msg_123")
    monkeypatch.setattr(redis_manager, "publish_event", fake_publish)
    
    # Also patch the underlying raw client just in case
    redis_manager.client = AsyncMock()
    yield fake_publish