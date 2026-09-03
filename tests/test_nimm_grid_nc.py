import tempfile
import unittest
from pathlib import Path

import netCDF4
import numpy as np
import xarray as xr

import meteva_base as meb


PROJECT_ROOT = Path(__file__).resolve().parents[3]
TEMPLATE_DIR = PROJECT_ROOT / "output" / "nc_templates"
TEMPLATES = (
    TEMPLATE_DIR / "NIMM_CMPAS_1h1km_APCP_2026053020.000_float32.nc",
    TEMPLATE_DIR / "NIMM_ECMWF_APCP_2026060300.024_float32.nc",
)
REQUIRED_ATTRS = tuple(meb.NIMM_DATA_ATTR_DEFAULTS)


def small_grid(values=None):
    if values is None:
        values = np.array(
            [1.234, np.nan, -2.345, 3.0], dtype=np.float32
        ).reshape(1, 1, 1, 1, 2, 2)
    da = xr.DataArray(
        values,
        dims=meb.NIMM_DIMS,
        coords={
            "member": ["deterministic"],
            "level": np.array([0], dtype=np.float32),
            "time": np.array(["2026-06-03T00:00:00"], dtype="datetime64[ns]"),
            "dtime": np.array([24], dtype=np.int32),
            "lat": np.array([30.0, 31.0], dtype=np.float64),
            "lon": np.array([110.0, 111.0], dtype=np.float64),
        },
        name="data0",
        attrs={
            "SHORT_NAME": "APCP",
            "UNITS": "mm",
            "DTIME_UNITS": "hour",
            "LEVEL_TYPE": "ground",
            "TIME_TYPE": "UTC",
            "TIME_BOUNDS": [-24, 0],
        },
    )
    meb.set_griddata_global_attrs(
        da,
        {
            "TITLE": "NIMM unit-test grid",
            "SOURCE": "synthetic",
            "PRODUCT_TYPE": "forecast",
        },
    )
    return da


class TestNimmNormalization(unittest.TestCase):
    def test_required_coordinate_cannot_be_synthesized(self):
        source = xr.DataArray(
            np.ones((2, 2), dtype=np.float32),
            dims=("lat", "lon"),
            coords={"lat": [0.0, 1.0], "lon": [100.0, 101.0]},
        )
        with self.assertRaisesRegex(ValueError, "time"):
            meb.standardize_griddata_nimm(source)

    def test_sort_and_longitude_normalization_keep_values_aligned(self):
        source = xr.DataArray(
            np.array([[10.0, 11.0], [20.0, 21.0]], dtype=np.float64),
            dims=("lat", "lon"),
            coords={
                "lat": np.array([1.0, 0.0]),
                "lon": np.array([-1.0, 0.0]),
                "time": np.datetime64("2026-01-01T00:00:00"),
            },
            attrs={"units": "mm", "short_name": "APCP"},
        ).expand_dims("time")
        normalized = meb.standardize_griddata_nimm(source)
        np.testing.assert_array_equal(normalized.lat.values, [0.0, 1.0])
        np.testing.assert_array_equal(normalized.lon.values, [0.0, 359.0])
        np.testing.assert_array_equal(
            normalized.values[0, 0, 0, 0],
            np.array([[21.0, 20.0], [11.0, 10.0]], dtype=np.float32),
        )
        self.assertEqual(normalized.attrs["UNITS"], "mm")
        self.assertEqual(normalized.attrs["SHORT_NAME"], "APCP")
        self.assertNotIn("units", normalized.attrs)

    def test_validator_reports_ground_level_conflict_with_impact(self):
        da = small_grid().assign_coords(level=np.array([850], dtype=np.float32))
        report = meb.validate_griddata_nimm(da)
        self.assertFalse(report["valid"])
        issue = next(item for item in report["issues"] if item["item"] == "LEVEL_TYPE and level")
        self.assertIn("impact", issue)
        self.assertIn("suggestion", issue)

    def test_global_attrs_are_separate_from_data_attrs(self):
        da = small_grid()
        globals_ = meb.get_griddata_global_attrs(da)
        self.assertEqual(globals_["SOURCE"], "synthetic")
        self.assertNotIn("SOURCE", da.attrs)


