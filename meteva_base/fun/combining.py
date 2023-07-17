import pandas as pd
import copy
import meteva_base
import datetime
import math
import numpy as np

def concat(data_list):
    data1_list = []
    for data in data_list:
        if data is not None:
            data1_list.append(data)
    if len(data1_list) == 0:
        print("无需要拼接的数据")
        return

    if isinstance(data1_list[0], pd.DataFrame):
        sta = pd.concat(data1_list,axis=0)
        sta.drop_duplicates(keep="first",inplace=True)
        sta.attrs = copy.deepcopy(data1_list[0].attrs)
        #sta[["dtime"]] = sta[['dtime']].astype(int)
        return sta
    else:
        ngrd = len(data1_list)
        grid_combined = None
        for i in range(ngrd):
            grid1 = meteva_base.get_grid_of_data(data1_list[i])
            grid_combined = meteva_base.get_outer_grid(grid_combined, grid1, used_coords="all")
        grd_all = meteva_base.grid_data(grid_combined)
        grid_xy = meteva_base.grid(grid_combined.glon, grid_combined.glat)
        grd_all.values[:, :, :, :, :, :] = meteva_base.IV
        levels_all = grd_all["level"].values
        times_all = grd_all["time"].values
        dtimes_all = grd_all["dtime"].values
        members_all = grd_all["member"].values
        index_level = {}
        for i in range(len(levels_all)):
            index_level[levels_all[i]] = i
        index_time = {}
        for i in range(len(times_all)):
            index_time[times_all[i]] = i
        index_dtime = {}
        for i in range(len(dtimes_all)):
            index_dtime[dtimes_all[i]] = i
        index_member = {}
        for i in range(len(members_all)):
            index_member[members_all[i]] = i

        for x in range(ngrd):
            grd_interp = meteva_base.interp_gg_linear(data1_list[x], grid_xy)
            levels = grd_interp["level"].values
            times = grd_interp["time"].values
            dtimes = grd_interp["dtime"].values
            members = grd_interp["member"].values
            for i in range(len(levels)):
                i_level = index_level[levels[i]]
                for j in range(len(times)):
                    i_time = index_time[times[j]]
                    for k in range(len(dtimes)):
                        i_dtime = index_dtime[dtimes[k]]
                        for m in range(len(members)):
                            i_member = index_member[members[m]]
                            grd_all.values[i_member, i_level, i_time, i_dtime, :, :] = grd_interp.values[m, i, j, k, :,:]
        grd_all.attrs = copy.deepcopy(data1_list[0].attrs)
        return grd_all

# 两个站点信息合并为一个，在原有的dataframe的基础上增加行数
def combine_join(sta, sta1):
    if (sta is None):
        return sta1
    elif (sta1 is None):
        return sta
    else:
        data_name1 = meteva_base.basicdata.get_stadata_names(sta)
        data_name2 = meteva_base.basicdata.get_stadata_names(sta1)
        if data_name1 == data_name2:
            sta = concat([sta, sta1])
        else:
            sta2 = copy.deepcopy(sta1)
            meteva_base.basicdata.set_stadata_names(sta2,data_name1)
            sta = concat([sta, sta2])
    sta = sta.reset_index(drop=True)
    return sta


# 两个站点信息合并为一个，以站号为公共部分，在原有的dataframe的基础上增加列数
def combine_on_id(sta, sta1,how = "inner"):
    if sta is None:
        return sta1
    elif sta1 is None:
        return sta
    else:
        df = pd.merge(sta, sta1, on='id', how=how)
        columns = list(sta.columns)
        len_sta = len(columns)
        # 删除合并后第二组时空坐标信息
        drop_col = list(df.columns[len_sta:len_sta + 5])
        df.drop(drop_col, axis=1, inplace=True)
        columns_dim = list(sta.columns)[0:6]
        columns_data = list(df.columns)[6:]
        columns = columns_dim + columns_data
        df.columns = columns
        df.attrs = copy.deepcopy(sta.attrs)
        return df

