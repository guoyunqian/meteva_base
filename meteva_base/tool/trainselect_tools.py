# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2023， CMA National Meteorological Centre.
# All rights reserved.
#
# Distributed under the terms of the GPL v2 License.
#

import copy
import meteva_base as meb
import numpy as np
import datetime
import pandas as pd

def sample_time_select_from_sta(sta, fcst_time, fcst_fh=24, 
                                  year_before=2, day_len=60, fh_delta_list=[0,1], frt_hour=None,
                                  is_obs=False, is_show=True):
    """
    从meteva站点数据中， 筛选时间复合要求的历史训练样本并输出
    sta： meteva站点类型数据
    fcst_time(datetime.datetime), fcst_fh(int)：预报时间和时效
    year_before=2 ## 筛选往前推的年份
    day_len= 60 ## 筛选前后的日数
    fh_delta_list=[0,1] ## 筛选训练数据的预报时效，  ft = fcst_fh+fh_delta_list
    frt_hour = [8,20]## 筛选起报时间
    """ 
    import copy
    data_list = []
    for dy in np.arange(year_before+1):
        if is_obs:#实况处理(挑选)
            fcst_time0 = fcst_time + datetime.timedelta(hours=int(fcst_fh))
            fcst_fh0 = None
        else:#模式预报处理(起报时间+预报时效)
            fcst_time0 = fcst_time
            fcst_fh0 = fcst_fh

        if dy == 0:#今年
                end_time = fcst_time
                begin_time = fcst_time0 - datetime.timedelta(days=day_len)
                # print(fcst_time)
                # print(end_time, begin_time)
        else:
            end_time = copy.copy(fcst_time0).replace(year=fcst_time0.year-dy)+ datetime.timedelta(days=day_len)
            begin_time = copy.copy(fcst_time0).replace(year=fcst_time0.year-dy)- datetime.timedelta(days=day_len)
        if is_show:print("起始时间：{0}, 终止时间:{1}".format(begin_time, end_time))
        data_temp = sta.loc[(sta.time>=begin_time) & (sta.time<end_time),:]#所有历史样本数据
        if data_temp is not None:
            if  fcst_fh0 is not None:
                fhs = (fcst_fh0+ np.array(fh_delta_list))#.tolist()
                data_temp = data_temp.loc[data_temp.dtime.isin(fhs),:]
            time_index = pd.DatetimeIndex(data_temp.time)#时间索引
            if  fcst_hours is not None:
                data_temp = data_temp.loc[time_index.hour.isin(fcst_hours)]
            data_list.append(data_temp)
    data_all = pd.concat(data_list, axis=0)
    return(data_all)


def select_resemble_station(sta_info, sta_hgt, nearNum=101, alpha=200):
    """
    计算站点的相似度，返回相似站点列表
    # sta_info:所有站点，meteva的station格式
    # sta_hgt: 所有站点海拔高度
    # nearNum:邻近站点数
    # alpha: 海拔系数(距离+alpha*海拔)
    """
    from met_pre_cal.tools.temp.station_cal_nearby_select import sta_values_ensemble_nearby
    query_lonlat = sta_info.loc[:,['lon','lat']].values
    query_value = sta_info['data0'].values
    _,index,distance = sta_values_ensemble_nearby(ref_lonlat=query_lonlat, ref_value=query_value,
                                 nearNum=nearNum)
    ## id站点列表
    id_sta = sta_info.id.values
    # sta_id_邻近站点列表
    id_list = id_sta[index]
    ## 海拔高度列表
    np.set_printoptions(suppress=True)
    hgt0 = sta_hgt.data0.values
    hgt_list = hgt0[index]
    hgt0 = hgt0.reshape(-1,1)
    hgt_list = hgt_list - hgt0#海拔差delta
    ## 邻近相似度列表
    S = 1000*distance+alpha*np.abs(hgt_list)
    ## 相似度排序，由小至大返回对应id_list
    arg_S = np.argsort(S,axis=1)
    id_S_list = np.zeros_like(id_list)
    dis_S_list = np.zeros_like(distance)
    hgt_S_list = np.zeros_like(hgt_list)
    for i in np.arange(id_S_list.shape[0]):
        id_S_list[i,:] = id_list[i,:][arg_S[i,:]]
        dis_S_list[i,:] = distance[i,:][arg_S[i,:]]
        hgt_S_list[i,:] = hgt_list[i,:][arg_S[i,:]]
    return(id_S_list,dis_S_list,hgt_S_list)


