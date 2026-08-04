#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    描述： 新-检验化验费其他成本审计指标计算
    开发： 杨培泽
    日期： 2025/5/15 17:13

"""
from functools import reduce
# A310107 => YW0404     A73 => YW0412
# 新-计算审核指标
import asyncio
import time
import numpy as np
import pandas as pd
import warnings

warnings.filterwarnings("ignore")
from deepfos.element.finmodel import FinancialCube, AsyncFinancialCube


# from deepfos.element.finmodel import FinancialCube


def get_cube():
    # 实例化财务模型
    cube = FinancialCube("WS_cube")
    return cube


# 数据处理函数1   主要用于before函数    从cube里查数之后进行清洗
def df_process(df, account, measure, tax):
    df_acc = df.loc[(df["Account"] == account) & (df["Measure"] == measure) & (df["Tax"] == tax)]
    df_acc.rename(columns={"data": account}, inplace=True)
    # df_acc.drop(columns=["Account", "Measure", "Tax"], inplace=True)
    df_acc.drop(columns=["Account", "Measure"], inplace=True)
    return df_acc


def calc_before(p2, year, scenario):
    cube = get_cube()
    # 清数范围  清Unit + Total
    del_fix = (
            "Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->Misc1{%s}->Misc2{%s}->"
            "Period{Noperiod}->Entity{IDescendant(1,0)}->Account{YW0405}->"
            "Year{%s}->Scenario{%s}->Tax{Notax;Tax}->Measure{Unit}"
            % (
                p2["Version_wb1"],
                "Total",
                p2["Department_wb1"],
                p2["Allocation_wb1"],
                p2["Misc1_wb1"],
                p2["Misc2_wb1"],
                year,
                scenario,
            )
    )
    cube.delete(expression=del_fix)
    # 取数范围  取Exnpenses + Nomeasure + Total + Tax;Notax
    exp = (
            "Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->Misc1{%s}->Misc2{%s}->Period{Noperiod}->"
            "Entity{IDescendant(1,0)}->Account{%s}->Year{%s}->Scenario{%s}->Tax{%s}->Measure{%s}"
            % (
                p2["Version_wb1"],
                "Total",
                # p2["Material_wb1"],
                p2["Department_wb1"],
                p2["Allocation_wb1"],
                p2["Misc1_wb1"],
                p2["Misc2_wb1"],
                "PL0102;YW0205",
                year,
                scenario,
                "Tax;Notax",
                "Expenses;Nomeasure",
            )
    )
    df = cube.query(expression=exp, compact=False)
    if not df.empty:
        # df切片
        # df_yw0205 = df_process(df, account="YW0205", measure="Nomeasure", tax="Tax")
        # df_pl010218 = df_process(df, account="PL010218", measure="Expenses", tax="Notax")
        # df_pl010206 = df_process(df, account="PL010206", measure="Expenses", tax="Notax")
        df_pl0102_Tax = df_process(df, account="PL0102", measure="Expenses", tax="Tax")
        df_pl0102_Notax = df_process(df, account="PL0102", measure="Expenses", tax="Notax")
        df_yw0205_Tax = df_process(df, account="YW0205", measure="Nomeasure", tax="Tax")
        df_yw0205_Notax = df_process(df, account="YW0205", measure="Nomeasure", tax="Notax")
        group = ["Year", "Entity", "Scenario", "Period",
                 "Version", "Material", "Allocation", "Department", "Misc1", "Misc2"]

        df_yw0405_Tax = pd.merge(df_pl0102_Tax, df_yw0205_Tax, how="outer", on=group)
        if not df_yw0405_Tax.empty:
            df_yw0405_Tax.loc[:, "YW0405"] = df_yw0405_Tax.apply(
                lambda x: x["PL0102"] / x["YW0205"]
                if pd.notnull(x["PL0102"]) & pd.notnull(x["YW0205"]) & (x["YW0205"] != 0)
                else np.NaN,
                axis=1,
            )
        df_yw0405_Notax = pd.merge(df_pl0102_Notax, df_yw0205_Notax, how="outer", on=group)
        if not df_yw0405_Notax.empty:
            df_yw0405_Notax.loc[:, "YW0405"] = df_yw0405_Notax.apply(
                lambda x: x["PL0102"] / x["YW0205"]
                if pd.notnull(x["PL0102"]) & pd.notnull(x["YW0205"]) & (x["YW0205"] != 0)
                else np.NaN,
                axis=1,
            )
        if not df_yw0405_Tax.empty:
            df_yw0405_Tax.drop(columns=["Tax_x", "Tax_y", "PL0102", "YW0205"], inplace=True)
        df_yw0405_Tax["Tax"] = "Tax"
        df_yw0405_Tax["Measure"] = "Unit"
        # 存数
        cube.save_unpivot(df_yw0405_Tax, unpivot_dim="Account")
        if not df_yw0405_Notax.empty:
            df_yw0405_Notax.drop(columns=["Tax_x", "Tax_y", "PL0102", "YW0205"], inplace=True)
        df_yw0405_Notax["Tax"] = "Notax"
        df_yw0405_Notax["Measure"] = "Unit"
        # 存数
        cube.save_unpivot(df_yw0405_Notax, unpivot_dim="Account")


class Gross(object):

    def __init__(self, p2):
        # 实例化财务模型
        self.cube = FinancialCube("WS_cube")
        # 页面维度 Year Entity Version Material Allocation Tax Department Misc1 Misc2 Account Scenario Measure Period
        self.year = p2["Year_wb1"]
        self.last_year = str(int(self.year) - 1)
        self.entity = "IDescendant(1,0)"
        self.version = "Y1"
        self.material = 'Total'
        self.allocation = 'Original'
        # self.tax = "Notax"
        self.tax = "Tax;Notax"
        self.misc1 = "Nomisc1"
        self.misc2 = "Nomisc2"
        # 改为含税 + 不含税
        self.fix = "Year{%s}->Account{%s}->Entity{%s}->Version{%s}->Scenario{%s}->" \
                   "Department{%s}->Allocation{%s}->Measure{%s}->Period{%s}->" \
                   "Material{%s}->Tax{%s}->Misc1{%s}->Misc2{%s}"

    def delete_all(self):
        fix = "Entity{IDescendant(1,0)}->Version{Y1}->Allocation{Original}->Material{Total}->Tax{Tax;Notax}->" \
              "Misc1{Nomisc1}->Misc2{Nomisc2}"
        # 清数1 经营毛利率   清2025预算Unit + 2024实际Unit + 2024预算Unit   清条线汇总 Totaldepartment
        del_fix2 = fix + "->Year{%s}->Account{PL02}->Scenario{Budget}->" \
                         "Department{Totaldepartment}->Measure{Unit}->Period{Noperiod}" % self.year
        del_fix3 = fix + "->Year{%s}->Account{PL02}->Scenario{Actual;Budget}->" \
                         "Department{Totaldepartment}->Measure{Unit}->Period{Noperiod}" % self.last_year
        # 清数2 吨水非薪酬付现成本
        del_fix4 = fix + "->Year{%s}->Account{YW0405}->Scenario{Budget;New}->" \
                         "Department{Totaldepartment}->Measure{Unit}->Period{Noperiod}" % self.year
        # del_fix5 = fix + "->Year{%s}->Account{YW0405}->Scenario{Actual;Combinaion;New}->" \
        del_fix5 = fix + "->Year{%s}->Account{YW0405}->Scenario{Actual}->" \
                         "Department{Totaldepartment}->Measure{Unit}->Period{Noperiod}" % self.last_year

        # 异步访问cube清数
        async def cube_deal():
            cube = AsyncFinancialCube("WS_cube")
            results = await asyncio.gather(
                cube.delete(del_fix2),
                cube.delete(del_fix3),
                cube.delete(del_fix4),
                cube.delete(del_fix5)
            )
            return results

        asyncio.run(cube_deal())
        # 同步访问cube清数
        # async def cube_deal():
        #     cube = AsyncFinancialCube("WS_cube")
        #     results = await asyncio.gather(
        #         cube.delete(del_fix2),
        #         cube.delete(del_fix3),
        #         # cube.delete(del_fix4),
        #         # cube.delete(del_fix5)
        #     )
        #     return results
        # asyncio.run(cube_deal())
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
        # 取数    含税 + 不含税
        exp = self.fix % (self.year + ";" + self.last_year, account, self.entity, self.version, scenario,
                          department, self.allocation, measure, period,
                          self.material, self.tax, self.misc1, self.misc2)
        # self.material, self.tax, self.misc1, self.misc2)
        # 模型中取数
        df = self.cube.query(expression=exp, compact=False, pivot_dim="Account")
        if not df.empty:
            account_list = account.split(";")
            for i in account_list:
                if i not in df.columns:
                    return
            # 切分scenario和year   2024预算 + 2025预算 + 2024实际
            df_ac = df.loc[(df["Scenario"] == "Actual")
                           & (df["Year"] == self.last_year)
                           & (df["Period"] == "Noperiod")]
            df_bg1 = df.loc[(df["Scenario"] == "Budget")
                            & (df["Year"] == self.year)
                            # & (df["Period"] == "Noperiod")]
                            & (df["Period"] == "TotalPeriod")]
            df_bg2 = df.loc[(df["Scenario"] == "Budget")
                            & (df["Year"] == self.last_year)
                            & (df["Period"] == "Noperiod")]

            df = pd.concat([df_ac, df_bg1, df_bg2], axis=0)
            if not df.empty:
                # A36 = A35/A30     经营毛利/运营业务收入
                # PL02=PL01/PL0101
                # 计算相乘
                df.loc[:, "PL02"] = df.apply(lambda x: x["PL01"] / x["PL0101"]
                # if pd.notnull(x["PL01"]) & pd.notnull(x["A894"]) & (x["A894"] != 0)
                if pd.notnull(x["PL01"]) & pd.notnull(x["PL0101"]) & (x["PL0101"] != 0)
                else np.NaN,
                                             axis=1)
                df.drop(columns=["PL01", "PL0101"], inplace=True)
                # df["Period"] = "TotalPeriod"
                df["Period"] = "Noperiod"
                # df["Department"] = "Operation"
                df["Department"] = "Totaldepartment"
                df["Measure"] = "Unit"
                # 存数
                self.cube.save_unpivot(df, unpivot_dim="Account")

    # 计算 吨水非薪酬付现成本 YW0405
    def total_cash_outlay(self):
        print('---------- 计算吨水非薪酬函数开始 ----------')
        # scenario = "Budget;Actual;Combinaion;New"
        scenario = "Budget;Actual;New"
        account = "PL0102;YW0205"
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
        # print('-------- 1.拼接取数表达式 ---------')
        # print(exp)
        # 模型中取数
        # print('------- 2.从cube中取数 --------')
        df = self.cube.query(expression=exp, compact=False)
        # print(df)
        # print(df)

        if not df.empty:
            # 先切分scenario和year
            # print('------- 3..切分scenario和year --------')
            df_ac = df.loc[(df["Scenario"].isin(["Actual"]))
                           & (df["Year"] == self.last_year)
                           & (df["Period"] == "Noperiod")]
            # df_bg = df.loc[(df["Scenario"] == "Budget")
            df_bg = df.loc[(df["Scenario"].isin(["Budget", 'New']))
                           & (df["Year"] == self.year)]
            df = pd.concat([df_ac, df_bg], axis=0)
            # print(df)
            # 再切分A31和A05 不含税 + 含税
            # print('------- 4.切分PL0102和YW0205 不含税 + 含税 --------')
            # 不含税
            # print('------- 不含税数据集 --------')
            df_a31_Notax = df.loc[(df["Account"] == "PL0102")
                                  & (df["Measure"] == "Expenses")
                                  & (df["Material"] == "Total")
                                  & (df["Department"] == "Totaldepartment")
                                  & (df["Tax"] == "Notax")]
            # df_a31_bg_Notax = df_a31_Notax.loc[(df["Scenario"] == "Budget")
            df_a31_bg_Notax = df_a31_Notax.loc[(df["Scenario"].isin(["Budget"]))
                                               & (df["Period"] == "TotalPeriod")]
            df_a31_other_Notax = df_a31_Notax.loc[(df["Scenario"].isin(["Actual", 'New']))]
            df_a31_Notax = pd.concat([df_a31_other_Notax, df_a31_bg_Notax], axis=0)
            df_a31_Notax.drop(columns=["Account", "Measure", "Period", "Department"], inplace=True)
            # print(df_a31_Notax)

            df_a05_Notax = df.loc[(df["Account"] == "YW0205")
                                  & (df["Period"] == "Noperiod")
                                  & (df["Measure"] == "Nomeasure")
                                  & (df["Material"] == "Nomaterial")
                                  & (df["Department"] == "Operation")
                                  & (df["Tax"] == "Tax")]
            df_a05_Notax.drop(columns=["Account", "Measure", "Tax", "Material"], inplace=True)

            # 含税
            # print('------- 含税数据集 --------')
            df_a31_Tax = df.loc[(df["Account"] == "PL0102")
                                & (df["Measure"] == "Expenses")
                                & (df["Material"] == "Total")
                                & (df["Department"] == "Totaldepartment")
                                & (df["Tax"] == "Tax")]
            # df_a31_bg_Tax = df_a31_Tax.loc[(df["Scenario"] == "Budget")
            df_a31_bg_Tax = df_a31_Tax.loc[(df["Scenario"].isin(["Budget"]))
                                           & (df["Period"] == "TotalPeriod")]
            df_a31_other_Tax = df_a31_Tax.loc[(df["Scenario"].isin(["Actual", 'New']))]
            df_a31_Tax = pd.concat([df_a31_other_Tax, df_a31_bg_Tax], axis=0)
            df_a31_Tax.drop(columns=["Account", "Measure", "Period", "Department"], inplace=True)

            df_a05_Tax = df.loc[(df["Account"] == "YW0205")
                                & (df["Period"] == "Noperiod")
                                & (df["Measure"] == "Nomeasure")
                                & (df["Material"] == "Nomaterial")
                                & (df["Department"] == "Operation")
                                & (df["Tax"] == "Tax")]
            df_a05_Tax.drop(columns=["Account", "Measure", "Tax", "Material"], inplace=True)

            group = ["Year", "Entity", "Version", "Scenario", "Allocation", "Misc1", "Misc2"]
            # merge需要计算的数据集
            # print('----------- 合并需要计算的不含税数据集 + 含税数据集 -------------')
            df_Notax = pd.merge(df_a31_Notax, df_a05_Notax, how="outer", on=group)
            df_Tax = pd.merge(df_a31_Tax, df_a05_Tax, how="outer", on=group)
            # print(df_Notax)
            # print(df_Tax)

            if not df_Notax.empty:
                # print('----------- 不含税计算开始 --------------')
                for i in ["data_x", "data_y"]:
                    if i not in df_Notax.columns:
                        return
                # A66 = A31/A05
                # 计算相乘
                df_Notax.loc[:, "YW0405"] = df_Notax.apply(lambda x: x["data_x"] / x["data_y"]
                if pd.notnull(x["data_x"]) & pd.notnull(x["data_y"]) & (x["data_y"] != 0)
                else np.NaN, axis=1)
                df_Notax.drop(columns=["data_x", "data_y"], inplace=True)
                df_Notax["Measure"] = "Unit"
                df_Notax["Tax"] = "Notax"
                df_Notax["Material"] = "Total"
                df_Notax["Period"] = "Noperiod"
                # df_Notax["Department"] = "Operation"
                df_Notax["Department"] = "Totaldepartment"
                # 存数
                # print('---------- 存数-不含税 ----------')
                # print(df_Notax)
                self.cube.save_unpivot(df_Notax, unpivot_dim="Account")
            if not df_Tax.empty:
                # print('----------- 含税计算开始 --------------')
                for i in ["data_x", "data_y"]:
                    if i not in df_Tax.columns:
                        return
                # A66 = A31/A05
                # 计算相乘
                df_Tax.loc[:, "YW0405"] = df_Tax.apply(lambda x: x["data_x"] / x["data_y"]
                if pd.notnull(x["data_x"]) & pd.notnull(x["data_y"]) & (x["data_y"] != 0)
                else np.NaN,
                                                       axis=1)
                df_Tax.drop(columns=["data_x", "data_y"], inplace=True)
                df_Tax["Measure"] = "Unit"
                df_Tax["Tax"] = "Tax"
                df_Tax["Material"] = "Total"
                df_Tax["Period"] = "Noperiod"
                # df_Tax["Department"] = "Operation"
                df_Tax["Department"] = "Totaldepartment"
                # 存数
                # print('---------- 存数-含税 ----------')
                # print(df_Tax)
                self.cube.save_unpivot(df_Tax, unpivot_dim="Account")

            # print('---------- 计算吨水非薪酬函数结束 ----------')


def main(p1, p2):
    # 四期需求1-审核指标计算-前置操作2   计算经营毛利率   PL02    毛利率计算py只需传参year
    # 取Expenses写Unit    取Nomaterial写Nomaterial      条线清存Totaldepartment 取Operation + Equipment，存Totaldepartment
    # 毛利率计算
    begin = time.time()
    # 实例化
    g = Gross(p2)
    # 清数汇总
    g.delete_all()

    print('----------- 第一部分 经营毛利率计算 -----------')
    # 1.经营毛利率计算
    # 科目: 1.收入合计（污水收入+其他收入)  2.经营毛利（万元）
    # account = "A894;A35"
    account = "PL0101;PL01"
    scenario = "Budget;Actual"
    period = "Noperiod;TotalPeriod"
    # period = "Noperiod"
    department = "Totaldepartment"
    # department = p2["Department_wb1"]
    measure = "Expenses"
    # g.get_cube()
    g.gross_margin(account, scenario, measure, period, department)

    print('----------- 第二部分 吨水非薪酬计算 -----------')
    # 四期需求2-审核指标计算-前置操作1   计算吨水非薪酬付现成本（万元）
    # 取Expenses写Unit    取Nomaterial写Total

    # 2.吨水非薪酬付现成本计算
    # 总付现成本-吨水成本计算
    g.total_cash_outlay()

    # 调整 20250729 将该脚本计算置于配置表计算之前
    audit = time.time()
    from budget.Python.biz.calc.copy1_config_calc import main as main_audit
    main_audit(p1, p2)


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
