import contextlib
import json
import shutil
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, call

import pytest
from pytest_failure_tracker.plugin import (
    pytest_addoption,
    pytest_configure,
    pytest_runtest_makereport,
    pytest_sessionfinish,
    pytest_sessionstart,
    pytest_terminal_summary,
)


# Fixture to create a temporary directory for test files
@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


# Fixture to create a mock pytest config object
@pytest.fixture
def mock_config():
    """Create a mock pytest config object."""
    config = Mock()
    config.getoption.return_value = True
    return config


# Fixture to create a mock pytest session object
@pytest.fixture
def mock_session(mock_config, temp_dir):
    """Create a mock pytest session object."""
    session = Mock()
    session.config = mock_config
    session.results = {}
    return session


# Test for pytest_configure function
def test_pytest_configure():
    """
    Purpose: Verify that pytest_configure adds the correct marker to the config.

    Testing approach:
    1. Create a mock config object
    2. Call pytest_configure with the mock config
    3. Assert that addinivalue_line was called with the correct arguments

    Notes: Using Mock objects to simulate pytest behavior
    """
    config = Mock()
    pytest_configure(config)
    config.addinivalue_line.assert_called_once_with(
        "markers", "track_failures: mark test to have its failures tracked"
    )


# Test for pytest_addoption function
def test_pytest_addoption():
    """Test that the plugin adds the correct command line options."""
    parser = Mock()
    pytest_addoption(parser)
    
    parser.addoption.assert_has_calls([
        call(
            "--track-failures",
            dest="track_failures",
            action="store_true",
            help="Track test failures across runs"
        ),
        call(
            "--show-flaky-tests",
            action="store_true",
            help="Show potentially flaky tests in the summary"
        )
    ])


# Test for pytest_sessionstart function with a new file
def test_pytest_sessionstart_new_file(mock_session, temp_dir):
    """
    Purpose: Verify that pytest_sessionstart initializes an empty results dictionary when no file exists.

    Testing approach:
    1. Set up a mock session and a temporary directory
    2. Patch the RESULTS_FILE constant to use a file in the temporary directory
    3. Call pytest_sessionstart
    4. Assert that the session.results is an empty dictionary

    Notes:
    - Using fixtures (mock_session, temp_dir) for setup
    - Patching constants to control file locations
    """
    results_file = Path(temp_dir) / "test_results.json"
    with patch("pytest_failure_tracker.plugin.RESULTS_FILE", results_file):
        pytest_sessionstart(mock_session)
    assert mock_session.results == {}


# Test for pytest_sessionstart function with an existing file
def test_pytest_sessionstart_existing_file(mock_session, temp_dir):
    """
    Purpose: Verify that pytest_sessionstart loads existing results when a file is present.

    Testing approach:
    1. Set up a mock session and a temporary directory
    2. Create a test results file with sample data
    3. Patch the RESULTS_FILE constant to use the created file
    4. Call pytest_sessionstart
    5. Assert that the session.results contains the data from the file

    Notes:
    - Using fixtures for setup
    - Creating and manipulating files for testing
    - Patching constants to control file locations
    """
    results_file = Path(temp_dir) / "test_results.json"
    existing_results = {"test::id": {"passes": 1, "failures": 0, "skips": 0}}
    with open(results_file, "w") as f:
        json.dump(existing_results, f)

    with patch("pytest_failure_tracker.plugin.RESULTS_FILE", results_file):
        pytest_sessionstart(mock_session)
    assert mock_session.results == existing_results


# Test for pytest_runtest_makereport function
@pytest.mark.parametrize(
    "outcome,expected",
    [
        ("passed", {"passes": 1, "failures": 0, "skips": 0}),
        ("failed", {"passes": 0, "failures": 1, "skips": 0}),
        ("skipped", {"passes": 0, "failures": 0, "skips": 1}),
    ],
)
def test_pytest_runtest_makereport(mock_session, outcome, expected):
    """Test pytest_runtest_makereport with different outcomes."""
    # Initialize the results dictionary
    mock_session.results = {"test::id": {
        "passes": 0,
        "failures": 0,
        "skips": 0,
        "last_failure": None
    }}
    
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
        assert mock_session.results["test::id"]["last_failure"]["timestamp"] == "2021-01-01T00:00:00"
        assert mock_session.results["test::id"]["last_failure"]["traceback"] == ["Traceback line 1", "Traceback line 2"]
    else:
        assert mock_session.results["test::id"]["last_failure"] is None


# Test for pytest_sessionfinish function
def test_pytest_sessionfinish(mock_session, temp_dir):
    """
    Purpose: Verify that pytest_sessionfinish correctly saves the session results to a file.

    Testing approach:
    1. Set up a mock session with sample results
    2. Patch the RESULTS_FILE constant to use a file in the temporary directory
    3. Call pytest_sessionfinish
    4. Assert that the file was created and contains the correct data

    Notes:
    - Using fixtures for setup
    - Patching constants to control file locations
    - Verifying file contents after function execution
    """
    results_file = Path(temp_dir) / "test_results.json"
    mock_session.results = {"test::id": {"passes": 1, "failures": 0, "skips": 0}}

    with patch("pytest_failure_tracker.plugin.RESULTS_FILE", results_file):
        pytest_sessionfinish(mock_session)

    with open(results_file) as f:
        saved_results = json.load(f)
    assert saved_results == mock_session.results


# Test for pytest_terminal_summary function
def test_pytest_terminal_summary(mock_config, temp_dir):
    """Test terminal summary generation."""
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

    # Verify both sections are created
    terminalreporter.section.assert_has_calls([
        call("Test Failure Tracking Summary"),
        call("Recent Test Changes")
    ])
