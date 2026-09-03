import numpy as np
import math
import meteva_base
import os
import traceback
import warnings
warnings.filterwarnings("ignore")


def write_griddata_to_micaps4(da, save_path="a.txt", creat_dir=False, effectiveNum=3, show=False, title=None, inte=None,
                              vmin=None, vmax=None):
    """
    输出micaps4格式文件
    :param da:xarray多维数据信息,需要用 meteva 的格式
    :param save_path:存储路径
    :param creat_dir:存储路径中的文件夹若不存在是否创建
    :param effectiveNum：有效数字，默认 3
    :param show:是否输出存储结果，默认否
    :param title:MICAPS4第四类格式的title，默认根据 save_path 自动生成
    :param inte:MICAPS4第四类格式的等值线间隔，默认根据数值自动生成
    :param vmin:MICAPS4第四类格式的等值线起始值，默认根据数值自动生成
    :param vmax:MICAPS4第四类格式的等值线终止值，默认根据数值自动生成
    :return 最终按照需要保存的路径，将da数据保存为m4格式
    """
    try:
        dir = os.path.split(os.path.abspath(save_path))[0]
        if not os.path.isdir(dir):
            if not creat_dir:
                print("文件夹：" + dir + "不存在")
                return False
            else:
                meteva_base.tool.path_tools.creat_path(save_path)

        grid = meteva_base.basicdata.get_grid_of_data(da)
        nlon = grid.nlon
        nlat = grid.nlat
        slon = grid.slon
        slat = grid.slat
        elon = grid.elon
        elat = grid.elat
        dlon = grid.dlon
        dlat = grid.dlat
        level = grid.levels[0]
        stime = grid.stime_str
        year = stime[0:4]
        month = stime[4:6]
        day = stime[6:8]
        hour = stime[8:10]
        hour_range = str(grid.dtimes[0])
        values = da.values
        grid_values = np.squeeze(values)
        if (vmax is None):
            vmax = math.ceil(max(grid_values.flatten()))
        if (vmin is None):
            vmin = math.ceil(min(grid_values.flatten()))

        if (inte is None):
            dif = (vmax - vmin) / 10.0
            if dif == 0:
                inte = 1
            else:
                inte = math.pow(10, math.floor(math.log10(dif)))
            # 用基本间隔，将最大最小值除于间隔后小数点部分去除，最后把间隔也整数化
            r = dif / inte
            if r < 3 and r >= 1.5:
                inte = inte * 2
            elif r < 4.5 and r >= 3:
                inte = inte * 4
            elif r < 5.5 and r >= 4.5:
                inte = inte * 5
            elif r < 7 and r >= 5.5:
                inte = inte * 6
            elif r >= 7:
                inte = inte * 8
            vmin = inte * ((int)(vmin / inte) - 1)
            vmax = inte * ((int)(vmax / inte) + 1)

        end = len(save_path)
        start = max(0, end - 16)

        if title is None:
            title = ("diamond 4 " + save_path[start:end] + "\n"
                     + year + " " + month + " " + day + " " + hour + " " + hour_range + " " + str(level) + "\n"
                     + "{:.5f}".format(grid.dlon) + " " + "{:.5f}".format(grid.dlat) + " " + "{:.5f}".format(
                        grid.slon) + " " + "{:.5f}".format(grid.elon) + " "
                     + "{:.5f}".format(grid.slat) + " " + "{:.5f}".format(grid.elat) + " " + str(grid.nlon) + " " + str(
                        grid.nlat) + " "
                     + str(inte) + " " + str(vmin) + " " + str(vmax) + " 1 0")
        else:

            title = ("diamond 4 " + title + "\n"
                     + year + " " + month + " " + day + " " + hour + " " + hour_range + " " + str(level) + "\n"
                     + "{:.5f}".format(grid.dlon) + " " + "{:.5f}".format(grid.dlat) + " " + "{:.5f}".format(
                        grid.slon) + " " + "{:.5f}".format(grid.elon) + " "
                     + "{:.5f}".format(grid.slat) + " " + "{:.5f}".format(grid.elat) + " " + str(grid.nlon) + " " + str(
                        grid.nlat) + " "
                     + str(inte) + " " + str(vmin) + " " + str(vmax) + " 1 0")

        # 二维数组写入micaps文件
        format_str = "%." + str(effectiveNum) + "f "

        np.savetxt(save_path, grid_values, delimiter=' ',
                   fmt=format_str, header=title, comments='', encoding='GBK')
        if show:
            print('成功输出至' + save_path)
        return True
    except:
        exstr = traceback.format_exc()
        print(exstr)
        return False

