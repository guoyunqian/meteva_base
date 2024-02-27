#!/usr/bin/python3.6
# -*- coding:UTF-8 -*-
from meteva_base.basicdata.sta_data import *
import numpy as np
import os
import pandas as pd
import meteva_base
import traceback
import re
import copy
from . import DataBlock_pb2
from .GDS_data_service import GDSDataService
import struct
from collections import OrderedDict
import datetime
import math
from io import StringIO
from .CMADaasAccess import CMADaasAccess
from .httpclient import get_http_result_cimiss
import json
import h5py


def read_station(filename,keep_alt = False,show = False):
    '''
    :param filename: 站点文件路径，它可以是micaps第1、2、3、8类文件
    :return: 站点数据，其中time,dtime,level属性为设置的缺省值，数据内容都设置为0
    '''
    if not os.path.exists(filename):
        print(filename+"文件不存在")
        return None
    elif os.path.isdir(filename):
        print(filename+"是文件夹而不是文件")
        return None
    else:
        encoding,_ = meteva_base.io.get_encoding_of_file(filename,read_rows=1)
        if encoding is None:
            print("文件编码格式不识别")
            return None
        try:
            file = open(filename, encoding=encoding)
            sta = None
            head = file.readline()
            strs = head.split()
            if strs[1] == "3":
                if keep_alt:
                    sta = read_sta_alt_from_micaps3(filename)
                else:
                    sta = read_stadata_from_micaps3(filename)
            elif strs[1] == "16":
                sta = read_stadata_from_micaps16(filename)
            elif strs[1] == "1" or str[1] == "2" or str[1] == "8":
                sta = read_stadata_from_micaps1_2_8(filename,column=3)
            else:
                print(filename + "is not micaps第1、2、3、8类文件")

            if sta is not None:
                data_name = sta.columns[-1]
                if not keep_alt:
                    sta[data_name] = 0
                else:
                    meteva_base.set_stadata_names(sta,["alt"])
                meteva_base.set_stadata_coords(sta,time = datetime.datetime(2099,1,1,8,0),level = 0,dtime= 0)
                if show:
                    print("success read from "+filename)
                return sta
        except:
            if show:
                exstr = traceback.format_exc()
                print(exstr)

            print(filename + "文件格式不能识别。可能原因：文件未按micaps格式存储")
            return None

def read_sta_alt_from_micaps3(filename, station=None, drop_same_id=True,dtime_units = "hour",show = False):
    '''
    读取micaps3格式文件转换为pandas中dataframe结构的数据

    :param reserve_time_dtime_level:保留时间，时效和层次，默认为rue
    :param data_name:dataframe中数值的values列的名称
    :return:返回一个dataframe结构的多列站点数据。
    :param filename: 文件路径
    :param station: 站号，默认：None
    :param drop_same_id: 是否要删除相同id的行  默认为True
    :return:
    '''

    #print(os.path.exists(filename))
    if not os.path.exists(filename):
        print(filename+"文件不存在")
        return None
    elif os.path.isdir(filename):
        print(filename+"是文件夹而不是文件")
        return None
    else:
        encoding, _ = meteva_base.io.get_encoding_of_file(filename,read_rows=1)
        if encoding is None:
            print("文件编码格式不识别")
            return None

        try:
            file = open(filename, 'r',encoding= encoding)
            skip_num = 0
            strs = []
            nline = 0
            nregion = 0
            nstart = 0
            while 1 > 0:
                skip_num += 1
                str1 = file.readline()
                strs.extend(str1.split())

                if (len(strs) > 8):
                    nline = int(strs[8])
                if (len(strs) > 11 + nline):
                    nregion = int(strs[11 + nline])
                    nstart = nline + 2 * nregion + 14
                    if (len(strs) == nstart):
                        break
            file.close()

            file_sta = open(filename,'r',encoding= encoding)

            sta1 = pd.read_csv(file_sta, skiprows=skip_num, sep="\s+", header=None, usecols=[0, 1, 2, 3])
            sta1.columns = ['id', 'lon', 'lat', 'alt']
            sta1.drop_duplicates(keep='first', inplace=True)
            if drop_same_id:
                sta1 = sta1.drop_duplicates(['id'])
            # sta = bd.sta_data(sta1)
            sta = meteva_base.basicdata.sta_data(sta1)
            # print(sta)

            y2 = ""
            if len(strs[3]) == 2:
                year = int(strs[3])
                if year >= 50:
                    y2 = '19'
                else:
                    y2 = '20'
            if len(strs[3]) == 1: strs[3] = "0" + strs[3]
            if len(strs[4]) == 1: strs[4] = "0" + strs[4]
            if len(strs[5]) == 1: strs[5] = "0" + strs[5]
            if len(strs[6]) == 1: strs[6] = "0" + strs[6]

            time_str = y2 + strs[3] + strs[4] + strs[5] + strs[6]
            time_file = meteva_base.tool.time_tools.str_to_time(time_str)
            sta.loc[:,"time"] = time_file
            sta.loc[:,"dtime"] = 0
            sta.loc[:,"level"] = 0 #int(strs[7])

            if (station is not None):
                sta = meteva_base.put_stadata_on_station(sta, station)
            if show:
                print("success read from " + filename)
            sta.attrs = {}
            sta.attrs["dtime_units"] = dtime_units
            set_stadata_attrs(sta,units_attr = '',
                              model_var_attr = '',
                              dtime_units_attr = 'hour',
                              level_type_attr = 'isobaric',
                              time_type_attr = 'UT',
                              time_bounds_attr = [0,0])
            return sta
        except:
            if show:
                exstr = traceback.format_exc()
                print(exstr)

            print(filename+"文件格式不能识别。可能原因：文件未按micaps3格式存储")
            return None

def read_stadata_from_micaps3(filename, station=None,  level=None,time=None, dtime=None, data_name='data0', drop_same_id=True,dtime_units = "hour",show = False):
    '''
    读取micaps3格式文件转换为pandas中dataframe结构的数据

    :param reserve_time_dtime_level:保留时间，时效和层次，默认为rue
    :param data_name:dataframe中数值的values列的名称
    :return:返回一个dataframe结构的多列站点数据。
    :param filename: 文件路径
    :param station: 站号，默认：None
    :param time: 起报时  默认：NOne
    :param dtime: 时效 默认：None
    :param level:  层次  默认：None
    :param data_name: 要素名  默认：'data0'
    :param drop_same_id: 是否要删除相同id的行  默认为True
    :return:
    '''
    if not os.path.exists(filename):
        print(filename+"文件不存在")
        return None
    elif os.path.isdir(filename):
        print(filename+"是文件夹而不是文件")
        return None
    elif os.path.isdir(filename):
        print(filename+"是文件夹而不是文件")
        return None
    else:
        encoding, _ = meteva_base.io.get_encoding_of_file(filename,read_rows=1)
        if encoding is None:
            print("文件编码格式不识别")
            return None

        try:
            file = open(filename, 'r',encoding=encoding)
            skip_num = 0
            strs = []
            nline = 0
            nregion = 0
            nstart = 0
            while 1 > 0:
                skip_num += 1
                str1 = file.readline()
                #print(str1)
                strs.extend(str1.split())

                if (len(strs) > 8):
                    nline = int(strs[8])
                if (len(strs) > 11 + nline):
                    nregion = int(strs[11 + nline])
                    nstart = nline + 2 * nregion + 14
                    if (len(strs) == nstart):
                        break
            file.close()
            #print(skip_num)
            if int(strs[-1]) == 0:return None

            file_sta = open(filename, 'r',encoding=encoding)
            sta1 = pd.read_csv(file_sta, skiprows=skip_num, sep="\s+", header=None, usecols=[0, 1, 2, 4])
            sta1.columns = ['id', 'lon', 'lat', data_name]
            sta1.drop_duplicates(keep='first', inplace=True)
            if drop_same_id:
                sta1 = sta1.drop_duplicates(['id'])
            # sta = bd.sta_data(sta1)
            sta = meteva_base.basicdata.sta_data(sta1)
            #print(sta)

            y2 = ""
            if len(strs[3]) == 2:
                year = int(strs[3])
                if year >= 50:
                    y2 = '19'
                else:
                    y2 = '20'
            if len(strs[3]) == 1: strs[3] = "0" + strs[3]
            if len(strs[4]) == 1: strs[4] = "0" + strs[4]
            if len(strs[5]) == 1: strs[5] = "0" + strs[5]
            if len(strs[6]) == 1: strs[6] = "0" + strs[6]

            if time is None:
                time_str = y2 + strs[3] + strs[4] + strs[5] + strs[6]
                time_file = meteva_base.tool.time_tools.str_to_time(time_str)
                sta.loc[:,"time"] = time_file
            else:
                time_file = meteva_base.tool.time_tools.all_type_time_to_datetime(time)
                sta.loc[:,"time"] = time_file
            sta.loc[:,"dtime"] = 0
            sta.loc[:,"level"] = 0 #int(strs[7])
            #print(time_str)
            meteva_base.set_stadata_coords(sta, level=level, dtime=dtime)

            if (station is not None):
                sta = meteva_base.put_stadata_on_station(sta, station)
            sta.attrs = {}
            sta.attrs["dtime_units"] = dtime_units
            if show:
                print("success read from " + filename)
            set_stadata_attrs(sta,units_attr = '',
                              model_var_attr = '',
                              dtime_units_attr = 'hour',
                              level_type_attr = 'isobaric',
                              time_type_attr = 'UT',
                              time_bounds_attr = [0,0])
            return sta

        except:
            if show:
                exstr = traceback.format_exc()
                print(exstr)

            print(filename+"文件格式不能识别。可能原因：文件未按micaps3格式存储")
            return None

