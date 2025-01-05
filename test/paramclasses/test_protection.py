"""Tests directly related to @protected."""

import pytest

from paramclasses import PROTECTED, ParamClass, ProtectedError, protected


def test_mcs_is_frozen(assert_set_del_is_protected):
    """Cannot modify `_MetaParamClass' (without altering its meta).

    Its mutables can still be muted, but that is just evil behaviour.
    """
    mcs = type(ParamClass)
    attr = "random_attribute"
    regex = "^`_MetaParamClass' attributes are frozen$"
    assert_set_del_is_protected(mcs, attr, regex)


def test_cannot_subclass_mcs():
    """Cannot subclass `_MetaParamClass' (without altering its meta)."""
    mcs = type(ParamClass)
    regex = "^`_MetaParamClass' cannot be subclassed$"
    with pytest.raises(ProtectedError, match=regex):

        class Sub(mcs):
            __new__ = type.__new__


def test_multiple_protection():
    """Multiple redundant protections are fine."""

    class A(ParamClass):
        @protected
        @protected
        @protected
        def method(self) -> None: ...

    assert "method" in getattr(A, PROTECTED)


def test_simple_protection_inheritance():
    """Subclass cannot override protected."""
    regex = "^'params' is protected by 'ParamClass'$"
    with pytest.raises(ProtectedError, match=regex):

        class A(ParamClass):
            params = 0


def test_multiple_inheritance():
    """Check protection compatibility for multiple inheritance."""

    class A(ParamClass):
        x = protected(0)

    class B(ParamClass):
        x = 0

    class C:
        x = 0

    for Other in (B, C):
        # Coherent protection order: OK
        class C(A, Other): ...

        # Incoherent protection order
        regex = f"^'x' protection conflict: 'A', '{Other.__name__}'$"
        with pytest.raises(ProtectedError, match=regex):

            class D(Other, A): ...


def test_cannot_slot_previously_protected():
    """Cannot slot previously protected attribute."""
    regex = (
        r"^Cannot slot the following protected attributes: '__paramclass_protected_' "
        r"\(from <paramclasses root protection>\), 'params' \(from 'ParamClass'\)$"
    )
    with pytest.raises(ProtectedError, match=regex):

        class A(ParamClass):
            __slots__ = ("__paramclass_protected_", "params")


def test_post_creation_protection():
    """Post-creation protection is ignored, with warning."""

    class A(ParamClass): ...

    # Class-level
    regex = "^Cannot protect attribute 'x' after class creation. Ignored$"
    with pytest.warns(UserWarning, match=regex):
        A.x = protected(0)
    assert A.x == 0

    # Instance-level
    a = A()
    regex = "^Cannot protect attribute 'x' on instance assignment. Ignored$"
    with pytest.warns(UserWarning, match=regex):
        a.x = protected(1)
    assert a.x == 1


def test_dict_is_protected():
    """Attribute `__dict__` is protected."""
    assert "__dict__" in getattr(ParamClass, PROTECTED)


def test_cannot_turn_previously_protected_into_param():
    """Cannot make non-param protected into parameter."""
    regex = "^'params' is protected by 'ParamClass'$"
    with pytest.raises(ProtectedError, match=regex):

        class A(ParamClass):
            params: dict[str, object]  # type:ignore[annotation-unchecked]
