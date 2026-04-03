from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base


class User(Base):
    __tablename__ = "users"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username      = Column(String(50), unique=True, nullable=False)
    email         = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), onupdate=func.now())

    # ✅ User's repos go through UserRepo now
    user_repos = relationship("UserRepo", back_populates="user", cascade="all, delete")
    queries    = relationship("Query",    back_populates="user", cascade="all, delete")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete")


class Repo(Base):
    __tablename__ = "repos"

    id             = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name           = Column(String(255), nullable=False)
    repo_url       = Column(String(200), nullable=False, unique=True)  # ✅ unique
    status         = Column(String(20), default="placed")
    chunks_indexed = Column(Integer, default=0)
    error_message  = Column(Text)
    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    updated_at     = Column(DateTime(timezone=True), onupdate=func.now())

    # ✅ No user_id FK — repo is shared
    user_repos = relationship("UserRepo", back_populates="repo", cascade="all, delete")
    jobs       = relationship("Job",      back_populates="repo", cascade="all, delete")
    queries    = relationship("Query",    back_populates="repo", cascade="all, delete")
    files = relationship("FileMetadata", back_populates="repo", cascade="all, delete-orphan")

    


class UserRepo(Base):
    __tablename__ = "user_repos"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    repo_id    = Column(UUID(as_uuid=True), ForeignKey("repos.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # ✅ Relationships defined on both sides
    user = relationship("User", back_populates="user_repos")
    repo = relationship("Repo", back_populates="user_repos")

    __table_args__ = (
        UniqueConstraint("user_id", "repo_id", name="uq_user_repo"),
    )


class Job(Base):
    __tablename__ = "jobs"

    id            = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_id       = Column(UUID(as_uuid=True), ForeignKey("repos.id"), nullable=False)
    status        = Column(String(20), nullable=False, default="queued")
    progress      = Column(Integer, nullable=False, default=0)
    error_message = Column(Text)
    started_at    = Column(DateTime(timezone=True))
    completed_at  = Column(DateTime(timezone=True))
    created_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at    = Column(DateTime(timezone=True), onupdate=func.now())

    repo = relationship("Repo", back_populates="jobs")


class Query(Base):
    __tablename__ = "queries"

    id       = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id  = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    repo_id  = Column(UUID(as_uuid=True), ForeignKey("repos.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer   = Column(Text, nullable=False)
    source   = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    user = relationship("User", back_populates="queries")
    repo = relationship("Repo", back_populates="queries")



class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id         = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id    = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    token      = Column(String(500),        nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="refresh_tokens")

    __table_args__ = (
        Index("ix_refresh_tokens_token", "token"),
    )



class FileMetaData(Base):
    __tablename__ = "file_metadata" 

    id  = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    repo_id    = Column(UUID(as_uuid=True), ForeignKey("repos.id", ondelete="CASCADE"), nullable=False)
    file_path = Column(Text , nullable=False)
    file_hash = Column(String(64), nullable=False)
    imports    = Column(JSONB, default=[]) 
    exports    = Column(JSONB, default=[])
    summary  = Column(Text)
    status     = Column(String(20), default="pending")
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    repo  = relationship("Repo", back_populates="files")
    __table_args__ = (
        Index("idx_repo_file_path", "repo_id", "file_path", unique=True),
        {"extend_existing": True}
    )