"""Test some nontrivial fixtures."""

import pytest

from .conftest import attributes_kinds, kinds


def test_attributes_kinds_global_and_unique():
    """Check all factory attributes and uniqueness."""
    all_attrs = next(zip(*attributes_kinds(), strict=True))
    assert len(all_attrs) == len(set(all_attrs))
    assert sorted(all_attrs) == [
        "protected_nonparameter_with_deletedescriptor",
        "protected_nonparameter_with_getdeletedescriptor",
        "protected_nonparameter_with_getdescriptor",
        "protected_nonparameter_with_getsetdeletedescriptor",
        "protected_nonparameter_with_getsetdescriptor",
        "protected_nonparameter_with_nondescriptor",
        "protected_nonparameter_with_setdeletedescriptor",
        "protected_nonparameter_with_setdescriptor",
        "protected_parameter_with_deletedescriptor",
        "protected_parameter_with_getdeletedescriptor",
        "protected_parameter_with_getdescriptor",
        "protected_parameter_with_getsetdeletedescriptor",
        "protected_parameter_with_getsetdescriptor",
        "protected_parameter_with_nondescriptor",
        "protected_parameter_with_setdeletedescriptor",
        "protected_parameter_with_setdescriptor",
        "unprotected_nonparameter_slot",
        "unprotected_nonparameter_with_deletedescriptor",
        "unprotected_nonparameter_with_getdeletedescriptor",
        "unprotected_nonparameter_with_getdescriptor",
        "unprotected_nonparameter_with_getsetdeletedescriptor",
        "unprotected_nonparameter_with_getsetdescriptor",
        "unprotected_nonparameter_with_nondescriptor",
        "unprotected_nonparameter_with_setdeletedescriptor",
        "unprotected_nonparameter_with_setdescriptor",
        "unprotected_parameter_missing",
        "unprotected_parameter_slot",
        "unprotected_parameter_with_deletedescriptor",
        "unprotected_parameter_with_getdeletedescriptor",
        "unprotected_parameter_with_getdescriptor",
        "unprotected_parameter_with_getsetdeletedescriptor",
        "unprotected_parameter_with_getsetdescriptor",
        "unprotected_parameter_with_nondescriptor",
        "unprotected_parameter_with_setdeletedescriptor",
        "unprotected_parameter_with_setdescriptor",
    ]


def test_attributes_kinds_num_results():
    """Check a few results."""
    expected = [35, 18, 17, 16, 19, 2, 33, 1, 34, 8, 5]
    observed = [
        len(tuple(attributes_kinds(*expr)))
        for expr in [
            (),
            ("parameter",),
            ("nonparameter",),
            ("protected",),
            ("unprotected",),
            ("slot",),
            ("nonslot",),
            ("missing",),
            ("nonmissing",),
            ("protected", "parameter"),
            ("nondescriptor",),
        ]
    ]
    assert observed == expected


def test_attributes_kinds_raises_when_empty():
    """Raises `AttributeError` on zero match."""
    filters = ("parameter", "nonparameter")
    regex = r"^No factory attribute matches \('parameter', 'nonparameter'\)$"
    with pytest.raises(ValueError, match=regex):
        next(attributes_kinds(*filters))


def test_attributes_kinds_raises_unknown_filter():
    """Raises `AttributeError` on zero match."""
    regex = r"^Invalid filter 'unknown'. Consider adding it if necessary$"
    with pytest.raises(ValueError, match=regex):
        next(attributes_kinds("unknown"))


def test_attributekind_repr_human_readable():
    """Check that `_AttributeKind` repr is human-readable for debug."""
    kind = next(kinds("missing"))
    expected = (
        "_AttributeKind[unprotected_parameter_missing]"
        "(False, True, False, True, False, False, False)"
    )
    assert repr(kind) == expected


def test_make():
    """Check `make` fixture."""
    pytest.skip("NotImplemented")
