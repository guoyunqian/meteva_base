# import meteva
import meteva_base
import meteva_base as meb
import numpy as np
import pandas as pd
import datetime


def mean_of_sta(sta,used_coords = ["member"],span = 24,equal_weight = False,keep_all = True):
    if not isinstance(used_coords,list):
        used_coords = [used_coords]

    sta1 = meteva_base.not_IV(sta)

    if used_coords == ["member"]:
        sta_mean = sta1.loc[:,meteva_base.get_coord_names()]
        sta_data = sta1[meteva_base.get_stadata_names(sta1)]
        value = sta_data.values
        mean = np.mean(value,axis=1)
        sta_mean['mean'] = mean
        return sta_mean
    elif used_coords == ["time"]:
        times = sta.loc[:, 'time'].values
        times = list(set(times))
        times.sort()
        times = np.array(times)
        dtimes = times[1:] - times[0:-1]
        min_dtime = np.min(dtimes)
        min_dhour = min_dtime / np.timedelta64(1, 'h')

        if span is None:

            rain_ac = meteva_base.in_time_list(sta, [times[0]])
            rain_ac["count_for_add"] = 1
            meteva_base.set_stadata_coords(rain_ac, time=times[-1])
            for i in range(1, len(times)):
                rain01 = meteva_base.in_time_list(sta, times[i])
                rain01["count_for_add"] = 1
                meteva_base.set_stadata_coords(rain01, time=times[-1])
                rain_ac = meteva_base.add_on_level_time_dtime_id(rain_ac, rain01, how="outer", default=0)

            names = meteva_base.get_stadata_names(rain_ac)
            for n in range(len(names)-1):
                rain_ac[names[n]] /= rain_ac[names[-1]]
            rain_ac = meteva_base.in_member_list(rain_ac,names[:-1])
            rain_ac.attrs["valid_time"] = (times[-1] - times[0])/np.timedelta64(1, 'h')
            return rain_ac

        else:
            step = int(round(span/min_dhour))
            sta1["count_for_add"] = 1
            if not equal_weight:
                names = meteva_base.get_stadata_names(sta1)
                rain_ac = sta1.copy()
                for name in names:
                    rain_ac[name] *= 0.5

                for i in range(1,step):
                    rain1 = sta1.copy()
                    rain1["time"] = rain1["time"] + min_dtime * i
                    rain_ac = meteva_base.add_on_level_time_dtime_id(rain_ac, rain1, how="outer",default=0)
                rain1 = sta1.copy()
                rain1["time"] = rain1["time"] + min_dtime * step
                for name in names:
                    rain1[name] *= 0.5
                rain_ac = meteva_base.add_on_level_time_dtime_id(rain_ac, rain1, how="outer", default=0)

            else:
                rain_ac = None
                for i in range(step):
                    rain1 = sta1.copy()
                    rain1["time"] = rain1["time"] + min_dtime * i
                    rain_ac = meteva_base.add_on_level_time_dtime_id(rain_ac, rain1, how="outer",default=0)

            names = meteva_base.get_stadata_names(rain_ac)
            for n in range(len(names)-1):
                rain_ac[names[n]] /= rain_ac[names[-1]]
            rain_ac = meteva_base.in_member_list(rain_ac,names[:-1])
            rain_ac = meteva_base.between_time_range(rain_ac, times[0], times[-1])  # 删除时效小于range的部分

            if not keep_all:
                dtimes = times[:] - times[-1]
                dh = (dtimes / min_dtime).astype(np.int32)
                new_times = times[dh % step == 0]
                rain_ac = meteva_base.in_time_list(rain_ac, new_times)

            rain_ac.attrs["valid_time"] = span
            return rain_ac

    elif used_coords ==["dtime"]:
        if span is None:
            print("if used_coords == [dtime], span must be int of float bigger than 0 ")

        dtimes = sta.loc[:, 'dtime'].values
        dtimes = list(set(dtimes))
        dtimes.sort()
        dtimes = np.array(dtimes)

        dhour_unit = dtimes[0]
        if dhour_unit == 0:
            dhour_unit = dtimes[1]
        step = int(round(span/dhour_unit))

        if equal_weight:
            sta1["count_for_add"] = 1
            names = meteva_base.get_stadata_names(sta1)
            rain_ac = sta1.copy()
            for i in range(1,step):
                rain1 = sta1.copy()
                rain1["dtime"] = rain1["dtime"] + dhour_unit * i
                rain_ac = meteva_base.add_on_level_time_dtime_id(rain_ac, rain1,how="outer",default=0)
        else:
            pass
            dtimes_delta = (dtimes[1:] - dtimes[:-1])
            names = meteva_base.get_stadata_names(sta1)
            sta1["weight_pre"] =0
            sta1["weight_later"] = 0
            for i in range(len(dtimes)-1):
                sta1.loc[sta1["dtime"] == dtimes[i+1],"weight_pre"] = dtimes_delta[i]
                sta1.loc[sta1["dtime"] == dtimes[i], "weight_later"] = dtimes_delta[i]

            sta2 = sta1.iloc[:,:-2]
            sta2.loc[:,"count_for_add"] = sta1.loc[:,"weight_pre"]
            rain_ac = sta2.copy()


            for n in range(len(names)):
                rain_ac.loc[:,names[n]] *= sta2.loc[:,"count_for_add"]

            sta2.loc[:,"count_for_add"] = sta1.loc[:,"weight_pre"] + sta1.loc[:,"weight_later"]
            for i in range(1,step-1):
                rain1 = sta2.copy()
                for n in range(len(names)):
                    rain1.loc[:,names[n]] *= sta2.loc[:,"count_for_add"]
                rain1["dtime"] = rain1["dtime"] + dhour_unit * i
                rain_ac = meteva_base.add_on_level_time_dtime_id(rain_ac, rain1,how="outer",default=0)

            sta2.loc[:,"count_for_add"] = sta1.loc[:,"weight_later"]
            rain1 = sta2.copy()
            for n in range(len(names)):
                rain1.loc[:,names[n]] *= sta2.loc[:,"count_for_add"]
            rain1["dtime"] = rain1["dtime"] + dhour_unit * step
            rain_ac = meteva_base.add_on_level_time_dtime_id(rain_ac, rain1, how="outer", default=0)

        names = meteva_base.get_stadata_names(rain_ac)
        for n in range(len(names)-1):
            rain_ac[names[n]] /= rain_ac[names[-1]]

        rain_ac = meteva_base.in_member_list(rain_ac,names[:-1])
        rain_ac = meteva_base.in_dtime_list(rain_ac,dtimes[1:])  # 删除时效小于range的部分
        if not keep_all:
            dh = ((dtimes - dtimes[-1]) / dhour_unit).astype(np.int32)
            new_dtimes = dtimes[dh % step == 0]
            rain_ac = meteva_base.in_dtime_list(rain_ac, new_dtimes)
        rain_ac.attrs["valid_time"] = span
        return rain_ac

