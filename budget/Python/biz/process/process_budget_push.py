# -*- coding: utf-8 -*-
'''
@file    : process_budget_push.py
@Time    :
@Author  : CHEN
@Software: PyCharm
@Desc    : 北控水务 预算数推送接口
'''


try:
    from budget.__debug import para1, para2
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
    dim = Dimension(dimension, path='/02_Dimension/')

    # 查询维度现有成员
    # df = pd.DataFrame(dim.query(expression=expression, as_model=False))
    df = pd.DataFrame(dim.query(expression=expression, fields=fields, as_model=False))
    del df['id']
    df = df.where(df.notnull(), None)
    return df


def expand_period_12_to_1_12(df):
    """
    将 df 中 Period='12' 的记录拆分成 Period 1~12，每条记录独立平分金额
    :param df: 原 DataFrame
    :return: 处理后的 df
    """
    # 只处理 Period='12' 的行

    # mask = df['Period'] == '12'
    # df_to_expand = df[mask].copy()
    df_to_expand = df.loc[(df['Period'] == '12') & (df['data'] != 0)].copy()
    if df_to_expand.empty:
        return df  # 没有 12 月数据，直接返回原 df

    # 生成 1~12 的 Period 列表
    periods = [str(i) for i in range(1, 13)]

    # 为每条 12 月记录复制 12 份
    expanded_list = []
    for _, row in df_to_expand.iterrows():
        # 复制 12 份该行
        temp_df = pd.DataFrame([row] * 12)
        # 平分金额
        temp_df['data'] = temp_df['data'] / 12
        # 赋值 Period 1~12
        temp_df['Period'] = periods
        expanded_list.append(temp_df)

    # 合并所有拆分后的记录
    df_expanded = pd.concat(expanded_list, ignore_index=True)
    df_expanded['data'] = df_expanded['data'].round(6)  # 保留6位小数

    return df_expanded


def query_cube(p2, Year, cube_bewg, account):
    # 查询cube数据
    df = cube_bewg.query("Year{%s}->Version{Y1}->Scenario{Budget}->Allocation{Original}->Account{%s}->"
                         "Tax{Notax;Tax}->Misc1{Nomisc1}->Misc2{Nomisc2}->Entity{%s}->Department{%s}->"
                         "Material{Base(Total,0)}->Period{Remove(Base(TotalPeriod,0),Adjust)}"
                         % (Year, account, p2['Entity'], p2['Department']), compact=False)

    # 提取设备预算，将设备预算拆分成12个月得数据
    # 设备Account 列表
    target_accounts = [
        'PL0102040101', 'PL010204010201', 'PL010204010202',
        'PL010204010203', 'PL0102040201','PL0102040202','PL0102040203'
    ]

    # 只处理这些 按月份拆分设备数据
    df_equip = df[df['Account'].isin(target_accounts)].copy()
    df_other = df[~df['Account'].isin(target_accounts)].copy()

    df_equip = expand_period_12_to_1_12(df_equip)

    df = pd.concat([df_other,df_equip],ignore_index=True)


    # 获取预测数
    #  -------------------------------------------------------------------------------------------
    df_forecast = cube_bewg.query("Year{%s}->Version{Y1}->Scenario{%s}->Allocation{Original}->Account{%s}->"
                                "Period{Base(Oct,0)}->Tax{Notax;Tax}->Misc1{Nomisc1}->Misc2{Nomisc2}->"
                                "Material{Base(Total,0)}->Entity{%s}->Department{%s}"
                                % (int(Year) - 1, 'Forecast', account, p2['Entity'], p2['Department']), compact=False)


    # df_forecast = df_forecast.groupby(['Year', 'Scenario', 'Version', 'Entity', 'Period', 'Material', 'Tax',
    #                                'Allocation', 'Account', 'Department', 'Measure', 'Misc1', 'Misc2'],
    #                               as_index=False)['data'].sum()
    df = df.append(df_forecast).reset_index(drop=True)

    return df


