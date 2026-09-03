"""NIMM v1.0 grid-data normalization and validation helpers.

The generic meteva_base APIs historically used lower-case attributes and
permissive coordinate defaults.  This module provides the stricter contract
required by the NIMM grid NC format while keeping the conversion logic in one
place for constructors and NetCDF readers/writers.
"""

from __future__ import annotations

from copy import deepcopy

import numpy as np
import pandas as pd
import xarray as xr


NIMM_DIMS = ("member", "level", "time", "dtime", "lat", "lon")
NIMM_REQUIRED_COORDS = ("time", "lat", "lon")
NIMM_OPTIONAL_COORD_DEFAULTS = {
    "member": ["0"],
    "level": [np.float32(0.0)],
    "dtime": [np.int32(0)],
}
NIMM_DATA_ATTR_DEFAULTS = {
    "SHORT_NAME": "data0",
    "UNITS": "",
    "DTIME_UNITS": "hour",
    "LEVEL_TYPE": "ground",
    "TIME_TYPE": "UTC",
    "TIME_BOUNDS": [0, 0],
}
NIMM_LEVEL_TYPES = {
    "ground",
    "entire_atmosphere",
    "isobaric",
    "isoheight",
    "height_above_ground",
    "soil_layer",
    "model_level",
}
NIMM_DTIME_UNITS = {"hour", "minute", "second"}
NIMM_TIME_TYPES = {"UTC", "BJT"}
NIMM_GLOBAL_ATTRS_ENCODING_KEY = "_nimm_global_attrs"

__all__ = [
    "NIMM_DIMS",
    "NIMM_REQUIRED_COORDS",
    "NIMM_OPTIONAL_COORD_DEFAULTS",
    "NIMM_DATA_ATTR_DEFAULTS",
    "NIMM_LEVEL_TYPES",
    "NIMM_DTIME_UNITS",
    "NIMM_TIME_TYPES",
    "canonicalize_griddata_attrs",
    "set_griddata_global_attrs",
    "get_griddata_global_attrs",
    "validate_griddata_nimm",
    "standardize_griddata_nimm",
]

_LEGACY_ATTR_ALIASES = {
    "SHORT_NAME": ("short_name",),
    "UNITS": ("units",),
    "DTIME_UNITS": ("dtime_units", "dtime_type"),
    "LEVEL_TYPE": ("level_type",),
    "TIME_TYPE": ("time_type",),
    "TIME_BOUNDS": ("time_bounds",),
}
_LEGACY_ATTR_NAMES = {
    alias for aliases in _LEGACY_ATTR_ALIASES.values() for alias in aliases
} | {"model", "model_var"}


def _normalize_dtime_units(value):
    text = str(value).strip().lower()
    aliases = {
        "h": "hour",
        "hr": "hour",
        "hours": "hour",
        "m": "minute",
        "min": "minute",
        "minutes": "minute",
        "s": "second",
        "sec": "second",
        "seconds": "second",
    }
    return aliases.get(text, text)


def _normalize_time_type(value):
    text = str(value).strip().upper()
    return {"UT": "UTC", "BT": "BJT"}.get(text, text)


def _normalize_level_type(value):
    text = str(value).strip().lower()
    return {
        "surface": "ground",
        "altitude": "isoheight",
        "attitude": "isoheight",
    }.get(text, text)


def _normalize_time_bounds(value):
    values = np.asarray(value).reshape(-1)
    if values.size != 2:
        return value
    if not np.issubdtype(values.dtype, np.number):
        try:
            values = values.astype(np.float64)
        except (TypeError, ValueError):
            return value
    if np.all(np.equal(values, np.rint(values))):
        return np.asarray(values, dtype=np.int32)
    return np.asarray(values, dtype=np.float64)


