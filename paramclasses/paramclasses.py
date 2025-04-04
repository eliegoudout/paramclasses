"""Implements `ParamClass`."""

__all__ = [
    "IMPL",
    "MISSING",
    "ParamClass",
    "ProtectedError",
    "RawParamClass",
    "isparamclass",
    "protected",
]

import sys
from abc import ABCMeta
from dataclasses import dataclass
from reprlib import recursive_repr
from types import MappingProxyType
from typing import TYPE_CHECKING, NamedTuple, cast, final
from warnings import warn

if TYPE_CHECKING:  # pragma: no cover
    from collections.abc import Callable


@dataclass(frozen=True)
class _MissingType:
    repr: str = "..."

    def __repr__(self) -> str:
        return self.repr


IMPL = "__paramclass_impl_"  # would-be-mangled on purpose
MISSING = _MissingType("?")  # Sentinel object better representing missing value


@dataclass(frozen=True)
class _ProtectedType:
    val: object

    # See github.com/eliegoudout/paramclasses/issues/3
    def __new__(cls, *_: object, **__: object):  # noqa: ANN204 (no `Self` in 3.10)
        return super().__new__(cls)


def protected(val: object) -> _ProtectedType:
    """Make read-only with this decorator, including in subclasses.

    Should always be the outtermost decorator. Protection doesn't apply
    to annotations.
    """
    return _ProtectedType(val)


def _unprotect(val: object) -> tuple[object, bool]:
    """Unwrap protected value, recursively if needed."""
    if isinstance(val, _ProtectedType):
        return _unprotect(val.val)[0], True
    return val, False


class ProtectedError(AttributeError):
    """Don't assign or delete protected attributes."""

    __module__ = "builtins"


@final
class _MetaFrozen(type):
    """Make `_MetaParamClass` frozen with this metaclass.

    Legacy from when `_MetaParamClass` had exposed attributes. Keep it
    for now as it adds a small extra robustness, and prevents natural
    `_MetaParamClass` subclassing.
    """

    def __new__(mcs, name: str, bases: tuple, namespace: dict[str, object]) -> type:
        if not (len(bases) == 1 and name == "_MetaParamClass" and bases[0] is ABCMeta):
            msg = "`_MetaParamClass' cannot be subclassed"
            raise ProtectedError(msg)
        return type.__new__(mcs, name, bases, namespace)

    def __setattr__(*_: object, **__: object) -> None:
        msg = "`_MetaParamClass' attributes are frozen"
        raise ProtectedError(msg)

    def __delattr__(*_: object, **__: object) -> None:
        msg = "`_MetaParamClass' attributes are frozen"
        raise ProtectedError(msg)


def _assert_unprotected(attr: str, protected: dict[str, type | None]) -> None:
    """Assert that `attr not in protected`."""
    if attr in protected:
        owner = protected[attr]
        msg = f"'{attr}' is protected by {_repr_owner(owner)}"
        raise ProtectedError(msg)


def _assert_valid_param(attr: str) -> None:
    """Assert that `attr` is authorized as parameter name."""
    if attr.startswith("__") and attr.endswith("__"):
        msg = f"Dunder parameters ('{attr}') are forbidden"
        raise AttributeError(msg)


def _dont_assign_missing(attr: str, val: object) -> None:
    """Forbid assigning the special 'missing value'."""
    if val is MISSING:
        msg = f"Assigning special missing value (attribute '{attr}') is forbidden"
        raise ValueError(msg)


def _repr_owner(*bases: type | None) -> str:
    """Repr of bases for protection conflic error message."""

    def _mono_repr(cls: type | None) -> str:
        if cls is None:
            return "<paramclasses root protection>"
        return f"'{cls.__name__}'"

    return ", ".join(sorted(map(_mono_repr, bases)))


def _get_namespace_annotations(
    namespace: dict[str, object],
) -> dict[str, object]:  # pragma: no cover
    """Get annotations from a namespace dict, 3.14 compatible."""
    __annotations__ = cast("dict[str, object]", namespace.get("__annotations__", {}))

    if sys.version_info < (3, 14):
        return __annotations__

    # For python >= 3.14
    # https://discuss.python.org/t/python-3-14-metaclasses-interact-with-annotations-from-namespace-dict/87010
    from annotationlib import Format  # type: ignore[import-not-found]

    ann = cast("Callable[[int], dict[str, object]]", namespace.get("__annotate__"))
    return __annotations__ if ann is None else ann(Format.VALUE)  # soon FORWARDREF(?)