def get_resemble_station_DF(sta_info, sta_hgt=None, selectNum=50):
    ## 返回相似站点id的Dataframe
    if sta_hgt is None:
        hgt = meb.read_griddata_from_nc(r"O:\jianyan\NMC\TEMP\20220323_huanan_ppt\PROData\01_nearest_topo\supply\01_HGT_1km.nc")
        sta_hgt = meb.interp_gs_linear(hgt, sta=sta_info)
    ## 相似站点选取
    id_S_list,_,_ = select_resemble_station(sta_info, sta_hgt)
    ## 邻近站点id数据
    pd_index = sta_info.id.values
    df = pd.DataFrame(id_S_list, index=pd_index, columns=np.arange(id_S_list.shape[1]))
    df = df.iloc[:,0:selectNum+1]
    return(df)


def resemble_stations_select(sta, id, resemble_id_list):
    """
    从所有数据样本中，挑选某站的相似站点对应样本,按相似度排序,并输出
    sta： meteva站点类型数据
    id:   需要计算的站点id(单站点)
    resumble_id_list: 列表，里面是所有相似站点号
    """
    ## 本站id在相似站点id的第一位
    if not id in resemble_id_list:
        resemble_id_list = np.insert(resemble_id_list, 0, id)
    ## id与排序对应表
    num0 = np.arange(len(resemble_id_list))
    rank = (dict(zip(resemble_id_list, num0)))
    ## 挑选邻近站点样本，并排序
    resemble = sta.loc[sta.id.isin(resemble_id_list),:]
    resemble['rank'] = resemble.id
    resemble['rank'] = resemble['rank'].map(rank)
    resemble   = resemble.sort_values(by='rank')
    resemble.drop(columns=['rank'],inplace=True)
    return resemble


def resample_in_resemble_stations(sta, id, resemble_id_list, 
                        value=0.5, threshold_dict={0.1:50},is_show=True):
    """
    从所有数据样本中，挑选某站的相似站点对应样本,按相似度排序,并输出
    sta： meteva站点类型数据
    id:   需要计算的站点id(单站点)
    resumble_id_list: 列表，里面是所有相似站点号
    value: 预报值
    threshold_dict: 阈值样本字典
    return: 补充总样本sta_sample，对应量级阈值，补充站点数(不包括自己)
    """
    thresholds = np.array(list(threshold_dict))
    nsamples = np.array(list(threshold_dict.values()))
    args = np.argsort(thresholds)
    thresholds = thresholds[args]
    nsamples = nsamples[args]
    if not 0 in thresholds:
        thresholds = np.insert(thresholds,0,0)
        nsamples = np.insert(nsamples,0,0)
    ## value对应具体阈值及N
    index = np.searchsorted(thresholds, value+0.01)-1
    threshold = thresholds[index]
    if index==0:
        print(value,index)
        return(None,0)
    nsample = nsamples[index]
    ## 从前向后，依次添加相似样本
    resemble_all = resemble_stations_select(sta, id, resemble_id_list)
    resemble_all['year'] = pd.DatetimeIndex(resemble_all.time).year
    years  = resemble_all['year'].drop_duplicates().sort_values(ascending=False).values
    ## 循环添加样本,判断样本数是否超过阈值
    if not 'ob' in resemble_all.columns and 'obs' in resemble_all.columns:
        resemble_all.rename(columns={'obs':'ob'},inplace=True)
    if not 'ob' in resemble_all.columns and 'data0' in resemble_all.columns:
        resemble_all.rename(columns={'data0':'ob'},inplace=True)
    resemble_list = []#样本列表
    n_flag = 0#样本数量
    for i,id_num in enumerate(resemble_id_list):
        for year in  years:
            temp  = resemble_all.loc[(resemble_all.id==id_num)&(resemble_all.year==year),:]
            temp_num =  len(temp.loc[temp['ob']>=threshold])#大于阈值的样本数
            if n_flag>=nsample:
                break
            else:
                n_flag += temp_num
                resemble_list.append(temp)
            if is_show: print("补充样本： 站点-{0}, 年份-{1},  超阈值样本数-{2}".format(id_num, year, temp_num))
        if n_flag>=nsample:
            result = pd.concat(resemble_list, axis=0)
            result.drop(columns=['year'],inplace=True)
            if is_show : print("补充样本完毕。阈值-{0}, 超阈值样本-{1}".format(threshold, len(result.loc[result['ob']>=threshold])))##样本足够
            return(result,threshold,i)
    if is_show : print("补充不足。阈值-{0}, 超阈值样本-{1}".format(threshold, len(result.loc[result['ob']>=threshold])))
    return(resemble_all.drop(columns=['year']),threshold,i)#样本不足，返回所有相似站点样本




