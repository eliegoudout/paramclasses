"""Tests directly related to @protected."""

from itertools import chain

import pytest

from paramclasses import PROTECTED, ParamClass, ProtectedError, protected


def test_mcs_is_frozen(test_set_del_is_protected):
    """Cannot modify `_MetaParamClass' (without altering its meta).

    Its mutables can still be muted, but that is just evil behaviour.
    """
    mcs = type(ParamClass)
    attr = "random_attribute"
    regex = "^`_MetaParamClass' attributes are frozen$"
    test_set_del_is_protected(mcs, attr, regex)


def test_cannot_subclass_mcs():
    """Cannot subclass `_MetaParamClass' (without altering its meta)."""
    mcs = type(ParamClass)
    regex = "^`_MetaParamClass' cannot be subclassed$"
    with pytest.raises(ProtectedError, match=regex):

        class Sub(mcs):
            __new__ = type.__new__


def test_protection_works_on_class_and_instances(
    ParamTest,
    test_set_del_is_protected,
    paramtest_attrs,
):
    """Cannot set/delete protected attributes for classes/istances."""
    for attr in paramtest_attrs("protected"):
        regex = f"^Attribute '{attr}' is protected$"
        test_set_del_is_protected(ParamTest, attr, regex)
        test_set_del_is_protected(ParamTest(), attr, regex)


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
    regex = "^Attribute 'params' is protected$"
    with pytest.raises(ProtectedError, match=regex):

        class A(ParamClass):
            params = 0


def test_multiple_inheritance():
    """Check protection compatibility for multiple inheritance."""

    class A(ParamClass):
        x = protected(0)

    class B(ParamClass):
        x = 0

    class C(ParamClass):
        x = 0.0

    # Coherent protection order
    class D(A, B): ...

    # Incoherent order but same value so compatible
    class E(B, A): ...

    # Previously protected and incompatible value
    regex = "^Incoherent protection inheritance for attribute 'x'$"
    with pytest.raises(ProtectedError, match=regex):

        class F(C, A): ...


def test_cannot_slot_previously_protected():
    """Cannot slot previously protected attribute."""
    regex = "^Cannot slot already protected attributes: {'params'}$"
    with pytest.raises(ProtectedError, match=regex):

        class A(ParamClass):
            __slots__ = ("params",)


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


def test_protected_dict_manipulation_removed_on_get(ParamTest, paramtest_attrs):
    """For protected, direct `vars(self)` assignments removed on get."""
    null = object()
    instance = ParamTest()
    for attr in chain(paramtest_attrs("protected"), ["__dict__"]):
        before_dict_assignment = getattr(instance, attr, null)
        instance.__dict__[attr] = 0
        after_dict_assignment = getattr(instance, attr, null)
        # Get was not affected by `__dict__` manipulations and removed them
        assert after_dict_assignment is before_dict_assignment
        assert attr not in vars(instance)


def test_cannot_turn_previously_protected_into_param():
    """Cannot make non-param protected into parameter."""
    regex = "^Attribute 'params' is protected$"
    with pytest.raises(ProtectedError, match=regex):

        class A(ParamClass):
            params: dict[str, object]  # type:ignore[annotation-unchecked]
