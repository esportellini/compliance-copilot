import re
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy.dialects import postgresql

from app.db.base import Base


def _offline_postgres_sql() -> str:
    backend_dir = Path(__file__).resolve().parents[2]
    config = Config(str(backend_dir / "alembic.ini"))
    config.set_main_option("script_location", str(backend_dir / "alembic"))
    config.set_main_option(
        "sqlalchemy.url", "postgresql+psycopg://user:password@localhost/db"
    )
    output = StringIO()
    with redirect_stdout(output):
        command.upgrade(config, "head", sql=True)
    return output.getvalue()


def _columns_for(sql: str, table_name: str) -> set[str]:
    match = re.search(
        rf"CREATE TABLE {re.escape(table_name)} \((.*?)\n\);",
        sql,
        re.DOTALL,
    )
    assert match, f"migration did not create table {table_name}"
    columns = set()
    for raw_line in match.group(1).splitlines():
        line = raw_line.strip().rstrip(",")
        if not line or line.startswith(("PRIMARY ", "FOREIGN ", "CONSTRAINT ", "UNIQUE ")):
            continue
        columns.add(line.split()[0].strip('"'))
    return columns


def test_initial_migration_matches_current_model_tables_and_columns():
    sql = _offline_postgres_sql()
    migrated_tables = set(re.findall(r"CREATE TABLE ([a-z_]+) \(", sql))
    migrated_tables.discard("alembic_version")

    assert migrated_tables == set(Base.metadata.tables)

    for table in Base.metadata.sorted_tables:
        assert _columns_for(sql, table.name) == {column.name for column in table.columns}
        for index in table.indexes:
            assert f"INDEX {index.name} " in sql


def test_initial_migration_preserves_postgres_specific_types_and_identifier_index():
    sql = _offline_postgres_sql().lower()

    assert "tags varchar[]" in sql
    assert "condition jsonb" in sql
    assert "embedding jsonb" in sql
    assert "matched_rules jsonb" in sql
    assert "meta jsonb" in sql
    assert "uq_financial_products_identifier_normalized" in sql
    assert "upper(trim(identifier))" in sql

    product_tags = Base.metadata.tables["financial_products"].c.tags
    assert product_tags.type.compile(dialect=postgresql.dialect()) == "VARCHAR[]"


def test_pre_approval_keeps_optional_query_trace_with_set_null_semantics():
    table = Base.metadata.tables["pre_approval_requests"]
    source_query = table.c.source_query_id
    foreign_key = next(iter(source_query.foreign_keys))

    assert source_query.nullable is True
    assert foreign_key.target_fullname == "copilot_queries.id"
    assert foreign_key.ondelete == "SET NULL"
    assert {"copilot_initial_decision", "review_started_at"} <= {
        column.name for column in table.columns
    }
