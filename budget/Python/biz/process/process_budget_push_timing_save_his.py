# -*- coding: utf-8 -*-
'''
@file    : process_budget_push_timing_save_his.py
@Time    :
@Author  : XMX
@Software: PyCharm
@Desc    : 北控水务 预算数推送接口 定时推送全量最新版到预算数据中间表 Y1 每次全量覆盖 存储历史数据 新增、变化数据插入
'''
try:
    from _debug import para1, para2
    # print(para1)
except ImportError:
    para1 = para2 = {}

import traceback
import pandas as pd
from deepfos.element.datatable import DataTableClickHouse as ck
from deepfos.db.mysql import MySQLClient


# from _debug import p1, p2


def save_his(table):
    client = MySQLClient()
    where = "Version_Info = 'Y1'"
    df_insert = table.select_raw(where=where)
    df_insert = pd.DataFrame.from_dict(df_insert)
    df_insert = df_insert.drop(columns={"createtime", "createdate"})

    # 为数据核对使用

    # 这里不清表了
    # client.exec_sqls("delete from ${bewg_budget_data} where Version_Info = 'Y1'")

    updatecol = list(set(df_insert.columns) - {"Project_code", "Account_code","Year_Code","Period_Code","Tax_code","Version_Info"})

    client.insert_df(dataframe=df_insert, updatecol=updatecol,element_name='bewg_budget_data')

    sql = "select * from ${bewg_budget_data_his} t " \
          "where not exists " \
          "(select 1 from ${bewg_budget_data_his} " \
          "where Project_code = t.Project_code and Account_code = t.Account_code and Year_Code = t.Year_Code " \
          "and Period_Code = t.Period_Code and Tax_code = t.Tax_code and Version_Info = t.Version_Info " \
          "and Data_push_Time > t.Data_push_Time)"
    df_his = client.query_dfs(sql)

    # 对比
    df_check = pd.concat([df_insert, df_his, df_his]
                         ).drop_duplicates(subset=['Project_code', 'Account_code', 'Year_Code', 'Period_Code',
                                                   'Tax_code', 'Version_Info', 'figure', 'Attribute',
                                                   'Process_Approval_Status'],
                                           keep=False).reset_index(drop=True)
    if not df_check.empty:
        df_check['UpdateTime'] = pd.to_datetime(df_check['UpdateTime'])
        df_check['Data_push_Time'] = pd.to_datetime(df_check['Data_push_Time'])
        client.insert_df(dataframe=df_check, element_name='bewg_budget_data_his')
        print("历史数据已存储:", list(set(df_check['Project_code'].to_list())))
    else:
        print("无数据推送无数据更新")


def main(p1, p2):
    if "folderId" in p2:
        del p2['folderId']
    if "elementName" in p2:
        del p2['elementName']
    try:
        # 初始化
        table = ck('bewg_budget_data')
        save_his(table)
    except Exception as e:
        traceback.print_exc()


# debug
if __name__ == '__main__':
    # p1 = {}
    main(para1, para2)


