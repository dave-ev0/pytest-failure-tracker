import pytest
from datetime import datetime, timedelta
from pathlib import Path
from pytest_analytics.db import TestResultsDB
import duckdb

@pytest.fixture
def test_db(tmp_path):
    """Create a test database with some sample data."""
    db = TestResultsDB(tmp_path)
    
    # Add some test runs
    run_ids = []
    for i in range(3):
        run_id = db.start_test_run("pytest-7.0.0", "3.9.0")
        run_ids.append(run_id)
        
    # Add test results
    test_data = [
        # Stable passing test
        ("test_stable", "passed", 0.1, None, None),
        # Flaky test
        ("test_flaky", "passed", 0.2, None, None),
        ("test_flaky", "failed", 0.2, "AssertionError", "Traceback..."),
        ("test_flaky", "passed", 0.2, None, None),
        # Consistently failing test
        ("test_failing", "failed", 0.3, "ValueError", "Traceback..."),
    ]
    
    for i, (test_id, status, duration, error_msg, traceback) in enumerate(test_data):
        run_id = run_ids[i % len(run_ids)]
        timestamp = datetime.now() - timedelta(minutes=i)
        db.add_test_result(run_id, test_id, status, duration, error_msg, traceback)
    
    return db

def test_init_creates_directory(tmp_path):
    """Test that database initialization creates the necessary directory."""
    db = TestResultsDB(tmp_path)
    assert (tmp_path / ".pytest_analytics").exists()
    assert (tmp_path / ".pytest_analytics" / "results.db").exists()

def test_start_test_run(test_db):
    """Test starting a new test run."""
    run_id = test_db.start_test_run("pytest-7.0.0", "3.9.0")
    assert isinstance(run_id, int)
    
    # Verify the run was recorded
    result = test_db.conn.execute("""
        SELECT pytest_version, python_version 
        FROM test_runs 
        WHERE run_id = ?
    """, [run_id]).fetchone()
    
    assert result[0] == "pytest-7.0.0"
    assert result[1] == "3.9.0"

def test_add_test_result(test_db):
    """Test adding a test result."""
    run_id = test_db.start_test_run("pytest-7.0.0", "3.9.0")
    test_db.add_test_result(
        run_id=run_id,
        test_id="test_example",
        status="failed",
        duration=0.1,
        error_message="AssertionError",
        error_traceback="Traceback..."
    )
    
    result = test_db.conn.execute("""
        SELECT test_id, status, error_message
        FROM test_results
        WHERE run_id = ?
    """, [run_id]).fetchone()
    
    assert result[0] == "test_example"
    assert result[1] == "failed"
    assert result[2] == "AssertionError"

def test_generate_summary_json(test_db):
    """Test generating JSON summary."""
    summary = test_db.generate_summary_json()
    
    assert "test_stable" in summary
    assert summary["test_stable"]["passes"] == 1
    assert summary["test_stable"]["failures"] == 0
    
    assert "test_flaky" in summary
    assert summary["test_flaky"]["passes"] == 2
    assert summary["test_flaky"]["failures"] == 1

def test_get_flaky_tests(test_db):
    """Test identifying flaky tests."""
    flaky_tests = test_db.get_flaky_tests(min_runs=2, min_failure_rate=0.1)
    
    # Should find our flaky test
    assert len(flaky_tests) == 1
    assert flaky_tests[0][0] == "test_flaky"
    assert flaky_tests[0][2] > 0  # passes
    assert flaky_tests[0][3] > 0  # failures

def test_get_test_history(test_db):
    """Test retrieving test history."""
    history = test_db.get_test_history("test_flaky", limit=5)
    
    assert len(history) == 3  # Should have 3 results for flaky test
    assert any(result[1] == "failed" for result in history)  # Should have a failure
    assert any(result[1] == "passed" for result in history)  # Should have a pass 

def test_generate_summary_json_includes_analytics(test_db):
    """Test that the JSON summary includes analytics data."""
    summary = test_db.generate_summary_json()
    
    # Check flaky test analytics
    assert "test_flaky" in summary
    assert "analytics" in summary["test_flaky"]
    assert summary["test_flaky"]["analytics"]["is_flaky"]
    assert "flaky_details" in summary["test_flaky"]["analytics"]
    assert summary["test_flaky"]["analytics"]["flaky_details"]["total_runs"] == 3
    
    # Check history
    assert "history" in summary["test_flaky"]
    assert len(summary["test_flaky"]["history"]) == 3
    assert all(isinstance(h["timestamp"], str) for h in summary["test_flaky"]["history"])
    
    # Check performance metrics
    assert "performance" in summary["test_flaky"]["analytics"]
    assert "avg_duration" in summary["test_flaky"]["analytics"]["performance"]
    assert "min_duration" in summary["test_flaky"]["analytics"]["performance"]
    assert "max_duration" in summary["test_flaky"]["analytics"]["performance"]

def test_generate_summary_json_stable_test(test_db):
    """Test that stable tests are correctly represented."""
    summary = test_db.generate_summary_json()
    
    assert "test_stable" in summary
    assert not summary["test_stable"]["analytics"]["is_flaky"]
    assert summary["test_stable"]["failure_rate"] == 0.0
    assert len(summary["test_stable"]["history"]) == 1

def test_generate_summary_json_failing_test(test_db):
    """Test that consistently failing tests are correctly represented."""
    summary = test_db.generate_summary_json()
    
    assert "test_failing" in summary
    assert summary["test_failing"]["failures"] == 1
    assert summary["test_failing"]["passes"] == 0
    assert summary["test_failing"]["last_failure"] is not None
    assert "ValueError" in summary["test_failing"]["last_failure"]["error_message"]

def test_start_test_run_autoincrement(test_db):
    """Test that run_ids are auto-incrementing."""
    run_id1 = test_db.start_test_run("pytest-7.0.0", "3.9.0")
    run_id2 = test_db.start_test_run("pytest-7.0.0", "3.9.0")
    
    assert isinstance(run_id1, int)
    assert isinstance(run_id2, int)
    assert run_id2 > run_id1  # Should be auto-incrementing
    
    # Verify both runs were recorded
    runs = test_db.conn.execute("SELECT run_id FROM test_runs ORDER BY run_id").fetchall()
    assert len(runs) >= 2
    assert runs[-2][0] == run_id1
    assert runs[-1][0] == run_id2 

def test_constraints(test_db):
    """Test that database constraints are enforced."""
    run_id = test_db.start_test_run("pytest-7.0.0", "3.9.0")
    
    # Test NOT NULL constraints
    with pytest.raises(duckdb.ConstraintException):
        test_db.conn.execute("""
            INSERT INTO test_results 
            (result_id, run_id, test_id, status, duration)
            VALUES (nextval('result_id_seq'), ?, NULL, 'passed', 0.1)
        """, [run_id])
    
    # Test CHECK constraint on status
    with pytest.raises(duckdb.ConstraintException):
        test_db.add_test_result(
            run_id=run_id,
            test_id="test_example",
            status="invalid_status",  # Should fail
            duration=0.1
        )
    
    # Test foreign key constraint
    with pytest.raises(duckdb.ConstraintException):
        test_db.add_test_result(
            run_id=99999,  # Non-existent run_id
            test_id="test_example",
            status="passed",
            duration=0.1
        ) 