def std_of_sta(sta,used_coords = ["member"]):
    sta_std = sta.loc[:,meteva_base.get_coord_names()]
    sta_data = sta[meteva_base.get_stadata_names(sta)]
    value = sta_data.values.astype(np.float32)
    std = np.std(value, axis=1)
    sta_std['std'] = std
    return sta_std

def var_of_sta(sta,used_coords = ["member"]):
    sta_var = sta.loc[:,meteva_base.get_coord_names()]
    sta_data = sta[meteva_base.get_stadata_names(sta)]
    value = sta_data.values
    var = np.var(value, axis=1)
    sta_var['var'] = var
    return sta_var

def max_of_sta(sta,used_coords = ["member"],span = None, contain_start = False,keep_all = True,ignore_missing = False):
    if not isinstance(used_coords,list):
        used_coords = [used_coords]

    default = np.min(sta.iloc[:,6:].values)

    if ignore_missing:
        how = "outer"
    else:
        how = "inner"

    if used_coords  == ["member"]:
        sta_max = sta.loc[:,meteva_base.get_coord_names()]
        sta_data = sta[meteva_base.get_stadata_names(sta)]
        value = sta_data.values
        max1 = np.max(value, axis=1)
        sta_max['max'] = max1
        return sta_max
    elif used_coords == ["time"]:
        if span is None:
            times = sta.loc[:, 'time'].values
            times = list(set(times))
            times.sort()
            rain_ac = meteva_base.in_time_list(sta,[times[0]])
            meteva_base.set_stadata_coords(rain_ac, time=times[-1])
            for i in range(1,len(times)):
                rain01 = meteva_base.in_time_list(sta,times[i])
                meteva_base.set_stadata_coords(rain01,time=times[-1])
                rain_ac = meteva_base.max_on_level_time_dtime_id(rain_ac, rain01, how=how,default= default)
            return rain_ac
        else:
            times = sta.loc[:, 'time'].values
            times = list(set(times))
            times.sort()
            times = np.array(times)
            dtimes = times[1:] - times[0:-1]
            min_dtime = np.min(dtimes)
            min_dhour = min_dtime / np.timedelta64(1, 'h')
            rain_ac = None
            step = int(round(span/min_dhour))
            if contain_start: step += 1
            for i in range(step):
                rain1 = sta.copy()
                rain1["time"] = rain1["time"] + min_dtime * i
                rain_ac = meteva_base.max_on_level_time_dtime_id(rain_ac, rain1, default=default)
            time0_add_span = times[0] + np.timedelta64(int(min_dhour * (step - 1)),'h')
            rain_ac = meteva_base.sele_by_para(rain_ac,time_range=[time0_add_span,times[-1]])
            if not keep_all:
                dtimes = times[:] - times[-1]
                dh = (dtimes / min_dtime).astype(np.int32)
                new_times = times[dh % step == 0]
                rain_ac = meteva_base.in_time_list(rain_ac, new_times)
            return rain_ac
    elif used_coords ==["dtime"]:
        if span is None:
            dtimes = sta.loc[:, 'dtime'].values
            dtimes = list(set(dtimes))
            dtimes.sort()
            rain_ac = meteva_base.in_dtime_list(sta, [dtimes[0]])
            meteva_base.set_stadata_coords(rain_ac, dtime=dtimes[-1])
            for i in range(1, len(dtimes)):
                rain01 = meteva_base.in_dtime_list(sta, dtimes[i])
                meteva_base.set_stadata_coords(rain01, dtime=dtimes[-1])
                rain_ac = meteva_base.max_on_level_time_dtime_id(rain_ac, rain01, how=how,default= default)
            return rain_ac
        else:
            dtimes = sta.loc[:, 'dtime'].values
            dtimes = list(set(dtimes))
            dtimes.sort()
            dtimes = np.array(dtimes)
            dhour_unit = dtimes[1] - dtimes[0]

            #if dhour_unit == 0:
            #    dhour_unit = dtimes[1]

            rain_ac = sta.copy()
            #print(span)
            #print(dhour_unit)
            step = int(round(span/dhour_unit))
            if contain_start: step += 1
            for i in range(1,step):
                rain1 = sta.copy()
                rain1["dtime"] = rain1["dtime"] + dhour_unit * i
                # print(dhour_unit * i)
                rain_ac = meteva_base.max_on_level_time_dtime_id(rain_ac, rain1, default=default)


            begin_dtime = dtimes[0]+dhour_unit * (step - 1)
            rain_ac = meteva_base.between_dtime_range(rain_ac,begin_dtime,dtimes[-1])  # 删除时效小于range的部分
            dtimes =np.array(list(set(rain_ac.loc[:, "dtime"].values.tolist())))
            if not keep_all:
                dh = ((dtimes - dtimes[-1]) / dhour_unit).astype(np.int32)
                new_dtimes = dtimes[dh % step == 0]
                rain_ac = meteva_base.in_dtime_list(rain_ac, new_dtimes)
            return rain_ac

