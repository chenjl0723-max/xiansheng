#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    描述：检验化验费、其他成本、费用清单，浮动行表数据进cube

    开发： 杨培泽

    日期： 2025/4/17 17:54

"""
import pandas as pd
import numpy as np
import warnings
import os
import sys

top_path = os.path.abspath(os.path.join(__file__, "../../.."))
sys.path.append(top_path)
# 获取当前脚本文件的绝对路径 current_file = os.path.abspath(__file__)
# 获取当前脚本文件所在的目录 current_dir = os.path.dirname(current_file)
# 向上回溯两层目录，得到 common 目录所在的父目录 parent_dir = os.path.dirname(current_dir)
# 将父目录添加到 sys.path 中 sys.path.append(parent_dir)
from common.commons import *

def query_sql(p2):
    expenselist_df = rdb_.select(
        columns=[
            "Account",
            "Entity",
            "Year",
            "Scenario",
            "Version",
            "Department",
            "Jan",
            "Feb",
            "Mar",
            "Apr",
            "May",
            "Jun",
            "Jul",
            "Aug",
            "Sep",
            "Oct",
            "Nov",
            "Dec",
        ],
        tbl="ExpenseList",
        where=f"""(t.Entity == '{p2['Entity_wb1']}') & (t.Department == '{p2['Department_wb1']}') & (t.Year == '{p2['Year_wb1']}') & (t.Version == '{p2['Version_wb1']}') & (t.Account == '{p2['Account_wb1']}') & (t.Scenario == 'Budget')"""
    )
    # where=f"""(t.Price.isnull()) & (t.Quantity.isnull()) & (t.Entity == '{p2['Entity_wb1']}') & (t.Department == '{p2['Department_wb1']}') & (t.Year == '{p2['Year_wb1']}') & (t.Version == '{p2['Version_wb1']}') & (t.Account == '{p2['Account_wb1']}') & (t.Scenario == 'Budget')"""
    # print(where)
    print(expenselist_df)

    # 这段代码主要完成了两个数据处理操作：处理缺失值和分组求和
    expenselist_df = expenselist_df.fillna(0)

    expenselist_df = expenselist_df.groupby(
        by=["Entity", "Department", "Year", "Scenario", "Version", "Account"],
        as_index=False,
    ).sum()
    print('方法1結束 -----------')
    return expenselist_df


def calc_sum(expenselist_df, year):
    print('方法2开始 触发求和计算 -----------')
    expenselist_df = expenselist_df.fillna(0)
    expenselist_df = expenselist_df.groupby(
        by=["Entity", "Department", "Year", "Scenario", "Version", "Account"],
        as_index=False,
    ).sum()

    expenselist_df = (
        expenselist_df.set_index(
            ["Entity", "Department", "Year", "Scenario", "Version", "Account"]
        )
            .stack()
            .reset_index(drop=False, level=-1)
            .reset_index()
            .rename(columns={0: "data"})
    )
    expenselist_df = expenselist_df.rename(columns={"level_6": "Period"})

    expenselist_for_df = expenselist_df[(expenselist_df['Year']==year) & (expenselist_df['Period'].isin(['Oct_For', 'Nov_For', 'Dec_For']))]
    expenselist_bud_df = expenselist_df[(expenselist_df['Year']==str(int(year) + 1)) & ~(expenselist_df['Period'].isin(['Oct_For', 'Nov_For', 'Dec_For']))]
    expenselist_df = pd.concat([expenselist_for_df, expenselist_bud_df])
    scenario_mapping = {
        "Oct_For": "Forecast",
        "Nov_For": "Forecast",
        "Dec_For": "Forecast",
        "Jan": "Budget",
        "Feb": "Budget",
        "Mar": "Budget",
        "Apr": "Budget",
        "May": "Budget",
        "Jun": "Budget",
        "Jul": "Budget",
        "Aug": "Budget",
        "Sep": "Budget",
        "Oct": "Budget",
        "Nov": "Budget",
        "Dec": "Budget",
    }

    expenselist_df["Scenario"] = expenselist_df["Period"].apply(
        lambda x: scenario_mapping[x]
    )
    period_mapping = {
        "Oct_For": "10",
        "Nov_For": "11",
        "Dec_For": "12",
        "Jan": "1",
        "Feb": "2",
        "Mar": "3",
        "Apr": "4",
        "May": "5",
        "Jun": "6",
        "Jul": "7",
        "Aug": "8",
        "Sep": "9",
        "Oct": "10",
        "Nov": "11",
        "Dec": "12",
    }
    expenselist_df["Period"] = expenselist_df["Period"].apply(
        lambda x: period_mapping[x]
    )
    expenselist_df.loc[expenselist_df['Scenario']=='Forecast', "Year"] = year
    expenselist_df["Tax"] = "Tax"
    expenselist_df["Allocation"] = "Original"
    expenselist_df["Measure"] = "Expenses"
    expenselist_df["Misc1"] = "Nomisc1"
    expenselist_df["Misc2"] = "Nomisc2"
    expenselist_df["Material"] = "Nomaterial"

    print('方法2结束 -----------')
    return expenselist_df


def expenselist_to_cube(expenselist_df, pov, year):
    print('方法3开始 -----------')
    del_fix = (
                  "Account{%s}->Year{%s}->Scenario{%s}->"
                  "Measure{%s}->Period{%s}->Entity{%s}->"
                  "Version{%s}->Material{%s}->Department{%s}->"
                  "Allocation{%s}->Tax{%s}->Misc1{%s}->"
                  "Misc2{%s}"
              ) % (
                  pov['Account_wb1'],
                  pov['Year_wb1'],
                  "Budget",
                  "Expenses",
                  "1;2;3;4;5;6;7;8;9;10;11;12",
                  pov['Entity_wb1'],
                  pov['Version_wb1'],
                  "Nomaterial",
                  pov['Department_wb1'],
                  "Original",
                  "Tax",
                  "Nomisc1",
                  "Nomisc2"
              )
    print('方法3结束 -----------')
    cube_.data_to_cube(cube='WS_cube', del_fix=del_fix, data=expenselist_df)
    print('数据成功写入cube！！！！ -----------')



def main(p1, p2):
    # print(p2)

    del p2["sheetName"]
    # sheetId没有用到，不用改也没事
    del p2["sheetId"]
    # print(p2)
    # 根据p2条件 查ExpenseList表，获取总价
    expenselist_df = query_sql(p2)
    # print(expenselist_df)

    if expenselist_df.empty:
        return
    last_year = str(int(p2['Year_wb1']) - 1)
    # 汇总计算
    expenselist_df = calc_sum(expenselist_df, last_year)
    # 总价插入到 cube
    expenselist_to_cube(expenselist_df, p2, last_year)
    # ('成功触发写入数据写入cube ---------- 002 ！！！！')

if __name__ == "__main__":
    try:
        from common ._debug import para1, para2
    except:
        pass
    para2 = {
          "Account_wb1": "PL0102010402",
          "Entity_wb1": "XN61001_01",
          "Year_wb1": "2025",
          "Version_wb1": "Y1",
          "Department_wb1": "Operation",
          "Scenario_wb1": "Budget",
          "sheetName": "费用清单",
          "sheetId": "SHTac754700fcce",
    }
    main(para1, para2)
