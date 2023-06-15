import numpy as np
import math
import meteva

def put_uv_into_wind(u,v):
    grid0 = meteva.base.get_grid_of_data(u)
    grid1 = meteva.base.grid(grid0.glon,grid0.glat,grid0.gtime,
                                              dtime_list= grid0.dtimes,level_list=grid0.levels,member_list=["u","v"])
    wind = meteva.base.grid_data(grid1)
    wind.name = "wind"
    wind.values[0, :, :, :, :, :] = u.values[0, :, :, :, :, :]
    wind.values[1, :, :, :, :, :] = v.values[0, :, :, :, :, :]
    return wind

def get_wind_from_speed_angle(speed,angle):

    speed_v = speed.values.squeeze()
    angle_v = angle.values.squeeze()

    grid0 = meteva.base.get_grid_of_data(speed)
    grid1 = meteva.base.grid(grid0.glon,grid0.glat,grid0.gtime,
                                              dtime_list=grid0.dtimes,level_list=grid0.levels,member_list=["u","v"])
    wind = meteva.base.grid_data(grid1)
    wind.name = "wind"
    wind.values[0, :, :, :, :, :] = speed_v[:, :] * np.cos(angle_v[:, :] * math.pi /180)
    wind.values[1, :, :, :, :, :] = speed_v[:, :] * np.sin(angle_v[:, :] * math.pi /180)
    return wind