def min_of_sta(sta,used_coords = ["member"],span = None,contain_start = False,keep_all = True,ignore_missing = False):
    if not isinstance(used_coords,list):
        used_coords = [used_coords]

    default = np.max(sta.iloc[:,6:].values)
    if ignore_missing:
        how = "outer"
    else:
        how = "inner"
    if used_coords  == ["member"]:
        sta_min = sta.loc[:,meteva_base.get_coord_names()]
        sta_data = sta[meteva_base.get_stadata_names(sta)]
        value = sta_data.values
        min1 = np.min(value, axis=1)
        sta_min['min'] = min1
        return sta_min
    elif used_coords == ["time"]:
        if span is None:
            times = sta.loc[:, 'time'].values
            times = list(set(times))
            times.sort()
            rain_ac = meteva_base.in_time_list(sta,[times[0]])
            meteva_base.set_stadata_coords(rain_ac, time=times[-1])
            for i in range(1,len(times)):
                rain01 = meteva_base.in_time_list(sta,times[i])
                meteva_base.set_stadata_coords(rain01,time=times[-1])
                rain_ac = meteva_base.min_on_level_time_dtime_id(rain_ac, rain01, how=how,default= default)
            return rain_ac
        else:
            times = sta.loc[:, 'time'].values
            times = list(set(times))
            times.sort()
            times = np.array(times)
            dtimes = times[1:] - times[0:-1]
            min_dtime = np.min(dtimes)
            min_dhour = min_dtime / np.timedelta64(1, 'h')
            rain_ac = None
            step = int(round(span/min_dhour))
            if contain_start:step += 1
            for i in range(step):
                rain1 = sta.copy()
                rain1["time"] = rain1["time"] + min_dtime * i
                rain_ac = meteva_base.min_on_level_time_dtime_id(rain_ac, rain1, default= default)
            time0_add_span = times[0] + np.timedelta64(int(min_dhour * (step - 1)),'h')
            rain_ac = meteva_base.sele_by_para(rain_ac,time_range=[time0_add_span,times[-1]])
            if not keep_all:
                dtimes = times[:] - times[-1]
                dh = (dtimes / min_dtime).astype(np.int32)
                new_times = times[dh % step == 0]
                rain_ac = meteva_base.in_time_list(rain_ac, new_times)
            return rain_ac
    elif used_coords ==["dtime"]:
        if span is None:
            dtimes = sta.loc[:, 'dtime'].values
            dtimes = list(set(dtimes))
            dtimes.sort()
            rain_ac = meteva_base.in_dtime_list(sta, [dtimes[0]])
            meteva_base.set_stadata_coords(rain_ac, dtime=dtimes[-1])
            for i in range(1, len(dtimes)):
                rain01 = meteva_base.in_dtime_list(sta, dtimes[i])
                meteva_base.set_stadata_coords(rain01, dtime=dtimes[-1])
                rain_ac = meteva_base.min_on_level_time_dtime_id(rain_ac, rain01, how=how,default= default)
            return rain_ac
        else:
            dtimes = sta.loc[:, 'dtime'].values
            dtimes = list(set(dtimes))
            dtimes.sort()
            dtimes = np.array(dtimes)
            dhour_unit = dtimes[1] - dtimes[0]

            #if dhour_unit == 0:
            #    dhour_unit = dtimes[1]

            rain_ac = sta.copy()
            #print(span)
            #print(dhour_unit)
            step = int(round(span/dhour_unit))
            if contain_start:step += 1

            for i in range(1,step):
                rain1 = sta.copy()
                rain1["dtime"] = rain1["dtime"] + dhour_unit * i
                # print(dhour_unit * i)
                rain_ac = meteva_base.min_on_level_time_dtime_id(rain_ac, rain1,default=default)

            begin_dtime = dtimes[0]+dhour_unit * (step - 1)
            rain_ac = meteva_base.between_dtime_range(rain_ac,begin_dtime,dtimes[-1])  # 删除时效小于range的部分
            dtimes =np.array(list(set(rain_ac.loc[:, "dtime"].values.tolist())))
            if not keep_all:
                dh = ((dtimes - dtimes[-1]) / dhour_unit).astype(np.int32)
                new_dtimes = dtimes[dh % step == 0]
                rain_ac = meteva_base.in_dtime_list(rain_ac, new_dtimes)
            return rain_ac

