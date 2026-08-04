#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    描述： 配置表单计算

    开发： 陈 小

    日期： 2023/9/11 10:33

"""

import os
import sys

# top_path = os.path.abspath(os.path.join(__file__, "../../../.."))
# sys.path.append(top_path)

import warnings

warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
from common.commons import *
from deepfos.element.variable import Variable

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)
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
                "misc1": "Misc1",
                "misc2": "Misc2",
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
        # 获取此次 sheet 需要处理的计算名称
        form_list = list(config_df["form"].value_counts().index)
        form_num_list = [int(fl[2:]) for fl in form_list]
        form_num_list.sort()
        form_list = ["计算" + str(fnl) for fnl in form_num_list]

        insert_res_df = pd.DataFrame()  # 所有计算结果
        for form in form_list:
            calc_data_df = pd.DataFrame()
            config_form_df = config_df[config_df["form"] == form]
            config_select_df = config_form_df[config_form_df["sql"] == "select"]

            # 需要的计算列
            required_cols = set(config_select_df["calc"].tolist())
            # 初始化 calc_data_df，确保包含 Entity 和 Period
            calc_data_df = pd.DataFrame(columns=["Entity", "Period"] + list(required_cols))

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
                if not calc_df.empty:
                    calc_df = calc_df.rename(columns={"data": query_df["calc"]})
                    calc_df = calc_df[["Entity", "Period", "%s" % query_df["calc"]]]
                    if not calc_data_df.empty:
                        calc_data_df = pd.merge(calc_data_df, calc_df, how="outer", on=["Entity", "Period"])
                        calc_data_df = calc_data_df.fillna(0)
                    else:
                        calc_data_df = calc_df
                else:
                    print(f"Warning: No data retrieved for query {query_fix}. Setting {query_df['calc']} to 0.")
                    calc_data_df[query_df["calc"]] = 0  # 为缺失的列补 0

            if calc_data_df.empty or calc_data_df.shape[0] == 0:
                print(f"Warning: No data retrieved for form {form}. Skipping calculation.")
                continue

            # 补齐缺失的列
            col = set(required_cols) | {"Entity", "Period"}
            diff_list = list(col.difference(set(calc_data_df.columns)))
            if diff_list:
                print(f"Warning: Missing columns {diff_list}. Setting to 0.")
                calc_data_df[diff_list] = 0  # 直接赋值为 0

            # 统一 Period 为 Noperiod
            calc_data_df["Period"] = "Noperiod"
            calc_data_df = calc_data_df.groupby(["Entity", "Period"], as_index=False).sum()

            config_insert_df = config_form_df[config_form_df["sql"] == "insert"]
            for idx, insert_df in config_insert_df.iterrows():
                calc_type = insert_df["calc"]
                required_vars = {"A-B": ["A", "B"], "(A-B)/B": ["A", "B"], "A/B": ["A", "B"], "B/C": ["B", "C"]}

                # 检查所需列是否存在
                missing_vars = [var for var in required_vars.get(calc_type, []) if var not in calc_data_df.columns]
                if missing_vars:
                    print(
                        f"Warning: Cannot compute {calc_type} for form {form}. Missing columns: {missing_vars}. Skipping.")
                    continue

                # 执行计算
                try:
                    if calc_type == "A-B":
                        calc_data_df["data"] = calc_data_df["A"] - calc_data_df["B"]
                    elif calc_type == "(A-B)/B":
                        calc_data_df["data"] = (calc_data_df["A"] - calc_data_df["B"]) / calc_data_df["B"].where(
                            calc_data_df["B"] != 0, np.nan)
                    elif calc_type == "A/B":
                        calc_data_df["data"] = calc_data_df["A"] / calc_data_df["B"].where(calc_data_df["B"] != 0,
                                                                                           np.nan)
                    elif calc_type == "B/C":
                        calc_data_df["data"] = calc_data_df["B"] / calc_data_df["C"].where(calc_data_df["C"] != 0,
                                                                                           np.nan)
                except Exception as e:
                    print(f"Error computing {calc_type} for form {form}: {str(e)}. Skipping.")
                    continue

                calc_data_df["Account"] = insert_df["Account"]
                df_insert = calc_data_df[["Entity", "Period", "Account", "data"]]
                df_index = insert_df[
                    ["Scenario", "Measure", "Tax", "Version", "Year", "Department", "Material", "Allocation", "Misc1",
                     "Misc2"]
                ]
                for columnName, columnData in df_index.items():
                    df_insert[columnName] = df_index[columnName]
                insert_res_df = pd.concat([insert_res_df, df_insert])

        # 处理插入数据
        if not insert_res_df.empty:
            insert_res_df = insert_res_df.replace([np.inf, -np.inf], 0)
            insert_res_df = insert_res_df.fillna(0)
            print("最后插入审核指标", insert_res_df)
            cube_.save_cube(df=insert_res_df, cube_name=self.cube)
        else:
            print("Warning: No data to insert into cube.")


def main(p1, p2):
    # p2 = {'Year': '2024', 'Entity': 'XN34001_01', 'Version': 'Y1', 'Allocation': 'Original', 'Tax': 'Tax', 'misc2': 'Nomisc2', 'Department': 'Operation', 'Measure': 'Expenses', 'sheetName': '原材料单耗填报（集采药剂）', 'sheetId': 'SHT1ff5da80ca67', 'elementName': 'Material', 'folderId': 'DIRe437ed8262b4'}
    # p2 = {'elementName': '_Material_Consuption',
    # 'folderId': 'DIRb6550dd20485',
    # 'sheetName': '其他成本汇总表&检验化验费',
    # 'sheetId': '流程',
    # 'Entity': 'XN61001_01',
    # 'Version': 'Y1',
    # 'Tax': 'Tax',
    # 'Department': 'Operation',
    # 'Misc1': 'Nomisc1',
    # 'Misc2': 'Nomisc2',
    # 'Allocation': 'Original',
    # 'Measure': 'Expenses',
    # 'year': '2025',
    # 'entity': 'XN61001_01',
    # 'sheet_id': 'SHTbe2df9108365'}

    # if "year" not in p2:
    #     p2['year'] = p2['Year']
    # if "sheet_id" not in p2:
    #     p2['sheet_id'] = p2['sheetId']
    # year = p2["year"]
    entity = ""
    sheet_id = '设备类吨水成本相关计算'
    year = Variable('Variable').get('BudYear')
    # year = '2025'

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
    para2 = {'elementName': '_Material_Consuption', 'folderId': 'DIRb6550dd20485', 'sheetName': '原材料明细汇总表',
             'sheetId': 'SHT89dfe31d3a5f4c74af6a3cb2500dd51f', 'Entity': 'XN61001_01', 'Version': 'Y1', 'Tax': 'Tax',
             'Department': 'Operation', 'Misc1': 'Nomisc1', 'Misc2': 'Nomisc2', 'Allocation': 'Original',
             'Measure': 'Expenses', 'year': '2025', 'entity': 'XN61001_01',
             'sheet_id': 'SHT89dfe31d3a5f4c74af6a3cb2500dd51f'}

    main(para1, para2)
