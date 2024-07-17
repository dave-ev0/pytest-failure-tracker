import contextlib
import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from pytest_failure_tracker.plugin import (
    pytest_addoption,
    pytest_configure,
    pytest_runtest_makereport,
    pytest_sessionfinish,
    pytest_sessionstart,
    pytest_terminal_summary,
)


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def mock_config():
    """Create a mock pytest config object."""
    config = Mock()
    config.getoption.return_value = True
    return config


@pytest.fixture
def mock_session(mock_config, temp_dir):
    """Create a mock pytest session object."""
    session = Mock()
    session.config = mock_config
    session.results = {}
    return session


def test_pytest_configure():
    config = Mock()
    pytest_configure(config)
    config.addinivalue_line.assert_called_once_with(
        "markers", "track_failures: mark test to have its failures tracked"
    )


def test_pytest_addoption():
    parser = Mock()
    pytest_addoption(parser)
    parser.addoption.assert_called_once_with(
        "--track-failures", action="store_true", help="Track test failures across runs"
    )


def test_pytest_sessionstart_new_file(mock_session, temp_dir):
    results_file = Path(temp_dir) / "test_results.json"
    with patch("pytest_failure_tracker.plugin.RESULTS_FILE", results_file):
        pytest_sessionstart(mock_session)
    assert mock_session.results == {}


def test_pytest_sessionstart_existing_file(mock_session, temp_dir):
    results_file = Path(temp_dir) / "test_results.json"
    existing_results = {"test::id": {"passes": 1, "failures": 0, "skips": 0}}
    with open(results_file, "w") as f:
        json.dump(existing_results, f)

    with patch("pytest_failure_tracker.plugin.RESULTS_FILE", results_file):
        pytest_sessionstart(mock_session)
    assert mock_session.results == existing_results


@pytest.mark.parametrize(
    "outcome,expected",
    [
        ("passed", {"passes": 1, "failures": 0, "skips": 0}),
        ("failed", {"passes": 0, "failures": 1, "skips": 0}),
        ("skipped", {"passes": 0, "failures": 0, "skips": 1}),
    ],
)
def test_pytest_runtest_makereport(mock_session, outcome, expected):
    item = Mock()
    item.nodeid = "test::id"
    item.session = mock_session
    item.config = mock_session.config

    call = Mock()
    if outcome == "failed":
        call.excinfo = Mock()
        # Create a more realistic mock for the traceback
        mock_traceback = Mock()
        mock_traceback.tb_frame = Mock()
        mock_traceback.tb_frame.f_code = Mock()
        mock_traceback.tb_frame.f_code.co_filename = "test_file.py"
        mock_traceback.tb_frame.f_code.co_name = "test_function"
        mock_traceback.tb_lineno = 10
        mock_traceback.tb_next = None
        call.excinfo.tb = mock_traceback

    report = Mock()
    report.when = "call"
    setattr(report, outcome, True)
    setattr(report, "skipped" if outcome != "skipped" else "failed", False)
    setattr(report, "passed" if outcome != "passed" else "failed", False)

    with patch("pytest_failure_tracker.plugin.datetime") as mock_datetime, patch(
        "pytest_failure_tracker.plugin.traceback.format_tb"
    ) as mock_format_tb:
        mock_datetime.now.return_value.isoformat.return_value = "2021-01-01T00:00:00"
        mock_format_tb.return_value = ["Traceback line 1", "Traceback line 2"]

        # Create a mock for the yield
        mock_yield = Mock()
        mock_yield.get_result.return_value = report

        # Call the function and get the generator
        hookimpl = pytest_runtest_makereport(item, call)

        # Advance the generator and send the mock
        next(hookimpl)
        with contextlib.suppress(StopIteration):
            hookimpl.send(mock_yield)

    # Assert the results
    assert mock_session.results["test::id"]["passes"] == expected["passes"]
    assert mock_session.results["test::id"]["failures"] == expected["failures"]
    assert mock_session.results["test::id"]["skips"] == expected["skips"]

    if outcome == "failed":
        assert (
            mock_session.results["test::id"]["last_failure"]["timestamp"]
            == "2021-01-01T00:00:00"
        )
        assert mock_session.results["test::id"]["last_failure"]["traceback"] == [
            "Traceback line 1",
            "Traceback line 2",
        ]


def test_pytest_sessionfinish(mock_session, temp_dir):
    results_file = Path(temp_dir) / "test_results.json"
    mock_session.results = {"test::id": {"passes": 1, "failures": 0, "skips": 0}}

    with patch("pytest_failure_tracker.plugin.RESULTS_FILE", results_file):
        pytest_sessionfinish(mock_session)

    with open(results_file) as f:
        saved_results = json.load(f)
    assert saved_results == mock_session.results


def test_pytest_terminal_summary(mock_config, temp_dir):
    results_file = Path(temp_dir) / "test_results.json"
    results = {
        "test::id": {
            "passes": 3,
            "failures": 1,
            "skips": 1,
            "last_failure": {
                "timestamp": "2021-01-01T00:00:00",
                "traceback": ["line1", "line2"],
            },
        }
    }
    with open(results_file, "w") as f:
        json.dump(results, f)

    terminalreporter = Mock()

    with patch("pytest_failure_tracker.plugin.RESULTS_FILE", results_file):
        pytest_terminal_summary(terminalreporter, None, mock_config)

    terminalreporter.section.assert_called_once_with("Test Failure Tracking Summary")
    assert (
        terminalreporter.write_line.call_count == 11
    )  # Number of lines in the summary
