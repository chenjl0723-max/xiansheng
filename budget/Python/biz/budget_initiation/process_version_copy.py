# -*- coding: utf-8 -*-
'''
@file    : process_version_copy.py
@Time    :
@Author  : XMX
@Software: PyCharm
@Desc    : 北控水务 审批流程 版本复制功能 支持传参 默认值 Y5
'''

import traceback
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
    dim = Dimension(dimension, path='/02_Dimension')
    # 查询维度现有成员
    df = pd.DataFrame(dim.query(expression=expression, fields=fields, as_model=False))
    del df['id']
    df = df.where(df.notnull(), None)
    return df


def get_portion_scope():
    # # 数据导入
    # df = pd.read_excel(r'D:\FH-company\FH_WORK\北控水务业务预算\陈老师提供\科目类科目范围.xlsx')
    # # mysql 实例化
    # client = MySQLClient()
    # client.insert_df(dataframe=df, element_name='share_portion_account_scope',
    #                  table_info={'share_portion_account_scope': {'elementName': 'share_portion_account_scope',
    #                                         'elementType': 'DataTableMySQL',
    #                                         'path': '/Datatable/Middle_Table'}})
    # df = fun_qurey_dimension('Entity', 'Base(PS37030_01,0);Base(PS37046_01,0)', ['name', 'parent_name'])

    # 预算数据映射关系
    table_nm = 'works_project_apportion'
    path_table = '/05_Datatable/05_05_basic_info/'
    where = ''
    df_apportion_mapping = fun_query_mysql(where, table_nm, path_table)
    df_apportion_mapping = df_apportion_mapping.set_index(
        ['water_works', 'Operating_the_project']).stack().reset_index()
    df_apportion_mapping.columns = ['Project_code', 'electric_charge', 'account_type', 'portion']
    # 分摊比例适用科目范围
    table_nm = 'share_portion_account_scope'
    path_table = '/Datatable/Middle_Table'
    where = ''
    df_portion_scope = fun_query_mysql(where, table_nm, path_table)
    # 处理分摊比例数据转换
    df_account_data = pd.DataFrame()
    for i in df_portion_scope.index:
        df_account = fun_qurey_dimension('Account', df_portion_scope['account_expression'][i], ['name'])
        df_account['account_type'] = df_portion_scope['account_type'][i]
        df_account_data = df_account_data.append(df_account).reset_index(drop=True)
    df_mapping_data = pd.merge(df_apportion_mapping, df_account_data.rename(
        columns={"name": "Account_code"}), how='inner')
    return df_mapping_data


