# -*- coding: utf-8 -*-
'''
@file    : BIZ_push.py
@Time    :
@Author  : chenjl
@Software: PyCharm
@Desc    : 北控水务 预算数推送接口
'''


try:
    from BIZ.__debug import para1, para2
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
    dim = Dimension(dimension, path='/2_Dimension/')
    # 查询维度现有成员
    df = pd.DataFrame(dim.query(expression=expression, fields=fields, as_model=False))
    del df['id']
    df = df.where(df.notnull(), None)
    return df


def query_cube(p2, Year, cube_bewg, account):
    # 查询cube数据
    df = cube_bewg.query("Year{%s}->Version{Y1}->Scenario{Budget}->Account{%s}->Material{Base(Total,0)}->"
                         "Tax{Notax;Tax}->Misc1{Nomisc1}->Misc2{Nomisc2}->Misc3{Nomisc3}->Entity{%s}->Department{%s}->"
                         "Period{Base(TotalPeriod,0)}->Format{NoFormat}->Project_Type{NoProject_Type}->PM_Chars{NoPM_Chars}"
                         % (Year, account, p2['Entity'], p2['Department']), compact=False)
    # 剔除Noperiod的数据
    df = df[df['Period'] != 'Noperiod']
    # 根据需要复制成的不同版本 获取不同范围的数据
    if p2['Version'] in ['Y1', 'Y2', 'Y3', 'Y4']:
        # 实际数部分
        variable = Variable(element_name="Variable")
        val = variable.get_value("Forcast")
        #  -------------------------------------------------------------------------------------------
        df_actual = cube_bewg.query("Year{%s}->Version{Y1}->Scenario{%s}->Account{%s}->Material{Base(Total,0)}->"
                                    "Period{Base(Oct,0)}->Tax{Notax;Tax}->Misc1{Nomisc1}->Misc2{Nomisc2}->Misc3{Nomisc3}->"
                                    "Entity{%s}->Department{%s}->Format{NoFormat}->Project_Type{NoProject_Type}->PM_Chars{NoPM_Chars}"
                                    % (int(Year) - 1, 'Forecast', account, p2['Entity'], p2['Department']), compact=False)
        # df_actual.loc[df_actual['Period'] == 'Adjust', 'Period'] = '12'
        # df_actual = df_actual.groupby(['Year', 'Scenario', 'Version', 'Entity', 'Period', 'Material', 'Tax',
        #                                 'Account', 'Department', 'Measure', 'Misc1', 'Misc2', 'Misc3', 'Format', 'Project_Type', 'PM_Chars'],
        #                               as_index=False)['data'].sum()
        df = df.append(df_actual).reset_index(drop=True)

    return df


def apply_account_mapping(df, df_mapping, account_col='Account_code', mapping_col='Account_mapping',measure=None):
    """
    对 DataFrame 应用科目映射
    """
    if df_mapping is None or df_mapping.empty:
        return df

    if measure is None or pd.isna(measure) or measure == '':

        df = df.merge(
            df_mapping.drop_duplicates(),
            left_on=['Account_code','Material'],
            right_on=['Account_cd', 'Material'],
            how='inner'
        )
    else:
        # 用三列关联
        df = df.merge(
            df_mapping.drop_duplicates(),
            left_on=['Account_code', 'Material', measure],
            right_on=['Account_cd', 'Material', measure],
            how='inner'
        )

    # 执行映射：有映射值就替换，没有就保留原科目
    mask = df[mapping_col].notnull()
    df.loc[mask, account_col] = df.loc[mask, mapping_col]

    # 删除临时列
    df = df.drop(columns=['Account_cd', 'Account_mapping'], errors='ignore')
    return df


def merge_dimension_names(df):
    df_entity = fun_qurey_dimension('Entity', 'IDescendant(#root,0)',
                                    ['name', 'description_zh_cn', 'ud3']) \
        .rename(columns={
        "name": "Project_code",
        "description_zh_cn": "Project_name",
        "ud3": "Attribute"
    })

    df_account = fun_qurey_dimension('Account',
                                     "AndFilter(IDescendant(#root,0),Attr(sharedmember,False))",
                                     ['name', 'description_zh_cn']) \
        .rename(columns={
        "name": "Account_code",
        "description_zh_cn": "Account_name"
    })

    """
    关联 Entity 和 Account 的中文名称
    """
    if df_entity is not None and not df_entity.empty:
        df = pd.merge(
            df,
            df_entity[['Project_code', 'Project_name', 'Attribute']],
            on='Project_code',
            how='left'
        )

    if df_account is not None and not df_account.empty:
        df = pd.merge(
            df,
            df_account[['Account_code', 'Account_name']],
            on='Account_code',
            how='left'
        )
    return df



def group_and_sum(df, group_cols, value_col='figure'):
    """
    按指定维度汇总数值
    """
    if df.empty:
        return df

    # 确保 group_cols 中的列都存在
    exist_cols = [col for col in group_cols if col in df.columns]

    df = df.groupby(exist_cols, as_index=False)[value_col].sum()
    return df

