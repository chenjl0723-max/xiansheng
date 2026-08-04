"""
added by cjl
added in 20241011
added for 预算启动时，将上一年的预算明细数据存进历史表中，然后删除
主要逻辑：无
剩余问题：无
"""

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


class Detail_tools:
    def __init__(self, p1):
        # 获取变量年
        self.year = Variable('Variable').get('BudYear')
        self.year_1 = str(int(self.year) - 1)
        # self.year_2 = str(int(self.year) - 2)

        # 获取设备设施台账信息
        self.target_tab_JG = DataTableMySQL("equipment_profile_JG_details",path="/05_Datatable/05_08_Equipment/")
        self.target_tab_NJ = DataTableMySQL("equipment_profile_NJ_details",path="/05_Datatable/05_08_Equipment/")
        self.backup_tab_JG = DataTableMySQL("equipment_profile_JG_his",path="/05_Datatable/05_08_Equipment/")
        self.backup_tab_NJ = DataTableMySQL("equipment_profile_NJ_his",path="/05_Datatable/05_08_Equipment/")

        # 获取技改季度明细表字段
        jg_col =  self.target_tab_JG.meta.datatableColumn
        self.jg_col =  [item.name for item in jg_col if hasattr(item, 'name')]
        # self.jg_col = self.jg_col.remove('_id')
        columns_to_remove = ['_creator', '_create_time', '_modifier', '_modify_time', '_id']
        # 从列名列表中删除指定元素
        self.jg_col = [col for col in self.jg_col if col not in columns_to_remove]
        self.jg_col = ", ".join(self.jg_col)
        print(self.jg_col)

        # 获取非技改季度明细表字段
        nj_col = self.target_tab_NJ.meta.datatableColumn
        self.nj_col =  [item.name for item in nj_col if hasattr(item, 'name')]
        # self.nj_col = self.nj_col.remove('_id')
        columns_to_remove = ['_creator', '_create_time', '_modifier', '_modify_time', '_id']
        # 从列名列表中删除指定元素
        self.nj_col = [col for col in self.nj_col if col not in columns_to_remove]
        self.nj_col = ", ".join(self.nj_col)
        print(self.nj_col)

        # 创建MySQLClient类
        self.client = MySQLClient()

    def backup_equipment(self):
        """
        在profile表中只存year,year-1两年数据，把year-2年的数据迁移到历史表中
        """
        strsql_NJ = "insert into %s(%s) select %s from %s where year = %s ON DUPLICATE KEY UPDATE code = VALUES(code),year = VALUES(year),version = VALUES(version)" % (
            self.backup_tab_NJ.table_name,
            self.nj_col,
            self.nj_col,
            self.target_tab_NJ.table_name,
            self.year_1
            # self.year_2

        )
        strsql_JG = "insert into %s (%s)select %s from %s where year = %s ON DUPLICATE KEY UPDATE code = VALUES(code),year = VALUES(year),version = VALUES(version)" % (
            self.backup_tab_JG.table_name,
            self.jg_col,
            self.jg_col,
            self.target_tab_JG.table_name,
            self.year_1
            # self.year_2
        )
        insertsql = self.client.exec_sqls([strsql_NJ, strsql_JG])
        print(insertsql)

        # 清除技改、非技改
        self.target_tab_NJ.delete(where=self.target_tab_NJ.table.year == self.year_1)
        self.target_tab_JG.delete(where=self.target_tab_JG.table.year == self.year_1)


def main(p1, p2):
    # 调用方法，完成数据备份及初始化
    eq = Detail_tools(p1)
    # 备份equipment_profile表
    eq.backup_equipment()

if __name__ == "__main__":
    # from conf._evn import p1, p2

    main(para1, para2)