def _write_griddata_to_nc_legacy(da, save_path="a.txt", creat_dir=False, effectiveNum=3, show=False):
    try:
        dir = os.path.split(os.path.abspath(save_path))[0]
        if not os.path.isdir(dir):
            if not creat_dir:
                print("文件夹：" + dir + "不存在")
                return False
            else:
                meteva_base.tool.path_tools.creat_path(save_path)
        scale_factor = math.pow(10, -effectiveNum)
        # print(scale_factor)
        encodingdict = {da.name: {
            'dtype': 'int32',
            'scale_factor': scale_factor,
            'zlib': True,
            '_FillValue': None
        }
        }

        da.to_netcdf(save_path, encoding=encodingdict)
        if show:
            print('成功输出至' + save_path)
        return True
    except:
        exstr = traceback.format_exc()
        print(exstr)
        return False


def _check_integer_packing_range(da, dtype, scale_factor, add_offset, fill_value):
    """Fail before xarray casts values that cannot be represented safely."""

    limits = np.iinfo(np.dtype(dtype))
    valid_min = limits.min + 1 if fill_value == limits.min else limits.min
    valid_max = limits.max
    values = np.asarray(da.values, dtype=np.float32).reshape(-1)
    block_size = 1_000_000
    packed_min = None
    packed_max = None
    for start in range(0, values.size, block_size):
        block = values[start:start + block_size]
        finite = block[np.isfinite(block)].astype(np.float64)
        if finite.size == 0:
            continue
        packed = np.rint((finite - add_offset) / scale_factor)
        block_min = float(np.min(packed))
        block_max = float(np.max(packed))
        packed_min = block_min if packed_min is None else min(packed_min, block_min)
        packed_max = block_max if packed_max is None else max(packed_max, block_max)
        if block_min < valid_min or block_max > valid_max:
            raise OverflowError(
                f"packed values [{block_min}, {block_max}] exceed the safe "
                f"{np.dtype(dtype).name} range [{valid_min}, {valid_max}]"
            )
    return {"packed_min": packed_min, "packed_max": packed_max}


def _default_nimm_chunksizes(da):
    if any(da.sizes[name] < 1 for name in da.dims):
        raise ValueError("NIMM output cannot contain an empty dimension")
    return (
        1,
        1,
        1,
        1,
        min(512, da.sizes["lat"]),
        min(512, da.sizes["lon"]),
    )


