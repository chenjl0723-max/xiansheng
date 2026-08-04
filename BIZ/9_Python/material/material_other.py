# -*- coding: utf-8 -*-
'''
@file    : material_other.py
@Time    : 2025-09-10
@Author  : Chen
@Software:
@Desc    : 其他原材料计算脚本
'''

import traceback
import pandas as pd
import numpy as np
from deepfos.element.datatable import DataTableMySQL
from deepfos.element.finmodel import FinancialCube
from deepfos.element.dimension import Dimension
from deepfos.element.variable import Variable
from numpy.ma import filled

from budget.Python.biz.water_revenue.operational_plan import columns


class MaterialOther:
    def __init__(self, p2):
        self.year = p2['Year_wb1']
        self.entity = p2['Entity_wb1']
        # self.scenario = p2['Scenario_wb1']
        # self.version = p2['Version_wb1']
        # self.department = p2['Department_wb1']
        # self.tax = p2['Tax_wb1']
        self.cube_name = 'S_Cube'
        self.path = '/1_Cube/Financial_Model'

        # 获取其他原材料二维表数据
        tb_material = DataTableMySQL('Othere_Material')
        cols = ['Year','Entity','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec']

        if self.entity == 'Base(1,0)':
            where = "Year = '%s' " % (self.year)
            self.df_Othere_Material = tb_material.select(columns=cols, where=where)

        else:
            where = "Year = '%s' and Entity = '%s'" % (
                self.year, self.entity)
            self.df_Othere_Material = tb_material.select(columns=cols, where=where)



        print(self.df_Othere_Material)

    def process(self):
        df = self.df_Othere_Material.copy()
        df['Account'] = 'SPL01020101'
        df['Material'] = '100'
        df['Version'] = 'Y1'
        df['Scenario'] = 'Budget'
        df['Tax'] = 'Tax'
        df['Measure'] = 'Expenses'
        df['Department'] = 'Operation'
        df['Format'] = 'NoFormat'
        df['Project_Type'] = 'NoProject_Type'
        df['PM_Chars'] = 'NoPM_Chars'
        df['Misc1'] = 'Nomisc1'
        df['Misc2'] = 'Nomisc2'
        df['Misc3'] = 'Nomisc3'

        df = df.rename(columns={
            'Jan': '1',
            'Feb': '2',
            'Mar': '3',
            'Apr': '4',
            'May': '5',
            'Jun': '6',
            'Jul': '7',
            'Aug': '8',
            'Sep': '9',
            'Oct': '10',
            'Nov': '11',
            'Dec': '12'
        })


        cols = ['Year','Entity','Account','Material','Version','Scenario','Tax','Measure','Department','Format','Project_Type','PM_Chars','Misc1','Misc2','Misc3']
        df = df.melt(
            id_vars=cols,
            value_vars=[str(i) for i in range(1, 13)],
            var_name='Period',
            value_name='data'
        )

        # ----------------新增：按月份分组聚合----------------
        # 聚合维度：保留所有id_vars字段 + Period（月份），对data列sum求和（可替换为sum/mean等）
        # 定位分组依据的列（所有维度+月份）
        agg_cols = cols + ['Period']
        # 按月份聚合，数值求和
        df_agg = df.groupby(agg_cols, as_index=False)['data'].sum()

        cube = FinancialCube(element_name=self.cube_name, path=self.path)

        delete_pov = {
            'Year': self.year,
            'Entity': self.entity,
            'Scenario': 'Budget',
            'Period': ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12'],
            'Account': 'SPL01020101',
            'Tax': 'Tax;NoTax',
            'Version': 'Y1',
            'Department': 'Operation',
            'Project_Type': 'NoProject_Type',
            'Format': 'NoFormat',
            'PM_Chars': 'NoPM_Chars',
            'Misc1': 'Nomisc1',
            'Misc2': 'Nomisc2',
            'Misc3': 'Nomisc3',
            'Material': '100',
            'Measure': 'Expenses'
        }
        cube.delete(delete_pov)
        cube.save(df_agg)
        # print(df)



def main(p1, p2):
    calc = MaterialOther(p2)
    calc.process()



# debug
if __name__ == '__main__':
    from BIZ._debug import para1, para2

    para2 =  {'elementName': 'Material_Centralized',
              'folderId': 'DIR40444ad68bfb',
              'sheetName': '其他原材料',
              'sheetId': 'SHT63e73b9ee37546ae8d904f4c4dd9fd16',
              'Year_wb1': '2026',
              'Entity_wb1': 'Base(1,0)',
              'Version_wb1': 'Y1',
              'Scenario_wb1': 'Budget',
              'Tax_wb1': 'Tax',
              'Department_wb1': 'Operation'}
    main(para1, para2)










