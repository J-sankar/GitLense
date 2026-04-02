# tests/conftest.py
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base
from app.core.config import settings
from app.core.security import create_access_token, hash_password
from app.models.db import User, Repo, Job, UserRepo
from fastapi.testclient import TestClient
from main import app
from app.core.database import get_db
import uuid

# ── test DB ───────────────────────────────────────
TEST_DB_URL = settings.TEST_DATABASE_URL

engine      = create_engine(TEST_DB_URL)
TestSession = sessionmaker(bind=engine, autocommit=False, autoflush=False)


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Create all tables once per test session"""

    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def db(setup_db):
    """Fresh DB session per test, rolled back after"""
    connection  = engine.connect()
    transaction = connection.begin()
    session     = TestSession(bind=connection)

    yield session

    session.close()
    transaction.rollback()  # ← rollback after each test ✅
    connection.close()


@pytest.fixture(scope="function")
def client(db):
    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def test_user(db):
    user = User(
        id            = uuid.uuid4(),
        username      = "testuser",
        email         = "test@test.com",
        password_hash = hash_password("test1234")
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


@pytest.fixture
def auth_headers(test_user):
    token = create_access_token(str(test_user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_repo(db, test_user):
    repo = Repo(
        id             = uuid.uuid4(),
        name           = "test/repo",
        repo_url       = "https://github.com/test/repo",
        status         = "completed",
        chunks_indexed = 10
    )
    db.add(repo)
    db.flush()

    db.add(UserRepo(
        user_id = test_user.id,
        repo_id = repo.id
    ))
    db.flush()
    db.refresh(repo)
    return repo


@pytest.fixture
def test_job(db, test_repo):
    job = Job(
        id      = uuid.uuid4(),
        repo_id = test_repo.id,
        status  = "finished",
        progress = 100
    )
    db.add(job)
    db.flush()
    db.refresh(job)
    return job