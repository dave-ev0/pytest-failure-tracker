import json
import traceback
from datetime import datetime
from pathlib import Path

import pytest

RESULTS_FILE = Path("test_results.json")


def pytest_configure(config):
    config.addinivalue_line(
        "markers", "track_failures: mark test to have its failures tracked"
    )


def pytest_addoption(parser):
    parser.addoption(
        "--track-failures", action="store_true", help="Track test failures across runs"
    )


def pytest_sessionstart(session):
    if session.config.getoption("track_failures"):
        if RESULTS_FILE.exists():
            with open(RESULTS_FILE) as f:
                session.results = json.load(f)
        else:
            session.results = {}


@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()

    if item.config.getoption("track_failures"):
        test_id = f"{item.nodeid}"

        if test_id not in item.session.results:
            item.session.results[test_id] = {
                "passes": 0,
                "failures": 0,
                "skips": 0,
                "last_failure": None,
            }

        if report.when == "call":
            if report.passed:
                item.session.results[test_id]["passes"] += 1
            elif report.failed:
                item.session.results[test_id]["failures"] += 1
                item.session.results[test_id]["last_failure"] = {
                    "timestamp": datetime.now().isoformat(),
                    "traceback": traceback.format_tb(call.excinfo.tb),
                }
            elif report.skipped:
                item.session.results[test_id]["skips"] += 1


def pytest_sessionfinish(session):
    if session.config.getoption("track_failures"):
        with open(RESULTS_FILE, "w") as f:
            json.dump(session.results, f, indent=2)


def pytest_terminal_summary(terminalreporter, exitstatus, config):
    if config.getoption("track_failures"):
        terminalreporter.section("Test Failure Tracking Summary")

        with open(RESULTS_FILE) as f:
            results = json.load(f)

        for test_id, data in results.items():
            total_runs = data["passes"] + data["failures"] + data["skips"]
            failure_rate = data["failures"] / total_runs if total_runs > 0 else 0

            terminalreporter.write_line(f"{test_id}:")
            terminalreporter.write_line(f"  Total runs: {total_runs}")
            terminalreporter.write_line(f"  Passes: {data['passes']}")
            terminalreporter.write_line(f"  Failures: {data['failures']}")
            terminalreporter.write_line(f"  Skips: {data['skips']}")
            terminalreporter.write_line(f"  Failure rate: {failure_rate:.2%}")

            if data["last_failure"]:
                terminalreporter.write_line(
                    f"  Last failure: {data['last_failure']['timestamp']}"
                )
                terminalreporter.write_line("  Last failure traceback:")
                for line in data["last_failure"]["traceback"]:
                    terminalreporter.write_line(f"    {line.strip()}")

            terminalreporter.write_line("")
