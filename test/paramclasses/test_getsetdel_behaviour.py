"""Check correct getattr/setattr/delattr behaviour.

This is done according to the following expectations, in three sections:
    - Protected behaviour
    - Vanilla behaviour
    - Bypass Descriptors behaviour

          ╔══════════════════════════════════════╦═════════════════════════════════════╗
          ║               Parameters             ║             Non-Parameters          ║
 EXPECTED ╠═══════════════════╤══════════════════╬══════════════════╤══════════════════╣
BEHAVIOUR ║     Protected     │   Unprotected    ║    Protected     │   Unprotected    ║
╔═════════╬═══════════════════╪══════════════════╬══════════════════╪══════════════════╢
║ getattr ║Bypass Descriptors*│Bypass Descriptors║     Vanilla*     │     Vanilla      ║
╟─────────╫───────────────────│──────────────────╫──────────────────│──────────────────╢
║ setattr ║  ProtectedError   │Bypass Descriptors║  ProtectedError  │     Vanilla      ║
╟─────────╫───────────────────│──────────────────╫──────────────────│──────────────────╢
║ delattr ║  ProtectedError   │Bypass Descriptors║  ProtectedError  │     Vanilla      ║
╚═════════╩═══════════════════╧══════════════════╩══════════════════╧══════════════════╝
Vanilla means "same outputs or same error type and message than vanilla class".
The * means that `get` should ignore and remove any `vars(instance)` entry. We don't
    check for the warning.

The difficulty lies in geenrating every possible attribute scenario, dealing with
multiple degree of freedom:
- operations at class or instance level,
- class values with or without get/set/delete,
- missing value parameters,
- dict-managed ot slot-managed classes (+ complex inheritance possibilities),
- for dict-managed, instances with or without filled dict

For now: No inheritance and dict handled class (`ParamTest` and forced `VanillaTest`).
"""

from itertools import chain, product

import pytest


# ============================== [1] PROTECTED BEHAVIOUR ===============================
def test_behaviour_set_del_protected_class_and_instances(
    ParamTest,
    assert_set_del_is_protected,
    paramtest_attrs,
    obj,
):
    """Test protection."""
    obj_empty = obj("Param")
    obj_full = obj("Param", fill_dict=True)
    for attr in paramtest_attrs("protected"):
        regex = f"^Attribute '{attr}' is protected$"
        assert_set_del_is_protected(obj_empty, attr, regex)
        assert_set_del_is_protected(obj_full, attr, regex)
        assert_set_del_is_protected(ParamTest, attr, regex)


# ======================================================================================

# =============================== [2] VANILLA BEHAVIOUR ================================
all_ops = (
    ["get"],
    ["set", "get", "delete", "get"],
    ["set", "get", "set", "get"],
    ["delete", "get", "set", "get"],
    ["delete", "get", "delete", "get"],
)


@pytest.mark.parametrize("ops", all_ops, ids=" > ".join)
def test_behaviour_get_set_delete_unprotected_nonparameter_class_level(
    ParamTest,
    VanillaTest,
    assert_same_behaviour,
    paramtest_attrs,
    ops,
):
    """Test vanilla behaviour class level."""
    for attr in paramtest_attrs("unprotected", "nonparameter"):
        assert_same_behaviour(ParamTest, VanillaTest, attr=attr, ops=ops)


@pytest.mark.parametrize("ops", all_ops, ids=" > ".join)
def test_behaviour_get_set_delete_unprotected_nonparameter_instance_empty(
    assert_same_behaviour,
    paramtest_attrs,
    ops,
    obj,
):
    """Test vanilla behaviour."""
    param_empty = obj("Param")
    vanilla_empty = obj("Vanilla")
    for attr in paramtest_attrs("unprotected", "nonparameter"):
        assert_same_behaviour(param_empty, vanilla_empty, attr=attr, ops=ops)


@pytest.mark.parametrize("ops", all_ops, ids=" > ".join)
def test_behaviour_get_set_delete_unprotected_nonparameter_instance_filled(
    assert_same_behaviour,
    paramtest_attrs,
    ops,
    obj,
):
    """Test vanilla behaviour."""
    param_filled = obj("Param", fill_dict=True)
    vanilla_filled = obj("Vanilla", fill_dict=True)
    for attr in paramtest_attrs("unprotected", "nonparameter"):
        assert_same_behaviour(param_filled, vanilla_filled, attr=attr, ops=ops)