def _update_while_checking_consistency(orig: dict, update: MappingProxyType) -> None:
    """Update `orig` with `update`, verifying consistent shared keys.

    Use only for protection checking.
    """
    for attr, val in update.items():
        if attr not in orig:
            orig[attr] = val
            continue
        if (previous := orig[attr]) is not val:
            msg = f"'{attr}' protection conflict: {_repr_owner(val, previous)}"
            raise ProtectedError(msg)


@final
class _MetaParamClass(ABCMeta, metaclass=_MetaFrozen):
    """Specifically implemented as `RawParamClass`'s metaclass.

    Implements class-level protection behaviour and parameters
    identification, with default values. Also subclasses `ABCMeta` to
    be compatible with its functionality.
    """

    def __new__(mcs, name: str, bases: tuple, namespace: dict[str, object]) -> type:
        """Most of `_MetaParamClass` logic.

        It essentially does the following.
            1. Retrieves parameters and protected attributes from bases.
            2. Inspects `namespace` and its `__annotations__` to infer
                new parameters and newly protected attributes.
            3. Store those in `IMPL` class attribute.
        """

        class Impl(NamedTuple):
            """Details held for paramclass machinery."""

            default: MappingProxyType = MappingProxyType({})
            protected: MappingProxyType = MappingProxyType({})

        # # Bases: default, protected
        default: dict = {}
        protected_special = [IMPL, "__dict__"]
        protected = dict.fromkeys(protected_special)
        for base in bases[::-1]:
            default_base, protected_base = getattr(base, IMPL, Impl())
            default |= default_base
            # Previous bases protected coherence
            _update_while_checking_consistency(protected, protected_base)
            for attr in vars(base):
                if attr in protected_special:
                    continue
                if attr in protected and (owner := protected[attr]) is not base:
                    msg = f"'{attr}' protection conflict: {_repr_owner(base, owner)}"
                    raise ProtectedError(msg)

        # # Namespace: handle slots, protect, store parameters
        # Cannot slot protected
        slots = namespace.get("__slots__", ())
        slots = (slots,) if isinstance(slots, str) else cast("tuple", slots)
        protect_then_slot = set(protected).intersection(slots)
        if protect_then_slot:
            msg = "Cannot slot the following protected attributes: " + ", ".join(
                f"'{attr}' (from {_repr_owner(protected[attr])})"
                for attr in sorted(protect_then_slot)  # sort for pytest output
            )
            raise ProtectedError(msg)

        # Unwrap decorator and identify new protected
        protected_new = []
        namespace_final = {}
        for attr, val_potentially_protected in namespace.items():
            _assert_unprotected(attr, protected)
            val, was_protected = _unprotect(val_potentially_protected)
            _dont_assign_missing(attr, val)
            namespace_final[attr] = val
            if was_protected:
                protected_new.append(attr)

        # Store new parameters and default
        annotations = _get_namespace_annotations(namespace)
        for attr in annotations:
            _assert_unprotected(attr, protected)
            _assert_valid_param(attr)
            default[attr] = namespace_final.get(attr, MISSING)

        # Update namespace
        namespace_final[IMPL] = Impl(*map(MappingProxyType, [default, protected]))
        cls = ABCMeta.__new__(mcs, name, bases, namespace_final)

        # Declare `cls` as owner for newly protected attributes
        for attr in protected_new:
            protected[attr] = cls

        return cls

    def __getattribute__(cls, attr: str) -> object:
        """Handle descriptor parameters."""
        vars_cls = ABCMeta.__getattribute__(cls, "__dict__")

        # Special case `__dict__`
        if attr == "__dict__":
            return vars_cls

        # Not a parameter, normal look-up
        if attr not in vars_cls[IMPL].default:
            return ABCMeta.__getattribute__(cls, attr)

        # Parameters bypass descriptor
        if attr in vars_cls:
            return vars_cls[attr]

        for vars_base in map(vars, cls.__mro__[1:]):
            if attr in vars_base:
                return vars_base[attr]

        # Not found
        msg = f"type object '{cls.__name__}' has no attribute '{attr}'"
        raise AttributeError(msg)

    def __setattr__(cls, attr: str, val_potentially_protected: object) -> None:
        """Handle protection, missing value."""
        _assert_unprotected(attr, getattr(cls, IMPL).protected)
        val, was_protected = _unprotect(val_potentially_protected)
        _dont_assign_missing(attr, val)
        if was_protected:
            warn(
                f"Cannot protect attribute '{attr}' after class creation. Ignored",
                stacklevel=2,
            )
        return ABCMeta.__setattr__(cls, attr, val)

    def __delattr__(cls, attr: str) -> None:
        """Handle protection."""
        _assert_unprotected(attr, getattr(cls, IMPL).protected)
        return ABCMeta.__delattr__(cls, attr)