class TestNimmNetcdfIO(unittest.TestCase):
    def test_float32_templates_read_write_and_roundtrip(self):
        if not all(template.exists() for template in TEMPLATES):
            self.skipTest("external NIMM template fixtures are not available")
        for template in TEMPLATES:
            with self.subTest(template=template.name):
                source = meb.read_griddata_from_nc(str(template), raise_on_error=True)
                self.assertEqual(tuple(source.dims), meb.NIMM_DIMS)
                self.assertEqual(source.dtype, np.dtype("float32"))
                self.assertTrue(meb.validate_griddata_nimm(source)["valid"])
                self.assertTrue(all(name in source.attrs for name in REQUIRED_ATTRS))

                with tempfile.TemporaryDirectory() as directory:
                    target = Path(directory) / template.name
                    self.assertTrue(
                        meb.write_griddata_to_nc(
                            source,
                            str(target),
                            storage_type="float32",
                            roundtrip=True,
                            raise_on_error=True,
                        )
                    )
                    with netCDF4.Dataset(target) as dataset:
                        variable = dataset.variables["data0"]
                        self.assertEqual(variable.dtype, np.dtype("float32"))
                        self.assertEqual(variable.dimensions, meb.NIMM_DIMS)
                        self.assertEqual(float(variable._FillValue), 999999.0)
                        self.assertNotIn("scale_factor", variable.ncattrs())
                        self.assertNotIn("add_offset", variable.ncattrs())
                        self.assertTrue(all(name in variable.ncattrs() for name in REQUIRED_ATTRS))
                        self.assertEqual(dataset.variables["member"].dtype, str)
                        self.assertEqual(dataset.variables["level"].dtype, np.dtype("float32"))
                        self.assertEqual(dataset.variables["time"].dtype, np.dtype("float64"))
                        self.assertEqual(dataset.variables["dtime"].dtype, np.dtype("int32"))
                        self.assertEqual(dataset.variables["lat"].dtype, np.dtype("float64"))
                        self.assertEqual(dataset.variables["lon"].dtype, np.dtype("float64"))
                        self.assertTrue(variable.filters()["zlib"])
                        self.assertTrue(variable.filters()["shuffle"])
                        self.assertEqual(variable.filters()["complevel"], 4)

    def test_integer_storage_modes_and_default_compatibility(self):
        cases = (("int32", np.dtype("int32"), np.dtype("float64")),
                 ("int16", np.dtype("int16"), np.dtype("float32")),
                 (None, np.dtype("int32"), np.dtype("float64")))
        for mode, expected_dtype, expected_scale_dtype in cases:
            with self.subTest(storage_type=mode):
                with tempfile.TemporaryDirectory() as directory:
                    target = Path(directory) / "packed.nc"
                    meb.write_griddata_to_nc(
                        small_grid(),
                        str(target),
                        storage_type=mode,
                        effectiveNum=3,
                        roundtrip=True,
                        raise_on_error=True,
                    )
                    with netCDF4.Dataset(target) as dataset:
                        variable = dataset.variables["data0"]
                        self.assertEqual(variable.dtype, expected_dtype)
                        self.assertEqual(np.asarray(variable.scale_factor).dtype, expected_scale_dtype)
                        self.assertEqual(variable._FillValue, np.iinfo(expected_dtype).min)

    def test_int16_overflow_fails_before_write(self):
        values = np.full((1, 1, 1, 1, 2, 2), 1000.0, dtype=np.float32)
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "overflow.nc"
            with self.assertRaises(OverflowError):
                meb.write_griddata_to_nc(
                    small_grid(values),
                    str(target),
                    storage_type="int16",
                    effectiveNum=3,
                    raise_on_error=True,
                )

    def test_single_point_lat_lon_supported(self):
        da = small_grid().isel(lat=[0], lon=[0])
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "point.nc"
            meb.write_griddata_to_nc(
                da, str(target), storage_type="float32", raise_on_error=True
            )
            restored = meb.read_griddata_from_nc(str(target), raise_on_error=True)
            self.assertEqual(restored.shape, (1, 1, 1, 1, 1, 1))


if __name__ == "__main__":
    unittest.main()
