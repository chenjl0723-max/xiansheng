# -*- coding: utf-8 -*-
'''
@file    : lirun_push_zijin.py
@Desc    : 利润预算进资金预算
'''

try:
    from CWYS.__debug import para1, para2
except ImportError:
    para1 = para2 = {}

import pandas as pd
import traceback
import time
import os
import json
from datetime import datetime

from deepfos.element.datatable import DataTableMySQL
from deepfos.element.finmodel import FinancialCube
from deepfos.element.variable import Variable
from deepfos.element.dimension import Dimension
from deepfos.element.pyscript import PythonScript


def fix_scenarios(df, scenario_cols=None):
    """
    通用处理函数，支持有Tax和无Tax两种情况
    """
    if scenario_cols is None:
        scenario_cols = ['Actual', 'Forecast', 'Budget']

    # 判断是否有 Tax 列
    has_tax = 'Tax' in df.columns

    result = {}

    for scenario in scenario_cols:
        if scenario not in df.columns:
            continue

        # 根据是否有 Tax 选择需要的列
        if has_tax:
            temp = df[['Account_lirun', scenario, 'Tax']].copy()
        else:
            temp = df[['Account_lirun', scenario]].copy()

        temp = temp.rename(columns={scenario: 'Period'})

        # 过滤有效数据
        temp = temp.dropna(subset=['Period'])
        temp = temp[temp['Period'].astype(str).str.strip() != '-']
        temp = temp[temp['Period'].astype(str).str.strip() != '']

        temp['Scenario'] = scenario

        # 只在有 Tax 列时才处理 Tax
        if has_tax:
            temp['Tax'] = temp['Tax'].fillna('NoTax')
            temp = temp[['Account_lirun', 'Scenario', 'Period', 'Tax']]
        else:
            temp = temp[['Account_lirun', 'Scenario', 'Period']]

        # 去重
        temp = temp.drop_duplicates().reset_index(drop=True)

        result[scenario] = temp
        tax_status = '有' if has_tax else '无'
        print(f"{scenario:8} : {len(temp):4} 条记录 （Tax维度: {tax_status}）")

    return result


def main_processing(p1, p2,Version,Year,Entity,cube):

    """获取映射表"""
    dt_mapping = DataTableMySQL('subject_mapping')
    df = dt_mapping.select(columns=['profit_subj_code','fund_subj_code','Actual','Forecast','Budget','Tax'])

    # 创建两个DataFrame，分别基于profit_subj_code和fund_subj_code
    df_profit = df[['profit_subj_code', 'Actual', 'Forecast', 'Budget']].copy()
    df_profit = df_profit.rename(columns={'profit_subj_code': 'Account_lirun'})

    df_fund = df[['fund_subj_code', 'Actual', 'Forecast', 'Budget']].copy()
    df_fund = df_fund.rename(columns={'fund_subj_code': 'Account_lirun'})

    # 合并两个DataFrame
    df_combined = pd.concat([df_profit, df_fund], ignore_index=True)

    # 删除Account_lirun为空的行
    df_del_fix = df_combined.dropna(subset=['Account_lirun']).drop_duplicates()



    # 2. profit_subj_code 作为主要 account（如果为空则用 fund_subj_code）
    df['Account_lirun'] = df['profit_subj_code'].fillna(df['fund_subj_code'])

    # 根据映射表中的数据，筛选出有效的场景
    result = fix_scenarios(df)
    result_del = fix_scenarios(df_del_fix)

    account_mapping = df.copy()


    # 获取实际数场景筛选条件
    pov_list = df_json(result.get('Actual'),'Actual')
    df_actual = query_lirun_cube(pov_list,str(int(Year) - 1),Version,Entity,cube)

    # 获取实际数场景删除条件
    pov_list = df_json(result_del.get('Actual'),'Actual')
    del_zijin_cube(pov_list,'Actual_adjb',str(int(Year) - 1),Version,Entity)

    # 实际数科目映射+虚拟项目映射+汇总+写入资金模型
    df_actual = mapping_and_group(df_actual,account_mapping)
    push_to_cube(df_actual,'Actual_adjb')



    # 获取预测数场景筛选条件
    pov_list = df_json(result.get('Forecast'),'Forecast')
    df_forecast = query_lirun_cube(pov_list, str(int(Year) - 1), Version,Entity, cube)

    # 获取预测数场景删除条件
    pov_list = df_json(result_del.get('Forecast'),'Forecast')
    del_zijin_cube(pov_list,'Forecast',str(int(Year) - 1),Version,Entity)

    # 预测数科目映射+虚拟项目映射+汇总+写入资金模型
    df_forecast = mapping_and_group(df_forecast,account_mapping)
    push_to_cube(df_forecast,'Forecast')



    # 获取预算数场景筛选条件
    pov_list = df_json(result.get('Budget'),'Budget')
    df_budget = query_lirun_cube(pov_list,Year,Version,Entity,cube)

    # 获取预算数场景删除条件
    pov_list = df_json(result_del.get('Budget'),'Budget')
    del_zijin_cube(pov_list,'budget_adjb',Year,Version,Entity,)

    # 预算数科目映射+虚拟项目映射+汇总+写入资金模型
    df_budget = mapping_and_group(df_budget,account_mapping)
    push_to_cube(df_budget,'budget_adjb')





