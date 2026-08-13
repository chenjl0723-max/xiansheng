# -*- coding: utf-8 -*-
'''
@file    : BIZ_push.py
@Time    :
@Author  : XMX
@Software: PyCharm
@Desc    : 北控水务 预算数推送接口
'''


try:
    from budget.__debug import para1, para2
    # print(para1)
except ImportError:
    para1 = para2 = {}
from deepfos.options import OPTION
import pandas as pd
import datetime
import traceback
from deepfos.db.mysql import MySQLClient
from deepfos.element.datatable import DataTableClickHouse
from deepfos.element.finmodel import FinancialCube
from deepfos.element.datatable import DataTableClickHouse as ck
from deepfos.element.datatable import DataTableMySQL
from deepfos.element.variable import Variable
from deepfos.element.dimension import Dimension, DimMember
import numpy as np


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


def fun_qurey_dimension(dimension, expression, fields):
    # 维度 实例化
    dim = Dimension(dimension, path='/02_Dimension/')
    # 查询维度现有成员
    df = pd.DataFrame(dim.query(expression=expression, fields=fields, as_model=False))
    del df['id']
    df = df.where(df.notnull(), None)
    return df


def query_cube(p2, Year, account):
    cube_bewg = FinancialCube('WS_cube')

    # 查询cube数据
    df = cube_bewg.query("Year{%s}->Version{Y1}->Scenario{Budget}->Allocation{Original}->Account{%s}->"
                         "Tax{Notax;Tax}->Misc1{Nomisc1}->Misc2{Nomisc2}->Entity{%s}->Department{%s}->"
                         "Period{Remove(Base(TotalPeriod,0),Adjust)}"
                         % (Year, account, p2['Entity'], p2['Department']), compact=False)
    # 剔除Noperiod的数据
    df = df[df['Period'] != 'Noperiod']

    # df['Year'] = '2026'
    # 根据需要复制成的不同版本 获取不同范围的数据
    if p2['Version'] in ['Y1', 'Y2', 'Y3', 'Y4']:
        # 实际数部分
        variable = Variable(element_name="Variable")
        val = variable.get_value("Forcast")
        #  -------------------------------------------------------------------------------------------
        df_actual = cube_bewg.query("Year{%s}->Version{Y1}->Scenario{%s}->Allocation{Original}->Account{%s}->"
                                    "Period{Base(Oct,0)}->Tax{Notax;Tax}->Misc1{Nomisc1}->Misc2{Nomisc2}->"
                                    "Entity{%s}->Department{%s}"
                                    % (int(Year) - 1, 'Forecast', account, p2['Entity'], p2['Department']), compact=False)

        # df_actual['Year'] = '2025'
        # df_actual.loc[df_actual['Period'] == 'Adjust', 'Period'] = '12'
        df_actual = df_actual.groupby(['Year', 'Scenario', 'Version', 'Entity', 'Period', 'Material', 'Tax',
                                       'Allocation', 'Account', 'Department', 'Measure', 'Misc1', 'Misc2'],
                                      as_index=False)['data'].sum()
        df = df.append(df_actual).reset_index(drop=True)

    return df


