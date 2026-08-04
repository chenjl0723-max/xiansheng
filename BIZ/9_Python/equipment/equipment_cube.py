# -*- coding: utf-8 -*-
'''
@file    : water_fee_income_calc.py
@Time    : 2025-09-14
@Author  : chen
@Software:
@Desc    : 设备预算进cube
'''

from deepfos.element.datatable import DataTableMySQL
import pandas as pd
from deepfos.element.finmodel import FinancialCube
# from budget.Python.biz.equipment.amount_tax_and_acc_copy import *

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)




class EquipmentCalc:
    def __init__(self, p2):
        self.year = p2['Year_wb1']  # e.g., '2026'
        # self.last_year = str(int(self.year) - 1)  # 2025
        self.entity = p2['Entity_wb1']
        # self.p2 = p2
        self.cube_name = 'S_Cube'
        # self.folder_id = '/1_Cube/Financial_Model'

        # 固定维度，遵循提供的 POV 格式
        self.expr = "Version{Y1}->Department{Equipment}->Tax{Tax}->Project_Type{NoProject_Type}->\
        Format{NoFormat}->PM_Chars{NoPM_Chars}->Misc1{Nomisc1}->Misc2{Nomisc2}->Misc3{Nomisc3}->Material{Nomaterial}->Measure{Expenses}"


        self.pov = {
            'Version': 'Y1',
            'Department': 'Equipment',
            'Scenario': 'Budget',
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

        self.equipment_table = DataTableMySQL('Equipment_profile')
        where = "year = '%s' and entity = '%s' and account is not null" % (
            self.year, self.entity)

        cols = ['year','entity','account','implementation_or','sum',
                'district_amount_er','district_suggestion',
                'region_amount_er','region_suggestion',
                'group_amount_er','group_suggestion']

        self.df_all = self.equipment_table.select(columns=cols, where=where)
        self.df_equipment = self.df_all.rename(columns={
            'sum' : 'data',
            'entity' : 'Entity',
            'year' : 'Year',
            'account' : 'Account'
        })
        self.df_district = self.df_equipment.rename(columns={
            'district_amount_er': 'data',
            'entity': 'Entity',
            'year': 'Year',
            'account': 'Account'
        })
        self.df_region = self.df_equipment.rename(columns={
            'region_amount_er': 'data',
            'entity': 'Entity',
            'year': 'Year',
            'account': 'Account'
        })
        self.df_group = self.df_equipment.rename(columns={
            'group_amount_er': 'data',
            'entity': 'Entity',
            'year': 'Year',
            'account': 'Account'
        })

        print(1)


    def process(self):

        """主处理逻辑"""

        #  1、先处理设备日常维修费
        df_SPL0102040102 = self.df_equipment[self.df_equipment['Account'].isin(['SPL0102040102'])]
        df_SPL0102040102_sum = df_SPL0102040102.groupby(
            by=[
                "Year",
                "Entity",
                "Account",
                "implementation_or"
            ],
            as_index=False,)['data'].sum()

        # 将实施方式I05（委外）的科目替换为SPL010204010201；I06（自主维修）的科目替换为SPL010204010202
        df_SPL0102040102_sum.loc[df_SPL0102040102_sum["implementation_or"] == "I05", "Account"] = "SPL010204010201"
        df_SPL0102040102_sum.loc[df_SPL0102040102_sum["implementation_or"] == "I06", "Account"] = "SPL010204010202"

        # 删除 implementation_or 列
        df_SPL0102040102_sum = df_SPL0102040102_sum.drop(columns=["implementation_or"])

    #++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++

        # 2、在处理大修等其余设备费
        df_equipment = self.df_equipment[~self.df_equipment['Account'].isin(['SPL0102040102'])]

        df_equipment_sum = df_equipment.groupby(
            by=[
                "Year",
                "Entity",
                "Account"
            ],
            as_index=False,)['data'].sum()

        # 3、根据科目汇总完，将数据按照月份拆分，并补齐cube维度
        # 合并两类数据
        df = pd.concat([df_SPL0102040102_sum,df_equipment_sum],ignore_index=True)
        # 将小计分摊至1-12个月中
        # 1）先复制12份
        df_expanded = df.loc[df.index.repeat(12)].copy()  # 每行重复 12 次
        # 2）生成Period列值为1-12
        df_expanded["Period"] = df_expanded.groupby(level=0).cumcount() + 1  # 1-12
        # 3）将每个小计都除以12
        df_expanded["data"] = df_expanded["data"] / 12  # 平均分摊到 12 个月

        # 补cube维度
        for k, v in self.pov.items():
            df_expanded[k] = v

        print(1)
        # 插入cube
        cube = FinancialCube(element_name=self.cube_name)
        cube.save(df_expanded)

def main(p1, p2):
    calc = EquipmentCalc(p2)
    calc.process()


if __name__ == '__main__':
    from BIZ._debug import para1, para2
    para2 =   {'elementName': 'dailycare_equipment',
               'folderId': 'DIR40444ad68bfb',
               'sheetName': '设施日常维护费',
               'sheetId': 'SHTa72a3803d59748f8a17e05e71ec55154',
               'Year_wb1': '2026',
               'Entity_wb1': 'Y5120221036',
               'Department_wb1': 'Equipment',
               'Version_wb1': 'Y1',
               'Format_wb1': 'NoFormat',
               'Project_Type_wb1': 'NoProject_Type',
               'PM_Chars_wb1': 'NoPM_Chars'}



    main(para1, para2)