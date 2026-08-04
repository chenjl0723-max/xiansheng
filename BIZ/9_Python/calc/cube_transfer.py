# -*- coding: utf-8 -*-
'''
@file    : cube_transfer.py
@Time    :
@Author  : chenjl
@Software: PyCharm
@Desc    : 小业态cube1迁移cube2
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



def fun_qurey_dimension(dimension, expression, fields):
    # 维度 实例化
    dim = Dimension(dimension, path='/2_Dimension/')
    # 查询维度现有成员
    df = pd.DataFrame(dim.query(expression=expression, fields=fields, as_model=False))
    del df['id']
    del df['expectedName']

    # df = df.where(df.notnull(), None)
    return df


def query_cube(cube,p2):

    variable = Variable(element_name='Variable', path='/5_Variable/')
    # 推送变量年的
    Year = variable.get('BudYear')


    df_entity = fun_qurey_dimension('Entity', 'IDescendant(#root,0)', ['name', 'ud4','ud5','ud6']
                                    ).rename(columns={"name": "Entity"})
    # 查询cube数据-预算数
    df_budget_01 = cube.query("Year{%s;%s}->Version{Y1}->Scenario{Budget}->Account{Base(SPL,0)}->Material{Base(Total,0)}->"
                         "Tax{Notax;Tax}->Misc1{Nomisc1}->Misc2{Nomisc2}->Misc3{Nomisc3}->Entity{Base(1,0)}->Department{Base(#root,0)}->"
                         "Period{TotalPeriod}->Format{NoFormat}->Project_Type{NoProject_Type}->PM_Chars{NoPM_Chars}"
                         % (Year,str(int(Year)-1)), compact=False)


    df_budget_02 = cube.query(
        "Year{%s;%s}->Version{Y1}->Scenario{Budget}->Account{Base(SYW02,0)}->Material{Base(Total,0)}->"
        "Tax{Notax;Tax}->Misc1{Nomisc1}->Misc2{Nomisc2}->Misc3{Nomisc3}->Entity{Base(1,0)}->Department{Base(#root,0)}->"
        "Period{Noperiod}->Format{NoFormat}->Project_Type{NoProject_Type}->PM_Chars{NoPM_Chars}"
        % (Year, str(int(Year) - 1)), compact=False)

    # 查询cube数据-实际数
    #  -------------------------------------------------------------------------------------------
    df_actual = cube.query("Year{%s;%s;%s}->Version{Y1}->Scenario{Actual}->Account{Base(SPL,0);Base(SYW02,0)}->Material{Base(Total,0)}->"
                         "Tax{Notax;Tax}->Misc1{Nomisc1}->Misc2{Nomisc2}->Misc3{Nomisc3}->Entity{Base(1,0)}->Department{Base(#root,0)}->"
                         "Period{Noperiod}->Format{NoFormat}->Project_Type{NoProject_Type}->PM_Chars{NoPM_Chars}"
                         % (str(int(Year)-1),str(int(Year)-2),str(int(Year)-3)), compact=False)


    df = pd.concat([df_budget_01,df_budget_02, df_actual])
    print(1)

    df = pd.merge(df,df_entity,how='left',on='Entity')
    df.drop(['PM_Chars','Format','Project_Type'],axis=1,inplace=True)
    df = df.rename(columns={"ud4": "Format","ud5":"Project_Type","ud6":"PM_Chars"})

    df['PM_Chars'] = df['PM_Chars'].fillna('NoPM_Chars')
    df['Format'] = df['Format'].fillna('NoFormat')
    df['Project_Type'] = df['Project_Type'].fillna('NoProject_Type')

    return df


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
        cube = FinancialCube('S_Cube')
        # print(df_check)
        df = query_cube(cube, p2)
        df_push(df)
    except Exception as e:
        traceback.print_exc()

# debug
if __name__ == '__main__':
    main(para1, para2)

