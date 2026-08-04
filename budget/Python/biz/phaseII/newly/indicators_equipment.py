# -*- coding: utf-8 -*-
# @Time : 2023/9/12 10:53
# @Author : LiYuXin
# @FileName: indicators_equipment.py
# @Software: PyCharm
# 设备预算汇总的审核指标计算

import asyncio
import time
from functools import reduce

import numpy as np
import pandas as pd
import warnings

warnings.filterwarnings("ignore")

from deepfos.element.finmodel import FinancialCube, AsyncFinancialCube


def df_process(df, account, measure="Expenses", tax="Notax", period="TotalPeriod", department="Equipment"):
    df_acc = df.loc[(df["Account"] == account) & (df["Measure"] == measure) & (df["Tax"] == tax)
                    & (df["Period"] == period) & (df["Department"] == department)]
    df_acc.rename(columns={"data": account}, inplace=True)
    df_acc.drop(columns=["Account", "Measure", "Tax", "Period", "Department"], inplace=True)
    return df_acc


def calc_before(p2, year):
    # 实例化财务模型
    # cube = FinancialCube("BEWG")
    cube = AsyncFinancialCube("BEWG")
    last_year = str(int(year) - 1)
    # 清数范围
    del_fix_bg = (
            "Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->misc1{%s}->misc2{%s}->"
            "Period{TotalPeriod}->Entity{IDescendant(1,0)}->Account{A71;A72;A104}->"
            "Year{%s}->Scenario{%s}->Tax{Notax}->Measure{Unit}"
            % (
                p2["Version"],
                p2["Material"],
                p2["Department"],
                p2["Allocation"],
                p2["misc1"],
                p2["misc2"],
                year,
                "Budget",
            )
    )
    del_fix_ac = (
            "Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->misc1{%s}->misc2{%s}->"
            "Period{TotalPeriod}->Entity{IDescendant(1,0)}->Account{A71;A72;A104}->"
            "Year{%s}->Scenario{%s}->Tax{Notax}->Measure{Unit}"
            % (
                p2["Version"],
                p2["Material"],
                p2["Department"],
                p2["Allocation"],
                p2["misc1"],
                p2["misc2"],
                last_year,
                "Actual",
            )
    )
    # 取数范围
    exp = (
            "Version{%s}->Material{%s}->Department{%s;%s}->Allocation{%s}->misc1{%s}->misc2{%s}->"
            "Entity{IDescendant(1,0)}->Account{%s}->Year{%s;%s}->Scenario{%s}->Tax{%s}->Measure{%s}->Period{%s}"
            % (
                p2["Version"],
                p2["Material"],
                p2["Department"],
                "Operation",
                p2["Allocation"],
                p2["misc1"],
                p2["misc2"],
                "A310201;A310202;A310203;A05",
                year, last_year,
                "Budget;Actual",
                "Tax;Notax",
                "Nomeasure;Expenses",
                "Noperiod;TotalPeriod"
            )
    )

    async def cube_deal():
        results = await asyncio.gather(
            cube.query(expression=exp, compact=False),
            cube.delete(del_fix_bg),
            cube.delete(del_fix_ac),
        )
        return results
    data = asyncio.run(cube_deal())

    df = data[0]
    df_ac = df.loc[(df["Scenario"] == "Actual") & (df["Year"] == last_year)]
    df_bg = df.loc[(df["Scenario"] == "Budget") & (df["Year"] == year)]
    df = pd.concat([df_ac, df_bg], axis=0)

    if not df.empty:
        # df切片
        df_a05 = df_process(df, account="A05", measure="Nomeasure", tax="Tax", period="Noperiod",
                            department="Operation")

        df_a310201_bg = df_process(df_bg, account="A310201")
        df_a310201_ac = df_process(df_ac, account="A310201", period="Noperiod")
        df_a310201 = pd.concat([df_a310201_bg, df_a310201_ac], axis=0)

        df_a310202_bg = df_process(df_bg, account="A310202")
        df_a310202_ac = df_process(df_ac, account="A310202", period="Noperiod")
        df_a310202 = pd.concat([df_a310202_bg, df_a310202_ac], axis=0)

        df_a310203_bg = df_process(df_bg, account="A310203")
        df_a310203_ac = df_process(df_ac, account="A310203", period="Noperiod")
        df_a310203 = pd.concat([df_a310203_bg, df_a310203_ac], axis=0)


        group = ["Year", "Entity", "Scenario",
                 "Version", "Material", "Allocation", "misc1", "misc2"]

        # 计算A71 = A310201 / A05 (吨水设备设施日常维护费=设备设施日常维护费/【基础生产数据】合计实际处理水量)
        df_a71 = pd.merge(df_a05, df_a310201, how="outer", on=group)
        if not df_a71.empty:
            df_a71.loc[:, "A71"] = df_a71.apply(
                lambda x: x["A310201"] / x["A05"]
                if pd.notnull(x["A310201"]) & pd.notnull(x["A05"]) & (x["A05"] != 0)
                else np.NaN,
                axis=1,
            )

        # 计算A72 = A310202 / A05 (吨水设备日常维修费=设备日常维修费/【基础生产数据】合计实际处理水量)
        df_a72 = pd.merge(df_a05, df_a310202, how="outer", on=group)
        if not df_a72.empty:
            df_a72.loc[:, "A72"] = df_a72.apply(
                lambda x: x["A310202"] / x["A05"]
                if pd.notnull(x["A310202"]) & pd.notnull(x["A05"]) & (x["A05"] != 0)
                else np.NaN,
                axis=1,
            )

        # 计算A104 = A310203 / A05 (吨水设备设施大修重置费=设备设施大修重置费/【基础生产数据】合计实际处理水量)
        df_a104 = pd.merge(df_a05, df_a310203, how="outer", on=group)
        if not df_a104.empty:
            df_a72.loc[:, "A104"] = df_a104.apply(
                lambda x: x["A310203"] / x["A05"]
                if pd.notnull(x["A310203"]) & pd.notnull(x["A05"]) & (x["A05"] != 0)
                else np.NaN,
                axis=1,
            )

        # 合并计算结果
        df = reduce(lambda x, y: pd.merge(x, y, on=group, how="outer"),
                    [df_a71, df_a72, df_a104])
        if not df.empty:
            df.drop(columns=["A05", "A05_x", "A05_y", "A310201", "A310202", "A310203"], inplace=True)
            df["Tax"] = "Notax"
            df["Measure"] = "Unit"
            df["Period"] = "TotalPeriod"
            df["Department"] = "Equipment"
            # 存数
            # 实例化财务模型
            cube_now = FinancialCube("BEWG")
            cube_now.save_unpivot(df, unpivot_dim="Account")


