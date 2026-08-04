# -*- coding: utf-8 -*-
# @Time : 2023/9/26 18:24
# @Author : LiYuXin
# @FileName: gross_margin_calc.py
# @Software: PyCharm
import asyncio
import time
import numpy as np
import pandas as pd
import warnings
from deepfos.element.finmodel import FinancialCube, AsyncFinancialCube


class Gross(object):

    def __init__(self, p2):
        # 实例化财务模型
        self.cube = FinancialCube("WS_cube")
        # 页面维度 Year Entity Version Material Allocation Tax Department misc1 misc2 Account Scenario Measure Period
        self.year = p2["Year"]
        self.last_year = str(int(self.year) - 1)
        self.entity = "IDescendant(1,0)"
        self.version = "Y1"
        self.material = 'Total'
        self.allocation = 'Original'
        self.tax = "Notax"
        self.misc1 = "Nomisc1"
        self.misc2 = "Nomisc2"
        self.fix = "Year{%s}->Account{%s}->Entity{%s}->Version{%s}->Scenario{%s}->" \
                   "Department{%s}->Allocation{%s}->Measure{%s}->Period{%s}->" \
                   "Material{%s}->Tax{%s}->Misc1{%s}->Misc2{%s}"

    def delete_all(self):
        fix = "Entity{IDescendant(1,0)}->Version{Y1}->Allocation{Original}->Material{Total}->Tax{Notax}->" \
              "Misc1{Nomisc1}->Misc2{Nomisc2}"
        # 增长额增长率计算清数
        del_fix1 = fix + "->Year{%s}->Account{A35}->Scenario{Budget}->" \
                         "Department{Operation}->Measure{Increase;Riserate}->Period{Noperiod}" % self.year
        # 毛利率计算清数
        del_fix2 = fix + "->Year{%s}->Account{A36}->Scenario{Budget}->" \
                         "Department{Operation}->Measure{Unit}->Period{TotalPeriod}" % self.year
        del_fix3 = fix + "->Year{%s}->Account{A36}->Scenario{Actual}->" \
                         "Department{Operation}->Measure{Unit}->Period{TotalPeriod}" % self.last_year
        # 总付现成本-吨水成本清数
        del_fix4 = fix + "->Year{%s}->Account{A66}->Scenario{Budget}->" \
                         "Department{Operation}->Measure{Unit}->Period{Noperiod}" % self.year
        del_fix5 = fix + "->Year{%s}->Account{A66}->Scenario{Actual;Combinaion;New}->" \
                         "Department{Operation}->Measure{Unit}->Period{Noperiod}" % self.last_year
        # 增长额增长率清数
        del_fix6 = fix + "->Year{%s}->Account{A31;A66}->Scenario{Budget}->" \
                         "Department{Operation}->Measure{Increase;Riserate}->Period{Noperiod}" % self.year
        del_fix7 = fix + "->Year{%s}->Account{A31;A66}->Scenario{Combinaion}->" \
                         "Department{Operation}->Measure{Increase;Riserate}->Period{Noperiod}" % self.last_year

        async def cube_deal():
            cube = AsyncFinancialCube("WS_cube")
            results = await asyncio.gather(
                cube.delete(del_fix1),
                cube.delete(del_fix2),
                cube.delete(del_fix3),
                cube.delete(del_fix4),
                cube.delete(del_fix5),
                cube.delete(del_fix6),
                cube.delete(del_fix7),
            )
            return results
        asyncio.run(cube_deal())
        return

    def delete(self, account, scenario, measure, period, department, year=None):
        if year is None:
            year = self.year
        del_fix = self.fix % (year, account, self.entity, self.version, scenario,
                              department, self.allocation, measure, period,
                              self.material, self.tax, self.misc1, self.misc2)
        self.cube.delete(expression=del_fix)

    def audit(self, account, scenario, measure, period, department):
        # 取数
        exp = self.fix % (self.year + ";" + self.last_year, account, self.entity, self.version, scenario,
                          department, self.allocation, measure, period,
                          self.material, self.tax, self.misc1, self.misc2)
        # 模型中取数
        df = self.cube.query(expression=exp, compact=False)
        if not df.empty:
            # 切分scenario和year
            if "TotalPeriod" in period:
                period_bg = "TotalPeriod"
            else:
                period_bg = "Noperiod"
            group = ["Year", "Account", "Entity", "Version", "Scenario",
                     "Department", "Allocation", "Material", "Measure", "Period",
                     "Tax", "Misc1", "Misc2"]
            if "Actual" in scenario:
                df_ac = df.loc[(df["Scenario"] == "Actual")
                               & (df["Year"] == self.last_year)
                               & (df["Period"] == "Noperiod")]
                df_ac["Scenario"] = "Budget"
                df_ac["Year"] = self.year
                df_bg = df.loc[(df["Scenario"] == "Budget")
                               & (df["Year"] == self.year)
                               & (df["Period"] == period_bg)]
                df_bg["Period"] = "Noperiod"
                df = pd.merge(df_bg, df_ac, how="outer", on=group)
            elif "Combinaion" in scenario:
                df_cb = df.loc[(df["Scenario"] == "Combinaion")
                               & (df["Year"] == self.last_year)
                               & (df["Period"] == "Noperiod")]
                df_bg = df.loc[(df["Scenario"] == "Budget")
                               & (df["Year"] == self.year)
                               & (df["Period"] == period_bg)]
                df_bg["Scenario"] = "Combinaion"
                df_bg["Year"] = self.last_year
                df_bg["Period"] = "Noperiod"
                df = pd.merge(df_bg, df_cb, how="outer", on=group)
            else:
                print(scenario)
                return

            if not df.empty:
                df.fillna(value=0, inplace=True)
                for i in ["data_x", "data_y"]:
                    if i not in df.columns:
                        df[i] = 0
                # 计算逻辑
                df.loc[:, "Increase"] = df.apply(lambda x: x["data_x"] - x["data_y"], axis=1)
                df.loc[:, "Riserate"] = df.apply(
                    lambda x: (x["data_x"] - x["data_y"]) / x["data_y"]
                    if x["data_y"] != 0
                    else 0,
                    axis=1,
                )
                df.drop(columns=["data_x", "data_y", "Measure"], inplace=True)
                df["Department"] = "Operation"
                # 存数
                self.cube.save_unpivot(df, unpivot_dim="Measure")

    def gross_margin(self, account, scenario, measure, period, department):
        # 取数
        exp = self.fix % (self.year + ";" + self.last_year, account, self.entity, self.version, scenario,
                          department, self.allocation, measure, period,
                          self.material, self.tax, self.misc1, self.misc2)
        # 模型中取数
        df = self.cube.query(expression=exp, compact=False, pivot_dim="Account")
        if not df.empty:
            account_list = account.split(";")
            for i in account_list:
                if i not in df.columns:
                    return
            # 切分scenario和year
            df_ac = df.loc[(df["Scenario"] == "Actual")
                           & (df["Year"] == self.last_year)
                           & (df["Period"] == "Noperiod")]
            df_bg = df.loc[(df["Scenario"] == "Budget")
                           & (df["Year"] == self.year)
                           & (df["Period"] == "TotalPeriod")]
            df = pd.concat([df_ac, df_bg], axis=0)
            if not df.empty:
                # A36 = A35/A30
                # 计算相乘
                df.loc[:, "A36"] = df.apply(lambda x: x["A35"] / x["A894"]
                if pd.notnull(x["A35"]) & pd.notnull(x["A894"]) & (x["A894"] != 0)
                else np.NaN,
                                            axis=1)
                df.drop(columns=["A35", "A894"], inplace=True)
                df["Period"] = "TotalPeriod"
                df["Department"] = "Operation"
                df["Measure"] = "Unit"
                # 存数
                self.cube.save_unpivot(df, unpivot_dim="Account")

    def total_cash_outlay(self):
        scenario = "Budget;Actual;Combinaion;New"
        account = "A31;A05"
        period = "TotalPeriod;Noperiod"
        measure = "Expenses;Nomeasure"
        material = "Total;Nomaterial"
        department = "Totaldepartment;Operation"
        tax = "Notax;Tax"
        # 取数"Year{%s}->Account{%s}->Entity{%s}->Version{%s}->Scenario{%s}->" \
        #                    "Department{%s}->Allocation{%s}->Measure{%s}->Period{%s}->" \
        #                    "Material{%s}->Tax{%s}->misc1{%s}->misc2{%s}"
        exp = self.fix % (self.year + ";" + self.last_year, account, self.entity, self.version, scenario,
                          department, self.allocation, measure, period,
                          material, tax, self.misc1, self.misc2)
        # 模型中取数
        df = self.cube.query(expression=exp, compact=False)
        if not df.empty:
            # 切分scenario和year
            df_ac = df.loc[(df["Scenario"].isin(["Actual", "Combinaion", "New"]))
                           & (df["Year"] == self.last_year)
                           & (df["Period"] == "Noperiod")]
            df_bg = df.loc[(df["Scenario"] == "Budget")
                           & (df["Year"] == self.year)]
            df = pd.concat([df_ac, df_bg], axis=0)
            # 切分A31和A05
            df_a31 = df.loc[(df["Account"] == "A31")
                            & (df["Measure"] == "Expenses")
                            & (df["Material"] == "Total")
                            & (df["Department"] == "Totaldepartment")
                            & (df["Tax"] == "Notax")]
            df_a31_bg = df_a31.loc[(df["Scenario"] == "Budget")
                                   & (df["Period"] == "TotalPeriod")]
            df_a31_other = df_a31.loc[(df["Scenario"].isin(["Actual", "Combinaion", "New"]))]
            df_a31 = pd.concat([df_a31_other, df_a31_bg], axis=0)
            df_a31.drop(columns=["Account", "Measure", "Period", "Department"], inplace=True)

            df_a05 = df.loc[(df["Account"] == "A05")
                            & (df["Period"] == "Noperiod")
                            & (df["Measure"] == "Nomeasure")
                            & (df["Material"] == "Nomaterial")
                            & (df["Department"] == "Operation")
                            & (df["Tax"] == "Tax")]
            df_a05.drop(columns=["Account", "Measure", "Tax", "Material"], inplace=True)

            group = ["Year", "Entity", "Version", "Scenario", "Allocation", "Misc1", "Misc2"]
            df = pd.merge(df_a31, df_a05, how="outer", on=group)
            if not df.empty:
                for i in ["data_x", "data_y"]:
                    if i not in df.columns:
                        return
                # A66 = A31/A05
                # 计算相乘
                df.loc[:, "A66"] = df.apply(lambda x: x["data_x"] / x["data_y"]
                                            if pd.notnull(x["data_x"]) & pd.notnull(x["data_y"]) & (x["data_y"] != 0)
                                            else np.NaN,
                                            axis=1)
                df.drop(columns=["data_x", "data_y"], inplace=True)
                df["Measure"] = "Unit"
                df["Tax"] = "Notax"
                df["Material"] = "Total"
                df["Period"] = "Noperiod"
                df["Department"] = "Operation"
                # 存数
                self.cube.save_unpivot(df, unpivot_dim="Account")


