import os
import meteva_base as meb
import bz2
import logging
import time
import numpy as np
import pygrib
import pandas as pd
import xarray as xr


def un_bz2_file(file_name):
    """
    解压bz2 数据,生成文件
    :param file_name:文件绝对路径
    :return: 解压后文件名
    """
    if file_name.endswith('.bz2'):
        if not os.path.exists(file_name.split(".")[0]):
            st = time.time()
            newfilepath = os.path.join(file_name.split(".")[0])
            try:
                with open(newfilepath, 'wb+') as new_file, bz2.BZ2File(file_name, 'rb') as file:
                    for data in iter(lambda: file.read(10000 * 1024), b''):
                        new_file.write(data)
                print('decompress:' + newfilepath + ' with time:' + str(time.time() - st) + 's')
                return file_name.split(".")[0]
            except Exception as e:
                print(file_name + " data exception, please check")
                return None

def un_bz2_handle(file_name):
    """
    解压bz2 数据,生成文件obj
    :param file_name:文件绝对路径
    :return: 解压后文件名
    """
    if file_name.endswith('.bz2'):
        if not os.path.exists(file_name.split(".")[0]):
            st = time.time()
            try:
                file = bz2.BZ2File(file_name, 'rb')
                return(file)
            except Exception as e:
                print(file_name + " data exception, please check")
                return None

def dateDiffInHours(t1, t2):
    """
    计算预报时效
    :param t1:起报时间
    :param t2:预报时间
    :return: 小时数
    """
    td = t2 - t1
    return int(td.days * 24 + td.seconds / 3600)


def _is_nonstring_container(obj):
    """
    判断是否是非字符串的 container容器类。 返回bool类型
    """
    from collections.abc import Container, Iterable
    return isinstance(obj, Container) and isinstance(obj, Iterable) and not isinstance(obj, (str, bytes, bytearray))


def _pygrib_param_id(grb):
    """
    返回grib_message的param_id
    """
    try:
        # 对grib1类型数据获取其表格编码，两组数字组成
        param_id = str.format("{0:0>3d}_{1:0>3d}", grb.table2Version, grb.paramId)
    except Exception as e:
        try:
            # 对grib2类型数据提取，三组数字组成
            param_id = str.format("{0}_{1}_{2}", grb.discipline, grb.parameterCategory, grb.parameterNumber)
        except Exception as err:
            msg = r"ERROR: no grib param_id, please CHECK! "
            print(msg)
            raise ValueError(err)
    return param_id

def pygrib_vars_info(f, save_path=None):
    """
    读取grib数据的变量清单,pygrib库依赖
    :param 
        f: pygrib.open()打开文件对象
        save_path: 变量清单结果的存储路径,csv格式；默认为None不保存
    :return: 变量清单(pandas.DataFrame)
    """
    f.seek(0,0)
    data_list = []
    for grb in f:
        # try:
        #     # 对grib1类型数据获取其表格编码，两组数字组成
        #     param_id = str.format("{0:0>3d}_{1:0>3d}", grb.table2Version, grb.paramId)
        # except Exception as e:
        #     # 对grib2类型数据提取，三组数字组成
        #     param_id = str.format("{0}_{1}_{2}", grb.discipline, grb.parameterCategory, grb.parameterNumber)
        param_id = _pygrib_param_id(grb)
    #     print(grb.shortName, grb.name, param_id, grb.typeOfLevel, grb.level)
        data = pd.DataFrame([[grb.shortName, grb.name, param_id, grb.typeOfLevel, grb.level]],
                            columns=['shortName', 'name', 'param_id', 'typeOfLevel', 'level' ])
        data_list.append(data)
    data_all = pd.concat(data_list, axis=0)
    ## 数据去重排序
    data_all.drop_duplicates(keep='first', inplace=True)
    data_all.sort_values(by=['typeOfLevel','shortName','level'],inplace=True)
    if save_path is not None: ##文件保存变量清单
        try:
            data_all.to_csv(save_path)
        except Exception as err:
            print(err)
    return(data_all)