def read_stadata_from_csv_txt(filename, columns, member_list,skiprows=0,level = None,time = None,dtime = None, drop_same_id=False,
                          sep = "\s+",dtime_units = "hour",show = False):

    """
    读取站点数据
    :param filename:带有站点信息的路径已经文件名
    :param columns 列名
    :param skiprows:读取时跳过的行数，默认为：0
    :param drop_same_id: 是否要删除相同id的行  默认为True
    :return:返回带有'level','time','dtime','id','lon','lat','alt','data0'列的dataframe站点信息。
    """
    if not os.path.exists(filename):
        print(filename+"文件不存在")
        return None
    elif os.path.isdir(filename):
        print(filename+"是文件夹而不是文件")
        return None
    else:
        encoding,_ = meteva_base.io.get_encoding_of_file(filename,read_rows=skiprows)
        if encoding is None:
            print("文件编码格式不识别")
            return None
        try:
            file_sta = open(filename, 'r',encoding = encoding)
            if "time" in columns:
                index = columns.index("time")
                sta0 = pd.read_csv(file_sta, skiprows=skiprows,  header=None,sep=sep,parse_dates=[index])
                sta0.columns = columns
            else:
                sta0 = pd.read_csv(file_sta, skiprows=skiprows, header=None, sep=sep)
                sta0.columns = columns

            station_column = []
            for column in columns:
                if column in meteva_base.get_coord_names():
                    station_column.append(column)
            if not isinstance(member_list,list):
                member_list = [member_list]

            sta0.drop_duplicates(keep='first', inplace=True)
            station_column.extend(member_list)
            sta1 = sta0[station_column]
            nsta = len(sta1.index)
            if "lon" in station_column:
                if sta1.loc[0,"lon"] >1000:
                    a = sta1.loc[:, 'lon'] // 100 + (sta1.loc[:, 'lon'] %100)/60
                    sta1.loc[:, "lon"] = a
            if "lat" in station_column:
                if sta1.loc[0, "lat"] > 1000:
                    a = sta1.loc[:, 'lat'] // 100 + (sta1.loc[:, 'lat'] % 100) / 60
                    sta1.loc[:, "lat"] = a
                # for i in range(nsta):
                #     if sta1.loc[i, 'lon'] > 1000:
                #         a = sta1.loc[i, 'lon'] // 100 + (a % 100) / 60
                #         sta1.loc[i, 'lon'] = a
            # if "lat" in station_column:
            #     for i in range(nsta):
            #         if sta1.loc[i, 'lat'] > 1000:
            #             a = sta1.loc[i, 'lat'] // 100 + (a % 100) / 60
            #             sta1.loc[i, 'lat'] = a
            # sta = bd.sta_data(sta1)
            sta = meteva_base.basicdata.sta_data(sta1)
            if drop_same_id:
                sta = sta.drop_duplicates(['id'])

            # sta['time'] = method.time_tools.str_to_time64("2099010108")
            if time is not None:
                sta.loc[:,"time"] = time
            elif pd.isnull(sta.iloc[0,1]):
                sta.loc[:,'time'] = meteva_base.tool.time_tools.str_to_time64("2099010108")
            if dtime is not None:
                sta.loc[:,"dtime"] = dtime
            elif pd.isnull(sta.iloc[0,2]):
                sta.loc[:,"dtime"] = 0

            if level is not None:
                sta.loc[:,"level"] = level
            elif pd.isnull(sta.iloc[0,0]):
                sta.loc[:,"level"] = 0


            meteva_base.basicdata.reset_id(sta)
            sta.attrs = {}
            sta.attrs["dtime_units"] = dtime_units
            if show:
                print("success read from "+filename)
            return sta
        except:
            if show:
                exstr = traceback.format_exc()
                print(exstr)
            print(filename+"文件格式不能识别。可能原因：文件未按pandas能够识别的csv格式存储")
            return None

def read_stadata_from_sevp(filename, element_id,level=None,time=None,data_name = "data0",show = False,dtime_units = "hour"):
    '''
    兼容多个时次的预报产品文件 txt格式
    :param：filename:文件路径和名称
    :param: element:选取要素
    :param drop_same_id: 是否要删除相同id的行  默认为True
    :return：dataframe格式的站点数据

    '''

    if not os.path.exists(filename):
        print(filename+"文件不存在")
        return None
    elif os.path.isdir(filename):
        print(filename+"是文件夹而不是文件")
        return None
    else:
        encoding,lines = meteva_base.io.get_encoding_of_file(filename,read_rows=6)
        if encoding is None:
            print("文件编码格式不识别")
            return None
        try:
            #lines = heads.split("\n")
            file = open(filename,encoding = encoding)
            str_lines0 = file.readlines()
            str_lines = []
            for str1 in str_lines0:
                if str1.strip() !="":
                    str_lines.append(str1)
            if time is None:
                strs4 = lines[3].split()
                time_file = meteva_base.tool.time_tools.str_to_time(strs4[1])
            else:
                time_file = time
            if level is None:
                level = 0

            num_all = len(str_lines) - 1
            str_lines_list = []
            nline = 5
            while nline< num_all:
                str1 = str_lines[nline][:-1] +" "
                strs = str1.split()
                strs_len = len(strs)
                if(strs_len>5):
                    next_num = int(strs[4])
                    if strs_len > 6:
                        str1 = strs[0]+" " + strs[1] +" "+ strs[2] +" "+ strs[3] +" "+ strs[4] +" "+ strs[5] + " "
                    for i in range(1,next_num+1):
                        e_str = str1 + str_lines[nline+i]
                        str_lines_list.append(e_str)
                    nline += next_num+1
                else:
                    nline +=  1
            strs_all = "".join(str_lines_list)

            f = StringIO(strs_all)
            df = pd.read_csv(f,header = None,sep="\s+")
            df = df.loc[:,[0,1,2,6,6 + element_id]]
            df.columns = ["id", "lon", "lat", "dtime",data_name]
            df["time"] = time_file
            df["level"] = level
            sta = meteva_base.sta_data(df)
            sta.attrs = {}
            sta.attrs["dtime_units"] = dtime_units
            set_stadata_attrs(sta,units_attr = '',
                              model_var_attr = '',
                              dtime_units_attr = 'hour',
                              level_type_attr = 'isobaric',
                              time_type_attr = 'UT',
                              time_bounds_attr = [0,0])
            return sta
        except:
            if show:
                exstr = traceback.format_exc()
                print(exstr)
            print(filename + " 文件格式异常")


def read_stadata_from_micaps1_2_8(filename, column, station=None, level=None,time=None, dtime=None, data_name='data0', drop_same_id=True,dtime_units = "hour",show = False):
    '''
    read_from_micaps1_2_8  读取m1、m2、m8格式的文件
    :param filename: 文件路径
    :param column: 选取哪列要素  4-len
    :param station: 站号 默认为None
    :param drop_same_id: 是否要删除相同id的行  默认为True
    :return:
    '''
    if not os.path.exists(filename):
        print(filename+"文件不存在")
        return None
    elif os.path.isdir(filename):
        print(filename+"是文件夹而不是文件")
        return None
    else:
        encoding,heads = meteva_base.io.get_encoding_of_file(filename,read_rows=2)
        if encoding is None:
            print("文件编码格式不识别")
            return None

        try:
            file = open(filename,encoding=encoding)
            sta1 = pd.read_csv(file, skiprows=2, sep="\s+", header=None, usecols=[0, 1, 2,  column])
            sta1.columns = ['id', 'lon', 'lat', data_name]
            sta2 = meteva_base.basicdata.sta_data(sta1)
            if drop_same_id:
                sta2 = sta2.drop_duplicates(['id'])
            strs0 = heads[0].split()
            strs = heads[1].split()
            y2 = ""
            if len(strs[0]) == 2:
                year = int(strs[0])
                if year >= 50:
                    y2 = '19'
                else:
                    y2 = '20'
            if len(strs[0]) == 1: strs[0] = "0" + strs[0]
            if len(strs[1]) == 1: strs[1] = "0" + strs[1]
            if len(strs[2]) == 1: strs[2] = "0" + strs[2]
            if len(strs[3]) == 1: strs[3] = "0" + strs[3]

            time_str = y2 + strs[0] + strs[1] + strs[2] + strs[3]
            time_file = meteva_base.tool.time_tools.str_to_time(time_str)
            if time is None:
                sta2.loc[:,'time'] = time_file
            else:
                sta2.loc[:,'time'] = time
            #print(strs0)
            if strs0[1] == "1":
                sta2.loc[:,"level"] = 0
                sta2.loc[:,"dtime"] = 0
            elif strs0[1] == "2":
                sta2.loc[:,"level"] = int(strs[4])
                sta2.loc[:,"dtime"] = 0
            elif strs0[1] == "8":
                sta2.loc[:,"level"] = 0
                sta2.loc[:,"dtime"] = int(strs[4])
            else:
                print(filename + "is not micaps第1、2、3、8类文件")

            meteva_base.set_stadata_coords(sta2,level= level,time = time,dtime= dtime)
            if show:
                print("success read from "+filename)
            if station is None:
                sta2.attrs = {}
                sta2.attrs["dtime_units"] = dtime_units
                return sta2
            else:
                sta = meteva_base.put_stadata_on_station(sta2, station)
                sta.attrs = {}
                sta.attrs["dtime_units"] = dtime_units
                set_stadata_attrs(sta,units_attr = '',
                                  model_var_attr = '',
                                  dtime_units_attr = 'hour',
                                  level_type_attr = 'isobaric',
                                  time_type_attr = 'UT',
                                  time_bounds_attr = [0,0])
                return sta
        except:
            if show:
                exstr = traceback.format_exc()
                print(exstr)
            print(filename+"文件格式不能识别。可能原因：文件未按micaps第1、2、8类格式存储")
            return None


def read_stadata_from_micaps41_lightning(filename, column, level=0,data_name='data0', show = False,keep_millisecond = False,dtime_units = "hour"):
    '''
        read_from_micaps41  读取m41格式的文件
        :param filename: 文件路径
        :param column: 选取哪列要素  4-len
        :param station: 站号 默认为None
        :param drop_same_id: 是否要删除相同id的行  默认为True
        :return:
        '''
    if not os.path.exists(filename):
        print(filename+"文件不存在")
        return None
    elif os.path.isdir(filename):
        print(filename+"是文件夹而不是文件")
        return None
    else:
        encoding, heads = meteva_base.io.get_encoding_of_file(filename, read_rows=2)
        if encoding is None:
            print("文件编码格式不识别")
            return None

        try:
            file = open(filename, encoding=encoding)
            sta1 = pd.read_csv(file, skiprows=2, sep="\s+", header=None, usecols=[0, 1, 4,5,column])
            sta1.columns = ['id','time', 'lon', 'lat', data_name]
            sta1['time'] = pd.to_datetime(sta1['time'],format="%Y%m%d%H%M%S%f")
            if not keep_millisecond:
                sta1['time'] = sta1['time'].dt.ceil("S")
            sta2 = meteva_base.basicdata.sta_data(sta1)

            sta2.loc[:, "level"] = level
            sta2.loc[:, "dtime"] = 0
            sta2.attrs = {}
            sta2.attrs["dtime_units"] = dtime_units
            if show:
                print("success read from " + filename)
            set_stadata_attrs(sta2,units_attr = '',
                              model_var_attr = '',
                              dtime_units_attr = 'hour',
                              level_type_attr = 'isobaric',
                              time_type_attr = 'UT',
                              time_bounds_attr = [0,0])
            return sta2

        except:
            if show:
                exstr = traceback.format_exc()
                print(exstr)
            print(filename + "文件格式不能识别。可能原因：文件未按micaps第41类格式存储")
            return None


