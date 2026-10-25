from logging.config import fileConfig

from sqlalchemy import engine_from_config  # noqa: F401
from sqlalchemy import pool
import asyncio 
from sqlalchemy.ext.asyncio import create_async_engine
from alembic import context
from src.core.config import settings
from src.core.database import Base
from src.models.db import (
    User,  # noqa: F401
    Repo,# noqa: F401
    UserRepo,# noqa: F401
    Job,# noqa: F401
    FileMetaData# noqa: F401
)
# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config



# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def include_object(object, name, type_, reflected, compare_to):
    # The tables owned by the Auth Service
    ignored_tables = {"users", "refresh_tokens", "alembic_version_auth"}

    # 1. Ignore the tables themselves
    if type_ == "table":
        return name not in ignored_tables
    
    # 2. Ignore any columns, indexes, or constraints attached to those tables!
    if hasattr(object, "table") and object.table is not None:
        if object.table.name in ignored_tables:
            return False

    return True


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """

    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata
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
