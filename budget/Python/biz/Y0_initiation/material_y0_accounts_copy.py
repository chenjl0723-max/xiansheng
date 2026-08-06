# -*- coding: utf-8 -*-
'''
@file    : material_y0_accounts_copy.py
@Author  : cjl
@Desc    : 原材料Y0科目复制脚本
          将上年实际数（YW0307;YW0308;YW0317;YW0311;YW0302;YW0303）
          复制为当年Y0预算数
'''

try:
    from budget._debug import para1, para2
except ImportError:
    para1 = para2 = {}
from deepfos.options import OPTION
import pandas as pd
from deepfos.element.finmodel import FinancialCube
from deepfos.element.variable import Variable


def copy_accounts_to_y0(p1, p2, Entity, year):
    """
    将上年实际数复制为当年Y0预算数
    :param p1: 环境参数
    :param p2: 业务参数
    :param Entity: 实体
    :param year: 预算年
    """
    cube = FinancialCube('WS_cube')
    last_year = str(int(year) - 1)
    year_2 = str(int(year) - 2)

    # 要复制的科目列表
    accounts = ['YW0307', 'YW0308', 'YW0317', 'YW0311', 'YW0303']

    # =========================================================
    # 1. 从 cube 取上年实际数（Y1版本）
    # =========================================================
    fix_actual = (
        f"Entity{{{Entity}}}->"
        f"Material{{Base(MQ01,0);Base(MQ03,0);Base(MQ05,0)}}->"
        f"Department{{Operation}}->Version{{Y1}}->Allocation{{Original}}->"
        f"Misc1{{Base(Centralized_Agreement,0)}}->Misc2{{Nomisc2}}->"
        f"Account{{{';'.join(accounts)}}}->Scenario{{Actual}}->"
        f"Measure{{Expenses}}->Period{{10;11;12}}->"
        f"Tax{{Tax}}->Year{{{year_2}}}"
    )
    df_10_12 = cube.query(fix_actual, compact=False)
    forecast_df = df_10_12[(df_10_12['data'].notna()) & (df_10_12['data'] != 0)].copy()
    forecast_df['Year'] = last_year
    forecast_df['Version'] = 'Y0'
    forecast_df['Scenario'] = 'Forecast'

    budget_df_10_12 = df_10_12[(df_10_12['data'].notna()) & (df_10_12['data'] != 0)].copy()
    budget_df_10_12['Year'] = year
    budget_df_10_12['Version'] = 'Y0'
    budget_df_10_12['Scenario'] = 'Budget'

    fix_actual = (
        f"Entity{{{Entity}}}->"
        f"Material{{Base(MQ01,0);Base(MQ03,0);Base(MQ05,0)}}->"
        f"Department{{Operation}}->Version{{Y1}}->Allocation{{Original}}->"
        f"Misc1{{Base(Centralized_Agreement,0)}}->Misc2{{Nomisc2}}->"
        f"Account{{{';'.join(accounts)}}}->Scenario{{Actual}}->"
        f"Measure{{Expenses}}->Period{{1;2;3;4;5;6;7;8;9}}->"
        f"Tax{{Tax}}->Year{{{last_year}}}"
    )


    df_1_9 = cube.query(fix_actual, compact=False)
    budget_df_1_9 = df_1_9[(df_1_9['data'].notna()) & (df_1_9['data'] != 0)].copy()
    budget_df_1_9['Year'] = year
    budget_df_1_9['Version'] = 'Y0'
    budget_df_1_9['Scenario'] = 'Budget'


    # 有效成分单独取上一年预算
    fix_budget = (
        f"Entity{{{Entity}}}->"
        f"Material{{Base(MQ01,0);Base(MQ03,0);Base(MQ05,0)}}->"
        f"Department{{Operation}}->Version{{Y1}}->Allocation{{Original}}->"
        f"Misc1{{Base(Centralized_Agreement,0)}}->Misc2{{Nomisc2}}->"
        f"Account{{YW0302}}->Scenario{{Actual}}->"
        f"Measure{{Expenses}}->Period{{1;2;3;4;5;6;7;8;9;10;11;12}}->"
        f"Tax{{Tax}}->Year{{{last_year}}}"
    )


    df_1_12 = cube.query(fix_budget, compact=False)
    budget_df_1_12 = df_1_12[(df_1_12['data'].notna()) & (df_1_12['data'] != 0)].copy()
    budget_df_1_12['Year'] = year
    budget_df_1_12['Version'] = 'Y0'
    budget_df_1_12['Scenario'] = 'Budget'


    result = pd.concat([forecast_df, budget_df_1_9, budget_df_10_12, budget_df_1_12], ignore_index=True)

    cube.save(result, chunksize=200000)


    return result


def main(p1, p2):
    # 取预算年
    if 'Year_wb1' in p2 and p2['Year_wb1']:
        year = str(p2['Year_wb1'])
    else:
        BudYear = Variable('Variable').get('BudYear')
        year = BudYear

    # 取实体
    if 'Entity_wb1' in p2 and p2['Entity_wb1']:
        Entity = p2['Entity_wb1']
    else:
        Entity = 'Base(#root,0)'

    print(f"🚀 开始原材料Y0科目复制: Year={year}, Entity={Entity}")
    copy_accounts_to_y0(p1, p2, Entity, year)

    from budget.Python.biz.material.raw_material_calc import main as material_main
    material_main(p1, p2)


# debug
if __name__ == '__main__':
    # 测试用，可在 para2 中传参
    test_para2 =  {'elementName': '_Material_Unit', 'folderId': 'DIRacd99f1aefd0', 'sheetName': '原材料单耗填报（非集采药剂）',
     'sheetId': 'SHTdb258039787a486589a8827c08a1eafb', 'Year_wb1': '2026', 'Entity_wb1': 'XN61001_01',
     'Department_wb1': 'Operation', 'Tax_wb1': 'Tax', 'Version_wb1': 'Y0', 'Material_wb1': 'Nomaterial',
     'Allocation_wb1': 'Original', 'Measure_wb1': 'Expenses', 'Misc1_wb1': 'Nomisc1', 'Misc2_wb1': 'Nomisc2'}

    main(para1, test_para2)