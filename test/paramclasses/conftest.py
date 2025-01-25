"""Paramclasses global pytest configuration."""

import inspect
from collections.abc import Callable, Iterable
from itertools import chain, pairwise, product, starmap
from types import MappingProxyType
from typing import Generator, Literal, NamedTuple

import pytest

from paramclasses import MISSING, ParamClass, ProtectedError, protected
from paramclasses.paramclasses import _unprotect


@pytest.fixture(scope="session")
def unprotect() -> Callable:
    """Unprotect the @protected`."""
    return lambda val: _unprotect(val)[0]


@pytest.fixture(scope="session")
def assert_set_del_is_protected() -> Callable:
    """Test protection against `setattr` and `delattr`."""

    def _assert_set_del_is_protected(obj: object, attr: str, regex: str) -> None:
        """Test protection against `setattr` and `delattr`."""
        # Cannot assign
        with pytest.raises(ProtectedError, match=regex):
            setattr(obj, attr, None)

        # Cannot delete
        with pytest.raises(ProtectedError, match=regex):
            delattr(obj, attr)

    return _assert_set_del_is_protected


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
def DescriptorFactories() -> dict[tuple[bool, ...], type]:
    """All 8 descriptor (or not) factories."""

    class UsedGet(AttributeError): ...  # noqa: N818

    class UsedSet(AttributeError): ...  # noqa: N818

    class UsedDelete(AttributeError): ...  # noqa: N818

    def desc(obj) -> str:
        """To make error message comparable, no address."""
        if inspect.isclass(obj):
            return f"<class {obj.__name__}>"
        return f"<instance of {type(obj).__name__}>"

    def get_method(self, obj, type: type) -> None:  # noqa: A002
        msg = f"Used __get__(self: {desc(self)}, obj: {desc(obj)}, type: {desc(type)})"
        raise UsedGet(msg)

    def set_method(self, obj, val) -> None:
        msg = f"Used __set__(self: {desc(self)}, obj: {desc(obj)}, value: {desc(val)})"
        raise UsedGet(msg)

    def delete_method(self, obj) -> None:
        msg = f"Used __delete__(self: {desc(self)}, obj: {desc(obj)})"
        raise UsedGet(msg)

    _DescriptorFactories: dict[tuple[bool, ...], type] = {}
    attrs = ("__get__", "__set__", "__delete__")
    methods = (get_method, set_method, delete_method)
    for has_methods in product([True, False], repeat=3):
        namespace = {
            attr: method
            for attr, method, has_method in zip(
                attrs,
                methods,
                has_methods,
                strict=False,
            )
            if has_method
        }
        methods_str = (
            "".join(
                attr[2:-2].title()
                for attr, has_method in zip(attrs, has_methods, strict=False)
                if has_method
            )
            or "Non"
        )
        factory_name = f"{methods_str}DescriptorFactory"

        _DescriptorFactories[has_methods] = type(factory_name, (), namespace)

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
        ("a_unprotected_parameter_with_missing", (False, True)),
        ("a_unprotected_parameter_slot", (True, True)),
        ("a_unprotected_nonparameter_slot", (True, False)),
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
            attr += "_nondescriptor"

        out.append((attr, flags))

    return tuple(out)


FilterMode = Literal["and", "or", "none"]


@pytest.fixture(scope="session")
def attrs_filter() -> Callable[[tuple[str, ...], str, FilterMode], tuple[str, ...]]:
    """Filter factory attribute collection with expressions.

    Arguments:
        attrs (tuple[str, ...]): Tuple of factory attribute names.
        *exprs (str): Expressions to be matched exactly for filtering.
        mode (FilterMode): Mode to pass filter, "and" means all filter
            must be matched, "or" means at least one and "none" means
            none.

    """

    def keep_attr(attr, *expr: str, mode: FilterMode) -> bool:
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
        attrs: tuple[str, ...],
        *expr: str,
        mode: FilterMode = "and",
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


@pytest.fixture(scope="session")
def paramtest_namespace(
    DescriptorFactories,
    paramtest_attrs_no_value,
    paramtest_attrs_with_value,
) -> MappingProxyType:
    """Namespace for class fixtures."""
    # Non-valued attributes
    slots: list[str] = []
    annotations: dict[str, object] = {}
    for attr, (is_slot, is_parameter) in paramtest_attrs_no_value:
        if is_slot:
            slots.append(attr)
        if is_parameter:
            annotations[attr] = ...

    # Valued attributes
    namespace: dict[str, object] = {}
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

    # Make it essentially immutable -- modulo descriptors immutability
    namespace["__annotations__"] = MappingProxyType(annotations)
    namespace["__slots__"] = tuple(slots)
    namespace["__module__"] = __name__
    return MappingProxyType(namespace)


