#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    描述： 新-检验化验费其他成本审计指标计算
    开发： 杨培泽
    日期： 2025/5/15 17:13

"""
from functools import reduce
# A310107 => YW0404     A73 => YW0412
# 新-计算审核指标    预实完成率、同比增加额、同比增长率

import numpy as np
import pandas as pd
import warnings

warnings.filterwarnings("ignore")

from deepfos.element.finmodel import FinancialCube


def get_cube():
    # 实例化财务模型
    cube = FinancialCube("WS_cube")
    return cube

# 数据处理函数2 为后续增长率计算服务 主要用于对从多维模型（FinancialCube）查询到的数据进行清洗、重组和跨年份 / 场景的合并 切片 + 行转列重塑
def df_processing(df, year, last_year, scenario_calcyear, scenario_lastyear):
    # 将查出来的数据切成两片
    df_save = df.loc[(df["Scenario"] == scenario_calcyear) & (df["Year"] == year)]

    df_calc = df.loc[(df["Scenario"] == scenario_lastyear) & (df["Year"] == last_year)]
    # 把两年（保存年 + 计算年）的数据集拼接在一起
    df_calc = pd.concat([df_save, df_calc], axis=0)
    df_calc.drop(columns=["Scenario"], inplace=True)
    # 按照列索引重新排序
    df_calc_series = pd.pivot(
        df_calc,
        index=[
            "Entity",
            "Version",
            "Material",
            "Department",
            "Allocation",
            "Tax",
            "Misc1",
            "Misc2",
            "Measure",
            "Period",
            "Account",
        ],
        columns="Year",
        values="data",
    )
    df_calc = df_calc_series.reset_index()
    return df_calc

# 数据处理函数2 为后续增长率计算服务 主要用于对从多维模型（FinancialCube）查询到的数据进行清洗、重组和跨年份 / 场景的合并 切片 + 行转列重塑
def df_processing2(df, year, last_year, scenario_calcyear, scenario_lastyear):
    # 将查出来的数据切成两片
    df_save = df.loc[(df["Scenario"] == scenario_calcyear) & (df["Year"] == year)]
    df_calc = df.loc[(df["Scenario"] == scenario_lastyear) & (df["Year"] == last_year)]
    # 把两年（保存年 + 计算年）的数据集拼接在一起
    df_calc = pd.concat([df_save, df_calc], axis=0)
    df_calc.drop(columns=["Year"], inplace=True)
    # 按照列索引重新排序
    df_calc_series = pd.pivot(
        df_calc,
        index=[
            "Entity",
            "Version",
            "Material",
            "Department",
            "Allocation",
            "Tax",
            "Misc1",
            "Misc2",
            "Measure",
            "Period",
            "Account",
        ],
        columns="Scenario",
        values="data",
    )
    df_calc = df_calc_series.reset_index()
    return df_calc


# 三期需求-计算数据框中指定年份数据的增长值（Increase）和增长率（Riserate），并对数据框进行相应的处理
# 匿名函数 lambda x: (x[op_year] - x[op_last_year]) / x[op_last_year] if x[op_last_year] != 0 else 0 计算增长率。
# 如果 op_last_year 列的值不为 0，则计算增长率；否则，将增长率设为 0，避免除以零的错误。
# 将计算得到的增长率存储在 df 的新列 Riserate 中。
def calc_increase_riserate(df, op_year, op_last_year, year_save, scenario):
    # 计算Increase，Riserate
    if not df.empty:
        for j in [op_year, op_last_year]:
            if j not in df.columns:
                df[j] = 0
        # 计算逻辑  x为每一行数据
        df.loc[:, "Increase"] = df.apply(lambda x: x[op_year] - x[op_last_year], axis=1)
        df.loc[:, "Riserate"] = df.apply(
            lambda x: (x[op_year] - x[op_last_year]) / x[op_last_year]
            if x[op_last_year] != 0
            else 0,
            axis=1,
        )
        df.drop(columns=[op_year, op_last_year, "Measure"], inplace=True)
        df["Year"] = year_save
        df["Scenario"] = scenario
    else:
        df = pd.DataFrame()
    return df

# 计算预实完成率
def calc_budget_completion_rate(df, op_year, op_last_year, year_save, scenario):
    # 计算 budget_completion_rate
    if not df.empty:
        for j in [op_year, op_last_year]:
            if j not in df.columns:
                df[j] = 0
        # 计算逻辑
        # 【Pov-1年Actual】/【Pov-1年Budget】
        # 对 DataFrame 的 ** 每一行（axis=1）** 应用 lambda 函数
        df.loc[:, "budget_completion_rate"] = df.apply(
            lambda x: x[op_last_year] / x[op_last_year]
            if x[op_last_year] != 0
            else 0,
            axis=1,
        )
        df.drop(columns=[op_year, op_last_year, "Measure"], inplace=True)
        df["Year"] = year_save
        df["Scenario"] = scenario
    else:
        df = pd.DataFrame()
    return df

def cacl_enter1(
        p2, account_list, year, scenario_save, scenario_calcyear, scenario_lastyear, measure, entity, tax,
        al=None, year_save=None
):
    cube = get_cube()

    # 页面维度 Year Entity Version Material Allocation Tax Department misc1 misc2 Account Scenario Measure Period
    # tax没有取筛选器的值
    version = p2["Version_wb1"]
    material = p2["Material_wb1"]
    allocation = p2["Allocation_wb1"]
    department = p2["Department_wb1"]
    misc1 = p2["Misc1_wb1"]
    misc2 = p2["Misc2_wb1"]
    last_year = str(int(year) - 1)
    if year_save is None:
        year_save = year
    account = ';'.join(account_list)

    # 模型中取数
    # 四期需求去掉Com场景
    exp = (
            "Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->Tax{Notax;Tax}->Misc1{%s}->Misc2{%s}->"
            "Year{%s;%s}->Account{%s}->Scenario{Budget;Actual}->Entity{%s}->Measure{%s}->Period{Noperiod}"
            % (
                version,
                material,
                department,
                allocation,
                # tax,
                misc1,
                misc2,
                year,
                last_year,
                account,
                entity,
                measure,
            )
    )
    df = cube.query(expression=exp, compact=False)
    if al:
        exp_unit = (
                "Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->Tax{Notax;Tax}->Misc1{%s}->Misc2{%s}->"
                "Year{%s;%s}->Account{%s}->Scenario{Budget;Combinaion;Actual}->Entity{%s}->Measure{%s}->Period{Noperiod}"
                % (
                    version,
                    material,
                    department,
                    allocation,
                    # tax,
                    misc1,
                    misc2,
                    year,
                    last_year,
                    al,
                    entity,
                    "Unit",
                )
        )
        df_unit = cube.query(expression=exp_unit, compact=False)
        df_unit['Measure'] = measure

        df = pd.concat([df, df_unit])

    # df切片
    df_calc = df_processing(df=df, year=year, last_year=last_year,
                            scenario_lastyear=scenario_lastyear, scenario_calcyear=scenario_calcyear)

    # 计算increase，riserate
    # 取今年+去年-全场景的数据 存预算场景-今年
    df_save = calc_increase_riserate(df=df_calc, op_year=year, op_last_year=last_year, year_save=year_save,
                                     scenario=scenario_save)

    # 清数
    if al:
        account = account+";"+al+"}"
    exp_clear = (
            "Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->Tax{Notax;Tax}->Misc1{%s}->Misc2{%s}->"
            "Year{%s}->Account{%s}->Scenario{%s}->Entity{%s}->Measure{Increase;Riserate}->Period{Noperiod}"
            % (
                version,
                material,
                department,
                allocation,
                # tax,
                misc1,
                misc2,
                year_save,
                account,
                scenario_save,
                entity,
            )
    )
    cube.delete(exp_clear)
    # 存入数据
    # cube.save_unpivot(df_save1, unpivot_dim="Measure")
    cube.save_unpivot(df_save, unpivot_dim="Measure")
    print("%s场景下的%s审核指标计算完成" % (scenario_save, account))

def cacl_enter2(
        p2, account_list, year, scenario_save, scenario_calcyear, scenario_lastyear, measure, entity, tax,
        al=None, year_save=None
):
    cube = get_cube()

    # 页面维度 Year Entity Version Material Allocation Tax Department misc1 misc2 Account Scenario Measure Period
    # tax没有取筛选器的值
    version = p2["Version_wb1"]
    material = p2["Material_wb1"]
    allocation = p2["Allocation_wb1"]
    department = p2["Department_wb1"]
    misc1 = p2["Misc1_wb1"]
    misc2 = p2["Misc2_wb1"]
    # last_year = str(int(year) - 1)
    last_year = str(int(year))
    if year_save is None:
        year_save = year
    account = ';'.join(account_list)

    # 模型中取数
    #  Year{%s;%s}为取24 + 24两年的数据
    # 四期需求去掉Com场景
    exp = (
            "Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->Tax{Notax;Tax}->Misc1{%s}->Misc2{%s}->"
            "Year{%s;%s}->Account{%s}->Scenario{Budget;Actual}->Entity{%s}->Measure{%s}->Period{Noperiod}"
            % (
                version,
                material,
                department,
                allocation,
                # tax,
                misc1,
                misc2,
                year,
                last_year,
                account,
                entity,
                measure,
            )
    )
    df = cube.query(expression=exp, compact=False)
    if al:
        exp_unit = (
                "Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->Tax{Notax;Tax}->Misc1{%s}->Misc2{%s}->"
                "Year{%s;%s}->Account{%s}->Scenario{Budget;Combinaion;Actual}->Entity{%s}->Measure{%s}->Period{Noperiod}"
                % (
                    version,
                    material,
                    department,
                    allocation,
                    # tax,
                    misc1,
                    misc2,
                    year,
                    last_year,
                    al,
                    entity,
                    "Unit",
                )
        )
        df_unit = cube.query(expression=exp_unit, compact=False)
        df_unit['Measure'] = measure

        df = pd.concat([df, df_unit])

    # df切片
    df_calc = df_processing2(df=df, year=year, last_year=last_year,
                            scenario_lastyear=scenario_lastyear, scenario_calcyear=scenario_calcyear)

    # 计算Budget_Completion_Rate
    # 取 去年 全场景的数据 存预实差异场景-去年
    df_save = calc_budget_completion_rate(df=df_calc, op_year=year, op_last_year=last_year, year_save=year_save,
                                           scenario=scenario_save)

    # 清数
    if al:
        account = account+";"+al+"}"
    exp_clear = (
            "Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->Tax{Notax;Tax}->Misc1{%s}->Misc2{%s}->"
            "Year{%s}->Account{%s}->Scenario{%s}->Entity{%s}->Measure{Increase;Riserate}->Period{Noperiod}"
            % (
                version,
                material,
                department,
                allocation,
                # tax,
                misc1,
                misc2,
                year_save,
                account,
                scenario_save,
                entity,
            )
    )
    cube.delete(exp_clear)
    # 存入数据
    # cube.save_unpivot(df_save1, unpivot_dim="Measure")
    cube.save_unpivot(df_save, unpivot_dim="Measure")
    print("%s场景下的%s审核指标计算完成" % (scenario_save, account))


# 数据处理函数1   主要用于从cube里查数之后进行清洗
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
            "Period{Noperiod}->Entity{IDescendant(1,0)}->Account{PL010206;PL010207;PL010208;PL010209;PL010210;PL010211;PL010212;PL010213;PL010214;PL010215;PL010216;PL010217;PL010218}->"
            "Year{%s}->Scenario{%s}->Tax{Notax}->Measure{Expenses}"
            % (
                p2["Version_wb1"],
                p2["Material_wb1"],
                p2["Department_wb1"],
                p2["Allocation_wb1"],
                p2["Misc1_wb1"],
                p2["Misc2_wb1"],
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
                p2["Version_wb1"],
                p2["Material_wb1"],
                p2["Department_wb1"],
                p2["Allocation_wb1"],
                p2["Misc1_wb1"],
                p2["Misc2_wb1"],
                "PL010206;PL010218;PL010206",
                year,
                scenario,
                "Tax;Notax",
                "Nomeasure;Expenses",
            )
    )
    df = cube.query(expression=exp, compact=False)
    if not df.empty:
        # df切片
        df_yw0205 = df_process(df, account="YW0205", measure="Nomeasure", tax="Tax")
        df_pl010218 = df_process(df, account="PL010218", measure="Expenses", tax="Notax")
        df_pl010206 = df_process(df, account="PL010206", measure="Expenses", tax="Notax")

        group = ["Year", "Entity", "Scenario", "Period",
                 "Version", "Material", "Allocation", "Department", "Misc1", "Misc2"]

        # 计算A310107 = A310106 / A05 (检验化验吨水成本=检验化验费/[基础生产数据]合计实际处理水量)
        df_yw0404 = pd.merge(df_yw0205, df_pl010206, how="outer", on=group)
        if not df_yw0404.empty:
            df_yw0404.loc[:, "YW0404"] = df_yw0404.apply(
                lambda x: x["PL010206"] / x["YW0205"]
                if pd.notnull(x["PL010206"]) & pd.notnull(x["YW0205"]) & (x["YW0205"] != 0)
                else np.NaN,
                axis=1,
            )

        # 计算A73 = A3103 / A05 (其他成本吨水成本=其他成本/[基础生产数据]合计实际处理水量)
        df_yw0412 = pd.merge(df_yw0205, df_pl010218, how="outer", on=group)
        if not df_yw0412.empty:
            df_yw0412.loc[:, "YW0412"] = df_yw0412.apply(
                lambda x: x["PL010218"] / x["YW0205"]
                if pd.notnull(x["PL010218"]) & pd.notnull(x["YW0205"]) & (x["YW0205"] != 0)
                else np.NaN,
                axis=1,
            )

        # 合并计算结果
        df = pd.merge(df_yw0404, df_yw0412, how="outer", on=group)
        if not df.empty:
            df.drop(columns=["YW0205_x", "YW0205_y", "PL010218", "PL010206"], inplace=True)
            df["Tax"] = "Notax"
            df["Measure"] = "Expenses"
            # 存数
            cube.save_unpivot(df, unpivot_dim="Account")


def main(p1, p2):
    # 三期需求-前置计算-A310107 + A73
    # year = p2["Year_wb1"]
    # scenario = "Budget"
    # calc_before(p2, year, scenario)

    # year = str(int(p2["Year_wb1"]) - 1)
    # scenario = "Actual;New;Combinaion"
    # calc_before(p2, year, scenario)

    # 四期需求1-前置计算1-含税-取各个科目的最低组织层级的预算数据，逐级向上汇总
    # 四期需求2-前置计算1-不含税-取各个科目的最低组织层级的预算数据，逐级向上汇总

    # 方案2 双enter函数  分别计算 1.今年-增长额/增长率 和 2.去年-预实完成率
    # 四期需求3-计算 含税-上一年的预实完成率 + 同比增长额 + 同比增长率
    # 1.今年-增长额/增长率  存今年
    account_list = ["PL010206", "PL010207", "PL010208", "PL010209", "PL010210", "PL010211", "PL010212", "PL010213", "PL010214", "PL010215", "PL010216", "PL010217", "PL010218"]
    year = p2["Year_wb1"]
    scenario_save = "Budget"
    scenario_calcyear = "Budget"
    scenario_lastyear = "Actual"
    measure = "Expenses"
    entity = "IDescendant(1,0)"
    tax = "Tax"
    # tax_list = ["PL010206", "PL010207"]
    # al = "YW0404;YW0412"
    cacl_enter1(
        p2, account_list, year, scenario_save, scenario_calcyear, scenario_lastyear, measure, entity, tax
    )

    # 2.去年-预实完成率   存去年
    account_list = ["PL010206", "PL010207", "PL010208", "PL010209", "PL010210", "PL010211", "PL010212", "PL010213", "PL010214", "PL010215", "PL010216", "PL010217", "PL010218"]
    year = str(int(p2["Year_wb1"]) - 1)
    scenario_save = "Difference"
    scenario_calcyear = "Actual"
    scenario_lastyear = "Budget"
    measure = "Expenses"
    entity = "IDescendant(1,0)"
    tax = "Tax"
    year_save = str(int(p2["Year_wb1"]) - 1)
    cacl_enter2(
         p2, account_list, year, scenario_save, scenario_calcyear, scenario_lastyear, measure, entity, tax , year_save=year_save
    )

    # 四期需求4-计算 不含税-上一年的预实完成率 + 同比增长额 + 同比增长率
    # 1.今年-增长额/增长率  存今年
    #  account_list = ["PL010206", "PL010207", "PL010208", "PL010209", "PL010210", "PL010211", "PL010212", "PL010213", "PL010214", "PL010215", "PL010216", "PL010217", "PL010218"]
    #  year = p2["Year_wb1"]
    #  scenario_save = "Budget"
    #  scenario_calcyear = "Budget"
    #  scenario_lastyear = "Actual"
    #  measure = "Expenses"
    #  entity = "IDescendant(1,0)"
    #  tax = "Notax"
    #  # tax_list = ["PL010206", "PL010207"]
    #  # al = "YW0404;YW0412"
    #  cacl_enter1(
    #      p2, account_list, year, scenario_save, scenario_calcyear, scenario_lastyear, measure, entity, tax
    #  )
    #
    #  # 2.去年-预实完成率   存去年
    #  account_list = ["PL010206", "PL010207", "PL010208", "PL010209", "PL010210", "PL010211", "PL010212", "PL010213", "PL010214", "PL010215", "PL010216", "PL010217", "PL010218"]
    #  year = str(int(p2["Year_wb1"]) - 1)
    #  scenario_save = "Difference"
    #  scenario_calcyear = "Actual"
    #  scenario_lastyear = "Budget"
    #  measure = "Expenses"
    #  entity = "IDescendant(1,0)"
    #  tax = "Notax"
    #  year_save = str(int(p2["Year_wb1"]) - 1)
    #  cacl_enter2(
    #      p2, account_list, year, scenario_save, scenario_calcyear, scenario_lastyear, measure, entity, tax , year_save=year_save
    #  )

    # account_list = ["YW0404", "YW0412"]
    # measure = "Unit"
    # scenario_save = "Combinaion"
    # scenario_calcyear = "Budget"
    # scenario_lastyear = "Combinaion"
    # year_save = str(int(p2["Year_wb1"]) - 1)
    # cacl_enter(
    #     p2, account_list, year, scenario_save, scenario_calcyear, scenario_lastyear, measure, entity, tax, year_save=year_save
    # )

    # account_list = ["PL010218"]
    # measure = "Expenses"
    # cacl_enter(
    #     p2, account_list, year, scenario_save, scenario_calcyear, scenario_lastyear, measure, entity, tax, year_save=year_save
    # )


if __name__ == "__main__":
    try:
        from common._debug import para1
    except BaseException:
        pass
    para2 = {
        "Year_wb1": "2025",
        "Entity_wb1": "XN61001_01",
        "Version_wb1": "Y1",
        "Material_wb1": "Nomaterial",
        "Allocation_wb1": "Original",
        "Tax_wb1": "Tax",
        "Department_wb1": "Operation",
        "Misc1_wb1": "Nomisc1",
        "Misc2_wb1": "Nomisc2",
        "sheetName": "电费&污泥费",
        "sheetId": "SHT2dee513bd945",
        "elementName": "Electricity",
        "folderId": "DIRfd5a95b6f89c",
    }
    main(para1, para2)
