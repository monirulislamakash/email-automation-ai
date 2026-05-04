from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
from src.database.base import Base

from alembic.autogenerate.render import renderers


# --- SQLite Safe Alter Column Rendering ---
@renderers.dispatch_for("alter_column")
def render_sqlite_alter_column(autogen_context, op):
    """
    Override ALTER COLUMN for SQLite.
    SQLite does NOT support:
        ALTER TABLE ... ALTER COLUMN ... TYPE
    So we rewrite all column changes using batch_alter_table.
    """
    if autogen_context.dialect.name == "sqlite":
        kw = op.kw.copy()
        stmt = f"with op.batch_alter_table('{op.table_name}') as batch_op:\n" f"    batch_op.alter_column('{op.column_name}', "

        if "existing_type" in kw:
            stmt += f"existing_type={kw['existing_type']}, "
        if "type_" in kw:
            stmt += f"type_={kw['type_']}, "
        if "existing_nullable" in kw:
            stmt += f"existing_nullable={kw['existing_nullable']}, "

        stmt = stmt.rstrip(", ") + ")"

        return stmt

    # Non-SQLite fallback
    return renderers._render_alter_column(autogen_context, op)


# --- Alembic base setup ---
config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,  # detect type changes
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            render_as_batch=True,  # Batch mode for ALL migration scripts (SQLite safe)
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
