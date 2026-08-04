# -*- coding: utf-8 -*-
# @Time : 2023/9/12 10:53
# @Author : LiYuXin
# @FileName: indicators_equipment.py
# @Software: PyCharm
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
    cube = AsyncFinancialCube("WS_cube")
    last_year = str(int(year) - 1)
    # 清数范围
    del_fix_bg = (
            "Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->Misc1{%s}->Misc2{%s}->"
            "Period{TotalPeriod}->Entity{IDescendant(1,0)}->Account{YW0409;YW0411;YW0413}->"
            "Year{%s}->Scenario{%s}->Tax{Tax;Notax}->Measure{Unit}"
            % (
                p2["Version"],
                p2["Material"],
                p2["Department"],
                p2["Allocation"],
                p2["Misc1"],
                p2["Misc2"],
                year,
                "Budget",
            )
    )
    del_fix_ac = (
            "Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->Misc1{%s}->Misc2{%s}->"
            "Period{TotalPeriod}->Entity{IDescendant(1,0)}->Account{YW0409;YW0411;YW0413}->"
            "Year{%s}->Scenario{%s}->Tax{Tax;Notax}->Measure{Unit}"
            % (
                p2["Version"],
                p2["Material"],
                p2["Department"],
                p2["Allocation"],
                p2["Misc1"],
                p2["Misc2"],
                last_year,
                "Actual",
            )
    )
    # 取数范围
    exp = (
            "Version{%s}->Material{%s}->Department{%s;%s}->Allocation{%s}->Misc1{%s}->Misc2{%s}->"
            "Entity{IDescendant(1,0)}->Account{%s}->Year{%s;%s}->Scenario{%s}->Tax{%s}->Measure{%s}->Period{%s}"
            % (
                p2["Version"],
                p2["Material"],
                p2["Department"],
                "Operation",
                p2["Allocation"],
                p2["Misc1"],
                p2["Misc2"],
                "PL01020401;PL01020402;PL010204;YW0205",
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
    print(df)

    if not df.empty:
        # 处理 YW0205，复制 Tax 数据作为 Notax 数据
        df_a05_tax = df_process(df, account="YW0205", measure="Nomeasure", tax="Tax", period="Noperiod",
                                department="Operation")
        df_a05_tax["Tax"]  = "Tax"
        df_a05_notax = df_a05_tax.copy()
        df_a05_notax["Tax"] = "Notax"
        df_a05 = pd.concat([df_a05_tax, df_a05_notax], axis=0)

        # 费用科目：分别处理 Tax 和 Notax
        for tax in ["Tax", "Notax"]:
            # 日常维护费 (PL01020401)
            df_a310201_bg = df_process(df_bg, account="PL01020401", tax=tax)
            df_a310201_ac = df_process(df_ac, account="PL01020401", tax=tax, period="Noperiod")
            df_a310201 = pd.concat([df_a310201_bg, df_a310201_ac], axis=0)

            # 设备设施大修重置费 (PL01020402)
            df_a310203_bg = df_process(df_bg, account="PL01020402", tax=tax)
            df_a310203_ac = df_process(df_ac, account="PL01020402", tax=tax, period="Noperiod")
            df_a310203 = pd.concat([df_a310203_bg, df_a310203_ac], axis=0)

            # 设备类费用 (PL010204)
            df_PL010204_bg = df_process(df_bg, account="PL010204", tax=tax)
            df_PL010204_ac = df_process(df_ac, account="PL010204", tax=tax, period="Noperiod")
            df_PL010204 = pd.concat([df_PL010204_bg, df_PL010204_ac], axis=0)

            group = ["Year", "Entity", "Scenario", "Version", "Material", "Allocation", "Misc1", "Misc2"]

            # 计算 YW0410 = PL01020401 / YW0205
            df_a71 = pd.merge(df_a05[df_a05["Tax"] == tax], df_a310201, how="outer", on=group)
            if not df_a71.empty:
                df_a71.loc[:, "YW0410"] = df_a71.apply(
                    lambda x: x["PL01020401"] / x["YW0205"]
                    if pd.notnull(x["PL01020401"]) & pd.notnull(x["YW0205"]) & (x["YW0205"] != 0)
                    else np.NaN,
                    axis=1,
                )
                df_a71["Tax"] = tax
                print(f"YW0410 ({tax}):", df_a71)

            # 计算 YW0413 = PL01020402 / YW0205
            df_a104 = pd.merge(df_a05[df_a05["Tax"] == tax], df_a310203, how="outer", on=group)
            if not df_a104.empty:
                df_a104.loc[:, "YW0413"] = df_a104.apply(
                    lambda x: x["PL01020402"] / x["YW0205"]
                    if pd.notnull(x["PL01020402"]) & pd.notnull(x["YW0205"]) & (x["YW0205"] != 0)
                    else np.NaN,
                    axis=1,
                )
                df_a104["Tax"] = tax
                print(f"YW0413 ({tax}):", df_a104)

            # 计算 YW0409 = PL010204 / YW0205
            df_YW0409 = pd.merge(df_a05[df_a05["Tax"] == tax], df_PL010204, how="outer", on=group)
            if not df_YW0409.empty:
                df_YW0409.loc[:, "YW0409"] = df_YW0409.apply(
                    lambda x: x["PL010204"] / x["YW0205"]
                    if pd.notnull(x["PL010204"]) & pd.notnull(x["YW0205"]) & (x["YW0205"] != 0)
                    else np.NaN,
                    axis=1,
                )
                df_YW0409["Tax"] = tax
                print(f"YW0409 ({tax}):", df_YW0409)

            # 合并当前 tax 的计算结果
            df_tax = reduce(lambda x, y: pd.merge(x, y, on=group + ["Tax"], how="outer"),
                            [df_a71, df_a104, df_YW0409])
            df_tax["Measure"] = "Unit"
            df_tax["Period"] = "TotalPeriod"
            df_tax["Department"] = "Equipment"

            # 合并到总结果
            if tax == "Tax":
                df_result = df_tax
            else:
                df_result = pd.concat([df_result, df_tax], axis=0)

        # 清理多余列
        df_result.drop(columns=["YW0205_x", "YW0205_y", "PL01020401", "PL01020402", "PL010204"], errors="ignore", inplace=True)
        print("Final result:", df_result)

        # 存数
        cube_now = FinancialCube("WS_cube")
        cube_now.save_unpivot(df_result, unpivot_dim="Account")


def main(p1, p2):
    begin = time.time()
    year_p2 = p2["Year_wb1"]
    p2_fix = {'Version': 'Y1', 'Material': 'Nomaterial', 'Allocation': 'Original',
              'Department': 'Equipment', 'Misc1': 'Nomisc1', 'Misc2': 'Nomisc2'}

    # scenario = "Budget"
    # calc_before(p2_fix, year_p2, scenario)
    #
    # year = str(int(year_p2) - 1)
    # scenario = "Actual"
    calc_before(p2_fix, year_p2)

    print("calc before audit down", time.time()-begin)

    # from Python.biz.phaseII.newly.calc_audit_indicators import main as main_audit
    #
    # main_audit(p1, p2_fix, account_list=["A71", "A72", "A104"], year=year_p2,
    #            scenario_save="Budget", scenario_calcyear="Budget", scenario_lastyear="Actual",
    #            measure="Unit", entity="IDescendant(1,0)", tax="Notax", period="TotalPeriod")
    #
    # main_audit(p1, p2_fix, account_list=["A310201", "A310202", "A310203"], year=year_p2,
    #            scenario_save="Budget", scenario_calcyear="Budget", scenario_lastyear="Actual",
    #            measure="Expenses", entity="IDescendant(1,0)", tax="Notax", period="TotalPeriod;Noperiod")
    print(time.time()-begin)

if __name__ == "__main__":
    from common._debug import para1,para2
    p2 = {'Year_wb1': '2025'}
    main(para1, p2)

