# -*- coding: utf-8 -*-
'''
@file    : production_y0_copy.py
@Author  : cjl
@Desc    : 基础生产数据Y0科目复制脚本
          上年预测：取预算年-2实际 10-12月 → last_year Forecast/Y0
          本年预算：取预算年-1实际 1-9月 + 预算年-2实际 10-12月 → year Budget/Y0
          YW0204 单独处理（公式计算）
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

# 普通科目（从实际数复制）
NORMAL_ACCOUNTS = [
    'YW0201', 'YW0206',
    'YW020701', 'YW020702',
    'YW020901', 'YW020902',
]

# 单独处理的科目
SPECIAL_ACCOUNTS = ['YW0204']

# 水质科目
WATER_QUALITY_ACCOUNTS = ['YW0211', 'YW0212']
WATER_QUALITY_MEASURES = ['COD', 'BOD5', 'SS', 'NH3N', 'TN', 'TP']


def generate_calendar_days(entity_list, start_month, end_month, year):
    """生成日历天数数据"""
    month_days = [
        [str(m), calendar.monthrange(int(year), m)[1]]
        for m in range(start_month, end_month + 1)
    ]
    df_days = pd.DataFrame(month_days, columns=['Period', 'data'])
    df_days['key'] = 1
    df_entity = pd.DataFrame({'Entity': entity_list})
    df_entity['key'] = 1
    df_days = pd.merge(df_entity, df_days, on='key').drop('key', axis=1)
    df_days['Account'] = 'YW0202'
    return df_days


def get_entity_list(Entity):
    """获取实体列表"""
    if Entity == 'Base(#root,0)':
        dim = Dimension('Entity', path='/02_Dimension')
        entity_df = pd.DataFrame(dim.query(
            "AndFilter(Base(#root,0),Attr(isActive,'Y'))", as_model=False, fields=['name']
        ))
        return entity_df['name'].tolist()
    else:
        return [Entity]


def add_dimension_columns(df):
    """添加固定维度列"""
    df['Material'] = 'Nomaterial'
    df['Department'] = 'Operation'
    df['Allocation'] = 'Original'
    df['Misc1'] = 'Nomisc1'
    df['Misc2'] = 'Nomisc2'
    df['Tax'] = 'Tax'
    df['Measure'] = 'Nomeasure'
    return df


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
        f"Measure{{Nomeasure}}->Period{{10;11;12}}->"
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
        f"Measure{{Nomeasure}}->Period{{1;2;3;4;5;6;7;8;9}}->"
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
    YW0204 单独处理：
      预测: year-2 实际 10-12月 → last_year Forecast/Y0
      预算: year-1实际(月) * (1 + (year-1实际 - year-2实际) / year-2实际) → year Budget/Y0
    """
    last_year = str(int(year) - 1)
    year_2 = str(int(year) - 2)

    # =========================================================
    # 1. YW0204 预测数：year-2 实际 10-12月
    # =========================================================
    fix_forecast_0204 = (
        f"Entity{{{Entity}}}->"
        f"Material{{Nomaterial}}->"
        f"Department{{Operation}}->Version{{Y1}}->Allocation{{Original}}->"
        f"Misc1{{Nomisc1}}->Misc2{{Nomisc2}}->"
        f"Account{{YW0204}}->Scenario{{Actual}}->"
        f"Measure{{Nomeasure}}->Period{{10;11;12}}->"
        f"Tax{{Tax}}->Year{{{year_2}}}"
    )
    print(f"📥 [YW0204] 查询上年预测: {year_2}年 Actual 10-12月")
    df_0204_forecast = cube.query(fix_forecast_0204, compact=False)
    df_0204_forecast = df_0204_forecast[(df_0204_forecast['data'].notna()) & (df_0204_forecast['data'] != 0)].copy()
    if not df_0204_forecast.empty:
        df_0204_forecast['Year'] = last_year
        df_0204_forecast['Scenario'] = 'Forecast'
        df_0204_forecast['Version'] = 'Y0'
        cube.save(df_0204_forecast, chunksize=200000)
        print(f"   YW0204 上年预测: {len(df_0204_forecast)} 条")
    else:
        print("   YW0204 上年预测无数据")

    # =========================================================
    # 2. YW0204 预算数: year-1实际(月) * (1 + (year-1实际 - year-2实际) / year-2实际)
    # =========================================================
    # 取 year-1 实际 1-12月
    fix_0204_ly = (
        f"Entity{{{Entity}}}->"
        f"Material{{Nomaterial}}->"
        f"Department{{Operation}}->Version{{Y1}}->Allocation{{Original}}->"
        f"Misc1{{Nomisc1}}->Misc2{{Nomisc2}}->"
        f"Account{{YW0204}}->Scenario{{Actual}}->"
        f"Measure{{Nomeasure}}->Period{{1;2;3;4;5;6;7;8;9;10;11;12}}->"
        f"Tax{{Tax}}->Year{{{last_year}}}"
    )
    # 取 year-2 实际 1-12月
    fix_0204_y2 = (
        f"Entity{{{Entity}}}->"
        f"Material{{Nomaterial}}->"
        f"Department{{Operation}}->Version{{Y1}}->Allocation{{Original}}->"
        f"Misc1{{Nomisc1}}->Misc2{{Nomisc2}}->"
        f"Account{{YW0204}}->Scenario{{Actual}}->"
        f"Measure{{Nomeasure}}->Period{{1;2;3;4;5;6;7;8;9;10;11;12}}->"
        f"Tax{{Tax}}->Year{{{year_2}}}"
    )
    print(f"📥 [YW0204] 查询预算源数据: {last_year}年 & {year_2}年 Actual 1-12月")
    df_0204_ly = cube.query(fix_0204_ly, compact=False)
    df_0204_y2 = cube.query(fix_0204_y2, compact=False)

    df_0204_budget = df_0204_ly.merge(
        df_0204_y2[['Period', 'Entity', 'data']],
        on=['Period', 'Entity'],
        suffixes=('_ly', '_y2'),
        how='left'
    )

    df_0204_budget['data_y2'] = df_0204_budget['data_y2'].fillna(0)

    # 预算 = year-1实际 * (1 + (year-1实际 - year-2实际) / year-2实际)
    mask = df_0204_budget['data_y2'] != 0
    df_0204_budget.loc[mask, 'data'] = df_0204_budget.loc[mask, 'data_ly'] * (
        1 + (df_0204_budget.loc[mask, 'data_ly'] - df_0204_budget.loc[mask, 'data_y2']) / df_0204_budget.loc[mask, 'data_y2']
    )
    df_0204_budget.loc[~mask, 'data'] = df_0204_budget.loc[~mask, 'data_ly']

    # 过滤有效数据
    df_0204_budget = df_0204_budget[(df_0204_budget['data'].notna()) & (df_0204_budget['data'] != 0)].copy()

    if not df_0204_budget.empty:
        df_0204_budget['Year'] = str(year)
        df_0204_budget['Scenario'] = 'Budget'
        df_0204_budget['Version'] = 'Y0'
        df_0204_budget['Account'] = 'YW0204'
        df_0204_budget = add_dimension_columns(df_0204_budget)
        cube.save(df_0204_budget, chunksize=200000)
        print(f"   YW0204 本年预算: {len(df_0204_budget)} 条")
    else:
        print("   YW0204 本年预算无数据")

    # =========================================================
    # 3. YW0202 按日历天数生成
    # =========================================================
    generate_yw0202_days(cube, year)


def generate_yw0202_days(cube, year):
    """
    YW0202 运行天数：按日历天数生成
      预算: year年 1-12月 → Budget/Y0
      预测: last_year年 10-12月 → Forecast/Y0
    """
    last_year = int(year) - 1
    entity_list = get_entity_list('Base(#root,0)')
    entity_list = [e for e in entity_list if e.startswith('XN')]

    result_list = []

    # --- 预算: year年 1-12月日历天数 ---
    df_days_budget = generate_calendar_days(entity_list, 1, 12, year)
    df_days_budget = add_dimension_columns(df_days_budget)
    df_days_budget['Year'] = str(year)
    df_days_budget['Scenario'] = 'Budget'
    df_days_budget['Version'] = 'Y0'
    result_list.append(df_days_budget)
    print(f"   YW0202 本年预算(日历天数): {len(df_days_budget)} 条")

    # --- 预测: last_year年 10-12月日历天数 ---
    df_days_forecast = generate_calendar_days(entity_list, 10, 12, last_year)
    df_days_forecast = add_dimension_columns(df_days_forecast)
    df_days_forecast['Year'] = str(last_year)
    df_days_forecast['Scenario'] = 'Forecast'
    df_days_forecast['Version'] = 'Y0'
    result_list.append(df_days_forecast)
    print(f"   YW0202 上年预测(日历天数): {len(df_days_forecast)} 条")

    result = pd.concat(result_list, ignore_index=True)
    cube.save(result, chunksize=200000)
    print(f"✅ YW0202 日历天数生成完成，共 {len(result)} 条记录")


def copy_water_quality_accounts(cube, Entity, year):
    """
    水质科目（YW0211, YW0212）处理：
      度量: COD, BOD5, SS, NH3-N, TN, TP
      预测数: year-2 实际 10-12月 → last_year Forecast/Y0
      预算数: 上年实际 * (1 + (上年实际 - 上上年实际) / 上上年实际) → year Budget/Y0
    """
    last_year = str(int(year) - 1)
    year_2 = str(int(year) - 2)
    measures_str = ';'.join(WATER_QUALITY_MEASURES)
    account = ';'.join(WATER_QUALITY_ACCOUNTS)


    # =========================================================
    # 1. 预测数：year-2 实际 10-12月 → last_year Forecast/Y0
    # =========================================================
    fix_forecast = (
        f"Entity{{{Entity}}}->"
        f"Material{{Nomaterial}}->"
        f"Department{{Operation}}->Version{{Y1}}->Allocation{{Original}}->"
        f"Misc1{{Nomisc1}}->Misc2{{Nomisc2}}->"
        f"Account{{{account}}}->Scenario{{Actual}}->"
        f"Measure{{{measures_str}}}->Period{{10;11;12}}->"
        f"Tax{{Tax}}->Year{{{year_2}}}"
    )
    print(f"📥 [{account}] 查询上年预测: {year_2}年 Actual 10-12月")
    df_forecast = cube.query(fix_forecast, compact=False)
    df_forecast = df_forecast[(df_forecast['data'].notna()) & (df_forecast['data'] != 0)].copy()
    if not df_forecast.empty:
        df_forecast['Year'] = last_year
        df_forecast['Scenario'] = 'Forecast'
        df_forecast['Version'] = 'Y0'
        cube.save(df_forecast, chunksize=200000)
        print(f"   {account} 上年预测: {len(df_forecast)} 条")
    else:
        print(f"   {account} 上年预测无数据")

    # =========================================================
    # 2. 预算数: year-1实际 * (1 + (year-1实际 - year-2实际) / year-2实际)
    # =========================================================
    fix_ly = (
        f"Entity{{{Entity}}}->"
        f"Material{{Nomaterial}}->"
        f"Department{{Operation}}->Version{{Y1}}->Allocation{{Original}}->"
        f"Misc1{{Nomisc1}}->Misc2{{Nomisc2}}->"
        f"Account{{{account}}}->Scenario{{Actual}}->"
        f"Measure{{{measures_str}}}->Period{{1;2;3;4;5;6;7;8;9;10;11;12}}->"
        f"Tax{{Tax}}->Year{{{last_year}}}"
    )
    fix_y2 = (
        f"Entity{{{Entity}}}->"
        f"Material{{Nomaterial}}->"
        f"Department{{Operation}}->Version{{Y1}}->Allocation{{Original}}->"
        f"Misc1{{Nomisc1}}->Misc2{{Nomisc2}}->"
        f"Account{{{account}}}->Scenario{{Actual}}->"
        f"Measure{{{measures_str}}}->Period{{1;2;3;4;5;6;7;8;9;10;11;12}}->"
        f"Tax{{Tax}}->Year{{{year_2}}}"
    )
    print(f"📥 [{account}] 查询预算源数据: {last_year}年 & {year_2}年 Actual 1-12月")
    df_ly = cube.query(fix_ly, compact=False)
    df_y2 = cube.query(fix_y2, compact=False)

    # 按 Period, Entity, Measure 关联（水质有多个度量）
    df_budget = df_ly.merge(
        df_y2[['Period', 'Entity', 'Account','Measure', 'data']],
        on=['Period', 'Entity', 'Account','Measure'],
        suffixes=('_ly', '_y2'),
        how='left'
    )
    df_budget['data_y2'] = df_budget['data_y2'].fillna(0)

    # 预算 = year-1实际 * (1 + (year-1实际 - year-2实际) / year-2实际)
    mask = df_budget['data_y2'] != 0
    df_budget.loc[mask, 'data'] = df_budget.loc[mask, 'data_ly'] * (
        1 + (df_budget.loc[mask, 'data_ly'] - df_budget.loc[mask, 'data_y2']) / df_budget.loc[mask, 'data_y2']
    )
    df_budget.loc[~mask, 'data'] = df_budget.loc[~mask, 'data_ly']

    df_budget = df_budget[(df_budget['data'].notna()) & (df_budget['data'] != 0)].copy()
    if not df_budget.empty:
        df_budget['Year'] = str(year)
        df_budget['Scenario'] = 'Budget'
        df_budget['Version'] = 'Y0'

        cube.save(df_budget, chunksize=200000)
        print(f"   {account} 本年预算: {len(df_budget)} 条")
    else:
        print(f"   {account} 本年预算无数据")


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

    print(f"🚀 开始基础生产数据Y0科目复制: Year={year}, Entity={Entity}")

    cube = FinancialCube('WS_cube')

    # 1. 普通科目
    print(f"\n--- 普通科目处理 ({len(NORMAL_ACCOUNTS)}个) ---")
    copy_normal_accounts(cube, Entity, year)

    # 2. 特殊科目 YW0204 + YW0202
    print(f"\n--- 特殊科目处理 ({', '.join(SPECIAL_ACCOUNTS)} + YW0202) ---")
    copy_special_accounts(cube, Entity, year)

    # 3. 水质科目 YW0211, YW0212
    print(f"\n--- 水质科目处理 ({', '.join(WATER_QUALITY_ACCOUNTS)}) ---")
    copy_water_quality_accounts(cube, Entity, year)

    print(f"\n🎉 基础生产数据Y0科目复制全部完成")


# debug
if __name__ == '__main__':
    para2 = {
        'Year_wb1': '2026',
        'Entity_wb1': 'Base(1,0)',
    }

    main(para1, para2)