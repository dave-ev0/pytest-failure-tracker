# pytest-failure-tracker

![img](https://img.shields.io/pypi/v/pytest-failure-tracker.svg)
![](https://img.shields.io/pypi/pyversions/pytest-failure-tracker.svg)
![](https://img.shields.io/pypi/dm/pytest-failure-tracker.svg)

A pytest plugin for tracking test failures over multiple test runs, making it easier to identify flaky tests and frequently failing tests.

## Installation

You can install `pytest-failure-tracker` via pip:

```
pip install pytest-failure-tracker
```

## Usage

To use the plugin, simply run pytest with the `--track-failures` option:

```
pytest --track-failures
```

This will enable failure tracking for your test suite.

## Features

### Failure Tracking

The plugin tracks the following information for each test:

- Number of passes
- Number of failures
- Number of skips
- Timestamp of the last failure
- Traceback of the last failure

This data is stored in a JSON file (`test_results.json`) in your project directory.

### Summary Report

After each test run with `--track-failures` enabled, the plugin will display a summary report in the terminal. This report includes:

- Total number of runs for each test
- Number of passes, failures, and skips
- Failure rate
- Timestamp of the last failure
- Traceback of the last failure

### Persistent Storage

Test results are stored persistently, allowing you to track failures across multiple test runs and even across different sessions.

## Example Output

```
============================= Test Failure Tracking Summary =============================
test_module.py::test_example:
  Total runs: 10
  Passes: 8
  Failures: 2
  Skips: 0
  Failure rate: 20.00%
  Last failure: 2024-07-16T14:30:00.123456
  Last failure traceback:
    File "test_module.py", line 15, in test_example
      assert False, "This test intentionally fails sometimes"
    AssertionError: This test intentionally fails sometimes

test_module.py::test_another_example:
  Total runs: 10
  Passes: 10
  Failures: 0
  Skips: 0
  Failure rate: 0.00%
```

## Configuration

Currently, the plugin doesn't require any additional configuration beyond the `--track-failures` command-line option.

## Limitations and Considerations

- The plugin treats parameterized tests as separate tests.
- There is currently no built-in way to reset or clear the tracking data. You can manually delete the `test_results.json` file to reset.
- The plugin doesn't currently provide trend analysis over time.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[MIT](https://izikeros.mit-license.org/) © [Krystian Safjan](https://safjan.com).


TODO: expand documentation with:

1. More detailed examples of how to interpret the results
2. Any known issues or edge cases
3. A section on how to configure the plugin if you add any configuration options in the future
4. A more detailed contribution guide if you want to encourage open-source contributions
5. A changelog to track versions and updates
