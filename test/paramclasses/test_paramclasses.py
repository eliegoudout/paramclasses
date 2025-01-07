"""Miscellaneous tests not directly related to protection."""

import random
import re

import pytest

from paramclasses import MISSING, ParamClass, isparamclass


def test_slot_compatible(null):
    """It is possible to slot unprotected attribute."""

    class A(ParamClass):
        __slots__ = ("x",)

    a = A()
    a.x = null
    assert a.x is null
    assert "x" not in vars(a)


# @pytest.mark.skip(reason="Don't want to monkeypatch, treat #4 before")
def test_repr_with_missing_and_recursion(ParamTest):
    """Show non-default and missing in `repr`, handle recursive."""

    # Add recursive parameter
    class ReprTest(ParamTest):
        a_recursive_parameter: ...  # type:ignore[annotation-unchecked]

    instance = ReprTest()
    instance.a_recursive_parameter = instance

    expected = (
        "ReprTest("
        "a_unprotected_parameter_with_missing=?, "
        "a_unprotected_parameter_slot=<member 'a_unprotected_parameter_slot' of"
        " 'ParamTest' objects>, "
        "a_recursive_parameter=...)"
    )
    assert repr(instance) == expected


def test_missing_params(ParamTest, paramtest_attrs):
    """Test `missing_params` property."""
    paramtest_missing = sorted(ParamTest().missing_params)
    expected = sorted(paramtest_attrs("missing"))
    assert expected == paramtest_missing


def test_cannot_define_double_dunder_parameter():
    """Dunder parameters are forbidden."""
    regex = r"^Dunder parameters \('__'\) are forbidden$"
    with pytest.raises(AttributeError, match=regex):

        class A(ParamClass):
            __: ...  # type:ignore[annotation-unchecked]


def test_cannot_assign_special_missing_value(ParamTest, paramtest_attrs):
    """Missing value can never be assigned."""
    regex_empty = r"^Assigning special missing value \(attribute '{}'\) is forbidden$"
    # At class creation, parameter or not
    with pytest.raises(ValueError, match=regex_empty.format("x")):

        class A(ParamClass):
            x = MISSING

    with pytest.raises(ValueError, match=regex_empty.format("x")):

        class B(ParamClass):
            x: ... = MISSING  # type:ignore[annotation-unchecked]

    # After class creation: test for every kind of unprotected afftributes
    for attr in paramtest_attrs("unprotected"):
        regex = regex_empty.format(attr)
        # Class level
        with pytest.raises(ValueError, match=regex):
            setattr(ParamTest, attr, MISSING)

        # Instance level
        with pytest.raises(ValueError, match=regex):
            setattr(ParamTest(), attr, MISSING)


def test_init_and_set_params_works(ParamTest, paramtest_attrs, null):
    """For parameters, `set_params` works fine."""
    param_values = {attr: null for attr in paramtest_attrs("unprotected", "parameter")}
    instance_init = ParamTest(**param_values)
    instance_set_params = ParamTest()
    instance_set_params.set_params(**param_values)

    for instance in [instance_init, instance_set_params]:
        assert all(getattr(instance, attr) is null for attr in param_values)


def test_params(ParamTest, paramtest_attrs, null):
    """Test `params` property.

    Half randomly chosen parameters are assigned a `null` value before.
    """
    random.seed(0)
    unprotected = paramtest_attrs("unprotected", "parameter")
    assigned_null = random.sample(unprotected, len(unprotected) // 2)

    instance = ParamTest()
    parameters = paramtest_attrs("parameter")
    expected = {attr: getattr(ParamTest, attr, MISSING) for attr in parameters}
    for attr in assigned_null:
        setattr(instance, attr, null)
        expected[attr] = null

    observed = instance.params

    # Check equal keys and same object values
    assert sorted(observed.keys()) == sorted(expected.keys())
    assert all(observed[attr] is expected[attr] for attr in observed)


def test_init_and_set_params_wrong_attr_ignored(ParamTest, paramtest_attrs, null):
    """Using `set_params` on non-parameters fails."""
    param_values = {attr: null for attr in paramtest_attrs()}

    regex = "^Invalid parameters: {(.*?)}. Operation cancelled$"
    # Check error and match regex
    with pytest.raises(AttributeError, match=regex) as exc_init:
        ParamTest(**param_values)

    with pytest.raises(AttributeError, match=regex) as exc_set_params:
        ParamTest().set_params(**param_values)

    # Check list of non parameters
    expected = sorted(paramtest_attrs("nonparameter"))
    for excinfo in [exc_init, exc_set_params]:
        nonparams_str = re.match(regex, str(excinfo.value)).group(1)
        observed = sorted(attr_repr[1:-1] for attr_repr in nonparams_str.split(", "))

        assert expected == observed


def test_isparamclass_works_even_against_virtual(ParamTest):
    """Test `isparamclass`,  also against virtual subclassing."""
    assert isparamclass(ParamTest)

    class NonParamClass: ...

    # Not trivially fooled by virtual subclassing
    ParamClass.register(NonParamClass)
    assert issubclass(NonParamClass, ParamClass)
    assert not isparamclass(NonParamClass)
