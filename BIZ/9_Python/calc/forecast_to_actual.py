# -*- coding: utf-8 -*-
'''
@file    : forecast_to_actual.py
@Time    :
@Author  : chenjl
@Software: PyCharm
@Desc    : 场景变更时,预测数转换为实际数
'''

try:
    from BIZ._debug import para1, para2
    # print(para1)
except ImportError:
    para1 = para2 = {}

import pandas as pd
import datetime
import traceback
from deepfos.db.mysql import MySQLClient
from deepfos.element.finmodel import FinancialCube
from deepfos.element.datatable import DataTableClickHouse as ck
from deepfos.element.datatable import DataTableMySQL
from deepfos.element.variable import Variable
from deepfos.element.dimension import Dimension, DimMember

def query_mysql(name):
    dt = DataTableMySQL(name)
    df = dt.select()
    account_ids = df['Account_cd'].to_list()
    # 将 entity_ids 转换为逗号分隔的字符串，用于拼接sql
    account_ids_str = ";".join(account_ids)

    print(account_ids_str)
    return account_ids_str


def fun_qurey_dimension(dimension, expression, fields):
    # 维度 实例化
    dim = Dimension(dimension, path='/2_Dimension/')
    # 查询维度现有成员
    df = pd.DataFrame(dim.query(expression=expression, fields=fields, as_model=False))
    del df['id']
    del df['expectedName']

    # df = df.where(df.notnull(), None)
    return df


def query_cube(cube,account_str,p2):

    variable = Variable(element_name='Variable', path='/5_Variable/')
    # 推送变量年的
    Year = variable.get('BudYear')


    # 查询cube数据-实际数
    #  -------------------------------------------------------------------------------------------
    df_forecast = cube.query("Year{%s}->Version{Y1}->Scenario{Forecast}->Account{%s}->Material{Base(#root,0)}->"
                         "Tax{Notax;Tax}->Misc1{Nomisc1}->Misc2{Nomisc2}->Misc3{Nomisc3}->Entity{Base(1,0)}->Department{Base(#root,0)}->"
                         "Period{10;11;12}->Format{NoFormat}->Project_Type{NoProject_Type}->PM_Chars{NoPM_Chars}"
                         % (str(int(Year)-1),account_str), compact=False)
    df_forecast['Scenario'] = 'Actual'
    print(1)


    return df_forecast


def df_push(df):
    cube2 = FinancialCube('Audit_Cube')
    delete_dict = {
        "Year": ['2023', '2024','2025','2026'],
    "Period":['TotalPeriod','Noperiod'],
    "Version":'Y1'}
    cube2.delete(delete_dict)
    # tb = DataTableMySQL('bewg_budget_data')
    cube2.save(df)


def main(p1, p2):
    p2 = {"Version": "Y1", "Entity": "Base(#root,0)", "Department": "Base(#root,0)"}
    try:
        account_str = query_mysql('Forcast_account')
        cube = FinancialCube('S_Cube')
        # print(df_check)
        df = query_cube(cube, account_str,p2)
        cube.save(df)
    except Exception as e:
        traceback.print_exc()

# debug
if __name__ == '__main__':
    main(para1, para2)

