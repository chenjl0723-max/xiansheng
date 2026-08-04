# -*- coding: utf-8 -*-
'''
@file    : material_jg.py
@Time    :
@Author  : cjl
@Software: PyCharm
@Desc    : 原材料Y0生成脚本
'''


try:
    from budget._debug import para1, para2
    # print(para1)
except ImportError:
    para1 = para2 = {}
from deepfos.options import OPTION
import pandas as pd
import datetime
import traceback
from deepfos.db.mysql import MySQLClient
from deepfos.element.datatable import DataTableClickHouse
from deepfos.element.finmodel import FinancialCube
from deepfos.element.datatable import DataTableClickHouse as ck
from deepfos.element.datatable import DataTableMySQL
from deepfos.element.variable import Variable
from deepfos.element.dimension import Dimension, DimMember
import numpy as np


def convert_to_middle(df, year, value_col='data', result_col='data'):
    """
    小类折算中类公共函数
    :param df: 包含 Material 和 value_col 的 DataFrame
    :param rate_df: 折算系数（需含 YW0302, YW0317, YW0307）
    :param value_col: 需要折算的数值列名
    :param result_col: 折算后写入的列名
    :return: 折算并汇总后的中类 DataFrame
    """


    fix = "Entity{%s}->Material{Base(MQ01,0);Base(MQ03,0)}->Department{Operation}->Version{Y1}->Allocation{Original}->Misc1{Centralized_Agreement}->Misc2{Nomisc2}->Account{YW0302;YW0317;YW0307}->Scenario{%s}->" \
              "Measure{Expenses}->Period{1}->Tax{Tax}->Year{%s}" % (
                  'Base(#root,0)', 'Budget', year)

    cube = FinancialCube('WS_cube')
    rate_df =  cube.query(fix, compact=False,pivot_dim ='Account')
    # 合并折算系数
    merge_cols = ['Entity', 'Material']
    rate_cols = ['Entity', 'Material', 'YW0302', 'YW0317', 'YW0307']
    df = df.merge(rate_df[rate_cols], on=merge_cols, how='left')

    # 初始化结果列
    df[result_col] = df[value_col]

    # MQ01（除磷）: * YW0302 * YW0317
    mq01_mask = df['Material'].str.startswith('MQ01')
    df.loc[mq01_mask, result_col] = (
        df.loc[mq01_mask, value_col] *
        df.loc[mq01_mask, 'YW0302'].fillna(1) *
        df.loc[mq01_mask, 'YW0317'].fillna(1)
    )

    # MQ03（碳源）: * YW0302 * YW0307
    mq03_mask = df['Material'].str.startswith('MQ03')
    df.loc[mq03_mask, result_col] = (
        df.loc[mq03_mask, value_col] *
        df.loc[mq03_mask, 'YW0302'].fillna(1) *
        df.loc[mq03_mask, 'YW0307'].fillna(1)
    )

    if result_col == 'B':
        return df
    # MQ05 不折算，保持原值

    # 小类 → 中类编码映射
    material_map = {
        'MQ01': '02',
        'MQ03': '01',
        'MQ05': '05'
    }
    for prefix, code in material_map.items():
        df.loc[df['Material'].str.startswith(prefix), 'Material'] = code

    # 汇总
    exclude_cols = ['YW0302', 'YW0317', 'YW0307', value_col]
    if value_col != result_col:
        exclude_cols.append(result_col)  # 防止重复

    # group_cols = [col for col in df.columns if col not in exclude_cols + [result_col] or col == 'Material']
    # 更稳妥的写法：
    group_cols = [c for c in df.columns if c not in ['YW0302', 'YW0317', 'YW0307', value_col, result_col]]
    if result_col not in group_cols:
        pass

    df = df.groupby(group_cols, as_index=False)[result_col].sum()

    return df


