"""Type system — a lightweight Pydantic-like BaseModel with validation — optimized."""

from __future__ import annotations

import inspect
import json
import re as _re
from datetime import datetime, date, time
from decimal import Decimal
from enum import Enum
from typing import Any, get_type_hints, get_origin, get_args
from uuid import UUID


class Field:
    """Field descriptor for declaring model fields with defaults, aliases, and validators."""

    __slots__ = (
        "default", "default_factory", "alias", "description",
        "ge", "le", "gt", "lt", "min_length", "max_length", "pattern", "name",
    )

    def __init__(
        self,
        default: Any = ...,
        *,
        default_factory: callable = None,
        alias: str = None,
        description: str = "",
        ge: float = None,
        le: float = None,
        gt: float = None,
        lt: float = None,
        min_length: int = None,
        max_length: int = None,
        pattern: str = None,
    ):
        self.default = default
        self.default_factory = default_factory
        self.alias = alias
        self.description = description
        self.ge = ge
        self.le = le
        self.gt = gt
        self.lt = lt
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = pattern
        self.name = None

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, obj, objtype=None):
        if obj is None:
            return self
        return obj.__dict__.get(self.name, ...)

    def __set__(self, obj, value):
        obj.__dict__[self.name] = value


# ── Sentinels ────────────────────────────────────────────────

_UNSET = ...

# UnionType compatibility
try:
    from types import UnionType as _UnionType
except ImportError:
    _UnionType = getattr(__import__("typing"), "Union", None)


# ── Pre-compiled init plan for BaseModel ─────────────────────

_InitStep = tuple  # (field_name, alias, coerce_fn, default_or_unsent, default_factory_or_none, required)


def _build_init_plan(cls: type) -> list[_InitStep]:
    """Pre-compile initialization steps for a BaseModel subclass.

    Called once per class. Returns a list that __init__ can iterate without
    any type-dispatch overhead.
    """
    steps = []
    for field_name, (field_type, field_def, alias) in cls.__fields__.items():
        # Build a closure that validates this specific field type
        coerce_fn = _make_coercer(field_type, field_def)

        default = field_def.default
        default_factory = field_def.default_factory
        required = field_name in cls.__required__

        steps.append((field_name, alias, coerce_fn, default, default_factory, required))

    # Store validators separately (run after init)
    cls.__init_steps__ = steps
    return steps


def _make_coercer(field_type: type, field_def: Field) -> callable:
    """Create a specialized validation function for a specific field type.

    This avoids isinstance/issubclass dispatch on every call.
    """
    origin = get_origin(field_type)
    args = get_args(field_type)

    # Optional[T] / Union[T, None]
    if origin is _UnionType and type(None) in args:
        non_none = [a for a in args if a is not type(None)]
        if len(non_none) == 1:
            inner_coerce = _make_coercer_for_type(non_none[0], field_def)
            return lambda v, fn=inner_coerce: None if v is None else fn(v)

    # Any
    if field_type is Any:
        return lambda v: v

    # Union
    if origin is _UnionType:
        coercers = [_make_coercer_for_type(a, field_def) for a in args if a is not type(None)]
        nullable = type(None) in args

        def union_coerce(v, _coercers=coercers, _nullable=nullable):
            if v is None and _nullable:
                return None
            errors = []
            for c in _coercers:
                try:
                    return c(v)
                except TypeError as e:
                    errors.append(str(e))
            raise TypeError("; ".join(errors))
        return union_coerce

    # List[T]
    if origin is list:
        item_coerce = _make_coercer_for_type(args[0], None) if args else (lambda v: v)
        return lambda v, _ic=item_coerce: (
            [_ic(item) for item in v]
            if isinstance(v, (list, tuple))
            else _raise_type("list", v)
        )

    # Dict[K, V]
    if origin is dict:
        key_c = _make_coercer_for_type(args[0], None) if len(args) >= 1 else (lambda v: v)
        val_c = _make_coercer_for_type(args[1], None) if len(args) >= 2 else (lambda v: v)
        return lambda v, _kc=key_c, _vc=val_c: (
            {_kc(k): _vc(vv) for k, vv in v.items()}
            if isinstance(v, dict)
            else _raise_type("dict", v)
        )

    # Tuple
    if origin is tuple:
        item_coercers = [_make_coercer_for_type(a, None) for a in args] if args else []
        return lambda v, _ics=item_coercers: (
            tuple(c(item) for c, item in zip(_ics, v))
            if isinstance(v, (list, tuple))
            else _raise_type("tuple", v)
        )

    return _make_coercer_for_type(field_type, field_def)