def that_the_name_exists(list, value):
    '''
    that_the_name_exists判断value是否在list中  如果存在改value直到不在list中为止
    :param list: 一个要素名列表
    :param value:  要素名
    :return:
    '''
    value = str(value)
    list = [str(i) for i in list]
    if value in list:
        value = str(value) + 'x'
        return that_the_name_exists(list, value)
    else:
        return value

#  两个站点信息合并为一个，以站号为公共部分，在原有的dataframe的基础上增加列数
def combine_on_all_coords(sta, sta1,how = "inner"):
    '''
    merge_on_all_dim 合并两个sta_dataframe并且使要素名不重复
    :param sta: 一个站点dataframe
    :param sta1: 一个站点dataframe
    :return:
    '''
    if (sta is None):
        return sta1
    elif sta1 is None:
        return sta
    else:
        columns = ['level', 'time', 'dtime', 'id', 'lon', 'lat']
        sta_value_columns = sta.iloc[:, 6:].columns.values.tolist()
        sta1_value_columns = sta1.iloc[:, 6:].columns.values.tolist()
        if len(sta_value_columns) >= len(sta1_value_columns):

            for sta1_value_column in sta1_value_columns:
                ago_name = copy.deepcopy(sta1_value_column)
                sta1_value_column = that_the_name_exists(sta_value_columns, sta1_value_column)
                sta1.rename(columns={ago_name: sta1_value_column},inplace=True)
        else:
            for sta_value_column in sta_value_columns:
                ago_name = copy.deepcopy(sta_value_column)
                sta_value_column = that_the_name_exists(sta1_value_columns, sta_value_column)
                sta.rename(columns={ago_name: sta_value_column})
        df = pd.merge(sta, sta1, on=columns, how=how)
        df.attrs = copy.deepcopy(sta.attrs)
        return df

def combine_on_leve_time_id(sta,sta1):
    '''
    merge_on_all_dim 合并两个sta_dataframe并且使要素名不重复
    :param sta: 一个站点dataframe
    :param sta1: 一个站点dataframe
    :return:
    '''
    if (sta is None):
        return sta1
    elif sta1 is None:
        return sta
    else:
        columns = ['level', 'time',  'id']
        sta_value_columns = sta.iloc[:, 6:].columns.values.tolist()
        sta2 = copy.deepcopy(sta1)
        sta2_value_columns = sta2.iloc[:, 6:].columns.values.tolist()

        if len(sta_value_columns) >= len(sta2_value_columns):
            for sta2_value_column in sta2_value_columns:
                ago_name = copy.deepcopy(sta2_value_column)
                sta2_value_column = that_the_name_exists(sta_value_columns, sta2_value_column)
                sta2.rename(columns={ago_name: sta2_value_column},inplace=True)
        else:
            for sta_value_column in sta_value_columns:
                ago_name = copy.deepcopy(sta_value_column)
                sta_value_column = that_the_name_exists(sta2_value_columns, sta_value_column)
                sta.rename(columns={ago_name: sta_value_column})
        sta2.drop(['dtime',"lon","lat"], axis=1, inplace=True)
        df = pd.merge(sta, sta2, on=columns, how='inner')
        df.attrs = copy.deepcopy(sta.attrs)
        return df