def push_limit(Year, Version, df):
    # 初始化
    table = ck('bewg_budget_data')

    # 限定推送范围
    df = df[df['Scenario'] == 'Budget']
    # 剔除Noperiod的数据
    df = df[df['Period'] != 'Noperiod']
    # 剔除Noperiod的数据
    df = df[df['Tax'] != 'Taxrate']

    # 预算数据映射关系
    table_nm = 'budget_mapping'
    path_table = '/Datatable/Middle_Table'
    where = ''
    df_budget_mapping = fun_query_mysql(where, table_nm, path_table)
    df_budget_mapping = df_budget_mapping[['Account', 'Material', 'Department', 'Measure',
                                           'Account_mapping']].drop_duplicates()

    # 限定预算数据mapping关系
    df = pd.merge(df, df_budget_mapping, how='inner')
    # 单独处理A99科目映射
    df.loc[df['Account_mapping'].notnull(), 'Account'] = df['Account_mapping']
    del df['Account_mapping']
    df = df[['Year', 'Period', 'Entity', 'Version', 'Account', 'Tax', 'data']].rename(
        columns={"Year": "Year_Code", "Period": "Period_Code", "Entity": "Project_code", "Version": "Version_Info",
                 "Account": "Account_code", "Tax": "Tax_code", "data": "figure"})
    # 数据汇总
    df = df.groupby(['Year_Code', 'Period_Code', 'Project_code', 'Version_Info', 'Account_code',
                     'Tax_code'], as_index=False)['figure'].sum()

    # 指定推送版本
    df['Version_Info'] = Version

    # 关联中文
    df_entity = fun_qurey_dimension('Entity', 'IDescendant(#root,0)', ['name', 'description_zh_cn']
                                    ).rename(columns={"name": "Project_code", "description_zh_cn": "Project_name"})
    df_account = fun_qurey_dimension('Account', 'IDescendant(#root,0)', ['name', 'description_zh_cn']
                                     ).rename(columns={"name": "Account_code", "description_zh_cn": "Account_name"})
    df_version = fun_qurey_dimension('Version', 'IDescendant(#root,0)', ['name', 'description_zh_cn']
                                     ).rename(columns={"name": "Version_Info", "description_zh_cn": "Version_name"})
    df = pd.merge(df, df_entity, how='left')
    df = pd.merge(df, df_account, how='left')
    df = pd.merge(df, df_version, how='left')

    # 操作数据日期
    df['UpdateTime'] = datetime.datetime.now()
    df['Data_push_Time'] = datetime.datetime.now()

    # # 测试
    # # df.loc[df['Project_code'] == 'XN33007_01', 'Project_code'] = 'XN37046_01'
    # df = df[df['Project_code'].isin(['XN37019_01', 'Y3720210010', 'Y3720210012'])]
    # df.to_excel(r"D:\FH-company\FH_WORK\北控水务业务预算\测试数据\预算数据推送-测试基础数据-XN37019_01.xlsx", index=False)

    # 1、获取项目数据（不分摊数据）
    df_project = df[~df['Project_code'].str.startswith('XN')]

    # 获取分摊科目类型比例数据
    df_portion = get_portion_scope()

    # 2、处理分摊数据 跟项目、水厂关系以及科目范围取交集
    df = pd.merge(df, df_portion, how='inner')
    df.loc[df['portion'].notnull(), 'figure'] = df['figure'] * df['portion']
    del df['account_type']
    del df['portion']
    del df['Project_code']
    df = df.rename(columns={"electric_charge": "Project_code"})
    # 合并分摊数据以及不分摊数据
    df = df.append(df_project).reset_index(drop=True)

    # 部分子项科目需要汇总到父项，详见：预算明细科目汇总映射表。
    table_nm = 'budget_active_parent_mapping'
    path_table = '/Datatable/Middle_Table'
    where = ''
    df_active_parent_mapping = fun_query_mysql(where, table_nm, path_table)
    df = pd.merge(df, df_active_parent_mapping[['active_account', 'parent_account', 'parent_account_name']].rename(
        columns={"active_account": "Account_code"}), how='left')
    df.loc[~df['parent_account'].isnull(), 'Account_code'] = df['parent_account']
    df.loc[~df['parent_account_name'].isnull(), 'Account_name'] = df['parent_account_name']
    del df['parent_account']
    del df['parent_account_name']

    # 数据汇总
    df = df.groupby(['Year_Code', 'Period_Code', 'Project_code', 'Version_Info', 'Account_code',
                     'Tax_code', 'Project_name', 'Account_name', 'Version_name', 'UpdateTime', 'Data_push_Time'
                     ], as_index=False)['figure'].sum()
    if not df.empty:
        # 关联边界性质
        Project_code = ";".join(set(df['Project_code'].to_list()))
        df_entity = fun_qurey_dimension('Entity', Project_code, ['name', 'ud6'])
        df_nature = fun_qurey_dimension('Nature', 'Base(Totalnature,0)', ['name', 'description_zh_cn'])
        df_nature = pd.merge(df_entity, df_nature.rename(columns={"name": "ud6"}))
        df = pd.merge(df, df_nature[['name', 'description_zh_cn']].rename(
            columns={"name": "Project_code", "description_zh_cn": "Attribute"}), how='left')

    # 删除
    d = table.delete({"Year_Code": Year, "Version_Info": Version})
    # 插入数据
    i = table.insert_df(df)
    print("预算数据推送", d, i)


def copy_ps(p2, cube_bewg, Year):
    # p2['Department'] = 'Operation'
    df_ps = fun_qurey_dimension('Entity', 'Entity{Level(#root,0,4,4)}', ['name'])
    ps = ";".join(set(df_ps['name'].to_list()))
    # 获取配置数据
    path_table = '/05_Datatable/05_02_Middle_Table/'
    table_nm = 'measure_parent_write'
    where = ""
    df_measure = fun_query_mysql(where, table_nm, path_table)
    measure = ";".join(set(df_measure['Measure_code'].to_list()))
    df_ps_01 = cube_bewg.query("Year{%s}->Entity{%s}->Scenario{Budget;New}->Version{Y1}->Measure{%s}"
                               % (Year, ps, measure), compact=False)
    df_ps_02 = cube_bewg.query("Year{%s}->Entity{%s}->Scenario{Actual;Forecast}->Version{Y1}->"
                               "Measure{%s}" % (str(int(Year) - 1), ps, measure), compact=False)
    df_ps = df_ps_01.append(df_ps_02).reset_index(drop=True, inplace=False)
    # 数据操作cube
    # 先删
    fix_del = "Year{%s}->Entity{%s}->Scenario{Budget;New}->Version{%s}->Measure{%s}" \
              % (Year, ps, p2['version_to'], measure)
    d = cube_bewg.delete(fix_del)
    print('ps复制前删除Budget;New：', d, p2['version_to'])
    fix_del = "Year{%s}->Entity{%s}->Scenario{Actual;Forecast}->Version{%s}->Measure{%s}" \
              % (str(int(Year) - 1), ps, p2['version_to'], measure)
    d = cube_bewg.delete(fix_del)
    print('ps复制前删除Actual;Forecast：', d, p2['version_to'])
    return df_ps


