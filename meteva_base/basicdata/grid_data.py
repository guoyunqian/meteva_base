#!/usr/bin/python3.6
# -*- coding:UTF-8 -*-
import xarray as xr
import numpy as np
import pandas as pd
import datetime
import copy
import meteva_base
from .nimm_grid import (
    NIMM_DATA_ATTR_DEFAULTS,
    canonicalize_griddata_attrs,
    get_griddata_global_attrs,
    set_griddata_global_attrs,
)

#返回一个DataArray，其维度信息和grid描述一致，数组里面的值为0.
def grid_data(grid,data=None):
    slon = grid.slon
    dlon = grid.dlon
    slat = grid.slat
    dlat = grid.dlat
    nlon = grid.nlon
    nlat = grid.nlat
    # 通过起始经纬度和格距计算经纬度格点数
    lon = np.arange(nlon) * dlon + slon
    lat = np.arange(nlat) * dlat + slat
    times = pd.DatetimeIndex(grid.gtime)
    ntime = len(times)
    # 根据timedelta的格式，算出ndt次数和gds时效列表

    ndt = len(grid.dtimes)
    gdt_list = grid.dtimes

    level_list = grid.levels
    nlevel_list = len(level_list)

    member_list = grid.members
    nmember = len(member_list)
    if data is None:
        data = np.zeros((nmember, nlevel_list, ntime, ndt, nlat, nlon))
    else:
        data = data.reshape(nmember, nlevel_list, ntime, ndt, nlat, nlon)

    grd = (xr.DataArray(data, coords={'member': member_list,'level': level_list,'time': times,'dtime':gdt_list,
                               'lat': lat, 'lon': lon},
                         dims=['member', 'level','time', 'dtime','lat', 'lon']))
    grd.name = "data0"
    ## 属性赋值
    set_griddata_attrs(
        grd,
        units=grid.units,
        short_name=getattr(grid, "short_name", None),
        model_var=getattr(grid, "model_var", None),
        dtime_units=grid.dtime_units,
        level_type=grid.level_type,
        time_type=grid.time_type,
        time_bounds=grid.time_bounds,
        is_default=True,
    )
    set_griddata_global_attrs(grd, getattr(grid, "global_attrs", {}))
    ## 坐标数据类型统一
    set_griddata_coords_dtype(grd)
    return grd


def set_griddata_coords(grd,name = None,gtime = None,dtime_list = None,level_list = None, member_list = None,
                        ):
    """
    设置xarray的coords的一些属性
    :param grd:初始化之后的xarry结构的多维格点网格
    :param level:层次，默认为None
    :param gtime：时间，默认为None
    :param dtime:时效，默认为None
    :param member：要素，默认为None
    如果level不为None，并且grd的level维度上size = 1，则将level方向的坐标统一设置为传入的参数level,time,dtime,member一样类似处理。
    :return:grd:返回一个设置好的coords的格点网格信息。
    """
    if name is not None:
        grd.name = name
    nmember = int(len(grd.coords.variables.get(grd.coords.dims[0])))
    nlevel = int(len(grd.coords.variables.get(grd.coords.dims[1])))
    ndtime = int(len(grd.coords.variables.get(grd.coords.dims[3])))
    if level_list != None:
        if len(level_list) == nlevel:
            grd.coords["level"] = level_list
        else:
            print("level_list长度和grid_data的level维度的长度不一致")
    if dtime_list != None:
        if len(dtime_list) == ndtime:
            grd.coords["dtime"] = dtime_list
        else:
            print("dtime_list长度和grid_data的dtime维度的长度不一致")
    if member_list != None:
        if len(member_list) == nmember:
            grd.coords["member"] = member_list
        else:
            print("member_list长度和grid_data的member维度的长度不一致")

    ntime = int(len(grd.coords.variables.get(grd.coords.dims[2])))
    if gtime is not None:
        #time_list 内的内容兼容datetime 和str两种格式
        if not isinstance(gtime, list): gtime = [gtime]
        if len(gtime) == 1:
            times = meteva_base.basicdata.utils.get_time_input_single(gtime)
        elif len(gtime) ==3 and isinstance(gtime[2],str) and len(gtime[2])<=5: 
            times = meteva_base.basicdata.utils.get_time_input_three(gtime)
        else:
            if isinstance(gtime[0], datetime.datetime):
                times = gtime
            else:
                times = [meteva_base.all_type_time_to_datetime(dt) for dt in gtime]
        times = pd.DatetimeIndex(times)
        if ntime == len(times):
            grd.coords["time"] = times
        else:
            print("gtime对应的时间序列长度和grid_data的time维度的长度不一致")
    set_griddata_coords_dtype(grd)
    return

