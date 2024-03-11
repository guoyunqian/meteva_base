import math
import datetime
import re
from copy import deepcopy
import numpy as np
import pandas as pd

import meteva_base


class grid:
    '''
        定义一个格点的类grid，来存储网格的范围包括（起始经纬度、格距、起止时间，时间间隔，起止时效，时效间隔，层次列表，数据成员）
        约定坐标顺序为: member, time,ddtime, level, lat,lon
    '''
    def __init__(self,glon, glat, gtime=None, dtime_list=None, level_list=None, member_list = None,
                        units_attr      = '',#数据单位
                        model_var_attr  = '',#补充模式/要素信息
                        dtime_units_attr= 'hour',# hour/minite
                        level_type_attr = 'isobaric',# isobaric/attitude
                        time_type_attr  = 'UT',#UT/BT
                        time_bounds_attr= [0,0],#数据起止时间
                        ):
        """
        ## 格点坐标设置
        param glon : 东西向网格信息，list列表，[最小，最大，间隔]
        param glat : 南北向网格信息，list列表，[最小，最大，间隔]
        param gtime: 起报时间网格信息：若gtime只包含1个元 素，其内容为datetime变量，或者常用字符形式时间，例如"2019123108"、"2019-12-31:08"或"19年12月31日08时"等方式都能兼容。
                    若gtime包含三个元素，其内容为[起始时间,结束时间,时间间隔], 其中时间格式可以是datetime变量或者字符串形式，时间间隔为字符串，例如"12h"代表12小时，"30m"代表30分钟。
                    若为列表且非上述要素，则是直接的datetime列表
        param dtime_list: 时效信息，list列表，其元素dtime为整数, 默认为[0]
        param level_list: 层次名称信息，list列表，默认为[0]
        param member_list:成员名称信息，list列表，默认为['data0']
        ## 格点属性设置
        param units_attr      : 数据单位, 默认为None,
        param model_var_attr  : 补充模式/要素信息,默认为None
        param dtime_units_attr: 预报时效单位，hour/minite,默认为'hour' 
        param level_type_attr : 层次单位，isobaric/attitude，默认为'isobaric'等压面
        param time_type_attr  : 起报时间类型，UT（世界时间）/BT(北京时间)，默认'UT'
        time_bounds_attr      : 数据起止时间，如24h降水为[-24,0], 默认[0,0]
        
        """
        #提取成员维度信息
        if(member_list is None):
            self.members =['data0']
        else:
            self.members = member_list
        ############################################################################
        #提取层次维度信息
        if(level_list is None):
            self.levels =[0]
        else:
            self.levels = level_list
        ############################################################################
        #提取时间维度信息
        # try:
        if gtime is None:
            self.stime = np.datetime64('2020-01-01T00:00:00.000000')
            self.etime = np.datetime64('2020-01-01T00:00:00.000000')
            self.dtime_int = 1
            self.dtime_type = "h"
            self.times = pd.date_range(self.stime, self.etime, freq=str(self.dtime_int)+self.dtime_type ).to_pydatetime()#[datetime]
        else:
            try:
                _ = len(gtime)
            except:
                gtime = [gtime]
            if len(gtime) == 1:
                self.times = meteva_base.basicdata.utils.get_time_input_single(gtime)

            elif len(gtime) ==3 and isinstance(gtime[2],str) and len(gtime[2])<=5:
                self.times = meteva_base.basicdata.utils.get_time_input_three(gtime)

            else:
                if isinstance(gtime[0], datetime.datetime):
                    self.times = gtime
                else:
                    self.times = [meteva_base.all_type_time_to_datetime(dt) for dt in gtime]#[datetime]
        self.stime_str = self.times[0].strftime("%y%m%d%H%M")
        # except Exception as err:
            # print('gtime ERROR: ',err)
        ############################################################################
        #提取预报时效维度信息
        if dtime_list is None:
            self.dtimes = [0]
        else:
            self.dtimes = dtime_list
        ############################################################################
        #提取经度信息

        self.slon = get_true_value(glon[0])
        self.elon = get_true_value(glon[1])
        self.dlon = get_true_value(glon[2])
        nlon = 1 + (self.elon - self.slon) / self.dlon
        error = abs(round(nlon) - nlon)/nlon
        if (error > 0.01):
            self.nlon = int(math.ceil(nlon))
        else:
            self.nlon = int(round(nlon))

        self.elon = get_true_value(self.slon + (nlon - 1) * self.dlon)
        self.glon = [self.slon,self.elon,self.dlon]
        ############################################################################
        #提取纬度信息
        self.slat = get_true_value(glat[0])
        self.elat = get_true_value(glat[1])
        self.dlat = get_true_value(glat[2])
        nlat = 1 + (self.elat - self.slat) / self.dlat
        error = abs(round(nlat) - nlat)/nlat
        if (error > 0.01):
            self.nlat = int(math.ceil(nlat))
        else:
            self.nlat = int(round(nlat))
        self.elat = get_true_value(self.slat + (nlat - 1) * self.dlat)
        self.glat = [self.slat,self.elat,self.dlat]
        ## 格点数据属性设置(6属性)
        self.units       = units_attr
        self.model_var   = model_var_attr
        self.dtime_units = dtime_units_attr
        self.level_type  = level_type_attr
        self.time_type   = time_type_attr
        self.time_bounds = time_bounds_attr
        return




    #对原有的格点数据进行一次深拷贝，不改变原有的值和结构。
    def copy(self):
        return deepcopy(self)

    #reset的作用是把网格的坐标间隔统一为正数。
    def reset(self):
        if (self.dlon > 0 and self.dlat > 0):
            pass
        if (self.dlat < 0):
            tran = self.slat
            self.slat = self.elat
            self.elat = tran
            self.dlat = abs(self.dlat)
        if (self.dlon < 0):
            tran = self.slon
            self.slon = self.elon
            self.elon = tran
            self.dlon = abs(self.dlon)
        return


    def __str__(self):
        '''
        重置系统自动的函数，在print(grid) 的时候可以很整齐的看到所有信息
        :return:  string
        '''
        grid_str = ""
        grid_str += "## grid_coordinates ##" + "\n"
        grid_str += "members:" + str(self.members) +"\n"
        grid_str += "levels:" + str(self.levels) + "\n"
        # grid_str += "gtime:" + str([self.stime_str,self.etime_str,self.dtime_str]) + "\n"
        grid_str += "gtime:" + str(self.times)  +"\n"
        grid_str += "dtimes:" + str(self.dtimes)  +"\n"
        grid_str += "glon:" + str(self.glon) + "\n"
        grid_str += "glat:" + str(self.glat) + "\n"
        grid_str += "## grid_attributes ##" +  "\n"
        grid_str += "units:" + str(self.units) + "\n"
        grid_str += "model_var:" + str(self.model_var) + "\n"
        grid_str += "dtime_units:" + str(self.dtime_units) + "\n"
        grid_str += "level_type:" + str(self.level_type) + "\n"
        grid_str += "time_type:" + str(self.time_type) + "\n"
        grid_str += "time_bounds:" + str(self.time_bounds) + "\n"
        return grid_str