# ====================== 工具函数封装 ======================

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
                                    ['name', 'description_zh_cn', 'ud6']) \
        .rename(columns={
        "name": "Project_code",
        "description_zh_cn": "Project_name",
        "ud6": "Attribute"
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
        "Year{%s}->Version{Y1}->Scenario{Budget}->Allocation{Original}->Account{%s}->"
        "Tax{Notax;Tax}->Misc1{Nomisc1}->Misc2{Nomisc2}->Entity{%s}->Department{%s}->"
        "Material{Base(Total,0)}->Period{Noperiod}->Measure{Explain}"
        % (Year, account, 'IDescendant(#root,0)', p2['Department']),
        compact=False
    )

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

def material_with_mapping(df_main, cube_bewg, Year, account, df_mapping, p2):
    """
    查询编制说明，并按映射表进行科目映射后合并到主数据
    """
    if not account:
        # df_main['Budget_Explain'] = None
        return df_main
    # Year = '2025'
    account = ';'.join(account)
    # 查询编制说明
    df_material_budget = cube_bewg.query(
        "Year{%s}->Version{Y1}->Scenario{Budget}->Allocation{Original}->Account{%s}->"
        "Tax{Notax;Tax}->Misc1{Nomisc1}->Misc2{Nomisc2}->Entity{%s}->Department{%s}->"
        "Material{Base(Total,0)}->Period{Remove(Base(TotalPeriod,0),Adjust)}->Measure{Expenses}"
        % (Year, account, 'Base(#root,0)', p2['Department']),
        compact=False
    )
    df_material_forecast = cube_bewg.query(
        "Year{%s}->Version{Y1}->Scenario{Forecast}->Allocation{Original}->Account{%s}->"
        "Tax{Notax;Tax}->Misc1{Nomisc1}->Misc2{Nomisc2}->Entity{%s}->Department{%s}->"
        "Material{Base(Total,0)}->Period{10;11;12}->Measure{Expenses}"
        % (str(int(Year)-1), account, 'Base(#root,0)', p2['Department']),
        compact=False
    )

    df_material = pd.concat([df_material_budget,df_material_forecast], ignore_index=True)

    if df_material.empty:
        # df_main['Budget_Explain'] = None
        return df_main

    # 重命名
    df_material = df_material.rename(columns={
        'Year': 'Year_Code',
        'Period': 'Period_Code',
        'Entity': 'Project_code',
        'Account': 'Account_code',
        "Tax": "Tax_code",
        'data': 'figure'
    })

    df_material = df_material[['Year_Code', 'Period_Code', 'Project_code', 'Account_code', 'Tax_code','Scenario','Department','Material','figure']].copy()


    df_material = merge_dimension_names(df_material)

    df_main = pd.concat([df_main,df_material])

    return df_main

def fun_budget_data(cube_bewg, p2):

    # 获取系统变量 预算编制年
    variable = Variable(element_name='Variable', path='/03_Variable/')
    # 推送变量年的
    Year = variable.get('BudYear')
    # Year = '2026'


    Version = p2['Version']

    # 1. 获取映射表
    df_budget_mapping = fun_query_mysql('', 'Budget_mapping_ws', '/05_Datatable/05_10_Budget')
    df_budget_mapping = df_budget_mapping[['Account_cd', 'Material', 'Measure', 'Account_mapping']].drop_duplicates()

    Account = ";".join(df_budget_mapping["Account_cd"].astype(str).tolist())
    # print(result)

    # 2.查询 Cube 数据 （预算数+预测数）
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

    # 4. 应用科目映射（数值部分）
    df = apply_account_mapping(df, df_budget_mapping,measure='Measure')

    # 5. 处理分摊逻辑
    df_project = df[~df['Project_code'].str.startswith('XN')].copy()
    df_portion = get_portion_scope()
    df = pd.merge(df, df_portion, how='inner')
    df.loc[df['portion'].notnull(), 'figure'] = df['figure'] * df['portion']
    df = df.drop(columns=['account_type', 'portion','Project_code','expectedName'], errors='ignore')
    df = df.rename(columns={"electric_charge": "Project_code"})

    df = pd.concat([df, df_project], ignore_index=True)

    # 6. 关联中文名称
    df = merge_dimension_names(df)

    # 7. 汇总（只汇总一次）
    group_cols = ['Year_Code', 'Period_Code', 'Project_code', 'Account_code',
                  'Tax_code', 'Department', 'Scenario', 'Attribute','Material',
                  'Project_name', 'Account_name']

    # df = df[group_cols + ['figure']]

    df = group_and_sum(df, group_cols, value_col='figure')

    # 8. 原材料相关+电度电量+电度电量吨水电耗
    # material_account = ['YW0301','YW0304','YW0316','YW0312','YW0309','YW0215','YW0401']
    # df = material_with_mapping(df, cube_bewg, Year, material_account, df_budget_mapping, p2)

    # 9. 合并编制说明（带映射）
    df = merge_explain_with_mapping(df, cube_bewg, Year, Account, df_budget_mapping, p2)


    df['Source'] = 'YWYS'
    df['UpdateTime'] = datetime.datetime.now()

    return df

def get_portion_scope():

    year = Variable('Variable').get_value('BudYear')
    # 预算数据映射关系
    dt = DataTableMySQL("works_project_apportion")
    where = "Year = '%s' and Version = 'Y1'" % year
    df_apportion_mapping = dt.select(where=where)
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



def df_push(df,p1):
    # from deepfos.options import OPTION
    # p1['app'] = 'eemapg007'
    # p1['space'] = 'eemapg'
    # OPTION.api.header = p1
    # table = ck('bewg_budget_data')
    # table.delete({'Source':'YWYS'})
    # # tb = DataTableMySQL('bewg_budget_data')
    # table.insert_df(df)


    from deepfos.options import OPTION
    p1['app'] = 'eemapg007'
    p1['space'] = 'eemapg'
    OPTION.api.header = p1
    table = ck('bewg_budget_data')
    table.delete({'Source':'YWYS'})
    # tb = DataTableMySQL('bewg_budget_data')
    table.insert_df(df,chunksize=50000)





def main(p1, p2):
    p2 = {"Version": "Y1", "Entity": "Base(#root,0)", "Department": "Base(#root,0)"}
    try:
        cube_bewg = FinancialCube('WS_cube')
        # print(df_check)
        budget_df = fun_budget_data(cube_bewg, p2)
        df_push(budget_df,p1)
    except Exception as e:
        traceback.print_exc()

# debug
if __name__ == '__main__':
    main(para1, para2)