def main(p1, p2):
    begin = time.time()
    # 实例化
    g = Gross(p2)
    # 清数汇总
    g.delete_all()

    # # 增长额增长率计算清数
    # account = "A35"
    # scenario = "Budget"
    # measure = "Increase;Riserate"
    # period = "Noperiod"
    # department = "Operation"
    # g.delete(account, scenario, measure, period, department)

    # # 毛利率计算清数
    # account = "A36"
    # scenario = "Budget"
    # measure = "Unit"
    # period = "TotalPeriod"
    # department = "Operation"
    # g.delete(account, scenario, measure, period, department)
    # scenario = "Actual"
    # year = g.last_year
    # g.delete(account, scenario, measure, period, department, year)

    # 增长额增长率计算
    account = "A35"
    scenario = "Budget;Actual"
    measure = "Expenses"
    period = "Noperiod;TotalPeriod"
    department = "Totaldepartment"
    g.audit(account, scenario, measure, period, department)

    # 毛利率计算
    account = "A894;A35"
    scenario = "Budget;Actual"
    period = "Noperiod;TotalPeriod"
    department = "Totaldepartment"
    measure = "Expenses"
    g.gross_margin(account, scenario, measure, period, department)

    # # 总付现成本-吨水成本清数
    # account = "A66"
    # measure = "Unit"
    # period = "Noperiod"
    # department = "Operation"
    # scenario = "Budget"
    # g.delete(account, scenario, measure, period, department)
    # scenario = "Actual;Combinaion;New"
    # year = g.last_year
    # g.delete(account, scenario, measure, period, department, year)

    # 总付现成本-吨水成本计算
    g.total_cash_outlay()

    # # 增长额增长率清数
    # account = "A31;A66"
    # scenario = "Budget"
    # measure = "Increase;Riserate"
    # period = "Noperiod"
    # department = "Operation"
    # g.delete(account, scenario, measure, period, department)
    # scenario = "Combinaion"
    # year = g.last_year
    # g.delete(account, scenario, measure, period, department, year)

    # 增长额增长率计算
    account = "A31"
    scenario = "Budget;Actual"
    measure = "Expenses"
    period = "Noperiod;TotalPeriod"
    department = "Totaldepartment"
    g.audit(account, scenario, measure, period, department)

    account = "A31"
    scenario = "Budget;Combinaion"
    measure = "Expenses"
    period = "Noperiod;TotalPeriod"
    department = "Totaldepartment"
    g.audit(account, scenario, measure, period, department)

    account = "A66"
    scenario = "Budget;Actual"
    measure = "Unit"
    period = "Noperiod"
    department = "Operation"
    g.audit(account, scenario, measure, period, department)

    account = "A66"
    scenario = "Budget;Combinaion"
    measure = "Unit"
    period = "Noperiod"
    department = "Operation"
    g.audit(account, scenario, measure, period, department)

    times = time.time() - begin
    print(times)
    return


if __name__ == "__main__":
    # from conf._evn import p1
    try:
        from _debug import para1, para2

        print(para1)
    except ImportError:
        para1 = para2 = {}
    p2 = {'Year': '2024'}
    main(para1, p2)