def set_io_config(filename):
    if os.path.exists(filename):
        try:
            ip,port = read_gds_ip_port(filename)
            ips = ip.split(".")
            if len(ips) == 4:
                for i in range(4):
                    digital = int(ips[i])
            else:
                print("filename  内容的格式不符合要求")
            meteva_base.gds_ip_port = ip,port
            print("配置文件设置成功")
        except:
            print(filename + "中micaps分布式数据库设置格式不符合要求")

        try:
            meteva_base.cimiss_set = read_cimiss_set(filename)
        except:
            print(filename + "中未包含cimiss数据库设置，或格式不符合要求，不读取cmiss数据库中数据则可忽略该信息")

        try:
            meteva_base.cmadaas_set = read_cmadass_set(filename)
        except:
            print(filename + "中未包含cmadaas数据库设置，或格式不符合要求，不读取大数据云平台则可忽略该信息")
    else:
        print("cimiss和gds配置文件不存在")


def read_cimiss_set(filename,show = False):
    if filename is None:
        print("请使用set_config_ip_port 函数设置存储ip，port的配置文件的路径")
    file = open(filename)
    for i in range(100):
        title = file.readline()
        if title.find("CIMISS") >=0:
            break
    dns = file.readline().split("=")[1]
    dns = dns.strip()
    userId =file.readline().split("=")[1]
    userId = userId.strip()
    pwd = file.readline().split("=")[1]
    pwd = pwd.strip()
    file.close()
    if show:
        print("success read from " + filename)
    return dns,userId,pwd

def read_cmadass_set(filename,show = False):
    if filename is None:
        print("请使用set_config_ip_port 函数设置存储ip，port的配置文件的路径")
    file = open(filename)
    for i in range(100):
        title = file.readline()
        if title.find("CMADaaS") >=0:
            break
    dns = file.readline().split("=")[1]
    dns = dns.strip()
    port = file.readline().split("=")[1]
    port = port.strip()
    userId =file.readline().split("=")[1]
    userId = userId.strip()
    pwd = file.readline().split("=")[1]
    pwd = pwd.strip()
    file.close()
    if show:
        print("success read from " + filename)
    return dns,port,userId,pwd

def read_gds_ip_port(filename,show = False):
    if filename is None:
        print("请使用set_config_ip_port 函数设置存储ip，port的配置文件的路径")
    file = open(filename)
    for i in range(100):
        title = file.readline()
        if title.find("MICAPS") >=0:
            break
    ip = file.readline().split("=")[1]
    ip = ip.strip()
    port = int(file.readline().split("=")[1])
    file.close()
    if show:
        print("success read from " + filename)
    return ip,port

def read_stadata_from_gds(filename,element_id = None,station = None, level=None,time=None, dtime=None, data_name='data0',dtime_units = "hour",show = False):
    '''
    :param ip: 为字符串形式，示例 “10.20.30.40”
    :param port: 为整数形式 示例 8080
    :param filename0:
    :param element_id0:
    :param station:
    :param data_name:
    :return:
    '''
    directory, filename = os.path.split(filename)
    # connect to data service
    if meteva_base.gds_ip_port is None:
        print("请先使用set_config 配置gds的ip和port")
        return
    ip,port = meteva_base.gds_ip_port
    service = GDSDataService(ip, port)

    # get data file name
    element_id0 = element_id
    if element_id is not None:
        element_id_str0 = str(element_id)

    try:
        directory = directory.replace("mdfs:///", "")
        directory = directory.replace("\\","/")
        status, response = service.getData(directory, filename)
    except ValueError:
        print('Can not retrieve data' + filename + ' from ' + directory)
        return None
    try:
        ByteArrayResult = DataBlock_pb2.ByteArrayResult()
        if status == 200:
            ByteArrayResult.ParseFromString(response)
            if ByteArrayResult is not None:
                byteArray = ByteArrayResult.byteArray

                # define head structure
                head_dtype = [('discriminator', 'S4'), ('type', 'i2'),
                              ('description', 'S100'),
                              ('level', 'f4'), ('levelDescription', 'S50'),
                              ('year', 'i4'), ('month', 'i4'), ('day', 'i4'),
                              ('hour', 'i4'), ('minute', 'i4'), ('second', 'i4'),
                              ('Timezone', 'i4'),("id_type","i2"), ('extent', 'S98')]

                # read head information
                head_info = np.frombuffer(byteArray[0:288], dtype=head_dtype)
                #print(head_info)
                if time is None:
                    time = datetime.datetime(
                        head_info['year'][0], head_info['month'][0],
                        head_info['day'][0], head_info['hour'][0],
                        head_info['minute'][0], head_info['second'][0])
                else:
                    time = meteva_base.tool.time_tools.all_type_time_to_time64(time)
                if level is None:
                    level = head_info["level"][0]
                if dtime is None:
                    filename1 = os.path.split(filename)[1].split(".")
                    dtime = int(filename1[1])
                id_type = head_info['id_type'][0]
                ind = 288
                # read the number of stations
                station_number = np.frombuffer(
                    byteArray[ind:(ind+4)], dtype='i4')[0]
                ind += 4

                # read the number of elements

                element_number = np.frombuffer(
                    byteArray[ind:(ind+2)], dtype='i2')[0]

                if element_number == 0:
                    return None
                ind += 2

                # construct record structure
                element_type_map = {
                    1: 'b1', 2: 'i2', 3: 'i4', 4: 'i8', 5: 'f4', 6: 'f8', 7: 'S1'}
                element_map = {}
                element_map_len = {}
                for i in range(element_number):
                    element_id = str(np.frombuffer(byteArray[ind:(ind+2)], dtype='i2')[0])
                    ind += 2
                    element_type = np.frombuffer(
                        byteArray[ind:(ind+2)], dtype='i2')[0]
                    ind += 2
                    element_map[element_id] = element_type_map[element_type]
                    element_map_len[element_id] = int(element_type_map[element_type][1])

                if element_id0 is None:
                    dict0 = {}
                    id_dict = meteva_base.gds_element_id_dict
                    for key in element_map.keys():
                        if (int(key) in id_dict.values()):
                            for ele in id_dict.keys():
                                if int(key) == id_dict[ele]:
                                    dict0[ele] = key
                    if len(dict0.keys()) > 1:
                        print("element_id can not be None for this file")
                    else:
                        element_id_str0 = list(dict0.values())[0]
                dtype_str = element_map[element_id_str0]


                # loop every station to retrieve record
                if id_type ==0:
                    record_head_dtype = [
                        ('id', 'i4'), ('lon', 'f4'), ('lat', 'f4'), ('numb', 'i2')]
                    records = []
                    if station is None or len(station.index) * 100 > station_number:
                        for i in range(station_number):
                            record_head = np.frombuffer(
                                byteArray[ind:(ind+14)], dtype=record_head_dtype)
                            ind += 14
                            record = {
                                'id': record_head['id'][0], 'lon': record_head['lon'][0],
                                'lat': record_head['lat'][0]}
                            for j in range(record_head['numb'][0]):    # the record element number is not same, missing value is not included.
                                element_id = str(np.frombuffer(byteArray[ind:(ind + 2)], dtype='i2')[0])
                                ind += 2
                                element_len = element_map_len[element_id]
                                if element_id == element_id_str0:
                                    record[data_name] = np.frombuffer(
                                        byteArray[ind:(ind + element_len)],
                                        dtype=dtype_str)[0]
                                    records.append(record)
                                ind += element_len
                        records = pd.DataFrame(records)
                        records.set_index('id')
                        # get time

                        records['time'] = time
                        records['level'] = level
                        records['dtime'] = dtime
                        new_columns = ['level', 'time', 'dtime', 'id', 'lon', 'lat', data_name]
                        records = records.reindex(columns=new_columns)

                        if station is None:
                            return records
                        else:
                            sta = meteva_base.put_stadata_on_station(records, station)
                            return sta
                    else:
                        sta = copy.deepcopy(station)
                        byte_num = len(byteArray)
                        i4_num = (byte_num - ind -4) //4
                        ids = np.zeros((i4_num,4),dtype=np.int32)

                        ids[:, 0] = np.frombuffer(byteArray[ind:(ind + i4_num * 4)], dtype='i4')
                        ids[:, 1] = np.frombuffer(byteArray[(ind +1):(ind + 1 + i4_num * 4)], dtype='i4')
                        ids[:, 2] = np.frombuffer(byteArray[(ind + 2):(ind + 2 + i4_num * 4)], dtype='i4')
                        ids[:, 3] = np.frombuffer(byteArray[(ind + 3):(ind + 3 + i4_num * 4)], dtype='i4')
                        ids = ids.flatten()
                        station_ids = station["id"].values
                        dat = np.zeros(station_ids.size)

                        for k in range(dat.size):
                            id1 = station_ids[k]
                            indexs = np.where(ids == id1)
                            if len(indexs[0]) >=1:
                                for n in range(len(indexs)):
                                    ind1 =ind +  indexs[n][0]
                                    record_head = np.frombuffer(byteArray[ind1:(ind1 + 14)], dtype=record_head_dtype)
                                    if(record_head['lon'][0] >=-180 and record_head['lon'][0] <= 360 and
                                            record_head['lat'][0] >= -90 and record_head['lat'][0] <= 90 and record_head["numb"][0] < 1000):
                                        ind1 += 14
                                        for j in range(record_head['numb'][0]):  # the record element number is not same, missing value is not included.
                                            element_id = str(np.frombuffer(byteArray[ind1:(ind1 + 2)], dtype='i2')[0])
                                            ind1 += 2
                                            element_len = element_map_len[element_id]
                                            if element_id == element_id_str0:
                                                sta.iloc[k,-1] = np.frombuffer(byteArray[ind1:(ind1 + element_len)],dtype=dtype_str)[0]
                                            ind1 += element_len
                        meteva_base.set_stadata_names(sta,[data_name])
                        sta['time'] = time
                        sta['level'] = level
                        sta['dtime'] = dtime
                        sta.attrs = {}
                        sta.attrs["dtime_units"] = dtime_units
                        if show:
                            print("success read from " + filename)
                        set_stadata_attrs(sta,units_attr = '',
                                          model_var_attr = '',
                                          dtime_units_attr = 'hour',
                                          level_type_attr = 'isobaric',
                                          time_type_attr = 'UT',
                                          time_bounds_attr = [0,0])
                        return sta
                else:
                    record_head_dtype = [
                        ('lon', 'f4'), ('lat', 'f4'), ('numb', 'i2')]
                    records = []
                    # if station is None or len(station.index) * 100 > station_number:
                    for i in range(station_number):
                        string_id_record_length = np.frombuffer(byteArray[ind:(ind + 2)], dtype="i2")[0]
                        dtype1 = "S" + str(string_id_record_length)
                        string_id = np.frombuffer(byteArray[ind + 2:(ind + 2 + string_id_record_length)], dtype=dtype1)[0]
                        string_id = string_id.decode()
                        ind += (2 + string_id_record_length)
                        record_head = np.frombuffer(
                            byteArray[ind:(ind + 10)], dtype=record_head_dtype)
                        ind += 10
                        record = {
                            'id': string_id, 'lon': record_head['lon'][0],
                            'lat': record_head['lat'][0]}

                        for j in range(record_head['numb'][
                                           0]):  # the record element number is not same, missing value is not included.
                            element_id = str(np.frombuffer(byteArray[ind:(ind + 2)], dtype='i2')[0])
                            ind += 2
                            element_len = element_map_len[element_id]
                            if element_id == element_id_str0:
                                record[data_name] = np.frombuffer(
                                    byteArray[ind:(ind + element_len)],
                                    dtype=dtype_str)[0]
                                records.append(record)
                            ind += element_len
                    records = pd.DataFrame(records)
                    records.set_index('id')
                    # get time

                    records['time'] = time
                    records['level'] = level
                    records['dtime'] = dtime
                    new_columns = ['level', 'time', 'dtime', 'id', 'lon', 'lat', data_name]
                    records = records.reindex(columns=new_columns)
                    meteva_base.reset_id(records)
                    records.attrs = {}
                    records.attrs["dtime_units"] = dtime_units
                    if station is None:
                        return records
                    else:
                        sta = meteva_base.put_stadata_on_station(records, station)
                        if show:
                            print("success read from " + filename)
                        set_stadata_attrs(sta,units_attr = '',
                                          model_var_attr = '',
                                          dtime_units_attr = 'hour',
                                          level_type_attr = 'isobaric',
                                          time_type_attr = 'UT',
                                          time_bounds_attr = [0,0])
                        return sta
            else:
                print("连接服务状态正常，但返回的输入内容为空")
                return None
        else:
            print("连接服务的状态异常，不能读取相应的文件,可能原因相应的文件不在允许读取的时段范围")
            return None
    except:
        if show:
            exstr = traceback.format_exc()
            print(exstr)
        print(filename + "数据读取失败")
        return None