def canonicalize_griddata_attrs(grd, fill_defaults=True, drop_legacy=True):
    """Normalize NIMM data-variable attributes in place and return *grd*.

    Historical lower-case names are accepted as read aliases.  Canonical NIMM
    names are always upper-case.  Explicit canonical values win over aliases.
    ``model``/``model_var`` are not guessed as ``SHORT_NAME`` because their
    historical meaning mixes data source and element semantics.
    """

    attrs = dict(grd.attrs)
    canonical = {}
    for name, default in NIMM_DATA_ATTR_DEFAULTS.items():
        if name in attrs:
            value = attrs[name]
        else:
            value = None
            for alias in _LEGACY_ATTR_ALIASES[name]:
                if alias in attrs:
                    value = attrs[alias]
                    break
            if value is None and fill_defaults:
                value = deepcopy(default)
        if value is not None:
            canonical[name] = value

    if "DTIME_UNITS" in canonical:
        canonical["DTIME_UNITS"] = _normalize_dtime_units(
            canonical["DTIME_UNITS"]
        )
    if "TIME_TYPE" in canonical:
        canonical["TIME_TYPE"] = _normalize_time_type(canonical["TIME_TYPE"])
    if "LEVEL_TYPE" in canonical:
        canonical["LEVEL_TYPE"] = _normalize_level_type(
            canonical["LEVEL_TYPE"]
        )
    if "TIME_BOUNDS" in canonical:
        canonical["TIME_BOUNDS"] = _normalize_time_bounds(
            canonical["TIME_BOUNDS"]
        )

    if drop_legacy:
        attrs = {key: value for key, value in attrs.items() if key not in _LEGACY_ATTR_NAMES}
    attrs.update(canonical)
    grd.attrs = attrs
    return grd


def set_griddata_global_attrs(grd, attrs=None, **kwargs):
    """Attach logical NetCDF global attributes to a DataArray.

    A DataArray has no dataset-level attribute namespace.  The mapping is kept
    under a private in-memory encoding key and is moved to ``Dataset.attrs`` by
    ``write_griddata_to_nc``.  It is never serialized as a data-variable
    attribute.
    """

    merged = get_griddata_global_attrs(grd)
    if attrs:
        merged.update(dict(attrs))
    merged.update({key: value for key, value in kwargs.items() if value is not None})
    grd.encoding[NIMM_GLOBAL_ATTRS_ENCODING_KEY] = merged
    return grd


def get_griddata_global_attrs(grd):
    """Return a defensive copy of logical NetCDF global attributes."""

    return deepcopy(grd.encoding.get(NIMM_GLOBAL_ATTRS_ENCODING_KEY, {}))


def _append_issue(issues, item, message, suggestion):
    issues.append(
        {
            "item": item,
            "severity": "error",
            "message": message,
            "impact": "the object cannot be treated as NIMM v1.0 compliant",
            "suggestion": suggestion,
        }
    )


def _strictly_increasing(values):
    if len(values) < 2:
        return True
    return bool(np.all(np.diff(values) > 0))


def _regular(values, atol=1e-10):
    if len(values) < 3:
        return True
    differences = np.diff(values.astype(np.float64))
    return bool(np.allclose(differences, differences[0], rtol=1e-7, atol=atol))


