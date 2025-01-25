"""Easy ways of breaking the potection."""

from paramclasses import IMPL, ParamClass, ProtectedError, protected
import pytest


def test_break_protection_replacing_protected():
    """Stupid local break."""

    def protected(val: object) -> object:  # Identity
        return val

    class A(ParamClass):
        x = protected(0)

    # "x" is not added to protected attributes
    assert getattr(A, IMPL).protected == getattr(ParamClass, IMPL).protected


def test_break_protection_modifying_protected(monkeypatch):
    """Break protection by modifying `protected`."""
    m = monkeypatch

    m.setattr(type(protected(0)), "__new__", lambda _, x: x)

    class A(ParamClass):
        x = protected(0)

    # "x" is not added to protected attributes
    assert getattr(A, IMPL).protected == getattr(ParamClass, IMPL).protected


def test_break_protection_modifying_mcs(monkeypatch):
    """Break protection by modifying `ParamClass` from the bottom up."""
    m = monkeypatch

    m.setattr(type(type(ParamClass)), "__setattr__", type.__setattr__)
    m.setattr(type(ParamClass), "__setattr__", type.__setattr__)
    # Also `__delattr__` because it is called by `monkeypatch` to undo.
    m.setattr(type(ParamClass), "__delattr__", type.__delattr__)
    m.setattr(ParamClass, "__setattr__", object.__setattr__)

    # Try overriding a protected attribute
    m.setattr(ParamClass(), IMPL, "broken!")


def test_modify_mappingproxy(monkeypatch):
    """Modify mappingproxy using `__eq__` delegation to orig dict.

    From https://bugs.python.org/msg391039
    """
    m = monkeypatch

    class Exploit:
        def __eq__(self, other: dict) -> None:  # type:ignore[override]
            m.delitem(other, "params")

    instance = ParamClass()
    protected = getattr(instance, IMPL).protected

    # Check "params" protection before unprotecting it
    assert "params" in protected
    protected == Exploit()  # noqa: B015
    assert "params" not in protected


def test_multiple_inheritance_may_change_protected_with_super():
    """Using `super()` in protected attributes is inpredictable."""

    class A(ParamClass):
        x: ...  # type: ignore[annotation-unchecked]

        @protected
        def __repr__(self) -> str:
            return f"Protected repr: {super().__repr__()}"

    # `A.__repr__` rests on `ParamClass.__repr__`...
    assert repr(A()) == "Protected repr: A(x=?)"

    class B(ParamClass):
        def __repr__(self) -> str:
            return "broken!"

    class C(A, B): ...

    # ... but here `B.__repr__` is called first!
    assert repr(C()) == "Protected repr: broken!"


def test_use_type_methods_directly(null):
    """Bypass MRO using `type` methods directly."""

    class A(ParamClass):
        x = protected(null)

    # Protection works
    assert A.x is null
    regex = "^'x' is protected by 'A'$"
    with pytest.raises(ProtectedError, match=regex):
        del A.x

    # Delete `A.x` despite protection
    type.__delattr__(A, "x")
    regex = "^type object 'A' has no attribute 'x'$"
    with pytest.raises(AttributeError, match=regex):
        assert A.x is null
