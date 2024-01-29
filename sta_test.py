# -*- coding: utf-8 -*-
"""
Created on Wed Jan 24 15:27:27 2024

@author: cheny
"""
import pandas as pd
import h5py
import netCDF4
from meteva_base.basicdata import sta_data
import meteva_base as meb


# file_path=r'D:\Desktop\obs_all.h5'
file_path='a.h5'
# # # file_out_path=r'D:\Desktop\obs_all_out.h5'   #打开h5文件
# with h5py.File(file_path, 'a') as file:
#     # 获取文件头信息
#     # file.attrs['units']='m/s'
    
    
#     header_info = file.attrs.items()
#     print("HDF5 File Header Information:")
#     for key, value in header_info:
#         print(f"{key}: {value}")
# file.close()

# df=pd.read_hdf(file_path)
# meb.write_stadata_to_hdf(df)

data=meb.read_stadata_from_hdf(file_path)
print(data.attrs)
# # df.attrs['units']='m/s'


# a=pd.read_hdf('a.h5')

# print(a.attrs)
# print(df.attrs)

# sta=sta_data(df)
# print(df.attrs)
# print(type(sta))
# print(sta.attrs)

# data.to_hdf(file_out_path,key='data')