def material_processing(p1, p2, Entity,year, Version, material_list=None):
    """
    :param material_list: 要处理的物料列表，如 ['MQ01', 'MQ03', 'MQ05']，None 表示处理所有
    """
    last_year = str(int(year) - 1)
    # 1. 查询原材料单耗数据
    material_jg_dt =  DataTableMySQL('Material_JG')
    cols = ['Entity','Class','Year','Version','JG_bef','JG_aft']
    where = "Year = '%s' and Version = '%s' and Entity = '%s'" % (last_year, Version,Entity)
    if Entity == 'Base(#root,0)':
        where = "Year = '%s' and Version = '%s'" % (last_year, Version)
    material_df = material_jg_dt.select(columns=cols,where=where).rename(columns={
        'Class':'Material'
    })
    # 按物料列表过滤
    if material_list is not None:
        material_df = material_df[material_df['Material'].isin(material_list)]

    # 2. 补充固定维度拆分技改前后单耗
    df_bef = material_df[['Entity', 'Material', 'Year', 'Version', 'JG_bef']].rename(columns={'JG_bef': 'data'})
    df_bef['Measure'] = 'M0902'


    df_aft = material_df[['Entity', 'Material', 'Year', 'Version', 'JG_aft']].rename(columns={'JG_aft': 'data'})
    df_aft['Measure'] = 'M0903'


    material_df = pd.concat([df_bef, df_aft], ignore_index=True)



    # 3. 设置 Account
    material_df['Account'] = ''

    # 根据Material的值设置Account列, 分为吨水药耗，吨干泥药耗，电度电量吨水电耗
    material_df.loc[material_df['Material'].str.startswith(('MQ01', 'MQ03')), 'Account'] = 'YW0304'
    material_df.loc[material_df['Material'].str.startswith('MQ05'), 'Account'] = 'YW0316'
    material_df.loc[material_df['Material'] == 'MQ00', 'Account'] = 'YW0401'
    # 如果原材料为MQ00，度量为Nomaterial
    material_df.loc[material_df['Material'] == 'MQ00', 'Material'] = 'Nomaterial'



    # 4. 补充固定维度
    material_df = material_df.assign(
        Period='Noperiod',
        Department='Operation',
        Tax='Tax',
        Version='Y1',
        Scenario='Budget',
        Misc1='Nomisc1',
        Misc2='Nomisc2',
        Allocation='Original'
    )



    cube = FinancialCube('WS_cube')

    cube.save(material_df, chunksize=200000)

    # 5. 查询折算系数
    # fix = "Entity{%s}->Material{Base(MQ01,0);Base(MQ03,0)}->Department{Operation}->Version{Y1}->Allocation{Original}->Misc1{Centralized_Agreement}->Misc2{Nomisc2}->Account{YW0302;YW0317;YW0307}->Scenario{%s}->" \
    #           "Measure{Expenses}->Period{1}->Tax{Tax}->Year{%s}" % (
    #               'Base(#root,0)', 'Budget', year)

    # Y1_df =  cube.query(fix, compact=False,pivot_dim ='Account')
    # rate_df =  cube.query(fix, compact=False,pivot_dim ='Account')

    zhonglei_df = convert_to_middle(material_df, last_year, value_col='data', result_col='data')

    # 6. 合并折算系数并计算
    # zhonglei_df = pd.merge(material_df, Y1_df[['Entity', 'Material', 'Year', 'Version', 'Tax','YW0302','YW0317','YW0307']], how='left', on=['Entity', 'Material', 'Year', 'Version', 'Tax'])
    #
    #
    # # 对于除磷药剂MQ01开头的Material: data = data * YW0302 * YW0317
    # mq01_mask = zhonglei_df['Material'].str.startswith('MQ01')
    # zhonglei_df.loc[mq01_mask, 'data'] *= zhonglei_df.loc[mq01_mask, 'YW0302'] * zhonglei_df.loc[mq01_mask, 'YW0317']
    #
    # # 对于碳源药剂MQ03开头的Material: data = data * YW0302 * YW0307
    # mq03_mask = zhonglei_df['Material'].str.startswith('MQ03')
    # zhonglei_df.loc[mq03_mask, 'data'] *= zhonglei_df.loc[mq03_mask, 'YW0302'] * zhonglei_df.loc[mq03_mask, 'YW0307']
    #
    #
    # # 7. 将原材料编码转换为中类编码
    # material_map = {
    #     'MQ01': '02',
    #     'MQ03': '01',
    #     'MQ05': '05'
    # }
    # for prefix, code in material_map.items():
    #     zhonglei_df.loc[zhonglei_df['Material'].str.startswith(prefix), 'Material'] = code
    #
    # # 8. 中类汇总
    # account_list = ['YW0302','YW0317','YW0307']
    # group_cols = [col for col in zhonglei_df.columns if col not in account_list + ['data']]
    # zhonglei_df = zhonglei_df.groupby(group_cols, as_index=False)['data'].sum()

    # 9. 保存中类数据
    cube.save(zhonglei_df, chunksize=200000)
    return