def sum_of_sta(sta,used_coords = ["member"],span = None,keep_all = True):
    if not isinstance(used_coords,list):
        used_coords = [used_coords]

    if used_coords == ["member"]:
        sta_sum = sta.loc[:,meteva_base.get_coord_names()]
        sta_data = sta[meteva_base.get_stadata_names(sta)]
        value = sta_data.values
        min1 = np.sum(value, axis=1)
        sta_sum['sum'] = min1
        return sta_sum

    elif used_coords == ["time"]:
        if span is None:
            times = sta.loc[:, 'time'].values
            times = list(set(times))
            times.sort()
            rain_ac = meteva_base.in_time_list(sta,[times[0]])
            meteva_base.set_stadata_coords(rain_ac, time=times[-1])
            for i in range(1,len(times)):
                rain01 = meteva_base.in_time_list(sta,times[i])
                meteva_base.set_stadata_coords(rain01,time=times[-1])
                rain_ac = meteva_base.add_on_level_time_dtime_id(rain_ac, rain01, how="outer",default=0)
            return rain_ac
        else:
            times = sta.loc[:, 'time'].values
            times = list(set(times))
            times.sort()
            times = np.array(times)
            dtimes = times[1:] - times[0:-1]
            min_dtime = np.min(dtimes)
            min_dhour = min_dtime / np.timedelta64(1, 'h')
            rain_ac = None
            step = int(round(span/min_dhour))
            for i in range(step):
                rain1 = sta.copy()
                rain1["time"] = rain1["time"] + min_dtime * i
                rain_ac = meteva_base.add_on_level_time_dtime_id(rain_ac, rain1, how="inner")

            time0_add_span = times[0] + np.timedelta64(int(min_dhour * (step - 1)),'h')
            rain_ac = meteva_base.sele_by_para(rain_ac,time_range=[time0_add_span,times[-1]])
            if not keep_all:
                dtimes = times[:] - times[-1]
                dh = (dtimes / min_dtime).astype(np.int32)
                new_times = times[dh % step == 0]
                rain_ac = meteva_base.in_time_list(rain_ac, new_times)
            return rain_ac
    elif used_coords ==["dtime"]:
        if span is None:
            dtimes = sta.loc[:, 'dtime'].values
            dtimes = list(set(dtimes))
            dtimes.sort()
            rain_ac = meteva_base.in_dtime_list(sta, [dtimes[0]])
            meteva_base.set_stadata_coords(rain_ac, dtime=dtimes[-1])
            for i in range(1, len(dtimes)):
                rain01 = meteva_base.in_dtime_list(sta, dtimes[i])
                meteva_base.set_stadata_coords(rain01, dtime=dtimes[-1])
                rain_ac = meteva_base.add_on_level_time_dtime_id(rain_ac, rain01, how="outer",default=0)

                # rain_ac0 = rain_ac.copy()
                # a = rain_ac0.duplicated(subset=["level","time","dtime","id"])
                # for ii in range(len(a)):
                #     if a[ii]:
                #         ids = rain_ac["id"].values[ii]
                #         sta4 = meteva_base.sele_by_para(rain_ac,id = ids)
                #         print(sta4)
                #         print()

                #rain_ac.drop_duplicates(subset=["level","time","dtime","id"],inplace=True)
            return rain_ac
        else:
            dtimes = sta.loc[:, 'dtime'].values
            dtimes = list(set(dtimes))
            dtimes.sort()
            dtimes = np.array(dtimes)
            dhour_unit = dtimes[1] - dtimes[0]

            #if dhour_unit == 0:
            #    dhour_unit = dtimes[1]

            rain_ac = sta.copy()
            #print(span)
            #print(dhour_unit)
            step = int(round(span/dhour_unit))
            #print(step)
            for i in range(1,step):
                rain1 = sta.copy()
                rain1["dtime"] = rain1["dtime"] + dhour_unit * i
                # print(dhour_unit * i)
                rain_ac = meteva_base.add_on_level_time_dtime_id(rain_ac, rain1, default=0)

            begin_dtime = dtimes[0]+dhour_unit * (step - 1)
            rain_ac = meteva_base.between_dtime_range(rain_ac,begin_dtime,dtimes[-1])  # 删除时效小于range的部分
            dtimes =set(rain_ac.loc[:, "dtime"].values.tolist())
            dtimes = list(dtimes)
            dtimes.sort()
            dtimes = np.array(dtimes)
            if not keep_all:
                dh = ((dtimes - dtimes[-1]) / dhour_unit).astype(np.int32)
                new_dtimes = dtimes[dh % step == 0]
                rain_ac = meteva_base.in_dtime_list(rain_ac, new_dtimes)
            return rain_ac

