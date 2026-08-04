# -*- coding: utf-8 -*-
'''
@file    : water_fee_income_calc.py
@Time    : 2025-09-14
@Author  : Grok
@Software:
@Desc    : 收入汇总表计算实际数全年合计、
           预测、预算、实际数全年合计含税转不含税
'''

import pandas as pd
import numpy as np
from deepfos.element.finmodel import FinancialCube
from deepfos.element.dimension import Dimension
from deepfos.element.variable import Variable

class WaterFeeIncomeCalc:
    def __init__(self, p2):
        variable = Variable(element_name='Variable')
        self.Forcast = variable.get('Forcast')
        self.Forcast = 'Forecast'

        self.year = p2['Year_wb1']  # e.g., '2026'
        self.last_year = str(int(self.year) - 1)  # 2025
        self.entity = p2.get('Entity_wb1', 'Base(1,0)')
        self.cube_name = 'S_Cube'
        self.fix = (
            "Account{%s}->Year{%s}->Scenario{%s}->"
            "Measure{%s}->Period{%s}->Entity{%s}->"
            "Version{%s}->Material{%s}->Department{%s}->"
            "Tax{%s}->Project_Type{%s}->Format{%s}->PM_Chars{%s}->"
            "Misc1{%s}->Misc2{%s}->Misc3{%s}"
        )


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


        # 预测数期间范围
        self.periods_forecast = ['10', '11', '12']

        # 预算数期间范围
        self.periods_budget = ['1','2','3','4','5','6','7','8','9','10','11','12']

        # 预算数期间范围
        self.periods_actual_1_12 = ['1','2','3','4','5','6','7','8','9','10','11','12']
        self.periods_actual_1_9 = ['1','2','3','4','5','6','7','8','9']

        # 需要计算全年合计的科目
        self.account_actual = ['SPL01010101','SPL01010102','SPL010102','SPL010103','SPL010104','SPL010105','SPL010106','SPL010108','SPL010111','SPL010112','SPL010115']
        self.account_budget = ['SPL01010102','SPL010103','SPL010104','SPL010106','SPL010108','SPL010111','SPL010112','SPL010115']

        self.account_actual = ['Base(SPL0101,0)']
        self.account_budget = ['Base(SPL0101,0)']

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



    def notax_actual(self):
        """ 际数月份不含税转含税"""
        cube = FinancialCube('S_Cube', path='/1_Cube/Financial_Model')
        # 删除实际数月份明细含税
        del_fix1 = self.fix % (
            "Base(SPL0101,0)",
            self.last_year,
            "Actual",
            "Expenses",
            "1;2;3;4;5;6;7;8;9;10;11;12",
            self.entity if self.entity else "Base(1,0)",
            "Y1",
            "Nomaterial",
            "Operation",
            "Tax",
            "NoProject_Type",
            "NoFormat",
            "NoPM_Chars",
            "Nomisc1",
            "Nomisc2",
            "Nomisc3"
        )
        cube.delete(del_fix1)

        actual_fix1 = self.fix % (
            "Base(SPL0101,0)",
            self.last_year,
            "Actual",
            "Expenses",
            "1;2;3;4;5;6;7;8;9;10;11;12",
            self.entity if self.entity else "Base(1,0)",
            "Y1",
            "Nomaterial",
            "Operation",
            "Notax",
            "NoProject_Type",
            "NoFormat",
            "NoPM_Chars",
            "Nomisc1",
            "Nomisc2",
            "Nomisc3"
        )
        # 1-12月不含税实际数
        df_notax_actual = cube.query(actual_fix1, compact=False)

        # 查询税率
        taxrate_df = self.query_taxrate()

        df_notax_rate = df_notax_actual.merge(
            taxrate_df[['Account', 'Entity', 'Taxrate']],
            how='inner',
            on = ['Entity', 'Account'],
            suffixes=('', '_Tax')
        )

        df_notax_rate['data'] *= (1 + df_notax_rate['Taxrate'])
        df_notax_rate['Tax'] = 'Tax'  # 更新Tax字段为'Tax'
        df_Tax = df_notax_rate.drop(columns=['Taxrate'])

        cube.save(df_Tax)
        print(1)

    def noperiod_cala(self,actual_detail=pd.DataFrame(), forecast_detail=pd.DataFrame(), budget_detail=pd.DataFrame()):

        df_noperiod = pd.concat([actual_detail,budget_detail,forecast_detail],ignore_index=True)


        df_noperiod["Period"] = "Noperiod"
        df_noperiod = df_noperiod.groupby(
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

        return df_noperiod


    def query_taxrate(self):
        # 税率转换逻辑
        cube_bewg = FinancialCube('S_Cube', path='/1_Cube/Financial_Model')
        # 查询税率数据
        tax_rate_query = (
            "Year{%s}->Scenario{Actual}->Version{Y1}->Entity{%s}->Period{Noperiod}->"
            "Material{Nomaterial}->Tax{Taxrate}->Account{Base(SPL0101,0)}->Department{Base(#root,0)}->"
            "Measure{Expenses}->Format{NoFormat}->"
            "Project_Type{NoProject_Type}->PM_Chars{NoPM_Chars}->"
            "Misc1{Nomisc1}->Misc2{Nomisc2}->Misc3{Nomisc3}"
            % (self.last_year,self.entity)
        )
        df_tax_rate = cube_bewg.query(tax_rate_query, compact=False)
        df_tax_rate = df_tax_rate.rename(columns={'data': 'Taxrate'})
        return df_tax_rate


    def process(self):
        cube = FinancialCube(element_name=self.cube_name)
        if self.Forcast == 'Forecast':

            actual_detail = self.fetch_input_data('Actual', self.last_year, self.periods_actual_1_9, self.account_actual)
            forecast_detail = self.fetch_input_data('Forecast', self.last_year, self.periods_forecast, self.account_actual)
            forecast_detail['Scenario'] = 'Actual'
            # budget_detail = self.fetch_input_data('Budget', self.year, self.periods_budget, self.account_budget)
            # noperiod_result = self.noperiod_cala(actual_detail,forecast_detail,budget_detail)
            noperiod_result = self.noperiod_cala(actual_detail,forecast_detail)

        elif self.Forcast == 'Actual':
            actual_detail = self.fetch_input_data('Actual', self.last_year, self.periods_actual_1_12, self.account_actual)
            # budget_detail = self.fetch_input_data('Budget', self.year, self.periods_budget, self.account_budget)
            # noperiod_result = self.noperiod_cala(actual_detail,budget_detail)
            noperiod_result = self.noperiod_cala(actual_detail)
            forecast_detail = pd.DataFrame()

        print(1)


        entity_expr = self.entity if self.entity else "Base(1,0)"

        '''
        pov = {**self.pov,
               'Year': self.year,
               'Scenario': 'Budget',
               'Period': 'Noperiod',
               'Account': self.account_budget,
               'Entity': entity_expr}
        cube.delete(pov)

        pov = {**self.pov,
               'Year': self.last_year,
               'Scenario': 'Actual',
               'Period': 'Noperiod',
               'Account': self.account_actual,
               'Entity': entity_expr}
        cube.delete(pov)


        cube.save(data=noperiod_result)
        '''

        return forecast_detail, noperiod_result


    # 计算预测数、实际数全年合计税率转换
    def tax_conversion(self,forecast_detail,actual_noperiod):
        cube = FinancialCube(element_name=self.cube_name)
        entity_expr = self.entity if self.entity else "Base(1,0)"
        # 获取预算数1-12月收入类数据
        budget_detail = self.fetch_input_data('Budget', self.year, self.periods_budget, ['Base(SPL0101,0)'])

        # 获取预算数税率
        exp = f"Year{{{self.year}}}->Account{{Base(SPL0101,0)}}->Entity{{{entity_expr}}}->Scenario{{Budget}}->Period{{Noperiod}}->Version{{Y1}}->Tax{{Taxrate}}"
        budget_taxrate = cube.query(expression=exp,compact=False)
        # 获取实际数税率
        exp = f"Year{{{self.last_year}}}->Account{{Base(SPL0101,0)}}->Entity{{{entity_expr}}}->Scenario{{Actual}}->Period{{Noperiod}}->Version{{Y1}}->Tax{{Taxrate}}"
        actual_taxrate = cube.query(expression=exp, compact=False)

        df_taxrate = pd.concat([actual_taxrate,budget_taxrate],ignore_index=True)


        del df_taxrate["Tax"]
        del df_taxrate["Period"]
        # del df_taxrate["Scenario"]
        df_taxrate = df_taxrate.rename(columns={"data": "taxrate"})

        # 计算预算数含税转不含税
        # 拼接税率
        rate_budget_df = pd.merge(budget_detail, df_taxrate, how="inner").fillna(0)
        rate_budget_df["data"] = rate_budget_df["data"] / (
                1 + rate_budget_df["taxrate"]
        )

        # 计算实际数全年合计含税转不含税
        rate_actnoperiod_df = pd.merge(actual_noperiod, df_taxrate, how="inner").fillna(0)
        rate_actnoperiod_df["data"] = rate_actnoperiod_df["data"] / (
                1 + rate_actnoperiod_df["taxrate"]
        )

        # 不含税金额
        tax_amount_df = pd.concat([rate_budget_df,rate_actnoperiod_df],ignore_index=True)

        # 如果变量为预测时，计算预测数含税转不含税
        if self.Forcast == 'Forecast':
            # 拼接税率
            rate_forecast_df = pd.merge(forecast_detail, df_taxrate, how="left").fillna(0)
            rate_forecast_df['Scenario'] = 'Forecast'
            rate_forecast_df["data"] = rate_forecast_df["data"] / (
                    1 + rate_forecast_df["taxrate"]
            )
            tax_amount_df = pd.concat([tax_amount_df,rate_forecast_df],ignore_index=True)

        # 数据处理
        del tax_amount_df["taxrate"]
        tax_amount_df["Tax"] = "Notax"

        print(1)
        # 清除数据
        # 1.清除不含税预算数
        del_fix1 = self.fix % (
            "Base(SPL0101,0)",
            self.year,
            "Budget",
            "Expenses",
            "1;2;3;4;5;6;7;8;9;10;11;12",
            self.entity if self.entity else "Base(1,0)",
            "Y1",
            "Nomaterial",
            "Operation",
            "Notax",
            "NoProject_Type",
            "NoFormat",
            "NoPM_Chars",
            "Nomisc1",
            "Nomisc2",
            "Nomisc3"
        )
        # 2.清除不含税预测数
        del_fix2 = self.fix % (
            "Base(SPL0101,0)",
            self.last_year,
            "Forecast",
            "Expenses",
            "10;11;12",
            self.entity if self.entity else "Base(1,0)",
            "Y1",
            "Nomaterial",
            "Operation",
            "Notax",
            "NoProject_Type",
            "NoFormat",
            "NoPM_Chars",
            "Nomisc1",
            "Nomisc2",
            "Nomisc3"
        )
        # 2.清除不含税实际数全年合计
        del_fix3 = self.fix % (
            "Base(SPL0101,0)",
            self.last_year,
            "Actual",
            "Expenses",
            "Noperiod",
            self.entity if self.entity else "Base(1,0)",
            "Y1",
            "Nomaterial",
            "Operation",
            "Notax",
            "NoProject_Type",
            "NoFormat",
            "NoPM_Chars",
            "Nomisc1",
            "Nomisc2",
            "Nomisc3"
        )


        if self.Forcast == 'Forecast':
            cube.delete(del_fix2)
        cube.delete(del_fix1)
        cube.delete(del_fix3)
        cube.save(tax_amount_df)



        print(1)


def main(p1, p2):
    calc = WaterFeeIncomeCalc(p2)
    # 计算实际数不含税转含税月份明细
    calc.notax_actual()

    # 计算实际数全年合计，并返回实际数全年合计
    forecast_detail,act_noperiod = calc.process()
    # 对10-12预测数，1-12预算数，实际数全年合计做含税转不含税
    calc.tax_conversion(forecast_detail,act_noperiod)


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