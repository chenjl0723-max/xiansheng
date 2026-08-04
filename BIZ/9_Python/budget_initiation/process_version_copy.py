# -*- coding: utf-8 -*-
# -*- coding: utf-8 -*-
'''
@file    : process_version_copy.py
@Time    :
@Author  : XMX
@Software: PyCharm
@Desc    : 北控水务 审批流程 版本复制功能 支持传参 默认值 Y5
'''

import traceback

from deepfos.element import DataTableMySQL
from deepfos.element.finmodel import FinancialCube
from deepfos.element.variable import Variable
from deepfos.db.mysql import MySQLClient
from deepfos.element.dimension import Dimension, DimMember
from deepfos.element.datatable import DataTableClickHouse as ck
import pandas as pd
import datetime
import traceback

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)


# from _debug import p1, p2


def fun_query_mysql(where, table_nm, path_table):
    # mysql 实例化
    client = MySQLClient()
    # mysql查询
    sql_01 = "select * from ${%s} %s" % (table_nm, where)
    df_table = client.query_dfs(sqls=sql_01,
                                table_info={table_nm: {'elementName': table_nm,
                                                       'elementType': 'DataTableMySQL',
                                                       'path': path_table}})
    return df_table


def fun_insert_mysql(df, table_nm, path_table, updatecol):
    # mysql 实例化
    client = MySQLClient()
    # mysql插入
    client.insert_df(dataframe=df, element_name=table_nm, updatecol=updatecol,
                     table_info={table_nm: {'elementName': table_nm,
                                            'elementType': 'DataTableMySQL',
                                            'path': path_table}})


def fun_qurey_dimension(dimension, expression, fields):
    # 维度 实例化
    dim = Dimension(dimension, path='/2_Dimension')
    # 查询维度现有成员
    df = pd.DataFrame(dim.query(expression=expression, fields=fields, as_model=False))
    del df['id']
    df = df.where(df.notnull(), None)
    return df


# S_Cube 版本复制
def cube1_version_copy(p1, p2):
    cube_bewg = FinancialCube('S_Cube')

    # 获取系统变量 预算编制年
    variable = Variable(element_name='Variable', path='/5_Variable/')
    Year = variable.get('BudYear')

    #
    # Year = '2024'
    # 获取需要复制到的版本
    Version = p2['version_to']
    # # 固定值
    # Version = 'Y5'

    # 查询数据 Y1版本 分批查
    # 1、@cur-Budget
    df_01 = cube_bewg.query("Year{%s;2025}->Scenario{Budget}->Account{Base(#root,0)}->Version{Y1}->Measure{Expenses}" % Year, compact=False)
    df_02 = cube_bewg.query("Year{%s;2025}->Scenario{Budget}->Account{Descendant(#root,0)}->Version{Y1}->Measure{Division;Explain;Areacomment;Regioncomment;Groupcomment;Approve1;Approve2;Approve3;Areaaccount;Regionaccount;Groupaccount}" % Year, compact=False)


    # 2、(@cur-1)-Actual;Forecast;New
    df_03 = cube_bewg.query("Year{%s}->Scenario{Actual;Forecast;Difference}->Account{Base(#root,0)}->Version{Y1}->Measure{Expenses}" % str(int(Year) - 1),
                            compact=False)
    df_04 = cube_bewg.query(
        "Year{%s}->Scenario{Actual;Forecast;Difference}->Account{Descendant(#root,0)}->Version{Y1}->Measure{Division;Explain;Areacomment;Regioncomment;Groupcomment;Approve1;Approve2;Approve3;Areaaccount;Regionaccount;Groupaccount}" % str(int(Year) - 1),
        compact=False)

    # 第一年特殊逻辑， 包含（@Var-2、@Var-3 Actual）

    # 合并两块数据
    df = pd.concat([df_01, df_02,df_03,df_04])


    df['Version'] = Version



    # 修改删数范围，增加场景控制
    fix_del = "Year{%s;2025}->Version{%s}->Scenario{Budget}->Account{IDescendant(#root,0)}->Measure{IDescendant(#root,0)}->Tax{Tax;Notax}" % (Year, Version)
    fix_del_last = "Year{%s}->Version{%s}->Scenario{Actual;Forecast;Difference}->Account{IDescendant(#root,0)}->Measure{IDescendant(#root,0)}->Tax{Tax;Notax}" % (str(int(Year) - 1), Version)
    w = cube_bewg.insert_null(fix_del_last)
    d = cube_bewg.insert_null(fix_del)

    # 后插
    i = cube_bewg.save(df, chunksize=10000)
    # print("cube复制", d, i)
    return Year, Version, df



