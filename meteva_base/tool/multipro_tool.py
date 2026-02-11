# parallel_tools.py（补充同步/异步、有返回/无返回的详细注释，用于代码维护）
from multiprocessing import Pool
from typing import Callable, Dict, List, Any, Optional
import os
from time import time


class SimpleParallelTool:
    """
    简化汇总版并行工具类（支持同步/异步、全局参数配置，仅保留核心统计汇总）
    核心概念说明：
    1.  并行模式：同步（sync）/ 异步（async）→ 控制任务执行的阻塞/非阻塞特性
    2.  返回模式：有返回（with_return=True）/ 无返回（with_return=False）→ 控制是否收集任务执行结果
    """

    def __init__(
        self,
        target_func: Callable,
        num_process: int = 4,
        parallel_mode: str = "sync",
        with_return: bool = True,
        fixed_params: Optional[Dict] = None,
    ):
        """
        类初始化：统一配置全局参数，后续调用无需重复传参
        :param target_func: 目标函数，所有并行任务都将执行此函数
            说明：目标函数的参数分为固定参数和并行参数，
                固定参数：在所有并行任务中保持不变的参数，如数据库连接信息、固定计算系数等, 固定参数在fixed_params中配置
                并行参数：每个并行任务根据不同输入值变化的参数，如批量处理的列表、字典等, 并行参数在process方法中配置
        :param num_process: 默认最大并行进程数（正整数，默认4）
            说明：控制进程池的大小，建议根据CPU核心数设置（一般为CPU核心数*1~2），避免进程过多导致资源竞争
        :param parallel_mode: 并行执行模式，仅支持两种取值
            - "sync"：同步并行（默认）→ 阻塞执行，直到所有任务全部完成后才返回结果/继续后续代码
              适合场景：需要立即获取任务结果、后续逻辑依赖并行任务输出、小批量任务（1000条以内）
            - "async"：异步并行 → 非阻塞执行，调用后立即返回，任务在后台进程池中运行
              适合场景：无需立即等待结果、后续逻辑不依赖并行任务输出、大批量任务（1000条以上）、后台批量操作（如批量写入、批量通知）
        :param with_return: 任务结果返回模式，布尔值
            - True：有返回值（默认）→ 收集所有任务的执行返回结果，封装为列表返回，支持后续结果汇总和数据处理
              适合场景：批量计算、批量查询、需要统计任务执行结果、需要对返回数据进行二次处理的场景（如数据清洗、入库）
            - False：无返回值 → 仅执行任务，不收集任何返回结果，执行效率更高，节省内存
              适合场景：批量打印、批量写入文件/数据库、批量发送请求/通知、仅需执行操作无需获取结果的场景
        :param fixed_params: 全局固定参数字典（所有任务共享），可选
            说明：固定参数会被每个任务的并行参数覆盖（同名键优先级：并行参数 > 固定参数）
            适合场景：所有任务共用的公共配置（如计算幂次、打印前缀、请求超时时间）
        """
        # 0. 目标函数校验
        if not callable(target_func):
            raise ValueError("target_func 必须是可调用对象（函数、方法、lambda表达式等）")
        self.target_func = target_func

        # 1. 并行模式校验与配置
        if parallel_mode not in ["sync", "async"]:
            raise ValueError("parallel_mode 仅支持 'sync'（同步）或 'async'（异步）")
        self.parallel_mode = parallel_mode

        # 2. 其他全局参数配置
        self.with_return = with_return
        self.fixed_params = fixed_params or {}
        if num_process >= os.cpu_count():
            num_process = os.cpu_count() - 1
        self.default_max_processes = num_process

        # 3. 全局参数合法性二次校验
        if not isinstance(self.with_return, bool):
            raise ValueError("with_return 必须是布尔值（True/False）")
        if not isinstance(self.fixed_params, dict):
            raise ValueError("fixed_params 仅支持字典格式")
        if not isinstance(self.default_max_processes, int) or self.default_max_processes <= 0:
            raise ValueError("default_max_processes 必须是正整数")

        # 4. 缓存变量：用于异步模式存储结果（非阻塞场景）
        self._async_results = None

    # ---------------------- 顶层可序列化函数（新增异步执行函数）----------------------
    @staticmethod  # 改为静态方法，避免引用实例变量导致序列化问题
    def _execute_with_params(params: Dict) -> Any:
        """顶层方法：执行目标函数并传递参数（替代局部lambda）"""
        target_func = params.pop("_target_func")
        return target_func(** params)

    @staticmethod  # 改为静态方法
    def _execute_ignore_return(params: Dict) -> None:
        """顶层方法：执行目标函数但忽略返回值（替代嵌套函数）"""
        try:
            target_func = params.pop("_target_func")
            target_func(** params)
        except Exception as e:
            print(f"同步任务执行异常：{str(e)}")

    @staticmethod  # 改为静态方法，彻底避免跨进程传递实例
    def _execute_async_with_return(params: Dict) -> Any:
        """顶层方法：异步执行并返回结果（解决pickle序列化问题）"""
        try:
            return params["_target_func"](** params)
        except Exception as e:
            print(f"异步任务执行异常：{str(e)}")
            return None

    # ---------------------- 私有辅助方法（聚合字典处理）----------------------
    def _validate_aggregate_dict(self, aggregate_dict: Dict) -> None:
        """校验聚合字典格式是否合法（仅支持：{'参数名': [批量参数列表]}）"""
        if not isinstance(aggregate_dict, dict):
            raise ValueError("并行参数仅支持聚合字典格式 → 示例：{'base': [1,2,3]}")
        if len(aggregate_dict) == 0:
            raise ValueError("聚合字典不能为空，请传入有效参数键值对")
        for key, value in aggregate_dict.items():
            if not (isinstance(value, list) and len(value) > 0):
                raise ValueError(f"聚合字典中键「{key}」对应的值必须是非空列表")
        list_lengths = [len(lst) for lst in aggregate_dict.values()]
        if len(set(list_lengths)) != 1:
            raise ValueError("聚合字典中所有参数列表的长度必须一致")

    def _convert_aggregate_to_task_list(self, aggregate_dict: Dict) -> List[Dict]:
        """将聚合字典转换为单个任务的参数字典列表（供后续并行执行）"""
        self._validate_aggregate_dict(aggregate_dict)
        param_keys = list(aggregate_dict.keys())
        param_lists = list(aggregate_dict.values())
        task_count = len(param_lists[0])

        task_list = []
        for i in range(task_count):
            single_task_dict = {key: param_lists[j][i] for j, key in enumerate(param_keys)}
            task_list.append(single_task_dict)
        return task_list

    def _merge_task_params(self, task_list: List[Dict]) -> List[Dict]:
        """合并单个任务字典与全局固定参数字典（并行参数优先级 > 固定参数）"""
        return [{**self.fixed_params, **single_task} for single_task in task_list]

    # ---------------------- 核心并行逻辑（同步+异步，有返回+无返回）----------------------
    # --- 同步并行（阻塞）---
    def _parallel_sync_with_return(self, full_task_params: List[Dict]) -> Optional[List[Any]]:
        """
        同步-有返回值：阻塞执行，收集所有任务结果
        特性：调用后会阻塞当前线程，直到所有任务执行完成并收集完结果才返回
        适合场景：小批量任务、后续逻辑依赖任务结果、需要立即获取并处理返回数据
        """
        # 给每个任务参数添加目标函数（顶层方法可序列化）
        task_params_with_func = [{"_target_func": self.target_func, **params} for params in full_task_params]
        with Pool(processes=self.default_max_processes) as pool:
            all_results = pool.map(self._execute_with_params, task_params_with_func)
        return all_results

    def _parallel_sync_without_return(self, full_task_params: List[Dict]) -> None:
        """
        同步-无返回值：阻塞执行，仅执行任务不收集结果
        特性：调用后会阻塞当前线程，直到所有任务执行完成，但不收集任何返回结果，节省内存
        适合场景：小批量操作类任务（如批量打印、小文件写入）、无需获取结果但需要等待任务全部完成
        """
        task_params_with_func = [{"_target_func": self.target_func, **params} for params in full_task_params]
        with Pool(processes=self.default_max_processes) as pool:
            pool.map(self._execute_ignore_return, task_params_with_func)
        return None

    # --- 异步并行（非阻塞）---
    def _parallel_async_with_return(self, full_task_params: List[Dict]) -> Optional[List[Any]]:
        """
        异步-有返回值：非阻塞执行，收集所有任务结果（修复pickle序列化问题）
        特性：调用后立即返回，任务在后台进程池中运行；结果通过get()获取（内部已处理，保证兼容性）
        """
        # 1. 给任务参数添加目标函数（和同步逻辑保持一致）
        task_params_with_func = [{"_target_func": self.target_func, **params} for params in full_task_params]
        
        # 2. 重构异步逻辑：避免Pool对象跨进程传递
        pool = Pool(processes=self.default_max_processes)
        try:
            # 提交异步任务（使用静态方法，无实例引用）
            self._async_results = pool.map_async(
                self._execute_async_with_return, 
                task_params_with_func
            )
            # 如需完全非阻塞，可注释掉下面的get()，让用户自行调用self._async_results.get()
            # 保留get()保证原有逻辑兼容性（异步但仍等待结果返回，符合示例代码预期）
            results = self._async_results.get(timeout=None)  
            return results if self.with_return else None
        finally:
            pool.close()  # 不接受新任务
            pool.join()   # 等待所有子进程完成

    def _parallel_async_without_return(self, full_task_params: List[Dict]) -> None:
        """
        异步-无返回值：非阻塞执行，仅执行任务不收集结果
        特性：调用后立即返回，任务在后台进程池中运行，不收集任何返回结果，效率最高、内存占用最少
        """
        task_params_with_func = [{"_target_func": self.target_func, **params} for params in full_task_params]
        pool = Pool(processes=self.default_max_processes)
        try:
            pool.map_async(self._execute_ignore_return, task_params_with_func)
            return None
        finally:
            pool.close()  # 不接受新任务
            # 异步无返回场景不调用join()，保证非阻塞特性
            # pool.join()  # 注释掉，避免阻塞

    # ---------------------- 公开统一执行入口（根据全局配置自动分支）----------------------
    def process(self, parallel_params: Dict, show: bool = True) -> Optional[List[Any]]:
        """
        统一执行入口：根据__init__中的全局配置，自动切换同步/异步、有返回/无返回
        :param parallel_params: 并行参数（仅支持聚合字典 {'base': [1,2,3]}）
        :param show: 是否打印任务结果汇总信息（默认True）
        :return: 有返回值场景返回结果列表，无返回值场景返回None
        分支逻辑说明：
        1.  parallel_mode="sync" + with_return=True → 同步阻塞，返回结果列表（小批量计算/查询）
        2.  parallel_mode="sync" + with_return=False → 同步阻塞，仅执行任务（小批量操作）
        3.  parallel_mode="async" + with_return=True → 异步非阻塞，返回结果列表（大批量计算/查询）
        4.  parallel_mode="async" + with_return=False → 异步非阻塞，仅执行任务（大批量操作，推荐）
        """
        # 1. 参数合法性校验
        if not isinstance(parallel_params, dict) or not parallel_params:
            raise ValueError("parallel_params 必须是非空字典")

        # 2. 处理并行参数（聚合字典 → 任务列表 → 合并固定参数）
        task_list = self._convert_aggregate_to_task_list(parallel_params)
        full_task_params = self._merge_task_params(task_list)

        # 3. 根据全局配置分支执行（并行模式 + 是否返回结果）
        summary = {}#统计信息
        start_time = time()
        if self.with_return:#有返回值
            # 同步分支：阻塞执行，等待所有任务完成
            if self.parallel_mode == "sync":
                result = self._parallel_sync_with_return(full_task_params)
            # 异步分支：非阻塞执行，后台运行任务
            else:
                result = self._parallel_async_with_return(full_task_params)
            if result is not None:
                total_count = len(result)
                summary["total_count"] = total_count
        else:#无返回值
            # 同步分支：阻塞执行，仅执行任务（小批量操作）
            if self.parallel_mode == "sync":
                self._parallel_sync_without_return(full_task_params)
            # 异步分支：非阻塞执行，仅执行任务（大批量操作，推荐）
            else:
                self._parallel_async_without_return(full_task_params)
        summary["total_time"] = time() - start_time
        if show:
            print("\n===== 并行结束，结果汇总 =====")
            print(summary)
        return result if self.with_return else None
    


