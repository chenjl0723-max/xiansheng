# -*- coding: utf-8 -*-
'''
@file    : act_access.py
@Time    :
@Author  : CHENJL
@Software: PyCharm
@Desc    : cube数据迁移
'''

try:
    from common.__debug import para1, para2
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
from deepfos.options import OPTION
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)

def query_dim():
    print(1)

def query_sql():
    dt = DataTableMySQL('account_mapping')
    df = dt.select()
    return df
# 抽取cube数据
def extract_cube(account_map):
    cube = FinancialCube('BEWG')
    result_dfs = []  # 存储所有月份的结果

    # 循环年份和月份
    for year in range(2024, 2026):  # 2020 到 2026
        for month in [1,2,3,4,5,6,7,8,9,10,11,12,'Noperiod']:  # 1 到 12 月

            p1 = {'app': 'eemapg001', 'space': 'eemapg', 'user': '1ef2c32f-4a07-4f19-bff0-bf3bd2e662df', 'language': 'zh-cn',
             'token': '675DAA54DABB51FEAA4CFCFABEA13EFAFBD06DCD88D5E2687C879ED43F60D4A1',
             'cookie': 'deepfos_users=%7B%22invitationActivation%22%3Atrue%2C%22nickName%22%3A%22chenjinglei%22%2C%22nickname%22%3A%22chenjinglei%22%2C%22token%22%3A%22675DAA54DABB51FEAA4CFCFABEA13EFAFBD06DCD88D5E2687C879ED43F60D4A1%22%2C%22tokenKey%22%3A%22deepfos_token%22%2C%22type%22%3A1%2C%22userId%22%3A%221ef2c32f-4a07-4f19-bff0-bf3bd2e662df%22%2C%22username%22%3A%22chenjinglei%22%7D; deepfos_token=675DAA54DABB51FEAA4CFCFABEA13EFAFBD06DCD88D5E2687C879ED43F60D4A1',
             'envUrl': 'http://web-gateway'}
            OPTION.api.header = p1

            # 构造维度表达式，月份格式化为两位数
            period = f"{month}"  # 01, 02, ..., 12
            year = f"{year}"  # 01, 02, ..., 12
            cube_pov = f"Entity{{Base(#root,0)}}->Department{{Base(#root,0)}}->Year{{{year}}}->Period{{{period}}}->Account{{Base(A894,0);A300101;A300201}}->Tax{{NoTax}}->Version{{Y2;Y3;Y4;Y5;Y6;Y7}}"

            # 查询 Cube 数据
            try:
                df = cube.query(cube_pov, compact=False)
                print(f"查询 Year={year}, Period={period}, 原始数据行数: {len(df)}")

                # 过滤 data == 0 的行
                # filtered_df = df.loc[df['data'] == 0]
                df = df.loc[df['data'] != 0]

                # 与 account_map 合并
                df_new = pd.merge(df, account_map, how='left', on=['Account'])
                df_new = df_new.drop(columns=['Account', '_id'])
                df_new = df_new.rename(columns={'Account_new': 'Account'})
                df_new.loc[df_new['Department'] == 'HR', 'Department'] = 'Technical'
                df_new = df_new.rename(columns={'misc1': 'Misc1','misc2':'Misc2'})
                print(f"Year={year}, Period={period}, 去0后剩余：: {len(df_new)}")

                df_new = df_new.groupby(
                    ['Year', 'Scenario', 'Version', 'Entity', 'Period', 'Material', 'Tax', 'Allocation', 'Account',
                     'Department', 'Measure', 'Misc1', 'Misc2'], as_index=False)['data'].sum()


                print(f"Year={year}, Period={period}, 科目汇总后: {len(df_new)}")
                data_to_cube(df_new)

                # 将结果添加到列表
                # result_dfs.append(df_new)
            except Exception as e:
                print(f"查询 Year={year}, Period={period} 失败: {str(e)}")
                continue


def data_to_cube(df):
    p1 = {'app': 'eemapg011', 'space': 'eemapg', 'user': '1ef2c32f-4a07-4f19-bff0-bf3bd2e662df', 'language': 'zh-cn',
          'token': '675DAA54DABB51FEAA4CFCFABEA13EFAFBD06DCD88D5E2687C879ED43F60D4A1',
          'cookie': 'deepfos_users=%7B%22invitationActivation%22%3Atrue%2C%22nickName%22%3A%22chenjinglei%22%2C%22nickname%22%3A%22chenjinglei%22%2C%22token%22%3A%22675DAA54DABB51FEAA4CFCFABEA13EFAFBD06DCD88D5E2687C879ED43F60D4A1%22%2C%22tokenKey%22%3A%22deepfos_token%22%2C%22type%22%3A1%2C%22userId%22%3A%221ef2c32f-4a07-4f19-bff0-bf3bd2e662df%22%2C%22username%22%3A%22chenjinglei%22%7D; deepfos_token=675DAA54DABB51FEAA4CFCFABEA13EFAFBD06DCD88D5E2687C879ED43F60D4A1',
          'envUrl': 'http://web-gateway'}
    OPTION.api.header = p1

    cube = FinancialCube("WS_cube")
    cube.save(df,chunksize=10000)





def main(p1, p2):
    account_map = query_sql()
    extract_cube(account_map)

# debug
if __name__ == '__main__':
    # p1 = {}
    # p2 = {'func': "实际数", 'year': "空", 'month_begin': "1", 'month_end': "12", 'entity': "空"}
    main(para1, para2)
