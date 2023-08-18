import datetime
import numpy as np
import re

#所有类型的时间转换为time64
def all_type_time_to_time64(time0):
    if isinstance(time0,np.datetime64):
        return time0
    elif isinstance(time0,datetime.datetime):
        return np.datetime64(time0)
    elif type(time0) == str:
        return str_to_time64(time0)
    elif isinstance(time0,int):
        time1 = datetime.datetime.utcfromtimestamp(time0 / 1000000000)
        np.datetime64(time1)
        return np.datetime64(time1)
    else:
        print("时间类型不识别")
        return None

def all_type_time_to_datetime(time0):
    if isinstance(time0,int):
        time1 = datetime.datetime.utcfromtimestamp(time0 / 1000000000)
        return time1
    time64 = all_type_time_to_time64(time0)
    time1 = time64.astype(datetime.datetime)
    if isinstance(time1,int):
        time1 = datetime.datetime.utcfromtimestamp(time1/1000000000)
    return time1

def all_type_time_to_str(time0):
    time1 = all_type_time_to_time64(time0)
    return time_to_str(time1)


#所有的timedelta类型的数据转为timedelta64类型的时间格式
def all_type_timedelta_to_timedelta64(timedelta0):
    if isinstance(timedelta0,np.timedelta64):
        return timedelta0
    elif isinstance(timedelta0,datetime.timedelta):
        return np.timedelta64(timedelta0)
    elif type(timedelta0) == str:
        timedelta1 = str_to_timedelta(timedelta0)
        return np.timedelta64(timedelta1)
    else:
        print("时效类型不识别")
        return None

def all_type_timedelta_to_timedelta(timedelta0):
    if isinstance(timedelta0,datetime.timedelta):
        return timedelta0
    elif isinstance(timedelta0,np.timedelta64):
        seconds = int(timedelta0 / np.timedelta64(1, 's'))
        timedelta1 = datetime.timedelta(seconds = seconds)
        return timedelta1
    elif type(timedelta0) == str:
        timedelta1 = str_to_timedelta(timedelta0)
        return timedelta1
    else:
        print("时效类型不识别")
        return None

#str类型的时间转换为timedelta64类型的时间
def str_to_timedelta(timedalta_str):
    num_str = ''.join([x for x in timedalta_str if x.isdigit()])
    num = int(num_str)
    # 提取出dtime_type类型
    TIME_type = re.findall(r"\D+", timedalta_str)[0].lower()
    if TIME_type == 'h':
        return datetime.timedelta(hours=num)
    elif TIME_type == 'd':
        return datetime.timedelta(days=num)
    elif TIME_type == 'm':
        return datetime.timedelta(minutes=num)
    else:
        print("输入的时效格式不识别")
        return None

#str类型的时间转换为time64类型的时间
def str_to_time64(time_str):
    str1 = ''.join([x for x in time_str if x.isdigit()])
    # 用户输入2019041910十位字符，后面补全加0000，为14位统一处理
    if len(str1) == 4:
        str1 += "0101000000"
    elif len(str1) == 6:
        str1 +="01000000"
    elif len(str1) == 8:
        str1 +="000000"
    elif len(str1) == 10:
        str1 +="0000"
    elif len(str1) == 12:
        str1 +="00"
    elif len(str1) == 14:
        str1 = time_str
    else:
        print("输入日期格式不识别，请检查！")

    # 统一将日期变为datetime类型
    time = datetime.datetime.strptime(str1, '%Y%m%d%H%M%S')
    time64 = np.datetime64(time)
    return time64



#datetime64类型的数据转换为str类型
def time_to_str(time):
    if isinstance(time,np.datetime64):
        str1 = str(time).replace("-", "").replace(" ", "").replace(":", "").replace("T", "")[0:14]
    else:
        str1 = time.strftime("%Y%m%d%H%M%S")
    return str1


#字符转换为datetime
def str_to_time(str0):
    num = ''.join([x for x in str0 if x.isdigit()])
    # 用户输入2019041910十位字符，后面补全加0000，为14位统一处理
    if len(num) == 4:
        num += "0101000000"
    elif len(num) == 6:
        num += "01000000"
    elif len(num) == 8:
        num += "000000"
    elif len(num) == 10:
        num += "0000"
    elif len(num) == 12:
        num += "00"
    elif len(num) > 12:
        num = num[0:12]
    else:
        print("输入日期有误，请检查！")
    # 统一将日期变为datetime类型
    return datetime.datetime.strptime(num, '%Y%m%d%H%M%S')


def get_dtime_of_path(path_model,path):
    ttt_index = path_model.find("TTT")
    if (ttt_index >= 0):
        ttt = int(path[ttt_index:ttt_index + 3])
    else:
        ttt = 0
    return ttt