def material_processing_mq00(p1, p2, year, Version):
    """MQ00（电度电量）单独处理，无需中类折算"""
    last_year = str(int(year) - 1)

    # 1. 查询 MQ00 单耗数据
    material_jg_dt = DataTableMySQL('Material_JG')
    cols = ['Entity', 'Class', 'Year', 'Version', 'JG_bef', 'JG_aft']
    where = "Year = '%s' and Version = '%s' and Class = 'MQ00'" % (last_year, Version)
    material_df = material_jg_dt.select(columns=cols, where=where).rename(columns={'Class': 'Material'})

    if material_df.empty:
        print("⚠️ 无 MQ00 数据，跳过")
        return

    # 2. 拆分技改前后单耗
    df_bef = material_df[['Entity', 'Material', 'Year', 'Version', 'JG_bef']].rename(columns={'JG_bef': 'data'})
    df_bef['Measure'] = 'M0902'

    df_aft = material_df[['Entity', 'Material', 'Year', 'Version', 'JG_aft']].rename(columns={'JG_aft': 'data'})
    df_aft['Measure'] = 'M0903'

    material_df = pd.concat([df_bef, df_aft], ignore_index=True)

    # 3. 设置 Account 和 Material
    material_df['Account'] = 'YW0401'
    material_df['Material'] = 'Nomaterial'

    # 4. 补充固定维度
    material_df = material_df.assign(
        Period='Noperiod',
        Department='Operation',
        Tax='Tax',
        Version='Y1',
        Scenario='Budget',
        Misc1='Nomisc1',
        Misc2='Nomisc2',
        Allocation='Original'
    )

    # 5. 直接保存（无需中类折算）
    cube = FinancialCube('WS_cube')
    cube.save(material_df, chunksize=200000)
    print(f"✅ MQ00 单耗保存完成，共 {len(material_df)} 条记录")


    cube = FinancialCube('WS_cube')


    fix = "Entity{%s}->Material{Base(MQ01,0);Base(MQ03,0);Base(MQ05,0)}->Department{Operation}->Version{Y1}->Allocation{Original}->Misc1{Base(Centralized_Agreement,0)}->Misc2{Nomisc2}->Account{YW0304;YW0316}->Scenario{%s}->" \
              "Measure{Expenses}->Period{1;2;3;4;5;6;7;8;9;10;11;12}->Tax{Tax}->Year{%s}" % (
                  'Base(#root,0)', 'Actual', str(int(year)-1))
    # 删除数据
    Y1_df =  cube.query(fix, compact=False)
    print(1)


    fix = "Entity{%s}->Material{01;02;05;Nomaterial}->Department{Operation}->Version{Y1}->Allocation{Original}->Misc1{Nomisc1}->Misc2{Nomisc2}->Account{YW0401;YW0304;YW0304;YW0316}->Scenario{%s}->" \
              "Measure{M9901;M9902;M9903}->Period{Noperiod}->Tax{Tax}->Year{%s}" % (
                  'Base(#root,0)', 'Budget', year)