def get_true_value(value):
    dlon2 = round(value, 2)
    dlon3 = round(value, 3)
    dlon4 = round(value, 4)
    dlon5 = round(value, 5)
    if dlon2 == dlon3 and dlon3 == dlon4:
        return dlon3
    elif dlon3 == dlon4 and dlon5 == dlon4:
        return dlon3
    else:
        return value


def get_grid_of_data(grid_data0):
    '''
     获取grid的数据values值
    :param grid_data0:初始化之后的网格数据
    :return:返回grid数据。
    '''
    member_list = grid_data0['member'].values
    level_list = grid_data0['level'].values
    times = grid_data0['time'].values
    gtime = times

    gdt = grid_data0['dtime'].values.tolist()
    attrs_name = list(grid_data0.attrs)


    lons = grid_data0['lon'].values
    dlon = get_true_value(lons[1] - lons[0])
    glon = [get_true_value(lons[0]), get_true_value(lons[-1]), dlon]
    lats = grid_data0['lat'].values
    dlat = get_true_value(lats[1] - lats[0])
    glat = [get_true_value(lats[0]), get_true_value(lats[-1]), dlat]

    units_attr       = grid_data0.attrs['units']
    model_var_attr   = grid_data0.attrs['model']
    dtime_units_attr = grid_data0.attrs['dtime_units']
    level_type_attr  = grid_data0.attrs['level_type']
    time_type_attr   = grid_data0.attrs['time_type']
    time_bounds_attr = grid_data0.attrs['time_bounds']

    grid01 = grid(glon, glat, gtime, gdt, level_list, member_list,
                        units_attr      = units_attr,
                        model_var_attr  = model_var_attr,
                        dtime_units_attr= dtime_units_attr,
                        level_type_attr = level_type_attr,
                        time_type_attr  = time_type_attr,
                        time_bounds_attr= time_bounds_attr)
    return grid01


def reset_grid(grid0):
    if grid0.dlat <0:
        grid0.dlat = - grid0.dlat
        tran = grid0.slat
        grid0.slat = grid0.elat
        grid0.elat = tran
    if grid0.dlon <0:
        grid0.dlon = - grid0.dlon
        tran = grid0.slon
        grid0.slon = grid0.elon
        grid0.elon = tran
    return

