# -*- coding: utf-8 -*-
'''
@file    : update_basic_info.py
@Time    :
@Author  : XMX
@Software: PyCharmrenew_entity_scjbxxtb
@Desc    : "更新项目基本信息（项目管理特征，边界性质）；
# 项目基本信息维护
'''

import traceback
import pandas as pd
from deepfos.element.dimension import Dimension, DimMember
from deepfos.element.variable import Variable
from deepfos.element.datatable import DataTableMySQL
from deepfos.db.mysql import MySQLClient

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)

def renew(p1, p2):
    # 变量年
    # year = Variable('Variable').get('BudYear')
    year = p2['Year']

    # 维度 实例化
    dim = Dimension("Entity", path="/2_Dimension")

    # 查询数据中间表
    basic_table = DataTableMySQL('Project_Basic_Information')
    cols = ['project_cd','pro_characteristics','nature','project_corp_cd']
    where = (basic_table.table.year == year) & (basic_table.table.pro_characteristics.isnotnull() | basic_table.table.nature.isnotnull())
    basic_df = basic_table.select(columns = cols, where = where)

    basic_df = basic_df.rename(columns={
        "project_cd": "name",
        # "project_name": "language_zh-cn",
        "project_corp_cd": "parent_name",
        "nature": "ud3",
        "pro_characteristics" : "ud6"
    })
    print(basic_df)
    dim.load_dataframe(basic_df,"incr_replace")


# 更新p2参数的键
def rename_wb1_keys(params):
    # Create a new dictionary to avoid modifying the original
    new_params = {}
    for key, value in params.items():
        # If key ends with '_wb1', remove the suffix; otherwise, keep the key as is
        new_key = key[:-4] if key.endswith('_wb1') else key
        new_params[new_key] = value
    return new_params


def main(p1, p2):
    p2 = rename_wb1_keys(p2)
    try:
        print(p1, p2)
        renew(p1, p2)
    except Exception as e:
        traceback.print_exc()


# debug
if __name__ == '__main__':
    from BIZ._debug import para1, para2
    p2 = {'elementName': 'jichu',
          'folderId': 'DIRf721f29b7612',
          'sheetName': '项目基础信息',
          'sheetId': 'SHT288a9d1b4f9d4fb482daeecf0b838e45',
          'Year_wb1': '2026',
          'Entity_wb1': '1'}

    main(para1, p2)

