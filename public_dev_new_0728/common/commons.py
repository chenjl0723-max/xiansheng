"""
    组合common.py有get_system_data.py对外提供工具
    --- 正式版
"""
from typing import List, Dict, Optional, Union, Tuple, Iterable, Any, Callable
import os
import sys
import functools
import time
import logging
import traceback
import tracemalloc

p = os.path.abspath(os.path.join(__file__, "../.."))
sys.path.append(p)

# import common.common as common_legacy
from deepfos.element.variable import Variable
from deepfos.element.finmodel import FinancialCube
from deepfos.element.dimension import Dimension
from deepfos.element.datatable import DataTableMySQL
from deepfos.db.mysql import MySQLClient
from deepfos.lib.utils import expr_to_dict, dict_to_expr

from deepfos.options import OPTION

import pandas as pd
import calendar
from datetime import datetime
from loguru import logger

__all__ = ["dim_", "cube_", "dtm_", "var_", "rdb_", "timer", "resources_monitor"]

chunksize = 200000


def resources_monitor(
    info: str = "",
    only_once: bool = True,
    monitor_time: bool = True,
    monitor_time_times: int = 1,
    monitor_space: bool = True,
    before_func: Callable = None,
    after_func: Callable = None,
):
    """
    运行资源监视器：监视目标函数的运行时间和运行空间
    如果目标函数只能运行一次，那么运行时间和运行空间需要同时监测；因为在监测运行空间，所以此时的运行时间会明
    显高于正常的运行时间；因为在监测运行时间，所以此时的运行空间会略微大于正常的运行空间（多出2个浮点型变量）。

    Args:
        info: <str> 函数功能介绍
        only_once: <bool> 目标函数是否只能运行一次
        monitor_time: <bool> 是否监测目标函数的运行时间
        monitor_time_times: <int> 监测目标函数运行时间时目标函数的运行次数
            只有当 monitor_time == True and only_once == False 时，monitor_time_times的设置才生效
        monitor_space: <bool> 是否监测目标函数的运行空间
        before_func: <Callable> 函数运行开始前运行的函数，before_func的参数为函数的参数
        after_func: <Callable> 函数运行完成后运行的函数，after_func的参数为函数的返回值
    """

    if info:
        info = f"- {info} "

    if only_once:
        monitor_time_times = 1

    def monitor_decorator(func):
        name = func.__name__

        @functools.wraps(func)
        def wrap_func(*args, **kwargs):
            # 运行执行前运行函数
            if before_func and callable(before_func):
                before_func(*args, **kwargs)

            # 目标函数运行一次 + 同时监测运行时间和运行空间
            if only_once and monitor_time and monitor_space:
                tracemalloc.start()
                start_time = time.time()
                res = func(*args, **kwargs)
                end_time = time.time()
                cur_space, peak_space = tracemalloc.get_traced_memory()  # 返回当前空间和峰值空间
                tracemalloc.stop()

            else:
                # 测试运行时间
                start_time = time.time()
                for _ in range(monitor_time_times):
                    func(*args, **kwargs)
                end_time = time.time()
                # 测试运行空间
                tracemalloc.start()
                res = func(*args, **kwargs)
                cur_space, peak_space = tracemalloc.get_traced_memory()  # 返回当前空间和峰值空间
                tracemalloc.stop()

            use_time = round((end_time - start_time) / monitor_time_times, 6)
            logger.info(
                f"{name} {info} - 运行时间={use_time} 结束内存={cur_space}（字节） 内存峰值={peak_space}（字节）"
            )

            # 运行执行后运行函数
            if after_func and callable(after_func):
                after_func(res)

            return res

        return wrap_func

    return monitor_decorator


def timer(func):
    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        start_time = time.time()
        ret = func(*args, **kwargs)
        end_time = time.time()
        spend_time = end_time - start_time
        print(
            "\033[1;31m function:{} Spend_time:{} s \033[0m".format(
                func.__name__, spend_time
            )
        )
        return ret

    return _wrapper


