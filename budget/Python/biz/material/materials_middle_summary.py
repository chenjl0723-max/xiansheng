#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    描述： 原材料中类汇总表
            1）药量计算（第一步计算）
            2）费用计算
            3）单价计算
            4）吨水药耗、吨水成本计算
            5）加碳源后△COD/△TN计算
            6）摩尔比计算
            7）税率计算

    开发： 陈 小

    日期： 2023/8/29 10:07

"""
import os
import sys

top_path = os.path.abspath(os.path.join(__file__, "../.."))
sys.path.append(top_path)

import warnings

warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
from budget.Python.common.commons import *
from deepfos.element.variable import Variable
import time

import gc


def delete_deepcube(year, last_year, measure, entity, version, department, allocation, tax, misc1, misc2):
    """
    批量删除数据
    """
    from deepcube.cube.cube import DeepCube
    cube = DeepCube("WS_cube")
    # 数据范围
    cube.init_data(
        {
            "Measure": cube.Measure[measure],
            "Entity": cube.Entity[entity],  # entity = 'XN21012_01'可以，entity='IDescendant(1,0)'
            # "Entity": cube.Entity[entity].IDescendant(),      # entity = '1'
            "Version": cube.Version[version],
            "Department": cube.Department[department],
            "Allocation": cube.Allocation[allocation],
            "Tax": cube.Tax[tax],
            "Misc1": cube.misc1[misc1],
            "Misc2": cube.misc2[misc2],
        }
    )
    cube.scope(
        {
            "Measure": cube.Measure[measure],
            "Entity": cube.Entity[entity],
            "Version": cube.Version[version],
            "Department": cube.Department[department],
            "Allocation": cube.Allocation[allocation],
            "Tax": cube.Tax[tax],
            "Misc1": cube.misc1[misc1],
            "Misc2": cube.misc2[misc2],
        }
    )
    period = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
    period_no = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "Noperiod"]
    material = ["01", "02", "03", "04", "05", "98", "99"]
    c_scope1 = {
        "Account": cube.Account[["YW0301", "PL01020101"]],
        "Material": cube.Material[material],
        "Year": cube.Year[year],
        "Scenario": cube.Scenario["Budget"],
        "Period": cube.Period[period],
    }
    c_scope2 = {
        "Account": cube.Account[["YW0301", "PL01020101"]],
        "Material": cube.Material[material],
        "Year": cube.Year[last_year],
        "Scenario": cube.Scenario["New"],
        "Period": cube.Period["Noperiod"],
    }
    c_scope3 = {
        "Account": cube.Account[["YW0301", "PL01020101"]],
        "Material": cube.Material[material],
        "Year": cube.Year[last_year],
        "Scenario": cube.Scenario["Forecast"],
        "Period": cube.Period[["10", "11", "12"]],
    }
    c_scope4 = {
        "Account": cube.Account["YW0301"],
        "Material": cube.Material[material],
        "Year": cube.Year[year],
        "Scenario": cube.Scenario["Budget"],
        "Period": cube.Period["Noperiod"],
    }
    c_scope5 = {
        "Account": cube.Account["YW0301"],
        "Material": cube.Material[material],
        "Year": cube.Year[last_year],
        "Scenario": cube.Scenario["Actual"],
        "Period": cube.Period["Noperiod"],
    }
    c_scope6 = {
        "Account": cube.Account["PL01020101"],
        "Material": cube.Material[material],
        "Year": cube.Year[year],
        "Scenario": cube.Scenario["Budget"],
        "Period": cube.Period["Noperiod"],
    }
    c_scope7 = {
        "Account": cube.Account["PL01020101"],
        "Material": cube.Material[material],
        "Year": cube.Year[last_year],
        "Scenario": cube.Scenario["Actual"],
        "Period": cube.Period["Noperiod"],
    }
    c_scope8 = {
        "Account": cube.Account["YW0303"],
        "Material": cube.Material[material],
        "Year": cube.Year[last_year],
        "Scenario": cube.Scenario[["Budget", "Actual"]],
        "Period": cube.Period[period_no],
    }
    c_scope9 = {
        "Account": cube.Account["YW0303"],
        "Material": cube.Material[material],
        "Year": cube.Year[last_year],
        "Scenario": cube.Scenario["New"],
        "Period": cube.Period["Noperiod"],
    }
    c_scope10 = {
        "Account": cube.Account["YW0303"],
        "Material": cube.Material[material],
        "Year": cube.Year[last_year],
        "Scenario": cube.Scenario["Forecast"],
        "Period": cube.Period[["10", "11", "12"]],
    }
    c_scope11 = {
        "Account": cube.Account["YW0304"],
        "Material": cube.Material[["01", "02", "03", "04", "99"]],
        "Year": cube.Year[year],
        "Scenario": cube.Scenario["Budget"],
        "Period": cube.Period[period_no],
        "Measure": cube.Measure[["Unit", "Expenses"]],
    }
    c_scope12 = {
        "Account": cube.Account["YW0304"],
        "Material": cube.Material[["01", "02", "03", "04", "99"]],
        "Year": cube.Year[last_year],
        "Scenario": cube.Scenario[["Actual", "New"]],
        "Period": cube.Period["Noperiod"],
        "Measure": cube.Measure[["Unit", "Expenses"]],
    }
    c_scope13 = {
        "Account": cube.Account["YW0304"],
        "Material": cube.Material[["01", "02", "03", "04", "99"]],
        "Year": cube.Year[last_year],
        "Scenario": cube.Scenario["Forecast"],
        "Period": cube.Period[["10", "11", "12"]],
        "Measure": cube.Measure[["Unit", "Expenses"]],
    }
    c_scope14 = {
        "Account": cube.Account["YW0316"],
        "Material": cube.Material[["98", "99"]],
        "Year": cube.Year[year],
        "Scenario": cube.Scenario["Budget"],
        "Period": cube.Period[period_no],
        "Measure": cube.Measure[["Unit", "Expenses"]],
    }
    c_scope15 = {
        "Account": cube.Account["YW0316"],
        "Material": cube.Material[["98", "99"]],
        "Year": cube.Year[last_year],
        "Scenario": cube.Scenario[["Actual", "New"]],
        "Period": cube.Period["Noperiod"],
        "Measure": cube.Measure[["Unit", "Expenses"]],
    }
    c_scope16 = {
        "Account": cube.Account["YW0316"],
        "Material": cube.Material[["98", "99"]],
        "Year": cube.Year[last_year],
        "Scenario": cube.Scenario["Forecast"],
        "Period": cube.Period[["10", "11", "12"]],
        "Measure": cube.Measure[["Unit", "Expenses"]],
    }
    c_scope17 = {
        "Account": cube.Account["YW0306"],
        "Material": cube.Material[material],
        "Year": cube.Year[year],
        "Scenario": cube.Scenario[["Budget", "Actual"]],
        "Period": cube.Period[period_no],
        "Measure": cube.Measure[["Unit", "Expenses"]],
    }
    c_scope18 = {
        "Account": cube.Account["YW0306"],
        "Material": cube.Material[material],
        "Year": cube.Year[last_year],
        "Scenario": cube.Scenario["New"],
        "Period": cube.Period["Noperiod"],
        "Measure": cube.Measure[["Unit", "Expenses"]],
    }
    c_scope19 = {
        "Account": cube.Account["YW0306"],
        "Material": cube.Material[material],
        "Year": cube.Year[last_year],
        "Scenario": cube.Scenario["Forecast"],
        "Period": cube.Period[["10", "11", "12"]],
        "Measure": cube.Measure[["Unit", "Expenses"]],
    }
    c_scope20 = {
        "Account": cube.Account["YW0309"],
        "Material": cube.Material["01"],
        "Year": cube.Year[year],
        "Scenario": cube.Scenario["Budget"],
        "Period": cube.Period[period_no],
    }
    c_scope21 = {
        "Account": cube.Account["YW0309"],
        "Material": cube.Material["01"],
        "Year": cube.Year[last_year],
        "Scenario": cube.Scenario["Actual"],
        "Period": cube.Period["Noperiod"],
    }
    c_scope22 = {
        "Account": cube.Account["YW0309"],
        "Material": cube.Material["01"],
        "Year": cube.Year[last_year],
        "Scenario": cube.Scenario["Forecast"],
        "Period": cube.Period[["10", "11", "12"]],
    }
    c_scope23 = {
        "Account": cube.Account["YW0312"],
        "Material": cube.Material["02"],
        "Year": cube.Year[year],
        "Scenario": cube.Scenario["Budget"],
        "Period": cube.Period[period_no],
    }
    c_scope24 = {
        "Account": cube.Account["YW0312"],
        "Material": cube.Material["02"],
        "Year": cube.Year[last_year],
        "Scenario": cube.Scenario[["Actual", "New"]],
        "Period": cube.Period["Noperiod"],
    }
    c_scope25 = {
        "Account": cube.Account["YW0312"],
        "Material": cube.Material["02"],
        "Year": cube.Year[last_year],
        "Scenario": cube.Scenario["Forecast"],
        "Period": cube.Period[["10", "11", "12"]],
    }
    c_scope26 = {
        "Account": cube.Account[["YW0306", "PL01020101"]],
        "Material": cube.Material[material],
        "Year": cube.Year[year],
        "Scenario": cube.Scenario["Budget"],
        "Period": cube.Period[period_no],
        "Tax": cube.Tax["Notax"],
        "Measure": cube.Measure["Expenses"],
    }
    c_scope27 = {
        "Account": cube.Account[["YW0306", "PL01020101"]],
        "Material": cube.Material[material],
        "Year": cube.Year[last_year],
        "Scenario": cube.Scenario[["New", "Actual"]],
        "Period": cube.Period["Noperiod"],
        "Tax": cube.Tax["Notax"],
        "Measure": cube.Measure["Expenses"],
    }
    c_scope28 = {
        "Account": cube.Account[["YW0306", "PL01020101"]],
        "Material": cube.Material[material],
        "Year": cube.Year[last_year],
        "Scenario": cube.Scenario["Forecast"],
        "Period": cube.Period[["10", "11", "12"]],
        "Tax": cube.Tax["Notax"],
        "Measure": cube.Measure["Expenses"],
    }
    c_scope29 = {
        "Account": cube.Account["YW0306"],
        "Material": cube.Material[material],
        "Year": cube.Year[year],
        "Scenario": cube.Scenario["Budget"],
        "Period": cube.Period["Noperiod"],
        "Tax": cube.Tax["Notax"],
        "Measure": cube.Measure["Unit"],
    }
    c_scope30 = {
        "Account": cube.Account["YW0306"],
        "Material": cube.Material[material],
        "Year": cube.Year[last_year],
        "Scenario": cube.Scenario["Actual"],
        "Period": cube.Period["Noperiod"],
        "Tax": cube.Tax["Notax"],
        "Measure": cube.Measure["Unit"],
    }

    cube.clear_data(c_scope1, c_scope2, c_scope3, c_scope4, c_scope5, c_scope6, c_scope7, c_scope8, c_scope9, c_scope10,
                    c_scope20, c_scope21, c_scope22, c_scope23, c_scope24, c_scope25, c_scope26,
                    c_scope11, c_scope12, c_scope13, c_scope14, c_scope15, c_scope16, c_scope17, c_scope18, c_scope19,
                    c_scope27, c_scope28,
                    c_scope29, c_scope30)
    return


class MMS:
    def __init__(
            self,
    ):
        self.cube = "WS_cube"
        self.fix = (
            "Account{%s}->Material{%s}->Year{%s}->Scenario{%s}->"
            "Period{%s}->Measure{%s}->Entity{%s}->Version{%s}->"
            "Department{%s}->Allocation{%s}->Tax{%s}->Misc1{%s}->"
            "Misc2{%s}"
        )
        # 新增代码
        mater_01 = dim_.get_dim_attr("Material", "Base(MQ01,0)", ["name"])
        mater_02 = dim_.get_dim_attr("Material", "Base(MQ02,0)", ["name"])
        mater_03 = dim_.get_dim_attr("Material", "Base(MQ03,0)", ["name"])
        self.list_mater_01 = list(mater_01["name"])
        self.list_mater_02 = list(mater_02["name"])
        self.list_mater_03 = list(mater_03["name"])

    def _get_site_data(self, year):
        site_df = rdb_.select(
            columns=["Entity", "Site"], tbl="Phosphorus", where=f"t.Year=='{year}'"
        )
        return site_df

    def dosage(self, measure, version, department, allocation, tax, misc1, misc2,
               entity, list_year, period, scenario):
        """
        计算药量
        """
        year = ";".join(list_year)
        dosage_account = "YW0301"
        # 科目赋值的 material
        copy_material = "MQ04;MQ05;MQ98;MQ99"
        # 碳源药剂 01
        carbon_material = "Base(MQ03, 0)"
        # 消毒药剂 04
        disinfectant_material = "Base(MQ02, 0)"

        # 除磷药剂 02
        phosphorus_material = "Base(MQ01, 0)"

        # 获取数据
        material_copy_fix = self.fix % (
            dosage_account,
            copy_material,
            year,
            scenario,
            period,
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            "#root",
            misc2,
        )
        material_copy_df = cube_.query_cube(
            cube_name=self.cube, fix=material_copy_fix, pivot_dim="Material"
        )

        mq_fix = self.fix % (
            "YW0301;YW0302",
            "Base(MQ01, 0);Base(MQ02, 0);Base(MQ03, 0)",
            year,
            scenario,
            period,
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            "Base(#root,0)",
            misc2,
        )
        # 第一步取出全部数据
        df_mq = cube_.query_cube(cube_name=self.cube, fix=mq_fix, pivot_dim="Account")
        df_mq["Account"] = "YW0301"
        for item in ["YW0301", "YW0302"]:
            if item not in df_mq.columns.to_list():
                df_mq[item] = 1
            else:
                df_mq[item] = df_mq[item].fillna(1)
        # 拆分数据，取MQ01，MQ02，MQ03数据
        carbon_df = df_mq[df_mq["Material"].isin(self.list_mater_03)]
        disinfectant_df = df_mq[df_mq["Material"].isin(self.list_mater_02)]
        phosphorus_df = df_mq[df_mq["Material"].isin(self.list_mater_01)]
        del df_mq
        acc_fix = self.fix % (
            "YW0307;YW0317",
            carbon_material + ";" + disinfectant_material + ";" + phosphorus_material,
            year,
            scenario,
            period,
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        df_acc = cube_.query_cube(cube_name=self.cube, fix=acc_fix, pivot_dim="Account")
        for item in ["YW0307", "YW0317"]:
            if item not in df_acc.columns.to_list():
                df_acc[item] = 0
            else:
                df_acc[item] = df_acc[item].fillna(0)

        YW0307_df = df_acc[df_acc["Material"].isin(self.list_mater_03)]
        YW0317_df_dis = df_acc[df_acc["Material"].isin(self.list_mater_02)]
        YW0317_df_phos = df_acc[df_acc["Material"].isin(self.list_mater_01)]

        YW0307_df = YW0307_df[["YW0307", "Period", "Material", "Entity", "Year", "Scenario"]]
        carbon_df = pd.merge(carbon_df, YW0307_df, how="left").fillna(0)
        carbon_df["Material"] = "01"

        YW0317_df_dis = YW0317_df_dis[
            ["YW0317", "Period", "Material", "Entity", "Year", "Scenario"]
        ]
        disinfectant_df = pd.merge(disinfectant_df, YW0317_df_dis, how="left").fillna(0)
        disinfectant_df["Material"] = "04"

        YW0317_df_phos = YW0317_df_phos[
            ["YW0317", "Period", "Material", "Entity", "Year", "Scenario"]
        ]
        phosphorus_df = pd.merge(phosphorus_df, YW0317_df_phos, how="left").fillna(0)
        phosphorus_df["Material"] = "02"

        # material 复制
        if not material_copy_df.empty:
            diff_list = list(
                {"MQ04", "MQ05", "MQ98", "MQ99"}.difference(material_copy_df.columns)
            )
            if diff_list:
                material_copy_df[diff_list] = [0] * len(diff_list)
            material_copy_df = material_copy_df.rename(
                columns={"MQ04": "03", "MQ05": "05", "MQ98": "98", "MQ99": "99"}
            )
        # carbon_df disinfectant_df phosphorus_df 计算
        if not carbon_df.empty:
            diff_list = list({"YW0301", "YW0302", "YW0307"}.difference(carbon_df.columns))
            if diff_list:
                carbon_df[diff_list] = [0] * len(diff_list)
            carbon_df["data"] = carbon_df["YW0301"] * carbon_df["YW0302"] * carbon_df["YW0307"]
            carbon_df = carbon_df.drop(columns=["YW0301", "YW0302", "YW0307"])
        if not disinfectant_df.empty:
            diff_list = list({"YW0301", "YW0302", "YW0317"}.difference(disinfectant_df.columns))
            if diff_list:
                disinfectant_df[diff_list] = [0] * len(diff_list)
            disinfectant_df["data"] = (
                    disinfectant_df["YW0301"] * disinfectant_df["YW0302"] * disinfectant_df["YW0317"]
            )
            disinfectant_df = disinfectant_df.drop(columns=["YW0301", "YW0302", "YW0317"])
        if not phosphorus_df.empty:
            diff_list = list({"YW0301", "YW0302", "YW0317"}.difference(phosphorus_df.columns))
            if diff_list:
                phosphorus_df[diff_list] = [0] * len(diff_list)
            phosphorus_df["data"] = (
                    phosphorus_df["YW0301"] * phosphorus_df["YW0302"] * phosphorus_df["YW0317"]
            )
            phosphorus_df = phosphorus_df.drop(columns=["YW0301", "YW0302", "YW0317"])
            phosphorus_df = phosphorus_df.replace([np.inf, -np.inf], 0)
            phosphorus_df = phosphorus_df.fillna(0)
        material_copy_df = pd.melt(
            material_copy_df,
            id_vars=[
                "Period",
                "Account",
                "Year",
                "Scenario",
                "Measure",
                "Entity",
                "Version",
                "Department",
                "Allocation",
                "Tax",
                "Misc1",
                "Misc2",
            ],
            var_name="Material",
            value_name="data",
        )
        calc_mcdp = pd.concat(
            [carbon_df, disinfectant_df, phosphorus_df, material_copy_df]
        )
        calc_mcdp["Misc1"] = misc1
        # 分组聚合
        calc_mcdp = calc_mcdp.groupby(
            by=[
                "Material",
                "Period",
                "Year",
                "Scenario",
                "Measure",
                "Entity",
                "Version",
                "Department",
                "Allocation",
                "Tax",
                "Misc1",
                "Misc2",
                "Account",
            ],
            as_index=False,
        ).sum()
        # 存数
        calc_mcdp = calc_mcdp.rename(
            columns={
                "Misc1": "Misc1",
                "Misc2": "Misc2",
            }
        )
        # 过滤掉多余的数据
        # 获取Budget
        calc_mcdp_budget = calc_mcdp[
            (calc_mcdp["Scenario"] == "Budget")
            & (
                calc_mcdp["Period"].isin(
                    ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
                )
            )
            & (calc_mcdp["Year"] == list_year[0])
            ]
        # 获取New
        calc_mcdp_new = calc_mcdp[
            (calc_mcdp["Scenario"] == "New")
            & (calc_mcdp["Period"] == "Noperiod")
            & (calc_mcdp["Year"] == list_year[0])
            ]
        # 获取Forcast
        calc_mcdp_forcast = calc_mcdp[
            (calc_mcdp["Scenario"] == "Forecast")
            & (calc_mcdp["Period"].isin(["10", "11", "12"]))
            & (calc_mcdp["Year"] == list_year[1])
            ]
        calc_mcdp = pd.concat([calc_mcdp_budget, calc_mcdp_new, calc_mcdp_forcast])

        if not calc_mcdp.empty:
            cube_.save_cube(cube_name=self.cube, df=calc_mcdp)

    def year_dosage(self, measure, version, department, allocation, tax, misc1, misc2,
                    entity, list_year, period, scenario, fc_var=None):
        year = ";".join(list_year)
        """
        计算全年药量
        """
        account = "YW0301"
        # 科目赋值的 material
        material = "01;02;03;04;05;98;99"
        query_misc1 = "#root"
        # 获取所有数据
        sear_fix = self.fix % (
            account,
            material,
            year,
            scenario,
            "1;2;3;4;5;6;7;8;9;10;11;12;Totalperiod",
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            query_misc1,
            misc2,
        )

        df_data = cube_.query_cube(
            cube_name=self.cube, fix=sear_fix, pivot_dim="Material"
        )
        if df_data.empty:
            return
        # 获取Budget数据
        df_budget = df_data[
            (df_data["Year"] == list_year[0])
            & (df_data["Period"] == "TotalPeriod")
            & (df_data["Scenario"] == "Budget")
            ]

        # 根据fc_var变量获取其他数据
        if fc_var == "Forecast":
            # 这里获取两个数据源
            df_actual = df_data[
                (df_data["Year"] == list_year[1])
                & (
                    df_data["Period"].isin(
                        ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
                    )
                )
                & (df_data["Scenario"] == "Actual")
                ]
            df_fcst = df_data[
                (df_data["Year"] == list_year[1])
                & (df_data["Period"].isin(["10", "11", "12"]))
                & (df_data["Scenario"] == fc_var)
                ]
            df_fcst = pd.concat([df_fcst, df_actual])
            df_fcst["Scenario"] = "Actual"
        else:
            df_fcst = df_data[
                (df_data["Year"] == list_year[1])
                & (
                    df_data["Period"].isin(
                        ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
                    )
                )
                & (df_data["Scenario"] == "Actual")
                ]

        # 将budget与Actual合并起来
        dosage_df = pd.concat([df_fcst, df_budget])
        # 删除无用的数据集
        del df_budget, df_data, df_fcst

        if not dosage_df.empty:
            dosage_df["Misc1"] = misc1
            dosage_df["Period"] = period
            dosage_df = pd.melt(
                dosage_df,
                id_vars=[
                    "Period",
                    "Account",
                    "Year",
                    "Scenario",
                    "Measure",
                    "Entity",
                    "Version",
                    "Department",
                    "Allocation",
                    "Tax",
                    "Misc1",
                    "Misc2",
                ],
                var_name="Material",
                value_name="data",
            )
            # 分组聚合
            dosage_df = dosage_df.groupby(
                by=[
                    "Material",
                    "Period",
                    "Year",
                    "Scenario",
                    "Measure",
                    "Entity",
                    "Version",
                    "Department",
                    "Allocation",
                    "Tax",
                    "Misc1",
                    "Misc2",
                    "Account",
                ],
                as_index=False,
            ).sum()
            # 存数
            dosage_df = dosage_df.rename(
                columns={
                    "Misc1": "Misc1",
                    "Misc2": "Misc2",
                }
            )
            if not dosage_df.empty:
                cube_.save_cube(cube_name=self.cube, df=dosage_df)

    def cost(self, measure, version, department, allocation, tax, misc1, misc2,
             entity, list_year, period, scenario):
        """
        计算 费用
        """
        year = ";".join(list_year)
        raw_material_account = "PL01020101"
        # 材料复制的 material
        copy_material = "MQ01;MQ02;MQ03;MQ04;MQ05;MQ98;MQ99"
        # 获取数据
        material_copy_fix = self.fix % (
            raw_material_account,
            copy_material,
            year,
            scenario,
            period,
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            "#root",
            misc2,
        )
        material_copy_df = cube_.query_cube(
            cube_name=self.cube, fix=material_copy_fix, pivot_dim="Material"
        )
        # material 复制
        if not material_copy_df.empty:
            material_copy_df["Misc1"] = misc1
            diff_list = list(
                {"MQ04", "MQ05", "MQ98", "MQ99", "MQ01", "MQ04", "MQ02"}.difference(
                    material_copy_df.columns
                )
            )
            if diff_list:
                material_copy_df[diff_list] = [0] * len(diff_list)
            material_copy_df = material_copy_df.rename(
                columns={
                    "MQ04": "03",
                    "MQ05": "05",
                    "MQ98": "98",
                    "MQ99": "99",
                    "MQ03": "01",
                    "MQ02": "04",
                    "MQ01": "02",
                }
            )
        else:
            return
        # 分组聚合
        material_copy_df = material_copy_df.groupby(
            by=[
                "Period",
                "Year",
                "Scenario",
                "Measure",
                "Entity",
                "Version",
                "Department",
                "Allocation",
                "Tax",
                "Misc1",
                "Misc2",
                "Account",
            ],
            as_index=False,
        ).sum()
        # 存数
        material_copy_df = material_copy_df.rename(
            columns={
                "Misc1": "Misc1",
                "Misc2": "Misc2",
            }
        )
        # 过滤掉多余的数据
        # 获取Budget
        calc_mcdp_budget = material_copy_df[
            (material_copy_df["Scenario"] == "Budget")
            & (
                material_copy_df["Period"].isin(
                    ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
                )
            )
            & (material_copy_df["Year"] == list_year[0])
            ]
        # 获取New
        calc_mcdp_new = material_copy_df[
            (material_copy_df["Scenario"] == "New")
            & (material_copy_df["Period"] == "Noperiod")
            & (material_copy_df["Year"] == list_year[0])
            ]
        # 获取Forcast
        calc_mcdp_forcast = material_copy_df[
            (material_copy_df["Scenario"] == "Forecast")
            & (material_copy_df["Period"].isin(["10", "11", "12"]))
            & (material_copy_df["Year"] == list_year[1])
            ]
        material_copy_df = pd.concat(
            [calc_mcdp_budget, calc_mcdp_new, calc_mcdp_forcast]
        )

        if not material_copy_df.empty:
            cube_.pivot_data_to_cube(
                cube=self.cube, data=material_copy_df, pivot="Material"
            )

    def year_cost(self, measure, version, department, allocation, tax, misc1, misc2,
                  entity, list_year, period, scenario, fc_var=None):
        """
        计算全年费用
        """
        year = ";".join(list_year)
        account = "PL01020101"
        material = "01;02;03;04;05;98;99"
        # 判断全局变量
        query_misc1 = "#root"

        # 获取所有数据
        sear_fix = self.fix % (
            account,
            material,
            year,
            scenario,
            "1;2;3;4;5;6;7;8;9;10;11;12",
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            query_misc1,
            misc2,
        )

        df_data = cube_.query_cube(
            cube_name=self.cube, fix=sear_fix, pivot_dim="Material"
        )
        if df_data.empty:
            return
        # 获取Budget数据
        df_budget = df_data[
            (df_data["Year"] == list_year[0]) & (df_data["Scenario"] == "Budget")
            ]

        # 根据fc_var变量获取其他数据
        if fc_var == "Forecast":
            # 这里获取两个数据源
            df_actual = df_data[
                (df_data["Year"] == list_year[1])
                & (
                    df_data["Period"].isin(
                        ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
                    )
                )
                & (df_data["Scenario"] == "Actual")
                ]
            df_fcst = df_data[
                (df_data["Year"] == list_year[1])
                & (df_data["Period"].isin(["10", "11", "12"]))
                & (df_data["Scenario"] == fc_var)
                ]
            df_fcst = pd.concat([df_fcst, df_actual])
            df_fcst["Scenario"] = "Actual"
        else:
            df_fcst = df_data[
                (df_data["Year"] == list_year[1])
                & (
                    df_data["Period"].isin(
                        ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
                    )
                )
                & (df_data["Scenario"] == "Actual")
                ]

        # 将budget与Actual合并起来
        cost_df = pd.concat([df_fcst, df_budget])
        # 删除无用的数据集
        del df_budget, df_data, df_fcst

        # material 复制
        if not cost_df.empty:
            cost_df["Period"] = period
            cost_df["Misc1"] = misc1
            # 分组聚合
            cost_df = cost_df.groupby(
                by=[
                    "Period",
                    "Year",
                    "Scenario",
                    "Measure",
                    "Entity",
                    "Version",
                    "Department",
                    "Allocation",
                    "Tax",
                    "Misc1",
                    "Misc2",
                    "Account",
                ],
                as_index=False,
            ).sum()
            # 存数
            cost_df = cost_df.rename(
                columns={
                    "Misc1": "Misc1",
                    "Misc2": "Misc2",
                }
            )
            if not cost_df.empty:
                cube_.pivot_data_to_cube(cube=self.cube, data=cost_df, pivot="Material")

    def unit_price(self, measure, version, department, allocation, tax, misc1, misc2,
                   entity, list_year, period, scenario):
        """
        计算 单价
        """
        year = ";".join(list_year)
        dosage_material_account = "PL01020101;YW0301"
        # 材料复制的 material
        copy_material = "01;02;03;04;05;98;99"
        # 获取数据
        unit_price_fix = self.fix % (
            dosage_material_account,
            copy_material,
            year,
            scenario,
            period,
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        unit_price_df = cube_.query_cube(
            cube_name=self.cube, fix=unit_price_fix, pivot_dim="Account"
        )
        # 单价计算 总价/量*1w
        if not unit_price_df.empty:
            diff_list = list({"YW0301", "PL01020101"}.difference(unit_price_df.columns))
            if diff_list:
                unit_price_df[diff_list] = [0] * len(diff_list)
            unit_price_df["YW0303"] = unit_price_df["PL01020101"] / unit_price_df["YW0301"] * 10000
            unit_price_df.drop(columns=["PL01020101", "YW0301"], inplace=True)
            unit_price_df = unit_price_df.replace([np.inf, -np.inf], 0)
            unit_price_df = unit_price_df.fillna(0)
        # 存数
        unit_price_df = unit_price_df.rename(
            columns={
                "Misc1": "Misc1",
                "Misc2": "Misc2",
            }
        )

        # 过滤数据，将需要保存的数据过滤出来
        # budget
        calc_mcdp_budget = unit_price_df[
            (unit_price_df["Scenario"] == "Budget")
            & (unit_price_df["Year"] == list_year[0])
            ]
        # 获取New
        calc_mcdp_new = unit_price_df[
            (unit_price_df["Scenario"] == "New")
            & (unit_price_df["Period"] == "Noperiod")
            & (unit_price_df["Year"] == list_year[0])
            ]
        # 获取Forcast
        calc_mcdp_forcast = unit_price_df[
            (unit_price_df["Scenario"] == "Forecast")
            & (unit_price_df["Period"].isin(["10", "11", "12"]))
            & (unit_price_df["Year"] == list_year[1])
            ]
        # 获取Actual
        calc_mcdp_actual = unit_price_df[
            (unit_price_df["Scenario"] == "Actual")
            # & (unit_price_df["Period"] == "Noperiod")
            & (unit_price_df["Year"] == list_year[1])
            ]
        unit_price_df = pd.concat(
            [calc_mcdp_budget, calc_mcdp_new, calc_mcdp_forcast, calc_mcdp_actual]
        )
        if not unit_price_df.empty:
            cube_.pivot_data_to_cube(
                cube=self.cube, data=unit_price_df, pivot="Account"
            )

    def drug_water(self, account, material, measure, version, department, allocation, tax, misc1, misc2,
                   entity, list_year, period, scenario, base_df):
        """
        计算吨水药耗 & 吨水成本
        """
        year = ";".join(list_year)
        # 根据参数account 判断参与计算的account是 药量还是费用
        if account in ["YW0304", "YW0316", "YW0304"]:
            calc_account = "YW0301"
        else:
            calc_account = "PL01020101"
        # 获取数据
        unit_measure_fix = self.fix % (
            calc_account,
            material,
            year,
            scenario,
            period,
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        unit_measure_df = cube_.query_cube(cube_name=self.cube, fix=unit_measure_fix)
        # 上边取数太多了，需要按条件过滤一下
        df_budget = unit_measure_df[
            (unit_measure_df["Scenario"] == "Budget")
            & (unit_measure_df["Year"] == list_year[0])
            ]
        if account == "YW0306":
            df_actual = unit_measure_df[
                (unit_measure_df["Scenario"] == "Actual")
                & (unit_measure_df["Year"] == list_year[1])
                ]
        else:
            df_actual = unit_measure_df[
                (unit_measure_df["Scenario"] == "Actual")
                & (unit_measure_df["Year"] == list_year[1])
                & (unit_measure_df["Period"] == "Noperiod")
                ]
        df_new = unit_measure_df[
            (unit_measure_df["Scenario"] == "New")
            & (unit_measure_df["Year"] == list_year[0])
            & (unit_measure_df["Period"] == "Noperiod")
            ]
        df_fcst = unit_measure_df[
            (unit_measure_df["Scenario"] == "Forecast")
            & (unit_measure_df["Year"] == list_year[1])
            & (unit_measure_df["Period"].isin(["10", "11", "12"]))
            ]
        print(df_new)
        unit_measure_df = pd.concat([df_budget, df_new, df_actual, df_fcst])

        # 单价计算 YW0301=总价/量*100 PL01020101=总价/量
        if not unit_measure_df.empty:
            # 关联 total_measure_df 与 base_df
            unit_measure_df = pd.merge(unit_measure_df, base_df, how="left")
            unit_measure_df["Account"] = calc_account
            unit_measure_df["data"] = unit_measure_df["data"] / unit_measure_df["base"]
            if calc_account == "YW0301":
                if account in ["YW0316"]:
                    unit_measure_df["data"] = unit_measure_df["data"] * 1000
                else:
                    unit_measure_df["data"] = unit_measure_df["data"] * 100
            del unit_measure_df["base"]
            unit_measure_df = unit_measure_df.replace([np.inf, -np.inf], 0)
            unit_measure_df = unit_measure_df.fillna(0)
            # 存数
            unit_measure_df = unit_measure_df.rename(
                columns={
                    "Misc1": "Misc1",
                    "Misc2": "Misc2",
                }
            )
            unit_measure_df["Account"] = account
            # 复制一份到Unit
            df_copy = unit_measure_df.copy(deep=True)
            df_copy["Measure"] = 'Unit'
            unit_measure_df = pd.concat([df_copy, unit_measure_df], axis=0)
            if not unit_measure_df.empty:
                cube_.save_cube(cube_name=self.cube, df=unit_measure_df)

    def get_base_df(self, list_year, scenario, period, entity, version,
                    department, allocation, tax, misc1, misc2):
        """
        一次获取重复利用的科目值
        """
        year = ";".join(list_year)
        base_account = "YW0205;YW0208"
        base_fix = self.fix % (
            base_account,
            "Nomaterial",
            year,
            scenario,
            period,
            "Nomeasure",
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        base_df = cube_.query_cube(cube_name=self.cube, fix=base_fix)
        # 处理基础数据
        base_df.drop(columns=["Material", "Measure"], inplace=True)
        base_df = base_df.rename(columns={"data": "base"})
        base_YW0205 = base_df[base_df["Account"] == "YW0205"]
        base_YW0208 = base_df[base_df["Account"] == "YW0208"]
        del base_YW0205["Account"]
        del base_YW0208["Account"]
        return base_YW0205, base_YW0208

    def cn_ratio(self, list_year, scenario, period, measure, entity, version,
                 department, allocation, tax, misc1, misc2):
        """
        加碳源后 碳氮比。
        """
        year = ";".join(list_year)
        account = "YW0309"
        material = "01"
        # 获取药量，YW0301
        account = "YW0301;YW0304"
        material = "01"
        dosage_fix = self.fix % (
            account,
            material,
            year,
            scenario,
            period,
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        dosage_df = cube_.query_cube(
            cube_name=self.cube, fix=dosage_fix, pivot_dim="Account"
        )

        if dosage_df.empty:
            return
        # 获取 进水c 出水c 进水n 出水n
        account = "YW0211;YW0212"
        material = "Nomaterial"
        water_measure = "COD;TN"
        water_fix = self.fix % (
            account,
            material,
            year,
            scenario,
            period,
            water_measure,
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        water_df = cube_.query_cube(
            cube_name=self.cube, fix=water_fix, pivot_dim="Account"
        )
        del water_df["Material"]
        water_cod_df = water_df[water_df["Measure"] == "COD"]
        water_cod_df = water_cod_df.rename(
            columns={
                "YW0211": "YW0211COD",
                "YW0212": "YW0212COD",
            }
        )
        del water_cod_df["Measure"]
        water_tn_df = water_df[water_df["Measure"] == "TN"]
        water_tn_df = water_tn_df.rename(
            columns={
                "YW0211": "YW0211TN",
                "YW0212": "YW0212TN",
            }
        )
        del water_tn_df["Measure"]
        water_df = pd.merge(water_cod_df, water_tn_df, how="left")

        # 计算
        dosage_water_drug_df = pd.merge(dosage_df, water_df, how="left").fillna(0)
        # dosage_water_drug_df = pd.merge(dosage_water_df, drug_df, how="left").fillna(0)
        diff_list = list(
            {"YW0301", "YW0211COD", "YW0211TN", "YW0212COD", "YW0212TN", "YW0304"}.difference(
                dosage_water_drug_df.columns
            )
        )
        if diff_list:
            dosage_water_drug_df[diff_list] = [0] * len(diff_list)
        dosage_water_drug_df = dosage_water_drug_df[dosage_water_drug_df["YW0301"] != 0]
        del dosage_water_drug_df["YW0301"]
        # 【（Account=YW0211，Measure=COD）-（Account=YW0212，Measure=COD）+YW0304】/【（Account=YW0211，Measure=TN）-（Account=YW0212，Measure=TN）】
        dosage_water_drug_df["data"] = (
                                               dosage_water_drug_df["YW0211COD"]
                                               - dosage_water_drug_df["YW0212COD"]
                                               + dosage_water_drug_df["YW0304"]
                                       ) / (dosage_water_drug_df["YW0211TN"] - dosage_water_drug_df["YW0212TN"])

        # 数据存储
        dosage_water_drug_df = dosage_water_drug_df.replace([np.inf, -np.inf], 0)
        dosage_water_drug_df = dosage_water_drug_df.fillna(0)
        # 存数
        dosage_water_drug_df = dosage_water_drug_df.rename(
            columns={
                "Misc1": "Misc1",
                "Misc2": "Misc2",
            }
        )
        dosage_water_drug_df["Account"] = "YW0309"
        del dosage_water_drug_df["YW0211COD"]
        del dosage_water_drug_df["YW0211TN"]
        del dosage_water_drug_df["YW0212COD"]
        del dosage_water_drug_df["YW0212TN"]
        del dosage_water_drug_df["YW0304"]

        # 过滤数据，将需要保存的数据过滤出来
        # budget
        calc_mcdp_budget = dosage_water_drug_df[
            (dosage_water_drug_df["Scenario"] == "Budget")
            & (dosage_water_drug_df["Year"] == list_year[0])
            ]
        # 获取Forcast
        calc_mcdp_forcast = dosage_water_drug_df[
            (dosage_water_drug_df["Scenario"] == "Forecast")
            & (dosage_water_drug_df["Period"].isin(["10", "11", "12"]))
            & (dosage_water_drug_df["Year"] == list_year[1])
            ]
        # 获取Actual
        calc_mcdp_actual = dosage_water_drug_df[
            (dosage_water_drug_df["Scenario"] == "Actual")
            & (dosage_water_drug_df["Period"] == "Noperiod")
            & (dosage_water_drug_df["Year"] == list_year[1])
            ]
        dosage_water_drug_df = pd.concat(
            [calc_mcdp_budget, calc_mcdp_forcast, calc_mcdp_actual]
        )
        if not dosage_water_drug_df.empty:
            cube_.save_cube(cube_name=self.cube, df=dosage_water_drug_df)

    def mol(self, site_df, list_year, scenario, period, measure, entity, version,
            department, allocation, tax, misc1, misc2):
        """
        摩尔比计算
        """
        year = ";".join(list_year)
        material = "02"
        # 查询 吨水药耗（mg/L） YW0304
        drug_fix = self.fix % (
            "YW0304",
            material,
            year,
            scenario,
            period,
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        drug_df = cube_.query_cube(cube_name=self.cube, fix=drug_fix)
        # 查询 Measure=TP Account进水YW0211 Account出水YW0212
        tp_fix = self.fix % (
            "YW0211;YW0212",
            "Nomaterial",
            year,
            scenario,
            period,
            "TP",
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        tp_df = cube_.query_cube(cube_name=self.cube, fix=tp_fix, pivot_dim="Account")
        del tp_df["Measure"]
        del tp_df["Material"]
        # 查询 Account出水YW0212 Measure 二沉池TP ETP Measure TP
        etp_fix = self.fix % (
            "YW0212",
            "Nomaterial",
            year,
            scenario,
            period,
            "TP;ETP",
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        etp_df = cube_.query_cube(cube_name=self.cube, fix=etp_fix, pivot_dim="Measure")
        del etp_df["Account"]
        del etp_df["Material"]
        # 判断执行计算逻辑1还是逻辑2
        drug_df = pd.merge(drug_df, site_df, how="left")
        # 逻辑1 吨水药耗*0.1/当量/(进水水质TP*0.5-出水水质TP),当量为1.645
        logic1_drug_df = drug_df[drug_df["Site"].isin(["二级处理除磷", "二级三级同步处理除磷"])]
        # 逻辑2 吨水药耗*0.1/当量/（二沉池出水TP-出水TP）当量为1.645
        logic2_drug_df = drug_df[drug_df["Site"] == "三级处理除磷"]
        if not logic1_drug_df.empty:
            logic1_drug_df = pd.merge(logic1_drug_df, tp_df, how="left")
            diff_list = list({"data", "YW0211", "YW0212"}.difference(logic1_drug_df.columns))
            if diff_list:
                logic1_drug_df[diff_list] = [0] * len(diff_list)
            logic1_drug_df["data"] = (
                    logic1_drug_df["data"]
                    / (logic1_drug_df["YW0211"] * 0.5 - logic1_drug_df["YW0212"])
                    / 16.45
            )
            logic1_drug_df = logic1_drug_df.replace([np.inf, -np.inf], 0)
            logic1_drug_df = logic1_drug_df.fillna(0)
            del logic1_drug_df["YW0211"]
            del logic1_drug_df["YW0212"]
        if not logic2_drug_df.empty:
            logic2_drug_df = pd.merge(logic2_drug_df, tp_df, how="left")
            logic2_drug_df = pd.merge(logic2_drug_df, etp_df, how="left")
            logic2_drug_df = pd.merge(logic2_drug_df, tp_df, how="left")
            diff_list = list({"data", "ETP", "TP"}.difference(logic2_drug_df.columns))
            if diff_list:
                logic2_drug_df[diff_list] = [0] * len(diff_list)
            logic2_drug_df["data"] = (
                    logic2_drug_df["data"]
                    / (logic2_drug_df["ETP"] - logic2_drug_df["TP"])
                    / 16.45
            )
            logic2_drug_df = logic2_drug_df.replace([np.inf, -np.inf], 0)
            logic2_drug_df = logic2_drug_df.fillna(0)
            del logic2_drug_df["ETP"]
            del logic2_drug_df["TP"]
        drug_df = pd.concat([logic1_drug_df, logic2_drug_df])
        del drug_df["Site"]
        drug_df["Account"] = "YW0312"
        if "YW0211" in drug_df.columns:
            del drug_df["YW0211"]
        if "YW0212" in drug_df.columns:
            del drug_df["YW0212"]

        # 过滤数据，将需要保存的数据过滤出来
        # budget
        calc_mcdp_budget = drug_df[
            (drug_df["Scenario"] == "Budget") & (drug_df["Year"] == list_year[0])
            ]
        # 获取New
        calc_mcdp_new = drug_df[
            (drug_df["Scenario"] == "New")
            & (drug_df["Period"] == "Noperiod")
            & (drug_df["Year"] == list_year[0])
            ]
        # 获取Forcast
        calc_mcdp_forcast = drug_df[
            (drug_df["Scenario"] == "Forecast")
            & (drug_df["Period"].isin(["10", "11", "12"]))
            & (drug_df["Year"] == list_year[1])
            ]
        # 获取Actual
        calc_mcdp_actual = drug_df[
            (drug_df["Scenario"] == "Actual")
            & (drug_df["Period"] == "Noperiod")
            & (drug_df["Year"] == list_year[1])
            ]
        drug_df = pd.concat(
            [calc_mcdp_budget, calc_mcdp_new, calc_mcdp_forcast, calc_mcdp_actual]
        )
        if not drug_df.empty:
            # 存数
            drug_df = drug_df.rename(
                columns={
                    "Misc1": "Misc1",
                    "Misc2": "Misc2",
                }
            )
            cube_.save_cube(cube_name=self.cube, df=drug_df)

    def no_tax(self, account, material, measure, version, department, allocation, tax, misc1, misc2,
               entity, list_year, period, scenario):
        """
        计算税率
        """
        year = ";".join(list_year)
        # 如果scenario为Forecast,取税率的时候用Actual
        rate_scenario = "Budget;New;Actual"
        # if scenario == "Forecast":
        #     rate_scenario = "Actual"
        # 获取税率
        rate_fix = self.fix % (
            "YW0501;YW0502;YW0503;YW0504;YW0505;YW0506;YW0507",
            "Nomaterial",
            year,
            rate_scenario,
            period,
            "Expenses",
            entity,
            version,
            department,
            allocation,
            "Taxrate",
            misc1,
            misc2,
        )
        rate_df = cube_.query_cube(cube_name=self.cube, fix=rate_fix)
        rate_df = rate_df.drop(columns=["Material","Measure", "Tax"])
        # rate_df["Scenario"] = scenario
        rate_df.loc[rate_df["Scenario"] == "Actual", "Scenario"] = "Forecast"
        # 根据税率的account，映射含税金额的material
        rate_df = rate_df.rename(columns={"Account": "Material"})
        am_mapping = {
            "YW0501": "01",
            "YW0502": "02",
            "YW0503": "03",
            "YW0504": "04",
            "YW0505": "05",
            "YW0506": "98",
            "YW0507": "99",
        }
        rate_df["Material"] = rate_df["Material"].apply(lambda x: am_mapping[x])

        rate_df = rate_df.rename(columns={"data": "rate"})
        # 获取tax数据
        tax_fix = self.fix % (
            account,
            material,
            year,
            scenario,
            period,
            measure,
            entity,
            version,
            department,
            allocation,
            "Tax",
            misc1,
            misc2,
        )
        tax_df = cube_.query_cube(cube_name=self.cube, fix=tax_fix)
        if tax_df.empty:
            return
        tax_df = pd.merge(tax_df, rate_df, how="left").fillna(0)
        tax_df["data"] = tax_df["data"] / (1 + tax_df["rate"])
        tax_df = tax_df.replace([np.inf, -np.inf], 0)
        tax_df = tax_df.fillna(0)
        del tax_df["rate"]
        tax_df["Tax"] = "Notax"
        # 存数
        tax_df = tax_df.rename(
            columns={
                "Misc1": "Misc1",
                "Misc2": "Misc2",
            }
        )

        # 过滤数据，将需要保存的数据过滤出来
        # budget
        calc_mcdp_budget = tax_df[
            (tax_df["Scenario"] == "Budget")
            & (tax_df["Year"] == list_year[0])
            & (tax_df["Period"] != "Noperiod")
            ]
        # 获取Forcast
        calc_mcdp_forcast = tax_df[
            (tax_df["Scenario"] == "Forecast")
            & (tax_df["Period"].isin(["10", "11", "12"]))
            & (tax_df["Year"] == list_year[1])
            ]
        # 获取Actual
        calc_mcdp_actual = tax_df[
            (tax_df["Scenario"] == "New")
            & (tax_df["Period"] == "Noperiod")
            & (tax_df["Year"] == list_year[0])
            ]
        tax_df = pd.concat([calc_mcdp_budget, calc_mcdp_forcast, calc_mcdp_actual])

        if not tax_df.empty:
            cube_.save_cube(cube_name=self.cube, df=tax_df)

    def annual_notax(self, account, material, measure, version, department, allocation, tax, misc1, misc2,
                     entity, list_year, period, scenario, fc_var=None):
        year = ";".join(list_year)
        # 获取所有数据
        sear_fix = self.fix % (
            account,
            material,
            year,
            scenario,
            "1;2;3;4;5;6;7;8;9;10;11;12;Totalperiod",
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )

        df_data = cube_.query_cube(cube_name=self.cube, fix=sear_fix)
        if df_data.empty:
            return
        # 获取Budget数据
        df_budget = df_data[
            (df_data["Year"] == list_year[0])
            & (df_data["Scenario"] == "Budget")
            & (df_data["Period"] == "TotalPeriod")
            ]

        # 根据fc_var变量获取其他数据
        if fc_var == "Forecast":
            # 这里获取两个数据源
            df_actual = df_data[
                (df_data["Year"] == list_year[1])
                & (
                    df_data["Period"].isin(
                        ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
                    )
                )
                & (df_data["Scenario"] == "Actual")
                ]
            df_fcst = df_data[
                (df_data["Year"] == list_year[1])
                & (df_data["Period"].isin(["10", "11", "12"]))
                & (df_data["Scenario"] == fc_var)
                ]
            df_fcst = pd.concat([df_fcst, df_actual])
            df_fcst["Scenario"] = "Actual"
        else:
            df_fcst = df_data[
                (df_data["Year"] == list_year[1])
                & (
                    df_data["Period"].isin(
                        ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
                    )
                )
                & (df_data["Scenario"] == "Actual")
                ]

        # 将budget与Actual合并起来
        annual_df = pd.concat([df_fcst, df_budget])
        # 删除无用的数据集
        del df_budget, df_data, df_fcst

        annual_df["Period"] = period

        # 求和
        # 分组聚合
        annual_df = annual_df.groupby(
            by=[
                "Material",
                "Period",
                "Year",
                "Scenario",
                "Measure",
                "Entity",
                "Version",
                "Department",
                "Allocation",
                "Tax",
                "Misc1",
                "Misc2",
                "Account",
            ],
            as_index=False,
        ).sum()
        # 存数
        annual_df = annual_df.rename(
            columns={
                "Misc1": "Misc1",
                "Misc2": "Misc2",
            }
        )
        if not annual_df.empty:
            cube_.save_cube(cube_name=self.cube, df=annual_df)

    def notax(self, account, material, measure, version, department, allocation, tax, misc1, misc2,
              entity, list_year, period, scenario):
        year = ";".join(list_year)
        annual_fix = self.fix % (
            "PL01020101",
            material,
            year,
            scenario,
            period,
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        annual_df = cube_.query_cube(cube_name=self.cube, fix=annual_fix)

        YW0205_fix = self.fix % (
            "YW0205",
            "Nomaterial",
            year,
            scenario,
            period,
            "Nomeasure",
            entity,
            version,
            department,
            allocation,
            "Tax",
            misc1,
            misc2,
        )
        YW0205_df = cube_.query_cube(cube_name=self.cube, fix=YW0205_fix, pivot_dim="Account")
        YW0205_df.drop(columns=["Material", "Measure", "Tax"], inplace=True)

        annual_YW0205_df = pd.merge(annual_df, YW0205_df, how="left").fillna(0)
        if "YW0205" not in annual_YW0205_df.columns:
            annual_YW0205_df["YW0205"] = 0

        annual_YW0205_df["data"] = annual_YW0205_df["data"] / annual_YW0205_df["YW0205"]

        del annual_YW0205_df["YW0205"]
        annual_YW0205_df["Account"] = "YW0306"

        annual_YW0205_df = annual_YW0205_df.replace([np.inf, -np.inf], 0)
        annual_YW0205_df = annual_YW0205_df.fillna(0)

        # 存数
        annual_YW0205_df = annual_YW0205_df.rename(
            columns={
                "Misc1": "Misc1",
                "Misc2": "Misc2",
            }
        )
        # 复制一份到Unit
        df_copy = annual_YW0205_df.copy(deep=True)
        df_copy["Measure"] = 'Unit'
        annual_YW0205_df = pd.concat([df_copy, annual_YW0205_df], axis=0)
        if not annual_YW0205_df.empty:
            cube_.save_cube(cube_name=self.cube, df=annual_YW0205_df)

    def delete_data(self, year, last_year, measure, entity, version,
                    department, allocation, tax, misc1, misc2):
        """
        批量删除数据
        """
        import asyncio
        from deepfos.element.finmodel import AsyncFinancialCube

        period = "1;2;3;4;5;6;7;8;9;10;11;12"
        period_no = "1;2;3;4;5;6;7;8;9;10;11;12;Noperiod"
        material = "01;02;03;04;05;98;99"
        l_exp = []
        dosage_fix_budget = self.fix % (
            "YW0301;PL01020101",
            material,
            year,
            "Budget",
            period,
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        dosage_fix_new = self.fix % (
            "YW0301;PL01020101",
            material,
            year,
            "New",
            "Noperiod",
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        dosage_fix_fcst = self.fix % (
            "YW0301;PL01020101",
            material,
            last_year,
            "Forecast",
            "10;11;12",
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        l_exp.append(dosage_fix_budget)
        l_exp.append(dosage_fix_new)
        l_exp.append(dosage_fix_fcst)
        year_dosage_fix_budget = self.fix % (
            "YW0301",
            material,
            year,
            "Budget",
            "Noperiod",
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        year_dosage_fix_actual = self.fix % (
            "YW0301",
            material,
            last_year,
            "Actual",
            "Noperiod",
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        l_exp.append(year_dosage_fix_budget)
        l_exp.append(year_dosage_fix_actual)
        # 这个与dosage_fix_budget合并了，这里只做声明，不执行，方便后续有问题排查   开始
        cost_fix_budget = self.fix % (
            "PL01020101",
            material,
            year,
            "Budget",
            period,
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        cost_fix_new = self.fix % (
            "PL01020101",
            material,
            year,
            "New",
            "Noperiod",
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        cost_fix_fcst = self.fix % (
            "PL01020101",
            material,
            last_year,
            "Forecast",
            "10;11;12",
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        # l_exp.append(cost_fix_budget)
        # l_exp.append(cost_fix_new)
        # l_exp.append(cost_fix_fcst)
        # 这个与dosage_fix_budget合并了，这里只做声明，不执行，方便后续有问题排查   结束
        year_cost_budget = self.fix % (
            "PL01020101",
            "01;02;03;04;05;98;99",
            year,
            "Budget",
            "Noperiod",
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        year_cost_actual = self.fix % (
            "PL01020101",
            "01;02;03;04;05;98;99",
            last_year,
            "Actual",
            "Noperiod",
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        l_exp.append(year_cost_budget)
        l_exp.append(year_cost_actual)

        unit_price_fix_budget = self.fix % (
            "YW0303",
            material,
            year,
            "Budget;Actual",
            "1;2;3;4;5;6;7;8;9;10;11;12;Noperiod",
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        unit_price_fix_new_actual = self.fix % (
            "YW0303",
            material,
            year,
            "New",
            "Noperiod",
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        unit_price_fix_fcst = self.fix % (
            "YW0303",
            material,
            last_year,
            "Forecast",
            "10;11;12",
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        l_exp.append(unit_price_fix_budget)
        l_exp.append(unit_price_fix_new_actual)
        l_exp.append(unit_price_fix_fcst)
        drug_water_budget = self.fix % (
            "YW0304",
            "02;01;03;99;04",
            year,
            "Budget;New",
            period_no,
            "Unit;Expenses",
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        drug_water_new_actual = self.fix % (
            "YW0304",
            "02;01;03;99;04",
            last_year,
            "Actual",
            "Noperiod",
            "Unit;Expenses",
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        drug_water_fcst = self.fix % (
            "YW0304",
            "02;01;03;99;04",
            last_year,
            "Forecast",
            "10;11;12",
            "Unit;Expenses",
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        l_exp.append(drug_water_budget)
        l_exp.append(drug_water_new_actual)
        l_exp.append(drug_water_fcst)

        drug_water_budget_51 = self.fix % (
            "YW0316",
            "05;98",
            year,
            "Budget;New",
            period_no,
            "Unit;Expenses",
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        drug_water_new_actual_51 = self.fix % (
            "YW0316",
            "05;98",
            last_year,
            "Actual",
            "Noperiod",
            "Unit;Expenses",
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        drug_water_fcst_51 = self.fix % (
            "YW0316",
            "05;98",
            last_year,
            "Forecast",
            "10;11;12",
            "Unit;Expenses",
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        l_exp.append(drug_water_budget_51)
        l_exp.append(drug_water_new_actual_51)
        l_exp.append(drug_water_fcst_51)
        drug_water_budget_42 = self.fix % (
            "YW0306",
            "01;02;03;04;05;98;99;Total",
            year,
            "Budget;Actual",
            period_no,
            "Unit;Expenses",
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        drug_water_new_actual_42 = self.fix % (
            "YW0306",
            "01;02;03;04;05;98;99;Total",
            year,
            "New",
            "Noperiod",
            "Unit;Expenses",
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        drug_water_fcst_42 = self.fix % (
            "YW0306",
            "01;02;03;04;05;98;99;Total",
            last_year,
            "Forecast",
            "10;11;12",
            "Unit;Expenses",
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        l_exp.append(drug_water_budget_42)
        l_exp.append(drug_water_new_actual_42)
        l_exp.append(drug_water_fcst_42)

        cn_ratio_fix_budget = self.fix % (
            "YW0309",
            "01",
            year,
            "Budget",
            period_no,
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        cn_ratio_fix_actual = self.fix % (
            "YW0309",
            "01",
            last_year,
            "Actual",
            "Noperiod",
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        cn_ratio_fix_fcst = self.fix % (
            "YW0309",
            "01",
            last_year,
            "Forecast",
            "10;11;12",
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        l_exp.append(cn_ratio_fix_budget)
        l_exp.append(cn_ratio_fix_actual)
        l_exp.append(cn_ratio_fix_fcst)
        mol_fix_budget = self.fix % (
            "YW0312",
            "02",
            year,
            "Budget;New",
            period_no,
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        mol_fix_new_actual = self.fix % (
            "YW0312",
            "02",
            last_year,
            "Actual",
            "Noperiod",
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        mol_fix_fcst = self.fix % (
            "YW0312",
            "02",
            last_year,
            "Forecast",
            "10;11;12",
            measure,
            entity,
            version,
            department,
            allocation,
            tax,
            misc1,
            misc2,
        )
        l_exp.append(mol_fix_budget)
        l_exp.append(mol_fix_new_actual)
        l_exp.append(mol_fix_fcst)
        no_tax_fix_budget = self.fix % (
            "PL01020101;YW0306",
            material,
            year,
            "Budget",
            period,
            measure,
            entity,
            version,
            department,
            allocation,
            "Notax",
            misc1,
            misc2,
        )
        no_tax_fix_new = self.fix % (
            "PL01020101;YW0306",
            material,
            year,
            "New",
            "Noperiod",
            measure,
            entity,
            version,
            department,
            allocation,
            "Notax",
            misc1,
            misc2,
        )
        no_tax_fix_fcst = self.fix % (
            "PL01020101;YW0306",
            material,
            last_year,
            "Forecast",
            "10;11;12",
            measure,
            entity,
            version,
            department,
            allocation,
            "Notax",
            misc1,
            misc2,
        )
        l_exp.append(no_tax_fix_budget)
        l_exp.append(no_tax_fix_new)
        l_exp.append(no_tax_fix_fcst)

        annual_notax_fix_budget = self.fix % (
            "PL01020101;YW0306",
            material,
            year,
            "Budget",
            "Noperiod",
            measure,
            entity,
            version,
            department,
            allocation,
            "Notax",
            misc1,
            misc2,
        )
        annual_notax_fix_actual = self.fix % (
            "PL01020101;YW0306",
            material,
            last_year,
            "Actual",
            "Noperiod",
            measure,
            entity,
            version,
            department,
            allocation,
            "Notax",
            misc1,
            misc2,
        )
        l_exp.append(annual_notax_fix_budget)
        l_exp.append(annual_notax_fix_actual)
        # 这两个跟annual_notax方法的删除合并到一起，这里写上不执行，方便后续有问题排查    开始
        notax_fix_budget = self.fix % (
            "YW0306",
            material,
            year,
            "Budget",
            "Noperiod",
            measure,
            entity,
            version,
            department,
            allocation,
            "Notax",
            misc1,
            misc2,
        )
        notax_fix_actual = self.fix % (
            "YW0306",
            material,
            last_year,
            "Actual",
            "Noperiod",
            measure,
            entity,
            version,
            department,
            allocation,
            "Notax",
            misc1,
            misc2,
        )
        # 这两个跟annual_notax方法的删除合并到一起，这里写上不执行，方便后续有问题排查    结束
        # 新增 YW0306 Unit
        notax_fix_budget = self.fix % (
            "YW0306",
            "01;02;03;04;05;98;99;Total",
            year,
            "Budget",
            "Noperiod",
            "Unit;" + measure,
            entity,
            version,
            department,
            allocation,
            "Notax",
            misc1,
            misc2,
        )
        notax_fix_actual = self.fix % (
            "YW0306",
            "01;02;03;04;05;98;99;Total",
            last_year,
            "Actual",
            "Noperiod",
            "Unit;" + measure,
            entity,
            version,
            department,
            allocation,
            "Notax",
            misc1,
            misc2,
        )
        l_exp.append(notax_fix_budget)
        l_exp.append(notax_fix_actual)

        # for fix in l_exp:
        #     cube_.delete(self.cube, fix)

        # 模型中清数,取数

        async def cube_deal(l_exp1):
            bewg_cube = AsyncFinancialCube("WS_cube")
            results = await asyncio.gather(*[bewg_cube.delete(exp) for exp in l_exp1])
            return results

        # if len(l_exp)<=10:
        #     result = asyncio.run(cube_deal(l_exp))
        # else:
        result_all = []
        result = asyncio.run(cube_deal(l_exp[0:10]))
        result_all.append(result)
        result = asyncio.run(cube_deal(l_exp[10:20]))
        result_all.append(result)
        result = asyncio.run(cube_deal(l_exp[20:30]))
        result_all.append(result)
        result = asyncio.run(cube_deal(l_exp[30:]))
        result_all.append(result)
        return result_all

        # 进程、线程
        return result

    def average(self, year, last_year, version, department, allocation, tax, misc1, misc2):
        import asyncio
        from deepfos.element import FinancialCube, AsyncFinancialCube
        from deepfos.element.dimension import Dimension
        # 清数fix
        clear_fix_YW0309_bg = self.fix % ("YW0309", "01", year, "Budget",
                                       "Noperiod", "Unit", "AndFilter(Base(1,0),Attr(ud10,'P01'));ILevel(1,0,1,3)",
                                       version, department, allocation, tax, misc1, misc2)
        clear_fix_YW0309_ac = self.fix % ("YW0309", "01", last_year, "Actual",
                                       "Noperiod", "Unit", "AndFilter(Base(1,0),Attr(ud10,'P01'));ILevel(1,0,1,3)",
                                       version, department, allocation, tax, misc1, misc2)
        clear_fix_YW0312_bg = self.fix % ("YW0312", "02", year, "Budget",
                                       "Noperiod", "Unit", "AndFilter(Base(1,0),Attr(ud10,'P01'));ILevel(1,0,1,3)",
                                       version, department, allocation, tax, misc1, misc2)
        clear_fix_YW0312_ac = self.fix % ("YW0312", "02", last_year, "Actual",
                                       "Noperiod", "Unit", "AndFilter(Base(1,0),Attr(ud10,'P01'));ILevel(1,0,1,3)",
                                       version, department, allocation, tax, misc1, misc2)
        # 取数fix
        query_fix = self.fix % ("YW0309;YW0312", "01;02", year + ';' + last_year, "Budget;Actual",
                                "Noperiod", "Expenses", "AndFilter(Base(1,0),Attr(ud10,'P01'))",
                                version, department, allocation, tax, misc1, misc2)

        async def cube_deal():
            a_cube = AsyncFinancialCube("WS_cube")
            # 异步清数取数
            results = await asyncio.gather(
                a_cube.query(expression=query_fix, compact=False),
                a_cube.delete(expression=clear_fix_YW0309_bg),
                a_cube.delete(expression=clear_fix_YW0309_ac),
                a_cube.delete(expression=clear_fix_YW0312_bg),
                a_cube.delete(expression=clear_fix_YW0312_ac),
            )
            # 切分
            df_YW0309 = results[0].loc[(results[0]["Account"] == "YW0309") & (results[0]["Material"] == "01")]
            df_YW0312 = results[0].loc[(results[0]["Account"] == "YW0312") & (results[0]["Material"] == "02")]
            df = pd.concat([df_YW0309, df_YW0312], axis=0)
            df_bg = df.loc[(df["Scenario"] == "Budget") & (df["Year"] == year)]
            df_ac = df.loc[(df["Scenario"] == "Actual") & (df["Year"] == last_year)]
            df = pd.concat([df_bg, df_ac], axis=0)
            return df

        # 异步清数取数
        df_base = asyncio.run(cube_deal())
        # 保存至unit
        df_base["Measure"] = "Unit"
        df_unit = df_base.copy(deep=True)

        def get_entity():
            entity_dim = Dimension("Entity")
            # 获取 entity base(1, 0)
            init_entity = entity_dim.query("AndFilter(Base(1,0),Attr(ud10,'P01'))",
                                           fields=['name', 'parent_name'], as_model=False)
            init_entity = pd.DataFrame(data=init_entity).loc[:, ["name", "parent_name"]]
            init_entity = init_entity.rename(
                columns={
                    "name": "Entity",
                    "parent_name": "Incorporated_Company"
                }
            )
            region_entity = entity_dim.query("Entity{IDescendant(1,0)}", fields=['name', 'parent_name'], as_model=False)
            region_entity = pd.DataFrame(data=region_entity).loc[:, ["name", "parent_name"]]
            region_entity = region_entity.rename(
                columns={
                    "name": "Incorporated_Company",
                    "parent_name": "Regional_Company"
                }
            )
            init_entity = pd.merge(init_entity, region_entity, how='left')
            region_entity = region_entity.rename(
                columns={
                    "Incorporated_Company": "Regional_Company",
                    "Regional_Company": "Region"
                }
            )
            df_map = pd.merge(init_entity, region_entity, how='left')
            df_map = df_map[~df_map["Region"].isin(['1', '#root'])]
            df_map["Clique"] = "1"
            return df_map

        # 获取entity层级关系
        df_entity = get_entity()
        df = pd.merge(df_base, df_entity, how="left", on="Entity")
        group = ["Year", "Scenario", "Account", "Material", "Period", "Version",
                 "Department", "Allocation", "Measure", "Tax", "Misc1", "Misc2", "data"]
        df_1 = df.loc[:, group + ["Incorporated_Company"]].rename(columns={"Incorporated_Company": "Entity"})
        df_2 = df.loc[:, group + ["Regional_Company"]].rename(columns={"Regional_Company": "Entity"})
        df_3 = df.loc[:, group + ["Region"]].rename(columns={"Region": "Entity"})
        df_4 = df.loc[:, group + ["Clique"]].rename(columns={"Clique": "Entity"})
        df = pd.concat([df_1, df_2, df_3, df_4], axis=0)
        # 聚合求平均值
        group.append("Entity")
        group.remove("data")
        df = df.groupby(group, as_index=False)["data"].mean()

        df_insert = pd.concat([df, df_unit], axis=0)
        cube = FinancialCube("WS_cube")
        cube.save(df_insert)
        print(df["Entity"].tolist())
        return


@resources_monitor()
def do_middle_logic(p1, p2, year, last_year, entity):
    mms = MMS()
    measure = p2["Measure"]
    version = p2["Version"]
    department = p2["Department"]
    allocation = p2["Allocation"]
    tax = p2["Tax"]
    if "Misc1" not in p2:
        p2["Misc1"] = "Nomisc1"
    misc1 = p2["Misc1"]
    misc2 = p2["Misc2"]
    # 获取全局变量
    var = Variable("Variable")
    fc_var = var.get_value("Forcast")

    # 先删除所有要计算的数据
    # t1 = time.time()
    # delete_deepcube(year, last_year, measure, entity, version, department, allocation, tax, misc1, misc2)
    # print("deepcube删数:", time.time()-t1)
    msg = mms.delete_data(
        year,
        last_year,
        measure,
        entity,
        version,
        department,
        allocation,
        tax,
        misc1,
        misc2,
    )
    # print(msg)

    # 药量计算
    # 1-12月
    scenario_list = "Budget;New;Forecast"
    period_list = "1;2;3;4;5;6;7;8;9;10;11;12;Noperiod"
    year_list = [year, last_year]

    mms.dosage(
        measure,
        version,
        department,
        allocation,
        tax,
        misc1,
        misc2,
        entity,
        year_list,
        period_list,
        scenario_list,
    )

    # 全年
    scenario = "Budget;Actual;%s" % fc_var
    period = "Noperiod"

    mms.year_dosage(
        measure,
        version,
        department,
        allocation,
        tax,
        misc1,
        misc2,
        entity,
        year_list,
        period,
        scenario,
        fc_var,
    )

    # 费用计算
    # 1-12月

    scenario_list = "Budget;New;Forecast"
    period_list = "1;2;3;4;5;6;7;8;9;10;11;12;Noperiod"
    mms.cost(
        measure,
        version,
        department,
        allocation,
        tax,
        misc1,
        misc2,
        entity,
        year_list,
        period_list,
        scenario_list,
    )

    # 全年

    scenario = "Budget;Actual;%s" % fc_var
    period = "Noperiod"

    mms.year_cost(
        measure,
        version,
        department,
        allocation,
        tax,
        misc1,
        misc2,
        entity,
        year_list,
        period,
        scenario,
        fc_var,
    )

    # 单价计算
    scenario_list = "Budget;New;Forecast;Actual"
    period_list = "1;2;3;4;5;6;7;8;9;10;11;12;Noperiod"

    mms.unit_price(
        measure,
        version,
        department,
        allocation,
        tax,
        misc1,
        misc2,
        entity,
        year_list,
        period_list,
        scenario_list,
    )

    # 吨水药耗
    account = "YW0304"
    material = "02;01;03;99;04"
    list_scenario = "Budget;New;Actual;Forecast"
    list_period = "1;2;3;4;5;6;7;8;9;10;11;12;Noperiod"

    base_YW0205, base_YW0208 = mms.get_base_df(
        year_list,
        list_scenario,
        list_period,
        "IDescendant(1,0)",
        version,
        department,
        allocation,
        tax,
        misc1,
        misc2,
    )

    mms.drug_water(
        account,
        material,
        measure,
        version,
        department,
        allocation,
        tax,
        misc1,
        misc2,
        entity,
        year_list,
        list_period,
        list_scenario,
        base_YW0205,
    )

    account = "YW0316"
    material = "05;98"
    mms.drug_water(
        account,
        material,
        measure,
        version,
        department,
        allocation,
        tax,
        misc1,
        misc2,
        entity,
        year_list,
        list_period,
        list_scenario,
        base_YW0208,
    )

    # 吨水成本计算
    account = "YW0306"
    material = "02;01;03;04;99;05;98;Total"
    mms.drug_water(
        account,
        material,
        measure,
        version,
        department,
        allocation,
        tax,
        misc1,
        misc2,
        "IDescendant(1,0)",
        year_list,
        list_period,
        list_scenario,
        base_YW0205,
    )

    list_scenario = "Budget;Actual;Forecast"
    list_period = "1;2;3;4;5;6;7;8;9;10;11;12;Noperiod"

    mms.cn_ratio(
        year_list,
        list_scenario,
        list_period,
        measure,
        entity,
        version,
        department,
        allocation,
        tax,
        misc1,
        misc2,
    )

    # 摩尔比计算
    site_df = mms._get_site_data(year)

    list_scenario = "Budget;Actual;New;Forecast"
    list_period = "1;2;3;4;5;6;7;8;9;10;11;12;Noperiod"
    mms.mol(
        site_df,
        year_list,
        list_scenario,
        list_period,
        measure,
        entity,
        version,
        department,
        allocation,
        tax,
        misc1,
        misc2,
    )

    account = "PL01020101;YW0306"
    material = "02;04;01;03;99;05;98"

    tax = "Notax"
    scenario = "Budget;New;Forecast"
    period = "1;2;3;4;5;6;7;8;9;10;11;12;Noperiod"

    mms.no_tax(
        account,
        material,
        measure,
        version,
        department,
        allocation,
        tax,
        misc1,
        misc2,
        entity,
        year_list,
        period,
        scenario,
    )

    tax = "Notax"
    period = "Noperiod"
    account = "PL01020101"

    material = "01;02;03;04;99;05;98"

    scenario = "Budget;Actual;%s" % fc_var
    mms.annual_notax(
        account,
        material,
        measure,
        version,
        department,
        allocation,
        tax,
        misc1,
        misc2,
        entity,
        year_list,
        period,
        scenario,
        fc_var,
    )

    tax = "Notax"
    period = "Noperiod"
    account = "YW0306"

    material = "01;02;03;04;99;05;98;Total"
    scenario = "Budget;Actual"
    mms.notax(
        account,
        material,
        measure,
        version,
        department,
        allocation,
        tax,
        misc1,
        misc2,
        entity,
        year_list,
        period,
        scenario,
    )

    # 新增Unit下汇总为平均值计算
    tax = p2["Tax"]
    mms.average(year, last_year, version, department, allocation, tax, misc1, misc2)


def main(p1, p2):
    # gc.collect()
    if p2["sheetId"] in ["SHTb4ed3d626a2d", "SHT4731243424bc"]:
        del p2["Material"]
    entity = p2["Entity"]
    year = p2["Year"]
    last_year = str(int(p2["Year"]) - 1)
    del p2["Year"]
    del p2["sheetName"]
    del p2["sheetId"]
    del p2["elementName"]
    del p2["folderId"]
    import datetime

    t1 = datetime.datetime.now()
    do_middle_logic(p1=p1, p2=p2, year=year, last_year=last_year, entity=entity)
    t2 = datetime.datetime.now()
    print("执行时间:", t2 - t1)
    # gc.collect()


if __name__ == "__main__":
    try:
        from _debug import para1
    except:
        pass
    para2 = {
        "Year": "2024",
        "Entity": "XN21012_01",
        "Version": "Y1",
        "Allocation": "Original",
        "Tax": "Tax",
        "Misc1": "Nomisc1",
        "Misc2": "Nomisc2",
        "Department": "Operation",
        "Measure": "Expenses",
        "sheetName": "原材料单耗填报",
        "sheetId": "SHTbe2df9108365",
        "elementName": "Material",
        "folderId": "DIRe437ed8262b4",
    }
    main(para1, para2)



