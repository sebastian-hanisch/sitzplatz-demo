import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from stz_constants import Layout, Params


@pytest.fixture
def mini_layout():
    """2 Wagen x 2 Reihen x 1 Platz: Reihen 0..3, Türen an jeder Reihe (0,1 | 2,3), von Hand rechenbar."""
    return Layout(cars=2, rows=2, seats=1)


@pytest.fixture
def mini_params(mini_layout):
    return Params(layout=mini_layout, stops=3, trip=1, reach_naive=1, reach_stand=1)
