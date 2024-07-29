# meteva_base
Include mostly all basic data structure and process APIs in Meteva lib.  Supporting the analysis/MOS/verification .etc on both OBS and NWF model

# meteva_base 基础数据读写处理库

meteva程序库由国家气象中心预报技术研发室检验科负责研发，旨在为从数值模式、客观方法、精细化网格预报到预报产品的应用的整个气象产品制作流程中的每个环节进行快速高效的检验，促进跨流程跨部门的检验信息共享，为推进研究型业务和改进预报质量提供技术支撑。

## 内容
**meteva_base包为meteva程序库中的数据、读写、处理计算及简单绘图等工具的汇总，可以支持大部分气象数据的基础读写转换计算工作。**
功能包括
* 站点、网格、线条数据在内的基础数据结构
* 多源读写(文件、GDS、天擎等)，数十种文件格式(micaps、nc、grib1/2、D131等)
* 多种数据处理转换方法(插值、选取、分组、合并、统计、诊断等)
* 以及多种实用工具(绘图、批量处理、时间处理、文件路径处理等)
* 可支持基于实况和模式预报的常规诊断、后处理及检验等工作。


## Installation  
suport both Windows and Linux system (test on Centos7.1).

```shell
pip install meteva_base
```

## 用户手册
[meteva_base 用户手册及接口API](https://www.showdoc.com.cn/metevabase)

## 设计和研发者
刘凑华（01058995621,15811585045），郭云谦(01058995370)，宫宇，曹勇，唐健，曾晓青，代刊，韦青，朱文剑，