class dim_:
    r"""
    维度相关:
        1.获取维度: get_dim(dim_name: str, expression: str, path=None), return []
        2.获取维度属性: get_dim_attr(dim_name: str,expression: str,fields: [],path=None) , return df
    """

    def query_dim(self, dim_name: str, expression: str, path=None):
        r"""
            获取维度节点
        :param path:
        :param dim_name: 维度名称
        :param expression: 维度表达式
        :return: 返回维度树
        """
        # 数据库客户端实例化
        dim = Dimension(dim_name, path=path)
        dim_list = []
        for item in dim.query(expression="%s" % expression):
            dim_list.append(item.name)
        return dim_list

    def get_dim_attr(self, dim_name: str, expression: str, fields: [], path=None):
        r"""
            获取维度属性
        :param path: 元素路径
        :param dim_name:  维度名称
        :param expression: 维度表达式
        :param fields:  想要获取的字段
        :return:
        """
        # fields = ['name', 'parent_name']
        # expression = "IDescendant(#root,0)"
        dim = Dimension(element_name=dim_name, path=path)
        data = pd.DataFrame(
            dim.query(expression=expression, fields=fields, as_model=False)
        ).drop(columns="id")
        return data


dim_ = dim_()


class cube_:
    r"""
    cube相关:
        1. 查询cube：query_cube(cube_name: str,fix: str, pov: Union[str, Dict[str, str]] = None, pivot_dim: Optional[str] = "Account", compact: bool = False)， return df_cube
        2. 保存cube：save_cube(df,
          cube_name: str,
          id_vars: [] = None,
          value_vars: [] = None,
          value_name: str = "data",
          var_name: str = "Account",
          del_fix: str = None) , void
        3. 保存cube的简单方式： save_cube_simple(cube, del_fix, data), void
        4. 列转行后保存cube的简单方式：save_cube_simple_pivot(cube, del_fix, data, pivot), void
        5. 同cube数据计算，封装了with方法：save_cube_deepfos(cube, calc_fix, del_fix, calc_func), void
    """

    def pivot_data_to_cube(self, cube, data, pivot, del_fix=None):
        cube = FinancialCube(cube)
        if del_fix:
            cube.delete(del_fix, chunksize=chunksize)
        cube.save_unpivot(data, unpivot_dim=pivot, chunksize=chunksize)

    def get_cube_data(self, cube, expression, pov, pivot_dim=None):
        cube = FinancialCube(cube)
        data = cube.query(
            expression=expression, pov=pov, pivot_dim=pivot_dim, compact=False
        )
        return data

    def data_to_cube(self, cube, del_fix, data):
        cube = FinancialCube(cube)
        cube.delete(del_fix, chunksize=chunksize)
        cube.save(data, chunksize=chunksize)

    def query_cube(
        self,
        cube_name: Union[str, FinancialCube],
        fix: str,
        pov: Union[str, Dict[str, str]] = None,
        pivot_dim: Optional[str] = None,
        compact: bool = False,
    ):
        r"""
            财务模型数据查询
        :param pov:
        :param compact: 是否将pov与查询数据分开输出以减少数据量
        :param cube_name: cube名称
        :param fix: 维度表达式
        :param pivot_dim: 行转列字段
        :return: 返回cube对象
        """
        if isinstance(cube_name, str):
            cube = FinancialCube(cube_name)
        else:
            cube = cube_name
        df_cube = cube.query(
            expression=fix, pov=pov, pivot_dim=pivot_dim, compact=compact
        )
        # df_cube.to_csv("行转列test.csv")
        return df_cube

    def query_cube_adv(
        self,
        cube_name: Union[str, FinancialCube],
        fix: str,
        pov: Union[str, Dict[str, str]] = None,
        pivot_dim: Optional[str] = None,
        compact: bool = False,
    ):
        r"""
            财务模型数据查询
        :param pov:
        :param compact: 是否将pov与查询数据分开输出以减少数据量
        :param cube_name: cube名称
        :param fix: 维度表达式
        :param pivot_dim: 行转列字段
        :return: 返回cube对象,cube数据
        """
        if isinstance(cube_name, str):
            cube = FinancialCube(cube_name)
        else:
            cube = cube_name
        df_cube = cube.query(
            expression=fix, pov=pov, pivot_dim=pivot_dim, compact=compact
        )
        # df_cube.to_csv("行转列test.csv")
        return df_cube, cube

    def save_cube(
        self,
        df,
        cube_name: str,
        id_vars: [] = None,
        value_vars: [] = None,
        value_name: str = "data",
        var_name: str = "Account",
        del_fix: str = None,
    ):
        r"""
            先根据fix进行删数动作后，保存cube数据
        :param df: DateFrame
        :param cube_name: Cube名称
        :param id_vars: 不需要转换的列名
        :param value_vars: 需要转换的列名
        :param value_name: 自定义的值的列名
        :param var_name: 自定义列名
        :param del_fix: 删数的维度表达式
        :param month: 月份
        :return:
        """
        task_dict = OPTION.general.task_info
        if "script_name" in task_dict:
            script_name = task_dict["script_name"].split(".")[-1]
        else:
            script_name = "python"
        cube = FinancialCube(element_name=cube_name, entry_object=script_name)
        if del_fix:
            # 删除原数据,insert_null
            cube.delete(del_fix, chunksize=chunksize)

        # 如果id_vars不为None,则使用cube的属性
        if id_vars is None:
            id_vars = list(cube.dim_col_map.keys())
            subset = list(cube.dim_col_map.keys())
        else:
            subset = id_vars

        if value_name not in df.columns:
            # 列转行
            data = pd.melt(
                df,
                id_vars=id_vars,
                value_vars=value_vars,
                value_name=value_name,
                var_name=var_name,
            )
        else:
            data = df
        # 剔除data为null的值
        # data = data[~data['data'].isnull()]
        data = data.dropna(axis=0, subset=subset, how="any")
        # data = data.dropna(axis=0, how="any")
        return cube.save(data, chunksize=chunksize)

    def save_cube_deepfos(self, cube, calc_fix, del_fix, calc_func):
        r"""
            相同cube，进行取值计算
        :param cube: deepfos的cube
        :param calc_fix: 查询数据范围的维度表达式
        :param del_fix: 删除数据的维度表达式
        :param calc_func: 同cube中的计算函数
        :return: 保存cube过程中，查询/删除等动作如果失败会抛出异常
        """

        # 根据fix进行删除
        cube.cube.delete(del_fix, chunksize=chunksize)
        # 计算cube值
        calc_func(cube, calc_fix)
        # 提交计算结果
        return cube.submit_calc_result()

    def delete(
        self,
        cube_name: Union[str, FinancialCube],
        expression: Union[str, Dict[str, Union[List[str], str]]],
        chunksize: int = chunksize,
    ):
        """
        删除cube数据
        :param cube_name:cube名称
        :param expression:删除fix
        :param chunksize:批处理条数
        :return:
        """
        if isinstance(cube_name, str):
            task_dict = OPTION.general.task_info
            if "script_name" in task_dict:
                script_name = task_dict["script_name"].split(".")[-1]
            else:
                script_name = "python"
            cube = FinancialCube(element_name=cube_name, entry_object=script_name)
        else:
            cube = cube_name
        if expression:
            # 删除原数据,insert_null
            return cube.delete(expression, chunksize=chunksize)

    def get_expr_with_cube(self, cube_name: Union[str, FinancialCube]):
        """
            获取维度表达式的拼接的字符串
        :param cube_name: cube或cube名字
        :return: 根据cube返回维度表达式的字符串形式
        """
        if isinstance(cube_name, str):
            cube = FinancialCube(cube_name)
        else:
            cube = cube_name

        expr = dict_to_expr(cube.col_dim_map)
        print(expr)
        return expr