def read_pygrib_message(f, shortName=None, typeOfLevel=None, level=None, id=None):
    """
    读取grib变量并输出,pygrib库依赖
    :param 
        f: pygrib.open()打开文件对象
        shortName: 要素变量的简写名，具体可查看变量清单。支持str及多str列表形式，用于提取一个或多个要素；默认为None提取所有要素
        typeOfLevel: 要素为单层或高空多层，具体可查看变量清单。('isobaricInhPa','surface',...)
        level: 要素层次，typeOfLevel为'isobaricInhPa'时可设置。支持int及int列表形式；默认为None提取所有层次
        id   : param_id（grib/grib2），具体见_pygrib_param_id（）函数
    :return: 变量(xarray.DataArray)列表list
    """
    dict0 = {}## select 参数列表
    if shortName is not None:
        dict0['shortName'] = shortName
    if typeOfLevel is not None:
        dict0['typeOfLevel'] = typeOfLevel
    if level is not None:
        if typeOfLevel != 'isobaricInhPa':
            print("Warning: CHECK whether typeOfLevel == isobaricInhPa if LEVEL is not None")
        dict0['level'] = level

    
    # 解码并存放读取完成的要素
    array = []
    s = time.time()
    ##pygrib.open/index为相似功能类；其中index.select参数只限制于单要素，open.select参数可以包含容器。 速度index.select>>open.select
    try:
        grib_data = f.select(**dict0)
    except ValueError as e:
        logging.info(e)
        raise ValueError(e)
    ## 循环解码要素列表
    for i in grib_data:
        try:
            # 混合编码数据可能会抛出的异常
            # try:
            #     # 对grib1类型数据获取其表格编码，两组数字组成
            #     param_id = str.format("{0:0>3d}_{1:0>3d}", i.table2Version, i.paramId)
            # except Exception as e:
            #     # 对grib2类型数据提取，三组数字组成
            #     param_id = str.format("{0}_{1}_{2}", i.discipline, i.parameterCategory, i.parameterNumber)
            param_id = _pygrib_param_id(i)
            if id is not None:
                if _is_nonstring_container(id): # param_id改为数组
                    id = [id]
                if param_id not in id:# 有id参数时，只解码对应param_id是否在id列表中
                    continue
            print('param_id', param_id)
            valid_time = meb.all_type_time_to_datetime(str(i.validityDate) + "{0:0>4d}".format(i.validityTime))
            data_time = meb.all_type_time_to_datetime(str(i.dataDate) + "{0:0>4d}".format(i.dataTime))
            # data_time = i.validDate
            # fhour = i.forecastTime
            fhour0 = dateDiffInHours(data_time, valid_time)
            # print(valid_time, data_time, fhour0)
            level = i.level
            s_lat = i.latitudeOfFirstGridPointInDegrees  # 纬度起始值
            e_lat = i.latitudeOfLastGridPointInDegrees  # 纬度结束值
            step_lat = i.jDirectionIncrementInDegrees  # 纬度间隔
            s_lon = i.longitudeOfFirstGridPointInDegrees  # 经度起始值
            e_lon = i.longitudeOfLastGridPointInDegrees  # 经度结束值
            if (s_lon>e_lon) and s_lon==180.:
                s_lon = 0-s_lon 
            step_lon = i.iDirectionIncrementInDegrees  # 经度步长
            latlon = i.latlons()
            lats = latlon[0][:,0]
            lons = latlon[1][0,:]
            # print(lons, lats)
            # print(latlon[0], latlon[1])
            # print( latlon[0].shape, latlon[1].shape)
            g_lon = [s_lon, e_lon, -step_lon if s_lon > e_lon else step_lon]
            g_lat = [s_lat, e_lat, -step_lat if s_lat > e_lat else step_lat]
            g_time = [data_time]
            # print(s_lon, e_lon, step_lon, s_lat, e_lat, step_lat)
            d_time = [dateDiffInHours(data_time, valid_time)]
            member = param_id + '-' + i.shortName + '-' + str(i.level)
            grid_info = meb.grid(glon=g_lon, glat=g_lat, gtime=g_time,
                                dtime_list=d_time, level_list=[level],
                                member_list=[member])
            grd = meb.grid_data(grid_info, i.values)
            grd.name = i.shortName
            # print(param_id, g_lat, g_lon, level, valid_time, data_time, d_time)
            array.append(grd)
        except Exception as e:
            logging.info(e)
            print('ERROR', e)
            continue
    # keys = i.keys()
    # lonlat = i.latlons()
    # print(i.validityDate, i.validityTime, i.validDate,  i.significanceOfReferenceTime, i.dataDate ,i.dataTime, i.forecastTime, i.julianDay)
    # print(i.year, i.month, i.day, i.hour, i.minute, i.second)
    f.close()
    logging.info('Data read complete with time:%s',  str(time.time() - s))
    return array


