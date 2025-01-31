import pytest

def test_passing():
    assert True

def test_failing():
    assert False

@pytest.mark.skip
def test_skipped():
    assert True 