cube_ = cube_()


class dtm_:
    r"""
    日期与时间相关:
    1. 获取期间的自然月天数: natural_month_days(year_period),return 返回自然月天数.
    2. 获取某月第一天: first_day_of_month(year, month),return 返回%Y-%m-%d格式日期, 如：2022-12-01.
    3. 获取某月最后一天: last_day_of_month(year, month),return 返回%Y-%m-%d格式日期.
    4. 获取次月第一天: first_day_of_next_month,return 返回%Y-%m-%d格式日期.
    """

    def calc_month_days(self, year_period):
        r"""
            获取期间的自然月天数
        :param year_period:
        :return: 返回自然月天数
        """
        # days = reduce(lambda x, y: calendar.monthrange(int(year), int(x))[1] + y, period)
        year, period = year_period.split("-")
        days = calendar.monthrange(int(year), int(period))
        return days

    def first_day_of_month(self, year, month):
        r"""
            获取某月第一天
        :param year:  年
        :param month: 月
        :return: 返回%Y-%m-%d格式日期, 如：2022-12-01
        """
        # 某月第一天
        return datetime.strptime(f"{year}-{month}-01", "%Y-%m-%d")

    def last_day_of_month(self, year, month):
        r"""
            获取某月最后一天
        :param year: 年
        :param month: 月
        :return: 返回%Y-%m-%d格式日期
        """
        # 获取每月最后一天
        l_day = calendar.monthrange(int(year), int(month))[1]
        last_day = datetime.strptime(f"{year}-{month}-{l_day}", "%Y-%m-%d")
        return last_day

    def first_day_of_next_month(self, year, month):
        r"""
            获取次月第一天
        :param year: 年
        :param month: 月
        :return:  返回%Y-%m-%d格式日期
        """
        # 次月第一天
        if int(month) == 12:
            next_first_day = datetime.strptime(f"{int(year) + 1}-01-01", "%Y-%m-%d")
        else:
            next_first_day = datetime.strptime(
                f"{year}-{str(int(month) + 1)}-01", "%Y-%m-%d"
            )

        return next_first_day