#获取网格数据的平均值
def mean_of_grd(grd,used_coords = ["member"],span = None):

    if used_coords==["member"]:
        grid0 = meteva_base.basicdata.get_grid_of_data(grd)
        grid1 = meteva_base.basicdata.grid(grid0.glon,grid0.glat,grid0.gtime,grid0.dtimes,grid0.levels,member_list=["mean"])
        dat = np.squeeze(grd.values)
        if len(dat.shape) > 2:
            dat = np.mean(dat,axis = 0)
        grd1 = meteva_base.basicdata.grid_data(grid1,dat)
        return grd1
    elif used_coords == "dtime" or used_coords == ["dtime"]:
        if span == None:
            grid0 = meteva_base.get_grid_of_data(grd)
            dtimes = np.array(grid0.dtimes)
            dtimes_sum = [dtimes[-1]]
            grid1 = meteva_base.grid(grid0.glon, grid0.glat, grid0.gtime, dtimes_sum, grid0.levels, grid0.members)
            grd_mean = meteva_base.grid_data(grid1)
            grd_mean.values[:, :, :, 0, :, :] = np.mean(grd.values[:, :, :, :, :, :], axis=3)
            return grd_mean
        else:
            grid0 = meteva_base.get_grid_of_data(grd)
            dtimes = np.array(grid0.dtimes)
            dtimes_sum = dtimes[dtimes >= span]
            grid1 = meteva_base.grid(grid0.glon, grid0.glat, grid0.gtime, dtimes_sum, grid0.levels, grid0.members)
            grd_mean = meteva_base.grid_data(grid1)
            for i in range(len(dtimes_sum)):
                dtime_e = dtimes_sum[i]
                dtime_s = dtimes_sum[i] - span
                index = np.where((dtimes > dtime_s) & (dtimes <= dtime_e))[0]

                grd_mean.values[:, :, :, i, :, :] = np.mean(grd.values[:, :, :, index, :, :], axis=3)
            return grd_mean
    elif used_coords =="time" or used_coords ==["time"]:
        if span ==None:
            grid0 = meteva_base.get_grid_of_data(grd)
            grid1 = meteva_base.grid(grid0.glon, grid0.glat, [grid0.gtime[1]], grid0.dtimes, grid0.levels,
                                     grid0.members)
            grd_mean = meteva_base.grid_data(grid1)

            grd_mean.values[:, :, 0, :, :, :] = np.mean(grd.values[:, :, :, :, :, :], axis=2)
            return grd_mean
        else:
            grid0 = meteva_base.get_grid_of_data(grd)
            grd_mean = meteva_base.grid_data(grid0)
            values = grd.values.copy()
            step = grid0.dtime_int
            half = int(span/step/2)
            kernal = np.ones(half * 2 +1)
            kernal[0] = 0.5
            kernal[-1] = 0.5
            shape = values.shape
            ntime = values.shape[2]
            for i in range(ntime):
                sum_v = np.zeros((shape[0],shape[1],shape[3],shape[4],shape[5]))
                sum_q = 0
                for k in range(-half,half+1,1):
                    i_k = i + k
                    if i_k>=0 and i_k< values.shape[2]:
                        q = kernal[k + half]
                        sum_v += grd.values[:, :, i_k, :, :, :] * q
                        sum_q+= q
                sum_v /= sum_q
                grd_mean.values[:, :, i, :, :, :] = sum_v

            return grd_mean



#获取网格数据的方差
def var_of_grd(grd,used_coords = ["member"]):
    grid0 = meteva_base.basicdata.get_grid_of_data(grd)
    grid1 = meteva_base.basicdata.grid(grid0.glon,grid0.glat,grid0.gtime,grid0.dtimes,grid0.levels,member_list=["var"])
    dat = np.squeeze(grd.values)
    if len(dat.shape) > 2:
        dat = np.var(dat,axis = 0)
    grd1 = meteva_base.basicdata.grid_data(grid1,dat)
    return grd1

#获取网格数据的标准差
def std_of_grd(grd,used_coords = ["member"]):
    grid0 = meteva_base.basicdata.get_grid_of_data(grd)
    grid1 = meteva_base.basicdata.grid(grid0.glon,grid0.glat,grid0.gtime,grid0.dtimes,grid0.levels,member_list=["std"])
    dat = np.squeeze(grd.values)
    if len(dat.shape) > 2:
        dat = np.std(dat,axis = 0)
    grd1 = meteva_base.basicdata.grid_data(grid1,dat)
    return grd1

#获取网格数据的最小值
def min_of_grd(grd,used_coords = ["member"]):
    grid0 = meteva_base.basicdata.get_grid_of_data(grd)
    grid1 = meteva_base.basicdata.grid(grid0.glon,grid0.glat,grid0.gtime,grid0.dtimes,grid0.levels,member_list=["min"])
    dat = np.squeeze(grd.values)
    if len(dat.shape)>2:
        dat = np.min(dat,axis = 0)
    grd1 = meteva_base.basicdata.grid_data(grid1,dat)
    return grd1

