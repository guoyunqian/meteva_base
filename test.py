# -*- coding: utf-8 -*-
"""
Created on Fri Jan 19 10:00:52 2024

@author: cheny
"""

import meteva_base as meb
import pandas as pd
import h5py
import netCDF4

from tables import *
grid0 = meb.grid([0,359.9,0.1],[90,-90,-0.1],
                  gtime=["2023120100"],
                  dtime_list = [24],
                  level_list = [0],
                  member_list = ["ECMWF"],
                  units_attr='m/s',
                  model_var_attr='test',
                  dtime_units_attr='hours',
                  # level_type_attr='altitude',
                  time_type_attr = 'test',
                  time_bounds_attr=[0,5]
                  )
# print(grid0)

# grd = meb.grid_data(grid0)  #根据网格信息生成网格数据，网格值都为0


# # print(grd)
# grid1 = meb.basicdata.get_grid_of_data(grd)
# print(grid1)
# meb.write_griddata_to_nc(grd,save_path=r'D:\Desktop\meb_test.nc')

# data=meb.read_griddata_from_nc(r'D:\Desktop\meb_test.nc')

# print(grid0)

# data2=meb.read_griddata_from_micaps4(r'D:\Desktop\2023112712.240')

# print(data2)

# meb.write_griddata_to_nc(data2,r'D:\Desktop\meb_test.nc')
# meb.write_griddata_to_micaps4(data2,r'D:\Desktop\2023120100.240')
data3=meb.read_griddata_from_nc(r'D:\Desktop\20240108.nc')
# data4=meb.read_griddata_from_micaps4(r'D:\Desktop\2023120100.240')
# print(data3)
# print(data2)
print(data3)

# data4=pd.read_hdf(r'D:\Desktop\nimm\nimm\nimm\fmm\resources\sta_info.h5')
# print(data2)

# #HDF5的读取：
# file_path=r'D:\Desktop\nimm\nimm\nimm\fmm\resources\sta_info.h5'   #打开h5文件
# with h5py.File(file_path, 'a') as file:
#     # 获取文件头信息
#     file.attrs['units']='m/s'
    
    
#     header_info = file.attrs.items()
#     print("HDF5 File Header Information:")
#     for key, value in header_info:
#         print(f"{key}: {value}")
# file.close()
#                          #可以查看所有的主键
# # a = f['df']                    #取出主键为data的所有的键值
# # f.close()