def combine_on_level_time_dtime_id(sta, sta1,how = 'inner'):
    '''
    merge_on_all_dim 合并两个sta_dataframe并且使要素名不重复
    :param sta: 一个站点dataframe
    :param sta1: 一个站点dataframe
    :return:
    '''

    if (sta is None):
        return sta1
    elif sta1 is None:
        return sta
    else:
        columns = ['level', 'time', 'dtime', 'id']
        sta_value_columns = sta.iloc[:, 6:].columns.values.tolist()
        sta2 = copy.deepcopy(sta1)
        sta2_value_columns = sta2.iloc[:, 6:].columns.values.tolist()

        if len(sta_value_columns) >= len(sta2_value_columns):
            for sta2_value_column in sta2_value_columns:
                ago_name = copy.deepcopy(sta2_value_column)
                sta2_value_column = that_the_name_exists(sta_value_columns, sta2_value_column)
                sta2.rename(columns={ago_name: sta2_value_column},inplace=True)
        else:
            for sta_value_column in sta_value_columns:
                ago_name = copy.deepcopy(sta_value_column)
                sta_value_column = that_the_name_exists(sta2_value_columns, sta_value_column)
                sta.rename(columns={ago_name: sta_value_column})
        if(how == "inner"):
            sta2.drop(["lon","lat"], axis=1, inplace=True)
            df = pd.merge(sta, sta2, on=columns, how=how)
        else:
            sta3 = sta.copy()
            #sta3.drop(["lon","lat"], axis=1, inplace=True)
            df = pd.merge(sta3, sta2, on=columns, how=how)
            index = np.isnan(df.loc[:,"lon_x"])
            if index.size >0:
                df.loc[index,"lon_x"] = df.loc[index,"lon_y"]
                df.loc[index,"lat_x"] = df.loc[index,"lat_y"]
            df.drop(["lon_y","lat_y"], axis=1, inplace=True)
            columns_Name = df.columns.values.tolist()
            columns_Name[4] = "lon"
            columns_Name[5] = "lat"
            df.columns = columns_Name
            if(len(df.index) == 0):
                print("no matched line")
                return None
            df = meteva_base.sta_data(df)
        df.attrs = copy.deepcopy(sta.attrs)
        return df


def combine_on_level_time_dtime(sta, sta1,how = 'inner'):
    '''
    merge_on_all_dim 合并两个sta_dataframe并且使要素名不重复
    :param sta: 一个站点dataframe
    :param sta1: 一个站点dataframe
    :return:
    '''
    if (sta is None):
        return sta1
    elif sta1 is None:
        return sta
    else:
        columns = ['level', 'time', 'dtime']
        sta_value_columns = sta.iloc[:, 6:].columns.values.tolist()
        sta2 = copy.deepcopy(sta1)
        sta2_value_columns = sta2.iloc[:, 6:].columns.values.tolist()

        if len(sta_value_columns) >= len(sta2_value_columns):
            for sta2_value_column in sta2_value_columns:
                ago_name = copy.deepcopy(sta2_value_column)
                sta2_value_column = that_the_name_exists(sta_value_columns, sta2_value_column)
                sta2.rename(columns={ago_name: sta2_value_column},inplace=True)
        else:
            for sta_value_column in sta_value_columns:
                ago_name = copy.deepcopy(sta_value_column)
                sta_value_column = that_the_name_exists(sta2_value_columns, sta_value_column)
                sta.rename(columns={ago_name: sta_value_column})
        if(how == "inner"):
            sta2.drop(["id","lon","lat"], axis=1, inplace=True)
            df = pd.merge(sta, sta2, on=columns, how=how)
        else:
            sta3 = sta.copy()
            sta3.drop(["id","lon","lat"], axis=1, inplace=True)
            df = pd.merge(sta3, sta2, on=columns, how=how)
            if(len(df.index) == 0):
                print("no matched line")
                return None
            df = meteva_base.sta_data(df)
        df.attrs = copy.deepcopy(sta.attrs)
        return df


