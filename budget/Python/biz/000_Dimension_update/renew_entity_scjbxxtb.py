# -*- coding: utf-8 -*-
'''
@file    : renew_entity_scjbxxtb.py
@Time    :
@Author  : XMX
@Software: PyCharmrenew_entity_scjbxxtb
@Desc    : "更新子水厂的基本信息（投资模式，边界性质，特殊项目类型，边界变化类型，边界变化时间，新增项目时间，是否超保底运行）；
            更新子水厂的子集（边界性质）"
# 水厂基本信息维护
'''

import traceback
import pandas as pd
from deepfos.element.dimension import Dimension, DimMember
from deepfos.element.variable import Variable
from deepfos.db.mysql import MySQLClient
# import datetime
# from deepfos.options import OPTION


# from _debug import p1, p2

def renew(p1, p2):
    # 变量年
    year = Variable('Variable').get('BudYear')

    # 维度 实例化
    dim = Dimension("Entity", path="/02_Dimension")
    df_parent_name = pd.DataFrame(
        dim.query(
            expression="IBase(%s,0)" % p2["Entity"],
            fields=["name", "parent_name"],
            as_model=False,
        )
    )[["name", "parent_name"]]
    # 查询数据中间表
    table = "basic_info"
    client = MySQLClient()
    sql = (
            "select entity name,inv_pattern ud5,nature ud6,chg_type ud7,chg_date ud8,new_date ud9,"
            "special_type ud12 ,Exceed_operation ud13 from ${%s} where entity='%s' and Year ='%s'" % (table, p2["Entity"],year)
    )
    df_ods = client.query_dfs(sql)
    # 处理水厂层级组织 更新ud5~ud12
    df_ps = df_ods.copy()
    df_ps["parent_name"] = df_parent_name[df_parent_name["name"] == p2["Entity"]][
        "parent_name"
    ].reset_index(drop=True)[0]
    df_ps = df_ps.where(df_ps.notnull(), "")

    # 处理项目、虚拟子水厂层级组织 只更新 ud6
    df = pd.merge(
        df_ods.rename(columns={"name": "parent_name"})[["parent_name", "ud6"]],
        df_parent_name,
        how="left",
    )
    df = pd.concat([df_ps, df])
    df = df.where(df.notnull(), "")
    print('更新的维度数据：', df)
    # 更新维度
    dim.load_dataframe(dataframe=df, strategy="incr_replace")


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
    from common._debug import para1, para2
    p2 = {'elementName': 'hynbase_info_write_r_copy', 'folderId': 'DIRd8a9a9e06226', 'sheetName': '水厂基本信息表', 'sheetId': 'SHT716efc09faca4fe39bc7b76b29b25720', 'Year': '2025', 'Entity': 'PS61001_01', 'Department': 'Operation', 'Version': 'Y1'}
    main(para1, p2)

