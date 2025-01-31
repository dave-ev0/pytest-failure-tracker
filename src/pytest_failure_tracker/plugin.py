import json
import traceback
from datetime import datetime
from pathlib import Path
import sys
import platform

import pytest
from .db import TestResultsDB

RESULTS_FILE = Path("test_results.json")


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "track_failures: mark test to have its failures tracked"
    )


def pytest_addoption(parser):
    parser.addoption(
        "--track-failures",
        dest="track_failures",
        action="store_true",
        help="Track test failures across runs"
    )
    parser.addoption(
        "--show-flaky-tests",
        action="store_true",
        help="Show potentially flaky tests in the summary"
    )


def pytest_sessionstart(session):
    """Initialize test tracking for the session."""
    if not session.config.getoption("track_failures"):
        return
        
    project_root = Path.cwd()
    session.test_db = TestResultsDB(project_root)
    session.test_run_id = session.test_db.start_test_run(
        pytest_version=pytest.__version__,
        python_version=platform.python_version()
    )
    
    # Initialize results from existing file if it exists
    if RESULTS_FILE.exists():
        with open(RESULTS_FILE) as f:
            session.results = json.load(f)
    else:
        session.results = {}


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """Hook implementation to track test results."""
    report = (yield).get_result()
    
    if not item.config.getoption("track_failures"):
        return
        
    if report.when == "call" or (report.when == "setup" and report.skipped):
        test_id = item.nodeid
        if test_id not in item.session.results:
            item.session.results[test_id] = {
                "passes": 0,
                "failures": 0,
                "skips": 0,
                "last_failure": None
            }
            
        if report.passed:
            item.session.results[test_id]["passes"] += 1
        elif report.failed:
            item.session.results[test_id]["failures"] += 1
            # Add failure information
            item.session.results[test_id]["last_failure"] = {
                "timestamp": datetime.now().isoformat(),
                "traceback": traceback.format_tb(call.excinfo.tb) if hasattr(call, 'excinfo') else None,
                "error_message": str(call.excinfo.value) if hasattr(call, 'excinfo') else None
            }
        elif report.skipped:
            item.session.results[test_id]["skips"] += 1

        # Also store in database
        status = "passed" if report.passed else "failed" if report.failed else "skipped"
        error_message = None
        error_traceback = None
        if report.failed and hasattr(call, 'excinfo'):
            error_message = str(call.excinfo.value)
            error_traceback = "".join(traceback.format_tb(call.excinfo.tb))

        item.session.test_db.add_test_result(
            run_id=item.session.test_run_id,
            test_id=test_id,
            status=status,
            duration=report.duration,
            error_message=error_message,
            error_traceback=error_traceback
        )


def pytest_sessionfinish(session):
    if session.config.getoption("track_failures") and hasattr(session, "results"):
        RESULTS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(RESULTS_FILE, "w") as f:
            json.dump(session.results, f, indent=2)


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if not config.getoption("track_failures"):
        return

    db = TestResultsDB(Path.cwd())
    results = db.generate_summary_json()
    
    # Debug print
    print("\nDEBUG - Results from DB:")
    print(json.dumps(results, indent=2))

    # Basic Summary
    terminalreporter.section("Test Failure Tracking Summary")
    for test_id, data in results.items():
        total_runs = data["analytics"]["total_runs"]
        failure_rate = data["failure_rate"]

        # Debug print
        print(f"\nDEBUG - Processing test: {test_id}")
        print(f"DEBUG - Data: {json.dumps(data, indent=2)}")

        terminalreporter.write_line(f"\n{test_id}:")
        terminalreporter.write_line(f"  Total runs: {total_runs}")
        terminalreporter.write_line(f"  Passes: {data['passes']}")
        terminalreporter.write_line(f"  Failures: {data['failures']}")
        terminalreporter.write_line(f"  Skips: {data['skips']}")
        terminalreporter.write_line(f"  Failure rate: {failure_rate:.2%}")

        # Performance Analytics
        if "performance" in data["analytics"]:
            perf = data["analytics"]["performance"]
            terminalreporter.write_line(f"  Performance:")
            terminalreporter.write_line(f"    Average duration: {perf['avg_duration']:.3f}s")
            terminalreporter.write_line(f"    Min duration: {perf['min_duration']:.3f}s")
            terminalreporter.write_line(f"    Max duration: {perf['max_duration']:.3f}s")

        # Flaky Test Analysis
        if data["analytics"]["is_flaky"]:
            flaky = data["analytics"]["flaky_details"]
            terminalreporter.write_line(f"  ⚠️ Flaky Test:")
            terminalreporter.write_line(f"    Failure rate: {flaky['failure_rate']:.2%}")
            terminalreporter.write_line(f"    Failed {flaky['total_failures']} times in {flaky['total_runs']} runs")

        # Recent History
        if data["history"]:
            terminalreporter.write_line("  Recent history:")
            for entry in data["history"]:
                status_symbol = "✓" if entry["status"] == "passed" else "✗" if entry["status"] == "failed" else "⚪"
                terminalreporter.write_line(
                    f"    {status_symbol} {entry['timestamp']} - {entry['status']} "
                    f"({entry['duration']:.3f}s)"
                )
                if entry["error_message"]:
                    terminalreporter.write_line(f"      Error: {entry['error_message']}")

    # Trend Analysis Section
    terminalreporter.section("Test Trends Analysis")
    
    # Show Flaky Tests
    flaky_tests = [test_id for test_id, data in results.items() if data["analytics"]["is_flaky"]]
    if flaky_tests:
        terminalreporter.write_line("\nPotentially Flaky Tests:")
        for test_id in flaky_tests:
            data = results[test_id]
            terminalreporter.write_line(
                f"  {test_id}: {data['analytics']['flaky_details']['failure_rate']:.2%} failure rate"
            )

    # Show Slowest Tests
    slow_tests = sorted(
        [(test_id, data) for test_id, data in results.items() if "performance" in data["analytics"]],
        key=lambda x: x[1]["analytics"]["performance"]["avg_duration"],
        reverse=True
    )[:5]
    
    if slow_tests:
        terminalreporter.write_line("\nSlowest Tests:")
        for test_id, data in slow_tests:
            avg_duration = data["analytics"]["performance"]["avg_duration"]
            terminalreporter.write_line(f"  {test_id}: {avg_duration:.3f}s average duration")

    # Show Recently Failed Tests
    recent_failures = [
        (test_id, data) for test_id, data in results.items()
        if data["last_failure"] and data["last_failure"]["timestamp"]
    ]
    recent_failures.sort(key=lambda x: x[1]["last_failure"]["timestamp"], reverse=True)
    
    if recent_failures:
        terminalreporter.write_line("\nRecent Failures:")
        for test_id, data in recent_failures[:5]:
            timestamp = data["last_failure"]["timestamp"]
            terminalreporter.write_line(f"  {test_id}: Last failed at {timestamp}")
