# pytest-failure-tracker

A pytest plugin that tracks test failures and provides analytics across test runs.

## Author
- Dave McCrory (dave@ev0.ai)

## Features

- Track test results across multiple runs
- Store detailed test execution history in SQLite database
- Generate comprehensive analytics about test behavior
- Identify flaky tests automatically
- Track performance metrics and trends
- Provide detailed failure analysis

### Analytics Provided

- Test execution statistics (pass/fail/skip rates)
- Performance metrics (avg/min/max duration)
- Flaky test detection
- Recent test history with status
- Trend analysis
- Test execution timing analysis
- Failure pattern analysis

## Installation

```bash
pip install pytest-failure-tracker
```

## Usage

Enable failure tracking by using the `--track-failures` flag:

```bash
pytest --track-failures
```

Additional options:
- `--show-flaky-tests`: Show potentially flaky tests in the summary

## Output

The plugin provides two main types of output:

1. A JSON file (`test_results.json`) containing detailed test results
2. A SQLite database (`.pytest_tracker/results.db`) for historical analysis
3. Terminal summary sections:

### Test Failure Tracking Summary
Shows per-test details including:
- Total runs, passes, failures, and skips
- Failure rate
- Performance metrics
- Recent test history with status indicators (✓, ✗, ⚪)
- Last failure details

### Test Trends Analysis
Provides aggregate analytics including:
- Potentially flaky tests
- Slowest tests
- Recent failures

## Example Output

```
==== Test Failure Tracking Summary ====

test_example.py::test_function:
  Total runs: 5
  Passes: 3
  Failures: 1
  Skips: 1
  Failure rate: 20.00%
  Performance:
    Average duration: 0.075s
    Min duration: 0.050s
    Max duration: 0.100s
  ⚠️ Flaky Test:
    Failure rate: 20.00%
    Failed 1 times in 5 runs
  Recent history:
    ✗ 2024-01-01T00:00:00 - failed (0.100s)
      Error: Test failed
    ✓ 2024-01-01T00:00:01 - passed (0.050s)

==== Test Trends Analysis ====

Potentially Flaky Tests:
  test_example.py::test_function: 20.00% failure rate

Slowest Tests:
  test_example.py::test_function: 0.075s average duration

Recent Failures:
  test_example.py::test_function: Last failed at 2024-01-01T00:00:00
```

## Database Schema

The plugin uses DuckDB to store test results with the following schema:

```sql
CREATE TABLE test_runs (
    run_id INTEGER PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    pytest_version VARCHAR NOT NULL,
    python_version VARCHAR NOT NULL
);

CREATE TABLE test_results (
    result_id INTEGER PRIMARY KEY,
    run_id INTEGER NOT NULL,
    test_id VARCHAR NOT NULL,
    status VARCHAR NOT NULL CHECK (status IN ('passed', 'failed', 'skipped')),
    duration DOUBLE NOT NULL,
    error_message VARCHAR,
    error_traceback VARCHAR,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (run_id) REFERENCES test_runs(run_id)
);
```

## Interpreting Results

### Flaky Test Detection
A test is considered "flaky" when it both passes and fails across multiple runs. The plugin uses these criteria:
- Has at least 2 runs
- Has both passes and failures
- Has a failure rate >= 10%

Example interpretation:
```
⚠️ Flaky Test:
  Failure rate: 20.00%
  Failed 1 times in 5 runs
```
This indicates an unstable test that needs investigation for race conditions, timing issues, or external dependencies.

### Performance Analysis
The plugin tracks execution timing statistics:
```
Performance:
  Average duration: 0.075s
  Min duration: 0.050s
  Max duration: 0.100s
```
Large variations between min and max durations can indicate:
- Resource contention
- Network latency issues
- Cache inconsistencies
- Background process interference

### Test History
Recent history shows the test's execution pattern:
```
Recent history:
  ✓ 2024-01-01T00:00:01 - passed (0.050s)
  ✗ 2024-01-01T00:00:00 - failed (0.100s)
```
Status indicators:
- ✓ : Passed test
- ✗ : Failed test
- ⚪ : Skipped test

## Advanced Usage

### Database Queries
The DuckDB database (`.pytest_tracker/results.db`) can be queried directly for custom analysis:

```sql
-- Find tests with increasing failure rates
SELECT test_id, 
       COUNT(*) as total_runs,
       AVG(CASE WHEN status = 'failed' THEN 1.0 ELSE 0.0 END) as failure_rate
FROM test_results
GROUP BY test_id
HAVING failure_rate > 0.2
ORDER BY failure_rate DESC;

-- Find tests with increasing duration
SELECT test_id,
       AVG(duration) as avg_duration,
       MIN(duration) as min_duration,
       MAX(duration) as max_duration
FROM test_results
GROUP BY test_id
HAVING MAX(duration) > 2 * MIN(duration)
ORDER BY avg_duration DESC;
```

### Configuration
The plugin reads these environment variables:
- `PYTEST_TRACKER_DB_PATH`: Override default database location
- `PYTEST_TRACKER_MIN_RUNS`: Minimum runs for flaky test detection (default: 2)
- `PYTEST_TRACKER_FAILURE_THRESHOLD`: Failure rate threshold for flaky tests (default: 0.1)

## Known Issues and Limitations

1. Database Lock Contention
   - Only one test session can write to the database at a time
   - Parallel test execution may cause delays in result recording

2. Memory Usage
   - Large test suites with many failures may accumulate significant traceback data
   - Consider periodic database maintenance for long-running projects

3. Platform Differences
   - Test duration measurements may vary by platform
   - Unicode support for status symbols depends on terminal capabilities

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add or update tests as needed
5. Update documentation
6. Submit a Pull Request

### Development Setup
```bash
# Clone the repository
git clone https://github.com/yourusername/pytest-failure-tracker.git
cd pytest-failure-tracker

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/
```

## Changelog

### 1.0.0 (2024-01)
- Initial release with DuckDB backend
- Added comprehensive test analytics
- Added flaky test detection
- Added performance tracking
- Added trend analysis

### 0.2.0 (2023-12)
- Migrated from JSON to DuckDB storage
- Added test history tracking
- Improved failure analysis

### 0.1.0 (2023-11)
- Basic test failure tracking
- JSON-based storage
- Simple failure reporting

## License

This project is licensed under the MIT License - see the LICENSE file for details.
