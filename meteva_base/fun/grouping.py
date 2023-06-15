# import meteva
import meteva_base
import datetime
import pandas as pd
import numpy as np
import copy


def group(sta_ob_and_fos,g = None,gll = None,drop_g_column = False):
    valid_group_list_list = []
    sta_ob_and_fos_list = []
    if g is None:
        sta_ob_and_fos_list.append(sta_ob_and_fos)
    else:
        group_list_list = gll
        if gll is not None:
            group_list_list0 = []
            for group_list in gll:
                if isinstance(group_list,list):
                    group_list_list0.append(group_list)
                else:
                    group_list_list0.append([group_list])
            group_list_list = group_list_list0
        valid_group = ["level","time","time_range","year","month","day","dayofyear","hour","xun",
                       "ob_time","ob_time_range","ob_year","ob_month","ob_day","ob_dayofyear","ob_hour",
                       "dtime","dtime_range","dday","dhour","id","lon_range","lon_step","lat_range","lat_step","last_range","last_step","grid",
                       "province_name","member"]

        data_names = meteva_base.get_stadata_names(sta_ob_and_fos)

        data_names_range = []
        for data_name in data_names:
            data_names_range.append(str(data_name) + "_range")

        data_names_step = []
        for data_name in data_names:
            data_names_step.append(str(data_name) + "_step")

        valid_group.extend(data_names)
        valid_group.extend(data_names_range)
        valid_group.extend(data_names_step)

        if not g in valid_group:
            print("group_by 参数必须为如下列表中的选项：")
            print(str(valid_group))
            return None
        if g in data_names:
            if group_list_list is None:
                grouped_dict = dict(list(sta_ob_and_fos.groupby(g)))
                keys = grouped_dict.keys()
                for key in keys:
                    valid_group_list_list.append([key])
                    sta = grouped_dict[key]
                    if drop_g_column:
                        sta = sta.drop(labels=g, axis=1)
                    sta_ob_and_fos_list.append(sta)
            else:
                for group_list in group_list_list:
                    sta = meteva_base.in_one_column_value_list(sta_ob_and_fos,g, group_list)
                    if len(sta.index) != 0:
                        valid_group_list_list.append(group_list)
                        if drop_g_column:
                            sta = sta.drop(labels=g, axis=1)
                        sta_ob_and_fos_list.append(sta)

        elif g in data_names_range:
            if group_list_list is None:
                print("当group_by =" + g + "时 group_list_list 参数不能为None")
            else:
                name1 = g.split("_")[0]
                for group_list in group_list_list:
                    sta = meteva_base.between_one_column_value_range(sta_ob_and_fos, name1,group_list[0], group_list[1])
                    if len(sta.index) != 0:
                        valid_group_list_list.append(group_list)
                        sta_ob_and_fos_list.append(sta)

        elif g in data_names_step:
            if group_list_list is None:
                print("当group_by =" + g + "时 group_list_list 参数不能为None")
            else:
                name1 = g.split("_")[0]
                group_list_list1 = []
                start = group_list_list[0][0]
                step = group_list_list[1][0]
                min = np.min(sta_ob_and_fos.loc[:,name1])
                max = np.max(sta_ob_and_fos.loc[:,name1])
                min =start - (int((start - min) / step) + 1) *step
                max = start + (int((max - start)/step) +1) * step
                value_list = np.arange(min,max,step)
                for value in value_list:
                    group_list_list1.append([value,value+ step - 1e-6])
                for group_list in group_list_list1:
                    sta = meteva_base.between_one_column_value_range(sta_ob_and_fos,name1,group_list[0],group_list[1])
                    if len(sta.index) !=0:
                        valid_group_list_list.append(group_list)
                        sta_ob_and_fos_list.append(sta)

        elif g == "level":
            if group_list_list is None:
                grouped_dict = dict(list(sta_ob_and_fos.groupby(g)))
                keys = grouped_dict.keys()
                for key in keys:
                    valid_group_list_list.append([key])
                    sta_ob_and_fos_list.append(grouped_dict[key])
            else:
                for group_list in group_list_list:
                    sta = meteva_base.in_level_list(sta_ob_and_fos,group_list)
                    if len(sta.index) !=0:
                        valid_group_list_list.append(group_list)
                        sta_ob_and_fos_list.append(sta)
        elif g == "time":
            if group_list_list is None:
                grouped_dict = dict(list(sta_ob_and_fos.groupby(g)))
                keys = grouped_dict.keys()

                for key in keys:
                    valid_group_list_list.append([key])
                    sta_ob_and_fos_list.append(grouped_dict[key])
            else:
                for group_list in group_list_list:
                    sta = meteva_base.in_time_list(sta_ob_and_fos,group_list)
                    if len(sta.index) !=0:
                        valid_group_list_list.append(group_list)
                        sta_ob_and_fos_list.append(sta)


        elif g == "time_range":
            if group_list_list is None:
                print("当group_by = time_range时 group_list_list 参数不能为None")
            else:
                for group_list in group_list_list:
                    sta = meteva_base.between_time_range(sta_ob_and_fos,group_list[0],group_list[1])
                    if len(sta.index) !=0:
                        valid_group_list_list.append(group_list)
                        sta_ob_and_fos_list.append(sta)


        elif g == "year":
            fo_times = pd.Series(0, index=sta_ob_and_fos['time'])
            if group_list_list is None:
                grouped_dict = dict(list(sta_ob_and_fos.groupby(fo_times.index.year)))
                keys = grouped_dict.keys()
                for key in keys:
                    valid_group_list_list.append([key])
                    sta_ob_and_fos_list.append(grouped_dict[key])
            else:
                for group_list in group_list_list:
                    sta = sta_ob_and_fos.loc[fo_times.index.year.isin(group_list)]
                    if len(sta.index) !=0:
                        valid_group_list_list.append(group_list)
                        sta_ob_and_fos_list.append(sta)

        elif g == "month":
            fo_times = pd.Series(0, index=sta_ob_and_fos['time'])
            if group_list_list is None:
                grouped_dict = dict(list(sta_ob_and_fos.groupby(fo_times.index.month)))
                keys = grouped_dict.keys()
                for key in keys:
                    valid_group_list_list.append([key])
                    sta_ob_and_fos_list.append(grouped_dict[key])
            else:
                for group_list in group_list_list:
                    sta = sta_ob_and_fos.loc[fo_times.index.month.isin(group_list)]
                    if len(sta.index) !=0:
                        valid_group_list_list.append(group_list)
                        sta_ob_and_fos_list.append(sta)
        elif g == "day":
            time0 = datetime.datetime(1900, 1, 1, 0, 0)
            seconds = 3600 * 24
            indexs = (sta_ob_and_fos['time'] - time0) // np.timedelta64(1, "D")
            if group_list_list is None:
                grouped_dict = dict(list(sta_ob_and_fos.groupby(indexs)))
                keys = grouped_dict.keys()
                for key in keys:
                    valid_group_list_list.append([time0 + datetime.timedelta(days=key)])
                    sta_ob_and_fos_list.append(grouped_dict[key])
            else:
                for group_list in group_list_list:
                    days_list = []
                    for day0 in group_list:
                        day1 = meteva_base.all_type_time_to_datetime(day0)
                        day = (day1 - time0).total_seconds() // seconds
                        days_list.append(day)
                    sta = sta_ob_and_fos.loc[indexs.isin(days_list)]
                    if len(sta.index) !=0:
                        valid_group_list_list.append(group_list)
                        sta_ob_and_fos_list.append(sta)
        elif g == "dayofyear":
            fo_times = pd.Series(0, index=sta_ob_and_fos['time'])
            if group_list_list is None:
                grouped_dict = dict(list(sta_ob_and_fos.groupby(fo_times.index.dayofyear)))
                keys = grouped_dict.keys()
                for key in keys:
                    valid_group_list_list.append([key])
                    sta_ob_and_fos_list.append(grouped_dict[key])
            else:
                for group_list in group_list_list:
                    sta = sta_ob_and_fos.loc[fo_times.index.dayofyear.isin(group_list)]
                    if len(sta.index) !=0:
                        valid_group_list_list.append(group_list)
                        sta_ob_and_fos_list.append(sta)
        elif g == "hour":
            fo_times = pd.Series(0, index=sta_ob_and_fos['time'])
            if group_list_list is None:
                grouped_dict = dict(list(sta_ob_and_fos.groupby(fo_times.index.hour)))
                keys = grouped_dict.keys()
                for key in keys:
                    valid_group_list_list.append([key])
                    sta_ob_and_fos_list.append(grouped_dict[key])
            else:
                for group_list in group_list_list:
                    sta = sta_ob_and_fos.loc[fo_times.index.hour.isin(group_list)]
                    if len(sta.index) !=0:
                        valid_group_list_list.append(group_list)
                        sta_ob_and_fos_list.append(sta)
        elif g == "xun":
            sta_ob_and_fos.reset_index(drop = True,inplace = True)
            fo_times = pd.Series(0, index=sta_ob_and_fos['time'])
            mons = fo_times.index.month.astype(np.int16)
            days = fo_times.index.day.astype(np.int16)
            xuns = np.ceil(days / 10).values.astype(np.int16)
            xuns[xuns > 3] = 3
            xuns += (mons - 1) * 3
            xuns = pd.Series(xuns)
            if group_list_list is None:
                grouped_dict = dict(list(sta_ob_and_fos.groupby(xuns)))
                keys = grouped_dict.keys()
                for key in keys:
                    valid_group_list_list.append([key])
                    sta_ob_and_fos_list.append(grouped_dict[key])
            else:
                for group_list in group_list_list:
                    sta = sta_ob_and_fos.loc[fo_times.index.hour.isin(group_list)]
                    if len(sta.index) !=0:
                        valid_group_list_list.append(group_list)
                        sta_ob_and_fos_list.append(sta)

        elif g == "ob_time":
            dtimes = sta_ob_and_fos["dtime"] * np.timedelta64(1, 'h')
            obtimes = sta_ob_and_fos['time'] + dtimes
            if group_list_list is None:
                grouped_dict = dict(list(sta_ob_and_fos.groupby(obtimes)))
                keys = grouped_dict.keys()
                for key in keys:
                    valid_group_list_list.append([key])
                    sta_ob_and_fos_list.append(grouped_dict[key])
            else:

                for group_list in group_list_list:
                    group_list1 = []
                    for time_g1 in group_list:
                        group_list1.append(meteva_base.all_type_time_to_datetime(time_g1))
                    sta = sta_ob_and_fos.loc[obtimes.isin(group_list1)]

                    if len(sta.index) !=0:
                        valid_group_list_list.append(group_list1)
                        sta_ob_and_fos_list.append(sta)
        elif g == "ob_time_range":
            if group_list_list is None:
                print("当group_by = ob_time_range时 group_list_list 参数不能为None")
            else:
                for group_list in group_list_list:
                    sta = meteva_base.between_ob_time_range(sta_ob_and_fos,group_list[0],group_list[1])
                    if len(sta.index) !=0:
                        valid_group_list_list.append(group_list)
                        sta_ob_and_fos_list.append(sta)


        elif g == "ob_year":
            dtimes = sta_ob_and_fos["dtime"] * np.timedelta64(1, 'h')
            obtimes = pd.Series(0, index=sta_ob_and_fos['time'] + dtimes)
            if group_list_list is None:
                grouped_dict = dict(list(sta_ob_and_fos.groupby(obtimes.index.year)))
                keys = grouped_dict.keys()
                for key in keys:
                    valid_group_list_list.append([key])
                    sta_ob_and_fos_list.append(grouped_dict[key])
            else:
                for group_list in group_list_list:
                    sta = sta_ob_and_fos.loc[obtimes.index.year.isin(group_list)]
                    if len(sta.index) !=0:
                        valid_group_list_list.append(group_list)
                        sta_ob_and_fos_list.append(sta)

        elif g == "ob_month":
            dtimes = sta_ob_and_fos["dtime"] * np.timedelta64(1, 'h')
            obtimes = pd.Series(0, index=sta_ob_and_fos['time'] + dtimes)
            if group_list_list is None:
                grouped_dict = dict(list(sta_ob_and_fos.groupby(obtimes.index.month)))
                keys = grouped_dict.keys()
                for key in keys:
                    valid_group_list_list.append([key])
                    sta_ob_and_fos_list.append(grouped_dict[key])
            else:
                for group_list in group_list_list:
                    sta = sta_ob_and_fos.loc[obtimes.index.month.isin(group_list)]
                    if len(sta.index) !=0:
                        valid_group_list_list.append(group_list)
                        sta_ob_and_fos_list.append(sta)
        elif g == "ob_day":
            dtimes = sta_ob_and_fos["dtime"] * np.timedelta64(1, 'h')
            obtimes = pd.Series(0, index=sta_ob_and_fos['time'] + dtimes)
            time0 = datetime.datetime(1900, 1, 1, 0, 0)
            seconds = 3600 * 24
            indexs = (obtimes.index - time0) // np.timedelta64(1, "D")

            if group_list_list is None:
                grouped_dict = dict(list(sta_ob_and_fos.groupby(indexs)))
                keys = grouped_dict.keys()
                for key in keys:
                    valid_group_list_list.append([time0 + datetime.timedelta(days=key)])
                    sta_ob_and_fos_list.append(grouped_dict[key])
            else:
                for group_list in group_list_list:
                    days_list = []
                    for day0 in group_list:
                        day = (day0 - time0).total_seconds() // seconds
                        days_list.append(day)
                    sta = sta_ob_and_fos.loc[indexs.isin(days_list)]
                    if len(sta.index) !=0:
                        valid_group_list_list.append(group_list)
                        sta_ob_and_fos_list.append(sta)
        elif g == "ob_dayofyear":
            dtimes = sta_ob_and_fos["dtime"] * np.timedelta64(1, 'h')
            obtimes = pd.Series(0, index=sta_ob_and_fos['time'] + dtimes)
            if group_list_list is None:
                grouped_dict = dict(list(sta_ob_and_fos.groupby(obtimes.index.dayofyear)))
                keys = grouped_dict.keys()
                for key in keys:
                    valid_group_list_list.append([key])
                    sta_ob_and_fos_list.append(grouped_dict[key])
            else:
                for group_list in group_list_list:
                    sta = sta_ob_and_fos.loc[obtimes.index.dayofyear.isin(group_list)]
                    if len(sta.index) !=0:
                        valid_group_list_list.append(group_list)
                        sta_ob_and_fos_list.append(sta)
        elif g == "ob_hour":
            dtimes = sta_ob_and_fos["dtime"] * np.timedelta64(1, 'h')
            obtimes = pd.Series(0, index=sta_ob_and_fos['time'] + dtimes)
            if group_list_list is None:
                grouped_dict = dict(list(sta_ob_and_fos.groupby(obtimes.index.hour)))
                keys = grouped_dict.keys()
                for key in keys:
                    valid_group_list_list.append([key])
                    sta_ob_and_fos_list.append(grouped_dict[key])
            else:
                for group_list in group_list_list:
                    sta = sta_ob_and_fos.loc[obtimes.index.hour.isin(group_list)]
                    if len(sta.index) !=0:
                        valid_group_list_list.append(group_list)
                        sta_ob_and_fos_list.append(sta)

        elif g == "dtime":
            if group_list_list is None:
                grouped_dict = dict(list(sta_ob_and_fos.groupby(g)))
                keys = grouped_dict.keys()
                for key in keys:
                    valid_group_list_list.append([key])
                    sta_ob_and_fos_list.append(grouped_dict[key])
            else:
                for group_list in group_list_list:
                    sta = meteva_base.in_dtime_list(sta_ob_and_fos,group_list)
                    if len(sta.index) !=0:
                        valid_group_list_list.append(group_list)
                        sta_ob_and_fos_list.append(sta)

        elif g == "dtime_range":
            if group_list_list is None:
                print("当group_by = dtime_range时 group_list_list 参数不能为None")
            else:
                for group_list in group_list_list:
                    sta = meteva_base.between_dtime_range(sta_ob_and_fos,group_list[0],group_list[1])
                    if len(sta.index) !=0:
                        valid_group_list_list.append(group_list)
                        sta_ob_and_fos_list.append(sta)


        elif g == "dday":
            ddays = np.ceil(sta_ob_and_fos['dtime'] / 24)
            if group_list_list is None:
                grouped_dict = dict(list(sta_ob_and_fos.groupby(ddays)))
                keys = grouped_dict.keys()
                for key in keys:
                    valid_group_list_list.append([key])
                    sta_ob_and_fos_list.append(grouped_dict[key])
            else:
                for group_list in group_list_list:
                    sta = sta_ob_and_fos.loc[ddays.isin(group_list)]
                    if len(sta.index) !=0:
                        valid_group_list_list.append(group_list)
                        sta_ob_and_fos_list.append(sta)
        elif g == "dhour":
            dhours = sta_ob_and_fos['dtime'] % 24
            if group_list_list is None:
                grouped_dict = dict(list(sta_ob_and_fos.groupby(dhours)))
                keys = grouped_dict.keys()
                for key in keys:
                    valid_group_list_list.append([key])
                    sta_ob_and_fos_list.append(grouped_dict[key])
            else:
                for group_list in group_list_list:
                    sta = sta_ob_and_fos.loc[dhours.isin(group_list)]
                    if len(sta.index) !=0:
                        valid_group_list_list.append(group_list)
                        sta_ob_and_fos_list.append(sta)
        elif g == "id":
            if group_list_list is None:
                grouped_dict = dict(list(sta_ob_and_fos.groupby(g)))
                keys = grouped_dict.keys()
                for key in keys:
                    valid_group_list_list.append([key])
                    sta_ob_and_fos_list.append(grouped_dict[key])
            else:
                for group_list in group_list_list:
                    sta = meteva_base.in_id_list(sta_ob_and_fos,group_list)
                    if len(sta.index) !=0:
                        valid_group_list_list.append(group_list)
                        sta_ob_and_fos_list.append(sta)

        elif g == "lon_range":
            if group_list_list is None:
                print("当group_by = lon_range时 group_list_list 参数不能为None")
            else:
                for group_list in group_list_list:
                    sta = meteva_base.between_lon_range(sta_ob_and_fos,group_list[0],group_list[1])
                    if len(sta.index) !=0:
                        valid_group_list_list.append(group_list)
                        sta_ob_and_fos_list.append(sta)

        elif g == "lat_range":
            if group_list_list is None:
                print("当groupy = lat_range时 group_list_list 参数不能为None")
            else:
                for group_list in group_list_list:
                    sta = meteva_base.between_lat_range(sta_ob_and_fos, group_list[0], group_list[1])
                    if len(sta.index) != 0:
                        valid_group_list_list.append(group_list)
                        sta_ob_and_fos_list.append(sta)

        elif g == "last_range":
            if group_list_list is None:
                print("当group_by = last_range时 group_list_list 参数不能为None")
            else:
                for group_list in group_list_list:
                    sta = meteva_base.between_last_range(sta_ob_and_fos, group_list[0], group_list[1])
                    if len(sta.index) != 0:
                        valid_group_list_list.append(group_list)
                        sta_ob_and_fos_list.append(sta)

        elif g == "lon_step":
            if group_list_list is None:
                print("当group_by = lon_step时 group_list_list 参数不能为None")
            else:
                group_list_list1 = []
                start = group_list_list[0][0]
                step = group_list_list[1][0]
                min = np.min(sta_ob_and_fos.loc[:,"lon"])
                max = np.max(sta_ob_and_fos.loc[:,"lon"])
                min =start - (int((start - min) / step) + 1) *step
                max = start + (int((max - start)/step) +1) * step
                for value in range(min,max,step):
                    group_list_list1.append([value,value+ step - 1e-6])
                #print(group_list_list1)
                for group_list in group_list_list1:
                    sta = meteva_base.between_lon_range(sta_ob_and_fos,group_list[0],group_list[1])
                    if len(sta.index) !=0:
                        valid_group_list_list.append(group_list)
                        sta_ob_and_fos_list.append(sta)

        elif g == "lat_step":
            if group_list_list is None:
                print("当group_by = lat_step时 group_list_list 参数不能为None")
            else:
                group_list_list1 = []
                start = group_list_list[0][0]
                step = group_list_list[1][0]
                min = np.min(sta_ob_and_fos.loc[:, "lat"])
                max = np.max(sta_ob_and_fos.loc[:, "lat"])
                min = start - (int((start - min) / step) + 1) * step
                max = start + (int((max - start) / step) + 1) * step
                for value in range(min, max, step):
                    group_list_list1.append([value, value + step - 1e-6])

                for group_list in group_list_list1:
                    sta = meteva_base.between_lat_range(sta_ob_and_fos, group_list[0], group_list[1])
                    if len(sta.index) != 0:
                        valid_group_list_list.append(group_list)
                        sta_ob_and_fos_list.append(sta)

        elif g == "last_step":
            if group_list_list is None:
                print("当group_by = lat_range时 group_list_list 参数不能为None")
            else:
                group_list_list1 = []
                start = group_list_list[0][0]
                step = group_list_list[1][0]
                min = np.min(sta_ob_and_fos.iloc[:, -1])
                max = np.max(sta_ob_and_fos.iloc[:, -1])

                min = start - (int((start - min) / step) + 1) * step
                max = start + (int((max - start) / step) + 1) * step
                value_list = np.arange(min,max,step)
                for value in value_list:
                    group_list_list1.append([value, value + step - 1e-6])
                for group_list in group_list_list1:
                    sta = meteva_base.between_last_range(sta_ob_and_fos, group_list[0], group_list[1])
                    if len(sta.index) != 0:
                        valid_group_list_list.append(group_list)
                        sta_ob_and_fos_list.append(sta)
        elif g == "grid":
            if group_list_list is None:
                print("当group_by = grid时 group_list_list 参数不能为None")
            for group_list in group_list_list:
                sta = meteva_base.in_grid(sta_ob_and_fos, group_list[0])
                if len(sta.index) != 0:
                    valid_group_list_list.append(group_list)
                    sta_ob_and_fos_list.append(sta)
        elif g == "province_name":
            ids = list(set(sta_ob_and_fos["id"].values))
            sta_province_name = meteva_base.tool.get_station_format_province_set(ids)
            sta_with_province_name = meteva_base.combine_expand_IV(sta_ob_and_fos,sta_province_name)
            grouped_dict = dict(list(sta_with_province_name.groupby(g)))
            keys = grouped_dict.keys()
            for key in keys:
                valid_group_list_list.append([key])
                sta1 = grouped_dict[key].drop([g], axis=1)
                sta_ob_and_fos_list.append(sta1)
        elif g== "member":
            if group_list_list is None:
                group_list_list = meteva_base.get_stadata_names(sta_ob_and_fos)
            for group_list in group_list_list:
                sta = meteva_base.in_member_list(sta_ob_and_fos,group_list)
                if sta is not None and len(sta.index) != 0:
                    valid_group_list_list.append(group_list)
                    sta_ob_and_fos_list.append(sta)

        else:
            if group_list_list is None:
                grouped_dict = dict(list(sta_ob_and_fos.groupby(g)))
                keys = grouped_dict.keys()
                for key in keys:
                    valid_group_list_list.append([key])
                    sta1 = grouped_dict[key].drop([g],axis = 1)
                    #print(sta1)
                    sta_ob_and_fos_list.append(sta1)
            else:
                pass
                #for group_list in group_list_list:
                #    sta = meteva_base.in_one_column_list(sta_ob_and_fos, group_list)
                #    if len(sta.index) != 0:
                #        valid_group_list_list.append(group_list)
                #        sta_ob_and_fos_list.append(sta)


    #返回分组结果，和实际分组方式
    if len(valid_group_list_list)==0:
        valid_group_list = None
    else:
        vg =np.array(valid_group_list_list)
        if len(valid_group_list_list) > 1:
            valid_group_list =  vg.squeeze().tolist()
        else:
            if vg.size == 1:
                valid_group_list = valid_group_list_list[0]
            else:
                valid_group_list = valid_group_list_list

    return sta_ob_and_fos_list,valid_group_list