def _verify_nimm_roundtrip(source, save_path, storage_type, scale_factor):
    restored = meteva_base.read_griddata_from_nc(
        save_path,
        nimm_standard=True,
        nimm_strict=True,
        raise_on_error=True,
    )
    if tuple(restored.dims) != tuple(source.dims) or restored.shape != source.shape:
        raise AssertionError("round-trip dimensions or shape changed")
    for name in ("member", "level", "time", "dtime", "lat", "lon"):
        left = np.asarray(source.coords[name].values)
        right = np.asarray(restored.coords[name].values)
        if name in ("member", "time"):
            equal = np.array_equal(left, right)
        else:
            equal = np.allclose(left, right, rtol=0, atol=1e-10)
        if not equal:
            raise AssertionError(f"round-trip coordinate {name} changed")

    source_values = np.asarray(source.values, dtype=np.float32)
    restored_values = np.asarray(restored.values, dtype=np.float32)
    source_missing = ~np.isfinite(source_values)
    restored_missing = ~np.isfinite(restored_values)
    if not np.array_equal(source_missing, restored_missing):
        raise AssertionError("round-trip missing-value positions changed")
    valid = ~(source_missing | restored_missing)
    maximum_error = 0.0
    if np.any(valid):
        maximum_error = float(
            np.max(
                np.abs(
                    source_values[valid].astype(np.float64)
                    - restored_values[valid].astype(np.float64)
                )
            )
        )
    if storage_type == "float32":
        max_value = float(np.max(np.abs(source_values[valid]))) if np.any(valid) else 1.0
        tolerance = float(np.finfo(np.float32).eps * max(1.0, max_value))
    else:
        tolerance = 0.5 * scale_factor + 1e-12
    if maximum_error > tolerance:
        raise AssertionError(
            f"round-trip maximum absolute error {maximum_error} exceeds {tolerance}"
        )
    for name in meteva_base.NIMM_DATA_ATTR_DEFAULTS:
        if name not in restored.attrs:
            raise AssertionError(f"round-trip lost required attribute {name}")
        left = np.asarray(source.attrs[name]).reshape(-1)
        right = np.asarray(restored.attrs[name]).reshape(-1)
        if left.dtype.kind in "iuf" and right.dtype.kind in "iuf":
            equal = np.allclose(left.astype(float), right.astype(float), rtol=0, atol=0)
        else:
            equal = np.array_equal(left.astype(str), right.astype(str))
        if not equal:
            raise AssertionError(f"round-trip attribute {name} changed")
    return {"maximum_absolute_error": maximum_error, "tolerance": tolerance}


def write_griddata_to_nc(
        da, save_path="a.nc", creat_dir=False, effectiveNum=3, show=False,
        storage_type=None, add_offset=0.0, global_attrs=None,
        zlib=True, complevel=4, shuffle=True, chunksizes=None,
        nimm_standard=True, nimm_strict=True, roundtrip=True,
        raise_on_error=False):
    """Write grid data using one of the NIMM v1.0 NetCDF storage modes.

    Parameters
    ----------
    storage_type : {"float32", "int32", "int16"}, optional
        ``None`` maps to ``int32`` for compatibility with the historical
        ``effectiveNum`` API.  New code should always select a mode explicitly.
    effectiveNum : int
        Decimal digits used only by integer packing.  Ignored for float32.
    roundtrip : bool
        Reopen and compare structure, coordinates, attributes, missing values
        and numeric error after writing.  Enabled by default for NIMM output.
    raise_on_error : bool
        Raise the original exception instead of returning ``False``.
    """

    if not nimm_standard:
        return _write_griddata_to_nc_legacy(
            da, save_path=save_path, creat_dir=creat_dir,
            effectiveNum=effectiveNum, show=show
        )
    try:
        directory = os.path.split(os.path.abspath(save_path))[0]
        if not os.path.isdir(directory):
            if not creat_dir:
                raise FileNotFoundError("文件夹：" + directory + "不存在")
            meteva_base.tool.path_tools.creat_path(save_path)

        mode = "int32" if storage_type is None else str(storage_type).lower()
        mode = {"f4": "float32", "i4": "int32", "i2": "int16"}.get(mode, mode)
        if mode not in {"float32", "int32", "int16"}:
            raise ValueError("storage_type must be float32, int32 or int16")

        normalized = meteva_base.standardize_griddata_nimm(
            da, fill_defaults=True, strict=nimm_strict, copy=True
        )
        logical_global_attrs = meteva_base.get_griddata_global_attrs(normalized)
        if global_attrs:
            logical_global_attrs.update(dict(global_attrs))
        logical_global_attrs.setdefault("CONVENTIONS", "CF-1.11, NIMM-v1.0")
        logical_global_attrs.setdefault("CRS", "WGS84")
        meteva_base.set_griddata_global_attrs(normalized, logical_global_attrs)

        if chunksizes is None:
            chunksizes = _default_nimm_chunksizes(normalized)
        else:
            chunksizes = tuple(int(value) for value in chunksizes)
            if len(chunksizes) != 6:
                raise ValueError("chunksizes must contain six integers")
            for size, dim in zip(chunksizes, normalized.dims):
                if size < 1 or size > normalized.sizes[dim]:
                    raise ValueError(f"invalid chunk size {size} for dimension {dim}")

        encoding = {
            "level": {"dtype": "float32", "_FillValue": None},
            "time": {
                "dtype": "float64",
                "units": "hours since 1970-01-01 00:00:00",
                "calendar": "standard",
                "_FillValue": None,
            },
            "dtime": {"dtype": "int32", "_FillValue": None},
            "lat": {"dtype": "float64", "_FillValue": None},
            "lon": {"dtype": "float64", "_FillValue": None},
        }
        common_encoding = {
            "zlib": bool(zlib),
            "complevel": int(complevel),
            "shuffle": bool(shuffle),
            "chunksizes": chunksizes,
        }
        scale_factor = None
        if mode == "float32":
            data_encoding = {
                "dtype": "float32",
                "_FillValue": np.float32(999999.0),
                **common_encoding,
            }
        else:
            if isinstance(effectiveNum, bool) or int(effectiveNum) != effectiveNum:
                raise ValueError("effectiveNum must be an integer")
            effectiveNum = int(effectiveNum)
            if effectiveNum < 0:
                raise ValueError("effectiveNum must be >= 0")
            scale_factor = float(math.pow(10, -effectiveNum))
            dtype = np.dtype(mode)
            fill_value = np.iinfo(dtype).min
            _check_integer_packing_range(
                normalized, dtype, scale_factor, float(add_offset), fill_value
            )
            packing_float = np.float64 if mode == "int32" else np.float32
            data_encoding = {
                "dtype": mode,
                "_FillValue": dtype.type(fill_value),
                "scale_factor": packing_float(scale_factor),
                "add_offset": packing_float(add_offset),
                **common_encoding,
            }
        encoding["data0"] = data_encoding

        dataset = normalized.to_dataset(name="data0")
        dataset.attrs = logical_global_attrs
        for variable in dataset.variables.values():
            variable.encoding = {}
        dataset.to_netcdf(
            save_path, mode="w", format="NETCDF4", engine="netcdf4",
            encoding=encoding
        )
        dataset.close()

        if roundtrip:
            _verify_nimm_roundtrip(normalized, save_path, mode, scale_factor)
        if show:
            print("成功输出至" + str(save_path))
        return True
    except Exception:
        if raise_on_error:
            raise
        print(traceback.format_exc())
        return False