# Audit_Cube 审核cube 版本复制
def cube2_version_copy(p1, p2):
    cube_bewg = FinancialCube('Audit_Cube')

    # 获取系统变量 预算编制年
    variable = Variable(element_name='Variable', path='/5_Variable/')
    Year = variable.get('BudYear')

    #
    # Year = '2024'
    # 获取需要复制到的版本
    Version = p2['version_to']
    # # 固定值
    # Version = 'Y5'

    # 查询数据 Y1版本 分批查
    # 1、@cur-Budget
    df_01 = cube_bewg.query(
        "Year{%s;2025}->Scenario{Budget}->Department{Base(#root,0)}->Account{Base(#root,0)}->Material{Base(Total,0)}->Version{Y1}->Measure{Expenses}->Period{TotalPeriod;Noperiod}->Format{Base(Format_all,0)}->Project_Type{IBase(PT01,0)}->PM_Chars{Base(PM_all,0)}" % Year,
        compact=False)

    df_02 = cube_bewg.query(
        "Entity{IDescendant(#root,0)}->Year{%s;2025}->Scenario{Budget}->Department{Totaldepartment}->Account{Base(#root,0)}->Material{IBase(Total,0)}->Version{Y1}->Measure{Unit}->Period{TotalPeriod;Noperiod}->Format{F010201;F030101;F02_wg;F080101}->Project_Type{IBase(PT01,0)}->PM_Chars{Base(PM_all,0)}" % Year,
        compact=False)

    # 2、(@cur-1)-Actual;Forecast;New
    df_03 = cube_bewg.query(
        "Year{%s}->Scenario{Actual}->Department{Base(#root,0)}->Account{Base(#root,0)}->Material{Base(Total,0)}->Version{Y1}->Measure{Expenses}->Period{Noperiod}->Format{Base(Format_all,0)}->Project_Type{IBase(PT01,0)}->PM_Chars{Base(PM_all,0)}" % str(int(Year) - 1),
        compact=False)

    df_04 = cube_bewg.query(
        "Entity{IDescendant(#root,0)}->Year{%s}->Scenario{Actual}->Department{Totaldepartment}->Account{Base(#root,0)}->Material{IBase(Total,0)}->Version{Y1}->Measure{Unit}->Period{Noperiod}->Format{F010201;F030101;F02_wg;F080101}->Project_Type{IBase(PT01,0)}->PM_Chars{Base(PM_all,0)}" % str(int(Year) - 1),
        compact=False)
    # 合并两块数据
    df = pd.concat([df_01, df_02,df_03,df_04])

    df['Version'] = Version

    # 修改删数范围，增加场景控制
    fix_del_budget = "Entity{IDescendant(#root,0)}->Year{%s}->Version{%s}->Scenario{Budget}->Account{IDescendant(#root,0)}->Measure{IDescendant(#root,0)}->Period{TotalPeriod;Noperiod}->Format{IDescendant(#root,0)}->Project_Type{IDescendant(#root,0)}->PM_Chars{IDescendant(#root,0)}->Tax{Tax;Notax}" % (Year, Version)
    fix_del_actual = "Entity{IDescendant(#root,0)}->Year{%s}->Version{%s}->Scenario{Actual}->Account{IDescendant(#root,0)}->Measure{IDescendant(#root,0)}->Period{TotalPeriod;Noperiod}->Format{IDescendant(#root,0)}->Project_Type{IDescendant(#root,0)}->PM_Chars{IDescendant(#root,0)}->Tax{Tax;Notax}" % (str(int(Year) - 1), Version)

    d = cube_bewg.insert_null(fix_del_budget)
    d = cube_bewg.insert_null(fix_del_actual)

    # 后插
    i = cube_bewg.save(df, chunksize=10000)
    # print("cube复制", d, i)
    return Year, Version, df


def check_version(p2):
    # 查询维度数据
    dimension = 'Version'
    fields = ['name']
    expression = 'Descendant(#root,0)'
    df_version = fun_qurey_dimension(dimension, expression, fields)
    version_list = df_version['name'].to_list()
    # 默认 不复制 Y1~Y4版本数据
    version_list.remove('Y1')
    # version_list.remove('Y2')
    # version_list.remove('Y3')
    # version_list.remove('Y4')
    print(version_list)

    if p2['version_to'] in version_list:
        version_check = 'True'
    else:
        version_check = 'False'
        print(p2['version_to'], "版本不允许复制")

    return version_check



def profile_version_copy(p1, p2, Year, Version):
    dt = DataTableMySQL("equipment_profile")
    dt_copy = DataTableMySQL("equipment_profile_Retention")
    where = "year = '%s' and version = '%s'" % (Year, Version)
    dt_copy.delete(where=where)

    where = "year = '%s' and version = 'Y1'" % (Year)
    df_equip = pd.DataFrame(dt.select_raw(where=where))


    df_equip.drop(['_id', '_creator', '_create_time', '_modifier', '_modify_time','_sort'], axis=1, inplace=True)
    # 事件类型字段转换
    df_equip['acceptance_month'] = pd.to_datetime(df_equip['acceptance_month'], errors='coerce')
    df_equip['last_overhaul_time'] = pd.to_datetime(df_equip['last_overhaul_time'], errors='coerce')
    df_equip['start_month'] = pd.to_datetime(df_equip['start_month'], errors='coerce')
    df_equip['start_time'] = pd.to_datetime(df_equip['start_time'], errors='coerce')

    df_equip['version'] = Version
    updatecol = list(set(df_equip.columns) - {"code", "year", "version"})
    # updatecol = list(updatecol.columns.values)
    dt_copy.insert_df(df_equip, updatecol)


def main(p1, p2):
    # p2 = {'version_to': 'Y7'}
    print(p2)
    try:
        # 判断输入版本是否正确
        version_check = check_version(p2)
        if version_check == 'True':
            # cube1 版本复制
            Year, Version, df = cube1_version_copy(p1, p2)
            #
            # # cube2 版本复制
            Year, Version, df = cube2_version_copy(p1, p2)

            # Year = '2026'
            # Version = 'Y1'
            # 设备预算二维表 版本复制
            profile_version_copy(p1, p2, Year, Version)

            # Year = '2025'
            # Version = 'Y5'
            # 复制水厂分摊比例
            # apportion_copy(p1, p2, Year, Version)

            # 审核指标中间表复制
            # version_copy_shzb(p2, Year, Version)
            # 预算数之推送Y5版本
            # if ((not df.empty)
            #         and (Version == 'Y5')):
            #     # 预算数中间表推送
            #     push_limit(Year, Version, df)
    except Exception as e:
        traceback.print_exc()

# # debug
if __name__ == '__main__':
    from BIZ._debug import para1
    # p1 = {}
    p2 = {'version_to': 'Y2'}
    main(para1, p2)

