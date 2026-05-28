# Meteva Base GridData 数据类型说明文档

## 1. 基本定义

**GridData** 是基于 `xarray.DataArray` 的多维格点数据格式，专门用于存储气象网格数据。

- **基础类型**: `xarray.DataArray`
- **固定维度顺序**: `[member, level, time, dtime, lat, lon]`
- **数据类型**: 默认为 `np.float32`

---

## 2. 六个维度定义

| 维度 | 说明 | 坐标值类型 | 默认值 |
|------|------|-----------|--------|
| `member` | 成员/要素名称 | `str` | `['data0']` |
| `level` | 层次/高度 | `np.float32` | `[0]` |
| `time` | 起报时间 | `np.datetime64` | - |
| `dtime` | 预报时效 | `np.int32` | `[0]` |
| `lat` | 纬度 | `np.float64` | - |
| `lon` | 经度 | `np.float64` | - |

---

## 3. 六个属性定义

| 属性 | 说明 | 默认值 |
|------|------|--------|
| `units` | 数据单位 | `''` |
| `model_var` | 模式/要素信息 | `''` |
| `dtime_units` | 预报时效单位 (`hour`/`minute`) | `'hour'` |
| `level_type` | 层次类型 (`isobaric`/`attitude`) | `'isobaric'` |
| `time_type` | 时间类型 (`UT`/`BT`) | `'UT'` |
| `time_bounds` | 数据起止时间（如24h降水为 `[-24,0]`） | `[0,0]` |

---

## 4. 核心功能接口

### 4.1 创建/转换

| 函数 | 功能 | 位置 |
|------|------|------|
| `grid_data(grid, data=None)` | 根据 `grid` 对象创建标准 `griddata` | `grid_data.py` |
| `xarray_to_griddata(xr0, value_name=None, member_dim=None, level_dim=None, time_dim=None, dtime_dim=None, lat_dim=None, lon_dim=None)` | 将外部 xarray 数据转换为标准格式 | `grid_data.py` |
| `DataArray_to_grd(dataArray, data_name='data0', member=None, level=None, time=None, dtime=None, lat=None, lon=None)` | 将 DataArray 转换为标准 griddata | `grid_data.py` |

### 4.2 坐标操作

| 函数 | 功能 | 位置 |
|------|------|------|
| `set_griddata_coords(grd, name=None, gtime=None, dtime_list=None, level_list=None, member_list=None)` | 设置网格坐标（member/level/time/dtime） | `grid_data.py` |
| `set_griddata_coords_dtype(da, member_type=str, level_type=np.float32, dtime_type=np.int32, time_type=np.datetime64, lat_type=np.float64, lon_type=np.float64, data_type=np.float32)` | 统一各坐标数据类型 | `grid_data.py` |

### 4.3 属性操作

| 函数 | 功能 | 位置 |
|------|------|------|
| `set_griddata_attrs(grd, units=None, model_var=None, dtime_units=None, level_type=None, time_type=None, time_bounds=None, is_default=False, default_attr={...})` | 设置网格数据属性（6个属性） | `grid_data.py` |
| `get_griddata_attrs(da, default_units='', default_model='', default_dtime_units='hour', default_level_type='isobaric', default_time_type='UT', default_time_bounds=[0,0])` | 获取网格数据属性 | `grid_data.py` |
| `set_griddata_attrs_same(grd, grd0)` | 从 grd0 复制属性到 grd | `grid_data.py` |

### 4.4 数据规范化

| 函数 | 功能 | 位置 |
|------|------|------|
| `reset(grd)` | **就地重置**：<br>1. 纬度/经度若递减则翻转并同步翻转数据<br>2. 强制维度顺序为 `[member, level, time, dtime, lat, lon]` | `grid_data.py` |

### 4.5 辅助工具

| 函数 | 功能 | 位置 |
|------|------|------|
| `get_grid_of_data(grid_data0)` | 从 griddata 提取对应的 `grid` 描述对象 | `grid.py` |
| `get_true_value(value)` | 推断浮点数的真实有效小数位数 | `grid.py` |
| `reset_grid(grid0)` | 重置 grid 的坐标间隔为正数 | `grid.py` |

