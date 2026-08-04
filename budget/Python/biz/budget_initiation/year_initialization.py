# -*- coding: utf-8 -*-
'''
@file    : initialize_entity_ud789.py
@Time    :
@Author  : XMX
@Software: PyCharm
@Desc    : 初始化 水厂分摊比例、原材料基本信息、协议价格、水厂项目基本信息、税率年份复制
'''

from deepfos.element.datatable import DataTableMySQL
from deepfos.element.variable import Variable
from deepfos.element.finmodel import FinancialCube
# from Python.common.commons import *
import pandas as pd
import numpy as np
from datetime import datetime



pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)


class Initialize:
    def __init__(self, p1,p2):
        # 水厂分摊比例
        self.apportion_table = DataTableMySQL("works_project_apportion")
        self.apportion_Data = pd.DataFrame(self.apportion_table.select_raw())

        # 原材料基本信息
        self.material_table = DataTableMySQL("Material_BasicData")
        self.material_Data = pd.DataFrame(self.material_table.select_raw())

        # 协议价格
        self.agr_table = DataTableMySQL("bewg_price_data")
        self.agr_Data = pd.DataFrame(self.agr_table.select_raw())

        # 水厂基本信息
        self.basic_table = DataTableMySQL("basic_info")
        self.basic_Data = pd.DataFrame(self.basic_table.select_raw())

        # # 设备台账——非技改
        # self.equip_nj_table = DataTableMySQL("equipment_profile_NJ")
        # self.equip_nj_Data = pd.DataFrame(self.equip_nj_table.select_raw())
        #
        # # 设备台账——技改
        # self.equip_jg_table = DataTableMySQL("equipment_profile_JG")
        # self.equip_jg_Data = pd.DataFrame(self.equip_jg_table.select_raw())
        #



    # 二维表预算启动更新年份
    def initialize(self,p1, p2):
        # 获取变量年
        year = Variable('Variable').get('BudYear')
        last_year = str(int(year) - 1)
        # print(year)

        # 备份水厂分摊比例
        # self.apportion_Data['Year'] = next_year
        self.apportion_Data.loc[self.apportion_Data['Year'] == last_year, 'Year'] = year
        apportion = self.apportion_Data[(self.apportion_Data['Year'] == year) & (self.apportion_Data['Version']=='Y1')].copy()
        apportion.drop(['_id','_creator','_create_time','_modifier','_modify_time'], axis=1, inplace=True)
        updatecol = list(set(apportion.columns)-{"Operating_the_project","Year"})
        self.apportion_table.insert_df(apportion,updatecol=updatecol)

        # 备份原材料基本信息
        self.material_Data.loc[self.material_Data['Year'] == last_year, 'Year'] = year
        material = self.material_Data[self.material_Data['Year'] == year].copy()
        material.drop(['_id','_creator','_create_time','_modifier','_modify_time'], axis=1, inplace=True)
        updatecol = list(set(material.columns)-{"Ingredient","Year"})
        self.material_table.insert_df(material,updatecol=updatecol,chunksize=500)

        # 备份协议价格 (年份是int类型）
        self.agr_Data.loc[self.agr_Data['Year'] == last_year, 'Year'] = year
        agr = self.agr_Data[self.agr_Data['Year'] == year].copy()
        agr.drop(['_id', '_creator', '_create_time', '_modifier', '_modify_time'], axis=1, inplace=True)
        updatecol = list(set(agr.columns) - {"Entity","Material","Misc1", "Year"})
        agr['push_data_time'] = str(datetime.now())
        self.agr_table.insert_df(agr, updatecol=updatecol,chunksize=500)

        # 水厂基本信息
        self.basic_Data.loc[self.basic_Data['Year'] == last_year, 'Year'] = year
        basic = self.basic_Data[self.basic_Data['Year'] == year].copy()
        basic.drop(['_id', '_creator', '_create_time', '_modifier', '_modify_time'], axis=1, inplace=True)
        updatecol = list(set(basic.columns) - {"entity", "Year"})
        basic['etl_data'] = pd.to_datetime(basic['etl_data'], format='%Y-%m-%d %H:%M:%S')
        self.basic_table.insert_df(basic, updatecol=updatecol,chunksize=500)




    # 复制税率
    def cube_initialize(self,p1,p2):
        # 获取变量年
        year = Variable('Variable').get('BudYear')
        last_year = str(int(year) - 1)
        print(p2)
        cube = FinancialCube("WS_cube")
        # 查询25年预算税率
        fix = "Scenario{Budget}->Year{%s}->Tax{Taxrate}" % last_year

        tax_cube = cube.query(expression=fix,compact=False)
        tax_cube_actual = tax_cube.copy()
        tax_cube_actual['Scenario'] = 'Actual'
        print(tax_cube_actual)
        cube.save(tax_cube_actual)


        tax_cube_budget = tax_cube.copy()
        tax_cube_budget['Year'] = year
        print(tax_cube_budget)
        cube.save(tax_cube_budget)








def main(p1, p2):
    databsae_tools = Initialize(p1, p2)
    databsae_tools.initialize(p1, p2)
    databsae_tools.cube_initialize(p1, p2)


if __name__ == "__main__":
    from common._debug import para1,para2
    main(para1,para2)
