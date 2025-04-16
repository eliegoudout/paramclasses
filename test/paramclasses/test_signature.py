"""Test the `__signature__` property.

When dropping 3.12, replace `repr(Signature)` with `Signature.format()`.
"""

from inspect import signature

import pytest

from paramclasses import ParamClass


def test_signature_no_post_init():
    """Test `__signature__` property."""

    class A(ParamClass):
        x: float  # type:ignore[annotation-unchecked]
        y: int = 0  # type:ignore[annotation-unchecked]
        z: str = 0  # type:ignore[annotation-unchecked]
        t = 0

    expected = "(*, x: float = ?, y: int = 0, z: str = 0)"
    assert repr(signature(A)) == f"<Signature {expected}>"


def test_signature_with_post_init():
    """Test `__signature__` property."""

    class A(ParamClass):
        x: float  # type:ignore[annotation-unchecked]
        y: int = 0  # type:ignore[annotation-unchecked]
        z: str = 0  # type:ignore[annotation-unchecked]
        t = 0

        def __post_init__(self, a, b, c) -> None:
            """Test with standard method."""

    expected = (
        "(post_init_args=[], post_init_kwargs={}, /, "
        "*, x: float = ?, y: int = 0, z: str = 0)"
    )
    assert repr(signature(A)) == f"<Signature {expected}>"


def test_signature_post_init_pos_and_kw():
    """Test `__signature__` property with `__post_init__`.

    Test classical method, staticmethod and classmethod.
    """

    class A(ParamClass):
        def __post_init__(self, a, /, b, *, c) -> None:
            """Test with standard method."""

    class B(ParamClass):
        @classmethod
        def __post_init__(cls, a, /, b, *, c) -> None:
            """Test with classmethod."""

    class C(ParamClass):
        @staticmethod
        def __post_init__(a, /, b, *, c) -> None:
            """Test with staticmethod."""

    expected = "(post_init_args=[], post_init_kwargs={}, /)"
    for cls in [A, B, C]:
        assert repr(signature(cls)) == f"<Signature {expected}>"


def test_signature_post_init_pos_only():
    """Test `__signature__` property with `__post_init__`.

    Test classical method, staticmethod and classmethod.
    """

    class A(ParamClass):
        def __post_init__(self, a, /) -> None:
            """Test with standard method."""

    class B(ParamClass):
        @classmethod
        def __post_init__(cls, a, /) -> None:
            """Test with classmethod."""

    class C(ParamClass):
        @staticmethod
        def __post_init__(a, /) -> None:
            """Test with staticmethod."""

    expected = "(post_init_args=[], /)"
    for cls in [A, B, C]:
        assert repr(signature(cls)) == f"<Signature {expected}>"


def test_signature_post_init_kw_only():
    """Test `__signature__` property with `__post_init__`.

    Test classical method, staticmethod and classmethod.
    """

    class A(ParamClass):
        def __post_init__(self, *, c) -> None:
            """Test with standard method."""

    class B(ParamClass):
        @classmethod
        def __post_init__(cls, *, c) -> None:
            """Test with classmethod."""

    class C(ParamClass):
        @staticmethod
        def __post_init__(*, c) -> None:
            """Test with staticmethod."""

    expected = "(post_init_kwargs={}, /)"
    for cls in [A, B, C]:
        assert repr(signature(cls)) == f"<Signature {expected}>"


def test_signature_post_init_argless():
    """Test `__signature__` property with `__post_init__`.

    Test classical method, staticmethod and classmethod.
    """

    class A(ParamClass):
        def __post_init__(self) -> None:
            """Test with standard method."""

    class B(ParamClass):
        @classmethod
        def __post_init__(cls) -> None:
            """Test with classmethod."""

    class C(ParamClass):
        @staticmethod
        def __post_init__() -> None:
            """Test with staticmethod."""

    expected = "()"
    for cls in [A, B, C]:
        assert repr(signature(cls)) == f"<Signature {expected}>"


def test_post_init_must_be_callable():
    """Test `__signature__` error when `__post_init__` not callable."""

    class A(ParamClass):
        __post_init__ = 0

    regex = r"^'__post_init__' attribute must be callable$"
    with pytest.raises(TypeError, match=regex):
        A.__signature__  # noqa: B018 (not useless)