def read_stadata_from_gdsfile(filename,element_id = None,station = None, level=None,time=None, dtime=None, data_name='data0',dtime_units = "hour",show = False):

    element_id0 = element_id
    if element_id is not None:
        element_id_str0 = str(element_id)

    if not os.path.exists(filename):
        print(filename+"文件不存在")
        return None
    elif os.path.isdir(filename):
        print(filename+"是文件夹而不是文件")
        return None
    else:
        try:
            element_id_str0 = str(element_id)
            file = open(filename,"rb")
            byteArray = file.read()
            # define head structure
            head_dtype = [('discriminator', 'S4'), ('type', 'i2'),
                          ('description', 'S100'),
                          ('level', 'f4'), ('levelDescription', 'S50'),
                          ('year', 'i4'), ('month', 'i4'), ('day', 'i4'),
                          ('hour', 'i4'), ('minute', 'i4'), ('second', 'i4'),
                          ('Timezone', 'i4'),("id_type","i2"), ('extent', 'S98')]

            # read head information
            head_info = np.frombuffer(byteArray[0:288], dtype=head_dtype)
            if time is None:
                time = datetime.datetime(
                    head_info['year'][0], head_info['month'][0],
                    head_info['day'][0], head_info['hour'][0],
                    head_info['minute'][0], head_info['second'][0])
            else:
                time = meteva_base.tool.time_tools.all_type_time_to_time64(time)
            if level is None:
                level = head_info["level"][0]
            if dtime is None:
                filename1 = os.path.split(filename)[1].split(".")
                dtime = int(filename1[1])
            id_type = head_info['id_type'][0]
            ind = 288
            # read the number of stations
            station_number = np.frombuffer(
                byteArray[ind:(ind+4)], dtype='i4')[0]
            ind += 4

            # read the number of elements
            element_number = np.frombuffer(
                byteArray[ind:(ind+2)], dtype='i2')[0]

            if element_number == 0:
                return None
            ind += 2

            # construct record structure
            element_type_map = {
                1: 'b1', 2: 'i2', 3: 'i4', 4: 'i8', 5: 'f4', 6: 'f8', 7: 'S1'}
            element_map = {}
            element_map_len = {}
            for i in range(element_number):
                element_id = str(np.frombuffer(byteArray[ind:(ind+2)], dtype='i2')[0])
                ind += 2
                element_type = np.frombuffer(
                    byteArray[ind:(ind+2)], dtype='i2')[0]
                ind += 2
                element_map[element_id] = element_type_map[element_type]
                element_map_len[element_id] = int(element_type_map[element_type][1])

            if element_id0 is None:
                dict0 = {}
                id_dict = meteva_base.gds_element_id_dict
                for key in element_map.keys():
                    if (int(key) in id_dict.values()):
                        for ele in id_dict.keys():
                            if int(key) == id_dict[ele]:
                                dict0[ele] = key
                if len(dict0.keys())>1:
                    print("element_id can not be None for this file" )
                else:
                    element_id_str0 = list(dict0.values())[0]
            dtype_str = element_map[element_id_str0]

            # loop every station to retrieve record
            if id_type ==0:
                record_head_dtype = [
                    ('id', 'i4'), ('lon', 'f4'), ('lat', 'f4'), ('numb', 'i2')]
                records = []
                if station is None or len(station.index) * 100 > station_number:
                    for i in range(station_number):
                        record_head = np.frombuffer(
                            byteArray[ind:(ind+14)], dtype=record_head_dtype)
                        ind += 14
                        record = {
                            'id': record_head['id'][0], 'lon': record_head['lon'][0],
                            'lat': record_head['lat'][0]}
                        for j in range(record_head['numb'][0]):    # the record element number is not same, missing value is not included.
                            element_id = str(np.frombuffer(byteArray[ind:(ind + 2)], dtype='i2')[0])
                            ind += 2
                            element_len = element_map_len[element_id]
                            if element_id == element_id_str0:
                                record[data_name] = np.frombuffer(
                                    byteArray[ind:(ind + element_len)],
                                    dtype=dtype_str)[0]
                                records.append(record)
                            ind += element_len
                    records = pd.DataFrame(records)
                    records.set_index('id')
                    # get time
                    records['time'] = time
                    records['level'] = level
                    records['dtime'] = dtime
                    new_columns = ['level', 'time', 'dtime', 'id', 'lon', 'lat', data_name]
                    records = records.reindex(columns=new_columns)
                    records.attrs = {}
                    records.attrs["dtime_units"] = dtime_units
                    if station is None:
                        return records
                    else:
                        sta = meteva_base.put_stadata_on_station(records, station)
                        if show:
                            print("success read from " + filename)
                        return sta
                else:
                    sta = copy.deepcopy(station)
                    byte_num = len(byteArray)
                    i4_num = (byte_num - ind -4) //4
                    ids = np.zeros((i4_num,4),dtype=np.int32)

                    ids[:, 0] = np.frombuffer(byteArray[ind:(ind + i4_num * 4)], dtype='i4')
                    ids[:, 1] = np.frombuffer(byteArray[(ind +1):(ind + 1 + i4_num * 4)], dtype='i4')
                    ids[:, 2] = np.frombuffer(byteArray[(ind + 2):(ind + 2 + i4_num * 4)], dtype='i4')
                    ids[:, 3] = np.frombuffer(byteArray[(ind + 3):(ind + 3 + i4_num * 4)], dtype='i4')
                    ids = ids.flatten()
                    station_ids = station["id"].values
                    dat = np.zeros(station_ids.size)

                    for k in range(dat.size):
                        id1 = station_ids[k]
                        indexs = np.where(ids == id1)
                        if len(indexs[0]) >=1:
                            for n in range(len(indexs)):
                                ind1 =ind +  indexs[n][0]
                                record_head = np.frombuffer(byteArray[ind1:(ind1 + 14)], dtype=record_head_dtype)
                                if(record_head['lon'][0] >=-180 and record_head['lon'][0] <= 360 and
                                        record_head['lat'][0] >= -90 and record_head['lat'][0] <= 90 and record_head["numb"][0] < 1000):
                                    ind1 += 14
                                    for j in range(record_head['numb'][0]):  # the record element number is not same, missing value is not included.
                                        element_id = str(np.frombuffer(byteArray[ind1:(ind1 + 2)], dtype='i2')[0])
                                        ind1 += 2
                                        element_len = element_map_len[element_id]
                                        if element_id == element_id_str0:
                                            sta.iloc[k,-1] = np.frombuffer(byteArray[ind1:(ind1 + element_len)],dtype=dtype_str)[0]
                                        ind1 += element_len
                    meteva_base.set_stadata_names(sta,[data_name])
                    sta['time'] = time
                    sta['level'] = level
                    sta['dtime'] = dtime
                    sta.attrs = {}
                    sta.attrs["dtime_units"] = dtime_units
                    if show:
                        print("success read from " + filename)
                    set_stadata_attrs(sta0,units_attr = '',
                                      model_var_attr = '',
                                      dtime_units_attr = 'hour',
                                      level_type_attr = 'isobaric',
                                      time_type_attr = 'UT',
                                      time_bounds_attr = [0,0])
                    return sta

            else:
                record_head_dtype = [
                   ('lon', 'f4'), ('lat', 'f4'), ('numb', 'i2')]
                records = []
                #if station is None or len(station.index) * 100 > station_number:
                for i in range(station_number):
                    string_id_record_length = np.frombuffer( byteArray[ind:(ind + 2)],dtype="i2")[0]
                    dtype1 = "S" + str(string_id_record_length)
                    #print(string_id_record_length)
                    if string_id_record_length==0:
                        string_id ="999999"
                    else:
                        string_id = np.frombuffer(byteArray[ind+2:(ind + 2+string_id_record_length)],dtype=dtype1)[0]
                        string_id = string_id.decode()
                    ind += (2+string_id_record_length)
                    record_head = np.frombuffer(
                        byteArray[ind:(ind + 10)], dtype=record_head_dtype)
                    ind += 10
                    record = {
                        'id': string_id, 'lon': record_head['lon'][0],
                        'lat': record_head['lat'][0]}

                    for j in range(record_head['numb'][
                                       0]):  # the record element number is not same, missing value is not included.
                        element_id = str(np.frombuffer(byteArray[ind:(ind + 2)], dtype='i2')[0])
                        ind += 2
                        element_len = element_map_len[element_id]
                        if element_id == element_id_str0:
                            record[data_name] = np.frombuffer(
                                byteArray[ind:(ind + element_len)],
                                dtype=dtype_str)[0]
                            records.append(record)
                        ind += element_len
                records = pd.DataFrame(records)
                records.set_index('id')
                # get time

                records['time'] = time
                records['level'] = level
                records['dtime'] = dtime
                new_columns = ['level', 'time', 'dtime', 'id', 'lon', 'lat', data_name]
                records = records.reindex(columns=new_columns)
                meteva_base.reset_id(records)
                records.attrs = {}
                records.attrs["dtime_units"] = dtime_units
                if station is None:
                    return records
                else:
                    sta = meteva_base.put_stadata_on_station(records, station)
                    if show:
                        print("success read from " + filename)
                    set_stadata_attrs(sta0,units_attr = '',
                                      model_var_attr = '',
                                      dtime_units_attr = 'hour',
                                      level_type_attr = 'isobaric',
                                      time_type_attr = 'UT',
                                      time_bounds_attr = [0,0])
                    return sta
        except:
            if show:
                exstr = traceback.format_exc()
                print(exstr)
            print(filename + "数据读取失败")
            return None