def write_griddata_to_micaps11(wind, save_path="a.txt", creat_dir=False, effectiveNum=3, show=False, title=None):
    try:
        dir = os.path.split(os.path.abspath(save_path))[0]
        if not os.path.isdir(dir):
            if not creat_dir:
                print("文件夹：" + dir + "不存在")
                return False
            else:
                meteva_base.tool.path_tools.creat_path(save_path)
        grid0 = meteva_base.basicdata.get_grid_of_data(wind)
        nlon = grid0.nlon
        nlat = grid0.nlat
        slon = grid0.slon
        slat = grid0.slat
        elon = grid0.elon
        elat = grid0.elat
        dlon = grid0.dlon
        dlat = grid0.dlat
        level = grid0.levels[0]
        stime = grid0.stime_str
        year = stime[0:4]
        month = stime[4:6]
        day = stime[6:8]
        hour = stime[8:10]
        values = wind.values
        grid_values = np.squeeze(values).reshape(2 * nlat, nlon)

        end = len(save_path)
        start = max(0, end - 16)

        if title is None:
            title = ("diamond 11 " + save_path[start:end] + "\n"
                     + year + " " + month + " " + day + " " + hour + " " + str(level) + "\n"
                     + str(grid0.dlon) + " " + str(grid0.dlat) + " " + str(grid0.slon) + " " + str(grid0.elon) + " "
                     + str(grid0.slat) + " " + str(grid0.elat) + " " + str(grid0.nlon) + " " + str(grid0.nlat))
        else:

            title = ("diamond 11 " + title + "\n"
                     + year + " " + month + " " + day + " " + hour + " " + str(level) + "\n"
                     + str(grid0.dlon) + " " + str(grid0.dlat) + " " + str(grid0.slon) + " " + str(grid0.elon) + " "
                     + str(grid0.slat) + " " + str(grid0.elat) + " " + str(grid0.nlon) + " " + str(grid0.nlat))

        format_str = "%." + str(effectiveNum) + "f "

        np.savetxt(save_path, grid_values, delimiter=' ',
                   fmt=format_str, header=title, comments='')
        if show:
            print('成功输出至' + save_path)
        return True
    except:
        exstr = traceback.format_exc()
        print(exstr)
        return False

