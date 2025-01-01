"""Paramclasses global pytest configuration."""

from collections.abc import Callable
from itertools import chain, product

import pytest

from paramclasses import MISSING, ParamClass, ProtectedError, protected


@pytest.fixture(scope="session")
def test_set_del_is_protected() -> Callable:
    """Test protection against `setattr` and `delattr`."""

    def _test_set_del_is_protected(obj: object, attr: str, regex: str) -> None:
        """Test protection against `setattr` and `delattr`."""
        # Cannot assign
        with pytest.raises(ProtectedError, match=regex):
            setattr(obj, attr, None)

        # Cannot delete
        with pytest.raises(ProtectedError, match=regex):
            delattr(obj, attr)

    return _test_set_del_is_protected


@pytest.fixture(scope="session")
def test_get_set_del_work() -> Callable:
    """Test `getattr`, `setattr`, `delattr` expected to work.

    Run set, then get, then del. Also, if a value is expected to be
    returned by `getattr`, pass it as `expected`. Paramclasses can never
    expect `MISSING` value. In absence of expectation, we suppose that
    the descriptor works "naturally", meaning `getattr` will return the
    just previously set value (if any). This is reasonable since only
    every used with factory descriptors (see `DescriptorFactories`).
    """

    def _test_get_set_del_work(  # noqa: PLR0913
        obj: object,
        attr: str,
        *,
        skip_set: bool = False,
        skip_get: bool = False,
        skip_del: bool = False,
        expected: object = MISSING,
    ) -> None:
        """Test `setattr`, `getattr` and `delattr` expected to work."""
        null = object()
        if not skip_set:
            setattr(obj, attr, null)
        if not skip_get:
            assert getattr(obj, attr) is (null if expected is MISSING else expected)
        if not skip_del:
            delattr(obj, attr)

    return _test_get_set_del_work


@pytest.fixture(scope="session")
def DescriptorFactories() -> dict[tuple[bool, bool, bool], type]:
    """All 8 descriptor (or not) factories."""

    class Filter(type):
        """Removes get/set/delete if required."""

        def __new__(  # noqa: PLR0913
            mcs,  # noqa: N804
            name,
            bases,
            namespace,
            *,
            has_get,
            has_set,
            has_delete,
        ) -> type:
            methods = []
            for attr, keep in zip(
                ["__get__", "__set__", "__delete__"],
                [has_get, has_set, has_delete],
                strict=True,
            ):
                if keep:
                    methods.append(attr)
                else:
                    del namespace[attr]

            methods_str = "".join(attr[2:-2].title() for attr in methods) or "None"
            name = f"DescriptorFactoryWith{methods_str}"
            namespace["__qualname__"] = name
            return super().__new__(mcs, name, bases, namespace)

    _DescriptorFactories: dict[tuple[bool, bool, bool], type] = {}
    for has_get, has_set, has_delete in product([True, False], repeat=3):

        class _DescriptorFactory(
            metaclass=Filter,
            has_get=has_get,
            has_set=has_set,
            has_delete=has_delete,
        ):
            val = object()

            def __get__(self, obj, objtype=None) -> object:
                return self if obj is None else self.val

            def __set__(self, obj, val) -> None:
                self.val = val

            def __delete__(self, obj) -> None: ...

        _DescriptorFactories[has_get, has_set, has_delete] = _DescriptorFactory
    return _DescriptorFactories


# Factory attributes WITHOUT value have 2 flags and are encoded like so:
# `(attr, (is_slot, is_parameter))`.
# Factory attributes WITH value have 5 flags and are encoded like so:
# `(attr, (is_protected, is_parameter, has_get, has_set, has_delete))`.
AttributesWithFlags = tuple[str, tuple[bool, ...]]


@pytest.fixture(scope="session")
def paramtest_attrs_no_value() -> tuple[AttributesWithFlags, ...]:
    """For non-valued attributes, `(attr, (is_slot, is_parameter))`."""
    return (
        ("a_unprotected_parameter_with_nodefaultvalue", (False, True)),
        ("a_unprotected_parameter_slot", (True, True)),
        ("a_unprotected_nonparameter_slot", (False, False)),
    )


