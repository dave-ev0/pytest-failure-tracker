# Usage


To use pytest-failure-tracker, you need to enable it when running pytest:

```bash
pytest --track-failures
```

This will create a `test_results.json` file in your current directory, which will track the results of your tests across multiple runs.

You can also mark specific tests to be tracked:

```python
import pytest

@pytest.mark.track_failures
def test_example():
    assert True
```
After running your tests, you'll see a summary of the tracked failures in the pytest output.