def validate_griddata_nimm(grd, raise_error=False):
    """Validate an in-memory grid against the NIMM v1.0 grid contract.

    The result uses plain-language issue records (item, message, impact and
    suggested handling) rather than stable numeric error codes, matching the
    standard's reporting guidance.
    """

    issues = []
    if not isinstance(grd, xr.DataArray):
        _append_issue(
            issues,
            "data object",
            "grid data is not an xarray.DataArray",
            "convert the input to a DataArray before validation",
        )
    else:
        if grd.name != "data0":
            _append_issue(
                issues,
                "variable name",
                "the only data variable must be named data0",
                "rename the DataArray to data0",
            )
        if tuple(grd.dims) != NIMM_DIMS:
            _append_issue(
                issues,
                "dimensions",
                "dimension names or order do not match the fixed six dimensions",
                "transpose to member, level, time, dtime, lat, lon",
            )
        for name in grd.dims:
            if grd.sizes[name] == 0:
                _append_issue(
                    issues,
                    f"dimension {name}",
                    f"dimension {name} is empty",
                    "provide at least one coordinate value on every dimension",
                )
        if np.dtype(grd.dtype) != np.dtype("float32"):
            _append_issue(
                issues,
                "data dtype",
                f"data0 dtype is {grd.dtype}, expected float32",
                "decode packing and convert data0 to np.float32",
            )

        expected_coordinate_dtypes = {
            "level": np.dtype("float32"),
            "dtime": np.dtype("int32"),
            "lat": np.dtype("float64"),
            "lon": np.dtype("float64"),
        }
        for name in NIMM_DIMS:
            if name not in grd.coords:
                _append_issue(
                    issues,
                    f"coordinate {name}",
                    f"coordinate {name} is missing",
                    "provide the coordinate or apply an allowed NIMM default",
                )
                continue
            if tuple(grd.coords[name].dims) != (name,):
                _append_issue(
                    issues,
                    f"coordinate {name}",
                    f"coordinate {name} is not one-dimensional on its own axis",
                    "convert it to a one-dimensional coordinate",
                )
            if name in expected_coordinate_dtypes:
                actual = np.dtype(grd.coords[name].dtype)
                if actual != expected_coordinate_dtypes[name]:
                    _append_issue(
                        issues,
                        f"coordinate {name} dtype",
                        f"{name} dtype is {actual}, expected {expected_coordinate_dtypes[name]}",
                        "convert the coordinate to the required dtype",
                    )

        if "member" in grd.coords:
            members = np.asarray(grd.member.values)
            if not all(isinstance(value, str) for value in members.tolist()):
                _append_issue(
                    issues,
                    "member dtype",
                    "member values are not strings",
                    "convert every member label to str",
                )
        if "time" in grd.coords and not np.issubdtype(grd.time.dtype, np.datetime64):
            _append_issue(
                issues,
                "time dtype",
                f"time dtype {grd.time.dtype} is not a decoded datetime64 type",
                "decode CF time before entering the in-memory NIMM model",
            )
        elif "time" in grd.coords and np.any(np.isnat(grd.time.values)):
            _append_issue(
                issues,
                "time values",
                "time contains NaT",
                "provide a valid timestamp for every time coordinate",
            )

        for name in ("level", "dtime", "lat", "lon"):
            if name in grd.coords:
                values = np.asarray(grd.coords[name].values)
                if not np.all(np.isfinite(values)):
                    _append_issue(
                        issues,
                        f"coordinate {name} values",
                        f"coordinate {name} contains a non-finite value",
                        "replace NaN or infinity with valid coordinate values",
                    )

        for name in ("level", "time", "dtime", "lat", "lon"):
            if name in grd.coords and len(grd.coords[name]) > 1:
                values = np.asarray(grd.coords[name].values)
                if not _strictly_increasing(values):
                    _append_issue(
                        issues,
                        f"coordinate {name} order",
                        f"{name} is not strictly ascending",
                        "sort the coordinate and reorder data0 on the same axis",
                    )
        if "lat" in grd.coords:
            lat = np.asarray(grd.lat.values, dtype=np.float64)
            if np.any((lat < -90.0) | (lat > 90.0)):
                _append_issue(
                    issues,
                    "latitude range",
                    "latitude values fall outside [-90, 90]",
                    "correct the latitude coordinate",
                )
            if not _regular(lat):
                _append_issue(
                    issues,
                    "latitude spacing",
                    "latitude is not regularly spaced",
                    "regrid to a regular latitude axis",
                )
        if "lon" in grd.coords:
            lon = np.asarray(grd.lon.values, dtype=np.float64)
            if np.any((lon < 0.0) | (lon >= 360.0)):
                _append_issue(
                    issues,
                    "longitude range",
                    "longitude values fall outside [0, 360)",
                    "normalize longitude with lon % 360 and reorder data0",
                )
            if not _regular(lon):
                _append_issue(
                    issues,
                    "longitude spacing",
                    "longitude is not regularly spaced",
                    "regrid to a regular longitude axis",
                )

        for name in NIMM_DATA_ATTR_DEFAULTS:
            if name not in grd.attrs or grd.attrs[name] is None:
                _append_issue(
                    issues,
                    f"attribute {name}",
                    f"required data attribute {name} is missing or null",
                    "provide an explicit value or apply the documented default",
                )

        dtime_units = grd.attrs.get("DTIME_UNITS")
        if dtime_units is not None and dtime_units not in NIMM_DTIME_UNITS:
            _append_issue(
                issues,
                "DTIME_UNITS",
                f"unsupported DTIME_UNITS={dtime_units!r}",
                "use hour, minute or second",
            )
        level_type = grd.attrs.get("LEVEL_TYPE")
        if level_type is not None and level_type not in NIMM_LEVEL_TYPES:
            _append_issue(
                issues,
                "LEVEL_TYPE",
                f"unsupported LEVEL_TYPE={level_type!r}",
                "use a value from the NIMM LEVEL_TYPE table",
            )
        time_type = grd.attrs.get("TIME_TYPE")
        if time_type is not None and time_type not in NIMM_TIME_TYPES:
            _append_issue(
                issues,
                "TIME_TYPE",
                f"unsupported TIME_TYPE={time_type!r}",
                "use UTC or BJT",
            )
        bounds = grd.attrs.get("TIME_BOUNDS")
        if bounds is None:
            pass
        else:
            values = np.asarray(bounds).reshape(-1)
            if (
                values.size != 2
                or not np.issubdtype(values.dtype, np.number)
                or not np.all(np.isfinite(values))
                or values[0] > values[1]
            ):
                _append_issue(
                    issues,
                    "TIME_BOUNDS",
                    "TIME_BOUNDS must be a finite numeric pair with start <= end",
                    "provide [start, end] in DTIME_UNITS",
                )
        if level_type in {"ground", "entire_atmosphere"} and "level" in grd.coords:
            if not np.allclose(grd.level.values, 0.0):
                _append_issue(
                    issues,
                    "LEVEL_TYPE and level",
                    f"LEVEL_TYPE={level_type} requires level=[0.0]",
                    "correct LEVEL_TYPE or the level coordinate",
                )

        short_name = grd.attrs.get("SHORT_NAME")
        if short_name is not None and not isinstance(short_name, (str, list, tuple, np.ndarray)):
            _append_issue(
                issues,
                "SHORT_NAME",
                "SHORT_NAME must be a string or a sequence of strings",
                "provide an element short name aligned with member",
            )
        if isinstance(short_name, (list, tuple, np.ndarray)) and "member" in grd.coords:
            if len(short_name) != len(grd.member):
                _append_issue(
                    issues,
                    "SHORT_NAME and member",
                    "SHORT_NAME list length does not match member length",
                    "align the SHORT_NAME sequence with member order",
                )
            elif not all(isinstance(value, str) for value in np.asarray(short_name).tolist()):
                _append_issue(
                    issues,
                    "SHORT_NAME",
                    "SHORT_NAME sequence contains a non-string value",
                    "convert every element short name to str",
                )

        global_attrs = get_griddata_global_attrs(grd)
        if str(global_attrs.get("PRODUCT_TYPE", "")).lower() == "observation":
            if "dtime" in grd.coords and not np.all(grd.dtime.values == 0):
                _append_issue(
                    issues,
                    "observation dtime",
                    "observation products require dtime=[0]",
                    "set dtime to zero or correct PRODUCT_TYPE",
                )

    report = {
        "valid": not issues,
        "issues": issues,
        "summary": "PASS" if not issues else f"FAIL ({len(issues)} issue(s))",
    }
    if raise_error and issues:
        details = "; ".join(issue["message"] for issue in issues)
        raise ValueError(f"NIMM grid-data validation failed: {details}")
    return report


