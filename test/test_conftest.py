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
        "a_protected_nonparameter_with_none",
        "a_protected_nonparameter_with_set",
        "a_protected_nonparameter_with_set_delete",
        "a_protected_parameter_with_delete",
        "a_protected_parameter_with_get",
        "a_protected_parameter_with_get_delete",
        "a_protected_parameter_with_get_set",
        "a_protected_parameter_with_get_set_delete",
        "a_protected_parameter_with_none",
        "a_protected_parameter_with_set",
        "a_protected_parameter_with_set_delete",
        "a_unprotected_nonparameter_slot",
        "a_unprotected_nonparameter_with_delete",
        "a_unprotected_nonparameter_with_get",
        "a_unprotected_nonparameter_with_get_delete",
        "a_unprotected_nonparameter_with_get_set",
        "a_unprotected_nonparameter_with_get_set_delete",
        "a_unprotected_nonparameter_with_none",
        "a_unprotected_nonparameter_with_set",
        "a_unprotected_nonparameter_with_set_delete",
        "a_unprotected_parameter_slot",
        "a_unprotected_parameter_with_delete",
        "a_unprotected_parameter_with_get",
        "a_unprotected_parameter_with_get_delete",
        "a_unprotected_parameter_with_get_set",
        "a_unprotected_parameter_with_get_set_delete",
        "a_unprotected_parameter_with_nodefaultvalue",
        "a_unprotected_parameter_with_none",
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
            ("nodefaultvalue",),
        ]
    ]
    assert observed == expected


def test_paramtest_attrs_no_attr(paramtest_attrs):
    """Raises `AttributeError` on zero match."""
    zero_match = ("parmaeter", "wiht", "solt", "potrected")
    mode = "or"
    import re

    regex = (
        f"^No factory attribute matches {re.escape(str(zero_match))} in mode '{mode}'$"
    )
    with pytest.raises(AttributeError, match=regex):
        paramtest_attrs(*zero_match, mode=mode)
