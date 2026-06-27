"""
DataForge DuckDB Manager

Manages an in-memory DuckDB instance for fast analytical queries
used by the dashboard server.
"""

from typing import List, Dict, Any, Optional


class DuckDBManager:
    """Manages DuckDB in-memory database for dashboard queries."""

    def __init__(self):
        try:
            import duckdb
            self.conn = duckdb.connect(':memory:')
        except ImportError:
            raise ImportError("duckdb required. Install: pip install duckdb")
        self.table_name: Optional[str] = None

    def load_data(self, headers: List[str], rows: List[List[Any]], table_name: str):
        """Load cleaned data into DuckDB for querying."""
        import duckdb

        self.table_name = table_name

        # Drop if exists
        self.conn.execute(f'DROP TABLE IF EXISTS "{table_name}"')

        if not headers or not rows:
            return

        # Build CREATE TABLE from data
        col_defs = ', '.join(f'"{h}" VARCHAR' for h in headers)
        self.conn.execute(f'CREATE TABLE "{table_name}" ({col_defs})')

        # Insert rows
        placeholders = ', '.join(['?' for _ in headers])
        insert_sql = f'INSERT INTO "{table_name}" VALUES ({placeholders})'

        clean_rows = []
        for row in rows:
            clean_row = ['' if v is None else str(v) for v in row]
            clean_rows.append(clean_row)

        self.conn.executemany(insert_sql, clean_rows)

    def query(self, sql: str) -> List[Dict[str, Any]]:
        """Execute SQL and return list of dicts."""
        try:
            result = self.conn.execute(sql).fetchdf()
            return result.to_dict(orient='records')
        except Exception as e:
            print(f"DuckDB query error: {e}")
            return []

    def get_categories(self, column_name: str, limit: int = 100) -> List[str]:
        """Get distinct non-null values for a column."""
        if not self.table_name:
            return []
        try:
            sql = f'SELECT DISTINCT "{column_name}" FROM "{self.table_name}" WHERE "{column_name}" IS NOT NULL ORDER BY "{column_name}" LIMIT {limit}'
            result = self.conn.execute(sql).fetchall()
            return [str(row[0]) for row in result]
        except Exception:
            return []

    def get_column_stats(self, column_name: str) -> Dict[str, Any]:
        """Get basic stats for a column."""
        if not self.table_name:
            return {}
        try:
            sql = f"""
                SELECT
                    COUNT(*) as total,
                    COUNT("{column_name}") as non_null,
                    COUNT(DISTINCT "{column_name}") as unique_vals
                FROM "{self.table_name}"
            """
            result = self.conn.execute(sql).fetchone()
            return {
                'total': result[0],
                'non_null': result[1],
                'unique_values': result[2],
                'null_count': result[0] - result[1],
            }
        except Exception:
            return {}

    def close(self):
        """Close the DuckDB connection."""
        try:
            self.conn.close()
        except Exception:
            pass
