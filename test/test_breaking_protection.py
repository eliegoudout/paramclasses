"""Easy ways of breaking the potection."""

from paramclasses import PROTECTED, ParamClass, protected


def test_break_protection_replacing_protected():
    """Stupid local break."""

    def protected(val: object) -> object:  # Identity
        return val

    class A(ParamClass):
        x = protected(0)

    # "x" is not added to protected attributes
    assert getattr(A, PROTECTED) == getattr(ParamClass, PROTECTED)


def test_break_protection_modifying_protected(monkeypatch):
    """Break protection by modifying `protected`."""
    m = monkeypatch

    m.setattr(type(protected(0)), "__new__", lambda _, x: x)

    class A(ParamClass):
        x = protected(0)

    # "x" is not added to protected attributes
    assert getattr(A, PROTECTED) == getattr(ParamClass, PROTECTED)


def test_break_protection_modifying_mcs(monkeypatch):
    """Break protection by modifying `ParamClass` from the bottom up."""
    m = monkeypatch

    m.setattr(type(type(ParamClass)), "__setattr__", type.__setattr__)
    m.setattr(type(ParamClass), "__setattr__", type.__setattr__)
    m.setattr(ParamClass, "__setattr__", object.__setattr__)

    # Try overriding a protected attribute
    m.setattr(ParamClass(), PROTECTED, "broken!")
