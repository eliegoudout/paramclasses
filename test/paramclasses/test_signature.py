"""Test the `__signature__` property.

When dropping 3.12, replace `repr(Signature)` with `Signature.format()`.
"""

from inspect import signature

import pytest

from paramclasses import ParamClass

from .conftest import make_post_init, parametrize_bool


def test_signature_property_explicit():
    """Test `__signature__` property on explicit example with params."""

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


def test_signature_no_post_init():
    """Test `__signature__` property."""

    class A(ParamClass):
        x: float  # type:ignore[annotation-unchecked]
        y: int = 0  # type:ignore[annotation-unchecked]
        z: str = 0  # type:ignore[annotation-unchecked]
        t = 0

    expected = "(*, x: float = ?, y: int = 0, z: str = 0)"
    assert repr(signature(A)) == f"<Signature {expected}>"


@pytest.mark.parametrize("kind", ["normal", "static", "class"])
@parametrize_bool("pos_only, pos_or_kw, var_pos, kw_only, var_kw")
def test_signature_property_post_init(pos_only, pos_or_kw, var_pos, kw_only, var_kw, kind):
    """Test `__signature__` property with all possible `__post_init__`.

    Test normal method, staticmethod and classmethod.
    """
    class PostInit(ParamClass):
        __post_init__ = make_post_init(pos_only, pos_or_kw, var_pos, kw_only, var_kw, kind)

    # Compute expected signature
    accepts_args = pos_only or pos_or_kw or var_pos
    accepts_kwargs = pos_or_kw or kw_only or var_kw

    argnames = []
    if accepts_args:
        argnames.append("post_init_args=[]")
    if accepts_kwargs:
        argnames.append("post_init_kwargs={}")
    if argnames:
        argnames.append("/")

    expected = f"<Signature ({', '.join(argnames)})>"
    assert repr(signature(PostInit)) == expected


@pytest.mark.parametrize("kind", ["normal", "static", "class"])
@parametrize_bool("pos_only, pos_or_kw, var_pos, kw_only, var_kw")
def test_signature_call_post_init(pos_only, pos_or_kw, var_pos, kw_only, var_kw, kind):
    """Test runtime call consistent with `__signature__` property."""
    assert 0, "To Do"
