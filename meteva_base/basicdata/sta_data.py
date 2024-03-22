# -*- coding:UTF-8 -*-
import copy
import numpy as np
import meteva_base
import pandas as pd

def sta_data(df,columns = None,
             # dtime_units="hour", data_source="", level_type="",
             # var_name="", var_cn_name="",
             # var_units="", valid_time=0, data_start_columns=6,
             reset_ids = True,
             units_attr      = '',#数据单位
             model_var_attr  = '',#补充模式/要素信息
             dtime_units_attr= 'hour',# hour/minite
             level_type_attr = 'isobaric',# isobaric/attitude
             time_type_attr  = 'UT',#UT/BT
             time_bounds_attr= [0,0],#数据起止时间
             ):
    '''
    sta_data() 对数据进行格式化成为固定格式
    :param df: dataframe的站点数据
    :param columns: 文件内包含的数据的列名
    :return: 包含‘level', 'time', 'dtime', 'id', 'lon', 'lat',  列的一个dataframe
    '''
    #提取dframe0 列名称
    if columns is None:
        columns = df.columns

    # 将列名变为小写
    columns_1 = []
    for column in columns:
        #column = column.lower()
        columns_1.append(column)
    columns = columns_1

    new_columns = ['level', 'time', 'dtime', 'id', 'lon', 'lat']

    # 提取数据列名称,扩展到新df的列名称中
    for column in columns:
        if column not in new_columns:
            new_columns.append(column)
    sta = copy.deepcopy(df)

    sta.columns = columns
    if "id" not in columns:
        sta["id"] = meteva_base.IV
    if reset_ids :reset_id(sta)
    sta.reset_index(inplace=True)

    # 更改列名
    sta = sta.reindex(columns = new_columns)
    #dframe1 = dframe1[new_columns]

    # 排序
    sta.sort_values(by=new_columns[:4],inplace=False)

    if len(sta.columns) == 6:
        sta["data0"] =0
    else:
        #for i in range(6,len(sta.columns)):
        #    sta.iloc[:,i] = (sta.values[:,i]).astype(np.float32)
        pass

    set_stadata_attrs(sta,units_attr = units_attr,model_var_attr = model_var_attr,dtime_units_attr = dtime_units_attr,
                      level_type_attr = level_type_attr,time_type_attr = time_type_attr,time_bounds_attr = time_bounds_attr,)
    sta=converse_type(sta)
    return sta

def set_stadata_attrs(sta, units_attr = None,model_var_attr = None,dtime_units_attr =None,
             level_type_attr = None,time_type_attr = None,
             time_bounds_attr = None):

    if sta.attrs is None: sta.attrs = {}
    # if dtime_units is not None:sta.attrs["dtime_units"] = dtime_units
    # if data_source is not None:sta.attrs["data_source"] = data_source
    # if level_type is not None: sta.attrs["data_type"] = level_type
    # if var_name is not None: sta.attrs["var_name"] = var_name
    # if var_cn_name is not None:sta.attrs["var_cn_name"] = var_cn_name
    # if var_units is not None:sta.attrs["var_units"] = var_units
    # if valid_time is not None:sta.attrs["valid_time"] = valid_time
    # if data_start_columns is not None:sta.attrs["data_start_columns"] = data_start_columns
    
    if units_attr is not None:sta.attrs["units"] = units_attr
    if model_var_attr is not None:sta.attrs["model"] = model_var_attr
    if dtime_units_attr is not None: sta.attrs["dtime_units"] =dtime_units_attr
    if level_type_attr is not None: sta.attrs["level_type"] = level_type_attr
    if time_type_attr is not None:sta.attrs["time_type"] = time_type_attr
    if time_bounds_attr is not None:sta.attrs["time_bounds"] = time_bounds_attr


def get_undim_data_names(sta):
    '''

    :param sta:
    :return:
    '''
    coor_columns = ['level', 'time', 'dtime', 'id', 'lon', 'lat']
    columns = sta.columns
    data_columns = []
    for column in columns:
        if column not in coor_columns:
            if column.find("dim_type")!=0:
                data_columns.append(column)
    return data_columns

def get_stadata_names(sta):
    '''
    get_data_names() 获取站点数据的要素名
    :param sta: 站点数据
    :return: 要素名列表
    '''
    #coor_columns = ['level', 'time', 'dtime', 'id', 'lon', 'lat']
    #columns = sta.columns
    #data_columns = []
    #for column in columns:
    #    if column not in coor_columns:
    #        data_columns.append(column)
    columns = sta.columns.values
    if "data_start_columns" not in sta.attrs.keys():
        sta.attrs["data_start_columns"] = 6
    data_start_column = sta.attrs["data_start_columns"]
    data_columns = columns[data_start_column:].tolist()
    return data_columns


