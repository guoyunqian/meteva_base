# -*- coding: utf-8 -*-
"""
Created on Wed Jan 24 15:27:27 2024

@author: cheny
"""
import pandas as pd
import h5py
import netCDF4
import meteva_base as meb


# file_path=r'D:\Desktop\obs_all.h5'
file_path='a.csv'

data=meb.read_stadata_from_csv('a.csv')


data.attrs['units']='test'

print(data.attrs)

meb.write_stadata_to_hdf(data,'b.h5')
meb.write_stadata_to_csv(data,'b.csv')

z=pd.read_csv('b.csv')
x=meb.read_stadata_from_hdf('b.h5')
y=meb.read_stadata_from_csv('b.csv')

print(x.attrs)
print(y.attrs)