#获取网格数据的最大值
def max_of_grd(grd,used_coords = ["member"]):
    grid0 = meteva_base.basicdata.get_grid_of_data(grd)
    grid1 = meteva_base.basicdata.grid(grid0.glon,grid0.glat,grid0.gtime,grid0.dtimes,grid0.levels,member_list=["max"])
    dat = np.squeeze(grd.values)
    if len(dat.shape)>2:
        dat = np.max(dat,axis = 0)
    grd1 = meteva_base.basicdata.grid_data(grid1,dat)
    return grd1

#获取网格数据的求和
def sum_of_grd(grd,used_coords = ["member"],span = None, keep_all=True):
    if used_coords ==["member"]:
        grid0 = meteva_base.basicdata.get_grid_of_data(grd)
        grid1 = meteva_base.basicdata.grid(grid0.glon,grid0.glat,grid0.gtime,grid0.dtimes,grid0.levels,member_list=["max"])
        dat = np.squeeze(grd.values)
        if len(dat.shape) > 2:
            dat = np.sum(dat,axis = 0)
        grd1 = meteva_base.basicdata.grid_data(grid1,dat)
        return grd1
    elif used_coords == "dtime" or used_coords ==["dtime"]:
        if span == None:
            grid0 = meteva_base.get_grid_of_data(grd)
            dtimes = np.array(grid0.dtimes)
            dtimes_sum = [dtimes[-1]]
            grid1 = meteva_base.grid(grid0.glon, grid0.glat, grid0.gtime, dtimes_sum, grid0.levels, grid0.members)
            grd_sum = meteva_base.grid_data(grid1)
            grd_sum.values[:, :, :, 0, :, :] = np.sum(grd.values[:, :, :, :, :, :], axis=3)
        else:
            grid0 = meteva_base.get_grid_of_data(grd)
            dtimes = np.array(grid0.dtimes)
            dtimes_sum = dtimes[dtimes>=span]
            grid1 = meteva_base.grid(grid0.glon,grid0.glat,grid0.gtime,dtimes_sum,grid0.levels,grid0.members)
            grd_sum = meteva_base.grid_data(grid1)
            for i in range(len(dtimes_sum)):
                dtime_e = dtimes_sum[i]
                dtime_s = dtimes_sum[i] - span
                index = np.where((dtimes > dtime_s) & (dtimes <= dtime_e))[0]

                grd_sum.values[:,:,:,i,:,:] = np.sum(grd.values[:,:,:,index,:,:],axis=3)
        if not keep_all: #只保留时刻预报时效
            fhs = np.sort(grd_sum.dtime.values)
            fhs0 = np.arange(fhs[-1], fhs[0]-1, 0-span)[::-1]
            grd_sum = grd_sum.sel(dtime = fhs0.tolist())
        return grd_sum
    elif used_coords =="time" or used_coords ==["time"]:
        if span ==None:
            grid0 = meteva_base.get_grid_of_data(grd)
            grid1 = meteva_base.grid(grid0.glon, grid0.glat, [grid0.gtime[1]], grid0.dtimes, grid0.levels, grid0.members)
            grd_sum = meteva_base.grid_data(grid1)
            grd_sum.values[:, :, 0, :, :, :] = np.sum(grd.values[:, :, :, :, :, :], axis=2)
        else:
            grid0 = meteva_base.get_grid_of_data(grd)
            grd_sum = meteva_base.grid_data(grid0)
            values = grd.values.copy()
            step = grid0.dtime_int
            count = int(span/step)

            shape = values.shape
            ntime = values.shape[2]
            for i in range(ntime):
                sum_v = np.zeros((shape[0],shape[1],shape[3],shape[4],shape[5]))
                for k in range(-count+1,1):
                    i_k = i + k
                    if i_k <0:continue
                    sum_v += grd.values[:, :, i_k, :, :, :]
                grd_sum.values[:, :, i, :, :, :] = sum_v

            grd_sum = grd_sum.isel(time = slice(count-1,ntime))
        return grd_sum



def time_ceilling(sta,step = 1, time_unit = "h",begin_hour= 8):
    '''
    将不规则时间观测数据累计到固定步长的整点时刻
    :param sta: 站点数据，例如原始的闪电观测数据
    :param step:  累计的步长
    :param time_unit: 累计的时间单位，可选项包括 “H"和”M"，分别代表小时和分钟。
    :param begin_hour: 时间类型，当累计步长超过1小时,例如3小时，起步累计的时间是从08时还是00时，通常对北京时数据来说以08时起步，世界时则以00时起步
    :return:
    '''
    sta1 = sta.copy()
    time0 = datetime.datetime(2000,1,1,begin_hour,0)
    if time_unit.lower() == "h":
        step *= 3600
    else:
        step *= 60
    delta = ((sta["time"] - time0)/np.timedelta64(1,"s")).values
    delta =np.ceil(delta/step) * step
    sta1["time"] = time0
    sta1["time"] += delta * np.timedelta64(1, "s")
    return sta1