def main(p1, p2):
    begin = time.time()
    year_p2 = p2["year"]
    p2_fix = {'Version': 'Y1', 'Material': 'Nomaterial', 'Allocation': 'Original',
              'Department': 'Equipment', 'misc1': 'Nomisc1', 'misc2': 'Nomisc2'}

    # scenario = "Budget"
    # calc_before(p2_fix, year_p2, scenario)
    #
    # year = str(int(year_p2) - 1)
    # scenario = "Actual"
    calc_before(p2_fix, year_p2)

    print("calc before audit down", time.time()-begin)

    from budget.Python.biz.water_revenue.calc_audit_indicators import main as main_audit

    main_audit(p1, p2_fix, account_list=["A71", "A72", "A104"], year=year_p2,
               scenario_save="Budget", scenario_calcyear="Budget", scenario_lastyear="Actual",
               measure="Unit", entity="IDescendant(1,0)", tax="Notax", period="TotalPeriod")

    main_audit(p1, p2_fix, account_list=["A310201", "A310202", "A310203"], year=year_p2,
               scenario_save="Budget", scenario_calcyear="Budget", scenario_lastyear="Actual",
               measure="Expenses", entity="IDescendant(1,0)", tax="Notax", period="TotalPeriod;Noperiod")
    print(time.time()-begin)

if __name__ == "__main__":
    from conf._evn import p1
    p2 = {'year': '2024'}
    main(p1, p2)