def combine_on_obTime_id(sta_ob,sta_fo_list,need_match_ob = False,how_fo = "inner"):
    '''
    将观测
    :param sta_ob:
    :param sta_fo_list:
    :return:
    '''
    if not isinstance(sta_fo_list, list):
        sta_fo_list = [sta_fo_list]
    #预报时效的时间处理
    dtime_units = "hour"
    for sta_fo1 in sta_fo_list:
        if sta_fo1.attrs is not None:
            if "dtime_units" in sta_fo1.attrs.keys():
            # if len(sta_fo1.attrs) >0:
                if(sta_fo1.attrs["dtime_units"] != "hour"):
                    dtime_units = "minute"
    if dtime_units != "hour":
        for sta_fo1 in sta_fo_list:
            if len(sta_fo1.attrs)  == 0 or sta_fo1.attrs["dtime_units"] == "hour" :
                sta_fo1["dtime"] *= 60
                sta_fo1.attrs["dtime_units"] = "minute"


    dtime_list = list(set(sta_fo_list[0]['dtime'].values.tolist()))
    nsta_ob = len(sta_ob.index)
    if(nsta_ob * len(dtime_list) >= 10000000):
        if nsta_ob >= 10000000:
            print("请注意，在大规模数据匹配合并时，need_match_ob 参数将自动切换为True")
            return combine_on_obTime_id_bigData(sta_ob,sta_fo_list,how_fo = how_fo)
        else:
            return combine_on_obTime_id_bigData(sta_ob, sta_fo_list,need_match_ob=need_match_ob,g = "dtime",how_fo= how_fo)
    else:


        sta_combine_fo = None
        for sta_fo in sta_fo_list:
            sta_combine_fo = combine_on_level_time_dtime_id(sta_combine_fo, sta_fo,how = how_fo)
            if sta_combine_fo is not None:
                sta_combine_fo = sta_combine_fo.fillna(meteva_base.IV)


        if sta_ob is None:
            sta_combine = None
        else:
            dtime_list = list(set(sta_combine_fo['dtime'].values.tolist()))
            sta_combine = []
            for dtime in dtime_list:
                sta = copy.deepcopy(sta_ob)
                if dtime_units == "hour":
                    sta["time"] = sta["time"] - datetime.timedelta(hours= dtime)
                else:
                    sta["time"] = sta["time"] - datetime.timedelta(minutes=dtime)
                sta["dtime"] = dtime
                sta_combine.append(sta)
            sta_combine = concat(sta_combine)

        if need_match_ob:
            sta_combine = meteva_base.not_IV(sta_combine)
            sta_combine = combine_on_level_time_dtime_id(sta_combine, sta_combine_fo, how="inner")
        else:
            sta_combine = combine_on_level_time_dtime_id(sta_combine,sta_combine_fo,how="right")
            if sta_combine is not None:
                sta_combine = sta_combine.fillna(meteva_base.IV)

        if sta_combine is None:
            print("观测和预报数据未能实现匹配，请检查观测和预报的层次、时间、时效、站号是否有严格的匹配关系")
        meteva_base.set_stadata_attrs(sta_combine,dtime_units=dtime_units)
        sta_combine.attrs = copy.deepcopy(sta_ob.attrs)
        sta_combine.drop_duplicates(subset=["level", "time", "dtime", "id"], inplace=True)
        sta_combine.sort_values(by=["level", "time", "dtime", "id"], inplace=True)
        return sta_combine


def combine_on_obTime_one_id(sta_ob,sta_fo_list,how = "inner",how_fo = "inner"):
    '''
    将观测
    :param sta_ob:
    :param sta_fo_list:
    :return:
    '''
    if not isinstance(sta_fo_list, list):
        sta_fo_list = [sta_fo_list]

    dtime_units ="hour"
    if len(sta_fo_list[0].attrs) >0:
        if "dtime_units" in sta_fo_list[0].attrs:
            if sta_fo_list[0].attrs["dtime_units"] != "hour":
                dtime_units = "minute"

    sta_combine_fo = None
    for sta_fo in sta_fo_list:
        sta_combine_fo = combine_on_level_time_dtime(sta_combine_fo, sta_fo,how= how_fo)

    if sta_ob is None:
        sta_combine = None
    else:
        dtime_list = list(set(sta_combine_fo['dtime'].values.tolist()))
        #print(dtime_list)
        sta_combine = []
        for dtime in dtime_list:
            sta = copy.deepcopy(sta_ob)
            if dtime_units == "hour":
                sta["time"] = sta["time"] - datetime.timedelta(hours= dtime)
            else:
                sta["time"] = sta["time"] - datetime.timedelta(minutes=dtime)
            sta["dtime"] = dtime
            sta_combine.append(sta)
        sta_combine = concat(sta_combine)

    sta_combine = combine_on_level_time_dtime(sta_combine, sta_combine_fo,how = how)
    if sta_combine is not None:
        sta_combine = sta_combine.fillna(meteva_base.IV)
    sta_combine.attrs = copy.deepcopy(sta_ob.attrs)
    return sta_combine

