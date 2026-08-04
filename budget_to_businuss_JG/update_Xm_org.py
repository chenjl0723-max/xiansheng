"""
added by cjl
added in 20241028
added for 更新运营项目的维度
主要逻辑：
    根据Entity_ZT_NEW运营项目表，依次写入维度：
    大区、区域、水厂、子水厂、虚拟子水厂、项目
剩余问题：目前项目信息不完善，无法执行代码
"""

try:
    from _debug import para1, para2
    # print(para1)
except ImportError:
    para1 = para2 = {}


from deepfos.element.finmodel import FinancialCube
from deepfos.element.datatable import DataTableMySQL
from deepfos.element.dimension import Dimension
from deepfos.db.mysql import MySQLClient
from deepfos.options import OPTION
from deepfos.element.variable import Variable

import time
import datetime
import pandas as pd
import numpy as np
import traceback
import copy


pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)

class ToMxorg:
    def __init__(self,p1):
        p1['app'] = 'yhacsq004'

        # mdms_xm表对象
        xm_table = DataTableMySQL("mdms_xm")
        xm_col = ["PRJ_CODE","PK_CO_ORG"]
        where = xm_table.table.PK_CO_ORG.notnull()
        self.df_xm = pd.DataFrame(xm_table.select_raw(columns=xm_col,where=where))
        # print("项目中间表",self.df_xm)

        # org表对象
        org_table = DataTableMySQL("mdms_org")
        org_col = ["PK_CO_ORG","USCC"]
        self.df_org = pd.DataFrame(org_table.select_raw())
        # print("法人组织表",self.df_org)

        # 获取变量年
        year = Variable("Variable")
        self.year = year.get_variable("Year").value
        # self.year = '2025'
        print(self.year)



        # 项目信息表和法人组织表进行合并和处理
        self.merge_table = self.merge_data()

        # 写入目标表：Basic_Data_Full
        self.target_table = DataTableMySQL("XM_org")
        # self.df_org = pd.DataFrame(self.target_table.select_raw())
        # print(self.df_org)



        # 只为导出文件与脚本功能无关
        # df = pd.DataFrame(self.target_table.select_raw())
        # # df = df.replace({r'[^\x00-\x7F]+': ''}, regex=True)
        # df.to_csv('Basic_Data_Full.csv',encoding='gbk',index=False, errors='ignore')





    def merge_data(self):
        df_merged = pd.merge(self.df_xm, self.df_org, how='left', left_on='PK_CO_ORG',
                             right_on="PK_CO_ORG")
        df_merged['Year'] = self.year
        df_merged['Version'] = "WorkVersion"

        df_final = df_merged.rename(columns={
            "PRJ_CODE" : "Entity_Number"
        })
        df_final['CHANGEDATE'] = pd.to_datetime(df_final['CHANGEDATE'],format='%Y-%m-%d %H:%M:%S')
        df_final['LASTDATE'] = pd.to_datetime(df_final['LASTDATE'],format='%Y-%m-%d %H:%M:%S')
        df_final = df_final.drop("_id",axis=1)
        # print("处理后的表",df_final)
        # df_merged.to_csv('123.csv',encoding='gbk',index=False)
        return df_final

    def load_main_table(self):
        self.target_table.delete()
        # df = self.target_table.select_raw()
        # print(df)
        # print(p1)
        # print(self.main_table)
        updatecol = list(set(self.merge_table.columns) - {"Entity_Number","Year","Version"})
        # print(updatecol)
        # print("self.merge_table",self.merge_table)
        self.target_table.insert_df(self.merge_table,updatecol,chunksize=300)


def main(p1,p2):
    main = ToMxorg(p1)
    main.load_main_table()
    # budget_jg_data = pusher.budget_JG(p1)

    # 检查 budget_jg_data 是否为空
    # if budget_jg_data.empty:
    #     print("该水厂下没有技改项目")
    #     return  # 直接返回，结束当前函数

    # pusher.push_business_jg(budget_jg_data,p1)

if __name__ == '__main__':
    # p2 = {'original_status': ['Status06'], 'result_status': 'Status08', 'form_data': [{'entity_id': 'PS21012_01', 'department_id': 'Equipment', 'year_id': '2024'}]}
    main(para1, para2)