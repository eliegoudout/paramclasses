"""Paramclasses global pytest configuration."""

__all__ = ["attributes", "attributes_kinds", "kinds", "parametrize_attr_kind"]

import inspect
import re
from collections.abc import Callable, Generator, Iterable
from itertools import chain, compress, pairwise, product, repeat
from types import MappingProxyType
from typing import Literal, NamedTuple

import pytest

from paramclasses import ParamClass, ProtectedError, protected


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


class _AttributeKind(NamedTuple):
    """Define the kind of attribute.

    Based on following degrees of freedom: slot, protected, parameter,
    missing value, get/set/delete descriptor.
    """

    protected: bool = False
    parameter: bool = False
    slot: bool = False
    missing: bool = False
    has_get: bool = False
    has_set: bool = False
    has_delete: bool = False

    @property
    def has_methods(self) -> tuple[bool, bool, bool]:
        """Group descriptor-specific flags."""
        return self.has_get, self.has_set, self.has_delete

    def __str__(self) -> str:
        """Name for kind, e.g. `unprotected_parameter_slot`."""
        base = (
            f"{'' if self.protected else 'un'}protected_"
            f"{'' if self.parameter else 'non'}parameter"
        )

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
        """Human-readable repr for debug."""
        # Weird shenanigans because `NamedTuple` is not a real class -- cf. source
        # code --, so `super().__repr__()` or `NamedTuple.__repr__(self)` do not work
        super_repr = type(self).__mro__[1].__repr__(self)  # type: ignore[call-arg]
        _, sep, tail = super_repr.partition("(")
        return f"{type(self).__name__}[{self}]{sep}{tail}"


def attributes_kinds(*filters: str) -> Generator[tuple[str, _AttributeKind], None, int]:
    """Generate all kinds of attributes, with filtering options."""
    # Process filters
    fields = tuple(zip(_AttributeKind._fields, repeat(set[bool])))
    filtered = NamedTuple("Filtered", fields)(*({True, False} for _ in fields))  # type: ignore[operator]
    for filter_ in filters:
        if match := re.fullmatch(r"(un)?protected", filter_):
            filtered.protected.discard(bool(match.group(1)))
        elif match := re.fullmatch(r"(non)?parameter", filter_):
            filtered.parameter.discard(bool(match.group(1)))
        elif match := re.fullmatch(r"(non)?slot", filter_):
            filtered.slot.discard(bool(match.group(1)))
        elif match := re.fullmatch(r"(non)?missing", filter_):
            filtered.missing.discard(bool(match.group(1)))
        elif match := re.fullmatch(r"nondescriptor", filter_):
            discard: bool = True
            filtered.has_get.discard(discard)
            filtered.has_set.discard(discard)
            filtered.has_delete.discard(discard)
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
        ({True},        {False}, {True, False}),  # has_delete
        strict=True,
    )  # fmt: skip

    def combinations_from_constraint(constraint) -> Iterable[tuple[bool, ...]]:
        """Generate compliant `_AttributeKind` arguments."""
        return product(*map(set.intersection, filtered, constraint))

    # Yield
    yielded = 0
    for args in chain(*map(combinations_from_constraint, constraints)):
        kind = _AttributeKind(*args)
        yield str(kind), kind
        yielded += 1

    # Raise on zero match
    if not yielded:
        msg = f"No factory attribute matches {filters}"
        raise ValueError(msg)

    return yielded


def attributes(*filters: str) -> Generator[str]:
    """Retrieve attributes from `attributes_kinds(*filters)`."""
    yield from (attribute for attribute, _ in attributes_kinds(*filters))


def kinds(*filters: str) -> Generator[_AttributeKind]:
    """Retrieve kinds from `attributes_kinds(*filters)`."""
    yield from (kind for _, kind in attributes_kinds(*filters))