def version_copy(p1, p2):
    cube_bewg = FinancialCube('WS_cube', path='/01_Cube')

    # 获取系统变量 预算编制年
    variable = Variable(element_name='Variable', path='/03_Variable')
    Year = variable.get('BudYear')

    #
    # Year = '2024'
    # 获取需要复制到的版本
    Version = p2['version_to']
    # # 固定值
    # Version = 'Y5'

    # 查询数据 Y1版本 分批查
    # 1、@cur-Budget
    df_01 = cube_bewg.query("Year{%s}->Scenario{Budget;New}->Version{Y1}" % Year, compact=False)
    # df = df_01[df_01['Tax']=='Taxrate']
    # print(df)

    # 2、(@cur-1)-Actual;Forecast;New
    df_02 = cube_bewg.query("Year{%s}->Scenario{Actual;Forecast}->Version{Y1}" % str(int(Year) - 1), compact=False)
    # 第一年特殊逻辑， 包含（@Var-2、@Var-3 Actual）
    if Year == '2023':
        # 3、@Var-2、@Var-3 Actual
        df_03 = cube_bewg.query("Year{%s;%s}->Scenario{Actual}->Version{Y1}"
                                % (str(int(Year) - 2), str(int(Year) - 3)),
                                compact=False)
        df_02 = df_02.append(df_03).reset_index(drop=True, inplace=False)
    # 合并两块数据
    df = df_01.append(df_02).reset_index(drop=True, inplace=False)

    # 单独复制 PS层级父级可以写入的数据
    df_ps = copy_ps(p2, cube_bewg, Year)
    df = df.append(df_ps).reset_index(drop=True, inplace=False)

    df['Version'] = Version

    # 数据操作cube
    if Year == '2023':
        # 先删
        fix_del = "Year{%s;%s;%s;%s}->Version{%s}" % (Year, str(int(Year) - 1), str(int(Year) - 2),
                                                      str(int(Year) - 3), Version)
    else:
        # 先删
        # fix_del = "Year{%s;%s}->Version{%s}" % (Year, str(int(Year) - 1), Version)

        # 修改删数范围，增加场景控制
        fix_del = "Year{%s}->Version{%s}->Scenario{Budget;New}" % (Year, Version)
        fix_del_last = "Year{%s}->Version{%s}->Scenario{Actual;Forecast}" % (str(int(Year) - 1), Version)
    # w = cube_bewg.insert_null(fix_del_last)

    # d = cube_bewg.insert_null(fix_del)
    # 后插
    # i = cube_bewg.save(df, chunksize=10000)
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


def version_copy_shzb(p2, Year, Version):
    # 查询数据
    table_nm = 'audit_analysi_calc_js'
    path_table = '/Datatable/Middle_Table'
    where = 'where Year = "%s" and Version = "Y1"' % Year
    df_js = fun_query_mysql(where, table_nm, path_table)
    print(df_js.head(10))

    # 指定此次复制版本
    df_js['Version'] = Version
    # 插入更新
    print(df_js.columns)
    updatecol = df_js.drop(columns={'Year', 'Account', 'Scenario', 'Measure', 'Period', 'Tax', 'Version',
                                    'Department', 'Material', 'Allocation', 'Misc1', 'Misc2',
                                    'Entity', 'ud6', 'sheetId'})
    updatecol = list(updatecol.columns.values)
    fun_insert_mysql(df_js, table_nm, path_table, updatecol)
    print(Version, "审核指标中间表复制")


def apportion_copy(p1, p2, Year, Version):
    table_nm = 'works_project_apportion'
    path_table = '/05_Datatable/05_05_basic_info/'
    where = 'where Year = "%s" and Version = "Y1"' % Year
    df_apportion = fun_query_mysql(where, table_nm, path_table)
    df_apportion['Version'] = Version
    df_apportion.drop(['_id', '_creator', '_create_time', '_modifier', '_modify_time'], axis=1, inplace=True)
    updatecol = list(set(df_apportion.columns) - {"Operating_the_project", "Year", "Version"})
    # updatecol = list(updatecol.columns.values)
    fun_insert_mysql(df_apportion, table_nm, path_table, updatecol)

def main(p1, p2):
    # p2 = {'version_to': 'Y7'}
    print(p2)
    try:
        # 判断输入版本是否正确
        version_check = check_version(p2)
        if version_check == 'True':
            # cube版本复制
            Year, Version, df = version_copy(p1, p2)
            # Year = '2025'
            # Version = 'Y5'
            # 复制水厂分摊比例
            apportion_copy(p1, p2, Year, Version)

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
    from common.__debug import para1
    # p1 = {}
    p2 = {'version_to': 'Y10'}
    main(para1, p2)