def set_griddata_coords_dtype(da,member_type=str,
                            level_type=np.float32,
                            dtime_type=np.int32,
                            time_type=np.datetime64,
                            lat_type=np.float64,
                            lon_type=np.float64,
                            data_type = np.float32
                            ):
    try:
        da.coords['member']=da.coords['member'].astype(member_type)
        da.coords['level']=da.coords['level'].astype(level_type)
        da.coords['dtime']=da.coords['dtime'].astype(dtime_type)
        da.coords['time']=da.coords['time'].astype(time_type)
        da.coords['lat']=da.coords['lat'].astype(lat_type)
        da.coords['lon']=da.coords['lon'].astype(lon_type)
        da.data = da.data.astype(data_type)
    except Exception as ex:
        print(ex)
    return None

def reset(grd):
    """
    重置 grd：
    1. lat/lon 若递减则翻转坐标并同步翻转数据
    2. 强制维度顺序 [member, level, time, dtime, lat, lon]
    返回重置后的 DataArray；维度转置时 xarray 会返回新对象。
    """
    # 1. lat/lon 翻转必须同步翻转 data0。单格点轴无需访问索引 1。
    if "lat" in grd.coords and grd.sizes.get("lat", 0) > 1:
        lats = np.asarray(grd["lat"].values)
        if lats[0] > lats[1]:
            lat_axis = grd.get_axis_num("lat")
            grd.data = np.flip(np.asarray(grd.data), axis=lat_axis).copy()
            grd.coords["lat"] = lats[::-1]

    if "lon" in grd.coords and grd.sizes.get("lon", 0) > 1:
        lons = np.asarray(grd["lon"].values)
        if lons[0] > lons[1]:
            lon_axis = grd.get_axis_num("lon")
            grd.data = np.flip(np.asarray(grd.data), axis=lon_axis).copy()
            grd.coords["lon"] = lons[::-1]

    # 2. xarray 不能可靠地就地改变维度定义；返回转置后的对象供新代码使用。
    target_order = ["member", "level", "time", "dtime", "lat", "lon"]
    current_dims = list(grd.dims)
    order = [d for d in target_order if d in current_dims]
    if len(order) < len(current_dims):
        order += [d for d in current_dims if d not in order]
    if order != current_dims:
        return grd.transpose(*order)
    return grd


def get_griddata_attrs(da,
              default_units='',
              default_model='',
              default_dtime_units='hour',
              default_level_type='ground',
              default_time_type='UTC',
              default_time_bounds=None):
    """Return the historical six-value tuple from canonical NIMM attributes.

    ``model`` in the old tuple is mapped to ``SHORT_NAME``.  New code should
    read ``da.attrs`` directly or use ``canonicalize_griddata_attrs``.
    """

    if default_time_bounds is None:
        default_time_bounds = [0, 0]
    attrs = da.attrs
    units = str(attrs.get("UNITS", attrs.get("units", default_units)))
    model = str(
        attrs.get(
            "SHORT_NAME",
            attrs.get("short_name", attrs.get("model", attrs.get("model_var", default_model))),
        )
    )
    dtime_units = str(
        attrs.get("DTIME_UNITS", attrs.get("dtime_units", default_dtime_units))
    )
    level_type = str(
        attrs.get("LEVEL_TYPE", attrs.get("level_type", default_level_type))
    )
    time_type = str(attrs.get("TIME_TYPE", attrs.get("time_type", default_time_type)))
    time_bounds = list(
        np.asarray(
            attrs.get("TIME_BOUNDS", attrs.get("time_bounds", default_time_bounds))
        ).reshape(-1)
    )
    return units, model, dtime_units, level_type, time_type, time_bounds