def get_time_of_path(path_model,path):
    yy_index = path_model.find("YYYY")
    if  yy_index < 0:
        yy_index = path_model.find("YY")
        if(yy_index <0):
            yy = 2000
        else:
            yy = int(path[yy_index: yy_index + 2]) + 2000
    else:
        yy = int(path[yy_index: yy_index+4])

    mm_index = path_model.find("MM")
    if(mm_index >=0):
        mm = int(path[mm_index:mm_index+2])
    else:
        mm = 1

    dd_index = path_model.find("DD")
    if(dd_index>=0):
        dd = int(path[dd_index:dd_index + 2])
    else:
        dd = 1
    hh_index = path_model.find("HH")
    if(hh_index>=0):
        hh = int(path[hh_index:hh_index + 2])
    else:
        hh = 0
    ff_index = path_model.find("FF")
    if(ff_index>=0):
        ff = int(path[ff_index:ff_index + 2])
    else:
        ff = 0
    ss_index = path_model.find("SS")
    if(ss_index>=0):
        ss = int(path[ss_index:ss_index + 2])
    else:
        ss = 0
    return datetime.datetime(yy,mm,dd,hh,ff,ss)

#### 时间相关操作函数
def _get_date_from_str(input,get_datetime64=False):
    '''
    输入str/datetime64/datetime时，输出datetime或np.datetime（通过get_datetime64参数控制）
    '''
    if isinstance(input, int):##输入为数字时
        input = ''.join([x for x in gtime[i] if x.isdigit()])
    if type(input) == str:## 输入为字符串
        num = ''.join([x for x in input if x.isdigit()])
        # 用户输入2019041910十位字符，后面补全加0000，为14位统一处理
        if len(num) == 4:
            num += "0101000000"
        elif len(num) == 6:
            num +="01000000"
        elif len(num) == 8:
            num +="000000"
        elif len(num) == 10:
            num +="0000"
        elif len(num) == 12:
            num +="00"
        else:
            print("输入日期有误，请检查！")
        # 统一将日期变为datetime类型
        stime = datetime.datetime.strptime(num, '%Y%m%d%H%M%S')#返回datetime
        if get_datetime64 :
            stime = np.datetime64(stime)#返回datetime64                
    elif isinstance(input,np.datetime64):## 输入为datetime64
        if get_datetime64:
            stime = input
        else:
            stime = input.astype(datetime.datetime)
            print("here",stime)
            if isinstance(stime, int):
                stime = datetime.datetime.utcfromtimestamp(stime / 1000000000)                
    elif isinstance(input, datetime.datetime):## 输入为datetime.datetime
        if get_datetime64:
            stime = np.datetime64(input)#返回datetime64
        else:
            stime = input
    return(stime)

def get_date_list_pd(gtime=['2020060700', '2020060712', 12], delta='H'):
    """
    ## 输入起始、终止、间隔时间，获取多时间列表
    gtime参数（start_date_str, end_date_str, hour_intervals）
    """
    num1 =[]
    if type(gtime[0]) == str:
        for i in range (0,2):
            num = ''.join([x for x in gtime[i] if x.isdigit()])
            num1.append(_get_date_from_str(num, get_datetime64=True))
        stime = num1[0]
        etime = num1[1]
    else:
        stime = _get_date_from_str(gtime[0])
        etime = _get_date_from_str(gtime[1])
    times = pd.date_range(stime, etime, freq=str(gtime[2])+delta)
    return(times.to_pydatetime())#返回datetime类型数组


def get_groupby_date_list(date_list, by='month'):
    """ 
    para:
        date_list   : 时间列表 List[datetime.datetime]
        by          : 分组方式，支持逐年'year'/逐月'month'/逐日'day'
    return：
        分组后的二维时间列表 List[List[datetime.datetime]]
        dim0为分组数，如逐年、逐月、逐日分组, 365天逐日分组时，len(dim0)=365
        dim1为具体每组的时间列表，如逐日分组时，列表中为同一天的具体时间datetime,  

    """
    time_index = pd.DatetimeIndex(date_list)
    time_index = time_index.sort_values(ascending=True)
    print(by)
    if by == 'year':
        temp = time_index.year*10000
    elif by == 'month':
        temp = time_index.year*10000 + time_index.month*100
    elif by == 'day':
        temp = time_index.year*10000 + time_index.month*100 + time_index.day
    else:
        raise ValueError('by参数应为： 逐年year/逐月month/逐日day， 请检查！！')
    time_pd = pd.DataFrame(temp, index=time_index,columns=['ymd'])
    time_pd_g = time_pd.groupby(by='ymd')
    time_monthly = []
    for f in time_pd_g:
        temp = f[1].index.to_pydatetime()
        time_monthly.append(temp)
    return time_monthly
