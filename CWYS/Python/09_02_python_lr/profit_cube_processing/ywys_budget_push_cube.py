# -*- coding: utf-8 -*-
'''
@file    : budget_push_cube.py
@Time    :
@Author  : CHEN
@Software: PyCharm
@Desc    : 预算数进利润预算模型
'''


try:
    from CWYS.__debug import para1, para2
    # print(para1)
except ImportError:
    para1 = para2 = {}
from deepfos.options import OPTION
import pandas as pd
from datetime import datetime
import traceback
import time
import os
from deepfos.db.mysql import MySQLClient
from deepfos.element.datatable import DataTableClickHouse
from deepfos.element.finmodel import FinancialCube
from deepfos.element.datatable import DataTableClickHouse as ck
from deepfos.element.datatable import DataTableMySQL
from deepfos.element.variable import Variable
from deepfos.element.dimension import Dimension, DimMember
from deepfos.element.pyscript import PythonScript
import numpy as np


# from _debug import p1, p2


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


def public_processing(p1, p2):
    # 公共层应用
    p1['app'] = 'eemapg007'
    OPTION.api.header = p1


    # 获取业务预算预算数据
    YS_dt = DataTableClickHouse('bewg_budget_data')
    cols = ['Project_code', 'Account_code', 'Year_Code', 'Period_Code', 'Tax_code', 'Scenario',
            'Explain', 'figure', 'Source']
    where = "Project_code not like 'XN%'"
    YS_df = YS_dt.select(columns=cols, where=where)
    YS_df = YS_df.rename(columns={
        "Period_Code": "Period",
        "Project_code": "Entity_GL",
        "Year_Code": "Year",
        "Tax_code": "Comprehensive",
    })

    # 添加度量已经合并Explain和figure
    YS_df['Measure'] = np.where(
        YS_df['Explain'].notna() &
        (YS_df['Explain'].astype(str).str.strip() != '') &
        (YS_df['Explain'].astype(str).str.strip().str.lower() != 'nan'),
        'Explain',
        'Expenses'
    )

    YS_df['data'] = np.where(
        YS_df['Measure'] == 'Explain',
        YS_df['Explain'],
        YS_df['figure'].fillna(0)
    )

    # 拆分XYT和YWYS数据
    XYT_df = YS_df[YS_df['Source'] == 'XYT']

    YWYS_df = YS_df[YS_df['Source'] == 'YWYS']

    # 预算科目映射表
    account_map_dt = DataTableMySQL('budget_account_mapping')
    cols = ['Account_cd_lanke', 'Account_cd_wushui', 'Account_cd_xiaoyetai']

    account_map_df = account_map_dt.select(columns=cols).rename(columns={
        "Account_cd_lanke": "Account_lirun",
        "Account_cd_wushui": "Account",
        "Account_cd_xiaoyetai": "Account_XYT"})

    # 小业态科目映射为管报科目
    XYT_df = XYT_df.merge(account_map_df[['Account_lirun', 'Account_XYT']], how='left', left_on='Account_code',
                          right_on='Account_XYT').drop(columns=['Account_code'])
    # 业务预算科目映射为管报科目
    YWYS_df = YWYS_df.merge(account_map_df[['Account', 'Account_lirun']], how='left', left_on='Account_code',
                            right_on='Account').drop(columns=['Account_code'])

    df = pd.concat([XYT_df, YWYS_df])
    df.drop(['Source', 'figure', 'Explain', 'Account_XYT', 'Account'], axis=1, inplace=True)

    df['Misc1'] = 'nomisc1'
    df['Misc2'] = 'nomisc2'
    # df['Commercial'] = 'Nomisc3'
    df['Comprehensive'] = df['Comprehensive'].replace('Notax', 'NoTax')

    group_cols = ['Year', 'Period', 'Entity_GL', 'Account_lirun',
                   'Scenario', 'Misc1','Misc2','Measure', 'Comprehensive']
    df = group_and_sum(df, group_cols, value_col='data')
    return df,account_map_df['Account_lirun']


