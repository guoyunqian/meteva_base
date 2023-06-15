import meteva_base
import numpy as np
import pandas as pd
import copy
import datetime
#格点转换为站点
def trans_grd_to_sta(grd):
    '''
    网格数据转站点数据
    :param grd: 网格预报数据
    :return: 站点数据
    '''
    levels = copy.deepcopy(grd["level"].values)
    times = copy.deepcopy(grd["time"].values)
    dtimes = copy.deepcopy(grd["dtime"].values)
    members = copy.deepcopy(grd["member"].values)
    x = grd['lon'].values
    y = grd['lat'].values
    grid_x, grid_y = np.meshgrid(x, y)
    grid_num = len(x) * len(y)
    sta_all = None
    column_list1 = ['lon', 'lat']
    column_list1.extend(members)
    column_list2 = ['level','time','dtime','id', 'lon', 'lat']
    column_list2.extend(members)

    for i in range(len(levels)):
        for j in range(len(times)):
            for k in range(len(dtimes)):
                dat = np.empty((grid_num, 2+len(members)))
                dat[:, 0] = grid_x.reshape(-1)
                dat[:, 1] = grid_y.reshape(-1)
                for m in range(len(members)):
                    dat[:,2+m] = grd.values[m,i,j,k,:,:].reshape(-1)
                sta = pd.DataFrame(dat,columns=column_list1)
                sta["id"] = np.arange(grid_num)
                sta['time'] = times[j]
                sta['dtime'] = dtimes[k]
                sta['level'] = levels[i]
                sta = sta.reindex(columns=column_list2)
                if (sta is None):
                    sta_all = sta
                else:
                    sta_all = pd.concat([sta_all, sta])
    sta_all.attrs = copy.deepcopy(grd.attrs)
    return sta_all