class RawParamClass(metaclass=_MetaParamClass):
    """`ParamClass` without `set_params`, `params`, `missing_params`."""

    # ========================= Subclasses may override these ==========================
    #
    def _on_param_will_be_set(self, attr: str, future_val: object) -> None:
        """Call before parameter assignment."""

    def __post_init__(self, *args: object, **kwargs: object) -> None:
        """Init logic, after parameters assignment."""

    @recursive_repr()
    def __repr__(self) -> str:
        """Show all non-default or missing, e.g. `A(x=1, z=?)`."""
        params_str = ", ".join(
            f"{attr}={getattr(self, attr, MISSING)!r}"
            for attr, val_default in getattr(self, IMPL).default.items()
            if (val_default is MISSING) or (getattr(self, attr, MISSING) != val_default)
        )
        return f"{type(self).__name__}({params_str})"

    # ==================================================================================

    @protected  # type: ignore[misc]  # mypy is fooled
    def __init__(
        self,
        args: list | None = None,
        kwargs: dict | None = None,
        /,
        **param_values: object,
    ) -> None:
        """Set parameters and call `__post_init__`.

        Arguments:
            args (list | None): If not `None`, unpacked as positional
                arguments for `__post_init__`.
            kwargs (dict | None): If not `None`, unpacked as keyword
                arguments for `__post_init__`.
            **param_values (object): Assigned parameter values at
                instantiation.

        """
        # Set params: KEEP UP-TO-DATE with `ParamClass.set_params`!
        wrong = set(param_values) - set(getattr(self, IMPL).default)
        if wrong:
            msg = f"Invalid parameters: {wrong}. Operation cancelled"
            raise AttributeError(msg)

        for attr, val in param_values.items():
            setattr(self, attr, val)

        # Call `__post_init__`
        if args is None:
            args = []
        if kwargs is None:
            kwargs = {}
        self.__post_init__(*args, **kwargs)

    @protected
    def __getattribute__(self, attr: str) -> object:  # type: ignore[override]  # mypy is fooled
        """Handle descriptor parameters."""
        cls = type(self)
        vars_self = object.__getattribute__(self, "__dict__")

        # Special case `__dict__`, which is protected
        if attr == "__dict__":  # To save a few statements
            if attr in vars_self:
                del vars_self[attr]
            return vars_self

        # Remove attr from `vars(self)` if protected -- should not be there!
        if attr in vars_self and attr in getattr(cls, IMPL).protected:
            del vars_self[attr]

        # Not a parameter, normal look-up
        if attr not in getattr(cls, IMPL).default:
            return object.__getattribute__(self, attr)

        # Parameters bypass descriptor
        # https://docs.python.org/3/howto/descriptor.html#invocation-from-an-instance
        if attr in vars_self:
            return vars_self[attr]

        for base in cls.__mro__:
            if attr in vars(base):
                return vars(base)[attr]

        # Not found
        msg = f"'{cls.__name__}' object has no attribute '{attr}'"
        raise AttributeError(msg)

    @protected
    def __setattr__(self, attr: str, val_potentially_protected: object) -> None:  # type: ignore[override]  # mypy is fooled
        """Handle protection, missing value, descriptor parameters.

        Also call the `_on_param_will_be_set()` callback when `attr` is
        a parameter key.
        """
        # Handle protection, missing value
        _assert_unprotected(attr, getattr(self, IMPL).protected)
        val, was_protected = _unprotect(val_potentially_protected)
        _dont_assign_missing(attr, val)
        if was_protected:
            warn(
                f"Cannot protect attribute '{attr}' on instance assignment. Ignored",
                stacklevel=2,
            )

        # Handle callback, descriptor parameters
        if attr in getattr(self, IMPL).default:
            self._on_param_will_be_set(attr, val)
            vars(self)[attr] = val
        else:
            object.__setattr__(self, attr, val)

    @protected
    def __delattr__(self, attr: str) -> None:  # type: ignore[override]  # mypy is fooled
        """Handle protection, descriptor parameters."""
        # Handle protection
        _assert_unprotected(attr, getattr(self, IMPL).protected)

        # Handle descriptor parameters
        if attr in getattr(self, IMPL).default:
            if attr not in (vars_self := vars(self)):
                raise AttributeError(attr)
            del vars_self[attr]
        else:
            object.__delattr__(self, attr)