def calc_y0_budget(p1, p2, year, Version):
    """
    计算 year 年 Y0 版本 1-12 月预算单耗
    """
    cube = FinancialCube('WS_cube')
    last_year = str(int(year) - 1)
    # last_year = str(int(year) - 1)

    # =========================================================
    # 1. 取上一年实际小类单耗
    # =========================================================
    fix_actual = (
        f"Entity{{Base(#root,0)}}->"
        f"Material{{Base(MQ01,0);Base(MQ03,0);Base(MQ05,0)}}->"
        f"Department{{Operation}}->Version{{Y1}}->Allocation{{Original}}->"
        f"Misc1{{Base(Centralized_Agreement,0)}}->Misc2{{Nomisc2}}->"
        f"Account{{YW0304;YW0316}}->Scenario{{Actual}}->"
        f"Measure{{Expenses}}->Period{{Noperiod}}->"
        f"Tax{{Tax}}->Year{{{last_year}}}"
    )
    actual_df = cube.query(fix_actual, compact=False)
    actual_df = actual_df.rename(columns={'data': 'actual_unit'})

    actual_df = actual_df[(actual_df['actual_unit'].notna()) & (actual_df['actual_unit'] != 0)].copy()
    # =========================================================
    # 2. 取技改节约值 JG_Middle_sav
    # =========================================================
    jg_dt = DataTableMySQL('Material_JG')
    jg_df = jg_dt.select(
        columns=['Entity', 'Class', 'Year', 'Version', 'JG_Middle_sav'],
        where=f"Year = '{last_year}' and Version = 'Y1'"
    ).rename(columns={'Class': 'Material', 'JG_Middle_sav': 'jg_sav'})

    # =========================================================
    # 3. 计算小类单耗 A = 实际单耗 - 技改节约值
    # =========================================================
    df_a = actual_df.merge(
        jg_df[['Entity', 'Material', 'jg_sav']],
        on=['Entity', 'Material'],
        how='left'
    )

    # 匹配不上技改单耗的节约值设为0
    df_a['jg_sav'] = df_a['jg_sav'].fillna(0)

    df_a['A'] = df_a['actual_unit'] - df_a['jg_sav']




    # =========================================================
    # 4. 取折算系数（与之前逻辑一致）
    # =========================================================


    # =========================================================
    # 5. 折算得到中类单耗 B
    df_b = convert_to_middle(df_a, year, value_col='A', result_col='B')

    def add_middle_sum(df, prefixes=('MQ01', 'MQ03', 'MQ05'), result_col='C'):
        """
        按 Entity + Year + Account 汇总同一前缀的 B 值，写回对应行的 C 列
        """
        df = df.copy()
        df[result_col] = None  # 先初始化 C 列

        for prefix in prefixes:
            mask = df['Material'].str.startswith(prefix)

            # 计算当前前缀的汇总值
            sum_series = (
                df[mask]
                .groupby(['Entity', 'Year', 'Account'])['B']
                .transform('sum')
            )

            # 只写回当前前缀的行
            df.loc[mask, result_col] = sum_series

        df.loc[df['Material'].str.startswith('MQ01'), 'Middle'] = '02'
        df.loc[df['Material'].str.startswith('MQ03'), 'Middle'] = '01'
        df.loc[df['Material'].str.startswith('MQ05'), 'Middle'] = '05'

        return df

    # 使用
    df_b = add_middle_sum(df_b, prefixes=('MQ01', 'MQ03', 'MQ05'), result_col='C')


    # =========================================================
    # 6. 取星级基线值
    # =========================================================
    stjx_dt = DataTableMySQL('Material_Stjx')
    stjx_df = stjx_dt.select(
        columns=[ 'Entity', 'Middle', 'Sed_Stjx'],
        where=f"Year = '{last_year}'"
    )

    df_b = df_b.merge(stjx_df[['Entity', 'Middle', 'Sed_Stjx']],how='left',on=['Entity','Middle'])




    # =========================================================
    # 7. 取预算目标下降幅度（优先级 M9903 > M9902 > M9901）
    # =========================================================
    fix_drop = (
        f"Entity{{Base(#root,0)}}->"
        f"Material{{01;02;05;Nomaterial}}->"
        f"Department{{Operation}}->Version{{Y1}}->Allocation{{Original}}->"
        f"Misc1{{Nomisc1}}->Misc2{{Nomisc2}}->"
        f"Account{{YW0401;YW0304;YW0316}}->Scenario{{Budget}}->"
        f"Measure{{M9901;M9902;M9903}}->Period{{Noperiod}}->"
        f"Tax{{Tax}}->Year{{{year}}}"
    )
    drop_df = cube.query(fix_drop, compact=False, pivot_dim='Measure')

    # 优先级处理
    drop_df['drop_rate'] = drop_df['M9903'].fillna(drop_df['M9902']).fillna(drop_df['M9901']).fillna(0)

    # 合并下降幅度（按中类）
    df_b = df_b.merge(
        drop_df[['Entity', 'Material', 'drop_rate']],
        left_on=['Entity', 'Middle'],
        right_on=['Entity', 'Material'],
        how='left',
        suffixes=('', '_y'))

    df_b['drop_rate'] = df_b['drop_rate'].fillna(0)

    # =========================================================
    # 8. 计算最终预算单耗
    # =========================================================
    # 如果 B <= 基线 → 用 A
    # 如果 B >  基线 → A * (1 - 下降幅度)
    df_b['data'] = df_b.apply(
        lambda row: row['A'] if row['C'] <= row['Sed_Stjx']
                    else row['A'] * (1 - row['drop_rate']),
        axis=1
    )

    # =========================================================
    # 9. 整理最终结果（Y0 版本 1-12 月）
    # =========================================================
    # 只保留需要的列
    result = df_b[['Entity', 'Material', 'Year', 'Account','Period','Department','Allocation','Misc1','Misc2','Tax','Version','Scenario','Measure', 'data']]

    result['Year'] = str(year)
    result['Scenario'] = 'Budget'
    result['Version'] = 'Y0'


    # 计算Y0中类
    zhonglei_df = convert_to_middle(result, last_year, value_col='data', result_col='data')


    # =========================================================
    # 10. 删除旧数据并保存
    # =========================================================
    del_expr = {
        'Year': str(year),
        'Scenario': 'Budget',
        'Version': 'Y0',
        'Measure': 'Expenses',
        'Period': [str(i) for i in range(1, 13)],
        'Tax': 'Tax',
        'Department': 'Operation',
        'Allocation': 'Original',
        'Misc1': 'Nomisc1',
        'Misc2': 'Nomisc2',
        'Account': ['YW0304', 'YW0316'],
        'Material': 'Base(MQ01,0);Base(MQ03,0);Base(MQ05,0)'
    }
    # cube.delete(del_expr)
    cube.save(result, chunksize=200000)
    cube.save(zhonglei_df, chunksize=200000)


    print(f"✅ Y0 预算单耗计算完成，共 {len(result)} 条记录")
    return result


