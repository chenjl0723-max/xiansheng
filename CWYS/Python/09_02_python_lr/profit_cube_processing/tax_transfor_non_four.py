# -*- coding: utf-8 -*-
'''
@file    : tax_transfor.py
@Time    :
@Author  : CHEN
@Software: PyCharm
@Desc    : 成本、收入税率转换
'''

try:
    from CWYS._debug import para1, para2
    # print(para1)
except ImportError:
    para1 = para2 = {}
from deepfos.options import OPTION
import pandas as pd
import traceback
import time
import os
from datetime import datetime
from deepfos.db.mysql import MySQLClient
from deepfos.element.datatable import DataTableClickHouse
from deepfos.element.finmodel import FinancialCube
from deepfos.element.datatable import DataTableClickHouse as ck
from deepfos.element.datatable import DataTableMySQL
from deepfos.element.variable import Variable
from deepfos.element.dimension import Dimension, DimMember
from deepfos.element.pyscript import PythonScript
import numpy as np


# from _debug import p1, p2


def group_and_sum(df, group_cols, value_col='figure'):
    """
    按指定维度汇总数值
    """
    if df.empty:
        return df

    # 确保 group_cols 中的列都存在
    exist_cols = [col for col in group_cols if col in df.columns]

    df = df.groupby(exist_cols, as_index=False)[value_col].sum()
    return df


def main_processing(p1, p2):
    Year = p2['Year_wb1']
    last_Year = str(int(Year) - 1)
    Version = p2['Version_wb1']
    Entity_GL = p2['Entity_GL_wb1']

    df_all = pd.DataFrame()
    cube = FinancialCube('sub_profit_cube')

    # 获取实际数
    fix_act = "Year{%s}->Scenario{Actual}->Version{%s}->Period{Base(TotalPeriod,0)}->Comprehensive{NoTax}->" \
              "Entity_GL{%s}->Measure{Expenses}->Account_lirun{Base(PL600102,0);Base(PL60020202,0)}->" \
              "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
              % (last_Year, Version, Entity_GL)

    df_act = cube.query(fix_act, compact=False)

    if not df_act.empty:
        df = tax_rate_processing(df_act, last_Year, Version, Entity_GL, Scenario='Actual')
        df_all = pd.concat([df_all, df])
        # push_processing(act_df,year)

    # 获取预测数
    fix_forecast = "Year{%s}->Scenario{Forecast}->Version{%s}->Period{Base(TotalPeriod,0)}->Comprehensive{NoTax}->" \
                   "Entity_GL{%s}->Measure{Expenses}->Account_lirun{Base(PL600102,0);Base(PL60020202,0)}->" \
                   "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                   % (last_Year, Version, Entity_GL)

    df_fix_forecast = cube.query(fix_forecast, compact=False)

    if not df_fix_forecast.empty:
        df = tax_rate_processing(df_fix_forecast, last_Year, Version, Entity_GL, Scenario='Forecast')
        df_all = pd.concat([df_all, df])

    # 获取预算数
    fix_budget = "Year{%s}->Scenario{Budget}->Version{%s}->Period{Base(TotalPeriod,0)}->Comprehensive{NoTax}->" \
                 "Entity_GL{%s}->Measure{Expenses}->Account_lirun{Base(PL600102,0);Base(PL60020202,0)}->" \
                 "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                 % (Year, Version, Entity_GL)

    df_fix_budget = cube.query(fix_budget, compact=False)

    if not df_fix_budget.empty:
        df = tax_rate_processing(df_fix_budget, Year, Version, Entity_GL, Scenario='Budget')
        df_all = pd.concat([df_all, df])

    print(1)
    push_processing(df_all, cube, Year, Version, Entity_GL)