def combine_on_obTime_id_bigData(sta_ob,sta_fo_list,need_match_ob = True,g = "id",how_fo = None):
    import sys,gc
    '''
    将观测
    :param sta_ob:
    :param sta_fo_list:
    :return:
    '''
    if not isinstance(sta_fo_list, list):
        print("the second args shold be a list")
        return
    sta_all = None

    if g =="id":
        grouped_ob = dict(list(sta_ob.groupby("id")))
        nfo = len(sta_fo_list)
        grouped_fo_list=[]
        for i in range(nfo):
            grouped_fo_list.append(dict(list(sta_fo_list[i].groupby("id"))))
        id_ob = list(grouped_ob.keys())
        sys._clear_type_cache()
        gc.collect()
        sta_all = []
        n_id = len(id_ob)

        if need_match_ob:
            how = "inner"
        else:
            how = "right"
        for i in range(n_id):
            rate = int((i/n_id)*100)
            if rate%5 == 0:
                if abs(i - rate * 0.01 * n_id)<1:
                    print(str(rate) + "% combined")

            key = id_ob[i]
            all_fos_have = True
            sta_ob_one_id = grouped_ob.pop(key)
            sta_fos_one_id = []
            for i in range(nfo):
                if key in grouped_fo_list[i].keys():
                   sta_fos_one_id.append(grouped_fo_list[i].pop(key))
                else:
                    all_fos_have = False
            if all_fos_have:
                combine_one = combine_on_obTime_one_id(sta_ob_one_id,sta_fos_one_id,how = how,how_fo = how_fo)
                sta_all.append(combine_one)
        sta_all = concat(sta_all)
    elif g == "dtime":
        nfo = len(sta_fo_list)
        grouped_fo_list = []
        dtime_list = []
        for i in range(nfo):
            dict1 = dict(list(sta_fo_list[i].groupby("dtime")))
            grouped_fo_list.append(dict1)
            dtime_list.extend(list(dict1.keys()))
        dtime_list = list(set(dtime_list))
        sys._clear_type_cache()
        gc.collect()
        sta_list = []
        n_dtime = len(dtime_list)

        for i in range(n_dtime):
            rate = int((i/n_dtime)*100)
            print(str(rate) + "% combined")

            key = dtime_list[i]
            all_fos_have = True
            sta_fos_one_dtime= []

            for i in range(nfo):
                if key in grouped_fo_list[i].keys():
                    sta_fos_one_dtime.append(grouped_fo_list[i].pop(key))
                else:
                    if how_fo == "outer":
                        pass
                    else:
                        all_fos_have = False
            if all_fos_have:
                combine_one = combine_on_obTime_id(sta_ob, sta_fos_one_dtime, need_match_ob=need_match_ob,how_fo=how_fo)
                sta_list.append(combine_one)
                del sta_fos_one_dtime

        sta_all = concat(sta_list)
        del sta_list
    if sta_all is not None:
        sta_all = sta_all.fillna(meteva_base.IV)
    sta_all.attrs = copy.deepcopy(sta_ob.attrs)
    sta_all.drop_duplicates(subset=["level","time","dtime","id"],inplace=True)
    sta_all.sort_values(by=["level", "time", "dtime", "id"], inplace=True)

    names = meteva_base.get_stadata_names(sta_ob)
    for i in range(len(sta_fo_list)):
        names.extend(meteva_base.get_stadata_names(sta_fo_list[i]))
    sta_all = meteva_base.in_member_list(sta_all,member_list=names)

    return sta_all


