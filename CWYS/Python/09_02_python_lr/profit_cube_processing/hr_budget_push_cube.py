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
    from CWYS.__debug import para1, para2
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

    # 分离预算和预测数据
    df_budget = hr_df[hr_df['Scenario'] == 'Budget'].copy()
    df_forecast = hr_df[hr_df['Scenario'] == 'Forecast'].copy()

    # return df_budget, account_map_df['Account_lirun']
    # 处理预测数（汇总全年→减实际→分摊到预测月）
    df_forecast = process_forecast_with_actuals(df_forecast, df_forecast['Account_lirun'])

    # 合并预算和预测
    hr_df = pd.concat([df_budget, df_forecast], ignore_index=True)

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
    hr_budget_data['Misc1'] = 'nomisc1'
    hr_budget_data['Misc2'] = 'nomisc2'
    # hr_budget_data['Commercial'] = 'Nomisc3'


    return hr_budget_data





def process_forecast_with_actuals(df_forecast, account_scope):
    """
    处理预测数：
    1. 把1-12月预测数汇总得到全年预测
    2. 根据场景变量取1-9月/1-10月/1-11月实际数
    3. 用全年预算(预测) - 实际数合计 = 剩余数
    4. 把剩余数分摊到预测月份中
    """
    if df_forecast is None or df_forecast.empty:
        return df_forecast

    Year = Variable('Variable').get('BudYear')
    # Year ='2026'
    Last_year = str(int(Year) - 1)
    Version = Variable('Variable').get('Edit_Ver')

    # 读取场景变量
    sc_10 = Variable('Variable').get('10_scenario')
    sc_11 = Variable('Variable').get('11_scenario')
    sc_12 = Variable('Variable').get('12_scenario')

    # 确定实际数月份范围和预测分摊月份
    # sc_10 决定10月是否为预测月：如果有值，说明9月数据已出，10月是预测月
    # sc_11 决定11月，sc_12 决定12月
    # 默认3个预测月，实际取1-9月
    actual_months = [str(i) for i in range(1, 10)]
    forecast_months = ['10', '11', '12']

    # 10月场景变为Actual时，实际取1-10月，预测11、12月
    if sc_10 == 'Actual':
        actual_months = [str(i) for i in range(1, 11)]
        forecast_months = ['11', '12']

    # 11月场景变为Actual时，实际取1-11月，预测12月
    if sc_11 == 'Actual':
        actual_months = [str(i) for i in range(1, 12)]
        forecast_months = ['12']

    # 12月场景也变为Actual时，全部是实际，不插入预测数
    if sc_12 == 'Actual':
        actual_months = [str(i) for i in range(1, 13)]
        forecast_months = []

    # 所有月都是实际，无需插入预测数
    if not forecast_months:
        print("所有场景均为Actual，不插入预测数")
        return pd.DataFrame()

    print(f"预测处理: 实际月={actual_months}, 预测月={forecast_months}")
    print(f"场景变量: sc_10={sc_10}, sc_11={sc_11}, sc_12={sc_12}")

    # 只处理金额数据（Measure=Expenses），说明文字不动
    df_expenses = df_forecast[df_forecast['Measure'] == 'Expenses'].copy()
    df_explain = df_forecast[df_forecast['Measure'] == 'Explain'].copy()

    if df_expenses.empty:
        return df_forecast

    # 只处理上年的预测数
    df_expenses = df_expenses[df_expenses['Year'] == Last_year].copy()
    df_explain = df_explain[df_explain['Year'] == Last_year].copy()

    if df_expenses.empty:
        return df_forecast

    # 汇总维度（去掉Period，保留Year）
    group_dims = ['Year', 'Entity_GL', 'Account_lirun', 'Scenario', 'Measure',
                  'Version', 'Misc1', 'Misc2', 'Comprehensive']

    # 1. 汇总全年预测（1-12月求和）
    df_annual = df_expenses.groupby(group_dims, as_index=False)['data'].sum()
    df_annual = df_annual.rename(columns={'data': 'annual_total'})

    # 2. 查询实际数
    cube = FinancialCube('sub_profit_cube')
    account_list = list(df_annual['Account_lirun'].dropna().unique())


    # 构建实际数查询表达式
    accounts_str = ';'.join([str(a) for a in account_list if a])
    periods_str = ';'.join(actual_months)

    fix_actual = (
        f"Year{{{Last_year}}}->Version{{{Version}}}->"
        f"Comprehensive{{NoTax;Base(Staff_Classification,0)}}->"
        f"Entity_GL{{Base(#root,0)}}->"
        f"Measure{{Expenses}}->"
        f"Account_lirun{{{accounts_str}}}->"
        f"Scenario{{Actual}}->Period{{{periods_str}}}"
    )

    print(f"查询实际数: {Last_year}年 {periods_str}月")
    df_actual = cube.query(fix_actual, compact=False)

    if not df_actual.empty:
        df_actual = df_actual.groupby(group_dims, as_index=False)['data'].sum()
        df_actual = df_actual.rename(columns={'data': 'actual_total'})
        del df_actual['Scenario']
        # 合并实际数
        df_annual = df_annual.merge(df_actual,  how='left')
    else:
        df_annual['actual_total'] = 0

    df_annual['actual_total'] = df_annual['actual_total'].fillna(0)

    # 3. 计算剩余数 = 全年预测 - 实际数合计
    df_annual['remaining'] = df_annual['annual_total'] - df_annual['actual_total']

    # 4. 分摊到预测月份
    n_forecast = len(forecast_months)
    df_annual['per_month'] = df_annual['remaining'] / n_forecast

    # 展开到每个月
    forecast_rows = []
    for _, row in df_annual.iterrows():
        for period in forecast_months:
            new_row = row.copy()
            new_row['Period'] = period
            new_row['data'] = row['per_month']
            forecast_rows.append(new_row)

    df_result = pd.DataFrame(forecast_rows)

    # 删除临时列
    for col in ['annual_total', 'actual_total', 'remaining', 'per_month']:
        if col in df_result.columns:
            df_result = df_result.drop(columns=[col])

    # 合并回说明文字
    result = pd.concat([df_result, df_explain], ignore_index=True)

    print(f"预测数处理完成: {len(df_result)} 条金额, {len(df_explain)} 条说明")
    return result


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
    entity_df = pd.DataFrame(entity_dim.query(expression="Base(D000001,0)", fields=['name','ud7'], as_model=False)).rename(columns={
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
        "Entity_GL": "IDescendant(D000001,0)",
        "Account_lirun": list(df['Account_lirun'].dropna().unique()),
        "Comprehensive":['NoTax','Base(Staff_Classification,0)'],
        "Version": Version,
    }
    expr_dict_forecast = {
        "Year": Last_year,
        "Scenario":'Forecast',
        "Entity_GL": "IDescendant(D000001,0)",
        "Account_lirun": list(df['Account_lirun'].dropna().unique()),
        "Comprehensive": ['NoTax','Base(Staff_Classification,0)'],
        "Version": Version,
    }

    # 清数
    cube.delete(expr_dict_budget)
    cube.delete(expr_dict_forecast)
    # 存数
    cube.save(df,chunksize=200000)

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