def tran_griddata_to_gds_flow(da):
    grid0 = meteva_base.get_grid_of_data(da)
    discriminator = b"mdfs"
    if len(grid0.members) == 1:
        data_type = 4
    elif len(grid0.members) == 2:
        data_type = 11
    else:
        print("仅支持micap4类和micaps11类数据输出成GDS格式")
    data_type_byte = np.ndarray.tobytes(np.array([data_type]).astype(np.int16))
    mName = grid0.members[0]
    mName = mName.encode(encoding='utf-8')
    if len(mName) < 20:
        mName = mName + np.ndarray.tobytes(np.zeros(20 - len(mName)).astype(np.int8))

    eleName = b""
    if "eleName" in da.attrs.keys():
        eleName = da.attrs["eleName"]
    if len(eleName) < 50:
        eleName = eleName + np.ndarray.tobytes(np.zeros(50 - len(eleName)).astype(np.int8))

    description = b""
    if "description" in da.attrs.keys():
        description = da.attrs["description"]
    if len(description) < 30:
        description = description + np.ndarray.tobytes(np.zeros(30 - len(description)).astype(np.int8))

    level = np.ndarray.tobytes(np.array(grid0.levels[0]).astype(np.float32))
    y_m_d_h_timezone_peroid = np.ndarray.tobytes(np.array([2021, 1, 1, 8, 8, 0]).astype(np.int32))
    slon_elon_dlon = np.ndarray.tobytes(np.array([grid0.slon, grid0.elon, grid0.dlon]).astype(np.float32))
    nlon = np.ndarray.tobytes(np.array([grid0.nlon]).astype(np.int32))
    slat_elat_dlat = np.ndarray.tobytes(np.array([grid0.slat, grid0.elat, grid0.dlat]).astype(np.float32))
    nlat = np.ndarray.tobytes(np.array([grid0.nlat]).astype(np.int32))
    vmin, vmax, inte = meteva_base.tool.plot_tools.get_isoline_set(da)
    sValue_eValue_dValue = np.ndarray.tobytes(np.array([vmin, vmax, inte]).astype(np.float32))
    blank = np.ndarray.tobytes(np.zeros(100).astype(np.int8))
    value_bytes = np.ndarray.tobytes(da.values.astype(np.float32))
    bytes1 = discriminator + data_type_byte + mName + eleName + description + level + y_m_d_h_timezone_peroid
    bytes2 = slon_elon_dlon + nlon + slat_elat_dlat + nlat + sValue_eValue_dValue + blank + value_bytes
    bytes = bytes1 + bytes2

    return bytes

def write_griddata_to_gds_file(da, save_path="a.txt", creat_dir=False, show=False):
    try:
        dir = os.path.split(os.path.abspath(save_path))[0]
        if not os.path.isdir(dir):
            if not creat_dir:
                print("文件夹：" + dir + "不存在")
                return False
            else:
                meteva_base.tool.path_tools.creat_path(save_path)

        bytes = tran_griddata_to_gds_flow(da)
        br = open(save_path, 'wb')
        br.write(bytes)
        br.close()
        if show:
            print('成功输出至' + save_path)
        return True
    except:
        exstr = traceback.format_exc()
        print(exstr)
        return False

if __name__ == "__main__":
    grd = meteva_base.read_griddata_from_micaps4(r"H:\test_data\input\meb\m4.txt")
    write_griddata_to_gds_file(grd, save_path=r"H:\test_data\output\meb\gds_test.000")