def __DescriptorFactories() -> dict[tuple[bool, ...], type]:
    """All 8 (non)descriptor factories."""

    class DescriptorError(AttributeError):
        __module__ = "builtins"
        __qualname__ = "DescriptorError"

    def desc(obj) -> str:
        """To make error message comparable, no address."""
        if inspect.isclass(obj):
            return f"<class {obj.__name__}>"
        return f"<instance of {type(obj).__name__}>"

    def get_method(self, obj, type: type) -> None:  # noqa: A002
        msg = f"Used __get__(self: {desc(self)}, obj: {desc(obj)}, type: {desc(type)})"
        raise DescriptorError(msg)

    def set_method(self, obj, val) -> None:
        msg = f"Used __set__(self: {desc(self)}, obj: {desc(obj)}, value: {desc(val)})"
        raise DescriptorError(msg)

    def delete_method(self, obj) -> None:
        msg = f"Used __delete__(self: {desc(self)}, obj: {desc(obj)})"
        raise DescriptorError(msg)

    desc_methods = (get_method, set_method, delete_method)
    desc_attrs = ("__get__", "__set__", "__delete__")
    desc_titles = tuple(attr[2:-2].title() for attr in desc_attrs)
    out = {}
    for mask in product([True, False], repeat=3):
        attrs = tuple(compress(desc_attrs, mask))
        methods = tuple(compress(desc_methods, mask))
        titles = tuple(compress(desc_titles, mask))
        namespace = dict(zip(attrs, methods, strict=False))
        name = f"{''.join(titles) or 'Non'}DescriptorFactory"
        out[mask] = type(name, (), namespace)

    return out


_DescriptorFactories = MappingProxyType(__DescriptorFactories())


@pytest.fixture(scope="session")
def make() -> Callable:  # noqa: C901  # Prefer complexity over modularization here
    """Generate target classes or instances dynamically.

    Factory for paramclass or vanilla class, or their instances.

    Arguments:
        targets (str): Coma-separated list of targets amongst `{"Param",
            "param", "param_fill", "Vanilla", "vanilla",
            "vanilla_fill"}`. The first and second half respectively
            refer to paramclass and vanilla objects. Capitalized targets
            are classes, non-capitalized are instances of these.
            Trailing `"_fill"` denotes instances with filled dict, using
            keys corresponding to `attr_kinds` and `fill` value. Targets
            can be repeated multiple times.
        *attr_kinds (_AttributeKind): The kind of attributes to be added
            to the dynamically created classes' namespace. Protection is
            ignored for vanilla classes.
        fill (object): Value to fill targets when requested. Defaults to
            `None`.

    Returns:
        out (object | list[object]): One objet or a list of objects
            corresponding to the requested `targets`. In the same order.
            Requesting a target multiple times provides different
            objects for instances, but the same class for classes.

    """
    supported_targets_cls = frozenset({"Param", "Vanilla"})
    supported_targets = frozenset({
        "Param",
        "param",
        "param_fill",
        "Vanilla",
        "vanilla",
        "vanilla_fill",
    })

    def _make(  # noqa: C901  # Prefer complexity over modularization here
        targets: str,
        *attr_kinds: _AttributeKind,
        fill: object = None,
    ) -> object | list[object]:
        targets_tpl = tuple(target.strip() for target in targets.split(","))
        assert supported_targets.issuperset(targets_tpl), f"Wrong targets {targets_tpl}"
        targets_cls = {target.removesuffix("_fill").title() for target in targets_tpl}

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
                val = _DescriptorFactories[attr_kind.has_methods]()
                is_protected = attr_kind.protected
                vals[attr] = val, is_protected

        # Dynamiclly create needed classes
        classes = {}
        for target_cls in targets_cls:
            paramcls = target_cls == "Param"
            namespace: dict[str, object] = {"__module__": __name__}
            for attr, (val, is_protected) in vals.items():
                namespace[attr] = protected(val) if paramcls and is_protected else val

            if slots:
                namespace["__slots__"] = slots + ([] if paramcls else ["__dict__"])

            if annotations:
                namespace["__annotations__"] = annotations

            mcs = type(ParamClass) if paramcls else type
            name = f"{'Param' if paramcls else 'Vanilla'}Test"
            bases = (ParamClass,) if paramcls else ()
            classes[target_cls] = mcs(name, bases, namespace)

        # Create and return requested classes / instances
        out = []
        for target in targets_tpl:
            # `target` is a class
            if target in supported_targets_cls:
                out.append(classes[target])
                continue

            # `target` is an instance
            target_base, _fill, _ = target.partition("_fill")
            instance = classes[target_base.title()]()

            # `target` requires filling `vars(instance)`
            if _fill:
                for attr in attrs:
                    vars(instance)[attr] = fill

            out.append(instance)

        return out if len(out) > 1 else out[0]

    return _make


def parametrize_attr_kind(*filters: str) -> pytest.MarkDecorator:
    """Parametrize attr_kind specifically."""

    def fn(attr_or_kind) -> str:
        return attr_or_kind if isinstance(attr_or_kind, str) else ""

    return pytest.mark.parametrize(("attr", "kind"), attributes_kinds(*filters), ids=fn)
