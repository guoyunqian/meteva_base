# -*- coding: utf-8 -*-

import xarray as xr
import numpy as np
import pandas as pd
import datetime
import copy
import meteva_base

def check_for_meb_griddata(grd, is_single=False, valid_val=[-1000, 1000, np.NaN]):
    """
    检查grd是否为符合meteva_base规定的网格数据, 未通过检查raise ValueError
    is_single: 是否检查网格数据是否为单要素(lat,lon),默认为否
    valid_val: 网格数据合理值范围下限(valid_val[0])上限(valid_val[1])， 若超过进行提示，并将超过值替换为valid_val[2]
    return:  通过检查则返回经过坐标顺序及数据类型修订后的网格数据, 数据类型强制为np.float32； 
    """
    import xarray as xr
    import numpy as np
    if not isinstance(grd, xr.DataArray):
        msg = "ERROR: griddata must be xr.DataArray, please check"
        raise ValueError(msg)
    if set(grd.dims) != {'member', 'level', 'time', 'dtime', 'lat', 'lon'} :
        msg = "ERROR: griddata dims must be set of {'member', 'level', 'time', 'dtime', 'lat', 'lon'} , please check"
        raise ValueError(msg)
    if is_single:
        if len(grd.values.squeeze().shape)>2:
            msg = "ERROR: griddata has more effective coordinates than (lat, lon) , please check"
            raise ValueError(msg)
    grd0 = grd.copy()
    ## 维度顺序
    if grd0.dims != ('member', 'level', 'time', 'dtime', 'lat', 'lon'):#坐标transpose
        grd0 = grd0.transpose('member', 'level', 'time', 'dtime', 'lat', 'lon')
    ## 数据类型
    if grd0.values.dtype == np.float64:#强制数据为float32格式(后处理数据类型)
        grd0.values = grd0.values.astype(np.float32)
    ## 合理值
    if ((grd0.values<valid_val[0])|(grd0.values>valid_val[1])).any():
        msg = "WARNING: griddata values exceed VALID_VAL, setting to np.NaN"
        print(msg)
        grd0.values[(grd0.values<valid_val[0])|(grd0.values>valid_val[1])] = valid_val[2]
    ## 维度数据类型
    return grd0
    

def check_for_same_coordinates(grd_list = [], is_time_match=False):
    """
    检查网格数据列表中要素是否维度信息相同或匹配(时间维度)
    is_time_match: 是否需要时间维度也可以匹配(time+dtime)，默认为True
    return: 列表网格数据维度匹配，返回True; 否则返回False
    """
    ref = grd_list[0]
    match = True
    for grd in grd_list[1:]:
        if is_time_match is False:
            match = (
                (grd.member.values == ref.member.values ).all()
                and (grd.level.values  == ref.level.values ).all()
                and (grd.lat.values  == ref.lat.values ).all()
                and (grd.lon.values  == ref.lon.values ).all()
                and match
            )
        else:
            match = (
                (grd.member.values  == ref.member.values ).all()
                and (grd.level.values  == ref.level.values ).all()
                and (grd.lat.values  == ref.lat.values ).all()
                and (grd.lon.values  == ref.lon.values ).all()
                and (grd.time.values  == ref.time.values ).all()
                and (grd.dtime.values  == ref.dtime.values ).all()                
                and match
            )
    return match