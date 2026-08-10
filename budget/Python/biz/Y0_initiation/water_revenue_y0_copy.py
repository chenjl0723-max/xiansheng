# -*- coding: utf-8 -*-
'''
@file    : water_revenue_y0_copy.py
@Author  : cjl
@Desc    : 水价收入Y0科目复制脚本
          上年预测：取前两年(year-2)实际 10-12月
          本年预算：取上年(year-1)实际 1-9月 + 前两年(year-2)实际 10-12月
          YW0102/YW0202 单独处理
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
    'PL01010101', 'YW0105', 'YW0106', 'YW0107',
    'PL01010102', 'YW0108', 'YW0109',
    'PL01010103', 'YW0101', 'YW0104',
    'PL010103', 'PL010104', 'PL010105', 'PL010106',
    'PL010109', 'PL010113', 'PL010116',
]

# 单独处理的科目
SPECIAL_ACCOUNTS = ['YW0102', 'YW0202']


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


def copy_special_accounts(cube, Entity, year):
    """
    YW0102/YW0202 单独处理：
      YW0102 预测: year-2 实际 10-12月 → last_year Forecast/Y0
      YW0102 预算: year-1实际(月) * (1 + (year-1实际 - year-2实际)) → year Budget/Y0
      YW0202: 按 genarate_day 逻辑生成日历天数 → Budget/Y0 + Forecast/Y0
    """
    last_year = str(int(year) - 1)
    year_2 = str(int(year) - 2)

    # =========================================================
    # 1. YW0102 预测数：year-2 实际 10-12月
    # =========================================================
    fix_forecast_0102 = (
        f"Entity{{{Entity}}}->"
        f"Material{{Nomaterial}}->"
        f"Department{{Operation}}->Version{{Y1}}->Allocation{{Original}}->"
        f"Misc1{{Nomisc1}}->Misc2{{Nomisc2}}->"
        f"Account{{YW0102}}->Scenario{{Actual}}->"
        f"Measure{{Expenses}}->Period{{10;11;12}}->"
        f"Tax{{Tax}}->Year{{{year_2}}}"
    )
    print(f"📥 [YW0102] 查询上年预测: {year_2}年 Actual 10-12月")
    df_0102_forecast = cube.query(fix_forecast_0102, compact=False)
    df_0102_forecast = df_0102_forecast[(df_0102_forecast['data'].notna()) & (df_0102_forecast['data'] != 0)].copy()
    if not df_0102_forecast.empty:
        df_0102_forecast['Year'] = last_year
        df_0102_forecast['Scenario'] = 'Forecast'
        df_0102_forecast['Version'] = 'Y0'
        cube.save(df_0102_forecast, chunksize=200000)
        print(f"   YW0102 上年预测: {len(df_0102_forecast)} 条")
    else:
        print("   YW0102 上年预测无数据")

    # =========================================================
    # 2. YW0102 预算数: year-1实际(月) * (1 + (year-1实际 - year-2实际))
    # =========================================================
    # 取 year-1 实际 1-12月
    fix_0102_ly = (
        f"Entity{{{Entity}}}->"
        f"Material{{Nomaterial}}->"
        f"Department{{Operation}}->Version{{Y1}}->Allocation{{Original}}->"
        f"Misc1{{Nomisc1}}->Misc2{{Nomisc2}}->"
        f"Account{{YW0102}}->Scenario{{Actual}}->"
        f"Measure{{Expenses}}->Period{{1;2;3;4;5;6;7;8;9;10;11;12}}->"
        f"Tax{{Tax}}->Year{{{last_year}}}"
    )
    # 取 year-2 实际 1-12月
    fix_0102_y2 = (
        f"Entity{{{Entity}}}->"
        f"Material{{Nomaterial}}->"
        f"Department{{Operation}}->Version{{Y1}}->Allocation{{Original}}->"
        f"Misc1{{Nomisc1}}->Misc2{{Nomisc2}}->"
        f"Account{{YW0102}}->Scenario{{Actual}}->"
        f"Measure{{Expenses}}->Period{{1;2;3;4;5;6;7;8;9;10;11;12}}->"
        f"Tax{{Tax}}->Year{{{year_2}}}"
    )
    print(f"📥 [YW0102] 查询预算源数据: {last_year}年 & {year_2}年 Actual 1-12月")
    df_0102_ly = cube.query(fix_0102_ly, compact=False)
    df_0102_y2 = cube.query(fix_0102_y2, compact=False)

    # 按 Entity + Period 合并两年数据
    merge_cols = ['Entity', 'Period']
    df_0102_ly = df_0102_ly[merge_cols + ['data']].rename(columns={'data': 'data_ly'})
    df_0102_y2 = df_0102_y2[merge_cols + ['data']].rename(columns={'data': 'data_y2'})

    df_0102_budget = df_0102_ly.merge(df_0102_y2, on=merge_cols, how='left')
    df_0102_budget['data_y2'] = df_0102_budget['data_y2'].fillna(0)

    # 预算 = year-1实际 * (1 + (year-1实际 - year-2实际))
    df_0102_budget['data'] = df_0102_budget['data_ly'] * (
        1 + (df_0102_budget['data_ly'] - df_0102_budget['data_y2'])
    )

    # 过滤有效数据
    df_0102_budget = df_0102_budget[(df_0102_budget['data'].notna()) & (df_0102_budget['data'] != 0)].copy()

    if not df_0102_budget.empty:
        df_0102_budget['Year'] = str(year)
        df_0102_budget['Scenario'] = 'Budget'
        df_0102_budget['Version'] = 'Y0'
        df_0102_budget['Account'] = 'YW0102'
        df_0102_budget['Material'] = 'Nomaterial'
        df_0102_budget['Department'] = 'Operation'
        df_0102_budget['Allocation'] = 'Original'
        df_0102_budget['Misc1'] = 'Nomisc1'
        df_0102_budget['Misc2'] = 'Nomisc2'
        df_0102_budget['Tax'] = 'Tax'
        df_0102_budget['Measure'] = 'Expenses'
        cube.save(df_0102_budget, chunksize=200000)
        print(f"   YW0102 本年预算: {len(df_0102_budget)} 条")
    else:
        print("   YW0102 本年预算无数据")

    # =========================================================
    # 3. YW0202 按 genarate_day 逻辑生成日历天数
    # =========================================================
    generate_yw0202_days(cube, Entity, year)


def generate_yw0202_days(cube, Entity, year):
    """
    YW0202 运行天数：按 genarate_day 逻辑生成日历天数
      预算: year年 1-12月 → Budget/Y0
      预测: last_year年 10-12月 → Forecast/Y0
    """
    last_year = int(year) - 1

    # 获取实体列表
    if Entity == 'Base(#root,0)':
        dim = Dimension('Entity', path='/02_Dimension')
        entity_df = pd.DataFrame(dim.query(
            "AndFilter(Base(#root,0),Attr(isActive,'Y'))", as_model=False, fields=['name']
        ))
        entity_list = entity_df['name'].tolist()
    else:
        entity_list = [Entity]

    result_list = []

    # --- 预算: year年 1-12月日历天数 ---
    year_int = int(year)
    month_days = [
        [str(m), calendar.monthrange(year_int, m)[1]]
        for m in range(1, 13)
    ]
    df_days_budget = pd.DataFrame(month_days, columns=['Period', 'data'])
    df_days_budget['key'] = 1
    df_entity = pd.DataFrame({'Entity': entity_list})
    df_entity['key'] = 1
    df_budget = pd.merge(df_entity, df_days_budget, on='key').drop('key', axis=1)
    df_budget['Account'] = 'YW0202'
    df_budget['Year'] = str(year)
    df_budget['Scenario'] = 'Budget'
    df_budget['Version'] = 'Y0'
    df_budget['Measure'] = 'Expenses'
    df_budget['Material'] = 'Nomaterial'
    df_budget['Department'] = 'Operation'
    df_budget['Allocation'] = 'Original'
    df_budget['Tax'] = 'Tax'
    df_budget['Misc1'] = 'Nomisc1'
    df_budget['Misc2'] = 'Nomisc2'
    result_list.append(df_budget)
    print(f"   YW0202 本年预算(日历天数): {len(df_budget)} 条")
    print(1)

    # --- 预测: last_year年 10-12月日历天数 ---
    month_days_fc = [
        [str(m), calendar.monthrange(last_year, m)[1]]
        for m in range(10, 13)
    ]
    df_days_forecast = pd.DataFrame(month_days_fc, columns=['Period', 'data'])
    df_days_forecast['key'] = 1
    df_forecast = pd.merge(df_entity, df_days_forecast, on='key').drop('key', axis=1)
    df_forecast['Account'] = 'YW0202'
    df_forecast['Year'] = str(last_year)
    df_forecast['Scenario'] = 'Forecast'
    df_forecast['Version'] = 'Y0'
    df_forecast['Measure'] = 'Expenses'
    df_forecast['Material'] = 'Nomaterial'
    df_forecast['Department'] = 'Operation'
    df_forecast['Allocation'] = 'Original'
    df_forecast['Tax'] = 'Tax'
    df_forecast['Misc1'] = 'Nomisc1'
    df_forecast['Misc2'] = 'Nomisc2'
    result_list.append(df_forecast)
    print(f"   YW0202 上年预测(日历天数): {len(df_forecast)} 条")

    result = pd.concat(result_list, ignore_index=True)
    cube.save(result, chunksize=200000)
    print(f"✅ YW0202 日历天数生成完成，共 {len(result)} 条记录")


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

    print(f"🚀 开始水价收入Y0科目复制: Year={year}, Entity={Entity}")

    cube = FinancialCube('WS_cube')

    # 1. 普通科目
    print(f"\n--- 普通科目处理 ({len(NORMAL_ACCOUNTS)}个) ---")
    copy_normal_accounts(cube, Entity, year)

    # 2. 特殊科目 YW0102/YW0202
    print(f"\n--- 特殊科目处理 ({', '.join(SPECIAL_ACCOUNTS)}) ---")
    copy_special_accounts(cube, Entity, year)

    print(f"\n🎉 水价收入Y0科目复制全部完成")


# debug
if __name__ == '__main__':
    test_para2 = {
        'Year_wb1': '2026',
        'Entity_wb1': 'Y6120210005',
    }
    if para2 and para2 != {} and 'Year_wb1' in para2:
        main(para1, para2)
    else:
        main(para1, test_para2)