def df_json(df, Scenario):
    """
    根据 df 是否包含 Tax 列，动态生成 JSON
    """
    # 判断是否有 Tax 列
    has_tax = 'Tax' in df.columns

    if has_tax:
        groups = df.groupby(['Period', 'Tax'])
    else:
        groups = df.groupby('Period')

    result_jsons = []

    for group_key, group in groups:
        accounts = group['Account_lirun'].dropna().unique().tolist()

        json_obj = {
            "Account_lirun": accounts,
            "Scenario": Scenario,
            "Period": [p.strip() for p in str(group_key[0] if has_tax else group_key).split(',') if p.strip()]
        }

        # 如果有 Tax 列，才加入 Comprehensive
        if has_tax:
            tax_value = group_key[1]
            json_obj["Comprehensive"] = tax_value   # 或 "Tax": tax_value，根据你的 Cube 维度名

        result_jsons.append(json_obj)
        print(f"[{Scenario}] Period='{group_key}' → {len(accounts)} 个科目")

    return result_jsons

def query_lirun_cube(pov_list,Year,Version,Entity,cube):
    df_all =  pd.DataFrame()
    for pov in pov_list:

        print(pov)
        Account_lirun =  ';'.join(pov.get('Account_lirun'))
        Scenario =  pov.get('Scenario')
        Period =  ';'.join(pov.get('Period'))
        Tax = pov.get('Comprehensive')

        fix = "Year{%s}->Version{%s}->Comprehensive{%s}->" \
              "Entity_GL{%s}->Measure{Expenses}->" \
              "Account_lirun{%s}->Scenario{%s}->Period{%s}"\
        %(Year, Version,Tax,Entity,Account_lirun,Scenario,Period)
        df = cube.query(expression=fix, compact=False)
        if not df.empty:
            df_all = pd.concat([df_all,df],ignore_index=True)

    print(df_all)
    return df_all

def del_zijin_cube(pov_list,Scenario,Year,Version,Entity):
    cube = FinancialCube('sub_fund_cube')
    # df_all =  pd.DataFrame()
    for pov in pov_list:

        print(pov)
        Account_lirun =  ';'.join(pov.get('Account_lirun'))

        Period =  ';'.join(pov.get('Period'))


        # Tax = pov.get('Comprehensive')

        fix = "Year{%s}->Version{%s}->Comprehensive{nocompr}->" \
              "Entity_FR{%s}->Measure{Expenses}->" \
              "Account_zijin{%s}->Scenario{%s}->Period{%s}->Counterparty{nocp}->Misc1{nomisc1}->Misc2{nomisc2}"\
        %(Year, Version,Entity,Account_lirun,Scenario,Period)
        cube.delete(expression=fix)




def mapping_and_group(df,account_mapping):
    # 科目映射+虚拟项目转实体项目+汇总金额
    if df.empty:
        return df

    # 将利润科目数据取出
    # 将资金科目数据取出
    df_CF = pd.merge(df, account_mapping[['Account_lirun','fund_subj_code']], how='left', on=['Account_lirun'])
    # 保留fund_subj_code不为空的行
    df_CF = df_CF[pd.notna(df_CF['fund_subj_code'])]
    # 将fund_subj_code重命名为Account_lirun
    df_CF = df_CF.drop(columns=['Account_lirun'])
    df_CF = df_CF.rename(columns={'fund_subj_code': 'Account_lirun'})

    df = pd.concat([df,df_CF],ignore_index=True)

    XN_mapping = DataTableMySQL('pl_virt_proj_fund_real_map')
    df_xn = XN_mapping.select(columns=['year','pl_virt_proj_code','fund_real_proj_code']).rename(columns={'pl_virt_proj_code':'Entity_GL','year':'Year'})

    df = pd.merge(df, df_xn, how='left', on=['Entity_GL','Year'])
    # 如果fund_real_proj_code不为空，则用其替换Entity_GL，否则保持原Entity_GL
    df['Entity_GL'] = df.apply(
        lambda row: row['fund_real_proj_code'] if pd.notna(row['fund_real_proj_code']) else row['Entity_GL'],
        axis=1
    )
    # 删除合并后多余的列
    df = df.drop(columns=['fund_real_proj_code'])

    if df.empty:
        return df

    # 获取除了 'data' 列之外的所有列名
    group_cols = [col for col in df.columns if col != 'data']
    # exist_cols = [col for col in group_cols if col in df.columns]
    df = df.groupby(group_cols, as_index=False)['data'].sum()
    return df


