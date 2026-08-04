#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    描述：

    开发： 陈 小

    日期： 2023/8/16 15:05

"""
from functools import reduce

import numpy as np
import pandas as pd
import warnings

warnings.filterwarnings("ignore")

from deepfos.element.finmodel import FinancialCube


def get_cube():
    # 实例化财务模型
    cube = FinancialCube("BEWG")
    return cube


def df_processing(df, year, last_year, scenario_calcyear, scenario_lastyear):
    df_save = df.loc[(df["Scenario"] == scenario_calcyear)
                     & (df["Year"] == year)]

    df_calc = df.loc[(df["Scenario"] == scenario_lastyear)
                     & (df["Year"] == last_year)]

    df_calc = pd.concat([df_save, df_calc], axis=0)
    df_calc.drop(columns=["Scenario"], inplace=True)
    df_calc_series = pd.pivot(
        df_calc,
        index=["Entity", "Version", "Material", "Department", "Allocation", "Tax",
               "Misc1", "Misc2", "Measure", "Period", "Account"],
        columns="Year",
        values="data",
    )
    df_calc = df_calc_series.reset_index()
    return df_calc


def calc_increase_riserate(df, op_year, op_last_year, year_save, scenario_save):
    # 计算Increase，Riserate
    if not df.empty:
        for j in [op_year, op_last_year]:
            if j not in df.columns:
                df[j] = 0
        # 计算逻辑
        df.loc[:, "Increase"] = df.apply(lambda x: x[op_year] - x[op_last_year], axis=1)
        df.loc[:, "Riserate"] = df.apply(
            lambda x: (x[op_year] - x[op_last_year]) / x[op_last_year]
            if x[op_last_year] != 0
            else 0,
            axis=1,
        )
        df.drop(columns=[op_year, op_last_year, "Measure"], inplace=True)
        df["Year"] = year_save
        df["Scenario"] = scenario_save
    else:
        df_result = pd.DataFrame()
    return df


def audit(p2, account_list, year, scenario_save, scenario_calcyear, scenario_lastyear, measure, entity, tax,
          year_save=None):
    # 第四部分：计算审核指标：实际处理水量、干泥量增加额、增长率

    cube = get_cube()

    # 页面维度 Year Entity Version Material Allocation Tax Department Misc1 Misc2 Account Scenario Measure Period
    version = p2["Version"]
    material = p2["Material"]
    allocation = p2["Allocation"]
    department = p2["Department"]
    Misc1 = p2["Misc1"]
    Misc2 = p2["Misc2"]
    last_year = str(int(year) - 1)
    if year_save is None:
        year_save = year
    account = ';'.join(account_list)

    # 模型中取数
    exp = ("Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->Tax{%s}->Misc1{%s}->Misc2{%s}->"
           "Year{%s;%s}->Account{%s}->Scenario{Budget;Combinaion;Actual}->Entity{%s}->Measure{%s}->Period{Noperiod}"
           % (version, material, department, allocation, tax, Misc1, Misc2,
              year, last_year, account, entity, measure))
    df = cube.query(expression=exp, compact=False)
    # print(df.columns)

    # df切片
    df_calc = df_processing(df=df, year=year, last_year=last_year,
                            scenario_lastyear=scenario_lastyear, scenario_calcyear=scenario_calcyear)

    # 计算increase，riserate
    df_save = calc_increase_riserate(df=df_calc, op_year=year, op_last_year=last_year, year_save=year_save,
                                     scenario_save=scenario_save)

    # 清数
    exp_clear = ("Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->Tax{%s}->Misc1{%s}->Misc2{%s}->"
                 "Year{%s}->Account{%s}->Scenario{%s}->Entity{%s}->Measure{Increase;Riserate}->Period{Noperiod}"
                 % (version, material, department, allocation, tax, Misc1, Misc2,
                    year, account, scenario_save, entity))
    cube.delete(exp_clear)
    # 存入数据
    cube.save_unpivot(df_save, unpivot_dim="Measure")
    print("%s场景下的%s审核指标计算完成" % (scenario_save, account))

    return


def df_process(df, account, measure, tax):
    df_acc = df.loc[(df["Account"] == account) & (df["Measure"] == measure) & (df["Tax"] == tax)]
    df_acc.rename(columns={"data": account}, inplace=True)
    df_acc.drop(columns=["Account", "Measure", "Tax"], inplace=True)
    return df_acc


def calc_before(p2, year, scenario):
    cube = get_cube()
    # 清数范围
    del_fix = (
            "Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->Misc1{%s}->Misc2{%s}->"
            "Period{Noperiod}->Entity{IDescendant(1,0)}->Account{A3101020202;A310105;A310103}->"
            "Year{%s}->Scenario{%s}->Tax{Notax}->Measure{Unit}"
            % (
                p2["Version"],
                p2["Material"],
                p2["Department"],
                p2["Allocation"],
                p2["Misc1"],
                p2["Misc2"],
                year,
                scenario,
            )
    )
    cube.delete(expression=del_fix)
    # 取数范围
    exp = (
            "Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->Misc1{%s}->Misc2{%s}->Period{Noperiod}->"
            "Entity{IDescendant(1,0)}->Account{%s}->Year{%s}->Scenario{%s}->Tax{%s}->Measure{%s}"
            % (
                p2["Version"],
                p2["Material"],
                p2["Department"],
                p2["Allocation"],
                p2["Misc1"],
                p2["Misc2"],
                "A05;A310104;A31010201;A31010202;A3101020203",
                year,
                scenario,
                "Tax;Notax",
                "Nomeasure;Expenses",
            )
    )
    df = cube.query(expression=exp, compact=False)
    if not df.empty:
        # df切片
        df_a05 = df_process(df, account="A05", measure="Nomeasure", tax="Tax")
        df_a3101020203 = df_process(df, account="A3101020203", measure="Expenses", tax="Tax")
        df_a310104 = df_process(df, account="A310104", measure="Expenses", tax="Notax")
        df_a31010201 = df_process(df, account="A31010201", measure="Expenses", tax="Notax")
        df_a31010202 = df_process(df, account="A31010202", measure="Expenses", tax="Notax")

        group = ["Year", "Entity", "Scenario", "Period",
                 "Version", "Material", "Allocation", "Department", "Misc1", "Misc2"]

        # 计算A3101020202 = A3101020203 / A05 (吨水电耗:电度电量/[基础生产数据]合计实际处理水量)
        df_a3101020202 = pd.merge(df_a05, df_a3101020203, how="outer", on=group)
        if not df_a3101020202.empty:
            df_a3101020202.loc[:, "A3101020202"] = df_a3101020202.apply(
                lambda x: x["A3101020203"] / x["A05"]
                if pd.notnull(x["A3101020203"]) & pd.notnull(x["A05"]) & (x["A05"] != 0)
                else np.NaN,
                axis=1,
            )

        # 计算A310105 = A310104 / A05 (污泥处理费吨水费用:污泥处理费/[基础生产数据]合计实际处理水量)
        df_a310105 = pd.merge(df_a05, df_a310104, how="outer", on=group)
        if not df_a310105.empty:
            df_a310105.loc[:, "A310105"] = df_a310105.apply(
                lambda x: x["A310104"] / x["A05"]
                if pd.notnull(x["A310104"]) & pd.notnull(x["A05"]) & (x["A05"] != 0)
                else np.NaN,
                axis=1,
            )

        # 计算A310103 = (A31010201+A31010202) / A05 (吨水电费(元/吨):(基本电费+电度电费)/[基础生产数据]合计实际处理水量)
        df_a310103 = reduce(lambda x, y: pd.merge(x, y, on=group, how="outer"),
                            [df_a31010201, df_a31010202, df_a05])
        if not df_a310103.empty:
            df_a310103['A31010201'].fillna(0, inplace=True)
            df_a310103['A31010202'].fillna(0, inplace=True)
            df_a310103.loc[:, "A310103"] = df_a310103.apply(
                lambda x: (x["A31010201"] + x["A31010202"]) / x["A05"]
                if pd.notnull(x["A05"]) & (x["A05"] != 0)
                else np.NaN,
                axis=1,
            )

        # 合并计算结果
        df = reduce(lambda x, y: pd.merge(x, y, on=group, how="outer"),
                    [df_a3101020202, df_a310105, df_a310103])
        if not df.empty:
            df.drop(columns=["A05", "A05_x", "A05_y", "A31010201", "A31010202", "A310104", "A3101020203"], inplace=True)
            df["Tax"] = "Notax"
            df["Measure"] = "Unit"
            # 存数
            cube.save_unpivot(df, unpivot_dim="Account")


def main(p1, p2):
    year = p2["Year"]
    scenario = "Budget"
    calc_before(p2, year, scenario)

    year = str(int(p2["Year"]) - 1)
    scenario = "Actual;New;Combinaion"
    calc_before(p2, year, scenario)

    print("calc before audit down")

    year = p2["Year"]
    entity = "IDescendant(1,0)"
    tax = "Notax"

    scenario_save = "Budget"
    scenario_calcyear = "Budget"
    scenario_lastyear = "Actual"

    account_list = ["A310102", "A310104"]
    measure = "Expenses"
    audit(p2, account_list, year, scenario_save, scenario_calcyear, scenario_lastyear, measure, entity, tax)

    account_list = ["A310103", "A310105", "A3101020202"]
    measure = "Unit"
    audit(p2, account_list, year, scenario_save, scenario_calcyear, scenario_lastyear, measure, entity, tax)

    scenario_save = "Combinaion"
    scenario_calcyear = "Budget"
    scenario_lastyear = "Combinaion"
    year_save = str(int(year) - 1)

    account_list = ["A310102", "A310104"]
    measure = "Expenses"
    audit(p2, account_list, year, scenario_save, scenario_calcyear, scenario_lastyear, measure, entity, tax, year_save)

    account_list = ["A310103", "A310105", "A3101020202"]
    measure = "Unit"
    audit(p2, account_list, year, scenario_save, scenario_calcyear, scenario_lastyear, measure, entity, tax, year_save)


if __name__ == "__main__":
    try:
        from common._debug import para1
    except BaseException:
        pass
    para2 = {
        "Year": "2024",
        "Entity": "XN13001_01",
        "Version": "Y1",
        "Material": "Nomaterial",
        "Allocation": "Original",
        "Tax": "Tax",
        "Department": "Operation",
        "Misc1": "Nomisc1",
        "Misc2": "Nomisc2",
        "sheetName": "电费&污泥费",
        "sheetId": "SHT2dee513bd945",
        "elementName": "Electricity",
        "folderId": "DIRfd5a95b6f89c",
    }
    main(para1, para2)
