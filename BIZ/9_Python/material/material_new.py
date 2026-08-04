# -*- coding: utf-8 -*-
'''
@file    : material_calc.py
@Time    : 2025-09-10
@Author  : Chen
@Software:
@Desc    : 非吨泥业态原材料计算脚本（按 Excel 公式和手工录入计算 Actual, Forecast, Budget 和 Noperiod）
'''

import traceback
import pandas as pd
import numpy as np
from deepfos.element.datatable import DataTableMySQL
from deepfos.element.finmodel import FinancialCube
from deepfos.element.dimension import Dimension
from deepfos.element.variable import Variable
from numpy.ma import filled


class MaterialCalc:
    def __init__(self, p2):
        self.year = p2['Year_wb1']  # e.g., '2026'
        self.last_year = str(int(self.year) - 1)  # 2025
        self.entity = p2.get('Entity_wb1', None)  # None means all Entities
        self.p2 = p2
        self.cube_name = 'S_Cube'
        self.folder_id = '/1_Cube/Financial_Model'
        self.forcast = Variable('Variable').get_value('Forcast')

        # 固定维度，遵循提供的 POV 格式
        self.fixed_pov = {
            'Version': 'Y1',
            'Department': 'Operation',
            'Tax': 'Tax',
            'Project_Type': 'NoProject_Type',
            'Format': 'NoFormat',
            'PM_Chars': 'NoPM_Chars',
            'Misc1': 'Nomisc1',
            'Misc2': 'Nomisc2',
            'Misc3': 'Nomisc3',
            'Measure': 'Expenses'
        }

        self.material_pov = {
            'Version': 'Y1',
            'Department': 'Operation',
            'Tax': 'Tax',
            'Project_Type': 'NoProject_Type',
            'Format': 'NoFormat',
            'PM_Chars': 'NoPM_Chars',
            'Misc1': 'Nomisc1',
            'Misc2': 'Nomisc2',
            'Misc3': 'Nomisc3',
            'Measure': 'Expenses'
        }

        self.accounts = ['SYW0309', 'SYW0310', 'SYW0311', 'SYW0312', 'SYW0313', 'SPL01020101']
        self.water_group = ['Base(MQ01,0)', 'Base(MQ03,0)', 'Base(MQ04,0)', 'Base(MQ02,0)', 'Base(MQ99,0)']
        self.dry_sludge_group = ['Base(MQ05,0)']
        self.sludge_group = ['Base(MQ98,0)']
        self.periods_actual = [str(i) for i in range(1, 13)]  # 1-12 月
        self.periods_forecast = ['10', '11', '12']  # 10-12 月
        self.periods_budget = [str(i) for i in range(1, 13)]  # 1-12 月

        self.water_materials = ['MQ01', 'MQ02', 'MQ03', 'MQ04', 'MQ99']
        self.dry_sludge_material = 'MQ05'
        self.sludge_material = 'MQ98'

        # Entity_dim = Dimension('Entity')
        # self.entity_biz = pd.DataFrame(
        #     Entity_dim.query(expression=self.entity, fields=['name', 'ud4'], as_model=False)).rename(
        #     columns={'name': 'Entity',
        #              'ud4': 'Format'})
        # print(self.entity_biz)

    def fetch_cube_data(self, scenario, year, periods, material_group):
        """从 Cube 查询指定物料组的原材料数据"""
        try:
            cube = FinancialCube(element_name=self.cube_name)
            account_expr = f"Account{{{';'.join(self.accounts)}}}"
            material_expr = f"Material{{{';'.join(material_group)}}}"
            period_expr = f"Period{{{';'.join(periods)}}}"
            entity_expr = f"Entity{{{self.entity}}}" if self.entity else "Entity{Base(1,0)}"
            pov = {
                'Year': year,
                'Scenario': scenario,
                **self.material_pov
            }
            exp = f"{account_expr}->{material_expr}->{entity_expr}->Year{{{year}}}->Scenario{{{scenario}}}->{period_expr}"
            data = cube.query(expression=exp, pov=pov, compact=False)

            data['material_category'] = data['Material'].str[:4]

            return data
        except Exception as e:
            print(f"查询 Cube 数据错误 ({scenario}, {year}): {str(e)}")
            return pd.DataFrame()

    def fetch_volume_data(self, scenario, year, periods, account):
        """从 Cube 查询水量、干泥量或泥量数据 (SYW020105, SYW020108, SYW020110)"""
        try:
            cube = FinancialCube(element_name=self.cube_name)
            entity_expr = f"Entity{{{self.entity}}}" if self.entity else "Entity{Base(1,0)}"
            period_expr = f"Period{{{';'.join(periods)}}}"
            # if not self.entity_biz.empty and self.entity_biz['Format'].iloc[0] == 'F050101':
            #     if account == 'SYW020108':
            #         account = 'SYW02030601'
            #     elif account == 'SYW020110':
            #         account = 'SYW0203020201'
            pov = {
                'Year': year,
                'Scenario': scenario,
                'Account': account,
                'Material': 'Nomaterial',
                **self.fixed_pov
            }
            exp = f"Account{{{account}}}->{entity_expr}->Year{{{year}}}->Scenario{{{scenario}}}->{period_expr}"
            data = cube.query(expression=exp, pov=pov, compact=False)
            if not data.empty:
                print(f"查询到 {scenario} {account} 数据，记录数：{len(data)}")
            else:
                print(f"未查询到 {scenario} {account} 数据。")
            return data
        except Exception as e:
            print(f"查询 {account} 数据错误 ({scenario}, {year}): {str(e)}")
            return pd.DataFrame()

    def calculate_group(self, scenario, year, periods, material_group, volume_account):
        """计算指定物料组的业务指标"""
        # 获取物料组数据
        df_raw = self.fetch_cube_data(scenario, year, periods, material_group)
        if df_raw.empty:
            print(f"未检索到 {scenario} {material_group} 物料组数据。")
            return pd.DataFrame()

        # 获取生产基础数据
        df_volume = self.fetch_volume_data(scenario, year, periods, volume_account)
        if df_volume.empty:
            print(f"未检索到 {scenario} {volume_account} 数据。")

        # 处理空数据
        df_pivot = df_raw.pivot_table(
            index=['Year', 'Entity', 'Scenario', 'Period', 'Material', 'material_category'] +list(self.material_pov.keys()),
            columns='Account',
            values='data',
            aggfunc='first'
        ).reset_index()

        # 确保所有科目列存在
        for account in self.accounts:
            if account not in df_pivot.columns:
                df_pivot[account] = np.nan

        # 添加空列以避免合并错误
        df_pivot['volume'] = np.nan

        # 合并原材料与基础生产数据
        if not df_volume.empty:
            df_volume = df_volume[['Entity', 'Period', 'data']].rename(columns={'data': 'volume'})
            df_pivot = df_pivot.drop(columns=['volume'], errors='ignore').merge(
                df_volume, on=['Entity', 'Period'], how='left'
            )

        # 计算药耗（仅 Actual 场景）
        if scenario == 'Actual':
            if material_group == self.water_group:
                df_pivot['SYW0311'] = np.where(
                    df_pivot['SYW0309'].notna() & df_pivot['volume'].notna() & (df_pivot['volume'] != 0),
                    df_pivot['SYW0309'] * 100 / df_pivot['volume'],  # 吨水药耗 (mg/L)
                    df_pivot['SYW0311']
                )
            elif material_group == self.dry_sludge_group:
                df_pivot['SYW0312'] = np.where(
                    df_pivot['SYW0309'].notna() & df_pivot['volume'].notna() & (df_pivot['volume'] != 0),
                    df_pivot['SYW0309'] * 1000 / df_pivot['volume'],  # 吨干泥药耗 (kg/tDS)
                    df_pivot['SYW0312']
                )
            elif material_group == self.sludge_group:
                df_pivot['SYW0313'] = np.where(
                    df_pivot['SYW0309'].notna() & df_pivot['volume'].notna() & (df_pivot['volume'] != 0),
                    df_pivot['SYW0309'] * 1000 / df_pivot['volume'],  # 吨泥药耗 (kg/t)
                    df_pivot['SYW0313']
                )

        # Forecast 和 Budget 场景：计算 SYW0309
        if scenario in ['Forecast', 'Budget']:
            if material_group == self.water_group:
                df_pivot['SYW0309'] = np.where(
                    df_pivot['SYW0311'].notna() & df_pivot['volume'].notna() & (df_pivot['volume'] != 0),
                    df_pivot['SYW0311'] * df_pivot['volume'] / 100,  # 药量 (吨)
                    df_pivot['SYW0309']
                )
            elif material_group == self.dry_sludge_group:
                df_pivot['SYW0309'] = np.where(
                    df_pivot['SYW0312'].notna() & df_pivot['volume'].notna() & (df_pivot['volume'] != 0),
                    df_pivot['SYW0312'] * df_pivot['volume'] / 1000,  # 药量 (吨)
                    df_pivot['SYW0309']
                )
            elif material_group == self.sludge_group:
                # MQ98: SYW0309 保留 Cube 数据（手工录入）
                df_pivot['SYW0309'] = np.where(
                    df_pivot['SYW0313'].notna() & df_pivot['volume'].notna() & (df_pivot['volume'] != 0),
                    df_pivot['SYW0313'] * df_pivot['volume'] / 1000,  # 药量 (吨)
                    df_pivot['SYW0309']
                )




        # 计算 SPL01020101（所有场景）
        df_pivot['SPL01020101'] = np.where(
            df_pivot['SYW0309'].notna() & df_pivot['SYW0310'].notna(),
            df_pivot['SYW0309'] * df_pivot['SYW0310'] / 10000,  # 原材料费用 (万元)
            df_pivot['SPL01020101']
        )

        # 转换回长格式（不包含 material_category）
        df_result = df_pivot.melt(
            id_vars=['Year', 'Entity', 'Scenario', 'Period', 'Material'] + list(self.material_pov.keys()),
            value_vars=self.accounts,
            var_name='Account',
            value_name='data'
        )

        return df_result

    def calculate_for_scenario(self, scenario, periods, year_adjust=0):
        """计算指定场景的 SYW0311, SYW0312, SYW0313 和 SPL01020101"""
        year = str(int(self.year) + year_adjust)
        # 计算水量相关物料组
        df_water = self.calculate_group(scenario, year, periods, self.water_group, 'SYW020105')

        # 计算干泥量相关物料组
        df_mq05 = self.calculate_group(scenario, year, periods, self.dry_sludge_group, 'SYW020108')

        # 计算湿泥产量相关物料组
        df_mq98 = self.calculate_group(scenario, year, periods, self.sludge_group, 'SYW020110')

        # 合并结果
        df_result = pd.concat([df_water, df_mq05, df_mq98])
        if df_result.empty:
            print(f"{scenario} 计算结果为空。")
            return pd.DataFrame()

        return df_result

    def calculate_noperiod(self, df_monthly, scenario, year):
        """计算 Noperiod 全年合计"""
        if df_monthly.empty:
            print(f"{scenario} 月度数据为空，无法计算 Noperiod。")
            return pd.DataFrame()


        # 获取 Noperiod 的水量、干泥量、湿泥产量
        df_water = self.fetch_volume_data(scenario, year, ['Noperiod'], 'SYW020105')
        # df_water['material_category'] =
        df_dry_sludge = self.fetch_volume_data(scenario, year, ['Noperiod'], 'SYW020108')
        df_sludge = self.fetch_volume_data(scenario, year, ['Noperiod'], 'SYW020110')

        df_water = df_water[df_water['Period'] == 'Noperiod'][['Entity', 'data']].rename(columns={'data': 'water_volume'}) if not df_water.empty else pd.DataFrame()
        df_dry_sludge = df_dry_sludge[df_dry_sludge['Period'] == 'Noperiod'][['Entity', 'data']].rename(columns={'data': 'dry_sludge_volume'}) if not df_dry_sludge.empty else pd.DataFrame()
        df_sludge = df_sludge[df_sludge['Period'] == 'Noperiod'][['Entity', 'data']].rename(columns={'data': 'sludge_volume'}) if not df_sludge.empty else pd.DataFrame()

        # 添加物料类别
        df_monthly['material_category'] = df_monthly['Material'].str[:4]

        # 转列
        df_pivot = df_monthly.pivot_table(
            index=['Year', 'Entity', 'Material', 'material_category', 'Period' ] + list(self.fixed_pov.keys()),
            columns='Account',
            values='data',
            aggfunc='first'
        ).reset_index()
        print(1)


        # 确保所有科目列存在
        for account in ['SPL01020101','SYW0309']:
            if account not in df_pivot.columns:
                df_pivot[account] = np.nan

        # 添加空列以避免合并错误
        df_pivot['water_volume'] = np.nan
        df_pivot['dry_sludge_volume'] = np.nan
        df_pivot['sludge_volume'] = np.nan

        # 合并水量、干泥量、湿泥量（若非空）
        if not df_water.empty:
            df_pivot = df_pivot.drop(columns=['water_volume'], errors='ignore').merge(
                df_water, on=['Entity'], how='left'
            )
        if not df_dry_sludge.empty:
            df_pivot = df_pivot.drop(columns=['dry_sludge_volume'], errors='ignore').merge(
                df_dry_sludge, on=['Entity'], how='left'
            )
        if not df_sludge.empty:
            df_pivot = df_pivot.drop(columns=['sludge_volume'], errors='ignore').merge(
                df_sludge, on=['Entity'], how='left'
            )

        # 拆分数据并记录数量
        df_water = df_pivot[df_pivot['material_category'].isin(self.water_materials)]
        df_mq05 = df_pivot[df_pivot['material_category'] == self.dry_sludge_material]
        df_mq98 = df_pivot[df_pivot['material_category'] == self.sludge_material]
        print(f"{scenario} Noperiod 数据拆分：水量相关物料（{len(df_water)} 行），MQ05（{len(df_mq05)} 行），MQ98（{len(df_mq98)} 行）")
        print(df_water[['SYW0309', 'water_volume', 'SYW0311','SPL01020101','SYW0310']].dtypes)
        print(df_water[['SYW0309', 'water_volume', 'SYW0311','SPL01020101','SYW0310']])
        # 计算指标
        # 1. 吨水药耗 (SYW0311)、吨干泥药耗 (SYW0312)、吨泥药耗 (SYW0313)
        if not df_water.empty:
            df_water['SYW0311'] = np.where(
                (df_water['SYW0309'].notna()) &
                (df_water['water_volume'].notna()) &
                (df_water['water_volume'] != 0),
                df_water['SYW0309'] * 100 / df_water['water_volume'],  # 吨水药耗 (mg/L)
                df_water['SYW0311']
            )
        if not df_mq05.empty:
            df_mq05['SYW0312'] = np.where(
                (df_mq05['SYW0309'].notna()) &
                (df_mq05['dry_sludge_volume'].notna()) &
                (df_mq05['dry_sludge_volume'] != 0),
                df_mq05['SYW0309'] * 1000 / df_mq05['dry_sludge_volume'],  # 吨干泥药耗 (kg/tDS)
                df_mq05['SYW0312']
            )
        if not df_mq98.empty:
            df_mq98['SYW0313'] = np.where(
                (df_mq98['SYW0309'].notna()) &
                (df_mq98['sludge_volume'].notna()) &
                (df_mq98['sludge_volume'] != 0),
                df_mq98['SYW0309'] * 1000 / df_mq98['sludge_volume'],  # 吨泥药耗 (kg/t)
                df_mq98['SYW0313']
            )

        # 2. 全年单价 (SYW0310) = 全年原材料费用 (SPL01020101) * 10000 / 全年药量 (SYW0309)
        if not df_water.empty:
            df_water['SYW0310'] = np.where(
                df_water['SYW0309'].isna() | df_water['SPL01020101'].isna(),  # 任一为空
                np.nan,
                np.where(
                    df_water['SYW0309'] == 0,  # 药量为0
                    np.where(df_water['SPL01020101'] == 0, 0.0, np.nan),  # 费用也0 → 单价0，否则空
                    df_water['SPL01020101'] * 10000 / df_water['SYW0309']  # 正常计算单价
                )
            )

        if not df_mq05.empty:
            df_mq05['SYW0310'] = np.where(
                df_mq05['SYW0309'].isna() | df_mq05['SPL01020101'].isna(),
                np.nan,
                np.where(
                    df_mq05['SYW0309'] == 0,
                    np.where(df_mq05['SPL01020101'] == 0, 0.0, np.nan),
                    df_mq05['SPL01020101'] * 10000 / df_mq05['SYW0309']
                )
            )

        if not df_mq98.empty:  # 或者你原来有这个变量就保留，没有就删掉这整段
            df_mq98['SYW0310'] = np.where(
                df_mq98['SYW0309'].isna() | df_mq98['SPL01020101'].isna(),
                np.nan,
                np.where(
                    df_mq98['SYW0309'] == 0,
                    np.where(df_mq98['SPL01020101'] == 0, 0.0, np.nan),
                    df_mq98['SPL01020101'] * 10000 / df_mq98['SYW0309']
                )
            )
        # 合并结果
        df_result = pd.concat([df_water, df_mq05, df_mq98])
        if df_result.empty:
            print(f"{scenario} 计算结果为空。")
            return pd.DataFrame()

        # 转换回长格式（不包含 material_category）
        df_result = df_result.melt(
            id_vars=['Year', 'Entity', 'Period', 'Material'] +list(self.fixed_pov.keys()),
            value_vars=self.accounts,
            var_name='Account',
            value_name='data'
        )

        return df_result


    def process(self):
        cube = FinancialCube(element_name=self.cube_name, path=self.folder_id)
        """主处理逻辑"""
        df_all = pd.DataFrame()

        # 1.计算 Budget 场景（固定计算，不受 Scenario_wb1 影响）
        df_budget = self.calculate_for_scenario('Budget', self.periods_budget, 0)
        df_total_budget = pd.DataFrame()
        if not df_budget.empty:
            df_total_budget = df_budget.groupby(['Entity', 'Material', 'Account', 'Year'] + list(self.fixed_pov.keys())).agg(
                {'data': 'sum'}).reset_index()
            df_total_budget['Period'] = 'Noperiod'

            df_total_budget = self.calculate_noperiod(df_total_budget, 'Budget', self.year)
            df_total_budget['Scenario'] = 'Budget'

        all_budget = pd.concat([df_budget, df_total_budget])
        cube.save(data=all_budget)
        print("Budget 场景计算完成：1-12 月预算数据，Noperiod 使用预算数据（直接查询 Noperiod）")


        # 根据 Scenario_wb1 决定计算哪些场景
        if self.forcast == 'Actual':
            # 计算 Actual 数据（1-12 月，上一年）
            df_actual = self.calculate_for_scenario('Actual', self.periods_actual, -1)
            df_total_actual = pd.DataFrame()
            if not df_actual.empty:
                df_total_actual = df_actual.groupby(
                    ['Entity', 'Material', 'Account', 'Year'] + list(self.fixed_pov.keys())).agg(
                    {'data': 'sum'}).reset_index()
                df_total_actual['Period'] = 'Noperiod'

                df_total_actual = self.calculate_noperiod(df_total_actual, 'Actual',
                                                          self.last_year) if not df_total_actual.empty else pd.DataFrame()
                df_total_actual['Scenario'] = 'Actual'
            all_actual = pd.concat([df_actual, df_total_actual])
            cube.save(data=all_actual)
            print("Actual 场景计算完成：1-12 月实际数据，Noperiod 使用实际数据（Noperiod 体积）")

        elif self.forcast == 'Forecast':
            # 计算 Actual 数据（1-9 月，上一年）
            periods_actual_1_9 = [str(i) for i in range(1, 10)]
            df_actual_1_9 = self.calculate_for_scenario('Actual', periods_actual_1_9, -1)
            # 计算 Forecast 数据（10-12 月，上一年）
            df_forecast = self.calculate_for_scenario('Forecast', self.periods_forecast, -1)
            # 计算 Forecast Noperiod（1-9 月 Actual + 10-12 月 Forecast）
            if not df_actual_1_9.empty or not df_forecast.empty:
                df_total_forecast = pd.concat([
                    df_actual_1_9,
                    df_forecast
                ]).groupby(['Entity', 'Material', 'Account', 'Year'] + list(self.fixed_pov.keys())).agg({'data': 'sum'}).reset_index()

                df_total_forecast['Period'] = 'Noperiod'
                # 重新计算 Forecast Noperiod 的指标
                df_total_forecast = self.calculate_noperiod(df_total_forecast, 'Actual', self.last_year)
                df_total_forecast['Scenario'] = 'Actual'
                df_actual = pd.concat([df_actual_1_9, df_forecast, df_total_forecast])
                cube.save(data=df_actual)
                print("Forecast 场景计算完成：1-9 月实际数据 + 10-12 月预测数据，Noperiod 使用混合数据（Noperiod 体积）")
            else:
                print("Forecast 场景无数据（1-9 月 Actual 或 10-12 月 Forecast 为空）")

        else:
            print(f"不支持的 Scenario_wb1: {self.forcast}")
            return pd.DataFrame()

    def middle_summary(self):

        # 物料映射规则
        material_mapping = {
            'MQ03': '01',
            'MQ01': '02',
            'MQ04': '03',
            'MQ02': '04',
            'MQ05': '05',
            'MQ98': '98',
            'MQ99': '99'
        }

        cube = FinancialCube(element_name=self.cube_name, path=self.folder_id)
        entity_expr = f"Entity{{{self.entity}}}" if self.entity else "Entity{Base(1,0)}"
        exp_forecast = f"Account{{SPL01020101}}->Material{{MQ01;MQ02;MQ03;MQ04;MQ05;MQ98;MQ99}}->{entity_expr}->Year{{{self.last_year}}}->Scenario{{Forecast}}->Period{{10;11;12}}"
        data_forecast = cube.query(expression=exp_forecast, compact=False)

        exp_act = f"Account{{SPL01020101}}->Material{{MQ01;MQ02;MQ03;MQ04;MQ05;MQ98;MQ99}}->{entity_expr}->Year{{{self.last_year}}}->Scenario{{Actual}}->Period{{Noperiod}}"
        data_act = cube.query(expression=exp_act, compact=False)

        exp_budget = f"Account{{SPL01020101}}->Material{{MQ01;MQ02;MQ03;MQ04;MQ05;MQ98;MQ99}}->{entity_expr}->Year{{{self.year}}}->Scenario{{Budget}}->Period{{1;2;;3;4;5;6;7;8;9;10;11;12}}"
        data_budget = cube.query(expression=exp_budget, compact=False)


        df_all = pd.concat([data_forecast, data_act, data_budget])
        df_all['Material'] = df_all['Material'].map(material_mapping)
        df_all['Measure'] = 'Expenses'

        # 删除中类数据
        del_forecast = f"Account{{SPL01020101}}->Material{{01;02;03;04;05;98;99}}->{entity_expr}->Year{{{self.last_year}}}->Scenario{{Forecast}}->Period{{10;11;12}}"
        del_act = f"Account{{SPL01020101}}->Material{{01;02;03;04;05;98;99}}->{entity_expr}->Year{{{self.last_year}}}->Scenario{{Actual}}->Period{{Noperiod}}"
        del_budget = f"Account{{SPL01020101}}->Material{{01;02;03;04;05;98;99}}->{entity_expr}->Year{{{self.year}}}->Scenario{{Budget}}->Period{{1;2;;3;4;5;6;7;8;9;10;11;12}}"
        cube.delete(del_forecast)
        cube.delete(del_act)
        cube.delete(del_budget)

        cube.save(df_all)
        return



def main(p1, p2):
    calc = MaterialCalc(p2)
    calc.process()
    calc.middle_summary()


# debug
if __name__ == '__main__':
    from BIZ.__debug import para1, para2

    para2 = {'elementName': 'Material_Centralized',
             'folderId': 'DIR40444ad68bfb',
             'sheetName': '原材料明细表',
             'sheetId': 'SHTd7a9db725d1e41d2b4977cf11df3e155',
             'Year_wb1': '2026',
             'Entity_wb1': 'Y4320241738',
             'Version_wb1': 'Y1',
             'Scenario_wb1': 'Budget',
             'Tax_wb1': 'Tax',
             'Department_wb1': 'Operation',
             'Tax_st1': 'Tax',
             'Measure_st1': 'Nomeasure'}
    main(para1, para2)