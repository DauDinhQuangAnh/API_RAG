import os
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

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
    
    def connect(self):
        """Establish connection to PostgreSQL"""
        try:
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            self.cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            return True
        except Exception as e:
            raise Exception(f"Failed to connect to PostgreSQL: {str(e)}")
    
    def disconnect(self):
        """Close connection"""
        if self.cursor:
            self.cursor.close()
        if self.connection:
            self.connection.close()
    
    def execute_query(self, query: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """Execute SELECT query and return results"""
        try:
            self.cursor.execute(query, params)
            return self.cursor.fetchall()
        except Exception as e:
            raise Exception(f"Query execution failed: {str(e)}")
    
    def execute_update(self, query: str, params: Optional[tuple] = None) -> int:
        """Execute INSERT/UPDATE/DELETE and return affected rows"""
        try:
            self.cursor.execute(query, params)
            self.connection.commit()
            return self.cursor.rowcount
        except Exception as e:
            self.connection.rollback()
            raise Exception(f"Update execution failed: {str(e)}")
    
    def test_connection(self) -> dict:
        """Test database connection"""
        try:
            self.connect()
            self.cursor.execute("SELECT version();")
            version = self.cursor.fetchone()
            self.disconnect()
            return {
                "status": "success",
                "message": "Connected to PostgreSQL successfully",
                "database": self.database,
                "version": version['version'] if version else None
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "database": self.database
            }


# Singleton instance
_db_connection: Optional[PostgreSQLConnection] = None


def get_db_connection() -> PostgreSQLConnection:
    """Get or create database connection instance"""
    global _db_connection
    if _db_connection is None:
        _db_connection = PostgreSQLConnection()
    return _db_connection
