"""Check correct getattr/setattr/delattr behaviour.

This is done according to the following expectations, in three sections:
    - Protected behaviour
    - Vanilla behaviour
    - Bypass Descriptors behaviour

          ╭──────────────────────────────────────┬─────────────────────────────────────╮
   IMPLEM │               Parameters             │             Non-Parameters          │
 EXPECTED ├───────────────────┬──────────────────┼──────────────────┬──────────────────┤
BEHAVIOUR │     Protected     │   Unprotected    │    Protected     │   Unprotected    │
╭─────────┼───────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ getattr │Bypass Descriptors*│Bypass Descriptors│     Vanilla*     │     Vanilla      │
├─────────┼───────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ setattr │  ProtectedError   │Bypass Descriptors│  ProtectedError  │     Vanilla      │
├─────────┼───────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ delattr │  ProtectedError   │Bypass Descriptors│  ProtectedError  │     Vanilla      │
╰─────────┴───────────────────┴──────────────────┴──────────────────┴──────────────────╯

Vanilla means "same outputs or same error typeS and messageS as vanilla
classes".
The * means that `get` should ignore and remove any `vars(instance)`
entry. We don't check for the warning.

The difficulty lies in generating every possible attribute scenario,
dealing with multiple degree of freedom:
- operations at class or instance level,
- class values with or without get/set/delete,
- missing value parameter,
- slot members,
- instances with or without filled dict.

Only simple inheritance is tested here.
"""

import re
import sys

import pytest

from .conftest import parametrize_attr_kind


# ============================== [1] PROTECTED BEHAVIOUR ===============================
@parametrize_attr_kind("protected")
def test_behaviour_set_del_protected_class_and_instances(
    attr,
    kind,
    make,
    assert_set_del_is_protected,
):
    """Test protection."""
    objs = make(
        "Param, param, param_fill, ParamChild, paramchild, paramchild_fill",
        kind,
    )
    msg = f"{attr!r} is protected by {objs[0].__name__!r}"
    for obj in objs:
        assert_set_del_is_protected(obj, attr, f"^{re.escape(msg)}$")


# ======================================================================================

# =============================== [2] VANILLA BEHAVIOUR ================================
all_ops = (
    ["get"],
    ["set", "get"],
    ["delete", "get"],
)


@pytest.mark.parametrize("ops", all_ops, ids=" > ".join)
@parametrize_attr_kind("unprotected", "nonparameter")
def test_behaviour_get_set_delete_unprotected_nonparameter_class_level(
    ops,
    attr,
    kind,
    make,
    assert_same_behaviour,
):
    """Test vanilla behaviour class level."""
    # Treat cases where "get" should return a slot separately, because
    # the member descriptor is created at class instanciation and is
    # thusnot the same object between classes.
    if kind.slot and ops == ["get"]:
        return
    assert_same_behaviour(*make("Param, Vanilla", kind), attr=attr, ops=ops)

    if kind.slot and ops == ["delete", "get"]:
        return
    assert_same_behaviour(*make("ParamChild, VanillaChild", kind), attr=attr, ops=ops)


@parametrize_attr_kind("slot")
def test_behaviour_get_slot_class_level(attr, kind, make):
    """Always bypasses descriptors.

    Special case, soft check slot member descriptor.
    """
    classes = make("Param, ParamChild, Vanilla, VanillaChild", kind)
    members = tuple(getattr(cls, attr) for cls in classes)

    class ClassWithSlot:
        __slots__ = ("slot",)

    for cls, member in zip(classes, members, strict=True):
        assert type(member) is type(ClassWithSlot.slot)
        owner_name = cls.__name__.replace("Child", "")
        assert repr(member) == f"<member '{attr}' of '{owner_name}' objects>"


@pytest.mark.parametrize("ops", all_ops, ids=" > ".join)
@parametrize_attr_kind("unprotected", "nonparameter")
def test_behaviour_get_set_delete_unprotected_nonparameter_instance_empty(
    ops,
    attr,
    kind,
    make,
    assert_same_behaviour,
):
    """Test vanilla behaviour."""
    objs = make("param, paramchild, vanilla, vanillachild", kind)
    assert_same_behaviour(*objs, attr=attr, ops=ops)


@pytest.mark.parametrize("ops", all_ops, ids=" > ".join)
@parametrize_attr_kind("unprotected", "nonparameter")
def test_behaviour_get_set_delete_unprotected_nonparameter_instance_filled(
    ops,
    attr,
    kind,
    make,
    null,
    assert_same_behaviour,
):
    """Test vanilla behaviour."""
    objs_fill = make(
        "param_fill, paramchild_fill, vanilla_fill, vanillachild_fill",
        kind,
        fill=null,
    )
    assert_same_behaviour(*objs_fill, attr=attr, ops=ops)


@parametrize_attr_kind("protected", "nonparameter")
def test_behaviour_get_protected_nonparameter_class_level(
    attr,
    kind,
    make,
    assert_same_behaviour,
):
    """Test vanilla behaviour except param_fill <-> param."""
    classes = make("Param, ParamChild, Vanilla, VanillaChild", kind)
    assert_same_behaviour(*classes, attr=attr, ops="get")


