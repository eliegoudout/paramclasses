"""Test the runtime signature and `__signature__` property.

When dropping 3.12, replace `repr(Signature)` with `Signature.format()`.
"""

import re
from inspect import signature

import pytest

from paramclasses import ParamClass

from .conftest import make_with_post_init, parametrize_attr_kind, parametrize_bool


@parametrize_attr_kind("unprotected", "parameter")
def test_signature_call_and_set_params_on_parameter(attr, kind, make, null):
    """For parameters, `set_params` works fine."""
    Param, param_set_params = make("Param, param", kind)
    kw = {attr: null}
    param_init = Param(**kw)
    param_set_params.set_params(**kw)

    assert getattr(param_init, attr) is null
    assert getattr(param_set_params, attr) is null


@parametrize_attr_kind("nonparameter")
def test_signature_call_and_set_params_on_nonparameter(attr, kind, make, null):
    """Using `set_params` on nonparameters fails."""
    Param, param_set_params = make("Param, param", kind)
    kw = {attr: null}

    msg = f"Invalid parameters: { {attr} }. Operation cancelled"
    with pytest.raises(AttributeError, match=f"^{re.escape(msg)}$"):
        Param(**kw)

    with pytest.raises(AttributeError, match=f"^{re.escape(msg)}$"):
        param_set_params.set_params(**kw)


def test_signature_call_no_post_init(make):
    """Check that provided arguments raise error when no post-init."""
    Param = make("Param")

    msg = "Unexpected positional arguments (no '__post_init__' is defined)"
    with pytest.raises(TypeError, match=f"^{re.escape(msg)}$"):
        Param(None)


@pytest.mark.parametrize("kind", ["normal", "static", "class"])
@parametrize_bool("pos_only, pos_or_kw, var_pos, kw_only, var_kw, prefer_kw")
def test_signature_call_valid(
    pos_only,
    pos_or_kw,
    var_pos,
    kw_only,
    var_kw,
    prefer_kw,
    kind,
):
    """Test runtime call consistent with `__signature__` property."""
    ParamWithPostInit = make_with_post_init(
        pos_only=pos_only,
        pos_or_kw=pos_or_kw,
        var_pos=var_pos,
        kw_only=kw_only,
        var_kw=var_kw,
        kind=kind,
    )

    # Prepare valid arguments
    args = []
    kwargs = {}
    if pos_only:
        args.append("pos_only")
    if pos_or_kw:
        if prefer_kw and not var_pos:
            kwargs["pos_or_kw"] = "pos_or_kw"
        else:
            args.append("pos_or_kw")
    if var_pos:
        args.append("var_pos")
    if kw_only:
        kwargs["kw_only"] = "kw_only"
    if var_kw:
        kwargs["var_kw"] = "var_kw"

    # Test valid call
    accepts_args = pos_only or pos_or_kw or var_pos
    accepts_kwargs = pos_or_kw or kw_only or var_kw

    args_kwargs = []
    if accepts_args:
        args_kwargs.append(args)
    if accepts_kwargs:
        args_kwargs.append(kwargs)

    ParamWithPostInit(*args_kwargs)  # Works


@pytest.mark.parametrize("kind", ["normal", "static", "class"])
@parametrize_bool("pos_only, pos_or_kw, var_pos, kw_only, var_kw")
def test_signature_call_too_many_arguments(
    pos_only,
    pos_or_kw,
    var_pos,
    kw_only,
    var_kw,
    kind,
):
    """Test runtime call consistent with `__signature__` property."""
    ParamWithPostInit = make_with_post_init(
        pos_only=pos_only,
        pos_or_kw=pos_or_kw,
        var_pos=var_pos,
        kw_only=kw_only,
        var_kw=var_kw,
        kind=kind,
    )

    accepts_args = pos_only or pos_or_kw or var_pos
    accepts_kwargs = pos_or_kw or kw_only or var_kw
    n_expexcted = accepts_args + accepts_kwargs

    msg = (
        f"Invalid '__post_init__' arguments. Signature: {ParamWithPostInit.__name__}"
        f"{signature(ParamWithPostInit)}"
    )
    with pytest.raises(TypeError, match=f"^{re.escape(msg)}$"):
        ParamWithPostInit(*range(n_expexcted + 1))


@pytest.mark.parametrize("kind", ["normal", "static", "class"])
@parametrize_bool("pos_only, pos_or_kw, var_pos, kw_only, var_kw")
def test_signature_call_non_unpackable(
    pos_only,
    pos_or_kw,
    var_pos,
    kw_only,
    var_kw,
    kind,
):
    """Test runtime call consistent with `__signature__` property."""
    ParamWithPostInit = make_with_post_init(
        pos_only=pos_only,
        pos_or_kw=pos_or_kw,
        var_pos=var_pos,
        kw_only=kw_only,
        var_kw=var_kw,
        kind=kind,
    )

    accepts_args = pos_only or pos_or_kw or var_pos
    accepts_kwargs = pos_or_kw or kw_only or var_kw
    # >=3.15.0a2-compatible message (python/cpython/pull/136395)
    msg = " after * must be an iterable, not NoneType"

    # Non-unpackable ``args``
    if accepts_args:
        args_kwargs = [None, {}] if accepts_kwargs else [None]
        with pytest.raises(TypeError, match=f"{re.escape(msg)}$"):
            ParamWithPostInit(*args_kwargs)

    # Non-unpackable ``kwargs``
    if accepts_kwargs:
        args_kwargs = [[], None] if accepts_args else [None]
        with pytest.raises(TypeError, match=f"{re.escape(msg)}$"):
            ParamWithPostInit(*args_kwargs)


@pytest.mark.parametrize("kind", ["normal", "static", "class"])
@parametrize_bool("pos_only, var_pos")
def test_signature_call_args_as_mapping(
    pos_only,
    var_pos,
    kind,
):
    """Test runtime call consistent with `__signature__` property."""
    # Filter accept args
    if not pos_only and not var_pos:
        return

    ParamWithPostInit = make_with_post_init(
        pos_only=pos_only,
        pos_or_kw=False,
        var_pos=var_pos,
        kw_only=False,
        var_kw=False,
        kind=kind,
    )

    msg = (
        "To avoid confusion, passing 'post_init_args' as a mapping is not supported. "
        "Use 'iter(your_mapping)' instead"
    )
    args = {"pos_arg": "from mapping key"}
    with pytest.raises(TypeError, match=f"^{re.escape(msg)}$"):
        ParamWithPostInit(args)


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


def test_signature_property_no_post_init():
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
def test_signature_property_post_init(
    pos_only,
    pos_or_kw,
    var_pos,
    kw_only,
    var_kw,
    kind,
):
    """Test `__signature__` property with all possible `__post_init__`.

    Test normal method, staticmethod and classmethod., no parameters.
    """
    ParamWithPostInit = make_with_post_init(
        pos_only=pos_only,
        pos_or_kw=pos_or_kw,
        var_pos=var_pos,
        kw_only=kw_only,
        var_kw=var_kw,
        kind=kind,
    )

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
    assert repr(signature(ParamWithPostInit)) == expected
