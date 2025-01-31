import pytest

def test_passing():
    assert True

@pytest.mark.xfail(reason="This test is meant to fail")
def test_failing():
    assert False

@pytest.mark.skip
def test_skipped():
    assert True 