def fun_budget_data(p1, p2):
    # 初始化
    # table = ck('bewg_budget_data')
    # t = table.table
    # 获取系统变量 预算编制年
    # variable = Variable(element_name='Variable', path='/03_Variable/')
    # # 推送变量年的
    # Year = variable.get('BudYear')
    # Year = '2025'

    # 推送指定年的
    # Year = '2024'
    # Version = p2['Version']

    # 预算数据映射关系

    # 公共层应用
    # p1['app'] = 'yhacsq015'
    # OPTION.api.header = p1
    YS_dt = ck('bewg_budget_data')
    cols = ['Project_code','Project_name','Account_code','Account_name','Year_Code','Period_Code','Tax_code','figure','Source']
    YS_df = YS_dt.select(columns=cols)




    df_budget_mapping = fun_query_mysql(where, table_nm, path_table)
    df_budget_mapping = df_budget_mapping[['Account', 'Material', 'Department', 'Measure',
                                           'Account_mapping']].drop_duplicates()

    df_account_mapping = fun_query_mysql(where,'account_mapping','/test')

    df_mapping = df_budget_mapping.merge(df_account_mapping,how="left",left_on='Account',right_on='Account')
    df_cleaned = df_mapping.dropna(subset=['Account_new'])
    Account = ";".join(df_cleaned["Account_new"].astype(str).tolist())
    # print(result)

    p1['app'] = 'eemapg011'
    p1['space'] = 'eemapg'
    OPTION.api.header = p1
    df = query_cube(p2, Year, Account)

    # 限定预算数据mapping关系
    df = pd.merge(df, df_cleaned, how='inner',left_on=['Account','Material','Measure','Department'], right_on=['Account_new','Material','Measure','Department'])
    df = df.drop(['Account_x', 'Account_new','_id'], axis=1)
    df = df.rename(columns={'Account_y':'Account'})
    # 单独处理A99科目映射
    df.loc[df['Account_mapping'].notnull(), 'Account'] = df['Account_mapping']
    del df['Account_mapping']
    df = df[['Year', 'Period', 'Entity', 'Account', 'Tax', 'data']].rename(
        columns={"Year": "Year_Code", "Period": "Period_Code", "Entity": "Project_code",
                 "Account": "Account_code", "Tax": "Tax_code", "data": "figure"})
    # 数据汇总
    df = df.groupby(['Year_Code', 'Period_Code', 'Project_code', 'Account_code',
                     'Tax_code'], as_index=False)['figure'].sum()


    # 操作数据日期
    df['UpdateTime'] = datetime.datetime.now()



    # 关联中文
    df_entity = fun_qurey_dimension('Entity', 'IDescendant(#root,0)', ['name', 'description_zh_cn']
                                    ).rename(columns={"name": "Project_code", "description_zh_cn": "Project_name"})
    del df_entity['expectedName']
    df_account = fun_qurey_dimension('Account', 'IDescendant(#root,0)', ['name', 'description_zh_cn']
                                     ).rename(columns={"name": "Account_code", "description_zh_cn": "Account_name"})
    del df_account['expectedName']

    df = pd.merge(df, df_entity, how='left')
    df = pd.merge(df, df_account, how='left')


    # 数据汇总
    df = df.groupby(['Year_Code', 'Period_Code', 'Project_code', 'Account_code','Tax_code',
                     'Project_name', 'Account_name', 'UpdateTime',], as_index=False)['figure'].sum()





    # 获取分摊科目类型比例数据
    df_project = df[~df['Project_code'].str.startswith('XN')]
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
    print('df4', len(df))

    # 关联中文
    # df_entity = fun_qurey_dimension('Entity', 'IDescendant(#root,0)', ['name', 'description_zh_cn']
    #                                 ).rename(columns={"name": "Project_code", "description_zh_cn": "Project_name"})
    # del df_entity['expectedName']
    # df_account = fun_qurey_dimension('Account', 'IDescendant(#root,0)', ['name', 'description_zh_cn']
    #                                  ).rename(columns={"name": "Account_code", "description_zh_cn": "Account_name"})
    # del df_account['expectedName']
    # df_version = fun_qurey_dimension('Version', 'IDescendant(#root,0)', ['name', 'description_zh_cn']
    #                                  ).rename(columns={"name": "Version_Info", "description_zh_cn": "Version_name"})
    # del df_version['expectedName']
    #
    # df = pd.merge(df, df_entity, how='left')
    # print('df41', len(df))
    # df = pd.merge(df, df_version, how='left')
    # print('df42', len(df))
    # df = pd.merge(df, df_account, how='left')
    # print('df43', len(df))

    # 部分子项科目需要汇总到父项，详见：预算明细科目汇总映射表。
    table_nm = 'budget_active_parent_mapping'
    path_table = '/05_Datatable/05_10_Budget/'
    where = ''
    df_active_parent_mapping = fun_query_mysql(where, table_nm, path_table)
    df = pd.merge(df, df_active_parent_mapping[['active_account', 'parent_account', 'parent_account_name']].rename(
        columns={"active_account": "Account_code"}), how='left')
    df.loc[~df['parent_account'].isnull(), 'Account_code'] = df['parent_account']
    df.loc[~df['parent_account_name'].isnull(), 'Account_name'] = df['parent_account_name']
    del df['parent_account']
    del df['parent_account_name']
    del df['expectedName']

    # 数据汇总
    df = df.groupby(['Year_Code', 'Period_Code', 'Project_code', 'Account_code',
                     'Tax_code',
                     'Project_name', 'Account_name',
                     'UpdateTime'], as_index=False)['figure'].sum()

    if not df.empty:
        # 关联边界性质
        Project_code = ";".join(set(df['Project_code'].to_list()))
        df_entity = fun_qurey_dimension('Entity', Project_code, ['name', 'ud6'])
        del df_entity["expectedName"]
        # df_nature = fun_qurey_dimension('Nature', 'Base(Totalnature,0)', ['name', 'description_zh_cn'])
        # del df_nature["expectedName"]
        print("改了")
        # df_nature = pd.merge(df_entity, df_nature.rename(columns={"name": "ud6"}))
        df = pd.merge(df, df_entity[['name', 'ud6']].rename(
            columns={"name": "Project_code", "ud6": "Attribute"}), how='left')

        df['Source'] = 'YWYS'


    return df

def df_push(df,p1):


    table = ck('bewg_budget_data_ws')
    table.delete({'Year_Code':['2024','2025']})
    # tb = DataTableMySQL('bewg_budget_data')
    table.insert_df(df)


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
    #20241115临时切换表名
    # table_nm = 'works_project_apportion_copy_copy'
    table_nm = 'works_project_apportion'
    path_table = '/05_Datatable/05_05_basic_info/'
    where = ''
    df_apportion_mapping = fun_query_mysql(where, table_nm, path_table)
    df_apportion_mapping = df_apportion_mapping.set_index(
        ['water_works', 'Operating_the_project']).stack().reset_index()
    df_apportion_mapping.columns = ['Project_code', 'electric_charge', 'account_type', 'portion']
    # 分摊比例适用科目范围
    table_nm = 'share_portion_account_scope'
    path_table = '/05_Datatable/05_10_Budget'
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