# ---------------------- 测试函数，无返回值任务函数 ----------------------
def batch_print_info(base, prefix='任务') -> None:
    """
    批量打印信息函数（无返回值，适配简化汇总版并行类）
    必选参数：base（基础信息）
    可选参数：prefix（打印前缀，默认「任务」）
    """
    try:
        # 仅执行操作（无返回值）
        print(f"【{prefix}】执行完毕：base={base}", flush=True)
    except Exception as e:
        print(f"【任务异常】：{str(e)}")
    return None

# 测试并行性能
if __name__ == "__main__":
      
    #循环参数
    base0 = list(range(1, 12)) #待循环参数
    print(base0)

    ###循环非并行执行
    prefix0 = '循环任务'
    for base in base0:
        batch_print_info(prefix=prefix0,base=base)

    ###并行异步执行
    prefix1 = '异步任务'
    # 1. 实例化并行类（全局配置：异步、无返回、固定参数）
    parallel_tool = SimpleParallelTool(
        target_func=batch_print_info,#目标函数
        parallel_mode="async",#异步模式
        with_return=False,#无返回值
        fixed_params={#固定参数,非循环参数
            "prefix": prefix1
        },
        num_process=4#进程数
    )
    # 2. 配置并行参数
    parallel_params = {
        "base": base0
    }
    # 3. 执行并行任务（异步非阻塞，后台执行）
    parallel_tool.process(
        parallel_params=parallel_params
    )
    # 【新增】主线程在此空转等待，给子进程执行打印的时间
    from time import sleep
    print("主线程已结束任务提交，正在等待子进程后台运行...")
    sleep(2)  # 暂停2秒，足够让简单的打印任务执行完