@pytest.fixture
def ParamTest(paramtest_namespace) -> type[ParamClass]:
    """Fixture paramclass with all kinds of attributes.

    Dynamically created paramclass. By "all kinds" we mean regarding
    combinations of being slot/valued/protected/parameter and having
    get/set/delete methods.
    """
    return type(ParamClass)("ParamTest", (ParamClass,), dict(paramtest_namespace))


@pytest.fixture
def VanillaTest(paramtest_namespace, unprotect) -> type:
    """Analogue to `ParamTest` for vanilla classes."""
    # Unprotect and enable dict
    namespace = {attr: unprotect(val) for attr, val in paramtest_namespace.items()}
    namespace["__slots__"] = namespace["__slots__"] + ("__dict__",)
    return type("VanillaTest", (), namespace)


@pytest.fixture
def obj(
    paramtest_attrs,
    ParamTest,
    VanillaTest,
) -> object:
    """Object of Vanilla or Param classes, with dict filled or not."""

    def _obj(kind: Literal["Param", "Vanilla"], *, fill_dict: bool = False) -> object:
        if kind == "Param":
            instance = ParamTest()
        elif kind == "Vanilla":
            instance = VanillaTest()
        else:
            msg = f"Invalid class kind '{kind}'"
            raise ValueError(msg)

        if not fill_dict:
            return instance

        # Fill vars(instance) manually
        for attr in chain(paramtest_attrs()):
            vars(instance)[attr] = None

        return instance

    return _obj


@pytest.fixture(scope="session")
def assert_same_behaviour() -> Callable:
    """Test whether all `obj` behave similarly for `attr`.

    WARNING: By iteracting with `ops`, objects or their classes may be
    modified.

    Arguments:
        *objs (object): Objects whose behaviour is compared.
        attr (str): The attribute to get / set / delete.
        ops (str | tuple[str, ...]): One or more operations to execute
            one after the other. Each in `{"get", "set", "delete"}`.

    """

    def _assert_consistency(
        iterable: Iterable,
        *,
        desc: str = "",
        ctxt: Callable[[int], object] | None = None,
        mode: Literal["==", "is"],
    ) -> object:
        """Check `==` or `is' along iterable and return last value."""
        msg_ = f"Inconsistency: {desc}" + (". Context:\n{}" if ctxt else "")

        no_pairs = True
        for i, (obj1, obj2) in enumerate(pairwise(iterable)):
            msg = msg_.format(ctxt(i)) if ctxt else msg_
            if mode == "==":
                assert obj1 == obj2, msg
            elif mode == "is":
                assert obj1 is obj2, msg
            else:
                msg = f"Invalid mode '{mode}' for '_assert_consistency'"
                raise ValueError(msg)
            no_pairs = False

        assert not no_pairs, "Provide at least 2-long iterable"
        return obj2

    opattr = Literal["get", "set", "delete"]

    def _assert_same_behaviour(
        *objs: object,
        attr: str,
        ops: opattr | tuple[opattr, ...],
    ) -> None:
        # Objects should all be classes or all non-class
        are_classes = _assert_consistency(
            map(inspect.isclass, objs),
            mode="==",
            desc="'isclass' flags",
            ctxt=lambda i: f"objects: {objs[i]}, {objs[i + 1]}",
        )

        if isinstance(ops, str):
            ops = (ops,)

        null = object()
        do = {
            "get": getattr,
            "set": lambda obj, attr: setattr(obj, attr, null),
            "delete": delattr,
        }
        assert set(ops).issubset(do), f"Invalid ops: {ops}"

        # Collect behaviour
        collected: tuple[list, ...] = tuple([] for _ in objs)
        for (i, obj), op in product(enumerate(objs), ops):
            # Unify classname before collecting, to unify error messages.
            cls: type = obj if are_classes else type(obj)  # type: ignore[assignment]
            name = cls.__name__
            qualname = cls.__qualname__
            cls.__qualname__ = "UniqueQualnameClass"
            cls.__name__ = "UniqueNameClass"
            try:
                collected[i].append((name, False, do[op](obj, attr)))
            except AttributeError as e:
                collected[i].append((name, True, f"{type(e).__name__}: {e}"))
            cls.__qualname__ = qualname
            cls.__name__ = name

        # Loop through ops
        for i, collected_op in enumerate(zip(*collected, strict=False)):
            names, exception_flags, blueprints = zip(*collected_op, strict=False)
            ctxt = lambda j: "\n".join([  # noqa: E731
                f"attr: '{attr}'",
                f"classes: '{names[j]}', '{names[j + 1]}'",  # noqa: B023
                f"blueprints: '{blueprints[j]}', '{blueprints[j + 1]}'",  # noqa: B023
            ])
            ops_str = f"'{' > '.join(ops[: i + 1])}'"

            # All exceptions or all outputs
            are_exceptions = _assert_consistency(
                exception_flags,
                mode="==",
                desc=f"'is_exception' flags after {ops_str}",
                ctxt=ctxt,
            )

            # Check exceptions or outputs are consistent
            _ = _assert_consistency(
                blueprints,
                mode="==" if are_exceptions else "is",
                desc=f"{'exceptions' if are_exceptions else 'outputs'} after {ops_str}",
                ctxt=ctxt,
            )

    return _assert_same_behaviour


