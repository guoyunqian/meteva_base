# NIMM 网格 NC v1.0 接口说明

本分支为 `meteva_base` 增加 NIMM 网格 NC v1.0 的内存模型、标准化校验和读写支持。正式规范要求唯一数据变量为：

```text
data0(member, level, time, dtime, lat, lon)
```

内存中的 `data0` 为 `float32`，缺测值为 `NaN`。`time`、`lat`、`lon` 是必需坐标；仅 `member=['0']`、`level=[0.0]`、`dtime=[0]` 可在缺失时补默认值。

## 主要接口

### 标准化与校验

```python
import meteva_base as meb

normalized = meb.standardize_griddata_nimm(source, strict=True)
report = meb.validate_griddata_nimm(normalized)
assert report["valid"]
```

标准化会完成固定六维转置、坐标类型转换、经度归一化到 `[0, 360)`、坐标与数据同步排序、数据转为 `float32`，并将历史小写属性映射为以下规范属性：

- `SHORT_NAME`
- `UNITS`
- `DTIME_UNITS`
- `LEVEL_TYPE`
- `TIME_TYPE`
- `TIME_BOUNDS`

显式的规范大写属性优先于历史别名。`model` 和 `model_var` 的旧含义同时混合了数据来源和要素语义，因此读取时不会自动猜测；调用 `set_griddata_attrs(..., model_var=...)` 时仅为兼容旧调用，将其视为 `SHORT_NAME` 的别名。

### 读取

```python
grd = meb.read_griddata_from_nc(
    "input.nc",
    nimm_standard=True,
    nimm_strict=True,
    raise_on_error=True,
)
```

默认执行 CF 时间、缩放和缺测解码，并返回 NIMM 六维 `float32` DataArray。文件含多个数据变量时必须通过 `value_name` 指定；源文件缺少 `time`、`lat` 或 `lon` 时严格模式报错。

`raise_on_error=False` 保留旧接口的失败行为（打印异常并返回 `None`）；生产流程建议设为 `True`。

### 写出

```python
meb.write_griddata_to_nc(
    grd,
    "output.nc",
    storage_type="float32",
    global_attrs={"SOURCE": "example", "PRODUCT_TYPE": "forecast"},
    roundtrip=True,
    raise_on_error=True,
)
```

支持三种规范存储方式：

| `storage_type` | 文件数据类型 | `_FillValue` | 缩放属性 |
|---|---|---:|---|
| `float32` | float32 | `999999.0f` | 无 |
| `int32` | int32 | int32 最小值 | `scale_factor`/`add_offset` 为 float64 |
| `int16` | int16 | int16 最小值 | `scale_factor`/`add_offset` 为 float32 |

整数打包在写文件前检查取值范围，溢出直接失败。默认压缩为 `zlib=True`、`complevel=4`、`shuffle=True`，并采用六维 chunk。`roundtrip=True` 会重新读取文件，核对结构、坐标、属性、缺测位置和允许误差。

为兼容旧接口，省略 `storage_type` 时仍采用历史的 int32 打包方式；新代码应显式传入存储类型。只有明确传入 `nimm_standard=False` 时才调用旧 NC 写出实现。

## 全局属性

xarray DataArray 没有独立的 Dataset 全局属性命名空间。接口使用以下方法暂存全局属性，写出时转移到 `Dataset.attrs`，不会混入 `data0.attrs`：

```python
meb.set_griddata_global_attrs(grd, {"TITLE": "example", "SOURCE": "ECMWF"})
attrs = meb.get_griddata_global_attrs(grd)
```

## 测试

在仓库上级项目目录执行：

```powershell
$env:PYTHONPATH=(Resolve-Path -LiteralPath 'CODE\meteva_base').Path
python -m unittest discover -s 'CODE\meteva_base\tests' -p 'test_nimm*.py' -v
```

测试覆盖两份真实 NIMM float32 模板、三种存储模式、写后回读、属性作用域、坐标排序与数据同步、必需坐标拒绝、单格点网格和整数溢出保护。
