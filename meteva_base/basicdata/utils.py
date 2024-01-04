import numpy as np
import pandas as pd
import datetime
import re

import meteva_base

def get_time_input_single(gtime): 
    time = meteva_base.all_type_time_to_time64(gtime[0])
    stime = time
    etime = time
    dtime_int = 1
    dtime_type = "h"
    dtimedelta = np.timedelta64(dtime_int, dtime_type)
    times = pd.date_range(stime, etime, freq=str(dtime_int)+dtime_type ).to_pydatetime()
    return times

def get_time_input_three(gtime):  
    num1 =[]
    ## stime etime
    if type(gtime[0]) == str:
        for i in range (0,2):
            num = ''.join([x for x in gtime[i] if x.isdigit()])
            #用户输入2019041910十位字符，后面补全加0000，为14位统一处理
            if len(num) == 4:
                num1.append(num + "0101000000")
            elif len(num) == 6:
                num1.append(num + "01000000")
            elif len(num) == 8:
                num1.append(num + "000000")
            elif len(num) == 10:
                num1.append(num + "0000")
            elif len(num) == 12:
                num1.append(num + "00")
            elif len(num) == 14:
                num1.append(num)
            else:
                print("输入日期有误，请检查！")
            #统一将日期变为datetime类型
        #print(num1)
        stime = datetime.datetime.strptime(num1[0], '%Y%m%d%H%M%S')
        etime = datetime.datetime.strptime(num1[1], '%Y%m%d%H%M%S')
        stime = np.datetime64(stime)
        etime = np.datetime64(etime)
    elif isinstance(gtime[0],np.datetime64):
        stime = gtime[0].astype(datetime.datetime)
        etime = gtime[1].astype(datetime.datetime)
        if isinstance(stime, int):
            stime = datetime.datetime.utcfromtimestamp(stime / 1000000000)
            etime = datetime.datetime.utcfromtimestamp(etime / 1000000000)
        stime = stime
        etime = etime
    else:
        stime = gtime[0]
        etime = gtime[1]
    ## dtime
    if type(gtime[2]) == str:
        dtime_int = re.findall(r"\d+", gtime[2])[0]
        dtime_type = re.findall(r"\D+", gtime[2])[0]
        if dtime_type == 'h':
            dtime_type ="h"
            dtimedelta = np.timedelta64(dtime_int,'h')
        elif dtime_type == 'd':
            dtime_type ="D"
            dtimedelta = np.timedelta64(dtime_int, 'D')
        elif dtime_type == 'm':
            dtime_type ="m"
            dtimedelta = np.timedelta64(dtime_int, 'm')
    elif isinstance(gtime[2],np.timedelta64):
        seconds = int(gtime[2] / np.timedelta64(1, 's'))
        if seconds % 3600 == 0:
            dtime_type = "h"
            dtime_int = int(seconds / 3600)
        else:
            dtime_type = "m"
            dtime_int = int(seconds / 60)
    else:
        dtimedelta = gtime[2]
        seconds = gtime[2].total_seconds()
        if seconds % 3600 == 0:
            dtime_type = "h"
            dtime_int = int(seconds/3600)
        else:
            dtime_type = "m"
            dtime_int = int(seconds / 60)
    times = pd.date_range(stime, etime, freq=str(dtime_int)+dtime_type ).to_pydatetime()
    return times


