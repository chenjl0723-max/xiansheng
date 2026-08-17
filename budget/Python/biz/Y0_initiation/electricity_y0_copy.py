# -*- coding: utf-8 -*-
'''
@file    : electricity_y0_copy.py
@Author  : cjl
@Desc    : 电费Y0科目复制脚本
          上年预测：取前两年(year-2)实际 10-12月
          本年预算：取上年(year-1)实际 1-9月 + 前两年(year-2)实际 10-12月
          YW0401 只复制预测
'''

try:
    from budget._debug import para1, para2
except ImportError:
    para1 = para2 = {}
from deepfos.options import OPTION
import pandas as pd
import calendar
from deepfos.element.finmodel import FinancialCube
from deepfos.element.variable import Variable
from deepfos.element.dimension import Dimension


# =========================================================
# 科目分组
# =========================================================

# 普通科目（上年预测取前两年10-12，本年预算取上年1-9 + 前两年10-12）
NORMAL_ACCOUNTS = [
    # 电费科目
    'PL01020201', 'PL01020203', 'PL01020204', 'PL01020205',
    'PL0102020201', 'PL0102030101',
    'YW0403', 'YW0214', 'YW0216', 'YW0217',
]

# 只复制预测的科目
FORECAST_ONLY_ACCOUNTS = ['YW0401']


def copy_normal_accounts(cube, Entity, year):
    """
    普通科目复制：
      上年预测 → year-2实际 10-12月 → 存为 last_year Forecast/Y0
      本年预算 → year-1实际 1-9月 + year-2实际 10-12月 → 存为 year Budget/Y0
    """
    last_year = str(int(year) - 1)
    year_2 = str(int(year) - 2)
    accounts_str = ';'.join(NORMAL_ACCOUNTS)

    result_list = []

    # =========================================================
    # 1. 上年预测：year-2 实际 10-12月 → last_year Forecast/Y0
    # =========================================================
    fix_forecast = (
        f"Entity{{{Entity}}}->"
        f"Material{{Nomaterial}}->"
        f"Department{{Operation}}->Version{{Y1}}->Allocation{{Original}}->"
        f"Misc1{{Nomisc1}}->Misc2{{Nomisc2}}->"
        f"Account{{{accounts_str}}}->Scenario{{Actual}}->"
        f"Measure{{Expenses}}->Period{{10;11;12}}->"
        f"Tax{{Tax}}->Year{{{year_2}}}"
    )
    print(f"📥 查询上年预测源数据: {year_2}年 Actual 10-12月")
    df_forecast = cube.query(fix_forecast, compact=False)
    df_forecast = df_forecast[(df_forecast['data'].notna()) & (df_forecast['data'] != 0)].copy()
    if not df_forecast.empty:
        df_forecast['Year'] = last_year
        df_forecast['Scenario'] = 'Forecast'
        df_forecast['Version'] = 'Y0'
        result_list.append(df_forecast)
        print(f"   上年预测: {len(df_forecast)} 条")

    # =========================================================
    # 2. 本年预算 - Part1: year-1 实际 1-9月
    # =========================================================
    fix_budget_1_9 = (
        f"Entity{{{Entity}}}->"
        f"Material{{Nomaterial}}->"
        f"Department{{Operation}}->Version{{Y1}}->Allocation{{Original}}->"
        f"Misc1{{Nomisc1}}->Misc2{{Nomisc2}}->"
        f"Account{{{accounts_str}}}->Scenario{{Actual}}->"
        f"Measure{{Expenses}}->Period{{1;2;3;4;5;6;7;8;9}}->"
        f"Tax{{Tax}}->Year{{{last_year}}}"
    )
    print(f"📥 查询本年预算源数据(1-9月): {last_year}年 Actual 1-9月")
    df_1_9 = cube.query(fix_budget_1_9, compact=False)
    df_1_9 = df_1_9[(df_1_9['data'].notna()) & (df_1_9['data'] != 0)].copy()
    if not df_1_9.empty:
        df_1_9['Year'] = str(year)
        df_1_9['Scenario'] = 'Budget'
        df_1_9['Version'] = 'Y0'
        result_list.append(df_1_9)
        print(f"   本年预算(1-9月): {len(df_1_9)} 条")

    # =========================================================
    # 3. 本年预算 - Part2: year-2 实际 10-12月
    # =========================================================
    print(f"📥 查询本年预算源数据(10-12月): {year_2}年 Actual 10-12月")
    df_10_12 = cube.query(fix_forecast, compact=False)  # 同一查询条件
    df_10_12 = df_10_12[(df_10_12['data'].notna()) & (df_10_12['data'] != 0)].copy()
    if not df_10_12.empty:
        df_10_12['Year'] = str(year)
        df_10_12['Scenario'] = 'Budget'
        df_10_12['Version'] = 'Y0'
        result_list.append(df_10_12)
        print(f"   本年预算(10-12月): {len(df_10_12)} 条")

    # =========================================================
    # 4. 合并保存
    # =========================================================
    if not result_list:
        print("⚠️ 普通科目无数据，跳过")
        return

    result = pd.concat(result_list, ignore_index=True)
    cube.save(result, chunksize=200000)
    print(f"✅ 普通科目复制完成，共 {len(result)} 条记录")
    return result


