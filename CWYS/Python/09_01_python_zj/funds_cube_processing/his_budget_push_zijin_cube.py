# -*- coding: utf-8 -*-
'''
@file    : his_budget_push_zijin_cube.py
@Time    :
@Author  : CHEN
@Software: PyCharm
@Desc    : 历史预算进资金模型
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


def actual_processing(p1, p2, Version, Year):

    
    # 获取业务预算预算数据
    budget_dt = DataTableMySQL('budget_data_zijin')
    cols = ['period', 'year', 'entity_cd', 'account_cd','commerical','data']



    # 筛选场景是0101(实际数)
    where = "year = '%s' " % Year

    budget_df = budget_dt.select(columns=cols,where = where)

    budget_df = budget_df.rename(columns={
        "period": "Period",
        "entity_cd": "Entity_FR",
        "year": "Year",
        "account_cd": "Account_zijin",
        # "commerical":"Commercial",
        # "counterparty": "Counterparty",
    })



    push_to_cube(budget_df,'budget_adjb',Version,Year)


def push_to_cube(df,Scenario,Version,Year):
    """推送数据到 rev_profit_cube"""

    entity_dim =  Dimension('Entity_FR')
    entity_df = pd.DataFrame(entity_dim.query(expression="Base(#root,0)", fields=['name','ud2'], as_model=False)).drop(['id','expectedName'],axis=1).rename(columns={
        'name':'Entity_FR',
        'ud2':'Commercial',})
    entity_df = entity_df.drop_duplicates(subset=['Entity_FR'])

    df = df.merge(entity_df, how='left', on='Entity_FR')
    df = df[df['Commercial'].notna() & (df['Commercial'] != '')]

    df['Counterparty'] = 'nocp'
    df['Comprehensive'] = 'nocompr'
    df['Scenario'] = Scenario
    df['Misc1'] = 'nomisc1'
    df['Misc2'] = 'nomisc2'
    df['Version'] = Version
    df['Measure'] = 'Expenses'



    # 4. 写入 Cube
    cube = FinancialCube('sub_fund_cube')

    # 删除cube

    fix = "Year{%s}->Version{%s}->Account_zijin{Base(CF00,0)}->" \
          "Entity_FR{Base(#root,0)}->Measure{Expenses}->Comprehensive{nocompr}->Counterparty{nocp}->" \
          "Scenario{%s}->Period{Base(TotalPeriod,0)}"\
    %(Year, Version,Scenario)
    cube.delete(expression=fix)

    # 保存数据
    cube.save(df, chunksize=200000)






def main(p1, p2):
    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    countAll = 0
    countSuccess = 0
    countError = 0
    countMsg = f"{start_time} 开始执行历史预算数接入任务\n"

    try:

        Version = Variable('Variable').get('Edit_Ver')

        if 'Year' in p2 and p2['Year']:
            Year = str(p2['Year'])
        else:
            Year = Variable('Variable').get('BudYear')

        actual_processing(p1, p2,Version,Year)
        countSuccess = 1
        countAll = 1
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 历史预算数接入处理完成\n"

    except Exception as e:
        countError = 1
        countAll = 1
        error_detail = traceback.format_exc()
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 历史预算数接入失败: {str(e)}\n"
        countMsg += f"详细错误信息:\n{error_detail}\n"
        print(f"历史预算数接入执行出错: {e}")
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
    para2 = {'Year':'2026'}
    main(para1, para2)