def merge_explain_with_mapping(df_main, cube_bewg, Year, account, df_mapping, p2):
    """
    查询编制说明，并按映射表进行科目映射后合并到主数据
    """
    if not account:
        df_main['Budget_Explain'] = None
        return df_main

    # 查询编制说明
    df_Explain = cube_bewg.query(
        "Year{%s}->Version{Y1}->Scenario{Budget}->Account{%s}->Material{Base(Total,0)}->"
     "Tax{Notax;Tax}->Misc1{Nomisc1}->Misc2{Nomisc2}->Misc3{Nomisc3}->Entity{%s}->Department{%s}->"
     "Period{NoPeriod}->Format{NoFormat}->Project_Type{NoProject_Type}->PM_Chars{NoPM_Chars}->Measure{Explain}"
     % (Year, account, 'IDescendant(#root,0)', p2['Department']), compact=False)




    if df_Explain.empty:
        df_main['Budget_Explain'] = None
        return df_main

    # 重命名
    df_Explain = df_Explain.rename(columns={
        'Year': 'Year_Code',
        'Period': 'Period_Code',
        'Entity': 'Project_code',
        'Account': 'Account_code',
        "Tax": "Tax_code",
        'data': 'Explain'
    })

    # df_Explain = df_Explain[['Year_Code', 'Period_Code', 'Project_code', 'Account_code', 'Budget_Explain']].copy()

    # 对编制说明也进行科目映射
    df_Explain = apply_account_mapping(df_Explain, df_mapping, account_col='Account_code',measure=None)

    # 如果同一科目有多条说明，合并成一条
    df_Explain = df_Explain.groupby(
        ['Year_Code', 'Period_Code', 'Project_code', 'Account_code','Tax_code','Department', 'Scenario',],
        as_index=False
    )['Explain'].agg(' | '.join)

    df_Explain = merge_dimension_names(df_Explain)

    df_main = pd.concat([df_main,df_Explain])

    return df_main


def fun_budget_data(cube_bewg, p2):

    # 获取系统变量 预算编制年
    variable = Variable(element_name='Variable', path='/5_Variable/')
    # 推送变量年的
    Year = variable.get('BudYear')
    # 推送指定年的
    # Year = '2024'
    Version = p2['Version']

    # 1.获取映射表
    table_nm = 'Budget_mapping_xyt'
    path_table = '/3_Datatable/Middle_Table/Budget_data/'
    where = ''
    df_budget_mapping = fun_query_mysql(where, table_nm, path_table)
    df_budget_mapping = df_budget_mapping[['Account_cd', 'Material', 'Measure',
                                           'Account_mapping']].drop_duplicates()

    Account = ";".join(df_budget_mapping["Account_cd"].astype(str).tolist())
    # print(result)

    # # 2.查询 Cube 数据 （预算数+预测数）
    df = query_cube(p2, Year, cube_bewg, Account)


    # 3. 重命名
    df = df.rename(columns={
        "Year": "Year_Code",
        "Period": "Period_Code",
        "Entity": "Project_code",
        "Account": "Account_code",
        "Tax": "Tax_code",
        "data": "figure"
    })

    # 限定预算数据mapping关系
    # 4. 应用科目映射（数值部分）
    df = apply_account_mapping(df, df_budget_mapping, measure='Measure')

    # 6. 关联中文名称
    df = merge_dimension_names(df)


    # 7. 汇总（只汇总一次）
    group_cols = ['Year_Code', 'Period_Code', 'Project_code', 'Account_code',
                  'Tax_code', 'Department', 'Scenario', 'Attribute','Material',
                  'Project_name', 'Account_name']
    df = group_and_sum(df, group_cols, value_col='figure')

    # 9. 合并编制说明（带映射）
    df = merge_explain_with_mapping(df, cube_bewg, Year, Account, df_budget_mapping, p2)


    # 操作数据日期
    df['UpdateTime'] = datetime.datetime.now()
    df['Source'] = 'XYT'


    return df

def df_push(df,p1):
    # uat环境
    # from deepfos.options import OPTION
    # p1['app'] = 'yhacsq015'
    # p1['space'] = 'yhacsq'
    # OPTION.api.header = p1
    # table = ck('bewg_budget_data')
    # d = table.delete({"Source": "XYT"})
    # table.insert_df(df)

    # 生产环境
    from deepfos.options import OPTION
    p1['app'] = 'eemapg007'
    p1['space'] = 'eemapg'
    OPTION.api.header = p1
    table = ck('bewg_budget_data')
    d = table.delete({"Source": "XYT"})
    # tb = DataTableMySQL('bewg_budget_data')
    table.insert_df(df)






def main(p1, p2):
    p2 = {"Version": "Y1", "Entity": "Base(#root,0)", "Department": "Base(#root,0)"}
    try:
        cube_bewg = FinancialCube('S_Cube')
        # print(df_check)
        budget_df = fun_budget_data(cube_bewg, p2)
        df_push(budget_df,p1)
    except Exception as e:
        traceback.print_exc()

# debug
if __name__ == '__main__':
    main(para1, para2)

