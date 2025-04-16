![cross platform](https://img.shields.io/badge/cross--platform-%E2%9C%93-blue)
[![python versions](https://img.shields.io/badge/python-3.10%20|%203.11%20|%203.12%20|%203.13%20|%203.14.0a6-blue)](https://devguide.python.org/versions/)
[![license MIT](https://img.shields.io/github/license/eliegoudout/paramclasses)](https://opensource.org/licenses/MIT)
[![pypi](https://img.shields.io/pypi/v/paramclasses)](https://pypi.org/project/paramclasses/)
[![pipeline status](https://github.com/eliegoudout/paramclasses/actions/workflows/ci.yml/badge.svg)](https://github.com/eliegoudout/paramclasses/actions)
[![codecov](https://codecov.io/gh/eliegoudout/paramclasses/graph/badge.svg?token=G7YIOODJXE)](https://codecov.io/gh/eliegoudout/paramclasses)
[![mypy](https://img.shields.io/badge/mypy-checked-blue)](https://mypy-lang.org/)
![typed](https://img.shields.io/pypi/types/paramclasses)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff#readme)
[![uv](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/uv/main/assets/badge/v0.json)](https://github.com/astral-sh/uv#readme)

# `ParamClass`

```bash
# Install from PyPI
pip install paramclasses
```

###### Table of Contents

1. [👩‍🏫 **Rationale**](#1-rationale-)
2. [🧐 **Overview**](#2-overview-)
    - [Defining a _paramclass_](#defining-a-paramclass)
    - [Protecting attributes with `@protected`](#protecting-attributes-with-protected)
    - [Seamless attributes interactions](#seamless-attributes-interactions)
    - [Expected `getattr`, `setattr` and `delattr` behaviour](#expected-getattr-setattr-and-delattr-behaviour)
    - [Additional functionalities](#additional-functionalities)
        - [Callback on parameters updates](#callback-on-parameters-updates)
        - [Instantiation logic with `__post_init__`](#instantiation-logic-with-__post_init__)
        - [Abstract methods](#abstract-methods)
3. [👩‍💻 **Subclassing API**](#3-subclassing-api-)
4. [🤓 **Advanced**](#4-advanced-)
    - [Post-creation protection](#post-creation-protection)
    - [Descriptor parameters](#descriptor-parameters)
    - [Multiple inheritance](#multiple-inheritance)
    - [`@protected` vs. `super()`](#protected-vs-super)
    - [Using `__slots__`](#using-__slots__)
    - [Breaking `ParamClass` protection scheme](#breaking-paramclass-protection-scheme)
    - [Type checkers](#type-checkers)
5. [🚀 **Contributing**](#5-contributing-)
    - [Developing with `uv`](#developing-with-uv)
6. [⚖️ **License**](#6-license-%EF%B8%8F)


## 1. Rationale 👩‍🏫

##### Parameter-holding classes vs. inheritance...

For a _parameter_-holding class, like [dataclasses](https://docs.python.org/3/library/dataclasses.html), it would be nice to embark some inherited functionality -- _e.g._ `params` property to access current `(param, value)` pairs, `missing_params` for unassigned parameter keys,... Such inheritance would allow to factor out specialized functionality for context-dependant methods -- _e.g._ `fit`, `reset`, `plot`, etc... However, such subclassing comes with a risk of attributes conflicts, especially for libraries or exposed APIs, when users do not necessarily know every "read-only" (or "**protected**") attributes from base classes.

##### Our solution 😌

To solve this problem, we propose a base `ParamClass` and an `@protected` decorator, which robustly protects any target attribute -- not only parameters -- from being accidentally overriden when subclassing, at runtime. If a subclass tries to override an attribute protected by one of its parents, a detailed `ProtectedError` will be raised and class definition will fail.

##### Why not use `@dataclass(frozen=True)` or `typing.final`?

First of all, the `@dataclass(frozen=True)` decorator only applies protection to instances. Besides, it targets all attributes indifferently. Morover, it does not protect against deletion or direct `vars(instance)` manipulation. Finally, protection is not inherited, thus subclasses need to use the decorator again, while being cautious not to silently override previously protected attributes.

The `typing` alternatives [`@final`](https://docs.python.org/3/library/typing.html#typing.final) and [`Final`](https://docs.python.org/3/library/typing.html#typing.Final) are designed for type checkers only, which we do not want to rely on. From python 3.11 onwards, `final` _does_ add a `__final__` flag when possible, but it will not affect immutable objects.

We also mention this [recent PEP draft](https://peps.python.org/pep-0767/) considering attribute-level protection, again for type checkers and without considering subclassing protection.

##### Disclaimer

Note that the protection provided by _paramclasses_ is very robust for **practical use**, but it **should not** be considered a security feature.

<sup>Back to [Table of Contents](#readme)👆</sup>


## 2. Overview 🧐

### Defining a _paramclass_

A _paramclass_ is simply defined by subclassing `ParamClass` directly or another _paramclass_. Similarly to [dataclasses](https://docs.python.org/3/library/dataclasses.html), **parameters** are identified as **any annotated attribute** and instanciation logic is automatically built-in -- though it can be [extended](#instantiation-logic-with-__post_init__). In our context, "default" means the current class value, which may change after the instanciation of an object.
```python
from paramclasses import ParamClass

class A(ParamClass):
    parameter_with_a__default_value: ... = "default value"
    parameter_with_no_default_value: ...
    not_a_parameter = "not a parameter"
    def an_actual_method(self): ...
    def a_method_turned_into_a_parameter(self): ...
    a_method_turned_into_a_parameter: ...

```

Instances have natural `__str__` and `__repr__` methods -- which can be overriden in subclasses --, the former displaying only **nondefault or missing** parameter values.
```pycon
>>> print(A(parameter_with_a__default_value="nondefault value"))  # Calls `__str__`
A(parameter_with_a__default_value='nondefault value', parameter_with_no_default_value=?)
```

One accesses current parameters dict and missing parameters of an instance with the properties `params` and `missing_params` respectively.
```pycon
>>> from pprint import pprint
>>> pprint(A().params)
{'a_method_turned_into_a_parameter': <function A.a_method_turned_into_a_parameter at 0x11067b9a0>,
 'parameter_with_a__default_value': 'default value',
 'parameter_with_no_default_value': ?}
>>> A().missing_params
('parameter_with_no_default_value',)
```
Note that `A().a_method_turned_into_a_parameter` **is not** a _bound_ method -- see [Descriptor parameters](#descriptor-parameters).

<sup>Back to [Table of Contents](#readme)👆</sup>

### Protecting attributes with `@protected`

Say we define the following `BaseEstimator` class.
```python
from paramclasses import ParamClass, protected

class BaseEstimator(ParamClass):
    @protected
    def fit(self, data): ...  # Some fitting logic
```

Then, we are [guaranteed](#breaking-paramclass-protection-scheme) that no subclass can redefine `fit`.
```pycon
>>> class Estimator(BaseEstimator):
...     fit = True  # This should FAIL
... 
<traceback>
ProtectedError: 'fit' is protected by 'BaseEstimator'
```

This **runtime** protection can be applied to all methods, properties, attributes -- with `protected(value)` --, etc... during class definition but [not after](#post-creation-protection). It is "robust" in the sense that breaking the designed behaviour, though possible, requires -- to our knowledge -- [obscure patterns](#breaking-paramclass-protection-scheme).

<sup>Back to [Table of Contents](#readme)👆</sup>

### Seamless attributes interactions

Parameters can be assigned values like any other attribute -- unless specifically [protected](#protecting-attributes-with-protected) -- with `instance.attr = value`. It is also possible to set multiple parameters at once with keyword arguments during instantiation, or after with `set_params`.
```python
class A(ParamClass):
    x: ...      # Parameter without default value
    y: ... = 0  # Parameter with default value `0`
    z: ... = 0  # Parameter with default value `0`
    t = 0       # Non-parameter attribute
```
```pycon
>>> a = A(y=1); a.t = 1; a    # Instantiation assignments
A(x=?, y=1, z=0)              # Shows every parameter with "?" for missing values
>>> A().set_params(x=2, y=2)  # `set_params` assignments
>>> A().y = 1                 # Usual assignment
>>> del A(x=0).x              # Usual deletion
>>> A.y = 1                   # Class-level assignment/deletion works...
>>> print(a)
A(x=?)                        # ... and default value gets updated -- otherwise would show `A(x=?, y=1)`
>>> a.set_params(t=0)         # Should FAIL: Non-parameters cannot be assigned with `set_params`
<traceback>
AttributeError: Invalid parameters: {'t'}. Operation cancelled
```

<sup>Back to [Table of Contents](#readme)👆</sup>

### Expected `getattr`, `setattr` and `delattr` behaviour

<table>
  <caption>Table of Expected Behaviour</caption>
  <tr>
    <th rowspan="2">Operation on<br><code>Class</code> or <code>instance</code></th>
    <th colspan="2">Parameters</th>
    <th colspan="2">Non-Parameters</th>
  </tr>
  <tr>
    <!-- <th>EXPECTED</th> -->
    <th>Protected</th>
    <th>Unprotected</th>
    <th>Protected</th>
    <th>Unprotected</th>
  </tr>
  <tr>
    <!-- <td rowspan="3">BEHAVIOUR</td> -->
    <td><code>getattr</code></td>
    <td>Bypass Descriptors*</td>
    <td>Bypass Descriptors</td>
    <td>Vanilla*</td>
    <td>Vanilla</td>
  </tr>
  <tr>
    <td><code>setattr</code></td>
    <td><code>ProtectedError</code></td>
    <td>Bypass Descriptors</td>
    <td><code>ProtectedError</code></td>
    <td>Vanilla</td>
  </tr>
  <tr>
    <td><code>delattr</code></td>
    <td><code>ProtectedError</code></td>
    <td>Bypass Descriptors</td>
    <td><code>ProtectedError</code></td>
    <td>Vanilla</td>
  </tr>
</table>
*<sub>On <code>instance</code>, <code>getattr</code> should ignore and remove any <code>vars(instance)</code> entry.</sub>

_Vanilla_ means that there should be no discernable difference compared to standard classes.

<sup>Back to [Table of Contents](#readme)👆</sup>

### Additional functionalities

#### Callback on parameters updates

Whenever an instance is assigned a value -- instantiation, `set_params`, dotted assignment -- the callback
```python
def _on_param_will_be_set(self, attr: str, future_val: object) -> None
```
is triggered. For example, it can be used to `unfit` and estimator on specific modifications. As suggested by the name and signature, the callback operates just before the `future_val` assignment. There is currently no counterpart for parameter deletion. This could be added upon motivated interest.

<sup>Back to [Table of Contents](#readme)👆</sup>

#### Instantiation logic with `__post_init__`

Similarly to [dataclasses](https://docs.python.org/3/library/dataclasses.html), a `__post_init__` method can be defined to complete instantiation after the initial setting of parameter values. It must have signature
```python
def __post_init__(self, *args: object, **kwargs: object) -> None
```
and is called as follows by `__init__`.
```python
# Close equivalent to actual implementation
@protected
def __init__(self, args: list[object] = [], kwargs: dict[str, object] = {}, /, **param_values: object) -> None:
        self.set_params(**param_values)
        self.__post_init__(*args, **kwargs)

```

Since parameter values are set before `__post_init__` is called, they are accessible when it executes. Note that even if a _paramclass_ does not define `__post_init__`, its bases might, in which case it is used.

<sup>Back to [Table of Contents](#readme)👆</sup>

#### Abstract methods

The base `ParamClass` already inherits `ABC` functionalities, so `@abstractmethod` can be used.
```python
from abc import abstractmethod

class A(ParamClass):
    @abstractmethod
    def next(self): ...
```
```pycon
>>> A()
<traceback>
TypeError: Can't instantiate abstract class A with abstract method next
```

<sup>Back to [Table of Contents](#readme)👆</sup>


## 3. Subclassing API 👩‍💻

As seen in [Additional functionalities](#additional-functionalities), three methods may be implemented by subclasses.
```python
# ===================== Subclasses may override these ======================
def _on_param_will_be_set(self, attr: str, future_val: object) -> None:
    """Call before parameter assignment."""

def __repr__(self) -> str:
    """Show all params, e.g. `A(x=1, z=?)`."""

def __str__(self) -> str:
    """Show all nondefault or missing, e.g. `A(z=?)`."""

# ===================== Subclasses may introduce these =====================
def __post_init__(self, *args: object, **kwargs: object) -> None:
    """Init logic, after parameters assignment."""

```

Furthermore, _as a last resort_, developers may occasionally wish to use the following module attributes.

- `IMPL`: Current value is `"__paramclass_impl_"`. Use `getattr(paramclass or instance, IMPL)` to get a `NamedTuple` instance with `annotations` and `protected` fields. Both are mapping proxies of, respectively, `(param, annotation)` and `(protected attribute, owner)` pairs. Note that the annotations are fixed at class creation and **never updated**. The string `IMPL` acts as special protected key for _paramclasses_' namespaces, to leave `annotations` and `protected` available to users. We purposefully chose a _would-be-mangled_ name to further decrease the odds of natural conflict.
- `MISSING`: The object representing the "missing value", used for string representations and checking parameter values.

```python
# Recommended way of using `IMPL`
from paramclasses import IMPL, ParamClass

getattr(ParamClass, IMPL).annotations  # mappingproxy({})
getattr(ParamClass, IMPL).protected    # mappingproxy({'__paramclass_impl_': None, '__dict__': None, '__init__': <class 'paramclasses.paramclasses.RawParamClass'>, '__getattribute__': <class 'paramclasses.paramclasses.RawParamClass'>, '__setattr__': <class 'paramclasses.paramclasses.RawParamClass'>, '__delattr__': <class 'paramclasses.paramclasses.RawParamClass'>, 'set_params': <class 'paramclasses.paramclasses.ParamClass'>, 'params': <class 'paramclasses.paramclasses.ParamClass'>, 'missing_params': <class 'paramclasses.paramclasses.ParamClass'>})
# Works on subclasses and instances too
```

When subclassing an external `UnknownClass`, one can check whether it is a _paramclass_ with `isparamclass`.
```python
from paramclasses import isparamclass

isparamclass(UnknownClass)  # Returns a boolean
```
Finally, it is possible to subclass `RawParamClass` directly -- unique parent class of `ParamClass` --, when `set_params`, `params` and `missing_params` are not necessary. In this case, use signature `isparamclass(UnknownClass, raw=True)`.

<sup>Back to [Table of Contents](#readme)👆</sup>


## 4. Advanced 🤓

### Post-creation protection

It is **not allowed** and will be ignored with a warning.
```python
class A(ParamClass):
    x: int = 1
```
```pycon
>>> A.x = protected(2)  # Assignment should WORK, protection should FAIL
<stdin>:1: UserWarning: Cannot protect attribute 'x' after class creation. Ignored
>>> a = A(); a
A(x=2)                  # Assignment did work
>>> a.x = protected(3)  # Assignment should WORK, protection should FAIL
<stdin>:1: UserWarning: Cannot protect attribute 'x' on instance assignment. Ignored
>>> a.x
3                       # First protection did fail, new assignment did work
>>> del a.x; a
A(x=2)                  # Second protection did fail
```

<sup>Back to [Table of Contents](#readme)👆</sup>

### Descriptor parameters

**TLDR**: using descriptors for parameter values **is fine** _if you know [what to expect](#expected-getattr-setattr-and-delattr-behaviour)_.
```python
import numpy as np

class Operator(ParamClass):
    op: ... = np.cumsum

Operator().op([0, 1, 2])  # array([0, 1, 3])
```

This behaviour is similar to [dataclasses](https://docs.python.org/3/library/dataclasses.html)' **but is not trivial**:
```python
class NonParamOperator:
    op: ... = np.cumsum
```
```pycon
>>> NonParamOperator().op([0, 1, 2])  # Should FAIL
<traceback>
TypeError: 'list' object cannot be interpreted as an integer
>>> NonParamOperator().op
<bound method cumsum of <__main__.NonParamOperator object at 0x13a10e7a0>>
```

Note how `NonParamOperator().op` is a **bound** method. What happened here is that since `np.cumsum` is a data [descriptor](https://docs.python.org/3/howto/descriptor.html) -- like all `function`, `property` or `member_descriptor` objects for example --, the function `np.cumsum(a, axis=None, dtype=None, out=None)` interpreted `NonParamOperator()` to be the array `a`, and `[0, 1, 2]` to be the `axis`.

To avoid this kind of surprises we chose, **for parameters only**, to bypass the get/set/delete descriptor-specific behaviours, and treat them as _usual_ attributes. Contrary to [dataclasses](https://docs.python.org/3/library/dataclasses.html), by also bypassing descriptors for set/delete operations, we allow property-valued parameters, for example.
```python
class A(ParamClass):
    x: property = property(lambda _: ...)  # Should WORK

@dataclass
class B:
    x: property = property(lambda _: ...)  # Should FAIL
```
```pycon
>>> A()  # paramclass
A()
>>> B()  # dataclass
<traceback>
AttributeError: can't set attribute 'x'
```
This should not be a very common use case anyway.

<sup>Back to [Table of Contents](#readme)👆</sup>

### Multiple inheritance

###### With _paramclass_ bases

Multiple inheritance is not a problem. Default values will be retrieved as expect following the MRO, but there's one caveat: protected attributes should be consistant between the bases. For example, if `A.x` is not protected while `B.x` is, one cannot take `(A, B)` for bases.
```python
class A(ParamClass):
    x: int = 0

class B(ParamClass):
    x: int = protected(1)

class C(B, A): ...  # Should WORK

class D(A, B): ...  # Should FAIL
```
```pycon
>>> class C(B, A): ...  # Should WORK
... 
>>> class D(A, B): ...  # Should FAIL
... 
<traceback>
ProtectedError: 'x' protection conflict: 'A', 'B'
```

###### Inheriting from non-_paramclasses_

It is possible to inherit from a mix of _paramclasses_ and non-_paramclasses_, with the two following limitations.

1. Because `type(ParamClass)` is a subclass of `ABCMeta`, non-_paramclass_ bases must be either vanilla classes or abstract classes.
2. Behaviour is not guaranteed for non-_paramclass_ bases with an `IMPL`-named attribute -- _see [Subclassing API](#3-subclassing-api-)_.
3. Until [#28](https://github.com/eliegoudout/paramclasses/issues/28) is fixed, one should manually ensure that MRO does not prioritize any non-paramclass before all paramclasses.

<sup>Back to [Table of Contents](#readme)👆</sup>

### `@protected` vs. `super()`

It is not recommended to use `super()` inside a `@protected` method definition, when the protection aims at "locking down" its behaviour. Indeed, one can never assume the MRO of future subclasses will ressemble that of the method-defining class.

For example, picture the following inheritance schemes.
```python
class A(RawParamClass): ...
class B(RawParamClass): ...
class C(B, A): ...
```
In this situation, the MRO of `C` would be `C -> B -> A -> RawParamClass -> object`. As such, if `B` was to redefine `__repr__` using `super()` and `@protected`, `repr(C())` would call `A.__repr__`, which can behave arbitrarily despite `B.__repr__` being `@protected`. Instead, it is recommended to call `RawParamClass.__repr__` directly.

<sup>Back to [Table of Contents](#readme)👆</sup>

### Using `__slots__`

Before using `__slots__` with `ParamClass`, please note the following.

1. Since `ParamClass` uses `__dict__`, any _paramclass_ will too.
2. You **cannot** slot a previously _protected_ attribute -- since it would require updating its class value.
3. Since parameters' get/set/delete interactions **bypass** descriptors, using `__slots__` on them **will not** yield the usual behaviour.
4. The overhead from `ParamClass` functionality would nullify any `__slots__` optimization in most cases anyway.

<sup>Back to [Table of Contents](#readme)👆</sup>

### Breaking `ParamClass` protection scheme

There is no such thing as "perfect attribute protection" in Python. As such `ParamClass` only provides protection against natural behaviour -- and even unnatural to a _large_ extent. Below are some [knonwn](test/paramclasses/test_breaking_protection.py) **anti-patterns** to break it, representing **discouraged behaviour**. If you find other elementary ways, please report them in an [issue](https://github.com/eliegoudout/paramclasses/issues).

1. Using `type.__setattr__`/`type.__delattr__` directly on _paramclasses_.
2. Modifying `@protected` -- _huh?_
3. Modifying or subclassing `type(ParamClass)` -- requires evil dedication.
4. Messing with `mappingproxy`, which is [not really](https://bugs.python.org/msg391039) immutable.

<sup>Back to [Table of Contents](#readme)👆</sup>

### Type checkers

The `@protected` decorator is not acting in the usual sense, as it is a simple wrapper meant to be detected and unwrapped by the metaclass constructing _paramclasses_. Consequently, type checkers such as [mypy](https://mypy-lang.org/) may be confused. If necessary, we recommend locally disabling type checking with the following comment -- and the appropriate [error-code](https://mypy.readthedocs.io/en/stable/error_codes.html).
```python
@protected  # type: ignore[error-code]  # mypy is fooled
def my_protected_method(self):
```
It is not ideal and _may_ be fixed in future updates.

<sup>Back to [Table of Contents](#readme)👆</sup>


## 5. Contributing 🚀

Questions, [issues](https://github.com/eliegoudout/paramclasses/issues), [discussions](https://github.com/eliegoudout/paramclasses/discussions) and [pull requests](https://github.com/eliegoudout/paramclasses/pulls) are welcome! Please do not hesitate to [contact me](mailto:eliegoudout@hotmail.com).

### Developing with `uv`

The project is developed with [uv](https://github.com/astral-sh/uv#readme) which simplifies _soooo_ many things!
```bash
# Installing `uv` on Linux and macOS
curl -LsSf https://astral.sh/uv/install.sh | sh
# Using `uv` command may require restarting the bash session
```
After having installed [uv](https://github.com/astral-sh/uv#readme), you can independently use all of the following without ever worrying about installing python or dependencies, or creating virtual environments.
```bash
uvx ruff check                        # Check linting
uvx ruff format --diff                # Check formatting
uv run mypy                           # Run mypy
uv pip install -e . && uv run pytest  # Run pytest
uv run python                         # Interactive session in virtual environment
```

<sup>Back to [Table of Contents](#readme)👆</sup>

## 6. License ⚖️

This package is distributed under the [MIT License](LICENSE).

<sup>Back to [Table of Contents](#readme)👆</sup>
