# -*- coding: utf-8 -*-
'''
@file    : gb_forecast_push_review_cube.py
@Time    :
@Author  : CHEN
@Software: PyCharm
@Desc    : 管报预测进利润审核模型
'''


try:
    from CWYS.__debug import para1, para2
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


def forecast_processing(p1, p2, Version, Year,cube):

    
    # 获取管报预测数据
    fore_dt = DataTableMySQL('gb_perf_forecast')
    cols = ['Mgmt_entity', 'Profit_acct', 'Year_code', 'Commercial','Projtype','Consv_Incrmt','Pattern','decimal_val']


    # 筛选场景是0101(实际数)
    where = "Year_code = '%s' and Period_code = 'TotalPeriod' and scenario = '0303' and Version = 'V0' " % Year

    fore_df = fore_dt.select(columns=cols,where = where)

    fore_df = fore_df.rename(columns={
        "Mgmt_entity": "Entity_GL",
        "Profit_acct": "Account_lirun",
        "Year_code": "Year",
        "Projtype": "Project_Type",
        "Consv_Incrmt":"inc_stock",
        "decimal_val": "data",
    })

    # 对指定列的值添加前缀
    if 'Commercial' in fore_df.columns:
        fore_df['Commercial'] = 'YT' + fore_df['Commercial'].astype(str)
    if 'inc_stock' in fore_df.columns:  # 注意：列已重命名为 'inc_stock'
        fore_df['inc_stock'] = 'A' + fore_df['inc_stock'].astype(str)
    if 'Pattern' in fore_df.columns:
        fore_df['Pattern'] = 'T' + fore_df['Pattern'].astype(str)

    fore_df['Version'] = 'V1'
    fore_df['Period'] = 'Noperiod'
    fore_df['Scenario'] = 'Forecast'
    fore_df['Measure'] = 'PerforAmt'
    fore_df['Misc1'] = 'nomisc1'
    fore_df['Misc2'] = 'nomisc2'

    push_processing(fore_df,Year,Version,cube)


def push_processing(fore_df,Year,Version,cube):

    # 过滤缺失项目得数据
    entity_dim = Dimension('Entity_GL')
    entity_list = pd.DataFrame(entity_dim.query(expression="Base(#root,0)", fields=['name'], as_model=False))
    df = fore_df[fore_df['Entity_GL'].isin(entity_list['name'])]

    # 找出缺失的科目
    missing_entitys = set(fore_df['Entity_GL']) - set(entity_list['name'])
    if missing_entitys:
        print(f"{Year}年，以下项目在维度中不存在: {missing_entitys}")


    # 过滤缺失科目
    account_dim = Dimension('Account_lirun')
    account_list = pd.DataFrame(account_dim.query(expression="Base(#root,0)", fields=['name'], as_model=False))
    df = df[df['Account_lirun'].isin(account_list['name'])]

    # 找出缺失的科目
    missing_accounts = set(fore_df['Account_lirun']) - set(account_list['name'])
    if missing_accounts:
        print(f"{Year}年，以下科目在维度中不存在: {missing_accounts}")


    # 剔出指定列值为空的数据
    cols_to_check = ['Entity_GL', 'Account_lirun', 'Commercial', 'inc_stock', 'Pattern', 'Project_Type']
    # 删除这些列中任意一列为空的行
    df = df.dropna(subset=cols_to_check)


    expr_dict_forecast = {
        "Year": Year,
        "Scenario":'Forecast',
        "Entity_GL": "IDescendant(#root,0)",
        "Account_lirun": "IDescendant(#root,0)",
        "Period": "Noperiod",
        "Version": Version,
        "Measure": 'PerforAmt',
    }
    cube.insert_null(expr_dict_forecast)
    # cube.insert_null(expr_dict_forecast)
    cube.save(df,chunksize=200000)

def main(p1, p2):
    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    countAll = 0
    countSuccess = 0
    countError = 0
    countMsg = f"{start_time} 开始执行管报预测接入任务\n"

    try:
        # 统一获取全局参数
        Version = Variable('Variable').get('Edit_Ver')

        if 'Year' in p2 and p2['Year']:
            Year = str(p2['Year'])
        else:
            Year = Variable('Variable').get('BudYear')
            Year = str(int(Year)-1)

        cube = FinancialCube('rev_profit_cube')

        forecast_processing(p1, p2, Version, Year,cube)
        countSuccess = 1
        countAll = 1
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 管报预测接入处理完成\n"

    except Exception as e:
        countError = 1
        countAll = 1
        error_detail = traceback.format_exc()
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 管报预测接入失败: {str(e)}\n"
        countMsg += f"详细错误信息:\n{error_detail}\n"
        print(f"管报预测接入执行出错: {e}")
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
    para2 = {'Year':'2025'}
    main(para1, para2)

