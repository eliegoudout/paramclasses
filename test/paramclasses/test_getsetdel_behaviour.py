"""Check correct getattr/setattr/delattr behaviour.

This is done according to the following expectations, in three sections:
    - Protected behaviour
    - Vanilla behaviour
    - Bypass Descriptors behaviour

          ╭──────────────────────────────────────┬─────────────────────────────────────╮
   IMPLEM │               Parameters             │             Non-Parameters          │
 EXPECTED ├───────────────────┬──────────────────┤──────────────────┬──────────────────┤
BEHAVIOUR │     Protected     │   Unprotected    │    Protected     │   Unprotected    │
╭─────────┼───────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ getattr │Bypass Descriptors*│Bypass Descriptors│     Vanilla*     │     Vanilla      │
├─────────┼───────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ setattr │  ProtectedError   │Bypass Descriptors│  ProtectedError  │     Vanilla      │
├─────────┼───────────────────┼──────────────────┼──────────────────┼──────────────────┤
│ delattr │  ProtectedError   │Bypass Descriptors│  ProtectedError  │     Vanilla      │
╰─────────┴───────────────────┴──────────────────┴──────────────────┴──────────────────╯

Vanilla means "same outputs or same error typeS and messageS as vanilla classes".
The * means that `get` should ignore and remove any `vars(instance)` entry. We don't
    check for the warning.

The difficulty lies in generating every possible attribute scenario, dealing with
multiple degree of freedom:
- operations at class or instance level,
- class values with or without get/set/delete,
- missing value parameter,
- slot members,
- instances with or without filled dict.

Inheritance is not tested here.
"""

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
    regex = None
    for obj in make("Param, param, param_fill", kind):
        regex = regex or f"^'{attr}' is protected by '{obj.__name__}'"
        assert_set_del_is_protected(obj, attr, regex)


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
    # Treat "get slot" separately because the member descriptor is
    # created at class instanciation and is thus distinct.
    if ops[0] == "get" and kind.slot:
        return

    assert_same_behaviour(*make("Param, Vanilla", kind), attr=attr, ops=ops)


@parametrize_attr_kind("slot")
def test_behaviour_get_slot_class_level(attr, kind, make):
    """Always bypasses descriptors.

    Special case, soft check slot member descriptor.
    """
    Param, Vanilla = make("Param, Vanilla", kind)
    param_membr = getattr(Param, attr)
    vanilla_membr = getattr(Vanilla, attr)

    assert type(param_membr) is type(vanilla_membr)
    for membr, cls in zip((param_membr, vanilla_membr), (Param, Vanilla), strict=True):
        assert repr(membr) == f"<member '{attr}' of '{cls.__name__}' objects>"


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
    objs = make("param, vanilla", kind)
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
    objs_fill = make("param_fill, vanilla_fill", kind, fill=null)
    assert_same_behaviour(*objs_fill, attr=attr, ops=ops)


@parametrize_attr_kind("protected", "nonparameter")
def test_behaviour_get_protected_nonparameter(
    attr,
    kind,
    make,
    null,
    assert_same_behaviour,
):
    """Test vanilla behaviour except param_fill <-> param."""
    Param, param, param_fill, Vanilla, vanilla = make(
        "Param, param, param_fill, Vanilla, vanilla",
        kind,
        fill=null,
    )
    assert_same_behaviour(Param, Vanilla, attr=attr, ops="get")

    # param_fill: remove from object dict
    assert attr in vars(param_fill)
    assert_same_behaviour(param, param_fill, vanilla, attr=attr, ops="get")
    assert attr not in vars(param_fill)


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
    Param, param, param_fill = make("Param, param, param_fill", kind, fill=null)
    cls_var = vars(Param)[attr]

    # Param, param
    for obj in (Param, param):
        assert getattr(obj, attr) is cls_var

    # param_fill: remove from object dict if protected
    assert vars(param_fill)[attr] is null
    if kind.protected:
        assert getattr(param_fill, attr) is cls_var
        assert attr not in vars(param_fill)
    else:
        assert getattr(param_fill, attr) is null


@parametrize_attr_kind("parameter", "missing")
def test_behaviour_get_parameter_missing(attr, kind, make, null):
    """Always bypasses descriptors."""
    Param, param, param_fill = make("Param, param, param_fill", kind, fill=null)

    # Param
    regex = f"^type object '{Param.__name__}' has no attribute '{attr}'$"
    with pytest.raises(AttributeError, match=regex):
        getattr(Param, attr)

    # param
    regex = f"^'{Param.__name__}' object has no attribute '{attr}'$"
    with pytest.raises(AttributeError, match=regex):
        getattr(param, attr)

    # param_fill
    assert getattr(param_fill, attr) is null


@parametrize_attr_kind("unprotected", "parameter")
def test_behaviour_set_unprotected_parameter(attr, kind, make, null):
    """Always bypasses descriptors."""
    for obj in make("Param, param, param_fill", kind):
        assert vars(obj).get(attr, None) is not null
        setattr(obj, attr, null)
        assert vars(obj)[attr] is null


@parametrize_attr_kind("unprotected", "parameter")
def test_delete_behaviour_unprotected_parameter_class_level(attr, kind, make):
    """Always bypasses descriptors."""
    Param = make("Param", kind)

    # Manually handle special cases
    if attr not in vars(Param):
        assert attr == "unprotected_parameter_missing"
        return

    delattr(Param, attr)
    assert attr not in vars(Param)


@parametrize_attr_kind("unprotected", "parameter")
def test_delete_behaviour_unprotected_parameter_instance_level(attr, kind, make):
    """Always bypasses descriptors."""
    param, param_fill = make("param, param_fill", kind)

    # Empty instance
    with pytest.raises(AttributeError, match=f"^{attr}$"):
        delattr(param, attr)

    # Filled instance
    delattr(param_fill, attr)
    assert attr not in vars(param_fill)


# ======================================================================================
