"""Test some nontrivial fixtures."""

import pytest


def test_paramtest_attrs_global_and_unique(paramtest_attrs):
    """Check all factory attributes and uniqueness."""
    all_attrs = paramtest_attrs()
    assert len(all_attrs) == len(set(all_attrs))
    assert tuple(sorted(all_attrs)) == (
        "a_protected_nonparameter_with_delete",
        "a_protected_nonparameter_with_get",
        "a_protected_nonparameter_with_get_delete",
        "a_protected_nonparameter_with_get_set",
        "a_protected_nonparameter_with_get_set_delete",
        "a_protected_nonparameter_with_nondescriptor",
        "a_protected_nonparameter_with_set",
        "a_protected_nonparameter_with_set_delete",
        "a_protected_parameter_with_delete",
        "a_protected_parameter_with_get",
        "a_protected_parameter_with_get_delete",
        "a_protected_parameter_with_get_set",
        "a_protected_parameter_with_get_set_delete",
        "a_protected_parameter_with_nondescriptor",
        "a_protected_parameter_with_set",
        "a_protected_parameter_with_set_delete",
        "a_unprotected_nonparameter_slot",
        "a_unprotected_nonparameter_with_delete",
        "a_unprotected_nonparameter_with_get",
        "a_unprotected_nonparameter_with_get_delete",
        "a_unprotected_nonparameter_with_get_set",
        "a_unprotected_nonparameter_with_get_set_delete",
        "a_unprotected_nonparameter_with_nondescriptor",
        "a_unprotected_nonparameter_with_set",
        "a_unprotected_nonparameter_with_set_delete",
        "a_unprotected_parameter_slot",
        "a_unprotected_parameter_with_delete",
        "a_unprotected_parameter_with_get",
        "a_unprotected_parameter_with_get_delete",
        "a_unprotected_parameter_with_get_set",
        "a_unprotected_parameter_with_get_set_delete",
        "a_unprotected_parameter_with_missing",
        "a_unprotected_parameter_with_nondescriptor",
        "a_unprotected_parameter_with_set",
        "a_unprotected_parameter_with_set_delete",
    )


def test_paramtest_attrs_num_results(paramtest_attrs):
    """Check a few results."""
    expected = [35, 18, 17, 16, 19, 16, 16, 2, 1]
    observed = [
        len(paramtest_attrs(*expr))
        for expr in [
            (),
            ("parameter",),
            ("nonparameter",),
            ("protected",),
            ("unprotected",),
            ("get",),
            ("delete",),
            ("slot",),
            ("missing",),
        ]
    ]
    assert observed == expected


@pytest.mark.parametrize(
    "exprs",
    [("parameter", "nonparameter"), ("protected", "unprotected"), ("with", "slot")],
)
def test_paramtest_attrs_natural_partitioning(exprs, paramtest_attrs):
    """Check that expected partitions of attributes actually are."""
    set1, set2 = map(set, map(paramtest_attrs, exprs))
    desc = f"'{exprs[0]}' and '{exprs[1]}'"
    assert set1.isdisjoint(set2), f"Intersecting attrs sets for {desc}"
    assert set1 | set2 == set(paramtest_attrs()), f"Incomplete attrs union for {desc}"


def test_paramtest_attrs_raises_when_empty(paramtest_attrs):
    """Raises `AttributeError` on zero match."""
    zero_match = ("parmaeter", "wiht", "solt", "potrected")
    mode = "or"
    import re

    regex = (
        f"^No factory attribute matches {re.escape(str(zero_match))} in mode '{mode}'$"
    )
    with pytest.raises(AttributeError, match=regex):
        paramtest_attrs(*zero_match, mode=mode)
