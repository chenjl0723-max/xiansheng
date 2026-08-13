# -*- coding: utf-8 -*-
'''
@file    : actual_push_cube.py
@Time    :
@Author  : CHEN
@Software: PyCharm
@Desc    : 实际数进利润预算模型
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


def actual_processing(p1, p2,year,Version):

    
    # 获取业务预算预算数据
    dt = DataTableMySQL('pl_adjust_data')
    cols = ['period_code', 'year_code', 'mgmt_entity', 'profit_acct','scenario','data']



    # 筛选场景是0101(实际数)
    where = "year_code = '%s' " % year

    df = dt.select(columns=cols,where = where)

    # 按关键维度汇总数据，假设需要汇总的维度是 'period_code', 'year_code', 'mgmt_entity', 'profit_acct', 'scenario'
    group_cols = ['period_code', 'year_code', 'mgmt_entity', 'profit_acct', 'scenario']
    df = group_and_sum(df, group_cols, value_col='data')


    df = df.rename(columns={
        "period_code": "Period",
        "mgmt_entity": "Entity_GL",
        "year_code": "Year",
        "profit_acct": "Account_lirun",
        # "commerical":"Commercial",
        "scenario": "Scenario",
    })

# 分离场景 0101 (实际数) 和 0201 (预算数)
    act_df = df[df['Scenario'] == '0101'].copy()
    if not act_df.empty:
        tax_rate_processing_act(act_df,year,Version)

    budget_df = df[df['Scenario'] == '0201'].copy()
    if not budget_df.empty:
        tax_rate_processing_budget(budget_df, year,Version)





def tax_rate_processing_act(act_df, Year,Version):
    """实际数税率处理 - 含税 = 不含税 * (1 + 税率)"""
    act_df = act_df.copy()
    act_df['Comprehensive'] = 'NoTax'
    # Version = Variable('Variable').get('Edit_Ver')

    cube = FinancialCube('sub_profit_cube')
    fix_rate = (
        "Year{%s}->Scenario{Actual}->Version{%s}->Period{Base(TotalPeriod,0)}->Comprehensive{Taxrate}->"
        "Entity_GL{Base(#root,0)}->Measure{Expenses}->Account_lirun{Base(PL60,0);YW0104;YW0205;YW020801;YW020802;YW0206;YW0201;YW0203;YW0215}->"
        "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}"
    ) % (Year, Version)

    # 获取税率
    df_rate = cube.query(fix_rate, compact=False)

    if df_rate.empty:
        print(f"警告: {Year}年实际数未找到任何税率数据，将使用 不含税 = 含税")
        df_all = act_df.copy()
        df_all['Comprehensive'] = 'Tax'
        df_all = pd.concat([act_df, df_all])
        expr_dict_actual = {
            "Year": Year,
            "Scenario":"Actual",
            "Entity_GL": "IDescendant(#root,0)",
            "Account_lirun": "IDescendant(#root,0)",
            "Comprehensive": ['Tax', 'NoTax'],
            "Period": "Base(TotalPeriod,0)",
            "Version": Version,
        }
        cube.insert_null(expr_dict_actual)
        df_all['Version'] = 'V4'
        push_processing(df_all, Year,'Actual')
        return

    # 合并税率（inner 改成 left，便于发现未匹配记录）
    df_act_tax = pd.merge(
        act_df,
        df_rate[['Account_lirun', 'Period', 'Year', 'Entity_GL', 'data']].rename(columns={"data": "rate_data"}),
        how='left',
        on=['Account_lirun', 'Period', 'Year', 'Entity_GL']
    )

    # 处理匹配不上税率的情况：含税 = 不含税
    no_match = df_act_tax['rate_data'].isna()
    if no_match.any():
        print(f"警告: {Year}年实际数有 {no_match.sum()} 条记录未匹配到税率，将含税设为不含税")

    df_act_tax.loc[no_match, 'rate_data'] = 0.0          # 未匹配时税率视为0
    df_act_tax['data'] = df_act_tax['data'] * (1 + df_act_tax['rate_data'])
    df_act_tax['Comprehensive'] = 'Tax'
    df_act_tax = df_act_tax.drop(columns=['rate_data'], errors='ignore')

    df_all = pd.concat([act_df, df_act_tax], ignore_index=True)
    df_all['Version'] = Version
    expr_dict_actual = {
        "Year": Year,
        "Scenario": "Actual",
        "Entity_GL": "IDescendant(#root,0)",
        "Account_lirun": "IDescendant(#root,0)",
        "Comprehensive": ['Tax', 'NoTax'],
        "Period": "Base(TotalPeriod,0)",
        "Version": Version,
    }
    cube.insert_null(expr_dict_actual)
    push_processing(df_all, Year,'Actual')


def tax_rate_processing_budget(budget_df, Year,Version):
    """预算数税率处理 - 含税 = 不含税 * (1 - 税率)"""
    budget_df = budget_df.copy()
    budget_df['Comprehensive'] = 'NoTax'
    # Version = Variable('Variable').get('Edit_Ver')

    cube = FinancialCube('sub_profit_cube')
    fix_rate = (
        "Year{%s}->Scenario{Budget}->Version{%s}->Period{Base(TotalPeriod,0)}->Comprehensive{Taxrate}->"
        "Entity_GL{Base(#root,0)}->Measure{Expenses}->Account_lirun{Base(PL60,0)}->"
        "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}"
    ) % (Year, Version)

    # 获取税率
    df_rate = cube.query(fix_rate, compact=False)

    if df_rate.empty:
        print(f"警告: {Year}年预算数未找到任何税率数据，将使用 不含税 = 含税")
        df_all = budget_df.copy()
        df_all['Comprehensive'] = 'Tax'

        df_all = pd.concat([budget_df, df_all])
        df_all['Version'] = 'V4'
        expr_dict_budget = {
            "Year": Year,
            "Scenario":"Budget",
            "Entity_GL": "IDescendant(#root,0)",
            "Account_lirun": "IDescendant(#root,0)",
            "Comprehensive": ['Tax', 'NoTax'],
            "Period": "Base(TotalPeriod,0)",
            "Version": "V4",
        }
        cube.insert_null(expr_dict_budget)
        push_processing(df_all, Year,'Budget')
        return

    # 合并税率（left join）
    df_budget_tax = pd.merge(
        budget_df,
        df_rate[['Account_lirun', 'Period', 'Year', 'Entity_GL', 'data']].rename(columns={"data": "rate_data"}),
        how='left',
        on=['Account_lirun', 'Period', 'Year', 'Entity_GL']
    )

    # 处理匹配不上税率的情况：含税 = 不含税
    no_match = df_budget_tax['rate_data'].isna()
    if no_match.any():
        print(f"警告: {Year}年预算数有 {no_match.sum()} 条记录未匹配到税率，将含税设为不含税")

    df_budget_tax.loc[no_match, 'rate_data'] = 0.0          # 未匹配时税率视为0
    df_budget_tax['data'] = df_budget_tax['data'] * (1 + df_budget_tax['rate_data'])
    df_budget_tax['Comprehensive'] = 'Tax'
    df_budget_tax = df_budget_tax.drop(columns=['rate_data'], errors='ignore')

    df_all = pd.concat([budget_df,  df_budget_tax], ignore_index=True)  # 修正变量名
    df_all['Version'] = 'V4'
    expr_dict_budget = {
        "Year": Year,
        "Scenario": "Budget",
        "Entity_GL": "IDescendant(#root,0)",
        "Account_lirun": "IDescendant(#root,0)",
        "Comprehensive": ['Tax', 'NoTax'],
        "Period": "Base(TotalPeriod,0)",
        "Version": "V4",
    }
    cube.insert_null(expr_dict_budget)
    push_processing(df_all, Year,'Budget')


def push_processing(act_df,year,Scenario):



    # 过滤缺失项目得数据
    entity_dim = Dimension('Entity_GL')
    entity_list = pd.DataFrame(entity_dim.query(expression="Base(#root,0)", fields=['name'], as_model=False))
    df = act_df[act_df['Entity_GL'].isin(entity_list['name'])]

    # 找出缺失的科目
    missing_entitys = set(act_df['Entity_GL']) - set(entity_list['name'])
    if missing_entitys:
        print(f"{year}年，以下项目在维度中不存在: {missing_entitys}")


    # 过滤缺失科目
    account_dim = Dimension('Account_lirun')
    account_list = pd.DataFrame(account_dim.query(expression="Base(#root,0)", fields=['name'], as_model=False))
    df = df[df['Account_lirun'].isin(account_list['name'])]

    # 找出缺失的科目
    missing_accounts = set(act_df['Account_lirun']) - set(account_list['name'])
    if missing_accounts:
        print(f"{year}年，以下科目在维度中不存在: {missing_accounts}")

    # 关联业态
    entity_dim =  Dimension('Entity_GL')
    entity_df = pd.DataFrame(entity_dim.query(expression="Base(D000001,0)", fields=['name','ud7'], as_model=False)).drop(['id','expectedName'],axis=1).rename(columns={
        'name':'Entity_GL',
        'ud7':'Commercial',})
    df = df.merge(entity_df, how='left', on='Entity_GL')

    # 过滤Commercial为空的数据
    df = df[df['Commercial'].notna() & (df['Commercial'] != '')]

    # df['data'] = df['data'] / 10000

    # 补充列
    df['Scenario'] = Scenario
    df['Measure'] = 'Expenses'
    df.loc[df['Account_lirun'].isin(['YW08020001', 'YW08020002']), 'Measure'] = 'Rate'

    # df['Version'] = Version
    df['Misc1'] = 'nomisc1'
    df['Misc2'] = 'nomisc2'


    cube = FinancialCube('sub_profit_cube')


    cube.save(df,chunksize=200000)


def XYT_processing(p1,p2,year,Version):


    # 进入小业态系统
    p1['app'] = 'eemapg012'
    OPTION.api.header = p1

    cube = FinancialCube('S_Cube')

    act_query = (
            "Year{%s}->Scenario{Actual}->Version{Y1}->Entity{Base(#root,0)}->Period{Base(TotalPeriod,0)}->"
            "Material{Nomaterial}->Tax{Tax}->Account{SYW020103;SYW020105;SYW020107;SYW020102;SYW020106;SYW020505}->Department{Operation}->"
            "Measure{Expenses}->Format{NoFormat}->Project_Type{NoProject_Type}->PM_Chars{NoPM_Chars}->"
            "Misc1{Nomisc1}->Misc2{Nomisc2}->Misc3{Nomisc3}"
            % year)

    act_df = cube.query(act_query, compact=False)

    # 定义科目映射字典
    account_mapping = {
        'SYW020103': 'YW0104',
        'SYW020105': 'YW0205',
        'SYW020107': 'YW0206',
        'SYW020102': 'YW0201',
        'SYW020106': 'YW0203',
        'SYW020505': 'YW0215'
    }
    # 根据映射字典替换Account列的值
    act_df['Account'] = act_df['Account'].replace(account_mapping)

    act_df['Comprehensive'] = 'NoTax'
    act_df['Version'] = Version
    # 只保留组织、科目、期间、年和data列
    act_df = act_df[['Entity', 'Account', 'Period', 'Year', 'data', 'Comprehensive','Version']].rename(columns={
        "Entity":"Entity_GL",
        "Account":"Account_lirun",

    })


    # 进入财务预算系统
    p1['app'] = 'eemapg016'
    OPTION.api.header = p1
    push_processing(act_df, year,'Actual')



def main(p1, p2):
    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    countAll = 0
    countSuccess = 0
    countError = 0
    countMsg = f"{start_time} 开始执行实际数接入任务\n"

    try:

        Version = Variable('Variable').get('Edit_Ver')
        if 'Year' in p2 and p2['Year']:
            year = str(p2['Year'])
        else:
            BudYear = Variable('Variable').get('BudYear')
            year = str(int(BudYear) - 1)
        actual_processing(p1, p2,year,Version)

        # 取小业态基础生产数据写入利润预算实际数

        XYT_processing(p1,p2,year,Version)

        countSuccess = 1
        countAll = 1
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 实际数接入处理完成\n"

    except Exception as e:
        countError = 1
        countAll = 1
        error_detail = traceback.format_exc()
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 实际数接入失败: {str(e)}\n"
        countMsg += f"详细错误信息:\n{error_detail}\n"
        print(f"实际数推送执行出错: {e}")
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

