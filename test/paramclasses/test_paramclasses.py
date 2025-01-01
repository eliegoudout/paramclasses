"""Extensive testing should be added soon."""

import random
import re

import pytest

from paramclasses import MISSING, ParamClass, isparamclass


def test_slot_compatible():
    """It is possible to slot unprotected attribute."""

    class A(ParamClass):
        __slots__ = ("x",)

    a = A()
    null = object()
    a.x = null
    assert a.x is null
    assert "x" not in vars(a)


def test_repr_with_missing_and_recursion(ParamTest):
    """Show non-default and missing in `repr`, handle recursive."""

    # Add recursive parameter
    class ReprTest(ParamTest):
        a_recursive_parameter: ...  # type:ignore[annotation-unchecked]

    instance = ReprTest()
    instance.a_recursive_parameter = instance

    expected = (
        "ReprTest("
        "a_unprotected_parameter_with_nodefaultvalue=?, "
        "a_unprotected_parameter_slot=<member 'a_unprotected_parameter_slot' of"
        " 'ParamTest' objects>, "
        "a_recursive_parameter=...)"
    )
    assert repr(instance) == expected


def test_missing_params(ParamTest, paramtest_attrs):
    """Test `missing_params` property."""
    paramtest_missing = sorted(ParamTest().missing_params)
    expected = sorted(paramtest_attrs("nodefaultvalue"))
    assert expected == paramtest_missing


def test_cannot_define_double_dunder_parameter():
    """Double dunder parameters are forbidden."""
    regex = r"^Double dunder parameters \('__'\) are forbidden$"
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


def test_can_get_set_del_unprotected_class_level(
    ParamTest,
    test_get_set_del_work,
    paramtest_attrs,
):
    """Check possible get/set/del at class-level."""
    for attr in paramtest_attrs("unprotected"):
        test_get_set_del_work(ParamTest, attr)


def test_can_get_set_del_unprotected_instance_level(
    ParamTest,
    test_get_set_del_work,
    paramtest_attrs,
):
    """Check that every unprotected attribute can be get/set/del."""
    instance = ParamTest()
    tested = []
    # Parameter bypass descriptor mechanisms
    for attr in paramtest_attrs("unprotected", "parameter"):
        test_get_set_del_work(instance, attr)
        tested.append(attr)

    # Non-parameters need special descriptor care
    for attr in paramtest_attrs("unprotected", "nonparameter"):
        clsval = getattr(ParamTest, attr, MISSING)
        has_get = hasattr(clsval, "__get__")
        has_set = hasattr(clsval, "__set__")
        has_del = hasattr(clsval, "__delete__")

        # Find expected value knowing descriptor behaviour
        if not has_get and (has_set or has_del):
            expected = clsval
        elif has_get and not has_set and has_del:
            expected = clsval.val
        else:
            expected = MISSING

        test_get_set_del_work(
            ParamTest(),
            attr,
            skip_set=has_del and not has_set,
            skip_del=has_set and not has_del,
            expected=expected,
        )


def test_set_params_works(ParamTest, paramtest_attrs):
    """For parameters, `set_params` works fine."""
    null = object()
    instance = ParamTest()
    param_values = {attr: null for attr in paramtest_attrs("unprotected", "parameter")}
    instance.set_params(**param_values)
    assert all(getattr(instance, attr) is null for attr in param_values)


def test_params(ParamTest, paramtest_attrs):
    """Test `params` property.

    Half randomly chosen parameters are assigned a `null` value before.
    """
    random.seed(0)
    unprotected = paramtest_attrs("unprotected", "parameter")
    assigned_null = random.sample(unprotected, len(unprotected) // 2)

    null = object()
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


def test_set_params_wrong_attr_ignored(ParamTest, paramtest_attrs):
    """Using `set_params` on non-parameters fails."""
    instance = ParamTest()
    param_values = {attr: 0 for attr in paramtest_attrs()}

    regex = "^Invalid parameters: {(.*?)}. Operation cancelled$"
    # Check error and match regex
    with pytest.raises(AttributeError, match=regex) as excinfo:
        instance.set_params(**param_values)

    # Check list of non parameters
    expected = sorted(paramtest_attrs("nonparameter"))
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