@parametrize_attr_kind("protected", "nonparameter")
def test_behaviour_get_protected_nonparameter_instance_level(
    attr,
    kind,
    make,
    null,
    assert_same_behaviour,
):
    """Test vanilla behaviour except param_fill <-> param."""
    targets = [
        "param",
        "paramchild",
        "param_fill",
        "paramchild_fill",
        "vanilla",
        "vanillachild",
    ]
    objs = make(", ".join(targets), kind, fill=null)
    are_filled = [target.endswith("_fill") for target in targets]

    # `param_fill` and `paramchild_fill`: should remove from object dict
    for obj, is_filled in zip(objs, are_filled, strict=True):
        if is_filled:
            assert attr in vars(obj)

    assert_same_behaviour(*objs, attr=attr, ops="get")

    for obj in objs:
        assert attr not in vars(obj)


def test_behaviour_get_special_case_instance_filled_attr_dict(make, null):
    """For protected, direct `vars(self)` assignments removed on get."""
    param = make("param")
    attr = "__dict__"

    before_dict_assignment = getattr(param, attr, null)
    vars(param)[attr] = None
    after_dict_assignment = getattr(param, attr, null)
    # Get was not affected by `__dict__` addition and removed it
    assert after_dict_assignment is before_dict_assignment
    assert attr not in vars(param)


# ======================================================================================


# =============================== [3] BYPASS DESCRIPTORS ===============================
@parametrize_attr_kind("parameter", "nonmissing")
def test_behaviour_get_parameter_nonmissing(attr, kind, make, null):
    """Always bypasses descriptors."""
    Param, ParamChild, param, paramchild, param_fill, paramchild_fill = make(
        "Param, ParamChild, param, paramchild, param_fill, paramchild_fill",
        kind,
        fill=null,
    )
    cls_var = vars(Param)[attr]

    # Nonfilled
    for obj in (Param, ParamChild, param, paramchild):
        assert getattr(obj, attr) is cls_var

    # Filled: remove from object dict if protected
    for obj_fill in (param_fill, paramchild_fill):
        assert vars(obj_fill)[attr] is null
        if kind.protected:
            assert getattr(obj_fill, attr) is cls_var
            assert attr not in vars(obj_fill)
        else:
            assert getattr(obj_fill, attr) is null


@parametrize_attr_kind("parameter", "missing")
def test_behaviour_get_parameter_missing(attr, kind, make, null):
    """Always bypasses descriptors."""
    Param, ParamChild, param, paramchild, param_fill, paramchild_fill = make(
        "Param, ParamChild, param, paramchild, param_fill, paramchild_fill",
        kind,
        fill=null,
    )

    # Class
    for cls in (Param, ParamChild):
        msg = f"type object {cls.__name__!r} has no attribute {attr!r}"
        with pytest.raises(AttributeError, match=f"^{re.escape(msg)}$"):
            getattr(cls, attr)

    # Empty instance
    for obj in (param, paramchild):
        msg = f"{type(obj).__name__!r} object has no attribute {attr!r}"
        with pytest.raises(AttributeError, match=f"^{re.escape(msg)}$"):
            getattr(obj, attr)

    # Filled instance
    for obj_fill in (param_fill, paramchild_fill):
        assert getattr(obj_fill, attr) is null


@parametrize_attr_kind("unprotected", "parameter")
def test_behaviour_set_unprotected_parameter(attr, kind, make, null):
    """Always bypasses descriptors."""
    objs = make(
        "Param, ParamChild, param, paramchild, param_fill, paramchild_fill",
        kind,
    )

    for obj in objs:
        assert vars(obj).get(attr, None) is not null
        setattr(obj, attr, null)
        assert vars(obj)[attr] is null


@parametrize_attr_kind("unprotected", "parameter")
def test_delete_behaviour_unprotected_parameter_class_level(attr, kind, make):
    """Always bypasses descriptors."""
    for cls in make("Param, ParamChild", kind):
        if attr in vars(cls):
            delattr(cls, attr)
            assert attr not in vars(cls)
            continue

        old = sys.version_info < (3, 11)
        prefix = "" if old else f"type object '{cls.__name__}' has no attribute '"
        suffix = "" if old else "'"
        msg = f"{prefix}{attr}{suffix}"

        with pytest.raises(AttributeError, match=f"^{re.escape(msg)}$"):
            delattr(cls, attr)


@parametrize_attr_kind("unprotected", "parameter")
def test_delete_behaviour_unprotected_parameter_instance_level(attr, kind, make):
    """Always bypasses descriptors."""
    param, param_fill = make("param, param_fill", kind)

    # Empty instance
    for obj in make("param, paramchild", kind):
        with pytest.raises(AttributeError, match=f"^{attr}$"):
            delattr(obj, attr)

    # Filled instance
    for obj in make("param_fill, paramchild_fill", kind):
        delattr(obj, attr)
        assert attr not in vars(obj)


# ======================================================================================
