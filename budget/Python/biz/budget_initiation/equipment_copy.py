# 设备预算版本复制到设备季度明细表


try:
    from common._debug import para1, para2
    print(para1)
except ImportError:
    para1 = para2 = {}
from budget.Python.common.commons import *
from budget.Python.conf.config import *
from deepfos.element.variable import Variable

from deepfos.element.datatable import DataTableMySQL
from deepfos.db.mysql import MySQLClient
import pandas as pd
import datetime
import re

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)


class Adj_tools:
    def __init__(self):
        # 获取变量年
        self.year = Variable('Variable').get('BudYear')
        self.year_1 = str(int(self.year) - 1)
        # self.year_2 = str(int(self.year) - 2)

        # 获取设备设施台账信息
        self.JG_details = DataTableMySQL("equipment_profile_JG_details",path="/05_Datatable/05_08_Equipment")
        self.NJ_details = DataTableMySQL("equipment_profile_NJ_details",path="/05_Datatable/05_08_Equipment")
        self.JG_TB = DataTableMySQL("equipment_profile_JG",path="/05_Datatable/05_08_Equipment")
        self.NJ_TB = DataTableMySQL("equipment_profile_NJ",path="/05_Datatable/05_08_Equipment")

        # 获取技改预算表字段
        jg_col =  self.JG_TB.meta.datatableColumn
        self.jg_col =  [item.name for item in jg_col if hasattr(item, 'name')]
        # self.jg_col = self.jg_col.remove('_id')
        columns_to_remove = ['_creator', '_create_time', '_modifier', '_modify_time', '_id']
        # 从列名列表中删除指定元素
        self.jg_col = [col for col in self.jg_col if col not in columns_to_remove]
        # jg_df = self.JG_TB.select(columns=self.jg_col)
        # print(jg_df)
        #
        # self.jg_col = ", ".join(self.jg_col)
        # print(self.jg_col)

        # 获取非技改预算表字段
        nj_col = self.NJ_TB.meta.datatableColumn
        self.nj_col =  [item.name for item in nj_col if hasattr(item, 'name')]
        # self.nj_col = self.nj_col.remove('_id')
        columns_to_remove = ['_creator', '_create_time', '_modifier', '_modify_time', '_id']
        # 从列名列表中删除指定元素
        self.nj_col = [col for col in self.nj_col if col not in columns_to_remove]
        # self.nj_col = ", ".join(self.nj_col)
        # print(self.nj_col)

        # 创建MySQLClient类
        self.client = MySQLClient()


    def quarter_adjust(self,p2):
        # 获取复制的版本
        version = p2['version_to']

        # 1、技改预算复制到明细表
        where = (self.JG_TB.table.year == self.year)
        jg_df = self.JG_TB.select(columns=self.jg_col,where=where)
        # 筛选条件：sum_new 不为空且不等于 0，或 sum_or 不为空且不等于 0
        filtered_jg_df = jg_df[
            ((jg_df['sum_new'].notna()) & (jg_df['sum_new'] != 0)) |
            ((jg_df['sum_or'].notna()) & (jg_df['sum_or'] != 0))
            ].copy()

        filtered_jg_df.loc[:, 'version'] = version
        # print(filtered_jg_df)
        jg_updatecol = list(set(self.jg_col) - {"code", "year", "version"})
        self.JG_details.insert_df(filtered_jg_df,updatecol=jg_updatecol)

        # 2、常规预算复制到明细表
        where = (self.NJ_TB.table.year == self.year)
        nj_df = self.NJ_TB.select(columns=self.nj_col,where=where)
        # 筛选条件：sum_new 不为空且不等于 0，或 sum_or 不为空且不等于 0
        filtered_nj_df = nj_df[
            ((nj_df['sum_new'].notna()) & (nj_df['sum_new'] != 0)) |
            ((nj_df['sum_or'].notna()) & (nj_df['sum_or'] != 0)) |
            ((nj_df['sum_dc'].notna()) & (nj_df['sum_dc'] != 0)) |
            ((nj_df['sum_dm'].notna()) & (nj_df['sum_dm'] != 0))
            ].copy()

        filtered_nj_df.loc[:, 'version'] = version
        print(filtered_nj_df)
        nj_updatecol = list(set(self.nj_col) - {"code", "year", "version"})
        self.NJ_details.insert_df(filtered_nj_df,updatecol=nj_updatecol)


def main(p1, p2):
    # 调用方法，完成数据备份及初始化
    eq = Adj_tools()
    # 备份equipment_profile表
    eq.quarter_adjust(p2)

if __name__ == "__main__":
    # from conf._evn import p1, p2
    p2 = {'version_to': 'Y5'}
    main(para1, p2)
