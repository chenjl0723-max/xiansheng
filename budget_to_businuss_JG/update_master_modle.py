"""
added by cjl
added in 20241028
added for
主要逻辑：

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

class ToMasterModle:
    def __init__(self,p1):
        p1['app'] = 'yhacsq004'

        # mdms_xm表对象
        xm_table = DataTableMySQL("mdms_xm")
        xm_col = [
            "PRJ_CODE",
            "PRJ_NAME",
            "PK_CO_ORG",
            "LEG_ORG_NAME",
            "LEG_ORG_CODE",
            "ORG_NAME",
            "PK_MANAG_ORG",
            "PRJ_DATA_STAT_NAME",
            "PRJ_START_DATE",
            "PRJ_END_DATE",
            "UND_PRJ_CAT_NAME",
            "UND_PRJ_NAME",
            "UND_PRJ_CODE",
            "IS_NT_COM_OPER",
            "EST_COM_OPER_DATE",
            "ACT_COM_OPER_DATE",
            "INV_MODE_NAME",
            "PRJ_PROV_NAME",
            "PRJ_CITY_NAME",
            "M_FIR_BIZ",
            "M_SEC_BIZ",
            "M_BIZ_TYPE_NAME",
            "PRJ_L1_NAME",
            "PRJ_L2_NAME",
            "PRJ_L3_NAME",
            "PROD_SERV_2ND_CODE",
            "PROD_SERV_2ND_NAME",
            "IS_NT_REL_MAIN_BUS",
            "REL_PRJ_NAME",
            "REL_PRJ_CODE",
            "ACQ_MODE_NAME",
            "PRJ_INV_TTL",
            "PRJ_INV_CTL",
            "CONST_TYPE",
            "REV_SIZE",
            "PD_SIZE_NET_KM",
            "CONST_SIZE_PLT",
            "CONST_SIZE_NET_KM",
            "CON_PER",
            "AGR_WAT_PR",
            "TIRR",
            "EIRR",
            "MIN_WAT_VOL",
            "PROJ_TYPE",
            "ANN_CONT_REV",
            "HAND_OVER_DATE",
            "CUR_USE_ECON",
            "M_FIR_BIZ_CODE",
            "M_SEC_BIZ_CODE",
            "M_BIZ_TYPE_CODE",
            "PROJ_PHASE",
            "EQ_SHR_PCT",
            "PD_SIZE_PLT",
            "OP_VOL_DAY",
            "OP_NET_KM"
        ]

        self.df_xm = pd.DataFrame(xm_table.select_raw(columns=xm_col))
        # print("项目中间表",self.df_xm)

        # org表对象
        org_table = DataTableMySQL("mdms_org")
        org_col = ["PK_CO_ORG","USCC"]
        self.df_org = pd.DataFrame(org_table.select_raw(columns=org_col))
        # print("法人组织表",self.df_org)

        # 获取变量年
        year = Variable("Variable")
        self.year = year.get_variable("Year").value
        self.year = '2025'
        print(self.year)

        # 项目信息表和法人组织表进行合并和处理
        self.main_table = self.merge_data()

        # 写入目标表：Basic_Data_Full
        self.target_table = DataTableMySQL("Basic_Data_Full")

        # 只为导出文件与脚本功能无关
        df = pd.DataFrame(self.target_table.select_raw())
        # df = df.replace({r'[^\x00-\x7F]+': ''}, regex=True)
        df.to_csv('Basic_Data_Full.csv',encoding='gbk',index=False, errors='ignore')





    def merge_data(self):
        df_merged = pd.merge(self.df_xm, self.df_org, how='left', left_on='PK_CO_ORG',
                             right_on="PK_CO_ORG")
        df_merged['Year'] = self.year
        df_merged['Version'] = "WorkVersion"
        df_final = df_merged.rename(columns={
            "PRJ_CODE" : "Entity_Number",
            "PRJ_NAME" : "Entity_Name",
            "PK_CO_ORG" : "Incorporated_Company",
            "INV_MODE_NAME" : "Investment",
            "PRJ_PROV_NAME" : "Province",
            "PRJ_CITY_NAME" : "City",
            "M_FIR_BIZ" : "Format_1",
            "M_SEC_BIZ" : "Format_2",
            "PROJ_PHASE" : "Project",
            "EQ_SHR_PCT" : "Ratio",
            "PD_SIZE_PLT" : "Scale_SJ",
            "OP_VOL_DAY" : "Scale_SJCL",
            "OP_NET_KM" : "Scale_GW"
        })

        # print("处理后的表",df_final)
        # df_merged.to_csv('123.csv',encoding='gbk',index=False)
        return df_final

    def load_main_table(self):
        # df = self.target_table.select_raw()
        # print(df)
        # print(p1)
        # print(self.main_table)
        updatecol = list(set(self.main_table.columns) - {"Year", "Entity_Number"})
        # print(self.main_table.columns)
        self.target_table.insert_df(self.main_table,updatecol,chunksize=300)


def main(p1,p2):
    main = ToMasterModle(p1)
    # main.load_main_table()
    # budget_jg_data = pusher.budget_JG(p1)

    # 检查 budget_jg_data 是否为空
    # if budget_jg_data.empty:
    #     print("该水厂下没有技改项目")
    #     return  # 直接返回，结束当前函数

    # pusher.push_business_jg(budget_jg_data,p1)

if __name__ == '__main__':
    # p2 = {'original_status': ['Status06'], 'result_status': 'Status08', 'form_data': [{'entity_id': 'PS21012_01', 'department_id': 'Equipment', 'year_id': '2024'}]}
    main(para1, para2)