def read_pygrib(file_path,  shortName=None, typeOfLevel=None, level=None, id=None,
            show_vars=False, dset=False):
    """
    读取grib格式数据，pygrib依赖
    :param 
        file_path: 数据文件绝对路径
        shortName: 要素变量的简写名，具体可查看变量清单。支持str及多str列表形式，用于提取一个或多个要素；默认为None提取所有要素
        typeOfLevel: 要素为单层或高空多层，具体可查看变量清单。('isobaricInhPa','surface',...)
        level: 要素层次，typeOfLevel为'isobaricInhPa'时可设置。支持int及int列表形式；默认为None提取所有层次
        show_vars: 是否返回要素清单，默认为否。可用该参数先了解grib文件中要素名称、种类等，再进行具体提取
        dset: 是否返回xarray.DataSet数据，默认为否； False:返回DataArray列表list
    :return: 返回提取要素，网格数据(xarray.DataSet或xarray.DataArray列表)
    """
    np.set_printoptions(suppress=True)

    # 解压bz2文件
    if not os.path.exists(file_path):
        print('File missing {0}'.format(file_path))
        return None
    try:
        if file_path.endswith('.bz2'):#bz2文件
            file_path0 = os.path.join(os.path.dirname(file_path), os.path.splitext(file_path)[0])#解压文件名
            print(file_path0)
            if os.path.exists(file_path0):#存在解压文件
                file_name = file_path0
            else:
                print("OPEN {}: Compressed".format(file_name))
                file_name = un_bz2_file(file_path)
        else:#非压缩文件名
            print("OPEN {}: not Compressed".format(file_path))
            file_name = file_path
    except Exception as err:
        print(err)
        return None
    # 读取文件
    try:
        pygrib.multi_support_on()
        f = pygrib.open(filename=file_name)
    except Exception as err:
        print(err)
        return None

    # 显示变量vars清单
    if show_vars == True:
        df_vars = pygrib_vars_info(f)
        return df_vars
    else:
        # 解码并存放读取完成的要素
        array = read_pygrib_message(f, shortName=shortName, typeOfLevel=typeOfLevel, level=level, id=id)
        if dset==False:
            return array
        else:
            arrays = xr.merge(array)
            return arrays


def get_stainfo(lons, lats, ids=None):
    if ids is None:
        ids = np.arange(len(lons))
    data = {"站号": ids,
            "经度": lons,
            "纬度": lats,}
    df = pd.DataFrame(data)
    sta = meb.sta_data(df,columns = ["id","lon","lat"])
    print(sta)
    return sta

def read_sta_from_grib2(file, sta_info):
    array = read_pygrib(file)
    grd = xr.merge(array)['data0']
    result = meb.interp_gs_linear(grd, sta=sta_info)
    return result, grd

if __name__ == '__main__':
    "添加逐时"
    ## 02 SCMOC_ER01
    lons = [116.35]
    lats = [39.95]
    sta_info = get_stainfo(lons=lons, lats=lats)
    file = r"J:\Z_NWGD_C_BABJ_20230505055246_P_RFFC_SCMOC-ER01_202305050500_03601.GRB2"
    array = read_pygrib(file, dset=True)#返回xr.dataset数据
    print(array)
    sta = meb.interp_gs_linear(array.unknown, sta=sta_info)
    print(sta)