def combine_on_obTime(sta_ob,sta_fo_list,need_match_ob = False):
    if not isinstance(sta_fo_list, list):
        sta_fo_list = [sta_fo_list]

    dtime_list = list(set(sta_fo_list[0]['dtime'].values.tolist()))
    sta_combine = []
    for dtime in dtime_list:
        sta = sta_ob.copy()
        sta["time"] = sta["time"] - datetime.timedelta(hours= dtime)
        sta["dtime"] = dtime
        sta_combine.append(sta)
    sta_combine = concat(sta_combine)

    sta_combine_fo = None
    for sta_fo in sta_fo_list:
        sta_combine_fo = combine_on_all_coords(sta_combine_fo, sta_fo)


    if need_match_ob:
        sta_combine = combine_on_all_coords(sta_combine, sta_combine_fo, how="inner")
    else:
        sta_combine = combine_on_all_coords(sta_combine,sta_combine_fo,how="right")
        sta_combine = sta_combine.fillna(meteva_base.IV)

    sta_combine.attrs = copy.deepcopy(sta_ob.attrs)
    return sta_combine

def combine_on_bak_idandobTime1(sta_list):
    '''
    merge_on_id_and_obTime  合并多个sta——dataframe  并且保证合并后的dataframe要素名不重复
    :param sta_list:   含有多个sta_dataframe的列表
    :return:
    '''
    intersection_of_data = None
    for sta in sta_list:
        sta['dtime'] = sta['dtime'].map(lambda x: datetime.timedelta(hours=x))
        sta['time'] = sta['time'] + sta['dtime']
        sta['dtime'] = 0

        intersection_of_data = combine_on_all_coords(intersection_of_data, sta)
    intersection_of_data.attrs = copy.deepcopy(sta_list[0].attrs)
    return intersection_of_data


def combine_expand_IV(sta,sta_with_IV):
    '''
        将观测
        :param sta_ob:
        :param sta_fo_list:
        :return:
        '''

    #sta_with_IV1 = meteva_base.sta_data(sta_with_IV)
    sta_with_IV1 = copy.deepcopy(sta_with_IV)
    columns = ["level","time","dtime","id"]
    for i in range(4):
        sta_expand = []
        if sta_with_IV.iloc[0,i] == meteva_base.IV or pd.isnull(sta_with_IV.iloc[0,i]):
            value_list = list(set(sta.iloc[:,i].values.tolist()))
            if i == 1:
                for j in range(len(value_list)):
                    value_list[j] = meteva_base.tool.all_type_time_to_time64(value_list[j])
            for value in value_list:
                sta1 = copy.deepcopy(sta_with_IV1)
                sta1.iloc[:,i] = value
                sta_expand.append(sta1)
            sta_with_IV1 = concat(sta_expand)
    #sta_with_IV1 = sta_with_IV1.dropna()
    sta_combine = combine_on_level_time_dtime_id(sta, sta_with_IV1)
    return sta_combine

def combine_expand(sta,sta_type):
    sta_type1 = meteva_base.sta_data(sta_type)
    return combine_expand_IV(sta,sta_type1)