def set_griddata_attrs(grd, units = None, model_var = None, dtime_units =None,
            level_type=None ,time_type=None , time_bounds=None,
            is_default=False,
            default_attr=None,
            short_name=None,
            global_attrs=None,
            ):
    """Set the six canonical NIMM data attributes.

    ``model_var`` is retained as a deprecated input alias for ``short_name``.
    Global NetCDF attributes are stored separately via
    ``set_griddata_global_attrs``.
    """

    if default_attr is None:
        default_attr = NIMM_DATA_ATTR_DEFAULTS
    if short_name is None and model_var not in (None, ""):
        short_name = model_var
    supplied = {
        "SHORT_NAME": short_name,
        "UNITS": units,
        "DTIME_UNITS": dtime_units,
        "LEVEL_TYPE": level_type,
        "TIME_TYPE": time_type,
        "TIME_BOUNDS": time_bounds,
    }
    for name, value in supplied.items():
        if value is not None:
            grd.attrs[name] = value
        elif is_default and name not in grd.attrs:
            if name in default_attr:
                grd.attrs[name] = copy.deepcopy(default_attr[name])
            else:
                legacy_name = {
                    "SHORT_NAME": "model_var",
                    "UNITS": "units",
                    "DTIME_UNITS": "dtime_units",
                    "LEVEL_TYPE": "level_type",
                    "TIME_TYPE": "time_type",
                    "TIME_BOUNDS": "time_bounds",
                }[name]
                if legacy_name in default_attr:
                    grd.attrs[name] = copy.deepcopy(default_attr[legacy_name])
    canonicalize_griddata_attrs(grd, fill_defaults=is_default, drop_legacy=True)
    if global_attrs:
        set_griddata_global_attrs(grd, global_attrs)
    return None



def set_griddata_attrs_same(grd, grd0):
    source = grd0.copy(deep=False)
    canonicalize_griddata_attrs(source, fill_defaults=True, drop_legacy=True)
    grd.attrs.update(copy.deepcopy(source.attrs))
    set_griddata_global_attrs(grd, get_griddata_global_attrs(grd0))
    return None
    

