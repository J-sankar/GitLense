from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(50), unique=True, nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)

    repos = relationship("Repo", back_populates="user" ,cascade="all, delete")
    queries = relationship("Query", back_populates="user" ,cascade="all, delete")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Repo(Base):
    __tablename__ = "repos"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    repo_url = Column(String(200), nullable=False)
    status         = Column(String(20), default="queued")
    chunks_indexed = Column(Integer, default=0)
    error_message  = Column(Text)

    user = relationship("User", back_populates="repos")
    jobs    = relationship("Job",   back_populates="repo",  cascade="all, delete")
    queries = relationship("Query", back_populates="repo", cascade="all, delete")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_id = Column(UUID(as_uuid=True), ForeignKey("repos.id"), nullable=False)
    status = Column(String(20), nullable=False, default="queued")
    progress = Column(Integer, nullable=False, default=0)
    error_message = Column(Text)

    repo = relationship("Repo", back_populates="jobs")

    started_at   = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Query(Base):
    __tablename__ = "queries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    repo_id = Column(UUID(as_uuid=True), ForeignKey("repos.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    source = Column(JSONB, nullable=False)
    user = relationship("User", back_populates="queries")
    repo = relationship("Repo", back_populates="queries")

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())