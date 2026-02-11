# task_functions.py（适配简化汇总版并行类，无需修改）
from typing import Union, Dict, Any
from multipro_plugin import SimpleParallelTool

# ---------------------- 测试函数，有返回值任务函数 ----------------------
def complex_calc_by_dict(**kwargs) -> Union[Dict[str, Any], str]:
    """
    多参数复杂计算函数（返回字典格式，适配简化汇总版并行类）
    必选参数：base（计算基数）
    可选参数：power（幂次，默认2）、coefficient（系数，默认1.0）、offset（偏移量，默认0.0）
    """
    try:
        # 提取参数
        base = kwargs["base"]
        power = kwargs.get("power", 2)
        coefficient = kwargs.get("coefficient", 1.0)
        offset = kwargs.get("offset", 0.0)
        # 执行计算
        calc_result = (pow(base, power)) * coefficient + offset

        # 返回字典格式结果（改为带状态的字典，方便汇总统计）
        return {"status": "成功", "msg": "计算完成", "data": calc_result}

    except KeyError as e:
        return {"status": "失败", "msg": f"缺少必选参数 {str(e)}", "data": None}
    except TypeError as e:
        return {"status": "失败", "msg": f"参数类型错误 - {str(e)}", "data": None}
    except Exception as e:
        return {"status": "失败", "msg": f"计算异常 - {str(e)}", "data": None}

# ---------------------- 测试函数，无返回值任务函数 ----------------------
def batch_print_info(**kwargs) -> None:
    """
    批量打印信息函数（无返回值，适配简化汇总版并行类）
    必选参数：base（基础信息）
    可选参数：prefix（打印前缀，默认「任务」）
    """
    try:
        # 提取参数
        base = kwargs["base"]
        prefix = kwargs.get("prefix", "任务")

        # 仅执行操作（无返回值）
        print(f"【{prefix}】执行完毕：base={base}")
    except Exception as e:
        print(f"【任务异常】：{str(e)}")




# ---------------------- 演示函数 ----------------------
def main_sync_with_return():
    """演示场景1：同步（sync）+ 有返回值（with_return=True），简化结果汇总"""
    # 1. 实例化并行类（全局配置：同步、有返回、固定参数）
    parallel_tool = SimpleParallelTool(
        target_func=complex_calc_by_dict,
        parallel_mode="sync",
        with_return=True,
        fixed_params={
            "power": 3,
            "coefficient": 0.8,
            "offset": 10.0
        },
        num_process=4
    )
    # 2. 配置并行参数（仅聚合字典）
    parallel_params = {
        "base": list(range(1, 12))  
    }
    # 3. 执行并行任务
    print("\n=== 场景1：同步（sync）+ 有返回值 ===")
    calc_results = parallel_tool.process(
        parallel_params=parallel_params
    )


def main_async_with_return():
    """演示场景2：异步（async）+ 有返回值（with_return=True），简化结果汇总"""
    # 1. 实例化并行类（全局配置：异步、有返回、固定参数）
    parallel_tool = SimpleParallelTool(
        target_func=complex_calc_by_dict,
        parallel_mode="async",
        with_return=True,
        fixed_params={
            "power": 2,
            "coefficient": 1.0,
            "offset": 5.0
        },
        num_process=4
    )
    # 2. 配置并行参数
    parallel_params = {
        "base": list(range(1, 12))
    }
    # 3. 执行并行任务（异步非阻塞，后台执行）
    print("\n=== 场景2：异步（async）+ 有返回值 ===")
    calc_results = parallel_tool.process(
        parallel_params=parallel_params
    )


def main_async_without_return():
    """演示场景3：异步（async）+ 无返回值（with_return=False），仅执行任务"""
    # 1. 实例化并行类（全局配置：异步、无返回、固定参数）
    parallel_tool = SimpleParallelTool(
        target_func=batch_print_info,
        parallel_mode="async",
        with_return=False,
        fixed_params={
            "prefix": "异步批量打印任务"
        },
        num_process=4
    )
    # 2. 配置并行参数
    parallel_params = {
        "base": list(range(1, 10))  # 10个打印任务
    }
    # 3. 执行并行任务（无返回值，仅打印）
    print("\n=== 场景3：异步（async）+ 无返回值 ===")
    parallel_tool.process(
        parallel_params=parallel_params
    )


if __name__ == "__main__":
    main_sync_with_return()
    main_async_with_return()
    main_async_without_return()