from typing import Generator, NamedTuple
from itertools import compress


class AttributeKind(NamedTuple):
    protected: bool = False
    parameter: bool = False
    slot: bool = False
    missing: bool = False
    has_get: bool = False
    has_set: bool = False
    has_delete: bool = False

    @property
    def has_methods(self) -> tuple[bool, bool, bool]:
        return self.has_get, self.has_set, self.has_delete

    def __str__(self) -> str:
        base = f"{'' if self.protected else 'un'}protected_{'' if self.parameter else 'non'}parameter"

        if self.slot:
            assert not self.protected, "Cannot protect slot"
            return f"{base}_slot"

        if self.missing:
            assert not self.protected, "Cannot protect missing"
            assert self.parameter, "Only parameters can be missing"
            return f"{base}_missing"

        methods = "".join(compress(["get", "set", "delete"], self.has_methods)) or "non"
        return f"{base}_with_{methods}descriptor"

    def __repr__(self) -> str:
        """Human-readable repr."""
        _, sep, tail = type(self).__mro__[1].__repr__(self).partition("(")
        return f"{type(self).__name__}[{self}]{sep}{tail}"


def attribute_kinds(*filters) -> Generator[tuple[str, AttributeKind], None, None]:
    """Generate all kinds of attributes, with filtering options."""
    # Process filters
    from collections import namedtuple
    import re
    filtered = namedtuple("Filtered", AttributeKind._fields)(*({True, False} for _ in "_" * 7))
    for filter_ in filters:
        if match := re.fullmatch(r"(un)?protected", filter_):
            filtered.protected.discard(bool(match.group(1)))
        elif match := re.fullmatch(r"(non)?parameter", filter_):
            filtered.parameter.discard(bool(match.group(1)))
        elif match := re.fullmatch(r"(non)?slot", filter_):
            filtered.slot.discard(bool(match.group(1)))
        elif match := re.fullmatch(r"(non)?missing", filter_):
            filtered.missing.discard(bool(match.group(1)))
        else:            
            msg = f"Invalid filter '{filter_}'. Consider adding it if necessary"
            raise ValueError(msg)

    # General unfiltered constraints (slots, missing, others)
    constraints = zip(
    #    Slots          Missing  Others
        ({False},       {False}, {True, False}),  # protected
        ({True, False}, {True},  {True, False}),  # parameter
        ({True},        {False}, {False}),        # slot
        ({False},       {True},  {False}),        # missing
        ({True},        {False}, {True, False}),  # has_get
        ({True},        {False}, {True, False}),  # has_set
        ({True},        {False}, {True, False})   # has_delete
    )

    def combinations_from_constraint(constraint):
        """Generate compliant `AttributeKind` arguments."""
        return product(*map(set.intersection, filtered, constraint))

    # Yield
    yielded = 0
    for args in chain(*map(combinations_from_constraint, constraints)):
        attr_kind = AttributeKind(*args)
        yield str(attr_kind), attr_kind
        yielded += 1

    # Raise on zero match
    if not yielded:
        msg = f"No factory attribute matches {filters}"
        raise ValueError(msg)

    return yielded