def calc_y0_budget_mq00(p1, p2, year, Version):
    """MQ00（电度电量）Y0 预算计算，无需中类折算和基线比较"""
    cube = FinancialCube('WS_cube')
    last_year = str(int(year) - 1)

    # =========================================================
    # 1. 取上一年实际单耗（MQ00 / YW0401）
    # =========================================================
    fix_actual = (
        f"Entity{{Base(#root,0)}}->"
        f"Material{{MQ00}}->"
        f"Department{{Operation}}->Version{{Y1}}->Allocation{{Original}}->"
        f"Misc1{{Base(Centralized_Agreement,0)}}->Misc2{{Nomisc2}}->"
        f"Account{{YW0401}}->Scenario{{Actual}}->"
        f"Measure{{Expenses}}->Period{{Noperiod}}->"
        f"Tax{{Tax}}->Year{{{last_year}}}"
    )
    actual_df = cube.query(fix_actual, compact=False)
    actual_df = actual_df.rename(columns={'data': 'actual_unit'})
    actual_df = actual_df[(actual_df['actual_unit'].notna()) & (actual_df['actual_unit'] != 0)].copy()

    if actual_df.empty:
        print("⚠️ 无 MQ00 上年实际数据，跳过 Y0 预算计算")
        return

    # =========================================================
    # 2. 取技改节约值
    # =========================================================
    jg_dt = DataTableMySQL('Material_JG')
    jg_df = jg_dt.select(
        columns=['Entity', 'Class', 'Year', 'Version', 'JG_Middle_sav'],
        where=f"Year = '{last_year}' and Version = 'Y1' and Class = 'MQ00'"
    ).rename(columns={'Class': 'Material', 'JG_Middle_sav': 'jg_sav'})

    # =========================================================
    # 3. 计算 A = 实际单耗 - 技改节约值
    # =========================================================
    df_a = actual_df.merge(
        jg_df[['Entity', 'Material', 'jg_sav']],
        on=['Entity', 'Material'],
        how='left'
    )
    df_a['jg_sav'] = df_a['jg_sav'].fillna(0)
    df_a['A'] = df_a['actual_unit'] - df_a['jg_sav']

    # =========================================================
    # 4. MQ00 不经过中类折算，A 直接作为预算值
    # =========================================================
    df_a['data'] = df_a['A']

    # =========================================================
    # 5. 整理最终结果（Y0 版本 1-12 月）
    # =========================================================
    result = df_a[['Entity', 'Material', 'Year', 'Account', 'Period', 'Department',
                   'Allocation', 'Misc1', 'Misc2', 'Tax', 'Version', 'Scenario', 'Measure', 'data']].copy()
    result['Year'] = str(year)
    result['Scenario'] = 'Budget'
    result['Version'] = 'Y0'

    # =========================================================
    # 6. 保存
    # =========================================================
    cube.save(result, chunksize=200000)
    print(f"✅ MQ00 Y0 预算单耗计算完成，共 {len(result)} 条记录")
    return result