def read_stawind_from_gds(filename,station = None, level=None,time=None, dtime=None,data_name = "",dtime_units = "hour",show = True):

    if meteva_base.gds_ip_port is None:
        print("请先使用set_config 配置gds的ip和port")
        return
    directory, filename = os.path.split(filename)
    ip,port = meteva_base.gds_ip_port
    service = GDSDataService(ip, port)

    try:
        directory = directory.replace("mdfs:///", "")
        directory = directory.replace("\\","/")
        #print(filename)
        status, response = service.getData(directory, filename)

    except ValueError:
        print('Can not retrieve data' + filename + ' from ' + directory)
        return None
    try:
        ByteArrayResult = DataBlock_pb2.ByteArrayResult()
        if status == 200:
            ByteArrayResult.ParseFromString(response)
            if ByteArrayResult is not None:
                byteArray = ByteArrayResult.byteArray

                head_dtype = [('discriminator', 'S4'), ('type', 'i2'),
                          ('description', 'S100'),
                          ('level', 'f4'), ('levelDescription', 'S50'),
                          ('year', 'i4'), ('month', 'i4'), ('day', 'i4'),
                          ('hour', 'i4'), ('minute', 'i4'), ('second', 'i4'),
                          ('Timezone', 'i4'), ('extent', 'S100')]
                if(len(byteArray)<300):
                    return None
                # read head information
                head_info = np.frombuffer(byteArray[0:288], dtype=head_dtype)
                if time is None:
                    time = datetime.datetime(
                        head_info['year'][0], head_info['month'][0],
                        head_info['day'][0], head_info['hour'][0],
                        head_info['minute'][0], head_info['second'][0])
                else:
                    time = meteva_base.tool.time_tools.all_type_time_to_time64(time)
                if level is None:
                    level = head_info["level"][0]
                if dtime is None:
                    filename1 = os.path.split(filename)[1].split(".")
                    dtime = int(filename1[1])
                ind = 288
                # read the number of stations
                station_number = np.frombuffer(
                    byteArray[ind:(ind+4)], dtype='i4')[0]
                ind += 4

                # read the number of elements
                element_number = np.frombuffer(
                    byteArray[ind:(ind+2)], dtype='i2')[0]

                if element_number == 0:
                    return None
                ind += 2

                # construct record structure
                element_type_map = {
                    1: 'b1', 2: 'i2', 3: 'i4', 4: 'i8', 5: 'f4', 6: 'f8', 7: 'S1'}
                element_map = {}
                element_map_len = {}
                for i in range(element_number):
                    element_id = str(np.frombuffer(byteArray[ind:(ind+2)], dtype='i2')[0])
                    ind += 2
                    element_type = np.frombuffer(
                        byteArray[ind:(ind+2)], dtype='i2')[0]
                    ind += 2
                    element_map[element_id] = element_type_map[element_type]
                    element_map_len[element_id] = int(element_type_map[element_type][1])

                dict0 = {}
                id_dict = meteva_base.gds_element_id_dict
                speed_id = -1
                angle_id = -1
                for key in element_map.keys():
                    if (int(key) in id_dict.values()):
                        for ele in id_dict.keys():
                            if int(key) == id_dict[ele]:
                                dict0[ele] = key
                                if ele.find("风速")>0:
                                    speed_id = key
                                    #print(ele)
                                if ele.find("风向")>0:
                                    angle_id = key
                                    #print(ele)

                if speed_id == -1 or angle_id == -1:
                    print("the file doesn't contains wind")
                dtype_str_speed = element_map[speed_id]
                dtype_str_angle = element_map[angle_id]

                # loop every station to retrieve record
                record_head_dtype = [
                    ('id', 'i4'), ('lon', 'f4'), ('lat', 'f4'), ('numb', 'i2')]
                records = []
                if station is None or len(station.index) * 100 > station_number:
                    for i in range(station_number):
                        record_head = np.frombuffer(
                            byteArray[ind:(ind+14)], dtype=record_head_dtype)
                        ind += 14
                        record = {
                            'id': record_head['id'][0], 'lon': record_head['lon'][0],
                            'lat': record_head['lat'][0]}
                        for j in range(record_head['numb'][0]):    # the record element number is not same, missing value is not included.
                            element_id = str(np.frombuffer(byteArray[ind:(ind + 2)], dtype='i2')[0])
                            ind += 2
                            element_len = element_map_len[element_id]
                            hadwind = False
                            if element_id == speed_id:
                                record["speed"] = np.frombuffer(
                                    byteArray[ind:(ind + element_len)],
                                    dtype=dtype_str_speed)[0]
                                hadwind = True
                            if element_id == angle_id:
                                record["angle"] = np.frombuffer(
                                    byteArray[ind:(ind + element_len)],
                                    dtype=dtype_str_angle)[0]
                                hadwind = True
                            if hadwind:
                                records.append(record)
                            ind += element_len
                    records = pd.DataFrame(records)
                    records.set_index('id')
                    # get time

                    records['time'] = time
                    records['level'] = level
                    records['dtime'] = dtime
                    new_columns = ['level', 'time', 'dtime', 'id', 'lon', 'lat', "speed"+data_name,"angle"+data_name]
                    records = records.reindex(columns=new_columns)
                    records.attrs = {}
                    records.attrs["dtime_units"] = dtime_units
                    if station is None:
                        return records
                    else:
                        sta = meteva_base.put_stadata_on_station(records, station)
                        if show:
                            print("success read from " + filename)
                        set_stadata_attrs(sta0,units_attr = '',
                                          model_var_attr = '',
                                          dtime_units_attr = 'hour',
                                          level_type_attr = 'isobaric',
                                          time_type_attr = 'UT',
                                          time_bounds_attr = [0,0])
                        return sta
                else:
                    sta = copy.deepcopy(station)
                    meteva_base.set_stadata_names(sta,["speed"+data_name])
                    sta["angle"+data_name] = meteva_base.IV
                    byte_num = len(byteArray)
                    i4_num = (byte_num - ind -4) //4
                    ids = np.zeros((i4_num,4),dtype=np.int32)

                    ids[:, 0] = np.frombuffer(byteArray[ind:(ind + i4_num * 4)], dtype='i4')
                    ids[:, 1] = np.frombuffer(byteArray[(ind +1):(ind + 1 + i4_num * 4)], dtype='i4')
                    ids[:, 2] = np.frombuffer(byteArray[(ind + 2):(ind + 2 + i4_num * 4)], dtype='i4')
                    ids[:, 3] = np.frombuffer(byteArray[(ind + 3):(ind + 3 + i4_num * 4)], dtype='i4')
                    ids = ids.flatten()
                    station_ids = station["id"].values
                    dat = np.zeros(station_ids.size)

                    for k in range(dat.size):
                        id1 = station_ids[k]
                        indexs = np.where(ids == id1)
                        if len(indexs[0]) >=1:
                            for n in range(len(indexs)):
                                ind1 =ind +  indexs[n][0]
                                record_head = np.frombuffer(byteArray[ind1:(ind1 + 14)], dtype=record_head_dtype)
                                if(record_head['lon'][0] >=-180 and record_head['lon'][0] <= 360 and
                                        record_head['lat'][0] >= -90 and record_head['lat'][0] <= 90 and record_head["numb"][0] < 1000):
                                    ind1 += 14
                                    for j in range(record_head['numb'][0]):  # the record element number is not same, missing value is not included.
                                        element_id = str(np.frombuffer(byteArray[ind1:(ind1 + 2)], dtype='i2')[0])
                                        ind1 += 2
                                        element_len = element_map_len[element_id]
                                        if element_id == speed_id:
                                            sta.iloc[k,-2] = np.frombuffer(byteArray[ind1:(ind1 + element_len)],dtype=dtype_str_speed)[0]
                                        if element_id == angle_id:
                                            sta.iloc[k,-1] = np.frombuffer(byteArray[ind1:(ind1 + element_len)],dtype=dtype_str_angle)[0]
                                        ind1 += element_len
                    sta['time'] = time
                    sta['level'] = level
                    sta['dtime'] = dtime
                    sta.attrs = {}
                    sta.attrs["dtime_units"] = dtime_units
                    if show:
                        print("success read from " + filename)
                    set_stadata_attrs(sta0,units_attr = '',
                                      model_var_attr = '',
                                      dtime_units_attr = 'hour',
                                      level_type_attr = 'isobaric',
                                      time_type_attr = 'UT',
                                      time_bounds_attr = [0,0])
                    return sta
            else:
                print(filename + " not exist")
                return None
        else:
            print("连接服务的状态异常，不能读取相应的文件,可能原因相应的文件不在允许读取的时段范围")
            return None
    except:
        if show:
            exstr = traceback.format_exc()
            print(exstr)
        print(filename + "数据读取失败")
        return None

