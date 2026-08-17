# -*- coding: utf-8 -*-
"""
@file    : copy_budget_forecast_xyt.py
@Desc    : 小业态-复制 2026年预算数 Y1 到 2027年预算数 Y1，
           复制 2025年预测数 Y1 到 2026年预测数 Y1
"""

import time
import traceback

from deepfos.options import OPTION
from deepfos.element.finmodel import FinancialCube


def copy_budget(p1, p2, cube):
    """
    复制 2026 年 Budget Y1 数据到 2027 年 Budget Y1
    """
    # 源年份
    src_year = '2026'
    # 目标年份
    tgt_year = '2027'

    # 查询源数据: 2026 Budget Y1
    expr_query = "Year{%s}->Scenario{Budget}->Version{Y1}" % src_year
    df = cube.query(expr_query, compact=False)

    if df.empty:
        print("【小业态-Budget 复制】源数据为空，Year=%s, Scenario=Budget, Version=Y1" % src_year)
        return 0

    row_cnt = len(df)
    print("【小业态-Budget 复制】查询到源数据 %d 条, Year=%s, Scenario=Budget, Version=Y1" % (row_cnt, src_year))

    # 修改年份为 2027
    df['Year'] = tgt_year

    # 先删除目标范围数据，避免重复
    expr_del = "Year{%s}->Scenario{Budget}->Version{Y1}" % tgt_year
    # d = cube.delete(expr_del)
    # print("【小业态-Budget 复制】删除目标数据 %s, Year=%s" % (d, tgt_year))

    # 保存数据
    i = cube.save(df, chunksize=200000)
    print("【小业态-Budget 复制】保存完成 %s, 共 %d 条, Year=%s" % (i, row_cnt, tgt_year))
    return row_cnt


def copy_forecast(p1, p2, cube):
    """
    复制 2025 年 Forecast Y1 数据到 2026 年 Forecast Y1
    """
    # 源年份
    src_year = '2025'
    # 目标年份
    tgt_year = '2026'

    # 查询源数据: 2025 Forecast Y1
    expr_query = "Year{%s}->Scenario{Forecast}->Version{Y1}" % src_year
    df = cube.query(expr_query, compact=False)

    if df.empty:
        print("【小业态-Forecast 复制】源数据为空，Year=%s, Scenario=Forecast, Version=Y1" % src_year)
        return 0

    row_cnt = len(df)
    print("【小业态-Forecast 复制】查询到源数据 %d 条, Year=%s, Scenario=Forecast, Version=Y1" % (row_cnt, src_year))

    # 修改年份为 2026
    df['Year'] = tgt_year

    # 先删除目标范围数据，避免重复
    expr_del = "Year{%s}->Scenario{Forecast}->Version{Y1}" % tgt_year
    # d = cube.delete(expr_del)
    # print("【小业态-Forecast 复制】删除目标数据 %s, Year=%s" % (d, tgt_year))

    # 保存数据
    i = cube.save(df, chunksize=200000)
    print("【小业态-Forecast 复制】保存完成 %s, 共 %d 条, Year=%s" % (i, row_cnt, tgt_year))
    return row_cnt


def main(p1, p2):

    expr_del = "Year{2027}->Scenario{Budget}->Version{Y1}"
    cube = FinancialCube('S_Cube')

    d = cube.insert_null(expr_del)
    expr_del = "Year{2026}->Scenario{Forecast}->Version{Y1}"
    d = cube.insert_null(expr_del)


    # print("【小业态-Budget 复制】删除目标数据 %s, Year=%s" % (d, tgt_year))


    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    print(f"{start_time} 开始执行小业态预算数/预测数 Y1 跨年复制任务")

    try:

        # 小业态 cube
        cube = FinancialCube('S_Cube')

        # 1. 复制 2026 Budget Y1 -> 2027 Budget Y1
        budget_cnt = copy_budget(p1, p2, cube)

        # 2. 复制 2025 Forecast Y1 -> 2026 Forecast Y1
        forecast_cnt = copy_forecast(p1, p2, cube)

        end_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
        print(f"{end_time} 任务执行完成, Budget 复制 {budget_cnt} 条, Forecast 复制 {forecast_cnt} 条")

    except Exception as e:
        print(f"执行出错: {e}")
        traceback.print_exc()


# debug
if __name__ == '__main__':
    try:
        from BIZ.__debug import para1, para2
    except ImportError:
        para1 = para2 = {}
    main(para1, para2)
