# `ParamClass`

###### Table of Contents

1. [🧑‍🏫 **Rationale**](#1-rationale-)
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
5. [🚀 **Contributing**](#5-contributing-)
6. [⚖️ **License**](#6-license-)

## 1. Rationale 🧑‍🏫

For a parameter-holding class (like [dataclasses](https://docs.python.org/3/library/dataclasses.html)), it is nice to embark some functionality (_e.g._ properties `params` to get a dict of parameters' `(key, value) pairs, `missing_params` for unassigned parameter-keys, ...). Inheriting them via subclassing would allows to factor out specialized functionalities with context-dependant methods (_e.g._ `fit`, `reset`, `plot`, etc...). However, such subclassing comes with a risk of attributes conflicts, especially for exposed APIs, when users do not necessarily know every "read-only" (or "**protected**") attributes from parents classes.

To solve this problem, we propose a base `ParamClass` with a `@protected` decorator, which robustly protects target attributes from being accidentally overriden when subclassing, at runtime -- contrary to `typing.final` and `typing.Final`.

## 2. Overview 🧐

#### Defining a _paramclass_

A _paramclass_ is defined by subclassing `ParamClass` directly or another _paramclass_. Similarly to [dataclasses](https://docs.python.org/3/library/dataclasses.html), **parameters** are identified as **any annotated attribute** -- the annotation in itself does not matter -- and there is no need to defined `__init__`.
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

Instances have a `repr` -- which can be overriden in subclasses -- displaying **non-default or missing** parameter-values.
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
['parameter_with_no_default_value']
```
Note that `A().a_method_turned_into_a_parameter` **is not** a _bound_ method -- see [Descriptor parameters](#descriptor-parameters).

#### Protecting attributes with `@protected`

Say we define the following `BaseEstimator` class.
```python
from paramclass import ParamClass, protected

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


#### Seamless attributes interactions

Parameters can be assigned values like any other attribute -- unless specifically [protected](#protecting-attributes-with-protected) -- with `instance.attr = value`. It is also possible to set multiple parameters at once with keyword arguments during instantiation, or after with `set_params`.
```python
class A(ParamClass):
    x: ...      # Parameter without default value
    y: ... = 1  # Parameter with default value `1`
    z = 2       # Non-parameter attribute
```
```pycon
>>> A(x=0, y=1)                 # Instantiation assignments
A(x=0)                          # Only shows non-default values
>>> A().set_params(x=0, y=2)    # `set_params assignments
>>> A().y = 1                   # Usual assignment
>>> del A(x=0).x                # Usual deletion
>>> A.x = 1                     # Class-level assignment/deletion works...
>>> A()
A(x=1)                          # ... and `A` remembers default values -- otherwise would show `A()`
>>> a.set_params(z=3)           # FAILS: Non-parameters cannot be assigned with `set_params`
<traceback>
AttributeError: Invalid parameters: {'z'}. Operation cancelled
```

#### Additional functionalities

##### Callback on parameters updates

Whenever an instance is assigned a value -- instantiation, `set_params`, dotted assignment -- the callback
```python
def _on_param_will_be_set(self, attr: str, future_val: object) -> None:
```
is triggered. For example, it can be used to `unfit` and estimator on specific modifications. As suggested by the name and signature, the callback operates just before the `future_val` assignment. There is currently no counterpart for parameter deletion. This could be added upon motivated interest.

##### Instantiation logic with `__post_init__`

Similarly to [dataclasses](https://docs.python.org/3/library/dataclasses.html), a `__post_init__` method can be defined to complete instantiation after the initial setting of parameters values. It must have signature
```python
def __post_init__(self, *args: object, **kwargs: object) -> None: ...
```
and it is called at instantiation with the following signature:
```python
MyParamClass(args: list = [], kwargs: dict = {}, /, **param_values)
```

Since parameter values are set before `__post_init__` is called, they are accessible when it executes.

##### Abstract methods

The base `ParamClass` already inherits `ABC` functionalities, so `@abstractmethod` can be used:
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

## 3. Subclassing API 👩‍💻

As seen in [Additional functionalities](#additional-functionalities), three methods may be overriden by subclasses:
```python
# ===================== Subclasses may override these ======================
def _on_param_will_be_set(self, attr: str, future_val: object) -> None:
    """Call before new parameter assignment."""

def __post_init__(self, *args: object, **kwargs: object) -> None:
    """Init logic, after parameters assignment."""

def __repr__(self) -> str:
    """Show all non-default or missing, e.g. `A(x=1, z=?)`."""

```

Furthermore, _as a last resort_, developers may occasionally wish to use the following _metaclass attributes_ -- where `mcs = type(ParamClass)`.

- `mcs.default`: Use `getattr(self, mcs.default)` to access the dict (`mappingproxy`) of parameters' `(key, default value)` pairs. Current value is `"__paramclass_default_"`.
- `mcs.protected`: Use `getattr(self, mcs.protected)` to access the set (`frozenset`) of protected parameters. Current value is `"__paramclass_protected_"`.
- `mcs.missing`: The object representing the "missing value" in the default values of parameters.

These as purposefully kept in the metaclass namespace to avoid as best as possible crowding `ParamClass` namespace. Indeed, users may want to use `default` or `missing` as parameter keys for example. Furthermore, their use should be occasional.

## 4. Advanced 🤓

#### Post-creation protection

It is **not allowed** and will trigger a warning:
```python
class A(ParamClass):
    x: int = 1
```
```pycon
>>> A.x = protected(2)  # Should work with warning
<stdin>:1: UserWarning: Cannot protect attribute 'x' after class creation. Ignored
>>> a = A(); a
A(x=2)                  # It indeed worked
>>> a.x = protected(3)  # Should work with warning
<stdin>:1: UserWarning: Cannot protect attribute 'x' on instance assignment. Ignored
>>> a.x
3                       # It indeed worked
```

#### Descriptor parameters

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

#### Multiple inheritance

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

#### Using `__slots__`

Before using `__slots__` with `ParamClass`, please note the following.

1. Since the _parameters_ get/set/delete interactions **bypass** descriptors, using `__slots__` on them **will not** yield the usual behaviour.
2. You **cannot** slot a previously _protected_ attribute -- since it would require replacing its value with a [member object](https://docs.python.org/3/howto/descriptor.html#member-objects-and-slots).
3. Since `ParamClass` does not use `__slots__`, any of its subclasses will still have a `__dict__`.
4. The overhead from `ParamClass` functionality, although not high, probably nullifies any `__slots__` optimization in most use cases.

#### Breaking `ParamClass` protection scheme

There is no such thing as "perfect attribute protection" in Python. As such `ParamClass` only provides protection against natural behaviour (and even unnatural to a large extent). Below are some knonwn easy ways to break it, representing **discouraged behaviour**. If you find other elementary ways, please report them in an issue.

1. Modifying `@protected` -- _huh?_
2. Use custom sub-metaclass, after modifying meta-metaclass -- requires dedication.
3. Manipulating `instance.__dict__` directly...


## 5. Contributing 🚀

Questions, [issues](https://github.com/eliegoudout/paramclasses/issues), [discussions](https://github.com/eliegoudout/paramclasses/discussions) and [pull requests](https://github.com/eliegoudout/paramclasses/pulls) are welcome! Please do not hesitate to [contact me](mailto:eliegoudout@hotmail.com).

## 6. License ⚖️

This package is distributed under the [MIT License](LICENSE).