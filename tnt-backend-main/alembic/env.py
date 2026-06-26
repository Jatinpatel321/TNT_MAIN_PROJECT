from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from app.database.base import Base
from app.database.session import DATABASE_URL

import app.modules.group_cart.model  # noqa: F401
import app.modules.ledger.model  # noqa: F401
import app.modules.menu.model  # noqa: F401
import app.modules.notifications.model  # noqa: F401
import app.modules.admin.broadcast_model  # noqa: F401
import app.modules.admin.model  # noqa: F401
import app.modules.calendar.model  # noqa: F401
import app.modules.orders.history_model  # noqa: F401
import app.modules.orders.model  # noqa: F401
import app.modules.payments.model  # noqa: F401
import app.modules.rewards.model  # noqa: F401
import app.modules.slots.model  # noqa: F401
import app.modules.stationery.job_model  # noqa: F401
import app.modules.stationery.service_model  # noqa: F401
import app.modules.users.model  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