def loc_of_max(sta,used_coords = ["dtime"],ignore_missing = False):
    '''
    返回站点数据在某些维度上最大值的坐标
    :param sta:
    :param used_coords:
    :param span:
    :param keep_all:
    :param ignore_missing:
    :return:
    '''
    if not isinstance(used_coords,list):
        used_coords = [used_coords]

    default = np.min(sta.iloc[:,6:].values)
    if ignore_missing:
        how = "outer"
    else:
        how = "inner"
    if used_coords  == ["dtime"]:
        dtimes = sta.loc[:, 'dtime'].values
        dtimes = list(set(dtimes))
        dtimes.sort()
        dtime_array = np.array(dtimes)
        data_names = meteva_base.get_stadata_names(sta)
        max_loc = None
        for data_name in data_names:
            sta1 = meteva_base.in_member_list(sta,[data_name])

            sta1_0 = meteva_base.in_dtime_list(sta1,[dtimes[0]])
            meteva_base.set_stadata_coords(sta1_0, dtime=0)
            for i in range(1, len(dtimes)):
                sta1_1 = meteva_base.in_dtime_list(sta1, dtimes[i])
                meteva_base.set_stadata_coords(sta1_1, dtime=0)
                meteva_base.set_stadata_names(sta1_1,data_name_list=[data_name+"_"+str(i)])
                sta1_0 = pd.merge(sta1_0, sta1_1, on=["level", "time", "dtime", "id","lon","lat"], how=how)

            sta1_0.fillna(default, inplace=True)

            all_values = sta1_0.iloc[:, 6:].values
            max_index = np.argmax(all_values,axis=1)
            max_dtime = dtime_array[max_index]
            sta1_dtime = meteva_base.in_member_list(sta1_0,[data_name])
            sta1_dtime.iloc[:,-1] = max_dtime[:]
            max_loc = meteva_base.combine_on_level_time_dtime_id(max_loc,sta1_dtime)

        return max_loc

def loc_of_min(sta,used_coords = ["dtime"],ignore_missing = False):
    sta1 = sta.copy()
    sta1.iloc[:,6:] *= -1
    return loc_of_max(sta1,used_coords=used_coords,ignore_missing = ignore_missing)



######### 格点数据时间拆分技术  #########

def read_multi_griddata(fmt, time, fhs, io_method=None, is_ob=False, is_fill0=True):
    """
    读取多时次网格数据，并merge融合为DataSet输出
    is_ob: 是否实况。是：time=time+fh,fh=0.
    is_fill0: 当dtime=0时，是否自动赋值value=0
    """
    import xarray as xr
    if io_method == None:
        io_method = meb.read_griddata_from_nc
    grd_list =[]
    flag0 = 0 ##是否需要补fh=0时刻的0值
    for i,fh in enumerate(fhs):
        if is_ob:
            time0 = time+datetime.timedelta(hours=int(fh))
            fh0 = 0
        else:
            time0 = time
            fh0 = fh
        tp03_file = meb.get_path(fmt, time=time0,  dt=int(fh0))
        if i%5==0: print('Read FILE: ',i, time0, fh0, tp03_file)
        if not os.path.exists(tp03_file):
            print('File missing: {}-{}'.format(time0, fh0))
            continue
        if not is_fill0:#不需要补0，直接读取fh=0
            grd = io_method(tp03_file)
            meb.set_griddata_coords(grd, gtime=[time0], dtime_list=[fh0])
            grd_list.append(grd)
        else:#无fh=0的数据，直接补0
            if fh0==0:#为0时，需要补充
                flag0 = 1
            else:
                grd = io_method(tp03_file)
                meb.set_griddata_coords(grd, gtime=[time0], dtime_list=[fh0])
                if flag0:#先补充fh=0的零值网格数据
                    grd_00 = grd.copy()
                    grd_00.values = np.zeros_like(grd_00.values)
                    meb.set_griddata_coords(grd_00, dtime_list=[0])
                    grd_list.append(grd_00)
                    flag0 = 0
                grd_list.append(grd)
    ## 组合数据
    try:
        grd_list0 = [i.astype(np.float32) for i in grd_list]
        del(grd_list)
        grd_all = meb.concat(grd_list0)
    except Exception as err:
        print(err)
        return None
    return grd_all


def cal_griddata_TimeSplit(input_fmt,  time, output_fmt=None,
    input_fh_list=np.arange(3,73,3), output_fh_list=np.arange(0,73,1),  interp_method='slinear', io_method = None,
    uv_fmt = None, #如非None,风速合成
    delta_hour = None, #delta变量
    is_fill0 = False, #fh=0时是读取文件或填0值
    ):
    """
    时间拆分预处理，包括uv生成风速、逐delta小时相减等计算
    """
    ## read data
    fh03_list = input_fh_list
    fh01_list = output_fh_list
    try:
        ## 组合数据 
        grd_all = read_multi_griddata(input_fmt, time, fh03_list, io_method=io_method, is_fill0=is_fill0)#DataArray
        print(grd_all)
        ## 预处理, UV风读取并合成风速
        if uv_fmt is not None:
            grd_0 = read_multi_griddata(uv_fmt, time, fh03_list, io_method=io_method, is_fill0=is_fill0)#读取v分量
            print(grd_0)
            # grd_all, _ = cal_wswd_from_meteva_uvgrid(grd_all, grd_0)#计算风速
            grd_all, _ = meb.u_v_to_speed_angle(grd_all, grd_0)#计算风速
        ## 拆分数据
        grd_all_01h = grd_all.interp(dtime=fh01_list, method=interp_method, kwargs={"fill_value": "extrapolate"})    
        ## 后处理，计算时间变量(delta)
        if delta_hour is not None:
            grd_all_01h = meb.change(grd_all_01h, delta=delta_hour, used_coords="dtime")
    except Exception as err:
        print(err)
        return None,None
    # 输出
    if output_fmt is not None:#输出拆分结果nc
        for fh01 in fh01_list:
            out_file = meb.get_path(output_fmt, time=time, dt=fh01)
            if not os.path.exists(out_file):
                try:
                    grd_01h = grd_all_01h.sel(dtime=[fh01]).astype(np.float32)
                    # grd_01h = grd_01h.astype(np.float32)
                    grd_01h.values[grd_01h.values<0] = 0#最小为0
                    meb.write_griddata_to_nc(grd_01h, out_file, effectiveNum=2, creat_dir=True)
                    print(out_file)
                except Exception as err:
                    print(err, time, fh01)
                    continue
    return(grd_all_01h, grd_all)


