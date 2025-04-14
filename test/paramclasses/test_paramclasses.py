"""Miscellaneous tests not directly related to protection."""

import pytest

from paramclasses import MISSING, ParamClass, RawParamClass, isparamclass

from .conftest import attributes, kinds, parametrize_attr_kind


def test_slot_compatible(null):
    """It is possible to slot unprotected attribute."""

    class A(ParamClass):
        __slots__ = ("x",)

    a = A()
    a.x = null
    assert a.x is null
    assert "x" not in vars(a)


def test_repr_str_with_missing_and_recursion(make):
    """Test `repr` and `str`, both with recursion."""
    param = make("param", *kinds("nondescriptor"))
    param.unprotected_parameter_with_nondescriptor = param
    runtime_repr = type(param).protected_parameter_with_nondescriptor

    expected_repr = (
        "ParamTest"
        "(unprotected_parameter_missing=?,"
        " unprotected_parameter_with_nondescriptor=..., "
        f"protected_parameter_with_nondescriptor={runtime_repr})"
    )
    expected_str = (
        "ParamTest"
        "(unprotected_parameter_missing=?, "
        f"unprotected_parameter_with_nondescriptor={expected_repr})"
    )

    assert repr(param) == expected_repr
    assert str(param) == expected_str


def test_missing_params_property(make):
    """Test `missing_params` property."""
    param = make("param", *kinds("missing"))

    observed = param.missing_params
    expected = tuple(attributes("missing"))
    assert observed == expected


def test_cannot_define_double_dunder_parameter():
    """Dunder parameters are forbidden."""
    regex = r"^Dunder parameters \('__'\) are forbidden$"
    with pytest.raises(AttributeError, match=regex):

        class A(ParamClass):
            __: ...  # type:ignore[annotation-unchecked]


def test_cannot_assign_special_missing_value_at_class_creation():
    """Missing value can never be assigned."""
    regex = r"^Assigning special missing value \(attribute 'x'\) is forbidden$"
    with pytest.raises(ValueError, match=regex):

        class A(ParamClass):
            x = MISSING

    with pytest.raises(ValueError, match=regex):

        class B(ParamClass):
            x: ... = MISSING  # type:ignore[annotation-unchecked]


@parametrize_attr_kind("unprotected")
def test_cannot_assign_special_missing_value_after_class_creation(attr, kind, make):
    """Missing value can never be assigned."""
    regex = rf"^Assigning special missing value \(attribute '{attr}'\) is forbidden$"

    for obj in make("param, Param", kind):
        with pytest.raises(ValueError, match=regex):
            setattr(obj, attr, MISSING)


@parametrize_attr_kind("unprotected", "parameter")
def test_init_and_set_params_work(attr, kind, make, null):
    """For parameters, `set_params` works fine."""
    Param, param_set_params = make("Param, param", kind)
    kw = {attr: null}
    param_init = Param(**kw)
    param_set_params.set_params(**kw)

    assert getattr(param_init, attr) is null
    assert getattr(param_set_params, attr) is null


@parametrize_attr_kind()
def test_params_property(attr, kind, make, null):
    """Test `params` property, before and afer assignment."""
    Param, param = make("Param, param", kind)

    # Before assignment
    expected_before = {attr: getattr(Param, attr, MISSING)} if kind.parameter else {}
    assert param.params == expected_before

    # Do not set protected or descriptor-handled attributes
    descriptor_handled_set = not kind.parameter and (kind.has_set or kind.has_delete)
    if kind.protected or descriptor_handled_set:
        return

    # After assignment
    setattr(param, attr, null)
    expected_after = {attr: null} if kind.parameter else {}
    assert param.params == expected_after


@parametrize_attr_kind("nonparameter")
def test_init_and_set_params_raise_on_nonparameter(attr, kind, make, null):
    """Using `set_params` on nonparameters fails."""
    Param, param_set_params = make("Param, param", kind)
    kw = {attr: null}

    # Check error and match regex
    regex = rf"^Invalid parameters: {{'{attr}'}}. Operation cancelled$"
    with pytest.raises(AttributeError, match=regex):
        Param(**kw)

    with pytest.raises(AttributeError, match=regex):
        param_set_params.set_params(**kw)


def test_isparamclass_works_even_against_virtual(make):
    """Test `isparamclass`,  also against virtual subclassing."""
    Param, Vanilla = make("Param, Vanilla")

    assert isparamclass(Param)

    # Robust against virtual subclassing, unlike built-in `issubclass`
    ParamClass.register(Vanilla)
    assert issubclass(Vanilla, ParamClass)
    assert not isparamclass(Vanilla)


def test_isparamclass_raw():
    """Test `isparamclass` in `raw` mode."""

    class RawParam(RawParamClass): ...

    assert not isparamclass(RawParam)
    assert isparamclass(RawParam, raw=True)