def trans_sta_to_grd(sta):
    """
    将站点形式的规则网格的数据转化为格点数据
    :param sta:站点数据
    :return:返回格点网格数据
    """
    lons = sta.loc[:,'lon'].values
    lons = list(set(lons))
    lons.sort()
    if len(lons) == 1:
        glon = lons
    else:
        lons = np.array(lons)
        dlons = lons[1:] - lons[:-1]
        dlon = np.min(dlons)
        glon = [lons[0],lons[-1],dlon]



    lats =sta.loc[:,'lat'].values
    lats = list(set(lats))
    lats.sort()
    #print(lats)
    if len(lats) == 1:
        glat = lats
    else:
        lats = np.array(lats)
        dlats = lats[1:] - lats[:-1]
        dlat = np.min(dlats)
        glat = [lats[0],lats[-1],dlat]

    #print(glat)

    times= sta.loc[:,'time'].values
    times = list(set(times))
    times.sort()
    if len(times) == 1:
        gtime = times
    else:
        gtime = [times[0],times[-1],times[1] - times[0]]

    slon = lons[0]
    slat = lats[0]
    dtime_list = list(set(sta['dtime'].values.tolist()))
    level_list = list(set(sta['level'].values.tolist()))
    member_list = sta.columns[6:].tolist()

    grid0 = meteva_base.basicdata.grid(glon, glat,gtime = gtime,
                                                        level_list=level_list,dtime_list=dtime_list,member_list= member_list)

    grd = meteva_base.grid_data(grid0)
    for i in range(len(level_list)):
        sta1 =  sta.loc[sta['level'] == level_list[i]]
        for j in range(len(times)):
            sta2 = sta1.loc[sta1['time'] == times[j]]
            for k in range(len(dtime_list)):
                sta3 = sta2.loc[sta2['dtime'] == dtime_list[k]]
                ig = ((sta3['lon'].values - slon) // dlon).astype(dtype='int16')
                jg = ((sta3['lat'].values - slat) // dlat).astype(dtype='int16')
                for m in range(len(member_list)):
                    dat = np.zeros((grid0.nlat, grid0.nlon))
                    dat[jg, ig] = sta3.loc[:, member_list[m]]
                    grd.values[m,i,j,k,:,:] = dat[:,:]
    grd.attrs = copy.deepcopy(sta.attrs)
    return grd


def trans_contours_to_sta(m14,station,grade_list):

    contours = m14["closed_contours"]
    ncontour = len(contours["cn_label"])
    ploys_dict = {}

    for g in range(len(grade_list)):
        grade = grade_list[g]
        ploys_dict[g] = []
        for n in range(ncontour):
            if float(contours["cn_label"][n]) == grade or (int(float(contours["cn_label"][n])) ==0 and g ==0):
                line = contours["cn_xyz"][n][:,0:2]
                ploys_dict[g].append(line)

    sta_fo = station.copy()  #  meteva_base.interp_gs_nearest(grd_fo, sta_ob_in)

    nsta = len(sta_fo.index)

    grade_list1 = [0]
    grade_list1.extend(grade_list)
    for i in range(nsta):
        point1 = [sta_fo.iloc[i,4],sta_fo.iloc[i,5]]
        gg = 0
        for g in range(len(grade_list)):
            ploys = ploys_dict[g]
            inploy = meteva_base.tool.math_tools.isPoiWithinPoly(point1,ploys)
            if not inploy:
                break
            else:
                gg = g + 1
        sta_fo.iloc[i, -1] = grade_list1[gg]

    return sta_fo



def move_fo_time(data,dtime,keep_minus_dtime = True):
    if isinstance(data, pd.DataFrame):
        sta1 = data.copy()
        sta1["time"] = data["time"] + dtime* np.timedelta64(1, 'h')
        sta1["dtime"] = data["dtime"] - dtime
        if not keep_minus_dtime: sta1 = meteva_base.between_dtime_range(sta1,0,10000)
        return sta1
    else:
        grd1 = data.copy()
        grd1.coords["time"]= grd1.coords["time"].values[:] + dtime* np.timedelta64(1, 'h')

        grd1.coords["dtime"] =grd1.coords["dtime"].values[:] -  dtime
        if not keep_minus_dtime:grd1 = meteva_base.between_dtime_range(grd1,0,10000)
        return grd1


def add_dtime_0(data):
    if isinstance(data, pd.DataFrame):
        sta1 = data.copy()
        dtime_list = list(set(sta1["dtime"].values.tolist()))
        dtime_list.sort()
        sta1_0 = meteva_base.sele_by_para(sta1,dtime_list[0])
        sta1_0["dtime"] = 0
        sta1_0.iloc[:,6:] = 0
        sta_add = meteva_base.concat([sta1_0,sta1])
        return sta_add
    else:
        grd1 = data.copy()
        dtime1 = grd1["dtime"].values[0]
        grd1_0 = meteva_base.in_dtime_list(grd1,dtime1)
        grd1_0.coords["dtime"] = [0]
        grd1_0.values[...] = 0
        grd_add = meteva_base.concat([grd1_0,grd1])
        return grd_add

def tran_ut_nature_local_time(sta):
    '''
    :param sta: 世界时站点数据
    :return:  当地时站点数据
    '''
    sta_lt = copy.deepcopy(sta)
    lon = copy.deepcopy(sta_lt["lon"].values)
    lon[lon>180] -= 360
    hour = np.round((lon/15)).astype(np.int)
    sta_lt["time"] += hour * np.timedelta64(1, 'h')

    return sta_lt

def tran_ut_Administrative_local_time(sta,id_zone):
    '''
    :param sta: 世界时站点数据
    :return:  当地时站点数据
    '''

    sta_zone = meteva_base.sta_data(id_zone)
    sta_com = meteva_base.combine_expand_IV(sta,sta_zone)
    sta_com["time"] += sta_com.iloc[:,-1] * np.timedelta64(1, 'h')
    sta_com = sta_com.iloc[:,:-1]
    sta_com.attrs = copy.deepcopy(sta.attrs)
    return sta_com