def split(sta_ob_and_fos,used_coords = ["level","time","dtime"],sta_list = None):
    '''

    :param sta_ob_and_fos: 包含多个层次，时间，时效，站点的观测和预报数据
    :param used_coords: 拆分的维度
    :param sta_list: 最终返回的结果
    :return:
    '''

    if sta_list is None:
        sta_list = []
    sta_group = group(sta_ob_and_fos, g=used_coords[0])[0]
    if len(used_coords) >1:
        # 取出第一个coord
        for sta in sta_group:
            split(sta,used_coords=used_coords[1:],sta_list = sta_list)
    else:
        for sta in sta_group:
            sta_list.append(sta)

    return sta_list

def split_grd(grd,used_coords = ["member","level","time","dtime"],grd_list = None):
    '''

    :param sta_ob_and_fos: 包含多个层次，时间，时效，站点的观测和预报数据
    :param used_coords: 拆分的维度
    :param sta_list: 最终返回的结果
    :return:
    '''

    if grd_list is None:
        grd_list = []
    grd_group = group_grd(grd, g=used_coords[0])
    if len(used_coords) >1:
        # 取出第一个coord
        for grd in grd_group:
            split_grd(grd,used_coords=used_coords[1:],grd_list = grd_list)
    else:
        for grd in grd_group:
            grd_list.append(grd)
    return grd_list


def group_grd(grd, g = None):
    if g == None:
        return [grd]
    else:
        ng = len(grd[g].values)
        grd_list = []
        for i in range(ng):
            if g =="level":
                grd1 = grd.isel(level = slice(i,i+1))
            elif g == "time":
                grd1 = grd.isel(time=slice(i, i+1))
            elif g == "dtime":
                grd1 = grd.isel(dtime=slice(i, i+1))
            elif g == "member":
                grd1 = grd.isel(member=slice(i, i+1))
            grd_list.append(grd1)
        return grd_list