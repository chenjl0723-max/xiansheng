#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    描述： 配置表单计算

    开发： 陈 小

    日期： 2023/9/11 10:33

"""

import os
import sys

top_path = os.path.abspath(os.path.join(__file__, "../../../.."))
sys.path.append(top_path)

import warnings

warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
from common.commons import *


class ConfigCalc:
    def __init__(
            self,
    ):
        self.tbl = "config_tbl"
        self.cube = "WS_cube"
        self.fix = (
            "Account{%s}->Year{%s}->Scenario{%s}->"
            "Measure{%s}->Period{%s}->Entity{%s}->"
            "Version{%s}->Material{%s}->Department{%s}->"
            "Allocation{%s}->Tax{%s}->Misc1{%s}->"
            "Misc2{%s}"
        )

    def get_config(self, sheet_id):
        config_df = rdb_.select(
            columns=None, tbl=self.tbl, where=f"t.sheet_id.like('%{sheet_id}%')"
        )

        config_df = config_df.rename(
            columns={
                "account": "Account",
                "year": "Year",
                "scenario": "Scenario",
                "measure": "Measure",
                "period": "Period",
                "entity": "Entity",
                "version": "Version",
                "material": "Material",
                "department": "Department",
                "allocation": "Allocation",
                "tax": "Tax",
                "Misc1": "Misc1",
                "Misc2": "Misc2",
            }
        )
        return config_df

    def mapping_year(self, config_df, year):
        mapping_dict = {
            "POV": year,
            "POV-1": str(int(year) - 1),
            "POV-2": str(int(year) - 2),
            "POV-3": str(int(year) - 3),
            "POV-4": str(int(year) - 4),
            "POV-5": str(int(year) - 5),
        }
        config_df["Year"] = config_df["Year"].apply(lambda x: mapping_dict[x])
        return config_df

    def mapping_entity(self, config_df, entity):
        if entity != "":
            config_df["Entity"] = entity
        return config_df

    def delete_data(self, config_del_df):
        for idx, del_df in config_del_df.iterrows():
            del_fix = self.fix % (
                del_df["Account"],
                del_df["Year"],
                del_df["Scenario"],
                del_df["Measure"],
                del_df["Period"],
                del_df["Entity"],
                del_df["Version"],
                del_df["Material"],
                del_df["Department"],
                del_df["Allocation"],
                del_df["Tax"],
                del_df["Misc1"],
                del_df["Misc2"],
            )
            cube_.delete(cube_name=self.cube, expression=del_fix)

    def calc_data(self, config_df):
        # 获取此次sheet需要处理的计算名称
        form_list = list(config_df["form"].value_counts().index)
        form_num_list = []
        for fl in form_list:
            form_num_list.append(int(fl[2:]))
        form_num_list.sort()
        form_list = []
        for fnl in form_num_list:
            form_list.append("计算" + str(fnl))
        # 单独计算每一个计算
        insert_res_df = pd.DataFrame()  # 所有计算结果
        for form in form_list:
            # 每个计算需要的计算数据
            calc_data_df = pd.DataFrame()
            config_form_df = config_df[config_df["form"] == form]
            config_select_df = config_form_df[config_form_df["sql"] == "select"]

            for idx, query_df in config_select_df.iterrows():
                query_fix = self.fix % (
                    query_df["Account"],
                    query_df["Year"],
                    query_df["Scenario"],
                    query_df["Measure"],
                    query_df["Period"],
                    query_df["Entity"],
                    query_df["Version"],
                    query_df["Material"],
                    query_df["Department"],
                    query_df["Allocation"],
                    query_df["Tax"],
                    query_df["Misc1"],
                    query_df["Misc2"],
                )
                calc_df = cube_.query_cube(cube_name=self.cube, fix=query_fix)
                # 计算列重命名
                calc_df = calc_df.rename(columns={"data": query_df["calc"]})
                # 保留所需字段
                calc_df = calc_df[
                    ["Entity", "Period", "%s" % query_df["calc"]]
                ]

                # 拼接列
                if not calc_data_df.empty:
                    calc_data_df = pd.merge(calc_data_df, calc_df, how="outer")
                    calc_data_df = calc_data_df.fillna(0)
                else:
                    calc_data_df = calc_df
            # 补列
            col = set(
                config_select_df["calc"].tolist()
                + [
                    "Entity",
                    "Period",
                ]
            )

            if not calc_data_df.empty:
                if list(calc_data_df["Period"].value_counts().index) == ['TotalPeriod', 'Noperiod']:
                    calc_data_df['Period'] = "TotalPeriod"
                    calc_data_df = calc_data_df.groupby(
                        by=['Entity', 'Period'], as_index=False
                    ).sum()

                diff_list = list(col.difference(set(calc_data_df.columns)))
                if diff_list:
                    calc_data_df[diff_list] = [0] * len(diff_list)

                config_insert_df = config_form_df[config_form_df["sql"] == "insert"]
                for idx, insert_df in config_insert_df.iterrows():
                    if insert_df["calc"] == "A-B":
                        calc_data_df["data"] = calc_data_df["A"] - calc_data_df["B"]
                    elif insert_df["calc"] == "(A-B)/B":
                        calc_data_df["data"] = (
                                                       calc_data_df["A"] - calc_data_df["B"]
                                               ) / calc_data_df["B"]
                    elif insert_df['calc'] == 'A/B':
                        calc_data_df["data"] = calc_data_df["A"] / calc_data_df["B"]
                    elif insert_df['calc'] == 'B/C':
                        calc_data_df["data"] = calc_data_df["B"] / calc_data_df["C"]
                    calc_data_df['Account'] = insert_df['Account']
                    # 构建需要插入的数据
                    df_insert = calc_data_df[["Entity", "Period", "Account", "data"]]
                    df_index = insert_df[
                        [
                            "Scenario",
                            "Measure",
                            "Tax",
                            "Version",
                            "Year",
                            "Department",
                            "Material",
                            "Allocation",
                            "Misc1",
                            "Misc2",
                        ]
                    ]
                    for columnName, columnData in df_index.iteritems():
                        df_insert[columnName] = df_index[columnName]
                    insert_res_df = pd.concat([insert_res_df, df_insert])
        # 数据存储
        insert_res_df = insert_res_df.replace([np.inf, -np.inf], 0)
        insert_res_df = insert_res_df.fillna(0)
        if not insert_res_df.empty:
            print(insert_res_df)
            cube_.save_cube(df=insert_res_df, cube_name=self.cube)


def main(p1, p2):
    # p2 = {'Year': '2024', 'Entity': 'XN34001_01', 'Version': 'Y1', 'Allocation': 'Original', 'Tax': 'Tax', 'misc2': 'Nomisc2', 'Department': 'Operation', 'Measure': 'Expenses', 'sheetName': '原材料单耗填报（集采药剂）', 'sheetId': 'SHT1ff5da80ca67', 'elementName': 'Material', 'folderId': 'DIRe437ed8262b4'}
    year = p2["Year_wb1"]
    entity = ""
    sheet_id = p2['sheetId']

    cc = ConfigCalc()

    # 根据p2['sheet_id']查询config_tbl获取需要计算的配置。
    config_df = cc.get_config(sheet_id)
    # config_df = config_df[config_df['form'].isin(['计算1'])]
    del config_df['_id']
    if not config_df.empty:
        # sheet_id 根据分号分割，拆分计算数据。
        config_df = config_df.assign(sheet_id=config_df['sheet_id'].str.split(";"))
        split_data = config_df['sheet_id'].apply(pd.Series).rename(columns=lambda x: "sheet_id" + str(x + 1))
        config_col = list(config_df.drop("sheet_id", axis=1).columns)
        config_df = pd.concat([config_df.drop("sheet_id", axis=1), split_data], axis=1)
        con_df = pd.DataFrame()
        split_col = split_data.columns
        for sc in split_col:
            cd = config_df[config_col + [sc]]
            cd = cd.rename(columns={
                sc: 'sheet_id'
            })
            con_df = con_df.append(cd)
        con_df = con_df[con_df['sheet_id'] == sheet_id]
        # 映射年份，pov=p2['year']
        con_df = cc.mapping_year(con_df, year)
        # 映射entity，如果传入则取传入，未传入则取配置表。
        con_df = cc.mapping_entity(con_df, entity)
        print(con_df)
        # 删除数据
        config_del_df = con_df[con_df["sql"] == "insert"]
        cc.delete_data(config_del_df)
        # 计算存数
        cc.calc_data(con_df)


if __name__ == "__main__":
    try:
        from common._debug import para1
    except:
        pass
    para2 = {'Year': '2025', 'Entity': 'XN61001_01', 'Version': 'Y1', 'Allocation': 'Original', 'Tax': 'Tax',
             'misc2': 'Nomisc2', 'Department': 'Operation', 'Measure': 'Expenses',
             'sheetName': '原材料费用', 'sheetId': 'SHT89dfe31d3a5f4c74af6a3cb2500dd51f', 'elementName': 'Material',
             'folderId': 'DIRe437ed8262b4'}

    main(para1, para2)
