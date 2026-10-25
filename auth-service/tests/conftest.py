# tests/conftest.py
import os
import uuid
import pytest
import pytest_asyncio
import asyncio
from typing import AsyncGenerator
from unittest.mock import AsyncMock
from httpx import ASGITransport, AsyncClient
from sqlalchemy import event
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from src.core.database import Base, get_db
from src.core.security import create_access_token, hash_password
from src.models.db import User
from src.core.redis import redis_manager
from main import app

TEST_DB_URL = os.getenv("TEST_DATABASE_URL")
# engine = create_async_engine(TEST_DB_URL, echo=False)
# --- REMOVE any global engine or TestSession variables from here ---

@pytest.fixture(scope="session")
def event_loop():
    """Provides a single unified asyncio loop context across the testing session"""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()

@pytest_asyncio.fixture(scope="session")
async def test_engine():
    """Creates the engine and tables ONCE for the whole test run"""
    engine = create_async_engine(TEST_DB_URL, echo=False)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        
    yield engine
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture(scope="function")
async def db(test_engine) -> AsyncGenerator[AsyncSession, None]:
    """
    Creates a pristine, isolated database transaction for EVERY test.
    Intercepts app commits so they don't hit the real database, 
    and rolls everything back when the test finishes.
    """
    async with test_engine.connect() as conn:
        await conn.begin()
        await conn.begin_nested()
        
        session = AsyncSession(bind=conn, expire_on_commit=False)

        # THIS IS THE MAGIC: It intercepts the application's db.commit() 
        # and turns it into a savepoint instead of a real commit.
        @event.listens_for(session.sync_session, "after_transaction_end")
        def restart_savepoint(sync_session, trans):
            if conn.closed:
                return
            if not conn.in_nested_transaction():
                conn.sync_connection.begin_nested()

        yield session

        await session.close()
        await conn.rollback()


@pytest_asyncio.fixture(scope="function")
async def db_session():
    async with engine.connect() as connection:
        transaction = await connection.begin()
        await connection.begin_nested()
        session = AsyncSession(bind=connection,expire_on_commit=False )


        # @event.listens_for(session.sync_session, "after_transaction_end")
        # def restart_savepoint(sync_session, trans):
        #     if connection.closed:
        #         return
        #     if not connection.in_nested_transaction():
        #         connection.sync_connection.begin_nested()
        yield session

        await session.close()
        await transaction.rollback()

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