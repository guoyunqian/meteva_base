# -*- coding:utf-8 -*-
import os
from concurrent import futures
from multiprocessing import Pool

def mult_process(func=None, func_args_all=[], max_workers=4, force_max_workers=False):
    '''
    [多进程计算/绘图]
    Keyword Arguments:
        func {[type]} -- [函数] (default: {None})
        func_args_all {list} -- [函数参数] (default: {[]})
        max_workers {number} -- [进程池大小] (default: {6})
        force_max_workers {bool} -- [是否强制使用max_workers参数，默认关闭] (default: {False})
    Returns:
        [list] -- [有效的返回结果]
    '''
    if len(func_args_all) == 0:
        return []

    # 多进程绘图
    if force_max_workers == False:
        use_sys_cpu = max(1, os.cpu_count() - 1)  # 可使用的cpu核心数为cpu核心数-1
        max_workers = min(max_workers, use_sys_cpu)  # 最大进程数
    print('cpu_count={}, use max_workers={}'.format(os.cpu_count(), max_workers))

    all_ret = []
    with futures.ProcessPoolExecutor(max_workers=max_workers) as executer:
        # 提交所有绘图任务
        all_task = [executer.submit(func, _) for _ in func_args_all]
        # 等待
        futures.wait(all_task, return_when=futures.ALL_COMPLETED)
        # 取返回值
        for task in all_task:
            exp = task.exception()
            if exp is None:
                all_ret.append(task.result())
            else:
                print(exp)
                pass
    return all_ret    


## 并行计算相关
def __split_list_equal(list0, n):
    ## list0等分，每份n个
    for i in range(0, len(list0),n):
        yield list0[i:i+n]

def __split_list_nlist(list0, n):
    ## list0等分为n组
    if len(list0)%n == 0:
        cnt = len(list0)//n
    else:
        cnt = len(list0)//n+1
    for i in range(0,n):
        yield list0[i*cnt : (i+1)*cnt]

def multi_pool_cal(operation, input, pro_count):
    """
    不带返回值的并行同步处理
    ## operation为待并行函数
    ## input为某参数并行列表(list)， pro_count为进程数
    ## 根据pro_count自动将input切分为等长的n份，作为并行参数
    """
    processes_pool = Pool(pro_count)
    input_mpi = list(__split_list_nlist(input, pro_count))
    # 开始并行
    processes_pool.map(operation, input_mpi)
    return None


def multi_model_process(model, input, n_pools = 6):
    """
    带返回值的并行同步处理，返回多结果列表。
    ## operation为待并行函数，支持多参数(args)
    ## 进行异步非阻塞循环
    """
    results=[]
    datelist_mpi = list(__split_list_nlist(input, n_pools))#大list平分为若干小list
    processes_pool = Pool(n_pools)
    for dtlist in datelist_mpi:
        print(dtlist)
        res = processes_pool.apply_async(model.process, args=(dtlist,))
        results.append(res)
    processes_pool.close()
    processes_pool.join()
    a = []
    # 数据整理,apply_async()组织数据
    a = [i.get() for i in results]
    results = pd.concat(a, axis=0)
    return(results)


if __name__ =="__main__":
    import numpy as np
    #result = task(numbers)
    list0 = np.arange(10)
    print(list(__split_list_equal(list0, 3)))
    pass