def get_inner_grid(grid0,grid1,used_coords = "xy"):
    if used_coords =="xy":
        si = 0
        sj = 0
        ei = 0
        ej = 0
        if(grid1.slon > grid0.slon):
            si = int(math.ceil((grid1.slon - grid0.slon)/grid0.dlon))
        if(grid1.slat > grid0.slat):
            sj = int(math.ceil((grid1.slat - grid0.slat)/grid0.dlat))
        if(grid1.elon < grid0.elon):
            ei = int(math.ceil((grid0.elon - grid1.elon)/grid0.dlon))
        if(grid1.elat < grid0.elat):
            ej = int(math.ceil((grid0.elat - grid1.elat)/grid0.dlat))
        slon = grid0.slon + si * grid0.dlon
        slat = grid0.slat + sj * grid0.dlat
        elon = grid0.elon - ei * grid0.dlon
        elat = grid0.elat - ej * grid0.dlat
        grid_inner = meteva_base.grid([slon,elon,grid0.dlon],[slat,elat,grid0.dlat],grid0.gtime,grid0.dtimes,grid0.levels,grid0.members)
        return grid_inner
    elif used_coords == "all":
        if grid0 is None:return grid1
        if grid1 is None:return grid0
        si = 0
        sj = 0
        ei = 0
        ej = 0
        if(grid1.slon > grid0.slon):
            si = int(math.ceil((grid1.slon - grid0.slon)/grid0.dlon))
        if(grid1.slat > grid0.slat):
            sj = int(math.ceil((grid1.slat - grid0.slat)/grid0.dlat))
        if(grid1.elon < grid0.elon):
            ei = int(math.ceil((grid0.elon - grid1.elon)/grid0.dlon))
        if(grid1.elat < grid0.elat):
            ej = int(math.ceil((grid0.elat - grid1.elat)/grid0.dlat))


        slon = grid0.slon + si * grid0.dlon
        slat = grid0.slat + sj * grid0.dlat
        elon = grid0.elon - ei * grid0.dlon
        elat = grid0.elat - ej * grid0.dlat

        times0 = pd.date_range(grid0.gtime[0], grid0.gtime[1], freq=grid0.gtime[2])
        times1 = pd.date_range(grid1.gtime[0], grid1.gtime[1], freq=grid1.gtime[2])

        times = list(set(times0) & set(times1))
        times.sort()

        if len(times) == 1:
            gtime_d = "1h"
        else:
            gtime_d = times[1] - times[0]

        dtimes = list(set(grid0.dtimes)&set(grid1.dtimes))
        dtimes.sort()
        levels = list(set(grid0.levels)&set(grid1.levels))
        levels.sort()
        members1= []
        for member in grid0.members:
            members1.append(member)
        for member in grid1.members:
            if member not in members1:
                members1.append(member)

        grid_inner = meteva_base.grid([slon, elon, grid0.dlon], [slat, elat, grid0.dlat], [times[0],times[-1],gtime_d], dtimes,
                                      levels, members1)
        return grid_inner
    else:
        pass

def get_outer_grid(grid0,grid1,used_coords = "xy"):
    if used_coords == "xy":
        slon = min(grid0.slon,grid1.slon)
        slat = min(grid0.slat,grid1.slat)
        elon = max(grid0.elon,grid1.elon)
        elat = max(grid0.elat,grid1.elat)
        grid_outer = meteva_base.grid([slon,elon,grid0.dlon],[slat,elat,grid0.dlat],grid0.gtime,grid0.dtimes,grid0.levels,grid0.members)
        return grid_outer
    elif used_coords == "all":
        if grid0 is None:return grid1
        if grid1 is None:return grid0
        slon = min(grid0.slon, grid1.slon)
        slat = min(grid0.slat, grid1.slat)
        elon = max(grid0.elon, grid1.elon)
        elat = max(grid0.elat, grid1.elat)

        times0 = pd.date_range(grid0.gtime[0], grid0.gtime[1], freq=grid0.gtime[2])
        times1 = pd.date_range(grid1.gtime[0], grid1.gtime[1], freq=grid1.gtime[2])

        times = list(set(times0)|set(times1))
        times.sort()
        if len(times) == 1:
            gtime_d = "1h"
        else:
            gtime_d = times[1] - times[0]

        dtimes = list(set(grid0.dtimes)|set(grid1.dtimes))
        dtimes.sort()

        levels = list(set(grid0.levels)|set(grid1.levels))
        levels.sort()

        members = copy.deepcopy(grid0.members)
        if not isinstance(members,list):
            members = members.tolist()
        for member in grid1.members:
            if member not in members:
                members.append(member)
        grid_outer = meteva_base.grid([slon, elon, grid0.dlon], [slat, elat, grid0.dlat], [times[0],times[-1],gtime_d], dtimes,
                                      levels, members)
        return grid_outer
    else:
        pass