class EnsData_Pre_rain03(object):
    """
    集合预报(网格数据)预处理，多时次预报合并，拆分至03h，从tp中计算rain03(时段累积)
    """
    def __init__(self,  input_fmt=None, output_fmt=None, input_fh_list=np.arange(0,73,3), output_fh_list=np.arange(0,73,1),
                        delta_hour=None,  interp_method='slinear', io_method = None):
        self.input_fmt      = input_fmt
        self.output_fmt     = output_fmt 
        self.input_fh_list  = input_fh_list
        self.output_fh_list = output_fh_list
        self.delta_hour     = delta_hour
        self.method         = interp_method
        self.io_method      = io_method

    def process(self, times):
        for time in times:
            print('Calculation: {}'.format(time))
            grd_03, grd_all = cal_griddata_TimeSplit(input_fmt=self.input_fmt, time=time, output_fmt=self.output_fmt,
                        input_fh_list=self.input_fh_list, output_fh_list=self.output_fh_list,
                        delta_hour=self.delta_hour,
                        interp_method=self.method, io_method=self.io_method, is_fill0=True)
        return grd_03, grd_all

######### 格点数据时间累加技术  #########
def sum_grd01h_to_03_24h(input_fmt, time, output_fmt=None, output_fmt2=None,
    input_fh_list=np.arange(1,25,1), 
    span1=3, span2=None, 
    io_method=None, is_ob=True):
    """
    将逐小时网格数据累加为其他时效(逐3h或逐24h<可选>)
    is_ob: True-处理为观测时间time，fh=0； False-与预报一直的time+fh
    """
    import xarray as xr
    fh01_list = input_fh_list
    grd_all = read_multi_griddata(input_fmt, time, fh01_list, io_method=io_method, is_ob=is_ob)#DataArray
    grd0 = grd_all
    try:
        ## 累加并提取
        grd03 = meb.sum_of_grd(grd0, used_coords="time", span=span1)#包括全部03h
        grd03 = _sel_keep_True(grd03, time, time0, add_hour=0-span1)
        if span2 is not None:
            grd24 = meb.sum_of_grd(grd0, used_coords="time", span=span2)#包括全部24h
            grd24 = _sel_keep_True(grd24, time, time0, add_hour=0-span2)
        else:
            grd24 = None
        # 输出
        if output_fmt is not None:#输出拆分结果nc
            fh03_list = grd03.dtime.values
            for fh03 in fh03_list:
                out_file = meb.get_path(output_fmt, time=time, dt=fh03)
                if not os.path.exists(out_file):
                    try:
                        grd = grd03.sel(dtime=[fh03])
                        grd.values[grd.values<0] = 0#最小为0
                        meb.write_griddata_to_nc(grd, out_file, effectiveNum=2, creat_dir=True)
                    except Exception as err:
                        print(err, time, fh03)
                        continue
        if span2 is not None and output_fmt2 is not None :#输出拆分结果nc
            fh24_list = grd24.dtime.values
            for fh24 in fh24_list:
                out_file = meb.get_path(output_fmt2, time=time, dt=fh24)
                if not os.path.exists(out_file):
                    try:
                        grd = grd24.sel(dtime=[fh24])
                        grd.values[grd.values<0] = 0#最小为0
                        meb.write_griddata_to_nc(grd, out_file, effectiveNum=2, creat_dir=True)
                    except Exception as err:
                        print(err, time, fh24)
                        continue
        return(grd03, grd24)
    except Exception as err:
        print(Exception)
        return None,None
        

def _sel_keep_True(grd, time, time0, add_hour=-3):
    ## 3h累加及挑选
    times03 = mtl.get_date_list_pd([time, time0, add_hour])
    times03.sort()
    dim_time = grd.coords["time"]#time维度
    try:
        temp = np.array([meb.all_type_time_to_datetime(i) for i in dim_time.values])
        flag = np.isin(temp, times03)  #挑选合适的flag(time维度isin对应的times03范围内)
        grd = grd.loc[
            dict(time=flag)
        ]
        return grd
    except Exception as err:
        print(err)
        return None