def CWYS_processing(p1, p2, df,account_scope):


    # # 写入财务预算分析模型
    p1['app'] = 'eemapg016'
    OPTION.api.header = p1


    # 获取变量年
    Year = Variable('Variable').get('BudYear')
    Year = '2027'
    Last_year =str(int(Year)-1)
    Last_year = '2026'

    Version = Variable('Variable').get('Edit_Ver')
    # df['Version'] = 'V4'

    # 排除特定科目编码
    exclude_accounts = {'SYW02020302', 'SYW02020301', 'SYW010105', 'SYW010103', 'SYW010104'}
    account_scope = [acct for acct in account_scope if acct not in exclude_accounts]

    # 过滤不需要的科目
    account_dim = Dimension('Account_lirun')
    account_list = pd.DataFrame(account_dim.query(expression="Base(#root,0)", fields=['name'], as_model=False))
    df = df[df['Account_lirun'].isin(account_list['name'])]

    missing_entities = df[~df['Account_lirun'].isin(account_list['name'])]['Account_lirun'].unique()
    if len(missing_entities) > 0:
        print(f"以下项目在业态维度中不存在，将被过滤掉: {list(missing_entities)}")


    # 关联业态
    entity_dim =  Dimension('Entity_GL')
    entity_df = pd.DataFrame(entity_dim.query(expression="Base(#root,0)", fields=['name','ud7'], as_model=False)).rename(columns={
        'name':'Entity_GL',
        'ud7':'Commercial',}).drop_duplicates(subset='Entity_GL')
    # 输出不存在于业态维度中的项目
    missing_entities = df[~df['Entity_GL'].isin(entity_df['Entity_GL'])]['Entity_GL'].unique()
    if len(missing_entities) > 0:
        print(f"以下项目在业态维度中不存在，将被过滤掉: {list(missing_entities)}")

    df = df[df['Entity_GL'].isin(entity_df['Entity_GL'])]
    df = df.merge(entity_df, how='left', on='Entity_GL')

    del df['id']
    del df['expectedName']

    # 单位换算：仅PL开头的科目*10000
    df['data'] = np.where(df['Account_lirun'].astype(str).str.startswith('PL'), df['data'] * 10000, df['data'])
    df['Year'] = df['Year'].apply(lambda x: str(int(x) + 1))

    # YW/SYW 开头科目：删除不含税数据，将含税数据复制一份到不含税
    yw_syw_mask = df['Account_lirun'].astype(str).str.startswith(('YW', 'SYW'))
    yw_syw_df = df[yw_syw_mask]
    # 删除 YW/SYW 科目的 NoTax 数据
    df = df[~(yw_syw_mask & (df['Comprehensive'] == 'NoTax'))]
    # 取 YW/SYW 科目的 Tax 数据复制一份，Comprehensive 改为 NoTax
    tax_df = yw_syw_df[yw_syw_df['Comprehensive'] == 'Tax'].copy()
    tax_df['Comprehensive'] = 'NoTax'
    df = pd.concat([df, tax_df], ignore_index=True)

    # df = df[df['Commercial'].notna()]

    # df['Commercial'] = df['ud7'].fillna('NoCommercial')
    # df.drop(['name', 'ud7'], axis=1, inplace=True)



    cube = FinancialCube('sub_profit_cube')
    expr_dict_budget = {
        "Year": Year,
        "Scenario":'Budget',
        "Entity_GL": "IDescendant(#root,0)",
        "Account_lirun": list(account_scope),
        "Comprehensive":['Tax', 'NoTax'],
        "Version": Version,
    }
    expr_dict_forecast = {
        "Year": Last_year,
        "Scenario":'Forecast',
        "Entity_GL": "IDescendant(#root,0)",
        "Account_lirun": list(account_scope),
        "Comprehensive": ['Tax', 'NoTax'],
        "Version": Version,
    }
    cube.delete(expr_dict_budget)
    cube.delete(expr_dict_forecast)
    print('删除完成')


    cube.save(df,chunksize=200000)

def main(p1, p2):
    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    countAll = 0
    countSuccess = 0
    countError = 0
    countMsg = f"{start_time} 开始执行业务预算+小业态预算数接入任务\n"

    try:
        # 公共层应用
        public_data,account_scope = public_processing(p1, p2)

        # 写入财务预算分析模型
        CWYS_processing(p1, p2, public_data,account_scope)
        countSuccess = 1
        countAll = 1
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 业务预算+小业态预算数接入处理完成\n"

    except Exception as e:
        countError = 1
        countAll = 1
        error_detail = traceback.format_exc()
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 业务预算+小业态预算数接入失败: {str(e)}\n"
        countMsg += f"详细错误信息:\n{error_detail}\n"
        print(f"业务预算+小业态预算数推送执行出错: {e}")
        traceback.print_exc()

    # ====================== 写入日志 ======================
    ele_name = os.path.basename(__file__)
    ele_path = os.path.dirname(os.path.abspath(__file__))

    try:
        sync_log = PythonScript(element_name='pyLog', path='/09_Python/common', should_log=True)
        sync_result = sync_log.run(
            parameter={
                'ele_name': ele_name,
                'ele_path': ele_path,
                'data_count': countAll,
                'error_count': countError,
                'logs': countMsg,
                'dt': datetime.now().strftime('%Y%m%d'),
                'start_time': start_time,
                'exe_parameter': str(p2)
            }
        )
        if sync_result:
            print("日志记录成功！")
        else:
            print("日志记录失败！")
    except Exception as log_e:
        print(f"日志记录异常: {log_e}")

    # 返回执行结果（与维度脚本保持一致）
    return False if countError > 0 else True


# debug
if __name__ == '__main__':
    main(para1, para2)