def main(p1, p2):
    if 'Year_wb1' in p2 and p2['Year_wb1']:
        year = str(p2['Year_wb1'])
    else:
        BudYear = Variable('Variable').get('BudYear')
        year = BudYear

    if 'Entity_wb1' in p2 and p2['Entity_wb1']:
        Entity = str(p2['Entity_wb1']).replace('PS','XN')

    else:
        Entity = 'Base(#root,0)'


    Version = p2['Version_wb1']


    # 从传参获取物料列表，默认全量
    material_list = p2.get('Material_wb1', ['MQ01', 'MQ03', 'MQ05', 'MQ00'])

    # 分离物料组：化学/污泥组（需中类折算）和电耗组（MQ00，无需中类折算）
    chem_sludge_materials = [m for m in material_list if m in ('MQ01', 'MQ03', 'MQ05')]
    power_materials = [m for m in material_list if m == 'MQ00']

    # 先执行 MQ01/MQ03/MQ05
    if chem_sludge_materials:
        print(f"🔧 处理化学/污泥物料组: {chem_sludge_materials}")
        material_processing(p1, p2, Entity, year, Version, material_list=chem_sludge_materials)
        calc_y0_budget(p1, p2, year, Version)
    else:
        print("⏭️ 无化学/污泥物料，跳过")

    # 再执行 MQ00（电度电量）
    if power_materials:
        print(f"🔧 处理电耗物料组: MQ00")
        material_processing_mq00(p1, p2, year, Version)
        calc_y0_budget_mq00(p1, p2, year, Version)
    else:
        print("⏭️ 无 MQ00 电耗物料，跳过")

# debug
if __name__ == '__main__':
    para2 = {'elementName': 'Material_JG_Fill',
             'folderId': 'DIR5b7224b8400b',
             'sheetName': '技改计划单耗填报',
             'sheetId': 'SHT3f5d35b891964f928f012276291ee312',
             'Year_wb1': '2026',
             'Entity_wb1': 'PS61001_01',
             'Version_wb1': 'Y1',
             'Material_wb1': ['MQ01']}

    main(para1, para2)

