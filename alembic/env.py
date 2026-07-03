import os
from logging.config import fileConfig

from sqlalchemy import create_engine, pool

from alembic import context
from app.db.url import normalize_database_url

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

database_url = normalize_database_url(os.environ.get("DATABASE_URL", ""))
if not database_url:
    raise RuntimeError("DATABASE_URL environment variable is required for migrations")
config.set_main_option("sqlalchemy.url", database_url)

from app.db.session import Base
import app.db.models  # noqa: F401 — ensure all models are registered

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(database_url, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