def push_to_cube(df,Scenario):
    """推送数据到 rev_profit_cube"""
    if df.empty:
        return
    df = df.rename(columns={'Entity_GL':'Entity_FR','Account_lirun':'Account_zijin'})
    # 替换Period列中的'Sepmtd'为'Sep'
    df['Period'] = df['Period'].replace('Sepmtd', 'Sep')
    df['Scenario'] = Scenario
    df['Comprehensive'] = 'nocompr'
    df['Counterparty'] = 'nocp'
    # 1. 过滤维度中存在的成员
    entity_dim = Dimension('Entity_FR')
    entity_list = pd.DataFrame(entity_dim.query("Base(#root,0)", fields=['name'], as_model=False))
    df = df[df['Entity_FR'].isin(entity_list['name'].tolist())]

    account_dim = Dimension('Account_zijin')
    account_list = pd.DataFrame(account_dim.query("Base(#root,0)", fields=['name'], as_model=False))
    df = df[df['Account_zijin'].isin(account_list['name'].tolist())]


    # 4. 写入 Cube
    cube = FinancialCube('sub_fund_cube')

    # 保存数据
    cube.save(df, chunksize=200000)




def main(p1, p2):
    # 统一获取全局参数
    Version = Variable('Variable').get('Edit_Ver')

    if 'Year_wb1' in p2 and p2['Year_wb1']:
            Year = str(p2['Year_wb1'])
    else:
        Year = Variable('Variable').get('BudYear')

    if 'Entity_FR_wb1' in p2 and p2['Entity_FR_wb1']:
        Entity = str(p2['Entity_FR_wb1'])
    else:
        Entity = 'Base(#root,0)'

    cube = FinancialCube('sub_profit_cube')
    main_processing(p1, p2, Version, Year, Entity, cube)

    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    countAll = countSuccess = countError = 0
    countMsg = f"{start_time} 开始执行利润预算进资金预算任务\n"

    try:
        # 统一获取全局参数
        Version = Variable('Variable').get('Edit_Ver')
        Version = 'V4'

        if 'Year_wb1' in p2 and p2['Year_wb1']:
            Year = str(p2['Year_wb1'])
        else:
            Year = Variable('Variable').get('BudYear')

        if 'Entity_FR_wb1' in p2 and p2['Entity_FR_wb1']:
            Entity = str(p2['Entity_FR_wb1'])
        else:
            Entity = 'Base(#root,0)'

        cube = FinancialCube('sub_profit_cube')
        main_processing(p1, p2, Version, Year,Entity,cube)
        countAll = countSuccess = 1
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 利润预算进资金预算处理完成\n"
    except Exception as e:
        countError = 1
        countAll = 1
        error_detail = traceback.format_exc()
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 利润预算进资金预算处理失败: {str(e)}\n"
        countMsg += f"详细错误:\n{error_detail}\n"
        print(f"执行出错: {e}")
        traceback.print_exc()

    # ====================== 写入日志 ======================
    ele_name = os.path.basename(__file__)
    ele_path = os.path.dirname(os.path.abspath(__file__))

    try:
        sync_log = PythonScript(element_name='pyLog', path='/09_Python/common', should_log=True)
        sync_log.run(
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
        print("日志记录成功！")
    except Exception as log_e:
        print(f"日志记录异常: {log_e}")

    return countError == 0


# ==================== 本地调试 ====================
if __name__ == '__main__':
    para2 = {'elementName': 'found_budget_main', 'folderId': 'DIRcc223f9bef26', 'sheetName': '资金预算汇总(跳转明细)', 'sheetId': 'SHT5c5b6504ff19490e8a37fb4d43380264', 'Year_wb1': '2026', 'Entity_FR_wb1': 'Base(#root,0)', 'Version_wb1': 'V1', 'Commercial_wb1': 'YT020101'}  # 修改这里可测试不同年份
    main(para1, para2)