def tax_rate_processing(df, Year, Version, Entity_GL, Scenario):
    # act_df['Comprehensive'] = 'NoTax'
    # Version = Variable('Variable').get('Edit_Ver')

    cube = FinancialCube('sub_profit_cube')

    if Scenario in ('Actual', 'Forecast'):
        fix_rate = "Year{%s}->Scenario{Actual}->Version{%s}->Period{Base(TotalPeriod,0)}->Comprehensive{Taxrate}->" \
                   "Entity_GL{%s}->Measure{Expenses}->Account_lirun{Base(PL600102,0);Base(PL60020202,0)}->" \
                   "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                   % (Year, Version, Entity_GL)
    elif Scenario == 'Budget':
        fix_rate = "Year{%s}->Scenario{%s}->Version{%s}->Period{Base(TotalPeriod,0)}->Comprehensive{Taxrate}->" \
                   "Entity_GL{%s}->Measure{Expenses}->Account_lirun{Base(PL600102,0);Base(PL60020202,0)}->" \
                   "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                   % (Year, Scenario, Version, Entity_GL)

    # 获取税率
    df_rate = cube.query(fix_rate, compact=False)

    # 实际数合并税率
    # df_tax = pd.merge(df,df_rate[['Account_lirun', 'Period','Year', 'Entity_GL', 'data']].rename(
    #                         columns={"data": "rate_data"}), how='inner')

    # 处理匹配不到税率的行：不含税等于含税
    # 首先，找出在df中但不在df_tax中的行（即内连接未匹配上的行）
    # 我们可以通过左连接然后筛选出rate_data为NaN的行来实现
    df_merged = pd.merge(df, df_rate[['Account_lirun', 'Period', 'Year', 'Entity_GL', 'data']].rename(
        columns={"data": "rate_data"}), how='left')

    # 对于rate_data为NaN的行，含税等于不含税，即直接使用原数据，Comprehensive设为'Tax'
    df_no_rate = df_merged[df_merged['rate_data'].isna()].copy()
    if not df_no_rate.empty:
        df_no_rate['Comprehensive'] = 'Tax'
        # 保持原数据不变
        # df_no_rate = df_no_rate.drop(columns=['rate_data'])

    # 对于有税率的行，进行税率转换计算
    df_with_rate = df_merged[df_merged['rate_data'].notna()].copy()
    if not df_with_rate.empty:
        df_with_rate['data'] = df_with_rate['data'] * (1 + df_with_rate['rate_data'])
        df_with_rate['Comprehensive'] = 'Tax'
        # df_with_rate = df_with_rate.drop(columns=['rate_data'])

    # 合并两部分结果
    df_all = pd.concat([df_with_rate, df_no_rate], ignore_index=True)

    del df_all['rate_data']

    return df_all


def push_processing(df, cube, Year, Version, Entity_GL):
    last_year = str(int(Year) - 1)
    # # 写入财务预算利润模型

    del_fix1 = "Year{%s}->Scenario{Actual}->Version{%s}->Period{Base(TotalPeriod,0)}->Comprehensive{Tax}->" \
               "Entity_GL{%s}->Account_lirun{Base(PL600102,0);Base(PL60020202,0)}" \
               % (last_year, Version, Entity_GL)
    del_fix2 = "Year{%s}->Scenario{Forecast}->Version{%s}->Period{Base(TotalPeriod,0)}->Comprehensive{Tax}->" \
               "Entity_GL{%s}->Account_lirun{Base(PL600102,0);Base(PL60020202,0)}" \
               % (last_year, Version, Entity_GL)
    del_fix3 = "Year{%s}->Scenario{Budget}->Version{%s}->Period{Base(TotalPeriod,0)}->Comprehensive{Tax}->" \
               "Entity_GL{%s}->Account_lirun{Base(PL600102,0);Base(PL60020202,0)}" \
               % (Year, Version, Entity_GL)

    cube.insert_null(del_fix1)
    cube.insert_null(del_fix2)
    cube.insert_null(del_fix3)
    # cube.insert_null(expr_dict_forecast)
    print(df)
    cube.save(df, chunksize=200000)


def main(p1, p2):
    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    countAll = 0
    countSuccess = 0
    countError = 0
    countMsg = f"{start_time} 开始执行非四大区收入成本税率转换任务\n"

    try:
        main_processing(p1, p2)
        countSuccess = 1
        countAll = 1
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 非四大区收入成本税率转换处理完成\n"

    except Exception as e:
        countError = 1
        countAll = 1
        error_detail = traceback.format_exc()
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}  非四大区收入成本税率转换失败: {str(e)}\n"
        countMsg += f"详细错误信息:\n{error_detail}\n"
        print(f" 非四大区收入成本税率转换执行出错: {e}")
        traceback.print_exc()

    # ====================== 写入日志 ======================
    ele_name = os.path.basename(__file__)
    ele_path = os.path.dirname(os.path.abspath(__file__))

    try:
        sync_log = PythonScript(element_name='pyLog', path='/09_Python/common', should_log=True)
        sync_result = sync_log.run(
            parameter={
                'ele_name': ele_name,
                'ele_path': ele_path,
                'data_count': countAll,
                'error_count': countError,
                'logs': countMsg,
                'dt': datetime.now().strftime('%Y%m%d'),
                'start_time': start_time,
                'exe_parameter': str(p2)
            }
        )
        if sync_result:
            print("日志记录成功！")
        else:
            print("日志记录失败！")
    except Exception as log_e:
        print(f"日志记录异常: {log_e}")

    # 返回执行结果（与维度脚本保持一致）
    return False if countError > 0 else True


# debug
if __name__ == '__main__':
    para2 = {'Year_wb1': '2026', 'Version_wb1': 'V1', 'Entity_GL_wb1': 'QT240019'}
    main(para1, para2)

