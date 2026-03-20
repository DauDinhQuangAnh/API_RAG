from __future__ import annotations

import os
from typing import Any

import psycopg2
from dotenv import load_dotenv
from psycopg2.extras import RealDictCursor

load_dotenv()


class PostgreSQLConnection:
    """PostgreSQL Database Connection Manager"""

    def __init__(self):
        self.host = os.getenv("DB_HOST", "localhost")
        self.port = os.getenv("DB_PORT", "5432")
        self.database = os.getenv("DB_NAME", "weavecarbon")
        self.user = os.getenv("DB_USER", "postgres")
        self.password = os.getenv("DB_PASSWORD", "123")
        self.connection = None
        self.cursor = None

    def __enter__(self) -> "PostgreSQLConnection":
        self.connect()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.disconnect()

    def connect(self) -> "PostgreSQLConnection":
        """Establish connection to PostgreSQL."""
        if self.connection and getattr(self.connection, "closed", 1) == 0:
            return self

        try:
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password,
            )
            self.cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            return self
        except Exception as exc:
            self.connection = None
            self.cursor = None
            raise RuntimeError(f"Failed to connect to PostgreSQL: {exc}") from exc

    def disconnect(self) -> None:
        """Close connection."""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
        self.cursor = None
        self.connection = None

    def _ensure_connected(self) -> None:
        if not self.connection or getattr(self.connection, "closed", 1) != 0:
            self.connect()

    def execute_query(
        self, query: str, params: tuple[Any, ...] | None = None
    ) -> list[dict[str, Any]]:
        """Execute SELECT query and return results."""
        self._ensure_connected()
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except Exception as exc:
            raise RuntimeError(f"Query execution failed: {exc}") from exc

    def execute_update(
        self, query: str, params: tuple[Any, ...] | None = None
    ) -> int:
        """Execute INSERT/UPDATE/DELETE and return affected rows."""
        self._ensure_connected()
        try:
            self.cursor.execute(query, params)
            self.connection.commit()
            return self.cursor.rowcount
        except Exception as exc:
            self.connection.rollback()
            raise RuntimeError(f"Update execution failed: {exc}") from exc

    def test_connection(self) -> dict:
        """Test database connection."""
        try:
            with self:
                self.cursor.execute("SELECT version();")
                version = self.cursor.fetchone()
            return {
                "status": "success",
                "message": "Connected to PostgreSQL successfully",
                "database": self.database,
                "version": version["version"] if version else None,
            }
        except Exception as exc:
            return {
                "status": "error",
                "message": str(exc),
                "database": self.database,
            }


def get_db_connection() -> PostgreSQLConnection:
    """Create a fresh database connection manager for each request flow."""
    return PostgreSQLConnection()
