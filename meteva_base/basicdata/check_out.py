# -*- coding: utf-8 -*-

import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import copy
import meteva_base


def checkout_griddata(grd, is_single=False, valid_val=[-1000, 1000, np.NaN]):
    """
    检查grd是否为符合meteva_base规定的网格数据, 未通过检查raise ValueError
    is_single: 是否检查网格数据是否为单要素(lat,lon),默认为否
    valid_val: 网格数据合理值范围下限(valid_val[0])上限(valid_val[1])， 若超过进行提示，并将超过值替换为valid_val[2]
    return:  通过检查则返回经过坐标顺序及数据类型修订后的网格数据, 数据类型强制为np.float32； 
    """

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
    

def _check_time_dtime_same(times0, dtimes0, times1, dtimes1):
    """
    time+dtime 预报时间加预报时效的结果， 两者是否相同
    input:  times-起报时间，datetime或datetime列表， dtimes-预报时效，int32或列表
    return: 相同则返回True,否则为False. 如比较24010108起报, [48,72]预报， 与24010208起报，[24,48]预报，结果为True
    """
    try:
        _ = len(times0)
    except:
        times0 = [times0]
    try:
        _ = len(dtimes0)
    except:
        dtimes0 = [dtimes0]
    try:
        _ = len(times1)
    except:
        times1 = [times1]
    try:
        _ = len(dtimes1)
    except:
        dtimes1 = [dtimes1]
    #统一为datetime格式
    times0 = [meteva_base.tool.all_type_time_to_datetime(fn) for fn in times0]
    times1 = [meteva_base.tool.all_type_time_to_datetime(fn) for fn in times1]
    ## alltime = time + dtime
    alltimes0 = []
    for time in times0:
        for dtime in dtimes0:
            alltimes0.append(time + timedelta(hours=int(dtime)))
    alltimes1 = []
    for time in times1:
        for dtime in dtimes1:
            alltimes1.append(time + timedelta(hours=int(dtime)))
    ## 两个alltime元素是否相同
    alltimes0 = set(alltimes0)
    alltimes1 = set(alltimes1)
    if alltimes0 & alltimes1 == alltimes0:
        match = True
    else:
        match = False
    return match


def checkout_griddata_same_coords(grd_list = [], is_time_match=False):
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
                and 
                    (((grd.time.values  == ref.time.values ).all()
                    and (grd.dtime.values  == ref.dtime.values ).all() #起报时间预报时效一致
                    ) 
                    or _check_time_dtime_same(grd.time.values, grd.dtime.values, ref.time.values, ref.dtime.values) #起报时间预报时效相加能对应
                    )   
                and match
            )
    return match


if __name__ == "__main__":
    # ## test1, time/dtime check
    # times0 = datetime(2024,3,1,8)
    # dtimes0 = [48,72,96]
    # times1 = datetime(2024,3,2,8)
    # dtimes1 = [24,48,72]
    # match = _check_time_dtime_same(times0, dtimes0, times1, dtimes1)
    # print('1:', match)
    # times2 =  [datetime(2024,3,2,8),datetime(2024,3,3,8),datetime(2024,3,4,8)]
    # dtimes2 = 24
    # match = _check_time_dtime_same(times0, dtimes0, times2, dtimes2)
    # print('2:', match)

    ## test2, time/dtime grd check
    import meteva_base as meb
    data = np.zeros((1,1,1,3,11,11),dtype=np.float64)
    grid_info0 = meb.grid(glon=[90,100,1] , glat=[30,40,1], gtime=[datetime(2024,3,1,8)], dtime_list=[48, 72, 96])
    grid_info1 = meb.grid(glon=[90,100,1] , glat=[30,40,1], gtime=[datetime(2024,3,2,8)], dtime_list=[24, 48, 96])
    grd0 = meb.grid_data(grid=grid_info0, data=data)
    grd1 = meb.grid_data(grid=grid_info1, data=data)
    # print(grd0.time.values, grd0.dtime.values, grd0.data.dtype, grd1.data.dtype)
    print(checkout_griddata_same_coords(grd_list = [grd0, grd1], is_time_match=False))
    print(checkout_griddata_same_coords(grd_list = [grd0, grd1], is_time_match=True))