def expand_to_contain_another_grid(grd0,grid1,used_coords = "xy",outer_value = 0):
    grid0 = meteva_base.get_grid_of_data(grd0)
    grid_outer = get_outer_grid(grid0,grid1,used_coords = used_coords)
    grd1 = meteva_base.grid_data(grid_outer)
    grd1.values[...] = outer_value

    si = 0
    sj = 0
    if (grid1.slon < grid0.slon):
        si = int(round((grid0.slon - grid1.slon) / grid0.dlon))
    if (grid1.slat < grid0.slat):
        sj = int(round((grid0.slat - grid1.slat) / grid0.dlat))
    grd1.values[:,:,:,:,sj:(sj + grid0.nlat), si:(si + grid0.nlon)] = grd0.values[...]
    return grd1



def combine_griddata(griddata_list,dtime_list  = None,how = "inner"):
    '''
    :param griddata_list: 网格数据列表
    :return:
    '''
    # 统计网格信息

    ngrd = len(griddata_list)
    grid_combined = None
    for i in range(ngrd):
        if griddata_list[i] is None: continue
        grid1 = meteva_base.get_grid_of_data(griddata_list[i])
        if how =="inner":
            grid_combined = meteva_base.get_inner_grid(grid_combined,grid1,used_coords="all")
        elif how == "outer":
            grid_combined = meteva_base.get_outer_grid(grid_combined, grid1, used_coords="all")

    #print(grid_combined)
    if grid_combined is None:
        print("没有可合并的格点数据")
    if dtime_list is not None:
        grid_combined.dtimes = dtime_list

    grd_all = meteva_base.grid_data(grid_combined)
    grid_xy = meteva_base.grid(grid_combined.glon,grid_combined.glat)

    #grd_all.values[:,:,:,:,:,:] = meteva_base.IV
    grd_all.values[:, :, :, :, :, :] = np.nan
    levels_all = grd_all["level"].values
    times_all = grd_all["time"].values
    dtimes_all = grd_all["dtime"].values
    members_all = grd_all["member"].values
    index_level = {}
    for i in range(len(levels_all)):
        index_level[levels_all[i]] = i
    index_time = {}
    for i in range(len(times_all)):
        index_time[times_all[i]] = i
    index_dtime = {}
    for i in range(len(dtimes_all)):
        index_dtime[dtimes_all[i]] = i
    index_member = {}
    for i in range(len(members_all)):
        index_member[members_all[i]] = i

    for i in range(ngrd):
        if griddata_list[i] is None:continue
        grd_interp = meteva_base.interp_gg_linear(griddata_list[i],grid_xy)
        levels = grd_interp["level"].values
        times = grd_interp["time"].values
        dtimes = grd_interp["dtime"].values
        members = grd_interp["member"].values
        for i in range(len(levels)):
            if not levels[i] in levels_all:continue
            i_level = index_level[levels[i]]
            for j in range(len(times)):
                if not times[j] in times_all: continue
                i_time = index_time[times[j]]
                for k in range(len(dtimes)):
                    if not dtimes[k] in dtimes_all:continue
                    i_dtime = index_dtime[dtimes[k]]
                    for m in range(len(members)):
                        if not members[m] in members_all:continue
                        i_member = index_member[members[m]]
                        grd_all.values[i_member,i_level,i_time,i_dtime,:,:] =  grd_interp.values[m, i, j, k, :, :]
    grd_all.attrs = copy.deepcopy(griddata_list[0].attrs)
    return grd_all


