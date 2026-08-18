"""Alembic migration environment for Genuine RX.

Reads GENUINE_RX_DB_URL from the environment so no credentials are
committed to version control. The placeholder in alembic.ini is ignored.
"""

import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# --------------------------------------------------------------------------- #
# Alembic Config object — access to values in alembic.ini
# --------------------------------------------------------------------------- #
config = context.config

# Override sqlalchemy.url from environment (mandatory — never use the ini value)
db_url = os.environ.get("GENUINE_RX_DB_URL")
if db_url:
    config.set_main_option("sqlalchemy.url", db_url)

# Set up logging from the ini file
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# We use raw SQL migrations (op.execute) rather than metadata-based autogenerate,
# so target_metadata stays None.
target_metadata = None


# --------------------------------------------------------------------------- #
# Offline mode (generates SQL without connecting)
# --------------------------------------------------------------------------- #
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


# --------------------------------------------------------------------------- #
# Online mode (runs against a live database)
# --------------------------------------------------------------------------- #
def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
