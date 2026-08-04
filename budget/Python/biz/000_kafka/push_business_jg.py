try:
    from common.__debug import para1, para2
    # print(para1)
except ImportError:
    para1 = para2 = {}

import copy
from budget.Python.common.commons import *
from budget.Python.conf.config import *

# from budget_to_businuss_JG.conf.config import app_name_target
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


class JGToBusiness:
    def __init__(self, p2):
        self.client = MySQLClient()
        # Budget_Production_Middle_Table表对象
        self.act_table = DataTableMySQL("Budget_Production_Middle_Table")

        # 解析参数 转置df
        df_status = pd.DataFrame(p2['form_data'])

        # 处理组织
        entity = list(set(df_status['entity_id'].to_list()))
        self.year = ','.join(df_status['year_id'].astype(str).unique())
        expression = ''
        for i in entity:
            expression += 'Base(%s,0);' % i
        expression = expression[:-1]
        # print(expression)
        df_entity = self.fun_query_dimension('Entity', expression, ['name'])
        # print('df_entity',df_entity)
        self.entity = tuple(df_entity['name'].to_list())
        print('entity',entity)
        # entity_id = "','".join(set(df_entity['name'].to_list()))
        # print('entity_id',entity_id)

    def fun_query_dimension(self, dimension, expression, fields):
        # 维度 实例化
        dim = Dimension(dimension, path='/02_Dimension')
        # 查询维度现有成员
        df = pd.DataFrame(dim.query(expression=expression, fields=fields, as_model=False))
        df = df.rename(columns={'description_zh_cn': 'language_zh-cn'})
        del df['id']
        df = df.where(df.notnull(), None)
        return df

    # 取业务预算的operation_jg表数据
    def budget_JG(self, p1):
        operation_jg_table = DataTableMySQL("Opreation_JG")
        operation_jg_columns = [
            'Year',
            'Entity_Opreation',
            'Entity_Name',
            'JT_ReviewTime',
            'PROJ_TYPE',
            'JG_Reason',
            'Actual_Water',
            'Water_Quality',
            'Now_Emission_Standard',
            'JG_Emission_Standard',
            'Y_CS',
            'Main_Index',
            'JGLast_Water_Yield',
            'JGAfter_Water_Yield',
            'Project_Arrears',
            'Technology',
            'Technology_Total',
            'Add_Cost',
            'YN_TJ',
            'JGLast_Price',
            'JGAfter_Price',
            'Y_State',
            'JG_Start_Time',
            'ADJ_Time',
            'Y1_JG_Amount',
            'YN_JTZDXM',
            'Jan',
            'Feb',
            'Mar',
            'Apr',
            'May',
            'Jun',
            'Jul',
            'Aug',
            'Sep',
            'Oct',
            'Nov',
            'Dec',
            'Q1',
            'Q2',
            'Q3',
            'Q4',
            'Version',
            'Approve_Status',
            'Scenario',
            'PLANCODE',
            'NAME',
            'ISPAID',
            'PAID_TYPE',
            'JXBH_REASON',
            'COST_PERIOD',
            # 'Department',
            '_id'
        ]
        # print(type(self.entity),self.entity)
        where = (operation_jg_table.table.Entity_Opreation.isin(self.entity) & operation_jg_table.table.Year == self.year)
        # print(type(where),where)
        df_operation_jg = pd.DataFrame(operation_jg_table.select_raw(columns=operation_jg_columns, where=where))
        # print(df_operation_jg)

        # 检查 df_operation_jg 是否为空
        if df_operation_jg.empty:
            print("该水厂下没有技改项目")
            return pd.DataFrame()  # 返回空 DataFrame 或者 None，具体取决于后续逻辑

        # 假设 df 是你的 DataFrame
        df_operation_jg['Scenario'] = df_operation_jg['Scenario'].replace({
            'Budget': 'Year',
            'Q1ADJ': 'Q1',
            'Q2ADJ': 'Q2',
            'Q3ADJ': 'Q3',
            'Q4ADJ': 'Q4'
        })

        df_operation_jg['YN_JG'] = 'Y'
        df_operation_jg['Entity_Number'] = df_operation_jg['Entity_Opreation']
        df_operation_jg['Version'] = 'workversion'
        # df_operation_jg['JG_ID'] = df_operation_jg['_id'].astype(str)

        # 查看结果
        print('推送技改计划有：', df_operation_jg)
        budget_jg = df_operation_jg.copy()
        date_columns = ['JG_Start_Time', 'ADJ_Time', 'JT_ReviewTime']
        for col in date_columns:
            budget_jg[col] = pd.to_datetime(budget_jg[col], errors='coerce')
        return budget_jg

        # print(df_equipment_act)

    # 存入经营计划3_operation_jg
    def push_business_jg(self, data, p1):
        # print(p1)
        p1['app'] = 'eemapg004'
        # print(p1)
        OPTION.api.header = p1
        business_JG_table = DataTableMySQL("3_Opreation_JG")
        # updatecol = list(set(data.columns) - {'Year', 'Entity_Opreation', 'Scenario', 'JG_ID'})
        updatecol = list(set(data.columns) - {'PLANCODE'})

        # print(business_JG_table.select_raw())
        # print(data)
        # 需要修改经营计划的3_Opreation_JG表字段类型
        business_JG_table.insert_df(data, updatecol)
        print('运行成功')


    # 存入专项计划3_operation_jg
    def push_zx_jg(self, data, p1):
        # print(p1)
        data = data.rename(columns={'PROJ_TYPE': 'project_type_cd'})
        data['Version'] = 'workversion'
        p1['app'] = 'eemapg009'
        # print(p1)
        OPTION.api.header = p1
        ZX_JG_table = DataTableMySQL("3_Opreation_JG")
        # updatecol = list(set(data.columns) - {'Year', 'Entity_Opreation', 'Scenario', 'JG_ID'})
        updatecol = list(set(data.columns) - {'PLANCODE'})

        # print(business_JG_table.select_raw())
        # print(data)
        # 需要修改经营计划的3_Opreation_JG表字段类型
        ZX_JG_table.insert_df(data, updatecol)
        print('运行成功')

def main(p1, p2):
    # p2 = {'original_status': ['Status06'], 'result_status': 'Status08', 'form_data': [{'entity_id': 'PS21012_01', 'department_id': 'Equipment', 'year_id': '2024'}]}

    pusher = JGToBusiness(p2)
    budget_jg_data = pusher.budget_JG(p1)

    # 检查 budget_jg_data 是否为空
    if budget_jg_data.empty:
        print("该水厂下没有技改项目")
        return  # 直接返回，结束当前函数

    pusher.push_business_jg(budget_jg_data, p1)
    pusher.push_zx_jg(budget_jg_data, p1)


if __name__ == '__main__':
    para2 = {'original_status': ['Status06'], 'result_status': 'Status08',
          'form_data': [{'entity_id': '1', 'department_id': 'Technical', 'year_id': '2025'}]}

    main(para1, para2)