---

## 5. Grid 类（网格描述）

`grid` 类用于描述网格的空间/时间范围，是创建 `griddata` 的基础。

### 5.1 构造方法

```python
g = grid(
    glon,           # 东西向网格信息，[最小, 最大, 间隔]
    glat,           # 南北向网格信息，[最小, 最大, 间隔]
    gtime=None,     # 起报时间信息
    dtime_list=None,# 时效列表，默认为[0]
    level_list=None,# 层次列表，默认为[0]
    member_list=None,   # 成员列表，默认为['data0']
    units_attr='',      # 数据单位
    model_var_attr='',  # 模式/要素信息
    dtime_units_attr='hour',    # 时效单位
    level_type_attr='isobaric', # 层次类型
    time_type_attr='UT',        # 时间类型
    time_bounds_attr=[0,0]      # 数据起止时间
)
```

### 5.2 坐标属性

| 属性 | 说明 |
|------|------|
| `members` | 成员列表 |
| `levels` | 层次列表 |
| `gtime` | 起报时间序列（list[datetime]） |
| `dtimes` | 预报时效列表 |
| `slon` | 起始经度 |
| `elon` | 结束经度 |
| `dlon` | 经度间隔 |
| `nlon` | 经度格点数 |
| `slat` | 起始纬度 |
| `elat` | 结束纬度 |
| `dlat` | 纬度间隔 |
| `nlat` | 纬度格点数 |
| `glon` | 经度范围 `[slon, elon, dlon]` |
| `glat` | 纬度范围 `[slat, elat, dlat]` |
| `stime_str` | 起始时间字符串（yyMMddHHmm格式） |

### 5.3 属性

与 griddata 共享 6 个属性：`units`, `model_var`, `dtime_units`, `level_type`, `time_type`, `time_bounds`

### 5.4 方法

| 方法 | 功能 |
|------|------|
| `copy()` | 深拷贝 |
| `reset()` | 重置坐标间隔为正数 |
| `__str__()` | 格式化输出网格信息 |

---

## 6. 使用示例

### 6.1 创建 Grid 对象

```python
from meteva_base.basicdata.grid import grid

# 定义网格范围
glon = [110.0, 120.0, 1.0]  # 经度：110-120度，间隔1度
glat = [20.0, 30.0, 1.0]    # 纬度：20-30度，间隔1度
gtime = ["2024010100"]      # 起报时间
dtime_list = [0, 6, 12, 24] # 预报时效
level_list = [850, 500]     # 层次
member_list = ['ECMWF', 'GFS']

# 创建 grid
g = grid(glon, glat, gtime, dtime_list, level_list, member_list,
         units_attr='hPa', model_var_attr='HGT')
```

### 6.2 创建 GridData

```python
from meteva_base.basicdata.grid_data import grid_data
import numpy as np

# 基于 grid 创建 griddata（自动创建全零数组）
grd = grid_data(g)

# 或使用自定义数据
data = np.random.randn(2, 2, 1, 4, 11, 11)  # 维度: [member, level, time, dtime, lat, lon]
grd = grid_data(g, data)
```

### 6.3 坐标和属性操作

```python
from meteva_base.basicdata.grid_data import (
    set_griddata_coords, set_griddata_attrs, reset
)

# 修改坐标
set_griddata_coords(grd, member_list=['MODEL_A', 'MODEL_B'])

# 修改属性
set_griddata_attrs(grd, units='mm', dtime_units='hour')

# 规范化数据（翻转递减坐标，统一维度顺序）
reset(grd)
```

### 6.4 从外部数据转换

```python
from meteva_base.basicdata.grid_data import xarray_to_griddata
import xarray as xr

# 假设有一个外部 xarray DataArray
da = xr.DataArray(...)

# 转换为标准 griddata
grd = xarray_to_griddata(
    da,
    value_name='temperature',
    lat_dim='latitude',
    lon_dim='longitude'
)
```

---

## 7. 相关文件位置

- **Grid 类**: `meteva_base/basicdata/grid.py`
- **GridData 相关函数**: `meteva_base/basicdata/grid_data.py`

---

*文档生成时间: 2026-03-10*
