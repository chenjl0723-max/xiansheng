# -*- coding: utf-8 -*-
'''
@file    : budget_push_cube.py
@Time    :
@Author  : CHEN
@Software: PyCharm
@Desc    : 预算数进利润预算模型
'''
from pandas import DataFrame

try:
    from CWYS._debug import para1, para2
    # print(para1)
except ImportError:
    para1 = para2 = {}
from deepfos.options import OPTION
import pandas as pd
from datetime import datetime
import traceback
import time
import os
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


def group_and_sum(df, group_cols, value_col='data'):
    """
    按指定维度汇总数值
    """
    if df.empty:
        return df

    # 确保 group_cols 中的列都存在
    exist_cols = [col for col in group_cols if col in df.columns]

    df = df.groupby(exist_cols, as_index=False)[value_col].sum()
    return df


def hr_processing(p1, p2):


    # 获取人力预算预算数据
    HR_dt = DataTableMySQL('budget_data_HR')
    cols = ['Entity_GL', 'Account_HR_cd', 'Year', 'Period',  'Scenario','comprehensive',
             'figure', 'Explan']
    # where = "Account_HR_cd != 'YW0901'"
    HR_df = HR_dt.select(columns=cols)


    # 人力科目映射
    account_map_dt = DataTableMySQL('budget_HR_mapping')
    account_cols = ['Account_HR_cd', 'comprehensive', 'Account_lirun_cd']

    account_map_df = account_map_dt.select(columns=account_cols).rename(columns={
        "Account_lirun_cd": "Account_lirun",})

    account_map_df['comprehensive'] = account_map_df['comprehensive'].str.split(',')

    account_map_df = account_map_df.explode('comprehensive')

    # 人力科目映射为管报科目
    HR_df = HR_df.merge(account_map_df[['Account_HR_cd','comprehensive','Account_lirun']], how='left')
    missing_accounts = HR_df[HR_df['Account_lirun'].isna()]['Account_HR_cd'].unique()

    # 把匹配失败的科目过滤掉
    HR_df = HR_df.dropna(subset=['Account_lirun'])
    print(f"以下科目在维度中不存在: {missing_accounts}")

    del HR_df['Account_HR_cd']
    del HR_df['comprehensive']

    # 金额科目处理
    hr_df = measure_process(HR_df)
    group_cols = ['Year', 'Period', 'Entity_GL', 'Account_lirun','Scenario','Measure','Version','Misc1','Misc2','Commercial']
    hr_df = group_and_sum(hr_df, group_cols)
    hr_df['Comprehensive'] = 'NoTax'


    '''
    # 人数科目单独处理
    where = "Account_HR_cd = 'YW0901'"
    YW0901_df = HR_dt.select(columns=cols,where=where).rename(columns={
        "Account_HR_cd": "Account_lirun",
        "comprehensive":"Comprehensive"})
    renshu_df = measure_process(YW0901_df,['Comprehensive'])


    # 合并人数和金额
    hr_budget_data = pd.concat([hr_df,renshu_df])
    '''

    # return hr_budget_data,account_map_df['Account_lirun']
    return hr_df,account_map_df['Account_lirun']


def measure_process(df,comprehensive=[]):
    # 预算金额
    hr_data = df[['Entity_GL', 'Account_lirun', 'Year', 'Period',  'Scenario','figure']+comprehensive].rename(columns={'figure':'data'})
    hr_data = hr_data[hr_data['data'].notna()]
    hr_data['Measure'] = 'Expenses'

    # 预算变更说明
    hr_Explan = df[['Entity_GL', 'Account_lirun', 'Year', 'Period', 'Scenario','Explan']+comprehensive].rename(columns={'Explan':'data'})
    hr_Explan = hr_Explan[hr_Explan['data'].notna()]
    hr_Explan['Measure'] = 'Explain'

    # 合并预算金额和预算变更说明
    hr_budget_data = pd.concat([hr_data, hr_Explan])

    # 补充维度列
    Version = Variable('Variable').get('Edit_Ver')
    hr_budget_data['Version'] = Version
    hr_budget_data['Misc1'] = 'Nomisc1'
    hr_budget_data['Misc2'] = 'Nomisc2'
    # hr_budget_data['Commercial'] = 'Nomisc3'


    return hr_budget_data





def push_processing(df,account_scope):

    # 获取变量年
    Year = Variable('Variable').get('BudYear')
    Last_year =str(int(Year)-1)

    Version = Variable('Variable').get('Edit_Ver')
    # df['Version'] = Version

    # 过滤不需要的科目
    account_dim = Dimension('Account_lirun')
    account_list = pd.DataFrame(account_dim.query(expression="Base(#root,0)", fields=['name'], as_model=False))
    df = df[df['Account_lirun'].isin(account_list['name'])]

    # 关联业态
    entity_dim =  Dimension('Entity_GL')
    entity_df = pd.DataFrame(entity_dim.query(expression="Base(#root,0)", fields=['name','ud7'], as_model=False)).rename(columns={
        'name':'Entity_GL',
        'ud7':'Commercial',})
    df = df.merge(entity_df, how='left', on='Entity_GL')
    df = df[df['Entity_GL'].isin(entity_df['Entity_GL'])]
    del df['id']
    del df['expectedName']

    cube = FinancialCube('sub_profit_cube')
    expr_dict_budget = {
        "Year": Year,
        "Scenario":'Budget',
        "Entity_GL": "IDescendant(#root,0)",
        "Account_lirun": list(account_scope),
        "Comprehensive":['NoTax','Base(Staff_Classification,0)'],
        "Version": Version,
    }
    expr_dict_forecast = {
        "Year": Last_year,
        "Scenario":'Forecast',
        "Entity_GL": "IDescendant(#root,0)",
        "Account_lirun": list(account_scope),
        "Comprehensive": ['NoTax','Base(Staff_Classification,0)'],
        "Version": Version,
    }

    # 清数
    cube.insert_null(expr_dict_budget)
    cube.insert_null(expr_dict_forecast)
    # 存数
    cube.save(df,chunksize=50000)

def main(p1, p2):
    # hr_budget_data,account_scope = hr_processing(p1, p2)
    #
    # # 写入财务预算分析模型
    # push_processing(hr_budget_data,account_scope)


    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    countAll = 0
    countSuccess = 0
    countError = 0
    countMsg = f"{start_time} 开始执行人力预算预算数接入任务\n"

    try:

        hr_budget_data, account_scope = hr_processing(p1, p2)

        # 写入财务预算分析模型
        push_processing(hr_budget_data, account_scope)
        countSuccess = 1
        countAll = 1
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 人力预算预算数接入处理完成\n"

    except Exception as e:
        countError = 1
        countAll = 1
        error_detail = traceback.format_exc()
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 人力预算预算数接入失败: {str(e)}\n"
        countMsg += f"详细错误信息:\n{error_detail}\n"
        print(f"人力预算预算数推送执行出错: {e}")
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
    main(para1, para2)


