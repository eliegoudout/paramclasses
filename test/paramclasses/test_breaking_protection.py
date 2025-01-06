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
    # Also `__delattr__` because it is called by `monkeypatch` to undo.
    m.setattr(type(ParamClass), "__delattr__", type.__delattr__)
    m.setattr(ParamClass, "__setattr__", object.__setattr__)

    # Try overriding a protected attribute
    m.setattr(ParamClass(), PROTECTED, "broken!")


def test_modify_mappingproxy(monkeypatch):
    """Modify mappingproxy using `__eq__` delegation to orig dict.

    From https://bugs.python.org/msg391039
    """
    m = monkeypatch

    class Exploit:
        def __eq__(self, other: dict) -> None:  # type:ignore[override]
            m.delitem(other, "params")

    instance = ParamClass()
    protected = getattr(instance, PROTECTED)

    # Check "params" protection before unprotecting it
    assert "params" in protected
    protected == Exploit()  # noqa: B015
    assert "params" not in protected
