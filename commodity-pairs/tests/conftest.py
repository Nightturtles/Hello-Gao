"""Shared fixtures for the simulator tests."""
import pytest

from .sim_support import START, END, copy_base, init, run


@pytest.fixture(scope="session")
def warm_template(tmp_path_factory):
    """A run initialised for START..END (all 5 real picks) and warm-started on the cached data, with no live session
    processed yet.  Tests copy it instead of repeating the replay."""
    base = tmp_path_factory.mktemp("sim_template")
    assert init(base, START, END) == 0
    assert run(base, "2026-07-14") == 0
    return base


@pytest.fixture
def base(warm_template, tmp_path):
    return copy_base(warm_template, tmp_path / "base")