def read_stawind_from_gdsfile(filename,station = None, level=None,time=None, dtime=None,data_name = "",dtime_units = "hour",show = False):
    if not os.path.exists(filename):
        print(filename+"文件不存在")
        return None
    elif os.path.isdir(filename):
        print(filename+"是文件夹而不是文件")
        return None
    else :
        try:
            file = open(filename,"rb")
            byteArray = file.read()
            # define head structure
            head_dtype = [('discriminator', 'S4'), ('type', 'i2'),
                          ('description', 'S100'),
                          ('level', 'f4'), ('levelDescription', 'S50'),
                          ('year', 'i4'), ('month', 'i4'), ('day', 'i4'),
                          ('hour', 'i4'), ('minute', 'i4'), ('second', 'i4'),
                          ('Timezone', 'i4'), ('extent', 'S100')]

            # read head information
            head_info = np.frombuffer(byteArray[0:288], dtype=head_dtype)
            if time is None:
                time = datetime.datetime(
                    head_info['year'][0], head_info['month'][0],
                    head_info['day'][0], head_info['hour'][0],
                    head_info['minute'][0], head_info['second'][0])
            else:
                time = meteva_base.tool.time_tools.all_type_time_to_time64(time)

            if level is None:
                level = head_info["level"][0]
            if dtime is None:
                filename1 = os.path.split(filename)[1].split(".")
                dtime = int(filename1[1])
            ind = 288
            # read the number of stations
            station_number = np.frombuffer(
                byteArray[ind:(ind+4)], dtype='i4')[0]
            ind += 4

            # read the number of elements
            element_number = np.frombuffer(
                byteArray[ind:(ind+2)], dtype='i2')[0]

            if element_number == 0:
                return None
            ind += 2

            # construct record structure
            element_type_map = {
                1: 'b1', 2: 'i2', 3: 'i4', 4: 'i8', 5: 'f4', 6: 'f8', 7: 'S1'}
            element_map = {}
            element_map_len = {}
            for i in range(element_number):
                element_id = str(np.frombuffer(byteArray[ind:(ind+2)], dtype='i2')[0])
                ind += 2
                element_type = np.frombuffer(
                    byteArray[ind:(ind+2)], dtype='i2')[0]
                ind += 2
                element_map[element_id] = element_type_map[element_type]
                element_map_len[element_id] = int(element_type_map[element_type][1])

            dict0 = {}
            id_dict = meteva_base.gds_element_id_dict

            speed_id = -1
            angle_id = -1
            for key in element_map.keys():
                if (int(key) in id_dict.values()):
                    for ele in id_dict.keys():
                        if int(key) == id_dict[ele]:
                            dict0[ele] = key
                            if ele.find("风速")>0:
                                speed_id = key
                                print(ele)
                            if ele.find("风向")>0:
                                angle_id = key
                                print(ele)

            if speed_id == -1 or angle_id == -1:
                print("the file doesn't contains wind")
            dtype_str_speed = element_map[speed_id]
            dtype_str_angle = element_map[angle_id]

            # loop every station to retrieve record
            record_head_dtype = [
                ('id', 'i4'), ('lon', 'f4'), ('lat', 'f4'), ('numb', 'i2')]
            records = []
            speed_name = "speed"+data_name
            angle_name = "angle"+data_name
            if station is None or len(station.index) * 100 > station_number:
                for i in range(station_number):
                    record_head = np.frombuffer(
                        byteArray[ind:(ind+14)], dtype=record_head_dtype)
                    ind += 14
                    record = {
                        'id': record_head['id'][0], 'lon': record_head['lon'][0],
                        'lat': record_head['lat'][0]}
                    for j in range(record_head['numb'][0]):    # the record element number is not same, missing value is not included.
                        element_id = str(np.frombuffer(byteArray[ind:(ind + 2)], dtype='i2')[0])
                        ind += 2
                        element_len = element_map_len[element_id]
                        hadwind = False
                        if element_id == speed_id:
                            record[speed_name] = np.frombuffer(
                                byteArray[ind:(ind + element_len)],
                                dtype=dtype_str_speed)[0]
                            hadwind = True
                        if element_id == angle_id:
                            record[angle_name] = np.frombuffer(
                                byteArray[ind:(ind + element_len)],
                                dtype=dtype_str_angle)[0]
                            hadwind = True
                        if hadwind:
                            records.append(record)
                        ind += element_len
                records = pd.DataFrame(records)
                records.set_index('id')
                # get time

                records['time'] = time
                records['level'] = level
                records['dtime'] = dtime
                new_columns = ['level', 'time', 'dtime', 'id', 'lon', 'lat', "speed"+data_name,"angle"+data_name]
                records = records.reindex(columns=new_columns)
                records.attrs = {}
                records.attrs["dtime_units"] = dtime_units
                if station is None:
                    return records
                else:
                    sta = meteva_base.put_stadata_on_station(records, station)
                    if show:
                        print("success read from " + filename)
                    set_stadata_attrs(sta,units_attr = '',
                                      model_var_attr = '',
                                      dtime_units_attr = 'hour',
                                      level_type_attr = 'isobaric',
                                      time_type_attr = 'UT',
                                      time_bounds_attr = [0,0])
                    return sta
            else:
                sta = copy.deepcopy(station)
                meteva_base.set_stadata_names(sta,["speed"+data_name])
                sta["angle"+data_name] = meteva_base.IV
                byte_num = len(byteArray)
                i4_num = (byte_num - ind -4) //4
                ids = np.zeros((i4_num,4),dtype=np.int32)

                ids[:, 0] = np.frombuffer(byteArray[ind:(ind + i4_num * 4)], dtype='i4')
                ids[:, 1] = np.frombuffer(byteArray[(ind +1):(ind + 1 + i4_num * 4)], dtype='i4')
                ids[:, 2] = np.frombuffer(byteArray[(ind + 2):(ind + 2 + i4_num * 4)], dtype='i4')
                ids[:, 3] = np.frombuffer(byteArray[(ind + 3):(ind + 3 + i4_num * 4)], dtype='i4')
                ids = ids.flatten()
                station_ids = station["id"].values
                dat = np.zeros(station_ids.size)

                for k in range(dat.size):
                    id1 = station_ids[k]
                    indexs = np.where(ids == id1)
                    if len(indexs[0]) >=1:
                        for n in range(len(indexs)):
                            ind1 =ind +  indexs[n][0]
                            record_head = np.frombuffer(byteArray[ind1:(ind1 + 14)], dtype=record_head_dtype)
                            if(record_head['lon'][0] >=-180 and record_head['lon'][0] <= 360 and
                                    record_head['lat'][0] >= -90 and record_head['lat'][0] <= 90 and record_head["numb"][0] < 1000):
                                ind1 += 14
                                for j in range(record_head['numb'][0]):  # the record element number is not same, missing value is not included.
                                    element_id = str(np.frombuffer(byteArray[ind1:(ind1 + 2)], dtype='i2')[0])
                                    ind1 += 2
                                    element_len = element_map_len[element_id]
                                    if element_id == speed_id:
                                        sta.iloc[k,-2] = np.frombuffer(byteArray[ind1:(ind1 + element_len)],dtype=dtype_str_speed)[0]
                                    if element_id == angle_id:
                                        sta.iloc[k,-1] = np.frombuffer(byteArray[ind1:(ind1 + element_len)],dtype=dtype_str_angle)[0]
                                    ind1 += element_len
                sta['time'] = time
                sta['level'] = level
                sta['dtime'] = dtime
                sta.attrs = {}
                sta.attrs["dtime_units"] = dtime_units
                if show:
                    print("success read from " + filename)
                set_stadata_attrs(sta,units_attr = '',
                                  model_var_attr = '',
                                  dtime_units_attr = 'hour',
                                  level_type_attr = 'isobaric',
                                  time_type_attr = 'UT',
                                  time_bounds_attr = [0,0])
                return sta
        except:
            if show:
                exstr = traceback.format_exc()
                print(exstr)
            print(filename + "数据读取失败")
            return None


