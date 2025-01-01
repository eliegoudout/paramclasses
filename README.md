[![pypi](https://img.shields.io/pypi/v/paramclasses)](https://pypi.org/project/paramclasses/)
[![python versions](https://img.shields.io/badge/python-3.10%20|%203.11%20|%203.12%20|%203.13-blue)](https://devguide.python.org/versions/)
[![license MIT](https://img.shields.io/github/license/eliegoudout/paramclasses)](https://opensource.org/licenses/MIT)
[![pipeline status](https://github.com/eliegoudout/paramclasses/actions/workflows/ci.yml/badge.svg)](https://github.com/eliegoudout/paramclasses/actions)
[![codecov](https://codecov.io/gh/eliegoudout/paramclasses/graph/badge.svg?token=G7YIOODJXE)](https://codecov.io/gh/eliegoudout/paramclasses)
[![mypy](https://www.mypy-lang.org/static/mypy_badge.svg)](https://mypy-lang.org/)
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
    - [Additional functionalities](#additional-functionalities)
        - [Callback on parameters updates](#callback-on-parameters-updates)
        - [Instantiation logic with `__post_init__`](#instantiation-logic-with-__post_init__)
        - [Abstract methods](#abstract-methods)
3. [👩‍💻 **Subclassing API**](#3-subclassing-api-)
4. [🤓 **Advanced**](#4-advanced-)
    - [Post-creation protection](#post-creation-protection)
    - [Descriptor parameters](#descriptor-parameters)
    - [Multiple inheritance](#multiple-inheritance)
    - [Using `__slots__`](#using-__slots__)
    - [Breaking `ParamClass` protection scheme](#breaking-paramclass-protection-scheme)
    - [Type checkers](#type-checkers)
5. [🚀 **Contributing**](#5-contributing-)
    - [Developing with `uv`](#developing-with-uv)
6. [⚖️ **License**](#6-license-)


## 1. Rationale 👩‍🏫

For a parameter-holding class (like [dataclasses](https://docs.python.org/3/library/dataclasses.html)), it is nice to embark some functionality (_e.g._ properties `params` to get a dict of parameters' `(key, value)` pairs, `missing_params` for unassigned parameter keys, ...). Inheriting them via subclassing would allows to factor out specialized functionalities with context-dependant methods (_e.g._ `fit`, `reset`, `plot`, etc...). However, such subclassing comes with a risk of attributes conflicts, especially for exposed APIs, when users do not necessarily know every "read-only" (or "**protected**") attributes from parents classes.

To solve this problem, we propose a base `ParamClass` with a `@protected` decorator, which robustly protects any target attribute from being accidentally overriden when subclassing, at runtime. Note that `@dataclass(frozen=True)` only applies protection to instances' *parameters* and can silently override subclass assignments. Atlernatives such as [`typing.final`](https://docs.python.org/3/library/typing.html#typing.final) and [`typing.Final`](https://docs.python.org/3/library/typing.html#typing.Final) are designed for type checkers on which we do not want to rely -- from python 3.11 onwards, `final` does add a `__final__` flag when possible, but it will not affect immutable objects.

<sup>Back to [Table of Contents](#readme)👆</sup>


## 2. Overview 🧐

### Defining a _paramclass_

A _paramclass_ is defined by subclassing `ParamClass` directly or another _paramclass_. Similarly to [dataclasses](https://docs.python.org/3/library/dataclasses.html), **parameters** are identified as **any annotated attribute** and instancation logic is automatically built-in -- though it can be [extended](#instantiation-logic-with-__post_init__).
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

Instances have a `repr` -- which can be overriden in subclasses -- displaying **non-default or missing** parameter values.
```pycon
>>> A(parameter_with_a__default_value="non-default value")
A(parameter_with_a__default_value='non-default value', parameter_with_no_default_value=?)
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
paramclasses.paramclasses.ProtectedError: Attribute 'fit' is protected
```

This **runtime** protection can be applied to all attributes -- with `protected(value)` --, methods, properties, etc... during class definition but [not after](#post-creation-protection). It is "robust" in the sense that breaking the designed behaviour, though possible, requires -- to our knowledge -- [obscure patterns](#breaking-paramclass-protection-scheme).

<sup>Back to [Table of Contents](#readme)👆</sup>

### Seamless attributes interactions

Parameters can be assigned values like any other attribute -- unless specifically [protected](#protecting-attributes-with-protected) -- with `instance.attr = value`. It is also possible to set multiple parameters at once with keyword arguments during instantiation, or after with `set_params`.
```python
class A(ParamClass):
    x: ...      # Parameter without default value
    y: ... = 1  # Parameter with default value `1`
    z = 2       # Non-parameter attribute
```
```pycon
>>> A(y=0)                      # Instantiation assignments
A(x=?, y=0)                     # Only shows non-default values
>>> A().set_params(x=0, y=0)    # `set_params` assignments
>>> A().y = 1                   # Usual assignment
>>> del A(x=0).x                # Usual deletion
>>> A.x = 1                     # Class-level assignment/deletion works...
>>> A()
A(x=1)                          # ... and `A` remembers default values -- otherwise would show `A(x=?)`
>>> a.set_params(z=0)           # Should FAIL: Non-parameters cannot be assigned with `set_params`
<traceback>
AttributeError: Invalid parameters: {'z'}. Operation cancelled
```

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
def __init__(self, args: list = [], kwargs: dict = {}, /, **param_values: object) -> None:
        self.set_params(**param_values)
        self.__post_init__(*args, **kwargs)

```

Since parameter values are set before `__post_init__` is called, they are accessible when it executes.

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

As seen in [Additional functionalities](#additional-functionalities), three methods may be overriden by subclasses.
```python
# ===================== Subclasses may override these ======================
def _on_param_will_be_set(self, attr: str, future_val: object) -> None:
    """Call before parameter assignment."""

def __post_init__(self, *args: object, **kwargs: object) -> None:
    """Init logic, after parameters assignment."""

def __repr__(self) -> str:
    """Show all non-default or missing, e.g. `A(x=1, z=?)`."""

```

Furthermore, _as a last resort_, developers may occasionally wish to use the following module attributes.

- `DEFAULT`: Current value is `"__paramclass_default_"`. Use `getattr(self, DEFAULT)` to access the dict (`mappingproxy`) of parameters' `(key, default value)` pairs.
- `PROTECTED`: Current value is `"__paramclass_protected_"`. Use `getattr(self, PROTECTED)` to access the set (`frozenset`) of protected parameters.
- `MISSING`: The object representing the "missing value" in the default values of parameters. Using `instance.missing_params` should almost always be enough, but if necessary, use `val is MISSING` to check for missing values.

Strings `DEFAULT` and `PROTECTED` act as special protected keys for _paramclasses_' namespaces, to leave `default` and `protected` available to users. We purposefully chose _would-be-mangled_ names to further decrease odds of natural conflict.

```python
# Recommended way of using `DEFAULT` and `PROTECTED`
from paramclasses import ParamClass, DEFAULT, PROTECTED

getattr(ParamClass, DEFAULT)    # mappingproxy({})
getattr(ParamClass, PROTECTED)  # frozenset({'params', '__getattribute__', '__paramclass_default_', '__paramclass_protected_', 'missing_params', '__setattr__', '__init__', '__delattr__', 'set_params', '__dict__'})
# Works on subclasses and instances too
```

Finally, when subclassing an external `Parent` class, one can check whether it is a paramclass with `isparamclass`.
```python
from paramclasses import isparamclass

isparamclass(Parent)  # Returns a boolean
```

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

**TLDR**: using descriptors for parameter values **is fine** _if you know what to expect_.
```python
import numpy as np

class Aggregator(ParamClass):
    aggregator: ... = np.cumsum

Aggregator().aggregator([0, 1, 2])  # array([0, 1, 3])
```

This behaviour is similar to [dataclasses](https://docs.python.org/3/library/dataclasses.html)' **but is not trivial**:
```python
class NonParamAggregator:
    aggregator: ... = np.cumsum
```
```pycon
>>> NonParamAggregator().aggregator([0, 1, 2])  # Should FAIL
<traceback>
TypeError: 'list' object cannot be interpreted as an integer
>>> NonParamAggregator().aggregator
<bound method cumsum of <__main__.NonParamAggregator object at 0x13a10e7a0>>
```

Note how `NonParamAggregator().aggregator` is a **bound** method. What happened here is that since `np.cumsum` is a [descriptor](https://docs.python.org/3/howto/descriptor.html) -- like all `function`, `property` or `member_descriptor` objects for example --, the function `np.cumsum(a, axis=None, dtype=None, out=None)` interpreted `NonParamAggregator()` to be the array `a`, and `[0, 1, 2]` to be the `axis`.

To avoid this kind of surprises we chose, **for instances' parameters only**, to bypass the get/set/delete descriptor-specific behaviours, and treat them as _usual_ attributes. Contrary to [dataclasses](https://docs.python.org/3/library/dataclasses.html), by also bypassing descriptors for set/delete operations, we allow property-valued parameters, for example.
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
paramclasses.paramclasses.ProtectedError: Incoherent protection inheritance for attribute 'x'
```

<sup>Back to [Table of Contents](#readme)👆</sup>

### Using `__slots__`

Before using `__slots__` with `ParamClass`, please note the following.

1. Since the _parameters_ get/set/delete interactions **bypass** descriptors, using `__slots__` on them **will not** yield the usual behaviour.
2. You **cannot** slot a previously _protected_ attribute -- since it would require replacing its value with a [member object](https://docs.python.org/3/howto/descriptor.html#member-objects-and-slots).
3. Since `ParamClass` does not use `__slots__`, any of its subclasses will still have a `__dict__`.
4. The overhead from `ParamClass` functionality, although not high, probably nullifies any `__slots__` optimization in most use cases.

<sup>Back to [Table of Contents](#readme)👆</sup>

### Breaking `ParamClass` protection scheme

There is no such thing as "perfect attribute protection" in Python. As such `ParamClass` only provides protection against natural behaviour (and even unnatural to a large extent). Below are some [knonwn](test/test_breaking_protection.py) easy ways to break it, representing **discouraged behaviour**. If you find other elementary ways, please report them in an [issue](https://github.com/eliegoudout/paramclasses/issues).

1. Modifying `@protected` -- _huh?_
2. Modifying or subclassing `type(ParamClass)` -- requires evil dedication.

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