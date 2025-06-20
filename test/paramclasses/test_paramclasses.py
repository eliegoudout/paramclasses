"""Miscellaneous tests not directly related to protection."""

import re

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
    msg = "Dunder parameters ('__') are forbidden"
    with pytest.raises(AttributeError, match=f"^{re.escape(msg)}$"):

        class A(ParamClass):
            __: ...  # type:ignore[annotation-unchecked]


def test_cannot_assign_special_missing_value_at_class_creation():
    """Missing value can never be assigned."""
    msg = "Assigning special missing value (attribute 'x') is forbidden"
    with pytest.raises(ValueError, match=f"^{re.escape(msg)}$"):

        class A(ParamClass):
            x = MISSING

    with pytest.raises(ValueError, match=f"^{re.escape(msg)}$"):

        class B(ParamClass):
            x: ... = MISSING  # type:ignore[annotation-unchecked]


@parametrize_attr_kind("unprotected")
def test_cannot_assign_special_missing_value_after_class_creation(attr, kind, make):
    """Missing value can never be assigned."""
    msg = f"Assigning special missing value (attribute {attr!r}) is forbidden"

    for obj in make("param, Param", kind):
        with pytest.raises(ValueError, match=f"^{re.escape(msg)}$"):
            setattr(obj, attr, MISSING)


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


def test_isparamclass_works_even_against_virtual(make):
    """Test `isparamclass`,  also against virtual subclassing."""
    Param, Vanilla = make("Param, Vanilla")

    assert isparamclass(Param)

    # Robust against virtual subclassing, unlike built-in `issubclass`
    ParamClass.register(Vanilla)
    assert issubclass(Vanilla, ParamClass)
    assert not isparamclass(Vanilla)


def test_isparamclass():
    """Test `isparamclass` mode."""

    class RawParam(RawParamClass): ...

    assert isparamclass(RawParam)
    assert not isparamclass(RawParam, raw=False)


def test_default_update():
    """Check that default is current runtime class value."""

    class A(ParamClass):
        x: int = 0  # type:ignore[annotation-unchecked]

    a = A(x=1)

    assert str(a) == "A(x=1)"
    A.x = 1
    assert str(a) == "A()"


def test_post_init_must_be_callable():
    """Test `__signature__` error when `__post_init__` not callable."""

    class A(ParamClass):
        __post_init__ = 0

    msg = "'__post_init__' attribute must be callable"
    with pytest.raises(TypeError, match=f"^{re.escape(msg)}$"):
        A.__signature__  # noqa: B018 (not useless)


def test_post_init_should_return_none():
    """Test `__signature__` error when `__post_init__` not callable."""
    null = object()

    class A(ParamClass):
        def __post_init__(self) -> None:
            return null

    msg = f"'__post_init__' should return 'None' (got {null!r})"
    with pytest.raises(TypeError, match=f"^{re.escape(msg)}$"):
        A()


def test_invalid_mro():
    """Check that MRO must have paramclasses first."""

    class A(ParamClass): ...

    class B: ...

    msg = (
        "Invalid method resolution order (MRO) for bases B, A: nonparamclass 'B'"
        " would come before paramclass 'A'"
    )
    with pytest.raises(TypeError, match=f"^{re.escape(msg)}$"):

        class C(B, A): ...


def test_cannot_use_metaclass_alone():
    """Forbid simple metaclass without inheritance."""
    msg = (
        "Function '_skip_mro_check' should only be called once: metaclass"
        " '_MetaParamClass' should never be explicitly passed except when constructing"
        " 'RawParamClass'"
    )
    with pytest.raises(RuntimeError, match=f"^{re.escape(msg)}$"):

        class A(metaclass=type(ParamClass)): ...


def test_metaclass_requires_inheriting_from_rawparamclass():
    """Check that paramclasses must inherit from RawParamClass."""
    msg = "Paramclasses must always inherit from 'RawParamClass'"
    with pytest.raises(TypeError, match=f"^{re.escape(msg)}$"):

        class A(int, metaclass=type(ParamClass)): ...

    # The (redundant) following works fine
    class A(ParamClass, metaclass=type(ParamClass)): ...