def xarray_to_griddata(xr0,
                       value_name=None, member_dim=None, level_dim=None, time_dim=None, dtime_dim=None, lat_dim=None,
                       lon_dim=None
                       ):
    da = None
    if isinstance(xr0,xr.DataArray):
        ds0 = xr.Dataset({'data0': xr0})
    else:
        if value_name is not None:
            da = xr0[value_name]
            ds0 = xr.Dataset({'data0': da})
            name = value_name
        else:
            ds0 = xr0


    if dtime_dim == "time":
        ds0 = ds0.rename_dims({"time": "dtime"})
        dtime_dim = "dtime"

    if time_dim == "dtime":
        ds0 = ds0.rename_dims({"dtime": "time"})
        time_dim = "time"

    drop_list = []
    ds = xr.Dataset()
    # 1判断要素成员member
    if (member_dim is None):
        member_dim = "member"
    if member_dim in list(ds0.coords) or member_dim in list(ds0.dims):
        if member_dim in ds0.coords:
            members = ds0.coords[member_dim]
        else:
            members = ds0[member_dim]
            drop_list.append(member_dim)
        if len(members.dims) ==0:
            members = [members.values]
            ds.coords["member"] = ("member", members)
        else:
            ds.coords["member"] = ("member", members.values)
            attrs_name = list(members.attrs)
            for key in attrs_name:
                ds.member.attrs[key] = members.attrs[key]
    else:
        ds.coords["member"] = ("member", [0])

    # 2判断层次level
    if (level_dim is None):
        if "level" in list(ds0.coords) or "level" in list(ds0.dims):
            level_dim = "level"
        elif "lev" in ds0.coords or "lev" in list(ds0.dims):
            level_dim = "lev"
    if level_dim in ds0.coords or level_dim in list(ds0.dims):
        if level_dim in ds0.coords:
            levels = ds0.coords[level_dim]
        else:
            levels = ds0[level_dim]
            drop_list.append(level_dim)

        if len(levels.dims) == 0:
            levels = [levels.values]
            ds.coords["level"] = ("level", levels)
        else:
            ds.coords["level"] = ("level", levels.values)
            attrs_name = list(levels.attrs)
            for key in attrs_name:
                ds.level.attrs[key] = levels.attrs[key]
    else:
        ds.coords["level"] = ("level", [0])

    # 3判断时间time
    if (time_dim is None):
        if "time" in ds0.coords or "time" in list(ds0.dims):
            time_dim = "time"


    if time_dim in ds0.coords or time_dim in list(ds0.dims):
        if time_dim in ds0.coords:
            times = ds0.coords[time_dim]
        else:
            times = ds0[time_dim]

        if len(times.dims) == 0:
            times = [times.values]
            ds.coords["time"] = ("time", times)
        else:

            # datetimeindex = times.indexes['time'].to_datetimeindex() 将cftime.DatetimeJulian 转换成普通的时间

            ds.coords["time"] = ("time", times.values)
            attrs_name = list(times.attrs)
            for key in attrs_name:
                ds.time.attrs[key] = times.attrs[key]
    else:
        ds.coords["time"] = ("time", [0])

    # 4判断时效dt
    dtime_dim0 = dtime_dim

    if dtime_dim is None:
        if "dtime" in ds0.coords or "dtime" in list(ds0.dims):
            dtime_dim = "dtime"
        elif "valid_time" in ds0.coords or "valid_time" in list(ds0.dims):
            dtime_dim = "valid_time"
    if dtime_dim in ds0.coords or dtime_dim in list(ds0.dims):
        if dtime_dim in ds0.coords:
            dts = ds0.coords[dtime_dim]
        else:
            dts = ds0[dtime_dim]
            drop_list.append(dtime_dim)

        if len(dts.dims) == 0:
            dts = [dts.values]
            ds.coords["dtime"] = ("dtime", dts)
        else:
            ds.coords["dtime"] = ("dtime", dts.values)
            attrs_name = list(dts.attrs)
            for key in attrs_name:
                ds.dtime.attrs[key] = dts.attrs[key]
    else:
        ds.coords["dtime"] = ("dtime", [0])

    # 5判断纬度lat
    if (lat_dim is None):
        if "latitude" in ds0.coords or "latitude" in list(ds0.dims):
            lat_dim = "latitude"
        elif "lat" in ds0.coords or "lat" in list(ds0.dims):
            lat_dim = "lat"
    if lat_dim in ds0.coords or lat_dim in list(ds0.dims):
        if lat_dim in ds0.coords:
            lats = ds0.coords[lat_dim]
        else:
            lats = ds0[lat_dim]
            drop_list.append(lat_dim)
        dims = lats.dims
        if len(dims) == 1:
            ds.coords["lat"] = ("lat", lats.values)
        else:
            if "lon" in dims[0].lower() or "x" in dims.lower():
                lats = lats.values.T
            ds.coords["lat"] = (("lat", "lon"), lats.values)
        attrs_name = list(lats.attrs)
        for key in attrs_name:
            ds.lat.attrs[key] = lats.attrs[key]
    else:
        ds.coords["lat"] = ("lat", [0])

    # 6判断经度lon
    if (lon_dim is None):
        if "longitude" in ds0.coords or "longitude" in list(ds0.dims):
            lon_dim = "longitude"
        elif "lon" in ds0.coords or "lon" in list(ds0.dims):
            lon_dim = "lon"
    if lon_dim in ds0.coords or lon_dim in list(ds0.dims):
        if lon_dim in ds0.coords:
            lons = ds0.coords[lon_dim]
        else:
            lons = ds0[lon_dim]
            # print(lons)
            drop_list.append(lon_dim)

        dims = lons.dims
        if len(dims) == 1:
            ds.coords["lon"] = ("lon", lons.values)
        else:
            if "lon" in dims[0].lower() or "x" in dims.lower():
                lons = lons.values.T
            ds.coords["lon"] = (("lat", "lon"), lons.values)
        attrs_name = list(lons.attrs)
        for key in attrs_name:
            ds.lon.attrs[key] = lons.attrs[key]
    else:
        ds.coords["lon"] = ("lon", [0])



    if da is None:
        name_list = list((ds0))
        for name in name_list:
            if name in drop_list: continue
            #print(ds0)
            da = ds0[name]
            shape = da.values.shape
            size = 1
            for i in range(len(shape)):
                size = size * shape[i]
            if size > 1:
                break

    dims = da.dims
    dim_order = {}

    for dim in dims:
        if member_dim == dim:
            dim_order["member"] = dim
        elif level_dim == dim:
            dim_order["level"] = dim
        elif time_dim == dim:
            dim_order["time"] = dim
        elif dtime_dim == dim:
            dim_order["dtime"] = dim
        elif lon_dim == dim:
            dim_order["lon"] = dim
        elif lat_dim == dim:
            dim_order["lat"] = dim
    for dim in dims:
        if "member" not in dim_order.keys() and "member" in dim.lower():
            dim_order["member"] = dim
        elif "time" not in dim_order.keys() and dim.lower().find("time") == 0:
            dim_order["time"] = dim
        elif "dtime" not in dim_order.keys() and dim.lower().find("dt") == 0:
            dim_order["dtime"] = dim
        elif "level" not in dim_order.keys() and dim.lower().find("lev") == 0:
            dim_order["level"] = dim
        elif "lat" not in dim_order.keys() and (dim.lower().find("lat") == 0 or 'y' == dim.lower()):
            dim_order["lat"] = dim
        elif "lon" not in dim_order.keys() and (dim.lower().find("lon") == 0 or 'x' == dim.lower()):
            dim_order["lon"] = dim

    if "member" not in dim_order.keys():
        #print(da)
        dim_order["member"] = "member"
        da = da.expand_dims("member")
        da = da.copy()
    if "time" not in dim_order.keys():
        dim_order["time"] = "time"
        da = da.expand_dims("time")
        da = da.copy()
    if "level" not in dim_order.keys():
        dim_order["level"] = "level"
        da = da.expand_dims("level")
        da = da.copy()
    if "dtime" not in dim_order.keys():
        dim_order["dtime"] = "dtime"
        da = da.expand_dims("dtime")
        da = da.copy()
    if "lat" not in dim_order.keys():
        dim_order["lat"] = "lat"
        da = da.expand_dims("lat")
        da = da.copy()
    if "lon" not in dim_order.keys():
        dim_order["lon"] = "lon"
        da = da.expand_dims("lon")
        da = da.copy()
    da = da.transpose(dim_order["member"], dim_order["level"], dim_order["time"],
                      dim_order["dtime"], dim_order["lat"], dim_order["lon"])

    #print(da)
    ds[name] = (("member", "level", "time", "dtime", "lat", "lon"), da.values)
    attrs_name = list(da.attrs)
    for key in attrs_name:
        ds[name].attrs[key] = da.attrs[key]
    attrs_name = list(ds0.attrs)
    for key in attrs_name:
        ds.attrs[key] = ds0.attrs[key]

    ds0.close()
    da1 = ds[name]

    #da1.name = "data0"
    if da1.coords["time"] is None:
        da1.coords['time'] = pd.date_range("2099-1-1", periods=1)
    else:
        time_dim_value = da1.coords["time"].values
        if len(time_dim_value) == 1:
            if pd.isnull(time_dim_value):
                da1.coords['time'] = pd.date_range("2099-1-1", periods=1)

    if da1.coords["dtime"] is None:
        da1.coords["dtime"] = [0]
    else:
        level_dim_value = da1.coords["dtime"].values
        if len(level_dim_value) == 1:
            if pd.isnull(level_dim_value):
                da1.coords["dtime"] = [0]

    if da1.coords["level"] is None:
        da1.coords["level"] = [0]
    else:
        level_dim_value = da1.coords["level"].values
        if len(level_dim_value) == 1:
            if pd.isnull(level_dim_value):
                da1.coords["level"] = [0]

    if isinstance(da1.coords["dtime"].values[0], np.timedelta64):
        dtime_int_m = (da1.coords["dtime"] / np.timedelta64(1, 'm'))
        dtime_int_dm = dtime_int_m % 60
        maxdm = np.max(dtime_int_dm)
        if maxdm == 0:
            # print(dtime_int)
            da1.coords["dtime"] = (dtime_int_m / 60).astype(np.int16)
        else:
            da1.coords["dtime"] = (dtime_int_m ).astype(np.int16)

    attrs_name = list(da1.attrs)
    if "dtime_type" in attrs_name:
        da1.attrs["dtime_type"] = "hour"

    da1 = reset(da1)
    lats = da1.lat.values
    dlats = lats[1:] - lats[:-1]
    if len(dlats) > 1 and np.max(np.abs(dlats)) > 0 and (
            np.max(dlats) - np.min(dlats)) / np.max(np.abs(dlats)) > 0.001:
        print("***")
        mindlats = np.min(dlats)
        nlat = int((lats[-1] - lats[0])/mindlats) + 2
        dlat = (lats[-1] - lats[0])/(nlat-1)
        lons = da1.lon.values
        dlon = (lons[-1] - lons[0])/(len(lons) - 1) if len(lons) > 1 else 1.0
        grid = meteva_base.grid([lons[0],lons[-1],dlon],[lats[0],lats[-1],dlat])
        da1 = meteva_base.interp_xg_linear(da1,grid)
    return da1



