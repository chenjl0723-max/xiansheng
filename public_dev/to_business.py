# 业务预算技改计划推送经营计划_已部署

try:
    from _debug import para1, para2
    # print(para1)
except ImportError:
    para1 = para2 = {}

import copy
from public_dev.conf.config import app_name_target
from deepfos.element.finmodel import FinancialCube
from deepfos.element.datatable import DataTableMySQL
from deepfos.db.mysql import MySQLClient

from deepfos.element.dimension import Dimension
from deepfos.options import OPTION
from deepfos.element.variable import Variable

import time
import datetime

import numpy as np
import traceback
import pandas as pd

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)





def execute_budget_function(p1, p2):
    # 处理与业务预算相关的逻辑
    print("开始执行业务预算逻辑...")
    pro_table = DataTableMySQL("project_new")
    col = [
        'project_code',
        'project_name',
        'sub_factory_code',
        'sub_factory_name',
        'pk_manag_org',
        'org_code',
        'org_name',
        'region_code',
        'region_name',
        'area_code',
        'area_name',
        'pk_company',
        'company_code',
        'company_name',
        'M_FIR_BIZ',
        'M_FIR_BIZ_CODE',
        'M_SEC_BIZ',
        'M_SEC_BIZ_CODE',
        'M_BIZ_TYPE_NAME',
        'M_BIZ_TYPE_CODE',
        'invest_model_code',
        'invest_model_name',
        'start_date',
        'end_date'
        ]
    where = ((pro_table.table.M_FIR_BIZ == '污水') & (pro_table.table.PRJ_L3_NAME == '运营项目'))
    df_pro_table = pd.DataFrame(pro_table.select_raw(where= where,columns=col))
    print(df_pro_table)

    p1['app'] = app_name_target
    OPTION.api.header = p1
    entity_table = DataTableMySQL("Entity_ZT_NEW_copy")
    col.remove('project_code')
    print(col)
    entity_table.insert_df(df_pro_table, col)



def execute_operation_plan_function(p1, p2):
    # 处理与经营计划相关的逻辑
    print("开始执行经营计划逻辑...")

    # 可以在此处调用相关的函数或脚本


def main(p1, p2):
    # print(p2)
    application = p2.get('application', '')  # 获取 application 参数
    application_list = application.split(';')
    # print(application_list)
    version = p2.get('version')  # 获取 version 参数
    print(version)

    # 如果 application_list 包含 "业务预算"，执行业务预算相关函数
    if '业务预算' in application_list:
        print("执行业务预算相关函数")
        execute_budget_function(p1, p2)  # 调用业务预算函数

    # 如果 application_list 包含 "经营计划"，执行经营计划相关函数
    if '经营计划' in application_list:
        print("执行经营计划相关函数")
        execute_operation_plan_function(p1, p2)  # 调用经营计划函数

    # 可以根据需要添加更多条件，处理其他应用场景
    else:
        print("没有匹配的应用类型")



if __name__ == '__main__':
    para2 = {'application': '业务预算;经营计划', 'version': 'V1'}
    main(para1, para2)