def read_stadata_from_gds_griddata(filename,station,level = None,time =None,dtime = None,data_name = "data0",dtime_units = "hour",show = False):
    # ip 为字符串形式，示例 “10.20.30.40”
    # port 为整数形式
    # filename 为字符串形式 示例 "ECMWF_HR/TCDC/19083108.000"
    if meteva_base.gds_ip_port is None:
        print("请先使用set_config 配置gds的ip和port")
        return
    ip,port = meteva_base.gds_ip_port
    service = GDSDataService(ip, port)
    try:
        if(service is None):
            print("service is None")
            return
        filename = filename.replace("mdfs:///", "")
        filename = filename.replace("\\","/")
        directory,fileName = os.path.split(filename)
        status, response = service.getData(directory, fileName)
        ByteArrayResult = DataBlock_pb2.ByteArrayResult()
        if status == 200:
            ByteArrayResult.ParseFromString(response)
            if ByteArrayResult is not None:
                byteArray = ByteArrayResult.byteArray
                level1, y, m, d, h, timezone, period = struct.unpack("fiiiiii", byteArray[106:134])
                startLon, endLon, dlon, nlon= struct.unpack("fffi", byteArray[134:150])
                startLat, endLat, dlat, nlat = struct.unpack("fffi", byteArray[150:166])
                nsta = len(station.index)
                ig = ((station['lon'].values - startLon) // dlon).astype(dtype='int32')
                jg = ((station['lat'].values - startLat) // dlat).astype(dtype='int32')
                dx = (station['lon'].values - startLon) / dlon - ig
                dy = (station['lat'].values - startLat) / dlat - jg
                c00 = (1 - dx) * (1 - dy)
                c01 = dx * (1 - dy)
                c10 = (1 - dx) * dy
                c11 = dx * dy
                ig1 = np.minimum(ig + 1, nlon - 1)
                jg1 = np.minimum(jg + 1, nlat - 1)
                i00 = (nlon * jg + ig)
                i01 = nlon * jg+ ig1
                i10 = nlon * jg1 + ig
                i11 = nlon * jg1 + ig1
                dat = np.zeros(nsta)
                #i4 = np.arange(4)
                #xx,yy = np.meshgrid(i4,i00)
                #i00 = xx + yy
                #i00 = i00.flatten()
                for i in range(nsta):
                    dat00 = np.frombuffer(byteArray[278 + i00[i] * 4:i00[i] * 4 + 282], dtype='float32')
                    dat01 = np.frombuffer(byteArray[278 + i01[i] * 4:i01[i] * 4 + 282], dtype='float32')
                    dat10 = np.frombuffer(byteArray[278 + i10[i] * 4:i10[i] * 4 + 282], dtype='float32')
                    dat11 = np.frombuffer(byteArray[278 + i11[i] * 4:i11[i] * 4 + 282], dtype='float32')
                    dat[i] = c00[i] * dat00 + c01[i] * dat01 +c10[i] * dat10 + c11[i] * dat11
                #grd.values = np.frombuffer(byteArray[278:], dtype='float32')
                sta = copy.deepcopy(station)
                sta.iloc[:,-1] = dat[:]
                filename1 = os.path.split(filename)[1].split(".")
                #print(filename1)
                if time is None:
                    time = datetime.datetime(y, m, d, h, 0)
                else:
                    time = meteva_base.tool.time_tools.all_type_time_to_time64(time)
                if level is None:
                    level = level1
                if dtime is None:
                    dtime = period
                sta.loc[:, "level"] = level
                sta.loc[:, "time"] = time
                sta.loc[:, "dtime"] = dtime
                meteva_base.set_stadata_names(sta,[data_name])
                sta.attrs = {}
                sta.attrs["dtime_units"] = dtime_units
                if show:
                    print("success read from " + filename)
                set_stadata_attrs(sta0,units_attr = '',
                                  model_var_attr = '',
                                  dtime_units_attr = 'hour',
                                  level_type_attr = 'isobaric',
                                  time_type_attr = 'UT',
                                  time_bounds_attr = [0,0])    
                return sta
            else:
                print(filename + " not exist")
                return None
        else:
            print("连接服务的状态异常，不能读取相应的文件,可能原因相应的文件不在允许读取的时段范围")
            return None
    except :
        if show:
            exstr = traceback.format_exc()
            print(exstr)
        print(filename +" 数据读取失败")
        return None

def print_gds_file_values_names(filename):
    # ip 为字符串形式，示例 “10.20.30.40”
    # port 为整数形式
    # filename 为字符串形式 示例 "ECMWF_HR/TCDC/19083108.000"
    value_id_list= []
    if os.path.exists(filename):
        file = open(filename, "rb")
        byteArray = file.read()
    else:

    #if os.path.exists(filename):
    #    ip,port = None,None
    #else:
        print(filename + "不是本地文件,尝试从服务器上读取相应数据")
        if meteva_base.gds_ip_port is None:
            print("在本地找不到文件"+filename+"考虑它为服务器上的路径")
            print("请先使用set_config 配置gds的ip和port")
            return
        ip,port = meteva_base.gds_ip_port

        filename = filename.replace("mdfs:///", "")
        filename = filename.replace("\\", "/")

        if ip is not None:
            service = GDSDataService(ip, port)
            try:
                directory, fileName = os.path.split(filename)
                status, response = service.getData(directory, fileName)
                ByteArrayResult = DataBlock_pb2.ByteArrayResult()
                if status == 200:
                    ByteArrayResult.ParseFromString(response)
                    if ByteArrayResult is not None:
                        byteArray = ByteArrayResult.byteArray
                else:
                    print("数据内容不可读")
            except:
                exstr = traceback.format_exc()
                print(exstr)


    ind = 288
    # read the number of stations
    station_number = np.frombuffer(
        byteArray[ind:(ind + 4)], dtype='i4')[0]
    ind += 4

    # read the number of elements
    element_number = np.frombuffer(
        byteArray[ind:(ind + 2)], dtype='i2')[0]

    if element_number == 0:
        return None
    ind += 2

    # construct record structure
    element_type_map = {
        1: 'b1', 2: 'i2', 3: 'i4', 4: 'i8', 5: 'f4', 6: 'f8', 7: 'S1'}
    element_map = {}
    element_map_len = {}
    for i in range(element_number):
        element_id = str(np.frombuffer(byteArray[ind:(ind + 2)], dtype='i2')[0])
        ind += 2
        element_type = np.frombuffer(
            byteArray[ind:(ind + 2)], dtype='i2')[0]
        ind += 2
        element_map[element_id] = element_type_map[element_type]
        element_map_len[element_id] = int(element_type_map[element_type][1])
    id_dict = meteva_base.gds_element_id_dict

    dict0 = {}
    for key in element_map.keys():
        if(int(key) in id_dict.values()):
            for ele in id_dict.keys():
                if int(key) == id_dict[ele]:
                    dict0[ele] = int(key)
                    print(ele + ":" + key)
    return dict0

def read_stadata_from_micaps16(filename,level = None,time= None,dtime = None,data_name = "data0",dtime_units = "hour",show = False):
    if not os.path.exists(filename):
        print(filename+"文件不存在")
        return None
    elif os.path.isdir(filename):
        print(filename+"是文件夹而不是文件")
        return None
    else:
        encoding,_ = meteva_base.io.get_encoding_of_file(filename,read_rows=1)
        if encoding is None:
            print("文件编码格式不识别")
            return None
        try:
            file = open(filename, 'r',encoding=encoding)
            head = file.readline()
            head = file.readline()
            stationids = []
            row1 = []
            row2 = []
            row3 = []
            while(head is not None and head.strip() != ""):
                strs = head.split()
                stationids.append(strs[0])
                a = int(strs[1])
                b = a // 100 + (a % 100) /60
                row1.append(b)
                a = int(strs[2])
                b = a // 100 + (a % 100) /60
                row2.append(b)
                row3.append(float(strs[3]))
                head =  file.readline()

            row1 = np.array(row1)
            row2 = np.array(row2)
            row3 = np.array(row3)
            ids = np.array(stationids)
            dat = np.zeros((len(row1),4))
            dat[:,0] = ids[:]
            if(np.max(row2) > 90 or np.min(row2) <-90):
                dat[:,1] = row2[:]
                dat[:,2] = row1[:]
            else:
                dat[:,1] = row1[:]
                dat[:,2] = row2[:]
            dat[:,3] = row3[:]
            station = pd.DataFrame(dat, columns=['id','lon', 'lat', data_name])
            station = meteva_base.sta_data(station)
            meteva_base.set_stadata_coords(station,level=level,time= time,dtime = dtime)
            station.attrs = {}
            station.attrs["dtime_units"] = dtime_units
            if show:
                print("success read from " + filename)
            return station
        except:
            if show:
                exstr = traceback.format_exc()
                print(exstr)
            print(filename+"文件格式不能识别。可能原因：文件未按micaps16格式存储")
            return None


def read_stadata_from_gds_griddata_file(filename,station,level = None,time = None,dtime = None,data_name = "data0",dtime_units = "hour",show = False):

    if not os.path.exists(filename):
        print(filename+"文件不存在")
        return None
    elif os.path.isdir(filename):
        print(filename+"是文件夹而不是文件")
        return None

    else:
        try:
            file = open(filename,"rb")
            position = file.seek(106)
            content = file.read(28)
            level1, y, m, d, h, timezone, period = struct.unpack("fiiiiii", content)
            position = file.seek(134)
            content = file.read(32)
            slon, elon, dlon,nlon,slat,elat,dlat,nlat = struct.unpack("fffifffi", content)
            nsta = len(station.index)
            ig = ((station['lon'].values - slon) // dlon).astype(dtype='int32')
            jg = ((station['lat'].values - slat) // dlat).astype(dtype='int32')
            dx = (station['lon'].values - slon) / dlon - ig
            dy = (station['lat'].values - slat) / dlat - jg
            c00 = (1 - dx) * (1 - dy)
            c01 = dx * (1 - dy)
            c10 = (1 - dx) * dy
            c11 = dx * dy
            ig1 = np.minimum(ig + 1, nlon - 1)
            jg1 = np.minimum(jg + 1, nlat - 1)
            i00 = (nlon * jg + ig)
            i01 = nlon * jg + ig1
            i10 = nlon * jg1 + ig
            i11 = nlon * jg1 + ig1
            dat = np.zeros(nsta)
            for i in range(nsta):
                position = file.seek(i00[i] * 4+278)
                content = file.read(4)
                dat00 = np.frombuffer(content, dtype='float32')
                position = file.seek(i01[i] * 4+278)
                content = file.read(4)
                dat01 = np.frombuffer(content, dtype='float32')
                position = file.seek(i10[i] * 4+278)
                content = file.read(4)
                dat10 = np.frombuffer(content, dtype='float32')
                position = file.seek(i11[i] * 4+278)
                content = file.read(4)
                dat11 = np.frombuffer(content, dtype='float32')
                dat[i] = c00[i] * dat00 + c01[i] * dat01 + c10[i] * dat10 + c11[i] * dat11
            file.close()
            sta = copy.deepcopy(station)
            sta.iloc[:, -1] = dat[:]
            if time is None:
                time = datetime.datetime(y, m, d, h, 0)
            else:
                time = meteva_base.tool.time_tools.all_type_time_to_time64(time)
            if level is None:
                level = level1
            if dtime is None:
                dtime = period
            sta.loc[:, "level"] = level
            sta.loc[:, "time"] = time
            sta.loc[:, "dtime"] = dtime
            meteva_base.set_stadata_names(sta, [data_name])
            sta.attrs = {}
            sta.attrs["dtime_units"] = dtime_units
            if show:
                print("success read from " + filename)
            set_stadata_attrs(sta0,units_attr = '',
                              model_var_attr = '',
                              dtime_units_attr = 'hour',
                              level_type_attr = 'isobaric',
                              time_type_attr = 'UT',
                              time_bounds_attr = [0,0])
            return sta
        except:
            if show:
                exstr = traceback.format_exc()
                print(exstr)
            print(filename+"文件格式不能识别")
            return None


def read_stawind_from_gds_gridwind_file(filename,station,level = None,time = None,dtime = None,data_name = "",dtime_units = "hour",show = False):

    if not os.path.exists(filename):
        print(filename+"文件不存在")
        return None
    elif os.path.isdir(filename):
        print(filename+"是文件夹而不是文件")
        return None
    else:
        try:
            file = open(filename, "rb")
            position = file.seek(106)
            content = file.read(28)
            level1, y, m, d, h, timezone, period = struct.unpack("fiiiiii", content)
            position = file.seek(134)
            content = file.read(32)
            slon, elon, dlon, nlon, slat, elat, dlat, nlat = struct.unpack("fffifffi", content)
            nsta = len(station.index)
            ig = ((station['lon'].values - slon) // dlon).astype(dtype='int32')
            jg = ((station['lat'].values - slat) // dlat).astype(dtype='int32')
            dx = (station['lon'].values - slon) / dlon - ig
            dy = (station['lat'].values - slat) / dlat - jg
            c00 = (1 - dx) * (1 - dy)
            c01 = dx * (1 - dy)
            c10 = (1 - dx) * dy
            c11 = dx * dy
            ig1 = np.minimum(ig + 1, nlon - 1)
            jg1 = np.minimum(jg + 1, nlat - 1)
            i00 = (nlon * jg + ig)
            i01 = nlon * jg + ig1
            i10 = nlon * jg1 + ig
            i11 = nlon * jg1 + ig1
            udata = np.zeros(nsta)
            vdata = np.zeros(nsta)
            i_s0 = 278
            i_s1 = i_s0 + nlon * nlat * 4

            for i in range(nsta):
                position = file.seek(i00[i] * 4 + i_s0)
                content = file.read(4)
                dat00 = np.frombuffer(content, dtype='float32')
                position = file.seek(i01[i] * 4 + i_s0)
                content = file.read(4)
                dat01 = np.frombuffer(content, dtype='float32')
                position = file.seek(i10[i] * 4 + i_s0)
                content = file.read(4)
                dat10 = np.frombuffer(content, dtype='float32')
                position = file.seek(i11[i] * 4 + i_s0)
                content = file.read(4)
                dat11 = np.frombuffer(content, dtype='float32')
                udata[i] = c00[i] * dat00 + c01[i] * dat01 + c10[i] * dat10 + c11[i] * dat11

                position = file.seek(i00[i] * 4 + i_s1)
                content = file.read(4)
                dat00 = np.frombuffer(content, dtype='float32')
                position = file.seek(i01[i] * 4 + i_s1)
                content = file.read(4)
                dat01 = np.frombuffer(content, dtype='float32')
                position = file.seek(i10[i] * 4 + i_s1)
                content = file.read(4)
                dat10 = np.frombuffer(content, dtype='float32')
                position = file.seek(i11[i] * 4 + i_s1)
                content = file.read(4)
                dat11 = np.frombuffer(content, dtype='float32')
                vdata[i] = c00[i] * dat00 + c01[i] * dat01 + c10[i] * dat10 + c11[i] * dat11
            file.close()
            sta = copy.deepcopy(station)
            sta.iloc[:, -1] = udata[:]
            sta["v"] = vdata
            if time is None:
                time = datetime.datetime(y, m, d, h, 0)
            else:
                time = meteva_base.tool.time_tools.all_type_time_to_time64(time)
            if level is None:
                level = level1
            if dtime is None:
                dtime = period
            sta.loc[:, "level"] = level
            sta.loc[:, "time"] = time
            sta.loc[:, "dtime"] = dtime
            meteva_base.set_stadata_names(sta,["u"+data_name,"v"+data_name])
            sta.attrs = {}
            sta.attrs["dtime_units"] = dtime_units
            if show:
                print("success read from " + filename)
            set_stadata_attrs(sta,units_attr = '',
                              model_var_attr = '',
                              dtime_units_attr = 'hour',
                              level_type_attr = 'isobaric',
                              time_type_attr = 'UT',
                              time_bounds_attr = [0,0])
            return sta
        except:
            if show:
                exstr = traceback.format_exc()
                print(exstr)
            print(filename + "文件格式不能识别")
            return None


def read_stadata_from_cmadaas(dataCode,element,time,station = None,level=0,dtime=0,data_name= None,id_type = "Station_Id_D",dtime_units = "hour",show = False):
    ## stations
    qparams = {'interfaceId': 'getSurfEleByTime',
               'dataCode': dataCode,
               'elements': 'Datetime,' + id_type+',Lat,Lon,'+element,
               }  ##字典规定接口名称，数据代码，下载要素代码。
    # 数据部分： SURF_CHN_MUL_HOR_N 数据为全国基准站(2400多站点)逐小时地面要素
    # 接口部分： getSurfEleByTime 接口为按时间提取地面要素
    # 要素部分： PRE_24h 为地面降水，其他包括TEM、TEM_Max、RHU、WIN_D_Avg_10mi、WIN_S_Avg_10mi等，可自己选择
    time = meteva_base.all_type_time_to_datetime(time)
    time_str = time.strftime("%Y%m%d%H%M")
    userID = meteva_base.cmadaas_set[2]
    pwd = meteva_base.cmadaas_set[3]
    try:
        sta = CMADaasAccess.get_obs_micaps3_from_cmadaas(qparams, userId=userID, pwd=pwd, time=time_str,show=show)
    except:
        if show:
            exstr = traceback.format_exc()
            print(exstr)
        return None
    if sta is not None:
        if data_name is None:
            data_name = element
        meteva_base.set_stadata_names(sta,data_name_list=[data_name])
        sta['level'] = level
        sta['dtime'] = dtime
        if (station is not None):
            sta = meteva_base.put_stadata_on_station(sta, station)
    else:
        print("数据读取失败")
    sta.attrs = {}
    sta.attrs["dtime_units"] = dtime_units
    set_stadata_attrs(sta,units_attr = '',
                      model_var_attr = '',
                      dtime_units_attr = 'hour',
                      level_type_attr = 'isobaric',
                      time_type_attr = 'UT',
                      time_bounds_attr = [0,0])
    return sta


def read_stadata_from_cimiss(dataCode,element,time,station = None,level = 0,dtime = 0,id_type = "Station_Id_D",dtime_units = "hour",show = False):

    time1 = meteva_base.all_type_time_to_datetime(time)
    time_str = time1.strftime("%Y%m%d%H%M%S")
    if dataCode.find("UPAR_")>=0:
        interface_id = "getUparEleByTime"
    else:
        interface_id = "getSurfEleByTime"
    params = {'dataCode': dataCode,
              'times': time_str,
              'orderby': "Station_Id_d",
              'elements': "Station_Id_d,lon,lat,"+element}

    contents = get_http_result_cimiss(interface_id,params,show_url=show)
    if contents is None:
        return None
    try:
        contents = json.loads(contents.decode('utf-8'))
        if contents['returnCode'] != '0':
            return None

        # construct pandas DataFrame
        df = pd.DataFrame(contents['DS'])
        data1 =df.iloc[0,3]
        if isinstance(data1,str):
            df[element] = df[element].astype("float")
        sta = meteva_base.sta_data(df,columns=["id","lon","lat",element])

        #sta.time = pd.to_datetime(sta.time)
        #sta.level = sta.level.astype(np.int16)
        sta.id = sta.id.astype(np.int32)
        #sta.dtime = sta.dtime.astype(np.int16)
        sta.lon = sta.lon.astype(np.float32)
        sta.lat = sta.lat.astype(np.float32)
        #sta.data0 = sta.data0.astype(np.float32)
        #sta.data0[sta.data0 >= 10000] = default

        meteva_base.set_stadata_coords(sta,time = time1,dtime=dtime,level=level)
        if (station is not None):
            sta = meteva_base.put_stadata_on_station(sta, station)
        return sta
    except:
        if show:
            exstr = traceback.format_exc()
            print(exstr)
        return None


def read_cyclone_trace(filename, id_cyclone,column=8,  data_name="data0",dtime_units = "hour",show = False):
    try:
        column_all = [0, 1, 2, 3, 4, 5, 6]
        if isinstance(column, list):
            column_all.extend(column)
        else:
            column_all.append(column)

        encoding, _ = meteva_base.io.get_encoding_of_file(filename,read_rows=1)
        if encoding is None:
            print("文件编码格式不识别")
            return None

        sta1 = pd.read_csv(filename, skiprows=2, sep="\s+", header=None,
                           usecols=column_all,encoding=encoding)

        dict1 = meteva_base.m7_element_column_dict
        dict2 = dict([val, key] for key, val in dict1.items())

        if len(column_all) == 8:
            dat_dict = {"level": {}, "time": {}, "dtime": {}, "id": {}, "lon": {}, "lat": {}, data_name: {} }
        else:
            dat_dict = {"level": {}, "time": {}, "dtime": {}, "id": {}, "lon": {}, "lat": {}}
            for j in range(7, len(column_all)):
                k = column_all[j]
                name = dict2[k]
                dat_dict[name] = {}

        for i in range(len(sta1.index)):
            dat_dict["level"][i] = 0
            dat_dict["time"][i] = datetime.datetime(sta1.iloc[i, 0], sta1.iloc[i, 1], sta1.iloc[i, 2], sta1.iloc[i, 3])
            dat_dict["dtime"][i] = sta1.iloc[i, 4]
            dat_dict["id"][i] = id_cyclone
            dat_dict["lon"][i] = sta1.iloc[i, 5]
            dat_dict["lat"][i] = sta1.iloc[i, 6]
            if len(column_all) == 8:
                dat_dict[data_name][i] = sta1.iloc[i, -1]
            else:
                for j in range(7,len(column_all)):
                    k = column_all[j]
                    name = dict2[k]
                    dat_dict[name][i] = sta1.iloc[i, j]

        sta2 = pd.DataFrame(dat_dict)
        sta2.attrs = {}
        sta2.attrs["dtime_units"] = dtime_units
        set_stadata_attrs(sta2,units_attr = '',
                          model_var_attr = '',
                          dtime_units_attr = 'hour',
                          level_type_attr = 'isobaric',
                          time_type_attr = 'UT',
                          time_bounds_attr = [0,0])
        return sta2
    except:
        if show:
            exstr = traceback.format_exc()
            print(exstr)
        return None

def read_stadata_from_hdf(filename):
    if not os.path.exists(filename):
        print(filename+"文件不存在")
        return None
    elif os.path.isdir(filename):
        print(filename+"是文件夹而不是文件")
        return None
    elif os.path.isdir(filename):
        print(filename+"是文件夹而不是文件")
        return None
    
    sta0=pd.read_hdf(filename)
    with h5py.File(filename, 'a') as file:
        if 'units' in file.attrs:
            units=file.attrs['units']
        else:
            units=''
            
        if 'model' in file.attrs:
            model=file.attrs['model']
        else:
            model=''
            
        if 'level_type' in file.attrs:
            level_type=file.attrs['level_type']
        else:
            level_type='isobaric'
            
        if 'dtime_units' in file.attrs:
            dtime_units=file.attrs['dtime_units']
        else:
            dtime_units='hour'
            
        if 'time_bound' in file.attrs:
            time_bounds=file.attrs['time_bounds']
        else:
            time_bounds=[0,0]
            
        if 'time_type' in file.attrs:
            time_type=file.attrs['time_type']
        else:
            time_type='UT'
    set_stadata_attrs(sta0,units_attr = units,
                      model_var_attr = model,
                      dtime_units_attr = dtime_units,
                      level_type_attr = level_type
                      ,time_type_attr = time_type,
                      time_bounds_attr = time_bounds)
        
    return sta0

def read_stadata_from_csv(filename):
    if not os.path.exists(filename):
        print(filename+"文件不存在")
        return None
    elif os.path.isdir(filename):
        print(filename+"是文件夹而不是文件")
        return None
    elif os.path.isdir(filename):
        print(filename+"是文件夹而不是文件")
        return None
    
    
    with open(filename,'r+') as f:
        content=f.readlines()

        if content[0]=='attrs,values'+'\n':
            sta0=pd.read_csv(filename,skiprows=7)
            infos=content[1:7]
            attrs=[]
            values=[]
            for info in infos:
                info=info.replace('\n','')
                info=info.replace('"','')
                attr=info.split(',')[0]
                attrs.append(attr)
                value=info.split(',',1)[1]
                values.append(value)
                print(attr,value)
            attrs_dict = dict(zip(attrs, values))
            set_stadata_attrs(sta0,units_attr = attrs_dict['units'],
                              model_var_attr = attrs_dict['model'],
                              dtime_units_attr = attrs_dict['dtime_units'],
                              level_type_attr = attrs_dict['level_type'],
                              time_type_attr = attrs_dict['time_type'],
                              time_bounds_attr =attrs_dict['time_bounds'])
        else:
            sta0=pd.read_csv(filename)
            set_stadata_attrs(sta0,units_attr = '',
                              model_var_attr = '',
                              dtime_units_attr = 'hour',
                              level_type_attr = 'isobaric',
                              time_type_attr = 'UT',
                              time_bounds_attr = [0,0])
    
    return sta0
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    