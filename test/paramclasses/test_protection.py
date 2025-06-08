"""Tests directly related to @protected."""

import re

import pytest

from paramclasses import IMPL, ParamClass, ProtectedError, protected


def test_mcs_is_frozen(assert_set_del_is_protected):
    """Cannot modify `_MetaParamClass' (without altering its meta).

    Its mutables can still be muted, but that is just evil behaviour.
    """
    mcs = type(ParamClass)
    attr = "random_attribute"
    msg = f"{mcs.__name__!r} attributes are frozen"
    assert_set_del_is_protected(mcs, attr, f"^{re.escape(msg)}$")


def test_cannot_subclass_mcs():
    """Cannot subclass `_MetaParamClass' (without altering its meta)."""
    mcs = type(ParamClass)
    msg = (
        f"Function '__new__' should only be called once: {type(mcs).__name__!r} should"
        f" only construct {mcs.__name__!r}"
    )
    with pytest.raises(RuntimeError, match=f"^{re.escape(msg)}$"):

        class Sub(mcs): ...


def test_multiple_protection():
    """Multiple redundant protections are fine."""

    class A(ParamClass):
        @protected
        @protected
        @protected
        def method(self) -> None: ...

    assert "method" in getattr(A, IMPL).protected


def test_simple_protection_inheritance():
    """Subclass cannot override protected."""
    msg = "'params' is protected by 'ParamClass'"
    with pytest.raises(ProtectedError, match=f"^{re.escape(msg)}$"):

        class A(ParamClass):
            params = 0


def test_multiple_inheritance_consistent_protection():
    """Check protection compatibility for multiple inheritance."""

    class A(ParamClass):
        x = protected(0)

    class B(ParamClass):
        x = 0

    class C:
        x = 0

    for BC in (B, C):
        # Coherent protection order: OK
        class D(A, BC): ...

        # Incoherent protection order
        msg = f"'x' protection conflict: 'A', {BC.__name__!r}"
        with pytest.raises(ProtectedError, match=f"^{re.escape(msg)}$"):

            class D(BC, A): ...


def test_multiple_inheritance_protection_conflict():
    """Cannot have two different attribute owners."""

    class A(ParamClass):
        x = protected(0)

    class B(ParamClass):
        x = protected(0)

    msg = "'x' protection conflict: 'A', 'B'"
    with pytest.raises(ProtectedError, match=f"^{re.escape(msg)}$"):

        class C(A, B): ...


def test_multiple_inheritance_diamond_is_fine():
    """Test common parent class in multiple inheritance."""

    class A(ParamClass):
        x = protected(0)

    class B(A): ...

    class C(A): ...

    # Diamond inheritance: OK
    class D(C, B): ...

    assert getattr(D, IMPL).protected["x"] is A


def test_cannot_slot_previously_protected():
    """Cannot slot previously protected attribute."""
    msg = (
        f"Cannot slot the following protected attributes: {IMPL!r} (from "
        "<paramclasses root protection>)"
    )
    with pytest.raises(ProtectedError, match=f"^{re.escape(msg)}$"):

        class A(ParamClass):
            __slots__ = (IMPL,)

    # Not necessarily given as iterable of strings
    with pytest.raises(ProtectedError, match=f"^{re.escape(msg)}$"):

        class A(ParamClass):
            __slots__ = IMPL


def test_post_creation_protection():
    """Post-creation protection is ignored, with warning."""

    class A(ParamClass): ...

    # Class-level
    msg = "Cannot protect attribute 'x' after class creation. Ignored"
    with pytest.warns(UserWarning, match=f"^{re.escape(msg)}$"):
        A.x = protected(0)
    assert A.x == 0

    # Instance-level
    a = A()
    msg = "Cannot protect attribute 'x' on instance assignment. Ignored"
    with pytest.warns(UserWarning, match=f"^{re.escape(msg)}$"):
        a.x = protected(1)
    assert a.x == 1


def test_dict_is_protected():
    """Attribute `__dict__` is protected."""
    assert "__dict__" in getattr(ParamClass, IMPL).protected


def test_cannot_turn_previously_protected_into_param():
    """Cannot make non-param protected into parameter."""
    msg = "'params' is protected by 'ParamClass'"
    with pytest.raises(ProtectedError, match=f"^{re.escape(msg)}$"):

        class A(ParamClass):
            params: dict[str, object]  # type:ignore[annotation-unchecked]