class ParamClass(RawParamClass):
    """Parameter-holding class with robust subclassing protection.

    This is the base "paramclass". To define a "paramclass", simply
    subclass `ParamClass` or any of its subclasses, inheriting from its
    functionalities. When defining a "paramclass", use the `@protected`
    decorator to disable further setting and deleting on target
    attributes. The protection affects both the defined class and its
    future subclasses, as well as any of their instances. Also,
    `ParamClass` inherits from `ABC` functionalities

    A "parameter" is any attribute that was given an annotation during
    class definition, similar to `@dataclass`. For "parameters",
    get/set/delete interactions bypass descriptors mechanisms. For
    example, if `A.x` is a descriptor, `A().x is A.x`. This is similar
    to the behaviour of dataclasses and is extended to set/delete.

    Subclasses may wish to implement a callback on parameter-value
    modification with `_on_param_will_be_set()`, or to further customize
    instanciation (which is similar to keywords-only dataclasses') with
    `__post_init__()`.

    Unprotected methods:
        _on_param_will_be_set: Call before parameter assignment.
        __post_init__: Init logic, after parameters assignment.
        __repr__: Show all non-default or missing, e.g. `A(x=1, y=?)`.

    Protected methods:
        set_params: Set multiple parameter values at once via keywords.
        __init__: Set parameters and call `__post_init__`.
        __getattribute__: Handle descriptor parameters.
        __setattr__: Handle protection, missing value, descriptor
            parameters.
        __delattr__: Handle protection, descriptor parameters.

    Protected properties:
        params (dict[str, object]): Copy of the current parameter dict
            for instance.
        missing_params (tuple[str]): Parameters without value.
    """

    @protected
    # KEEP UP-TO-DATE with first part of `RawParamClass.__init__`!
    def set_params(self, **param_values: object) -> None:
        """Set multiple parameter values at once via keywords."""
        wrong = set(param_values) - set(getattr(self, IMPL).default)
        if wrong:
            msg = f"Invalid parameters: {wrong}. Operation cancelled"
            raise AttributeError(msg)

        for attr, val in param_values.items():
            setattr(self, attr, val)

    @protected  # type: ignore[prop-decorator]  # mypy is fooled
    @property
    def params(self) -> dict[str, object]:
        """Copy of the current parameter dict for instance."""
        return {
            attr: getattr(self, attr, MISSING) for attr in getattr(self, IMPL).default
        }

    @protected  # type: ignore[prop-decorator]  # mypy is fooled
    @property
    def missing_params(self) -> tuple[str]:
        """Parameters without value."""
        return tuple(
            attr
            for attr in getattr(self, IMPL).default
            if not hasattr(self, attr) or getattr(self, attr) is MISSING
        )


def isparamclass(cls: type, *, raw: bool = False) -> bool:
    """Check if `cls` is a (raw)paramclass.

    If `raw`, subclassing `RawParamClass` is enough to return `True`.
    """
    # Should have same metaclass
    if type(cls) is not type(RawParamClass):
        return False

    # Should inherit from `(Raw)ParamClass`
    base_paramclass = RawParamClass if raw else ParamClass
    return any(base is base_paramclass for base in cls.__mro__)