def DataArray_to_grd(dataArray,data_name='data0', member = None,level = None,time = None,dtime = None,lat = None,lon= None):
    da = copy.deepcopy(dataArray)
    dim_order = {}
    new_coods = {}

    if member is None:
        da  = da.expand_dims("member")
        dim_order["member"] = "member"
        new_coods["member"] = [0]
    elif type(member) == str:
        if member in da.coords:
            dim_order["member"] = member
            # new_coods["member"] = da.coords[member]
            new_coods["member"] = ("member", da.coords[member].values) 
        else:
            da = da.expand_dims("member")
            dim_order["member"] = "member"
            new_coods["member"] = [0]
    else:
        dim_order["member"] = member.dims[0]
        new_coods["member"] = member.values.tolist()

    if level is None:
        da = da.expand_dims("level")
        dim_order["level"] = "level"
        new_coods["level"] = [0]
    elif type(level) == str:
        if level in da.coords:
            dim_order["level"] = level
            new_coods["level"] = ("level", da.coords[level].values) 

        else:
            da = da.expand_dims("level")
            dim_order["level"] = "level"
            new_coods["level"] = [0]
    else:
        dim_order["level"] = level.dims[0]
        new_coods["level"] = level.values.tolist()


    if time is None:
        da = da.expand_dims("time")
        dim_order["time"] = "time"
        new_coods["time"] = pd.date_range("2099-1-1", periods=1)
    elif type(time) == str:
        if time in da.coords:
            dim_order["time"] = time
            new_coods["time"] = ("time", da.coords[time].values) 
        else:
            da = da.expand_dims("time")
            dim_order["time"] = "time"
            new_coods["time"] = pd.date_range("2099-1-1", periods=1)
    else:
        dim_order["time"] = time.dims[0]
        new_coods["time"] = time.values.tolist()

    if dtime is None:
        da = da.expand_dims("dtime")
        dim_order["dtime"] = "dtime"
        new_coods["dtime"] = [0]
    elif type(dtime) == str:
        if dtime in da.coords:
            dim_order["dtime"] = dtime
            new_coods["dtime"] = ("dtime", da.coords[dtime].values) 
        else:
            da = da.expand_dims("dtime")
            dim_order["dtime"] = "dtime"
            new_coods["dtime"] = [0]
    else:
        dim_order["level"] = dtime.dims[0]
        new_coods["dtime"] = dtime.values.tolist()

    if lat is None:
        da = da.expand_dims("lat")
        dim_order["lat"] = "lat"
        new_coods["lat"] = [0]
    elif type(lat) == str:
        if lat in da.coords:
            dim_order["lat"] = lat
            new_coods["lat"] = ("lat", da.coords[lat].values) 
        else:
            da = da.expand_dims("lat")
            dim_order["lat"] = "lat"
            new_coods["lat"] = [0]
    else:
        dim_order["lat"] = lat.dims[0]
        new_coods["lat"] = lat.values.tolist()

    if lon is None:
        da = da.expand_dims("lon")
        dim_order["lon"] = "lon"
        new_coods["lon"] = [0]
    elif type(lon) == str:
        if lon in da.coords:
            dim_order["lon"] = lon
            new_coods["lon"] = ("lon", da.coords[lon].values) 
        else:
            da = da.expand_dims("lon")
            dim_order["lon"] = "lon"
            new_coods["lon"] = [0]
    else:
        dim_order["lon"] = lon.dims[0]
        new_coods["lon"] = lon.values.tolist()
    da = da.transpose(dim_order["member"], dim_order["level"], dim_order["time"],
                      dim_order["dtime"], dim_order["lat"], dim_order["lon"])

    da = xr.DataArray(
        da.values, 
        coords=new_coods, 
        dims=["member","level","time","dtime","lat","lon"]
    )
    da.name = data_name
    set_griddata_attrs_same(da, dataArray)
    set_griddata_coords_dtype(da)
    reset(da)
    return da



if __name__ == "__main__":

    data0 = np.random.rand(2,5,3)
    data1 = np.ones((2,5,3))
    x = np.arange(110,115,1)
    y = np.arange(30,33,1)
    z = np.arange(1,3,1)
    da0 = xr.DataArray(data0, coords=[z,x,y], dims=['z','lon','lat']) 
    da1 = xr.DataArray(data1, coords=[z,x,y], dims=['z','x','y'])

    # grd0 = DataArray_to_grd(da0, lat='lat',lon='lon')
    # print(da0)
    # print(grd0)
    grd1 = DataArray_to_grd(da1, lat='y',lon='x',dtime='z',data_name='test')
    print(da1)
    print(grd1)







