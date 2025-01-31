import json
import traceback
from datetime import datetime
from pathlib import Path
import sys

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
    if session.config.getoption("track_failures"):
        project_root = Path.cwd()
        session.test_db = TestResultsDB(project_root)
        session.test_run_id = session.test_db.start_test_run(
            pytest_version=pytest.__version__,
            python_version=f"{sys.version_info.major}.{sys.version_info.minor}"
        )


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if item.config.getoption("track_failures") and report.when == "call":
        status = "passed" if report.passed else "failed" if report.failed else "skipped"
        
        error_message = None
        error_traceback = None
        if report.failed:
            error_message = str(call.excinfo.value)
            error_traceback = "".join(traceback.format_tb(call.excinfo.tb))

        item.session.test_db.add_test_result(
            run_id=item.session.test_run_id,
            test_id=item.nodeid,
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
    
    # Basic Summary
    terminalreporter.section("Test Failure Tracking Summary")
    results = db.generate_summary_json()

    for test_id, data in results.items():
        total_runs = data["passes"] + data["failures"] + data["skips"]
        failure_rate = data["failures"] / total_runs if total_runs > 0 else 0

        terminalreporter.write_line(f"\n{test_id}:")
        terminalreporter.write_line(f"  Total runs: {total_runs}")
        terminalreporter.write_line(f"  Passes: {data['passes']}")
        terminalreporter.write_line(f"  Failures: {data['failures']}")
        terminalreporter.write_line(f"  Skips: {data['skips']}")
        terminalreporter.write_line(f"  Failure rate: {failure_rate:.2%}")

        if data["last_failure"]:
            terminalreporter.write_line(f"  Last failure: {data['last_failure']['timestamp']}")
            terminalreporter.write_line("  Last failure traceback:")
            for line in data["last_failure"]["traceback"]:
                terminalreporter.write_line(f"    {line.strip()}")

    # Flaky Tests Analysis
    flaky_tests = db.get_flaky_tests()
    if flaky_tests:
        terminalreporter.section("Flaky Tests Analysis")
        terminalreporter.write_line("Tests that sometimes pass and sometimes fail:")
        for test in flaky_tests:
            terminalreporter.write_line(
                f"  {test[0]}: {test[4]:.1%} failure rate ({test[3]} of {test[1]} runs failed)"
            )

    # Recent Test History
    terminalreporter.section("Recent Test Changes")
    for test_id in results:
        history = db.get_test_history(test_id, limit=5)
        if history and any(result[1] == 'failed' for result in history):
            terminalreporter.write_line(f"\n{test_id} recent history:")
            for timestamp, status, duration, error_msg in history:
                terminalreporter.write_line(
                    f"  {timestamp.strftime('%Y-%m-%d %H:%M:%S')} - {status} "
                    f"(duration: {duration:.2f}s)"
                )
                if error_msg:
                    terminalreporter.write_line(f"    Error: {error_msg}")