#####  样本kalman随机上采样
def random_sample_growth(sta, threshold=0.1, k=1.1, is_show=False):
    """
    样本随机增加，大于阈值部分(实况or预报)thresold随机复制
    # method: 过采样方法- RandomOverSampler/ SMOTE/ ADASYN（随机复制或新建相似样本）
    threshold: 是否全样本kalman过采样； 为None时全样本随机取样，否则只针对实况、预报大于threshold得样本进行随机复制过采样。
    """
    # from imblearn.over_sampling import RandomOverSampler,SMOTE,ADASYN
    from collections import Counter
    col_name = 'is_pre'
    sta_t = sta.copy()
    if threshold is not None:
        temp  = (sta_t.iloc[:,-2] >= threshold) | (sta_t.iloc[:,-1]>=threshold)
        temp0 = np.zeros_like(temp, dtype=int)
        temp0[temp] = 1
        sta_t[col_name] = temp0
        sta_t = sta_t.sort_values(by=col_name)
        a = dict(sorted(Counter(sta_t[col_name].values).items()))#计数分类字典，y为0和1
        ## kalman样本过采样
        index_raw   = a.get(1)
        if index_raw is None: return sta#若无该阈值以上样本，直接返回
        index_k     = int(index_raw*k)
        sta_all     = random_over_sampler_dict(sta_t, by=col_name, target={1:index_k}, is_show=is_show)
        if is_show:
            print("Raw sample: ", dict(sorted(Counter(sta_t.loc[:, col_name]).items())))
            print("ROS sample: ", dict(sorted(Counter(sta_all.loc[:, col_name]).items())))
        sta_all.drop(columns=[col_name], inplace=True)
    else:
        index_k = int(len(sta)*k)
        sta_all = oversample_random(sta, random_num=index_k, is_show=is_show)
    return sta_all


def random_over_sampler_dict(sta,  by='is_pre', 
        target={1: 1000,  0:1000},
        is_show=False,
        ):
    """站点数据过采样， 对by数据列中的分类增加， 
        target: 字典，具体每种分类需要随机上采样至的样本数目。必须大于或等于原样本数(否则报错)
    """
    from collections import Counter
    import random

    sta = sta.sort_values(by=by)
    y = sta.loc[:, by]
    origin = dict(sorted(Counter(y).items()))#计数分类字典
    sta_all = [sta]
    for cls in target.keys():
        # sta_list = []
        if cls not in list(origin.keys()):
            raise ValueError("target class should be one of origin class")
        samples_t = target[cls]#上采样后
        samples_o = origin[cls]#上采样前
        if samples_t < samples_o:
            raise ValueError("target class samples should greater than origin class samples")
        samples_t = samples_t-samples_o
        ## 随机扩充样本
        sta_cls = sta.loc[y==cls, :]#待上采样样本
        sta_random = oversample_random(sta_cls, random_num=samples_t, is_show=is_show)
        sta_all.append(sta_random) #扩充样本入队
    ## 所有样本转为整体DataFrame
    sta_all = pd.concat(sta_all, axis=0)
    return sta_all


def oversample_random(sta, random_num, is_show=True):
    """随机上采样，random_num：随机上采样至该样本数"""
    import random
    import pandas as pd
    sta_list = []
    try:
        sta.reset_index(inplace=True, drop=True)#使用index进行增殖
        samples_t = random_num
        samples_o = len(sta)
        if is_show:
            print(r"Random Oversample: origin-{}, oversample-{}".format(samples_o, samples_t))
        ntimes = int(samples_t / samples_o)
        randoms = samples_t % samples_o
        # print(ntimes, randoms)
        if ntimes>=1:
            for ntime in range(ntimes):
                sta_list.append(sta)
        random_index   = random.sample(sta.index.values.tolist(), randoms)
        sta_random     = sta.loc[sta.index.isin(random_index),:]
        sta_list.append(sta_random)
        sta_all = pd.concat(sta_list, axis=0) #扩充样本入队
        return sta_all
    except Exception as err:
        print(err)
        return None




if __name__ == "__main__":
    sta = pd.read_hdf(r"D:\Desktop\nimm_fmm\nimm_precipitation\data\ec\01train\20230101\2023010100_train.024.h5")
    meb.set_stadata_names(sta, ['obs','fcst'])
    sta0 = meb.sele_by_para(sta, time='20201202')
    # print(sta0)
    # print((sta0.iloc[:,-2] >= 0.1) | (sta0.iloc[:,-1]>=0.1))
    # sta_t, index_k = random_sample_growth(sta0, threshold=0.1)
    # sta_all = random_over_sampler(sta_t,  by='is_pre', 
    #     target={1: 10000,  0:1000},
    #     )
    # ## test random
    # import random
    # list = [1,2,3,4,5]
    # slice = random.sample(list, 5)
    # # print(slice)
    # sta_all = oversample_random(sta_t, random_num=20000)
    # print(dict(sorted(Counter(sta_all.loc[:, 'is_pre']).items())))
    
    from FMM_base import cal_FMM_raw
    
    result=cal_FMM_raw(sta0, sta0, levels=[0])
    # sta_all = random_sample_growth(sta0, threshold=0.1, k=1.5, is_show=True)
    # print(sta0.sort_values(by='data0'))
    # print(sta_all.sort_values(by='data0'))