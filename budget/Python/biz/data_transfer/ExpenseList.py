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
    dt = DataTableMySQL('ExpenseList')
    df = dt.select()
    df_new = pd.merge(df, account_map, how='left', on=['Account'])
    df_new = df_new.drop(columns=['Account', '_id'])
    df_new = df_new.rename(columns={'Account_new': 'Account'})

    data_to_cube(df_new)
    print(df_new)



def data_to_cube(df):
    p1 = {'app': 'eemapg011', 'space': 'eemapg', 'user': '1ef2c32f-4a07-4f19-bff0-bf3bd2e662df', 'language': 'zh-cn',
          'token': '675DAA54DABB51FEAA4CFCFABEA13EFAFBD06DCD88D5E2687C879ED43F60D4A1',
          'cookie': 'deepfos_users=%7B%22invitationActivation%22%3Atrue%2C%22nickName%22%3A%22chenjinglei%22%2C%22nickname%22%3A%22chenjinglei%22%2C%22token%22%3A%22675DAA54DABB51FEAA4CFCFABEA13EFAFBD06DCD88D5E2687C879ED43F60D4A1%22%2C%22tokenKey%22%3A%22deepfos_token%22%2C%22type%22%3A1%2C%22userId%22%3A%221ef2c32f-4a07-4f19-bff0-bf3bd2e662df%22%2C%22username%22%3A%22chenjinglei%22%7D; deepfos_token=675DAA54DABB51FEAA4CFCFABEA13EFAFBD06DCD88D5E2687C879ED43F60D4A1',
          'envUrl': 'http://web-gateway'}
    OPTION.api.header = p1

    dt = DataTableMySQL('ExpenseList')
    dt.insert_df(df)





def main(p1, p2):
    account_map = query_sql()
    extract_cube(account_map)

# debug
if __name__ == '__main__':
    # p1 = {}
    # p2 = {'func': "实际数", 'year': "空", 'month_begin': "1", 'month_end': "12", 'entity': "空"}
    main(para1, para2)