@pytest.fixture(scope="session")
def paramtest_attrs_with_value() -> tuple[AttributesWithFlags, ...]:
    """For valued attributes, `(attr, (is_protected, is_parameter, *has_methods))`."""
    out: list[AttributesWithFlags] = []
    for flags in product([True, False], repeat=5):
        is_protected, is_parameter, *has_methods = flags
        has_get, has_set, has_delete = has_methods

        # Generate attribute
        attr = "a_{}protected_{}parameter_with{}{}{}".format(
            "" if is_protected else "un",
            "" if is_parameter else "non",
            "_get" if has_get else "",
            "_set" if has_set else "",
            "_delete" if has_delete else "",
        )
        if not any(has_methods):
            attr += "_none"

        out.append((attr, flags))

    return tuple(out)


@pytest.fixture(scope="session")
def attrs_filter() -> Callable[[tuple[str], str], tuple[str, ...]]:
    """Filter factory attribute collection with expressions."""

    def keep_attr(attr, *expr: str, mode: str) -> bool:
        """Exact match, trailing or between "_"."""
        in_attr = set(attr.split("_"))
        in_expr = set(expr)
        if mode == "and":
            return in_expr.issubset(in_attr)
        if mode == "or":
            return not in_expr.isdisjoint(in_attr)
        if mode == "none":
            return in_expr.isdisjoint(in_attr)

        msg = f"Unsupported filtering mode '{mode}'"
        raise ValueError(msg)

    def _attrs_filter(
        attrs: tuple[str],
        *expr: str,
        mode: str = "and",
    ) -> tuple[str, ...]:
        """Filter factory attribute collection with expressions."""
        if not expr:
            return attrs

        assert "_" not in expr, "Double-marker filtering disabled"
        return tuple(attr for attr in attrs if keep_attr(attr, *expr, mode=mode))

    return _attrs_filter


@pytest.fixture(scope="session")
def paramtest_attrs(
    paramtest_attrs_no_value,
    paramtest_attrs_with_value,
    attrs_filter,
) -> Callable[[str], tuple[str, ...]]:
    """Get factory attributes containing f'_{expr}'."""
    paramtest_attrs = chain(paramtest_attrs_no_value, paramtest_attrs_with_value)
    # Remove flags, keep only attributes
    all_attrs = tuple(next(zip(*paramtest_attrs, strict=True)))

    def _paramtest_attrs_filter(*expr: str, mode: str = "and") -> tuple[str, ...]:
        """Get factory attributes containing f'_{expr}'."""
        out = attrs_filter(all_attrs, *expr, mode=mode)
        if not out:
            msg = f"No factory attribute matches {expr} in mode '{mode}'"
            raise AttributeError(msg)
        return out

    return _paramtest_attrs_filter


@pytest.fixture
def ParamTest(
    DescriptorFactories,
    paramtest_attrs_no_value,
    paramtest_attrs_with_value,
) -> type[ParamClass]:
    """Fixture paramclass with all kinds of attributes.

    Dynamically created paramclass. By "all kinds" we mean regarding
    combinations of being slot/valued/protected/parameter and having
    get/set/delete methods.
    """
    slots: list[str] = []
    annotations: dict[str, object] = {}
    namespace = {
        "__annotations__": annotations,
        "__slots__": slots,
        "__module__": __name__,
    }

    # Non-valued attributes
    for attr, (is_slot, is_parameter) in paramtest_attrs_no_value:
        if is_slot:
            slots.append(attr)
        if is_parameter:
            annotations[attr] = ...

    # Valued attributes
    for attr, (is_protected, is_parameter, *has_methods) in paramtest_attrs_with_value:
        # Generate descriptor and protect if required
        val = DescriptorFactories[tuple(has_methods)]()
        if is_protected:
            val = protected(val)
        # Make parameter by annotating if required
        if is_parameter:
            annotations[attr] = ...
        # Add to factory_dict
        namespace[attr] = val

    return type(ParamClass)("ParamTest", (ParamClass,), namespace)
