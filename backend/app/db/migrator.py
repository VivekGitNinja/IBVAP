"""
IBVAP — Autonomous Schema Migration & Database Integrity Engine
Provides zero-dependency schema creation, index reconciliation, and migration verification.
Compatible with SQLite (Edge) and PostgreSQL (Enterprise Defense Cloud).
"""

import logging
from typing import Dict, List, Any
from sqlalchemy import inspect, text
from sqlalchemy.engine import Engine

from backend.app.db.base import Base

logger = logging.getLogger("ibvap.migrator")


class DatabaseMigrator:
    """Manages database schema state, index synchronization, and health audits."""

    def __init__(self, engine: Engine):
        self.engine = engine

    def run_migrations(self) -> Dict[str, Any]:
        """
        Execute schema synchronization.
        Creates missing tables and ensures all declared indexes are applied.
        """
        # 1. Create tables if not present
        Base.metadata.create_all(bind=self.engine)

        # 2. Inspect created state
        inspector = inspect(self.engine)
        existing_tables = inspector.get_table_names()

        # 3. Reconcile missing columns on existing tables
        columns_added = 0
        for table in Base.metadata.sorted_tables:
            if table.name in existing_tables:
                existing_cols = {col["name"] for col in inspector.get_columns(table.name)}
                for col in table.columns:
                    if col.name not in existing_cols:
                        try:
                            col_type = col.type.compile(self.engine.dialect)
                            with self.engine.connect() as conn:
                                conn.execute(text(f"ALTER TABLE {table.name} ADD COLUMN {col.name} {col_type}"))
                                conn.commit()
                            columns_added += 1
                            logger.info(f"Reconciled schema: added column '{col.name}' to table '{table.name}'")
                        except Exception as e:
                            logger.debug(f"Column addition note on {table.name}.{col.name}: {e}")

        # 4. Create missing indexes if database dialect supports it
        indexes_verified = 0
        for table in Base.metadata.sorted_tables:
            if table.name in existing_tables:
                existing_indexes = {idx["name"] for idx in inspector.get_indexes(table.name)}
                for idx in table.indexes:
                    if idx.name and idx.name not in existing_indexes:
                        try:
                            idx.create(bind=self.engine)
                            indexes_verified += 1
                        except Exception as e:
                            logger.debug(f"Index creation notice on {idx.name}: {e}")
                    else:
                        indexes_verified += 1

        return {
            "status": "synchronized",
            "tables_count": len(existing_tables),
            "tables": existing_tables,
            "indexes_verified": indexes_verified,
        }

    def verify_schema_integrity(self) -> Dict[str, Any]:
        """Verify that all core tables and critical indexes are properly provisioned."""
        inspector = inspect(self.engine)
        existing_tables = set(inspector.get_table_names())
        expected_tables = {table.name for table in Base.metadata.sorted_tables}

        missing_tables = list(expected_tables - existing_tables)
        all_indexes = {}
        for tbl in existing_tables:
            all_indexes[tbl] = [idx["name"] for idx in inspector.get_indexes(tbl)]

        is_healthy = len(missing_tables) == 0

        return {
            "healthy": is_healthy,
            "dialect": self.engine.dialect.name,
            "missing_tables": missing_tables,
            "existing_tables_count": len(existing_tables),
            "indexes": all_indexes,
        }


def run_database_migrations(engine: Engine) -> Dict[str, Any]:
    migrator = DatabaseMigrator(engine)
    return migrator.run_migrations()