def test_behaviour_get_protected_nonparameter_class_and_instance(
    ParamTest,
    VanillaTest,
    assert_same_behaviour,
    paramtest_attrs,
    obj,
):
    """Test vanilla behaviour except param_filled <-> param_empty."""
    param_empty = obj("Param")
    param_filled = obj("Param", fill_dict=True)
    vanilla_empty = obj("Vanilla")
    for attr in chain(paramtest_attrs("protected", "nonparameter")):
        assert_same_behaviour(ParamTest, VanillaTest, attr=attr, ops="get")
        assert_same_behaviour(param_empty, vanilla_empty, attr=attr, ops="get")
        assert_same_behaviour(param_empty, param_filled, attr=attr, ops="get")
        assert attr not in vars(param_filled)


def test_behaviour_get_special_case_instance_filled_attr_dict(null, obj):
    """For protected, direct `vars(self)` assignments removed on get."""
    instance = obj("Param")
    attr = "__dict__"

    before_dict_assignment = getattr(instance, attr, null)
    instance.__dict__[attr] = 0
    after_dict_assignment = getattr(instance, attr, null)
    # Get was not affected by `__dict__` addition and removed it
    assert after_dict_assignment is before_dict_assignment
    assert attr not in vars(instance)


# ======================================================================================


# =============================== [3] BYPASS DESCRIPTORS ===============================
def test_behaviour_get_parameter(
    ParamTest,
    null,
    paramtest_attrs,
    paramtest_namespace,
    obj,
    unprotect,
):
    """Always bypasses descriptors."""
    param_empty = obj("Param")
    param_filled = obj("Param", fill_dict=True)
    protected_attrs = paramtest_attrs("protected")

    special = []
    for attr in paramtest_attrs("parameter"):
        # Handle separately those which were not assigned a value in class definition
        if attr in paramtest_namespace:
            expected = paramtest_namespace[attr]
        else:
            special.append(attr)
            continue

        assert getattr(ParamTest, attr) is unprotect(expected)
        assert getattr(param_empty, attr) is unprotect(expected)
        if attr in protected_attrs:
            assert getattr(param_filled, attr) is unprotect(expected)
            assert attr not in vars(param_filled)  # Value removed from dict
        else:
            assert getattr(param_filled, attr) is None  # The filled value

    # Manually handle special cases
    missing, slot = special
    assert missing == "a_unprotected_parameter_with_missing"
    assert slot == "a_unprotected_parameter_slot"

    # Missing
    assert getattr(ParamTest, missing, null) is null
    assert getattr(param_empty, missing, null) is null
    assert getattr(param_filled, missing, null) is None

    # Slot: Check it's a slot then test `getattr` results
    member_descriptor = type(type("", (), {"__slots__": "a"}).a)
    member = vars(ParamTest)[slot]
    assert type(member) is member_descriptor
    assert repr(member) == f"<member '{slot}' of '{ParamTest.__name__}' objects>"

    assert getattr(ParamTest, slot) is member
    assert getattr(param_empty, slot) is member
    assert getattr(param_filled, slot) is None


def test_behaviour_set_unprotected_parameter_class_level(
    ParamTest,
    paramtest_attrs,
    null,
):
    """Always bypasses descriptors."""
    for attr in paramtest_attrs("unprotected", "parameter"):
        setattr(ParamTest, attr, null)
        assert vars(ParamTest)[attr] is null


def test_behaviour_set_unprotected_parameter_instance_level(paramtest_attrs, null, obj):
    """Always bypasses descriptors."""
    param_empty = obj("Param")
    param_filled = obj("Param", fill_dict=True)
    for instance, attr in product(
        [param_empty, param_filled],
        paramtest_attrs("unprotected", "parameter"),
    ):
        setattr(instance, attr, null)
        assert vars(instance)[attr] is null


def test_delete_behaviour_unprotected_parameter_class_level(ParamTest, paramtest_attrs):
    """Always bypasses descriptors."""
    special = []
    for attr in paramtest_attrs("unprotected", "parameter"):
        if attr not in vars(ParamTest):
            special.append(attr)
            continue

        delattr(ParamTest, attr)
        assert attr not in vars(ParamTest)

    # Manually handle special cases
    assert special == ["a_unprotected_parameter_with_missing"]


def test_delete_behaviour_unprotected_parameter_instance_level(paramtest_attrs, obj):
    """Always bypasses descriptors."""
    param_empty = obj("Param")
    param_filled = obj("Param", fill_dict=True)
    for attr in paramtest_attrs("unprotected", "parameter"):
        # Empty instance
        assert attr not in vars(param_empty)
        with pytest.raises(AttributeError, match=f"^{attr}$"):
            delattr(param_empty, attr)

        # Filled instance
        assert attr in vars(param_filled)
        delattr(param_filled, attr)
        assert attr not in vars(param_filled)


# ======================================================================================
