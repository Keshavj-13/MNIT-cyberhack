"""Pytest wrapper turning each Z3 proof obligation into a test case.

unsat = the property holds for ALL inputs (no counterexample exists) = proof.
"""
import pytest
from verification.smt.reasoning_invariants import PROPERTIES, _prove


@pytest.mark.parametrize("name", list(PROPERTIES.keys()))
def test_property_proved(name):
    ok, cex = _prove(name, PROPERTIES[name])
    assert ok, f"Z3 found a counterexample for '{name}': {cex}"
