# -*- coding: utf-8 -*-
'''
@file    : water_fee_income_calc.py
@Time    : 2025-09-14
@Author  : chen
@Software:
@Desc    : 管网运营服务收入计算脚本（仅计算 SYW010201 和 SYW010203 的预测数、预算数、全年合计）
'''

import pandas as pd
import numpy as np
from deepfos.element.finmodel import FinancialCube
from deepfos.element.dimension import Dimension


class WaterFeeIncomeCalc:
    def __init__(self, p2):
        self.year = p2['Year_wb1']  # e.g., '2026'
        self.last_year = str(int(self.year) - 1)  # 2025
        self.entity = p2.get('Entity_wb1', None)
        # self.p2 = p2
        self.cube_name = 'S_Cube'
        # self.folder_id = '/1_Cube/Financial_Model'

        # 固定维度，遵循提供的 POV 格式
        self.pov = {
            'Version': 'Y1',
            'Department': 'Operation',
            'Tax': 'Tax',
            'Project_Type': 'NoProject_Type',
            'Format': 'NoFormat',
            'PM_Chars': 'NoPM_Chars',
            'Misc1': 'Nomisc1',
            'Misc2': 'Nomisc2',
            'Misc3': 'Nomisc3',
            'Material': 'Nomaterial',
            'Measure': 'Expenses'
        }

        # 需要从cube获取的值的科目
        self.input_accounts = ['SYW020111', 'SYW010205', 'SYW020112', 'SYW010206', 'SYW010202', 'SYW010207' ,'SYW010208']

        # 需要计算的科目
        self.output_accounts = ['SYW010201', 'SYW010203']

        # 预测数期间范围
        self.periods_forecast = ['10', '11', '12']

        # 预算数期间范围
        self.periods_budget = ['1','2','3','4','5','6','7','8','9','10','11','12']

        # 需要计算全年合计的科目
        self.noperiod_budget = ['SYW010201', 'SYW010202', 'SYW010203' ,'SYW010207', 'SYW010204']


    def fetch_input_data(self, scenario, year, periods,account):
        """从 Cube 查询输入数据"""
        cube = FinancialCube(element_name=self.cube_name)
        account_expr = f"Account{{{';'.join(account)}}}"
        entity_expr = self.entity if self.entity else "Base(1,0)"
        period_expr = f"Period{{{';'.join(periods)}}}"
        pov = {**self.pov, 'Year': year, 'Scenario': scenario}
        exp = f"{account_expr}->Entity{{{entity_expr}}}->Year{{{year}}}->Scenario{{{scenario}}}->{period_expr}"
        data = cube.query(expression=exp, pov=pov, compact=False)
        return data

    def calculate_for_scenario(self, scenario, periods, year_adjust=0):
        """计算指定场景的'SYW010201', 'SYW010203'"""
        year = str(int(self.year) + year_adjust)
        df_input = self.fetch_input_data(scenario, year, periods, self.input_accounts)

        # 将科目转列
        index_cols = [col for col in df_input.columns if col not in ['Account', 'data']]
        df_wide = df_input.pivot_table(
            index=index_cols,
            columns='Account',
            values='data',
            aggfunc='first'
        ).reset_index()

        # 确保所有输入科目列存在，缺失的填0
        for col in self.input_accounts:
            if col in df_wide.columns:
                df_wide[col] = df_wide[col].fillna(0)
            else:
                print(f"警告：列 {col} 不存在，已自动补 0")
                df_wide[col] = 0.0


        # 计算 SYW010101 和 SYW010102
        df_wide['SYW010201'] = df_wide['SYW020111'] * df_wide['SYW010205'] + df_wide['SYW020112'] * df_wide['SYW010206']
        df_wide['SYW010203'] = df_wide['SYW010207'] * (1 + df_wide['SYW010208'])

        if not df_wide.empty:
            # 月度结果
            df_monthly = df_wide[index_cols + self.output_accounts].melt(
                id_vars=index_cols,
                value_vars=self.output_accounts,
                var_name='Account',
                value_name='data'
            )

            return df_monthly
        df_monthly = pd.DataFrame()
        return df_monthly


    def noperiod_cala(self,scenario, periods):
        noperiod_budget = self.fetch_input_data(scenario, self.year, periods, self.noperiod_budget)
        noperiod_budget["Period"] = "Noperiod"
        budget_sum = noperiod_budget.groupby(
            by=[
                "Account",
                "Year",
                "Scenario",
                "Measure",
                "Period",
                "Entity",
                "Version",
                "Material",
                "Department",
                "Tax",
                'Project_Type',
                'Format',
                'PM_Chars',
                "Misc1",
                "Misc2",
                "Misc3",
            ],
            as_index=False,
        ).sum()

        return budget_sum


    def process(self):

        """主处理逻辑"""
        df_f_monthly = self.calculate_for_scenario('Forecast', self.periods_forecast, -1)
        df_b_monthly = self.calculate_for_scenario('Budget', self.periods_budget, 0)

        # 合并预测数、预算数数据
        cube = FinancialCube(element_name=self.cube_name)

        # 插入预测和预算数进入cube
        df_all = pd.concat([df_f_monthly , df_b_monthly], ignore_index=True)
        if not df_all.empty:
            save_cols = ['Year', 'Entity', 'Scenario', 'Period', 'Account', 'data'] + list(self.pov.keys())
            df_save = df_all[[col for col in save_cols if col in df_all.columns]]
            cube.save(data=df_save, data_column='data')
            print("数据计算和保存完成")


        # 计算预算数全年合计
        budget_sum = self.noperiod_cala('Budget',self.periods_budget)
        entity_expr = self.entity if self.entity else "Base(1,0)"
        pov = {**self.pov,
               'Year': self.year,
               'Scenario': 'Budget',
               'Period': 'Noperiod',
               'Account': self.noperiod_budget,
               'Entity': entity_expr}
        cube.delete(pov)
        cube.save(data=budget_sum)


        # 科目复制SYW0102->SPL010102
        SYW0102_f = self.fetch_input_data('Forecast', self.last_year, self.periods_forecast, ['SYW0102'])
        SYW0102_d = self.fetch_input_data('Budget', self.year, self.periods_budget, ['SYW0102'])
        SYW0102_d_sum = self.fetch_input_data('Budget', self.year, ['Noperiod'], ['SYW0102'])

        SPL010102 = pd.concat([SYW0102_f, SYW0102_d, SYW0102_d_sum], ignore_index=True)
        SPL010102['Account'] = 'SPL010102'

        # 删除收入科目的预算数
        pov = {**self.pov,
               'Year': self.year,
               'Scenario': 'Budget',
               'Period': self.periods_budget,
               'Account': 'SPL010102',
               'Entity': entity_expr}
        cube.delete(pov)

        # 删除收入科目的预测数
        pov = {**self.pov,
               'Year': self.last_year,
               'Scenario': 'Forecast',
               'Period': self.periods_forecast,
               'Account': 'SPL010102',
               'Entity': entity_expr}
        cube.delete(pov)

        cube.save(data=SPL010102)
        return



def main(p1, p2):
    calc = WaterFeeIncomeCalc(p2)
    calc.process()


if __name__ == '__main__':
    from BIZ._debug import para1, para2
    para2 =  {'elementName': 'Revenue',
              'folderId': 'DIR40444ad68bfb',
              'sheetName': '明细表-当期处理水费收入',
              'sheetId': 'SHT055638819fcf4724af51b3b233e2c1bb',
              'Year_wb1': '2026',
              'Entity_wb1': 'Base(1,0)',
              'Department_wb1': 'Operation',
              'Tax_wb1': 'Tax',
              'Version_wb1': 'Y1',
              'Format_wb1': 'NoFormat',
              'Project_Type_wb1': 'NoProject_Type',
              'PM_Chars_wb1': 'NoPM_Chars'}

    main(para1, para2)