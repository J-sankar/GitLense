from logging.config import fileConfig
import asyncio

from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context

# Adjust these imports to match your auth-service file structure
from src.core.config import settings
from src.core.database import Base
from src.models.db import (
    User,
    RefreshToken,
    
)

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def include_object(object, name, type_, reflected, compare_to):
    # INVERTED LOGIC: Auth service ONLY cares about these tables. 
    # It ignores everything else (like repos, jobs, file_metadata).
    if type_ == "table" and name not in ["users", "refresh_tokens", "queries"]:
        return False 
    return True


def run_migrations_offline() -> None:
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # CRITICAL: Isolate the offline migrations
        include_object=include_object,
        version_table="alembic_version_auth",
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        # CRITICAL: Isolate the online migrations
        include_object=include_object,
        version_table="alembic_version_auth",
        compare_type=True, # Recommended to catch column type changes
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    engine = create_async_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,
    )
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())