def get_expanded_coord_names(sta):
    columns = sta.columns.values
    data_start_column = sta.attrs["data_start_columns"]
    ecc = columns[0:data_start_column].tolist()
    return ecc

def get_coord_names():
    '''

    :return: 站点数据基本信息列名['level', 'time', 'dtime', 'id', 'lon', 'lat']列表
    '''
    return ['level', 'time', 'dtime', 'id', 'lon', 'lat']

def set_stadata_names(sta,data_name_list):
    '''
    更改 要素名，和添加缺省列
    :param sta: 站点数据
    :param data_name: 站点数据 要素名
    :return: 更改要素名名后的站点数据
    '''
    if not isinstance(data_name_list,list):
        data_name_list = [data_name_list]
    #if isinstance(data_name_list,list):
    coor_columns = ['level', 'time', 'dtime', 'id', 'lon', 'lat']
    for data_name in data_name_list:
        coor_columns.append(data_name)
    sta.columns = coor_columns
    #else:
    #    print("输出名称设置不成功，数据名称列表参数需为list形式")
    return

def set_stadata_coords(sta,level = None,time = None,dtime = None,id = None,lat = None,lon = None):
    '''
    set_time_dtime_level_name 设置time_dtime_level 的值  并且设置要素名
    :param sta: 站点数据
    :param time: 起报时
    :param dtime: 时效
    :param level: 层次
    :param data_name: 要素名
    :return:  站点数据
    '''
    if time is not None:
        time1 = meteva_base.all_type_time_to_time64(time)
        sta.loc[:,'time'] = time1
        if len(sta.index) ==1:
            sta["time"] = sta["time"].astype(np.datetime64)
    if dtime is not None:
        sta.loc[:,'dtime'] = dtime
        dtime_type = str(sta["dtime"].dtype)
        if dtime_type.find("int") < 0:
            sta[["dtime"]] = sta[['dtime']].astype(int)
    if level is not None:
        sta.loc[:,'level'] = level
    if id is not None:
        sta.loc[:,"id"] = id
    if lat is not None:
        sta.loc[:,"lat"] = lat
    if lon is not None:
        sta.loc[:,"lon"] = lon



def reset_id(sta):
    '''
    输入的sta的站号中可能有些站号包含a-z,A-Z的字母，对此将这些字母转换为对应的ASCII数字，再将整个字符串格式的站号转换为数值形式
    返回sta站号为整型
    '''
    #print(sta)

    id_type = str(sta["id"].dtype)
    if id_type.find("int32") <0:
        values = sta['id'].values
        if id_type.find("int") >=0 or id_type.find("float") >=0:
            int_id = values.astype(np.int32)
            sta['id'] = int_id
        else:
            int_id = np.zeros(len(values))
            for i in range(len(values)):
                if isinstance(values[i],str):
                    strs = values[i]
                    if strs =="":
                        strs_int=999999
                    else:
                        strs_int = ""
                        for s in strs:
                            if s.isdigit():
                                strs_int += s
                            else:
                                strs_int += str(ord(s))
                    int_id[i] = int(strs_int)
                else:
                    int_id[i] = values[i]

            int_id = int_id.astype(np.int32)
            sta['id'] = int_id
    return

def get_attrs(sta,
              default_units='',
              default_model='',
              default_dtime_units='hour',
              default_level_type='isobaric',
              default_time_type='UT',
              default_time_bounds=[0,0]):
    if 'units' in sta.attrs:
        units=sta.attrs['units']
    else:
        units=default_units
        
    if 'model' in sta.attrs:
        model=sta.attrs['model']
    else:
        model=default_model
        
    if 'dtime_units' in sta.attrs:
        dtime_units=sta.attrs['dtime_units']
    else:
        dtime_units=default_dtime_units
        
    if 'level_type' in sta.attrs:
        level_type=sta.attrs['level_type']
    else:
        level_type=default_level_type
        
    if 'time_type' in sta.attrs:
        time_type=sta.attrs['time_type']
    else:
        time_type=default_time_type
        
    if 'time_bounds' in sta.attrs:
        time_bounds=sta.attrs['time_bounds']
    else:
        time_bounds=default_time_bounds
    
    return units,model,dtime_units,level_type,time_type,time_bounds

def converse_type(sta):
    sta['time']=pd.to_datetime(sta['time'])
    sta['level']=sta['level'].astype('float32')
    sta['dtime']=sta['dtime'].astype('int32')
    sta['id']=sta['id'].astype('int32')
    sta['lon']=sta['level'].astype('float32')
    sta['lat']=sta['level'].astype('float32')
    for column in sta:
        if column  not in ['id','level','time','dtime','lon','lat']:
            sta[column]=sta[column].astype('float32')
    return None