def _make_coercer_for_type(field_type: type, field_def: Field | None) -> callable:
    """Create a coercer for a concrete (non-generic) type."""
    # Handle generics — dispatch to parent _make_coercer
    origin = get_origin(field_type)
    if origin is not None:
        return _make_coercer(field_type, field_def)

    if isinstance(field_type, type) and issubclass(field_type, Enum):
        members = {str(m.value): m for m in field_type}
        enum_cls = field_type

        def enum_coerce(v, _members=members, _cls=enum_cls):
            if isinstance(v, _cls):
                return v
            if isinstance(v, str) and v in _members:
                return _members[v]
            raise TypeError(f"Invalid enum value: {v!r}")
        return enum_coerce

    if isinstance(field_type, type) and issubclass(field_type, BaseModel):
        model_cls = field_type

        def model_coerce(v, _mc=model_cls):
            if isinstance(v, _mc):
                return v
            if isinstance(v, dict):
                return _mc(**v)
            raise TypeError(f"Expected {_mc.__name__}")
        return model_coerce

    # Simple types with constraint support
    if field_type is str:
        min_len = field_def.min_length if field_def else None
        max_len = field_def.max_length if field_def else None
        pattern = _re.compile(field_def.pattern) if (field_def and field_def.pattern) else None

        def str_coerce(v, _ml=min_len, _xl=max_len, _pat=pattern):
            s = v if isinstance(v, str) else str(v)
            if _ml is not None and len(s) < _ml:
                raise TypeError(f"Length {len(s)} < min {_ml}")
            if _xl is not None and len(s) > _xl:
                raise TypeError(f"Length {len(s)} > max {_xl}")
            if _pat is not None and not _pat.match(s):
                raise TypeError(f"Doesn't match pattern")
            return s
        return str_coerce

    if field_type is int:
        ge = field_def.ge if field_def else None
        le = field_def.le if field_def else None
        gt = field_def.gt if field_def else None
        lt = field_def.lt if field_def else None

        def int_coerce(v, _ge=ge, _le=le, _gt=gt, _lt=lt):
            if isinstance(v, bool):
                raise TypeError("Expected int, got bool")
            if not isinstance(v, int):
                try:
                    v = int(v)
                except (ValueError, TypeError):
                    raise TypeError(f"Expected int")
            if _ge is not None and v < _ge:
                raise TypeError(f"'{v}' must be >= {_ge}")
            if _le is not None and v > _le:
                raise TypeError(f"'{v}' must be <= {_le}")
            if _gt is not None and v <= _gt:
                raise TypeError(f"'{v}' must be > {_gt}")
            if _lt is not None and v >= _lt:
                raise TypeError(f"'{v}' must be < {_lt}")
            return v
        return int_coerce

    if field_type is float:
        ge = field_def.ge if field_def else None
        le = field_def.le if field_def else None
        gt = field_def.gt if field_def else None
        lt = field_def.lt if field_def else None

        def float_coerce(v, _ge=ge, _le=le, _gt=gt, _lt=lt):
            if not isinstance(v, float):
                try:
                    v = float(v)
                except (ValueError, TypeError):
                    raise TypeError(f"Expected float")
            if _ge is not None and v < _ge:
                raise TypeError(f"'{v}' must be >= {_ge}")
            if _le is not None and v > _le:
                raise TypeError(f"'{v}' must be <= {_le}")
            if _gt is not None and v <= _gt:
                raise TypeError(f"'{v}' must be > {_gt}")
            if _lt is not None and v >= _lt:
                raise TypeError(f"'{v}' must be < {_lt}")
            return v
        return float_coerce

    if field_type is bool:
        def bool_coerce(v):
            if isinstance(v, bool):
                return v
            raise TypeError("Expected bool")
        return bool_coerce

    if field_type is datetime:
        _fmts = ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d")

        def dt_coerce(v, _fmts=_fmts):
            if isinstance(v, datetime):
                return v
            if isinstance(v, str):
                for fmt in _fmts:
                    try:
                        return datetime.strptime(v, fmt)
                    except ValueError:
                        continue
            raise TypeError("Expected datetime")
        return dt_coerce

    if field_type is date:
        def d_coerce(v):
            if isinstance(v, date):
                return v
            if isinstance(v, str):
                return date.fromisoformat(v)
            if isinstance(v, datetime):
                return v.date()
            raise TypeError("Expected date")
        return d_coerce

    if field_type is time:
        def t_coerce(v):
            if isinstance(v, time):
                return v
            if isinstance(v, str):
                return time.fromisoformat(v)
            raise TypeError("Expected time")
        return t_coerce

    if field_type is UUID:
        def uuid_coerce(v):
            if isinstance(v, UUID):
                return v
            try:
                return UUID(str(v))
            except (ValueError, AttributeError):
                raise TypeError("Expected UUID")
        return uuid_coerce

    if field_type is Decimal:
        def dec_coerce(v):
            if isinstance(v, Decimal):
                return v
            try:
                return Decimal(str(v))
            except Exception:
                raise TypeError("Expected Decimal")
        return dec_coerce

    # Generic fallback — only check isinstance for non-generic types
    try:
        return lambda v, _ft=field_type: v if isinstance(v, _ft) else _raise_type(_ft.__name__, v)
    except TypeError:
        # Parameterized generics like list[str] can't be used with isinstance
        return lambda v: v