def _DescriptorFactories() -> dict[tuple[bool, ...], type]:
    """All 8 (non)descriptor factories."""

    class UsedGet(AttributeError): ...  # noqa: N818

    class UsedSet(AttributeError): ...  # noqa: N818

    class UsedDelete(AttributeError): ...  # noqa: N818

    def desc(obj) -> str:
        """To make error message comparable, no address."""
        if inspect.isclass(obj):
            return f"<class {obj.__name__}>"
        return f"<instance of {type(obj).__name__}>"

    def get_method(self, obj, type: type) -> None:  # noqa: A002
        msg = f"Used __get__(self: {desc(self)}, obj: {desc(obj)}, type: {desc(type)})"
        raise UsedGet(msg)

    def set_method(self, obj, val) -> None:
        msg = f"Used __set__(self: {desc(self)}, obj: {desc(obj)}, value: {desc(val)})"
        raise UsedGet(msg)

    def delete_method(self, obj) -> None:
        msg = f"Used __delete__(self: {desc(self)}, obj: {desc(obj)})"
        raise UsedGet(msg)

    desc_methods = (get_method, set_method, delete_method)
    desc_attrs = ("__get__", "__set__", "__delete__")
    desc_titles = tuple(attr[2:-2].title() for attr in desc_attrs)
    out = {}
    for mask in product([True, False], repeat=3):
        attrs = tuple(compress(desc_attrs, mask))
        methods = tuple(compress(desc_methods, mask))
        titles = tuple(compress(desc_titles, mask))
        namespace = dict(zip(attrs, methods))
        name = f"{''.join(titles) or 'Non'}DescriptorFactory"
        out[mask] = type(name, (), namespace)

    return out

DescriptorFactories_ = MappingProxyType(_DescriptorFactories())


@pytest.fixture(scope="session", autouse=True)
def make():
    """Generate custom class dynamically."""
    supported_kinds_cls = frozenset({"Param", "Vanilla"})
    supported_kinds = frozenset({"Param", "param", "param_fill", "Vanilla", "vanilla", "vanilla_fill"})

    def _make(kinds: str, *attr_kinds: AttributeKind, fill: object = None) -> object:
        kinds_tpl = tuple(kind.strip() for kind in kinds.split(","))
        assert supported_kinds.issuperset(kinds_tpl), f"Invalid obj kind in {kinds_tpl}"
        kinds_cls = set(kind.removesuffix("_fill").title() for kind in kinds_tpl)

        # Pre-process attributes
        slots = []
        annotations = {}
        vals = {}
        attrs = []
        for attr_kind in attr_kinds:
            attr = str(attr_kind)
            attrs.append(attr)
            if attr_kind.slot:
                slots.append(attr)
            if attr_kind.parameter:
                annotations[attr] = ...
            if not attr_kind.slot and not attr_kind.missing:
                vals[attr] = DescriptorFactories_[attr_kind.has_methods](), attr_kind.protected

        # Dynamiclly create needed classes
        classes = {}
        for kind_cls in kinds_cls:
            paramcls = kind_cls == "Param"
            namespace = {"__module__": __name__}
            for attr, (val, is_protected) in vals.items():
                namespace[attr] = protected(val) if paramcls and is_protected else val

            if slots:
                namespace["__slots__"] = slots + ([] if paramcls else ["__dict__"])

            if annotations:
                namespace["__annotations__"] = annotations

            mcs = type(ParamClass) if paramcls else type
            name = f"{'Param' if paramcls else 'Vanilla'}Test"
            bases = (ParamClass,) if paramcls else ()
            classes[kind_cls] = mcs(name, bases, namespace)

        # Create and return requested classes / objects
        out = []
        for kind in kinds_tpl:
            # `kind` is a class
            if kind in supported_kinds_cls:
                out.append(classes[kind])
                continue

            # `kind` is an object
            kind, _fill, _ = kind.partition("_fill")
            obj = classes[kind.title()]()

            # `kind` requires filling `vars(obj)`
            if _fill:
                for attr in attrs:
                    vars(obj)[attr] = fill

            out.append(obj)

        return out if len(out) > 1 else out[0]

    return _make


def parametrize_attr_kind(*args, **kw):
    """Parametrize attr_kind specifically."""
    def ids(attr_or_kind) -> str:
        return attr_or_kind if isinstance(attr_or_kind, str) else ""

    return pytest.mark.parametrize("attr, kind", attribute_kinds(*args, **kw), ids=ids)