def copy_forecast_only_accounts(cube, Entity, year):
    """
    只复制预测的科目（YW0401）：
      上年预测 → year-2实际 10-12月 → last_year Forecast/Y0
    """
    last_year = str(int(year) - 1)
    year_2 = str(int(year) - 2)
    accounts_str = ';'.join(FORECAST_ONLY_ACCOUNTS)

    # =========================================================
    # 预测数：year-2 实际 10-12月 → last_year Forecast/Y0
    # =========================================================
    fix_forecast = (
        f"Entity{{{Entity}}}->"
        f"Material{{Nomaterial}}->"
        f"Department{{Operation}}->Version{{Y1}}->Allocation{{Original}}->"
        f"Misc1{{Nomisc1}}->Misc2{{Nomisc2}}->"
        f"Account{{{accounts_str}}}->Scenario{{Actual}}->"
        f"Measure{{Expenses}}->Period{{10;11;12}}->"
        f"Tax{{Tax}}->Year{{{year_2}}}"
    )
    print(f"📥 查询预测科目源数据: {year_2}年 Actual 10-12月")
    df_forecast = cube.query(fix_forecast, compact=False)
    df_forecast = df_forecast[(df_forecast['data'].notna()) & (df_forecast['data'] != 0)].copy()
    if not df_forecast.empty:
        df_forecast['Year'] = last_year
        df_forecast['Scenario'] = 'Forecast'
        df_forecast['Version'] = 'Y0'
        cube.save(df_forecast, chunksize=200000)
        print(f"✅ 预测科目复制完成，共 {len(df_forecast)} 条记录")
    else:
        print("⚠️ 预测科目无数据，跳过")


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

    print(f"🚀 开始电费Y0科目复制: Year={year}, Entity={Entity}")

    cube = FinancialCube('WS_cube')

    # 1. 普通科目（复制预测+预算）
    print(f"\n--- 普通科目处理 ({len(NORMAL_ACCOUNTS)}个) ---")
    copy_normal_accounts(cube, Entity, year)

    # 2. 只复制预测的科目（YW0401）
    print(f"\n--- 预测科目处理 ({', '.join(FORECAST_ONLY_ACCOUNTS)}) ---")
    copy_forecast_only_accounts(cube, Entity, year)

    print(f"\n🎉 电费Y0科目复制全部完成")


# debug
if __name__ == '__main__':
    para2 = {
        'Year_wb1': '2026',
        'Entity_wb1': 'Base(1,0)',
    }

    main(para1, para2)