def _raise_type(expected: str, value: Any):
    raise TypeError(f"Expected {expected}, got {type(value).__name__}")


# ── Metaclass ────────────────────────────────────────────────

class ModelMeta(type):
    """Metaclass that collects typed fields, validators, and builds init plan."""

    def __new__(mcs, name, bases, namespace):
        cls = super().__new__(mcs, name, bases, namespace)
        cls.__fields__ = {}
        cls.__required__ = set()
        cls.__validators__ = {}
        cls.__init_steps__ = None  # Built lazily

        for base in reversed(bases):
            if hasattr(base, "__fields__"):
                cls.__fields__.update(base.__fields__)
            if hasattr(base, "__required__"):
                cls.__required__.update(base.__required__)
            if hasattr(base, "__validators__"):
                cls.__validators__.update(base.__validators__)

        try:
            hints = get_type_hints(cls, include_extras=False)
        except Exception:
            hints = namespace.get("__annotations__", {})

        for field_name, field_type in hints.items():
            if field_name.startswith("_"):
                continue
            default = namespace.get(field_name, _UNSET)
            if isinstance(default, Field):
                default.name = field_name
                cls.__fields__[field_name] = (field_type, default, default.alias or field_name)
                if default.default is _UNSET and default.default_factory is None:
                    cls.__required__.add(field_name)
            elif default is _UNSET:
                cls.__fields__[field_name] = (field_type, Field(), field_name)
                cls.__required__.add(field_name)
            else:
                cls.__fields__[field_name] = (field_type, Field(default=default), field_name)

        for attr_name, attr_value in namespace.items():
            if callable(attr_value) and getattr(attr_value, "_is_validator", False):
                for target_field in attr_value._validates_fields:
                    if target_field not in cls.__validators__:
                        cls.__validators__[target_field] = []
                    cls.__validators__[target_field].append(attr_value)

        return cls


# ── BaseModel ────────────────────────────────────────────────

class BaseModel(metaclass=ModelMeta):
    """Base class for data models with automatic type validation."""

    def __init__(self, **data: Any):
        # Build init plan lazily (once per class)
        steps = self.__class__.__init_steps__
        if steps is None:
            steps = _build_init_plan(self.__class__)

        # Resolve aliases — use dict comprehension for speed
        resolved = {}
        cls_fields = self.__class__.__fields__
        for fn in data:
            resolved[fn] = data[fn]
        # Also resolve aliases
        for field_name, (_, field_def, alias) in cls_fields.items():
            if field_name not in resolved and alias != field_name and alias in data:
                resolved[field_name] = data[alias]

        # Execute init plan — tight loop
        for field_name, alias, coerce_fn, default, default_factory, required in steps:
            if field_name in resolved:
                value = resolved[field_name]
            elif default_factory is not None:
                value = default_factory()
            elif default is not _UNSET:
                value = default
            elif required:
                raise TypeError(f"{self.__class__.__name__}.{field_name} is required")
            else:
                continue

            try:
                self.__dict__[field_name] = coerce_fn(value)
            except TypeError:
                raise
            except Exception as e:
                raise TypeError(f"{self.__class__.__name__}.{field_name}: {e}") from e

        # Run validators
        for field_name, validators in self.__class__.__validators__.items():
            if field_name in self.__dict__:
                value = self.__dict__[field_name]
                for validator_fn in validators:
                    try:
                        result = validator_fn(self.__class__, value)
                        if result is not None:
                            self.__dict__[field_name] = result
                            value = result
                    except ValueError as e:
                        raise TypeError(f"{self.__class__.__name__}.{field_name}: {e}") from e

    def model_dump(self, *, mode: str = "python") -> Any:
        result = {}
        for field_name in self.__class__.__fields__:
            value = self.__dict__.get(field_name, _UNSET)
            if value is not _UNSET:
                result[field_name] = _serialize(value, mode=mode)
        if mode == "json":
            return json.dumps(result, ensure_ascii=False, default=_json_serializer)
        return result

    def model_dump_json(self, **kwargs) -> str:
        return self.model_dump(mode="json")

    @classmethod
    def model_validate(cls, data: dict | Any) -> BaseModel:
        if isinstance(data, cls):
            return data
        return cls(**data)


# ── Validator decorator ──────────────────────────────────────

def validator(*field_names: str):
    def decorator(func):
        func._is_validator = True
        func._validates_fields = field_names
        return func
    return decorator


# ── Serialization helpers ────────────────────────────────────

def _serialize(value: Any, mode: str = "python") -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="python")
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, time):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, Decimal):
        return float(value) if mode == "json" else value
    if isinstance(value, dict):
        return {k: _serialize(v, mode) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize(v, mode) for v in value]
    return value


def _json_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, time):
        return obj.isoformat()
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, Enum):
        return obj.value
    raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")


def validate(model_cls: type[BaseModel], data: dict) -> BaseModel:
    return model_cls.model_validate(data)
