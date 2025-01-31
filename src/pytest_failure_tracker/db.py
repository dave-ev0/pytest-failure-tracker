import duckdb
from datetime import datetime
from pathlib import Path
import json

class TestResultsDB:
    def __init__(self, project_root: Path):
        self.project_root = project_root
        self.db_path = project_root / ".pytest_tracker" / "results.db"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = duckdb.connect(str(self.db_path))
        self._init_tables()

    def _init_tables(self):
        """Initialize the database tables if they don't exist."""
        self.conn.execute("""
            CREATE SEQUENCE IF NOT EXISTS run_id_seq;
            CREATE SEQUENCE IF NOT EXISTS result_id_seq;
            
            CREATE TABLE IF NOT EXISTS test_runs (
                run_id INTEGER PRIMARY KEY DEFAULT nextval('run_id_seq'),
                timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                pytest_version VARCHAR NOT NULL,
                python_version VARCHAR NOT NULL
            );

            CREATE TABLE IF NOT EXISTS test_results (
                result_id INTEGER PRIMARY KEY DEFAULT nextval('result_id_seq'),
                run_id INTEGER NOT NULL,
                test_id VARCHAR NOT NULL,
                status VARCHAR NOT NULL CHECK (status IN ('passed', 'failed', 'skipped')),
                duration DOUBLE NOT NULL,
                error_message VARCHAR,
                error_traceback VARCHAR,
                timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (run_id) REFERENCES test_runs(run_id)
            );
        """)

        # Create views for common queries using more efficient aggregations
        self.conn.execute("""
            CREATE OR REPLACE VIEW test_summary AS
            SELECT 
                tr.test_id,
                COUNT(*) as total_runs,
                COUNT(*) FILTER (WHERE status = 'passed') as passes,
                COUNT(*) FILTER (WHERE status = 'failed') as failures,
                COUNT(*) FILTER (WHERE status = 'skipped') as skips,
                CAST(COUNT(*) FILTER (WHERE status = 'failed') AS DOUBLE) / 
                    NULLIF(COUNT(*), 0) as failure_rate,
                MAX(tr.timestamp) FILTER (WHERE status = 'failed') as last_failure
            FROM test_results tr
            GROUP BY tr.test_id
        """)

    def start_test_run(self, pytest_version: str, python_version: str) -> int:
        """Start a new test run and return its ID."""
        result = self.conn.execute("""
            INSERT INTO test_runs (run_id, timestamp, pytest_version, python_version)
            VALUES (nextval('run_id_seq'), CURRENT_TIMESTAMP, ?, ?)
            RETURNING run_id;
        """, [pytest_version, python_version]).fetchone()
        
        if not result:
            raise RuntimeError("Failed to create test run")
        return result[0]

    def add_test_result(self, run_id: int, test_id: str, status: str, 
                       duration: float, error_message: str = None, 
                       error_traceback: str = None):
        """Add a test result to the database."""
        self.conn.execute("""
            INSERT INTO test_results 
            (result_id, run_id, test_id, status, duration, error_message, error_traceback, timestamp)
            VALUES (nextval('result_id_seq'), ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        """, [run_id, test_id, status, duration, error_message, error_traceback])

    def generate_summary_json(self) -> dict:
        """Generate a comprehensive summary in JSON format."""
        results = {}
        
        # Get basic summary data
        summary = self.conn.execute("""
            SELECT 
                ts.test_id,
                ts.total_runs,
                ts.passes,
                ts.failures,
                ts.skips,
                ts.failure_rate,
                ts.last_failure,
                tr.error_traceback,
                tr.error_message
            FROM test_summary ts
            LEFT JOIN test_results tr ON 
                ts.test_id = tr.test_id AND 
                ts.last_failure = tr.timestamp
        """).fetchall()

        for row in summary:
            test_id = row[0]
            results[test_id] = {
                "passes": row[2],
                "failures": row[3],
                "skips": row[4],
                "failure_rate": float(row[5]),  # Convert from Decimal
                "last_failure": {
                    "timestamp": row[6].isoformat() if row[6] else None,
                    "traceback": row[7].split('\n') if row[7] else None,
                    "error_message": row[8]
                } if row[6] else None,
                "history": [],
                "analytics": {
                    "total_runs": row[1],
                    "is_flaky": False,  # Will be updated below
                    "avg_duration": 0.0  # Will be updated below
                }
            }

        # Add test history
        for test_id in results:
            history = self.get_test_history(test_id, limit=5)
            results[test_id]["history"] = [
                {
                    "timestamp": ts.isoformat(),
                    "status": status,
                    "duration": duration,
                    "error_message": error_msg
                }
                for ts, status, duration, error_msg in history
            ]

        # Add flaky test information
        flaky_tests = self.get_flaky_tests()
        for test in flaky_tests:
            test_id = test[0]
            if test_id in results:
                results[test_id]["analytics"]["is_flaky"] = True
                results[test_id]["analytics"]["flaky_details"] = {
                    "failure_rate": float(test[4]),
                    "total_failures": test[3],
                    "total_runs": test[1]
                }

        # Add performance metrics
        performance = self.conn.execute("""
            SELECT 
                test_id,
                AVG(duration) as avg_duration,
                MIN(duration) as min_duration,
                MAX(duration) as max_duration
            FROM test_results
            GROUP BY test_id
        """).fetchall()

        for test_id, avg_duration, min_duration, max_duration in performance:
            if test_id in results:
                results[test_id]["analytics"]["performance"] = {
                    "avg_duration": float(avg_duration),
                    "min_duration": float(min_duration),
                    "max_duration": float(max_duration)
                }

        return results

    def get_flaky_tests(self, min_runs: int = 2, min_failure_rate: float = 0.1):
        """Identify flaky tests (tests that sometimes pass and sometimes fail)."""
        return self.conn.execute("""
            SELECT 
                test_id,
                total_runs,
                passes,
                failures,
                CAST(failures AS DOUBLE) / NULLIF(total_runs, 0) as failure_rate
            FROM test_summary
            WHERE total_runs >= ?
                AND passes > 0 
                AND failures > 0
                AND CAST(failures AS DOUBLE) / NULLIF(total_runs, 0) >= ?
            ORDER BY failure_rate DESC
        """, [min_runs, min_failure_rate]).fetchall()

    def get_test_history(self, test_id: str, limit: int = 10):
        """Get the recent history of a specific test."""
        return self.conn.execute("""
            SELECT 
                tr.timestamp,
                tr.status,
                tr.duration,
                tr.error_message
            FROM test_results tr
            WHERE test_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, [test_id, limit]).fetchall() 