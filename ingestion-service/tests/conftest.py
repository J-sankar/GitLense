import os
import pytest  # noqa: F401
import pytest_asyncio
import uuid
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from httpx import ASGITransport, AsyncClient
from src.core.database import get_db
from src.models.db import Base, Repo, Job,User
from main import app

TEST_DB_URL = os.getenv(
    "TEST_DATABASE_URL", 
    "postgresql+asyncpg://test_user:test_password@localhost:5432/test_db"
)

engine = create_async_engine(TEST_DB_URL, echo=False)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


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


@pytest_asyncio.fixture(scope="function")
async def test_repo(db_session):
    repo = Repo(
        id=uuid.uuid4(),
        repo_url="https://github.com/test-owner/test-repo",
        status="pending",
        name="test-repo"
    )
    db_session.add(repo)
    await db_session.flush() # Flush assigns the UUID and makes it queryable without committing
    
    return repo

@pytest_asyncio.fixture(scope="function")
async def test_user(db_session):
    user = User(
        id=uuid.uuid4()
    )
    db_session.add(user)
    await db_session.flush()

    return user


@pytest_asyncio.fixture(scope="function")
async def test_user_repo(db_session):
    repo = Repo(
        id=uuid.uuid4(),
        repo_url="https://github.com/test-owner/test-repo",
        status="pending",
        name="test-repo"
    )
    db_session.add(repo)
    await db_session.flush() # Flush assigns the UUID and makes it queryable without committing
    
    return repo

@pytest_asyncio.fixture(scope="function")
async def test_job(db_session, test_repo):
    """
    Inserts a standard pending Job linked to the test_repo.
    """
    job = Job(
        id=uuid.uuid4(),
        repo_id=test_repo.id,
        status="pending"
    )
    db_session.add(job)
    await db_session.flush()
    
    return job


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Async Client that automatically overrides the database dependency"""
    
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac
        
    app.dependency_overrides.clear()