dtm_ = dtm_()


# dtm_.natural_month_days = calc_month_days
# dtm_.first_day_of_month = first_day_of_month
# dtm_.last_day_of_month = last_day_of_month
# dtm_.first_day_of_next_month = first_day_of_next_month


class var_:
    r"""
    变量相关:
    1.获取变量：get_variable(variable, v_key) ,return 变量值, 多余的封装
    """

    def get_variable(self, variable, v_key):
        var = Variable(variable)
        return var.get_value(v_key)


var_ = var_()


class rdb_:
    r"""
    关系型数据库相关：
    1. 数据表查询: select(table, columns=None, where=None) ,return df
    """

    def select(self, columns, tbl, where="None", path=None):
        """
        获取mysql数据表中的数据
        :param tbl:表名
        :param path:路径
        :param columns:字段集合
        :param where:查询条件
        :return:
        """
        sql_obj = DataTableMySQL(tbl, path=path)
        t = sql_obj.table
        dt_data = sql_obj.select(columns=columns, where=eval(where))

        return dt_data

    def query_dfs(self, sqls: str):
        """
            使用sqls语句直接查询数据库表, 可多表联查
        :param sqls: SQL语句
        :return: 返回DataFrame
        """
        client = MySQLClient()
        dt_data = client.query_dfs(sqls)
        if dt_data.size > 0:
            return dt_data
        else:
            return pd.DataFrame()

    def exec_sql(self, sqls: str):
        client = MySQLClient()
        return client.exec_sqls(sqls)

    def insert_sql(
        self,
        tbl,
        data: pd.DataFrame,
        path: str = None,
        updatecol: Iterable = None,
        chunksize: int = 5000,
        auto_fit: bool = True,
    ):
        sql_obj = DataTableMySQL(tbl, path=path)
        return sql_obj.insert_df(data, updatecol, chunksize, auto_fit)


rdb_ = rdb_()


class dat_(object):
    r"""
    版本复制, 同cube操作, 推荐MDX方式
    """

    def version_copy(
        self, cube_name: Union[str, FinancialCube], formula: str, fix_members: str
    ):
        r"""
            简单的版本复制
        :param cube_name: cube名称或对象
        :param formula: 维度成员来源和目的的表达式
        :param fix_members: 维度成员的筛选表达式
        :return: void
        """

        if isinstance(cube_name, str):
            cube = FinancialCube(cube_name)
        else:
            cube = cube_name

        del_fix = fix_members + "->" + formula.split("=")[0]
        # 删数
        cube.delete(del_fix, chunksize=chunksize)
        # 保存数据
        cube.copy_calculate(formula=formula, fix_members=fix_members)


dat_ = dat_()

if __name__ == "__main__":
    ret = dtm_.first_day_of_month("2022", "02")
    print(ret)