def standardize_griddata_nimm(
    grd,
    fill_defaults=True,
    normalize_longitude=True,
    sort_coordinates=True,
    strict=True,
    copy=True,
):
    """Return a NIMM-normalized six-dimensional float32 DataArray.

    Only member, level and dtime may be synthesized.  time, lat and lon must
    exist.  Coordinate sorting and longitude normalization always reorder
    ``data0`` through xarray indexing, preventing coordinate/data misalignment.
    """

    if not isinstance(grd, xr.DataArray):
        raise TypeError("grid data must be an xarray.DataArray")
    result = grd.copy(deep=True) if copy else grd
    global_attrs = get_griddata_global_attrs(result)

    for name in NIMM_REQUIRED_COORDS:
        if name not in result.dims or name not in result.coords:
            raise ValueError(f"required NIMM coordinate {name!r} is missing")
    extra_dims = [name for name in result.dims if name not in NIMM_DIMS]
    if extra_dims:
        raise ValueError(f"unsupported dimensions for NIMM grid data: {extra_dims}")
    for name, default in NIMM_OPTIONAL_COORD_DEFAULTS.items():
        if name not in result.dims:
            result = result.expand_dims({name: default})
        elif name not in result.coords:
            if result.sizes[name] != 1:
                raise ValueError(f"coordinate {name!r} is missing for a non-singleton axis")
            result = result.assign_coords({name: default})

    result = result.transpose(*NIMM_DIMS)
    result.name = "data0"

    result = result.assign_coords(
        member=np.asarray([str(value) for value in result.member.values], dtype=str),
        level=np.asarray(result.level.values, dtype=np.float32),
        time=pd.to_datetime(result.time.values).values.astype("datetime64[ns]"),
        lat=np.asarray(result.lat.values, dtype=np.float64),
        lon=np.asarray(result.lon.values, dtype=np.float64),
    )
    dtime_float = np.asarray(result.dtime.values, dtype=np.float64)
    if not np.all(np.isfinite(dtime_float)) or not np.allclose(
        dtime_float, np.rint(dtime_float)
    ):
        raise ValueError("dtime values must be finite integers")
    int32 = np.iinfo(np.int32)
    if np.any(dtime_float < int32.min) or np.any(dtime_float > int32.max):
        raise OverflowError("dtime values exceed int32 range")
    result = result.assign_coords(dtime=np.rint(dtime_float).astype(np.int32))

    if normalize_longitude:
        result = result.assign_coords(lon=np.mod(result.lon.values, 360.0))
    if sort_coordinates:
        for name in ("level", "time", "dtime", "lat", "lon"):
            if result.sizes[name] > 1:
                order = np.argsort(result.coords[name].values, kind="stable")
                result = result.isel({name: order})
    for name in ("level", "time", "dtime", "lat", "lon"):
        values = np.asarray(result.coords[name].values)
        if len(values) > 1 and not _strictly_increasing(values):
            raise ValueError(f"coordinate {name!r} contains duplicates or is not ascending")

    result = result.astype(np.float32)
    canonicalize_griddata_attrs(
        result, fill_defaults=fill_defaults, drop_legacy=True
    )
    result.member.attrs = {"long_name": "member"}
    result.level.attrs = {"long_name": "vertical_level"}
    result.time.attrs = {"axis": "T", "standard_name": "time"}
    result.dtime.attrs = {
        "long_name": "forecast_period",
        "units": result.attrs.get("DTIME_UNITS", "hour"),
    }
    result.lat.attrs = {
        "units": "degrees_north",
        "axis": "Y",
        "standard_name": "latitude",
    }
    result.lon.attrs = {
        "units": "degrees_east",
        "axis": "X",
        "standard_name": "longitude",
    }
    set_griddata_global_attrs(result, global_attrs)
    if strict:
        validate_griddata_nimm(result, raise_error=True)
    return result