def main(p1, p2):
    entity_dt = DataTableMySQL("entity_info")
    entity_df = entity_dt.select(columns=['project_code', 'Format', 'Pattern', 'PM_Chars', 'Project_Type', 'Consv_Incrmt'])
    # 公共层应用
    p1['app'] = 'eemapg007'
    OPTION.api.header = p1
    YS_dt = DataTableClickHouse('bewg_budget_data')
    cols = ['Project_code', 'Project_name', 'Account_code', 'Account_name', 'Year_Code', 'Period_Code', 'Tax_code','Scenario','Department',
            'figure', 'Source']
    where = "Project_code not like 'XN%'"
    YS_df = YS_dt.select(columns=cols, where=where)

    # 拆分XYT和YWYS数据
    XYT_df = YS_df[YS_df['Source'] == 'XYT']

    YWYS_df = YS_df[YS_df['Source'] == 'YWYS']

    # 预算科目映射表
    account_map_dt = DataTableMySQL('budget_account_mapping')
    cols = ['Account_cd_lanke','Account_cd_wushui','Account_cd_xiaoyetai']


    account_map_df = account_map_dt.select(columns=cols).rename(columns={
        "Account_cd_lanke": "Account_GB",
        "Account_cd_wushui":"Account",
        "Account_cd_xiaoyetai":"Account_XYT"})

    XYT_df = XYT_df.merge(account_map_df[['Account_GB','Account_XYT']], how='left', left_on='Account_code', right_on='Account_XYT').drop(columns=['Account_code'])
    XYT_df['Account'] = 'Noaccount'
    YWYS_df = YWYS_df.merge(account_map_df[['Account','Account_GB']], how='left', left_on='Account_code', right_on='Account').drop(columns=['Account_code'])
    YWYS_df['Account_XYT'] = 'Noaccount'

    # 根据年份设置Scenario
    # XYT_df['Scenario'] = np.where(XYT_df['Year_Code'] == '2025', 'Forecast', 'Budget')
    # YWYS_df['Scenario'] = np.where(YWYS_df['Year_Code'] == '2025', 'Forecast', 'Budget')

    YS_df = pd.concat([XYT_df, YWYS_df])



    df = YS_df.merge(entity_df, how='left', left_on='Project_code', right_on='project_code')
    df = df.dropna(subset=['project_code'])
    df.drop(['Source','project_code','Source','Account_name','Project_name'], axis=1, inplace=True)
    # df['Department'] = 'Operation'
    df['Measure'] = 'Expenses'
    df['Version'] = 'Y1'
    df['Misc1'] = 'Nomisc1'
    df['Misc2'] = 'Nomisc2'
    df['Misc3'] = 'Nomisc3'
    # df['Format'] = 'F' + df['Format']
    # df['Project_Type'] = 'PT' + df['Project_Type']

    df = df.rename(columns={
        "Period_Code":"Period",
        "figure":"data",
        "Project_code":"Entity_org",
        "Year_Code":"Year",
        "Tax_code":"Tax",
    })
    df['Entity_manag'] = df['Entity_org']

    # 写入业务预算分析模型
    p1['app'] = 'eemapg011'
    OPTION.api.header = p1
    cube = FinancialCube('analytical_model')
    expr_dict = {
        # "Year": ['2020','2021','2022','2023','2024','2025','2026','2027']
        "Entity_org": "IDescendant(#root,0)"
    }

    Account_dim = Dimension('Account')
    Account_list = pd.DataFrame(Account_dim.query(expression="Base(#root,0)", fields=['name'], as_model=False))
    df = df[df['Account'].isin(Account_list['name'])]

    Account_XYT_dim = Dimension('Account_XYT')
    Account_XYT_list = pd.DataFrame(Account_XYT_dim.query(expression="Base(#root,0)", fields=['name'], as_model=False))
    df = df[df['Account_XYT'].isin(Account_XYT_list['name'])]

    Account_GB_dim = Dimension('Account_GB')
    Account_GB_list = pd.DataFrame(Account_GB_dim.query(expression="Base(#root,0)", fields=['name'], as_model=False))
    df = df[df['Account_GB'].isin(Account_GB_list['name'])]
    #
    # Entity_manag_dim = Dimension('Entity_manag')
    # Entity_manag_list = pd.DataFrame(Entity_manag_dim.query(expression="Base(#root,0)", fields=['name'], as_model=False))
    # df = df[df['Entity_manag'].isin(Entity_manag_list['name'])]
    #
    # Entity_org_dim = Dimension('Entity_org')
    # Entity_org_list = pd.DataFrame(Entity_org_dim.query(expression="Base(#root,0)", fields=['name'], as_model=False))
    # df = df[df['Entity_org'].isin(Entity_org_list['name'])]
    #
    cube.insert_null(expr_dict)
    cube.save(df,chunksize=100000)

# debug
if __name__ == '__main__':
    main(para1, para2)

