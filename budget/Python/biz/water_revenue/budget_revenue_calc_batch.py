# -*- coding: utf-8 -*-
# @Time : 2023/8/29 9:58
# @Author : LiYuXin
# @FileName: budget_revenue_calc_batch.py
# @Software: PyCharm
# @水价与收入脚本

import traceback
import time
from functools import reduce

import numpy as np
import pandas as pd

from deepfos.element.finmodel import FinancialCube
from deepfos.element.variable import Variable
from deepfos.element.dimension import Dimension

import asyncio
from deepfos.element.finmodel import AsyncFinancialCube
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)

class Revenue(object):
    # 水价与收入计算逻辑——批量entity
    def __init__(self, p2):
        # 获取变量
        variable = Variable(element_name="Variable")
        self.var = variable.get_value("Forcast")
        # 获取财务模型
        self.cube_bewg = FinancialCube("WS_cube", path="/01_Cube")
        # 有参数获取p2参数，当表单没有时取默认值
        self.fix = {
            "Version": "Y1",
            "Material": "Nomaterial",
            "Scenario": "Budget",
            "Department": "Operation",
            "Allocation": "Original",
            "Tax": "Tax",
            "Misc1": "Nomisc1",
            "Misc2": "Nomisc2",
        }
        # fix更新p2给fix
        self.fix = dict(self.fix, **p2)
        print(self.fix)
        del self.fix["sheetName"]
        del self.fix["sheetId"]
        del self.fix["elementName"]
        del self.fix["folderId"]
        self.measure = "Expenses"
        self.last_year = str(int(self.fix["Year"]) - 1)

    def df_query(self, **kwargs):
        fix_query = (
                "Account{%s}->Year{%s}->Scenario{%s}->Period{%s}->Measure{%s}->Entity{%s}->"
                "Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->Tax{%s}->Misc1{%s}->Misc1{%s}"
                % (
                    kwargs["account"],
                    kwargs["year"],
                    kwargs["scenario"],
                    kwargs["period"],
                    self.measure,
                    self.fix["Entity"],
                    self.fix["Version"],
                    self.fix["Material"],
                    self.fix["Department"],
                    self.fix["Allocation"],
                    self.fix["Tax"],
                    self.fix["Misc1"],
                    self.fix["Misc1"],
                )
        )
        df = self.cube_bewg.query(fix_query, compact=False, pivot_dim="Account")
        if not df.empty:
            account_list = kwargs["account"].split(";")
            for i in account_list:
                if i not in df.columns:
                    df[i] = np.NaN
        return df

    def del_cube(self):
        fix1_del = (
                "Account{%s}->Year{%s}->Scenario{%s}->Period{%s}->Entity{%s}->Measure{%s}->"
                "Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->Tax{%s}->Misc1{%s}->Misc2{%s}"
                % (
                    "YW0102;YW0106;YW0109;PL01010101;PL01010102",
                    self.fix["Year"],
                    "Budget",
                    "Remove(Base(TotalPeriod,0),Adjust);Noperiod",
                    self.fix["Entity"],
                    self.measure,
                    self.fix["Version"],
                    self.fix["Material"],
                    self.fix["Department"],
                    self.fix["Allocation"],
                    self.fix["Tax"],
                    self.fix["Misc1"],
                    self.fix["Misc2"],
                )
        )
        fix2_del = (
                "Account{%s}->Year{%s}->Scenario{%s}->Period{%s}->Entity{%s}->Measure{%s}->"
                "Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->Tax{%s}->Misc1{%s}->Misc2{%s}"
                % (
                    "YW0202;YW0101;YW0105;YW0107;YW0108;PL010103;PL01010103;PL01010201;PL01010202;PL010105",
                    self.fix["Year"],
                    "Budget",
                    "Noperiod",
                    self.fix["Entity"],
                    self.measure,
                    self.fix["Version"],
                    self.fix["Material"],
                    self.fix["Department"],
                    self.fix["Allocation"],
                    self.fix["Tax"],
                    self.fix["Misc1"],
                    self.fix["Misc2"],
                )
        )
        fix3_del = (
                "Account{%s}->Year{%s}->Scenario{%s}->Period{%s}->Entity{%s}->Measure{%s}->"
                "Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->Tax{%s}->Misc1{%s}->Misc2{%s}"
                % (
                    "YW0102;YW0106;YW0109;PL01010101;PL01010102",
                    self.last_year,
                    "Forecast",
                    "Base(Oct,0)",
                    self.fix["Entity"],
                    self.measure,
                    self.fix["Version"],
                    self.fix["Material"],
                    self.fix["Department"],
                    self.fix["Allocation"],
                    self.fix["Tax"],
                    self.fix["Misc1"],
                    self.fix["Misc2"],
                )
        )
        fix4_del = (
                "Account{%s}->Year{%s}->Scenario{%s}->Period{%s}->Entity{%s}->Measure{%s}->"
                "Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->Tax{%s}->Misc1{%s}->Misc2{%s}"
                % (
                    "YW0102;YW0106;YW0202;YW0101;YW0105;YW0107;YW0108;YW0109;PL01010101;PL01010102;PL010103;PL01010103;PL01010201;PL01010202;PL010105",
                    self.last_year,
                    "Actual",
                    "Noperiod",
                    self.fix["Entity"],
                    self.measure,
                    self.fix["Version"],
                    self.fix["Material"],
                    self.fix["Department"],
                    self.fix["Allocation"],
                    self.fix["Tax"],
                    self.fix["Misc1"],
                    self.fix["Misc2"],
                )
        )

        async def batch_delete():
            bewg_cube = AsyncFinancialCube("WS_cube")
            await asyncio.gather(
                bewg_cube.delete(expression=fix1_del),
                bewg_cube.delete(expression=fix2_del),
                bewg_cube.delete(expression=fix3_del),
                bewg_cube.delete(expression=fix4_del),
            )

        asyncio.run(batch_delete())

    def calc_revenue(self):
        # 取数汇总
        account = []
        year = []
        scenario = []
        period = []
        query_list = []
        # data_result[0],01部分
        account.append("YW0101;YW0202;YW0107")
        period.append("Remove(Base(TotalPeriod,0),Adjust)")
        scenario.append("Budget")
        year.append(self.fix["Year"])
        # data_result[1],01部分
        account.append("YW0101;YW0202;YW0107")
        period.append("Base(Oct,0)")
        scenario.append("Forecast")
        year.append(self.last_year)
        # data_result[2],02部分
        account.append("YW0102;YW0202;YW0106")
        period.append("Remove(Base(TotalPeriod,0),Adjust)")
        scenario.append("Actual")
        year.append(self.last_year)
        # data_result[3],03部分
        account.append("YW0105;YW0108")
        period.append("Remove(Base(TotalPeriod,0),Adjust)")
        scenario.append("Budget")
        year.append(self.fix["Year"])
        # data_result[4],03部分
        account.append("YW0105;YW0108")
        period.append("Remove(Base(TotalPeriod,0),Adjust)")
        scenario.append("Actual;Forecast")
        year.append(self.last_year)
        # data_result[5],05部分
        account.append("YW0109")
        period.append("Remove(Base(TotalPeriod,0),Adjust)")
        scenario.append("Actual")
        year.append(self.last_year)
        # data_result[6],02部分
        account.append("PL010103;PL01010103;PL01010201;PL01010202;PL010105")
        period.append("Remove(Base(TotalPeriod,0),Adjust)")
        scenario.append("Budget")
        year.append(self.fix["Year"])
        # data_result[7],02部分
        account.append("PL010103;PL01010103;PL01010201;PL01010202;PL010105")
        period.append("Oct")
        scenario.append("Forecast")
        year.append(self.last_year)
        # data_result[8],02部分
        account.append("PL010103;PL01010103;PL01010201;PL01010202;PL010105;PL01010101;PL01010102")
        period.append("Sepmtd")
        scenario.append("Actual")
        year.append(self.last_year)
        # data_result[9],02部分
        account.append("PL010103;PL01010103;PL01010201;PL01010202;PL010105;PL01010101;PL01010102")
        period.append("Oct")
        scenario.append("Actual")
        year.append(self.last_year)
        # len(account)==len(year)==len(scenario)==len(measure)==10
        for i in range(0, 10):
            fix_query = (
                    "Account{%s}->Year{%s}->Scenario{%s}->Period{%s}->Measure{%s}->Entity{%s}->"
                    "Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->Tax{%s}->Misc1{%s}->Misc1{%s}"
                    % (
                        account[i],
                        year[i],
                        scenario[i],
                        period[i],
                        self.measure,
                        self.fix["Entity"],
                        self.fix["Version"],
                        self.fix["Material"],
                        self.fix["Department"],
                        self.fix["Allocation"],
                        self.fix["Tax"],
                        self.fix["Misc1"],
                        self.fix["Misc1"],
                    )
            )
            query_list.append(fix_query)

        async def cube_query():
            bewg_cube = AsyncFinancialCube("WS_cube")
            results = await asyncio.gather(
                bewg_cube.query(expression=query_list[0], compact=False, pivot_dim="Account"),
                bewg_cube.query(expression=query_list[1], compact=False, pivot_dim="Account"),
                bewg_cube.query(expression=query_list[2], compact=False, pivot_dim="Account"),
                bewg_cube.query(expression=query_list[3], compact=False),
                bewg_cube.query(expression=query_list[4], compact=False),
                bewg_cube.query(expression=query_list[5], compact=False, pivot_dim="Account"),
                bewg_cube.query(expression=query_list[6], compact=False, pivot_dim="Account"),
                bewg_cube.query(expression=query_list[7], compact=False, pivot_dim="Account"),
                bewg_cube.query(expression=query_list[8], compact=False, pivot_dim="Account"),
                bewg_cube.query(expression=query_list[9], compact=False, pivot_dim="Account"),
            )
            return results

        data_result = asyncio.run(cube_query())

        for i in (list(range(0, 3)) + list(range(5, 10))):
            if not data_result[i].empty:
                account_list = account[i].split(";")
                for j in account_list:
                    if j not in data_result[i].columns:
                        data_result[i][j] = np.NaN

        # 01、计算合计实际处理水量、保底水量
        # return: YW0102,YW0106

        df_bg = data_result[0]
        df_fc = data_result[1]
        df_calc = pd.concat([df_bg, df_fc], axis=0)

        if not df_calc.empty:
            # df_a02 = df_calc[df_calc['Account'] == 'YW0202']
            # YW0102 = YW0101 * YW0202
            df_calc.loc[:, "YW0102"] = df_calc.apply(
                lambda x: x["YW0202"] * x["YW0101"]
                if pd.notnull(x["YW0202"]) & pd.notnull(x["YW0101"])
                else np.NaN,
                axis=1,
            )
            # YW0106 = YW0107 * YW0202
            df_calc.loc[:, "YW0106"] = df_calc.apply(
                lambda x: x["YW0202"] * x["YW0107"]
                if pd.notnull(x["YW0202"]) & pd.notnull(x["YW0107"])
                else np.NaN,
                axis=1,
            )
        else:
            for j in ["YW0101", 'YW0202', 'YW0107', "YW0102", "YW0106"]:
                if j not in df_calc.columns:
                    df_calc[j] = np.NaN
        df_YW0102_YW0105 = df_calc.copy(deep=True)
        df_YW0102_YW0105.drop(columns=["YW0202", "YW0101", "YW0107"], inplace=True)
        # 另存06要用到的数据
        df_bg_YW0106 = df_calc.loc[(df_calc["Scenario"] == "Budget")].drop(
            columns=["YW0202", "YW0101", "YW0107", "YW0102"]
        )
        print('df_bg_YW0106',df_bg_YW0106)
        df_fc_YW0106 = df_calc.loc[(df_calc["Scenario"] == "Forecast")].drop(
            columns=["YW0202", "YW0101", "YW0107", "YW0102"]
        )
        print('df_fc_YW0106', df_fc_YW0106)
        # 02、计算合计实际处理水量、保底水量、运行天数
        # return: YW0102,YW0106,YW0202 (Noperiod)

        df_bg = df_calc[df_calc["Scenario"] == "Budget"]
        df_fc = df_calc[df_calc["Scenario"] == "Forecast"]
        group = [
            "Year",
            "Version",
            "Entity",
            "Material",
            "Tax",
            "Allocation",
            "Department",
            "Measure",
            "Misc1",
            "Misc2",
        ]

        # 计算1-12月合计，存入Noperiod期间（Budget）
        if not df_bg.empty:
            df_bg = df_bg.groupby(group, as_index=False)["YW0102", "YW0106", "YW0202"].sum()
            df_bg["Period"] = "Noperiod"
            df_bg["Scenario"] = "Budget"

        # 计算1-12月合计，存入Noperiod期间（Actual）
        # 取Actual数据
        df_ac = data_result[2]
        # 根据变量的值分情况计算
        # self.var = "Actual"
        if self.var == "Actual":
            if not df_ac.empty:
                df_ac = df_ac.groupby(group, as_index=False)[
                    "YW0102", "YW0106", "YW0202"
                ].sum()
                df_ac["Period"] = "Noperiod"
                df_ac["Scenario"] = "Actual"
        elif self.var == "Forecast":
            df_ac = df_ac.loc[
                df_ac["Period"].isin(["1", "2", "3", "4", "5", "6", "7", "8", "9"])
            ]
            df_ac_fc = pd.concat([df_ac, df_fc], axis=0)
            if not df_ac_fc.empty:
                df_ac = df_ac_fc.groupby(group, as_index=False)[
                    "YW0102", "YW0106", "YW0202"
                ].sum()
                df_ac["Period"] = "Noperiod"
                df_ac["Scenario"] = "Actual"
        df_ac_bg = pd.concat([df_ac, df_bg], axis=0)
        # df_noperiod = df_ac_bg.copy(deep=True)

        # 03、计算日均实际处理水量、保底水价、日保底水量、超保底水价
        # return: YW0101, YW0105, YW0107, YW0108 (Noperiod)

        # 计算YW0101,YW0107
        if not df_ac_bg.empty:
            for i in ["YW0102", "YW0202", "YW0106"]:
                if i not in df_ac_bg.columns:
                    df_ac_bg[i] = np.NaN
            # YW0101=YW0102/YW0202
            df_ac_bg.loc[:, "YW0101"] = df_ac_bg.apply(
                lambda x: x["YW0102"] / x["YW0202"]
                if pd.notnull(x["YW0202"]) & pd.notnull(x["YW0102"]) & (x["YW0202"] != 0)
                else np.NaN,
                axis=1,
            )
            # YW0107=YW0106/YW0202
            df_ac_bg.loc[:, "YW0107"] = df_ac_bg.apply(
                lambda x: x["YW0106"] / x["YW0202"]
                if pd.notnull(x["YW0202"]) & pd.notnull(x["YW0106"]) & (x["YW0202"] != 0)
                else np.NaN,
                axis=1,
            )
        df_noperiod = df_ac_bg.copy(deep=True)

        # 计算YW0105,YW0108(1-12月平均值)
        df_bg = data_result[3]
        df_ac_fc = data_result[4]
        # 根据变量切分数据
        if self.var == "Forecast":
            df_ac = df_ac_fc.loc[
                (df_ac_fc["Scenario"] == "Actual")
                & (
                    df_ac_fc["Period"].isin(
                        ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
                    )
                )
                ]
            df_fc = df_ac_fc.loc[
                (df_ac_fc["Scenario"] == "Forecast")
                & (df_ac_fc["Period"].isin(["10", "11", "12"]))
                ]
            df_ac = pd.concat([df_ac, df_fc], axis=0)
            df_ac["Scenario"] = "Actual"
        elif self.var == "Actual":
            df_ac = df_ac_fc.loc[
                (df_ac_fc["Scenario"] == "Actual")
                & (
                    df_ac_fc["Period"].isin(
                        ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
                    )
                )
                ]
        df_ac_bg = pd.concat([df_ac, df_bg], axis=0)
        # 另存06要用到的数据
        df_bg_YW0105 = df_bg.loc[(df_bg["Account"] == "YW0105")]
        df_bg_YW0108 = df_bg.loc[(df_bg["Account"] == "YW0108")]
        df_fc_YW0105 = df_ac_fc.loc[
            (df_ac_fc["Scenario"] == "Forecast")
            & (df_ac_fc["Period"].isin(["10", "11", "12"]))
            & (df_ac_fc["Account"] == "YW0105")
            ]
        df_fc_YW0108 = df_ac_fc.loc[
            (df_ac_fc["Scenario"] == "Forecast")
            & (df_ac_fc["Period"].isin(["10", "11", "12"]))
            & (df_ac_fc["Account"] == "YW0108")
            ]
        # 计算不为空月份数量和月平均数
        group.append("Account")
        group.append("Scenario")
        if not df_ac_bg.empty:
            df_ac_bg["count"] = 1
            df_ac_bg = df_ac_bg.groupby(group, as_index=False)["count", "data"].sum()
            df_ac_bg.loc[:, "data"] = df_ac_bg.apply(
                lambda x: x["data"] / x["count"]
                if pd.notnull(x["count"]) & pd.notnull(x["data"]) & (x["count"] != 0)
                else np.NaN,
                axis=1,
            )
            df_ac_bg["Period"] = "Noperiod"
            del df_ac_bg["count"]
        df_noperiod_average = df_ac_bg.copy(deep=True)

        # 04、计算超保底水量
        # return: YW0109

        if not df_calc.empty:
            # 当 YW0106为空,YW0102不为空，YW0106=0
            df_calc.loc[:, "YW0106"] = df_calc.apply(
                lambda x: 0
                if pd.notnull(x["YW0102"]) & pd.isnull(x["YW0106"])
                else x["YW0106"],
                axis=1,
            )
            # IF(YW0102 > YW0106, YW0102 - YW0106, 0) 实际处理水量 > 保底水量，实际 - 保底，否则为0
            df_calc.loc[:, "YW0109"] = df_calc.apply(
                lambda x: x["YW0102"] - x["YW0106"] if x["YW0102"] > x["YW0106"] else 0,
                axis=1,
            )
        else:
            df_calc["YW0109"] = np.NaN
        df_calc.drop(
            columns=["YW0102", "YW0106", "YW0202", "YW0101", "YW0107"], inplace=True
        )

        df_YW0109 = df_calc.copy(deep=True)
        # 另存06要用到的数据
        df_bg_YW0109 = df_calc.loc[(df_calc["Scenario"] == "Budget")]
        df_fc_YW0109 = df_calc.loc[(df_calc["Scenario"] == "Forecast")]

        # 05、计算超保底水量
        # return: YW0109 (Noperiod)

        df_bg = df_calc[df_calc["Scenario"] == "Budget"]
        df_fc = df_calc[df_calc["Scenario"] == "Forecast"]
        group.remove("Scenario")
        group.remove("Account")
        # 计算1-12月合计，存入Noperiod期间（Budget）
        if not df_bg.empty:
            df_bg = df_bg.groupby(group, as_index=False)["YW0109"].sum()
            df_bg["Period"] = "Noperiod"
            df_bg["Scenario"] = "Budget"

        # 计算1-12月合计，存入Noperiod期间（Actual）
        # 取Actual数据
        df_ac = data_result[5]
        # 根据变量的值分情况计算
        # self.var = "Actual"
        if self.var == "Actual":
            if not df_ac.empty:
                df_ac = df_ac.groupby(group, as_index=False)["YW0109"].sum()
                df_ac["Period"] = "Noperiod"
                df_ac["Scenario"] = "Actual"
        elif self.var == "Forecast":
            df_ac = df_ac.loc[
                df_ac["Period"].isin(["1", "2", "3", "4", "5", "6", "7", "8", "9"])
            ]
            df_ac_fc = pd.concat([df_ac, df_fc], axis=0)
            if not df_ac_fc.empty:
                df_ac = df_ac_fc.groupby(group, as_index=False)["YW0109"].sum()
                df_ac["Period"] = "Noperiod"
                df_ac["Scenario"] = "Actual"
        df_ac_bg = pd.concat([df_ac, df_bg], axis=0)
        group.append("Scenario")
        group.append("Period")
        df_noperiod = pd.merge(df_noperiod, df_ac_bg, how="outer", on=group)

        # 06、计算保底收入、超保底收入
        # return: PL01010101, PL01010102

        # PL01010101 = YW0105 * YW0106 保底水价 * 保底水量
        df_bg_PL01010101 = pd.merge(df_bg_YW0105, df_bg_YW0106, how="inner", on=group)
        print('df_bg_PL01010101',df_bg_PL01010101)
        df_fc_PL01010101 = pd.merge(df_fc_YW0105, df_fc_YW0106, how="inner", on=group)
        print('df_fc_PL01010101', df_fc_PL01010101)
        df_PL01010101 = pd.concat([df_bg_PL01010101, df_fc_PL01010101], axis=0)
        if not df_PL01010101.empty:
            df_PL01010101.loc[:, "PL01010101"] = df_PL01010101.apply(
                lambda x: x["data"] * x["YW0106"]
                if pd.notnull(x["data"]) & pd.notnull(x["YW0106"])
                else np.NaN,
                axis=1,
            )
            df_PL01010101.drop(columns=["Account", "data", "YW0106"], inplace=True)
        else:
            df_PL01010101["PL01010101"] = np.NaN
            df_PL01010101.drop(columns=["Account", "data", "YW0106"], inplace=True)
        # PL01010102 = YW0108 * YW0109 超保底水价 * 超保底水量
        df_bg_PL01010102 = pd.merge(df_bg_YW0108, df_bg_YW0109, how="inner", on=group)
        df_fc_PL01010102 = pd.merge(df_fc_YW0108, df_fc_YW0109, how="inner", on=group)
        df_PL01010102 = pd.concat([df_bg_PL01010102, df_fc_PL01010102], axis=0)
        if not df_PL01010102.empty:
            df_PL01010102.loc[:, "PL01010102"] = df_PL01010102.apply(
                lambda x: x["data"] * x["YW0109"]
                if pd.notnull(x["data"]) & pd.notnull(x["YW0109"])
                else np.NaN,
                axis=1,
            )
            df_PL01010102.drop(columns=["Account", "data", "YW0109"], inplace=True)
        else:
            df_PL01010102["PL01010102"] = np.NaN
            df_PL01010102.drop(columns=["Account", "data", "YW0109"], inplace=True)
        df_PL01010101_PL01010102 = pd.merge(df_PL01010101, df_PL01010102, how="outer", on=group).copy(deep=True)

        # 07、计算保底收入、超保底收入、可用性服务费收入、其他收入、调价补以往年度收入、调保底水量补以往年度收入
        # return: PL01010101, PL01010102, PL010103, PL01010103, PL01010201, PL01010202, PL010105 (Noperiod)

        df_bg = data_result[6]
        df_fc = data_result[7]
        df_ac_sep = data_result[8]
        df_ac_oct = data_result[9]

        if not df_PL01010101_PL01010102.empty:
            df_bg = pd.merge(
                df_bg,
                df_PL01010101_PL01010102[df_PL01010101_PL01010102["Scenario"] == "Budget"],
                how="outer",
                on=group,
            )
        # 根据变量的值分情况计算
        if self.var == "Forecast":
            if not df_PL01010101_PL01010102.empty:
                df_fc = pd.merge(
                    df_fc,
                    df_PL01010101_PL01010102[df_PL01010101_PL01010102["Scenario"] == "Forecast"],
                    how="outer",
                    on=group,
                )
            df_ac = pd.concat([df_ac_sep, df_fc], axis=0)
            df_ac["Scenario"] = "Actual"
        elif self.var == "Actual":
            df_ac = pd.concat([df_ac_sep, df_ac_oct], axis=0)

        # 分组聚合，重置索引
        group.remove("Period")
        if not df_bg.empty:
            for i in ["PL01010101", "PL01010102", "PL010103", "PL01010103", "PL01010201", "PL01010202", "PL010105"]:
                if i not in df_bg.columns:
                    df_bg[i] = np.NaN
            df_bg = df_bg.groupby(group, as_index=False)[
                "PL010103", "PL01010103", "PL01010201", "PL01010202", "PL010105", "PL01010101", "PL01010102"
            ].sum()
            df_bg["Period"] = "Noperiod"
        if not df_ac.empty:
            for i in ["PL01010101", "PL01010102", "PL010103", "PL01010103", "PL01010201", "PL01010202", "PL010105"]:
                if i not in df_ac.columns:
                    df_ac[i] = np.NaN
            df_ac = df_ac.groupby(group, as_index=False)[
                "PL010103", "PL01010103", "PL01010201", "PL01010202", "PL010105", "PL01010101", "PL01010102"
            ].sum()
            df_ac["Period"] = "Noperiod"
        df_noperiod_other = pd.concat([df_bg, df_ac], axis=0)

        # 数据汇总并存入cube
        # df_YW0102_YW0105;df_YW0109;df_PL01010101_PL01010102;df_noperiod;df_noperiod_average;df_noperiod_other

        group.append("Period")
        df_insert_cube = reduce(
            lambda x, y: pd.merge(x, y, on=group, how="outer"),
            [df_YW0102_YW0105, df_YW0109, df_PL01010101_PL01010102],
        )
        df_noperiod_average = pd.pivot(
            df_noperiod_average, index=group, columns="Account", values="data"
        )
        df_noperiod = reduce(
            lambda x, y: pd.merge(x, y, on=group, how="outer"),
            [df_noperiod, df_noperiod_other, df_noperiod_average],
        )
        df_insert_cube = pd.concat([df_insert_cube, df_noperiod], axis=0)
        print('df_insert_cube',df_insert_cube)
        self.cube_bewg.save_unpivot(df_insert_cube, unpivot_dim="Account")

        return

    def calc_compare(self, p2):
        # 查询维度中父级节点
        entity_dim = Dimension("Entity")
        entity_parent = entity_dim.query(
            p2["Entity"], fields=["parent_name"], as_model=False
        )
        df_dim = pd.DataFrame(data=entity_parent)

        list_parent_name = df_dim["parent_name"].tolist()
        pare = ""
        for i in list_parent_name:
            pare += i
            pare += ";"
        # Python rfind()返回字符串最后一次出现的位置
        idx = pare.rfind(";")
        # 提取前一部分字符不替换，取后一部分字符进行替换
        # 这里用到了字符串切片的方式
        parent_name = pare[:idx] + str.replace(pare[idx:], ";", "")

        exp = (
                "Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->Tax{Tax}->Misc1{%s}->Misc2{%s}->Year{%s}->"
                "Account{YW0204;YW0106}->Scenario{Budget}->Entity{%s}->Measure{Nomeasure;Expenses}->Period{Noperiod}"
                % (
                    self.fix["Version"],
                    self.fix["Material"],
                    self.fix["Department"],
                    self.fix["Allocation"],
                    self.fix["Misc1"],
                    self.fix["Misc2"],
                    p2["Year"],
                    parent_name,
                )
        )
        # 模型中取数
        df = self.cube_bewg.query(expression=exp, compact=False)
        # df切片
        df_YW0105 = df.loc[
            (df["Account"] == "YW0106") & (df["Measure"] == "Expenses")
            ].rename(columns={"data": "YW0106"}, inplace=False)
        df_YW0204 = df.loc[
            (df["Account"] == "YW0204") & (df["Measure"] == "Nomeasure")
            ].rename(columns={"data": "YW0204"}, inplace=False)
        group = [
            "Year",
            "Version",
            "Entity",
            "Material",
            "Tax",
            "Allocation",
            "Department",
            "Misc1",
            "Misc2",
            "Period",
            "Scenario",
        ]
        df = pd.merge(df_YW0105, df_YW0204, how="inner", on=group)
        # 比较
        if not df.empty:
            df.loc[:, "ud13"] = df.apply(
                lambda x: "是" if float(df["YW0204"]) > float(df["YW0106"]) else "否",
                axis=1,
            )
            for i in df["Entity"]:
                ud13 = df.loc[(df["Entity"] == i), "ud13"]
                ud13 = ud13[0]
                entity_dim.update(i, ud13=ud13)
                print("已写入" + i + "维度ud13")
            entity_dim.save()
        else:
            print("存在YW0204或YW0106值为空，无法比较")

    def actual_tax(self):
        fix = ("Account{%s}->Year{%s}->Scenario{%s}->Period{%s}->Entity{%s}->Version{%s}->"
               "Measure{%s}->Material{%s}->Department{%s}->Allocation{%s}->Misc1{%s}->Misc2{%s}"
               % ("Base(PL0101,0);YW0105;YW0108",
                  self.last_year, "Actual", "1;2;3;4;5;6;7;8;9;10;11;12", self.fix["Entity"], self.fix["Version"],
                  self.measure, self.fix["Material"], self.fix["Department"], self.fix["Allocation"],
                  self.fix["Misc1"], self.fix["Misc2"]))
        # 清数fix
        fix_del = fix + "->Tax{Tax}"
        # 取数fix
        fix_query_notax = fix + "->Tax{Notax}"
        fix_query_taxrate = fix + "->Tax{Taxrate}"

        # 异步清数取数
        async def clear_get():
            bewg_cube = AsyncFinancialCube("WS_cube")
            results = await asyncio.gather(
                bewg_cube.delete(expression=fix_del),
                bewg_cube.query(expression=fix_query_notax, compact=False),
                bewg_cube.query(expression=fix_query_taxrate, compact=False),
            )
            return results

        data = asyncio.run(clear_get())

        if not data[1].empty:
            df = data[1].copy(deep=True)
            if not data[2].empty:
                df_taxrate = data[2].copy(deep=True)
                df_taxrate.drop(columns=["Tax"], inplace=True)
                group = ["Year", "Version", "Entity", "Period", "Scenario", "Account",
                         "Material", "Allocation", "Department", "Measure", "Misc1", "Misc2"]
                df = pd.merge(df, df_taxrate, how="left", on=group, suffixes=("", "_rate"))
                # 将未找到税率科目的税率设置为0
                df["data_rate"] = df["data_rate"].fillna(0)
                df['data'] = df['data'] * (1 + df['data_rate'])
                del df['data_rate']
            df["Tax"] = "Tax"
            # 存数
            self.cube_bewg.save(df)

    def actual_noperiod(self):
        Entity = 'Base(1,0)'
        del_fix = ("Account{%s}->Year{%s}->Scenario{%s}->Period{Noperiod}->Entity{%s}->Version{%s}->Tax{Tax}->"
               "Measure{%s}->Material{%s}->Department{%s}->Allocation{%s}->Misc1{%s}->Misc2{%s}"
               % ("PL010106;PL010107;PL010108;PL010109;PL010110;PL010111;PL010112;PL010113;PL010114;PL010115;PL010116",
                  self.last_year, "Actual", Entity, self.fix["Version"],
                  self.measure, self.fix["Material"], self.fix["Department"], self.fix["Allocation"],
                  self.fix["Misc1"], self.fix["Misc2"]))
        # bewg_cube = FinancialCube("WS_cube")
        self.cube_bewg.delete(expression=del_fix)
        fix = ("Account{%s}->Year{%s}->Scenario{%s}->Period{%s}->Entity{%s}->Version{%s}->Tax{Tax;Notax}->"
               "Measure{%s}->Material{%s}->Department{%s}->Allocation{%s}->Misc1{%s}->Misc2{%s}"
               % ("PL010106;PL010107;PL010108;PL010109;PL010110;PL010111;PL010112;PL010113;PL010114;PL010115;PL010116",
                  self.last_year, "Actual", "1;2;3;4;5;6;7;8;9;10;11;12",Entity, self.fix["Version"],
                  self.measure, self.fix["Material"], self.fix["Department"], self.fix["Allocation"],
                  self.fix["Misc1"], self.fix["Misc2"]))
        df = self.cube_bewg.query(expression=fix, compact=False)

        df["Period"] = "Noperiod"
        df = df.groupby(
            by=[
                "Account",
                "Year",
                "Scenario",
                "Measure",
                "Period",
                "Entity",
                "Version",
                "Material",
                "Department",
                "Allocation",
                "Tax",
                "Misc1",
                "Misc2",
            ],
            as_index=False,
        ).sum()
        self.cube_bewg.save(df)





    def YW0104_calc_deepcube(self):
        from deepcube.cube.cube import DeepCube
        from deepcube.cube import function as fn

        # 实例一个DeepCube对象，传参为cube元素名和path，如果cube元素名在应用中唯一，可以不传path
        cube = DeepCube('BEWG')
        # 从系统的财务模型中加载数据
        cube.init_data([
            cube.Entity[self.fix["Entity"]],
            cube.Version[self.fix["Version"]],
            cube.Measure[self.measure],
            cube.Material[self.fix["Material"]],
            cube.Department[self.fix["Department"]],
            cube.Allocation[self.fix["Allocation"]],
            cube.Tax[self.fix["Tax"]],
            cube.misc1[self.fix["Misc1"]],
            cube.misc2[self.fix["Misc2"]]
        ])
        # 确定一个背景scope范围
        cube.scope(
            cube.Account["YW0104"],
            cube.Entity[self.fix["Entity"]],
            cube.Version[self.fix["Version"]],
            cube.Measure[self.measure],
            cube.Material[self.fix["Material"]],
            cube.Department[self.fix["Department"]],
            cube.Allocation[self.fix["Allocation"]],
            cube.Tax[self.fix["Tax"]],
            cube.misc1[self.fix["Misc1"]],
            cube.misc2[self.fix["Misc2"]]
        )
        period = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]
        period_no = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "Noperiod"]
        period_fc = ["10", "11", "12"]
        period_ac = "Noperiod"
        period_ac_sum = ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
        # 清数
        clear_bg = {
            "Scenario": cube.Scenario["Budget"],
            "Year": cube.Year[self.fix["Year"]],
            "Period": cube.Period[period_no],
        }
        clear_fc = {
            "Scenario": cube.Scenario["Forecast"],
            "Year": cube.Year[self.last_year],
            "Period": cube.Period[period_fc],
        }
        clear_ac = {
            "Scenario": cube.Scenario["Actual"],
            "Year": cube.Year[self.last_year],
            "Period": cube.Period[period_ac],
        }
        cube.clear_data(clear_bg, clear_fc, clear_ac)
        # 计算
        cube.scope(
            cube.Account[["YW0102", "YW0106"]],
            cube.Scenario["Forecast"],
            cube.Year[self.last_year],
            cube.Period[period_fc],
        )
        cube.loc[cube.Account["YW0104"]] = fn.max(cube.loc[cube.Account[["YW0102", "YW0106"]]])
        cube.scope(
            cube.Scenario["Budget"],
            cube.Year[self.fix["Year"]],
            cube.Period[period]
        )
        cube.loc[cube.Account["YW0104"]] = fn.max(cube.loc[cube.Account[["YW0102", "YW0106"]]])
        # 将计算结果写入系统的财务模型中
        cube.submit_calc()
        # 计算
        cube.scope(
            cube.Account["YW0104"],
            cube.Scenario["Budget"],
            cube.Year[self.fix["Year"]],
        )
        cube.loc[cube.Period["Noperiod"]] = fn.sum(cube.loc[cube.Period[period]])
        if self.var == "Actual":
            cube.scope(
                cube.Scenario["Actual"],
                cube.Year[self.last_year],
            )
            cube.loc[cube.Period["Noperiod"]] = fn.sum(cube.loc[cube.Period[period]])
        else:
            cube.scope(
                cube.Scenario["Actual"],
                cube.Year[self.last_year],
            )
            cube.loc[cube.Period["Noperiod"]] = fn.sum(cube.loc[cube.Period[period_fc], cube.Scenario["Forecast"]]) \
                                                + fn.sum(cube.loc[cube.Period[period_ac_sum], cube.Scenario["Actual"]])
        # 将计算结果写入系统的财务模型中
        cube.submit_calc()

    def YW0104_calc(self):
        fix = ("Entity{%s}->Version{%s}->Misc1{%s}->Misc2{%s}->"
               "Measure{%s}->Material{%s}->Department{%s}->Allocation{%s}->Tax{%s}"
               % (self.fix["Entity"], self.fix["Version"], self.fix["Misc1"], self.fix["Misc2"],
                  self.measure, self.fix["Material"], self.fix["Department"], self.fix["Allocation"], self.fix["Tax"]))
        # 清数fix
        fix_del_bg = fix + "->Account{YW0104}->Year{%s}->Scenario{Budget}" \
                           "->Period{Remove(Base(TotalPeriod,0),Adjust);Noperiod}" \
                     % self.fix["Year"]
        fix_del_fc = fix + "->Account{YW0104}->Year{%s}->Scenario{Forecast}->Period{Base(Oct,0)}" % self.last_year
        fix_del_ac = fix + "->Account{YW0104}->Year{%s}->Scenario{Actual}->Period{Noperiod}" % self.last_year
        # 取数fix
        fix_query_bg = fix + "->Account{YW0102;YW0106}->Year{%s}->Scenario{Budget}" \
                             "->Period{Remove(Base(TotalPeriod,0),Adjust)}" \
                       % self.fix["Year"]
        fix_query_fc = fix + "->Account{YW0102;YW0106}->Year{%s}->Scenario{Forecast}->Period{Base(Oct,0)}" \
                       % self.last_year
        fix_query_ac = fix + "->Account{YW0104}->Year{%s}->Scenario{Actual}->Period{Remove(Base(TotalPeriod,0),Adjust)}" \
                       % self.last_year

        async def clear_get():
            # 异步清数取数
            bewg_cube = AsyncFinancialCube("WS_cube")
            results = await asyncio.gather(
                bewg_cube.delete(expression=fix_del_bg),
                bewg_cube.delete(expression=fix_del_fc),
                bewg_cube.delete(expression=fix_del_ac),
                bewg_cube.query(expression=fix_query_bg, compact=False, pivot_dim="Account"),
                bewg_cube.query(expression=fix_query_fc, compact=False, pivot_dim="Account"),
                bewg_cube.query(expression=fix_query_ac, compact=False, pivot_dim="Account"),
            )
            return results

        data = asyncio.run(clear_get())

        # 计算YW0104
        df = pd.concat([data[3], data[4]], axis=0)
        for i in ["YW0102", "YW0106"]:
            if i not in df.columns:
                df[i] = 0
        df["YW0102"] = df["YW0102"].fillna(0)
        df["YW0106"] = df["YW0106"].fillna(0)
        if not df.empty:
            df.loc[:, "YW0104"] = df.apply(lambda x: max(x["YW0102"], x["YW0106"]), axis=1)
        # df.loc[:, "YW0104"] = df.apply(lambda x: x["YW0102"] if x["YW0102"] >= x["YW0106"] else x["YW0106"], axis=1)
        df.drop(columns=["YW0102", "YW0106"], inplace=True)
        df_insert = df.copy(deep=True)

        # 计算YW0104合计Budget
        df_bg = df.loc[df["Scenario"] == 'Budget']
        group = ["Year", "Version", "Entity", "Scenario", "Tax",
                 "Allocation", "Material", "Department", "Measure", "Misc1", "Misc2"]
        if not df_bg.empty:
            df_bg = df_bg.groupby(group, as_index=False)["YW0104"].sum()
        df_bg["Period"] = "Noperiod"
        df_insert = df_insert.append(df_bg)

        # 计算YW0104合计Actual
        if self.var == "Actual":
            if not data[5].empty:
                df_ac = data[5].groupby(group, as_index=False)["YW0104"].sum()
                df_ac["Period"] = "Noperiod"
            else:
                df_ac = pd.DataFrame()
        else:
            df_fc = df.loc[df["Scenario"] == 'Forecast']
            df_fc["Scenario"] = "Actual"
            if not data[5].empty:
                df_ac = data[5].loc[data[5]["Period"].isin(["1", "2", "3", "4", "5", "6", "7", "8", "9"])]
                df_ac = pd.concat([df_fc, df_ac], axis=0)
            else:
                df_ac = df_fc
            if not df_ac.empty:
                df_ac = df_ac.groupby(group, as_index=False)["YW0104"].sum()
            df_ac["Period"] = "Noperiod"
        df_insert = df_insert.append(df_ac)

        # 删不含税数
        fix_del_act_Notax = "Account{YW0104}->Year{%s}->Scenario{Actual}->Period{Remove(Base(TotalPeriod,0),Adjust);Noperiod}" \
                            "->Version{Y1}->Tax{Notax}->Entity{%s}"\
                       % (self.last_year,self.fix["Entity"])
        fix_del_budget_Notax = "Account{YW0104}->Year{%s}->Scenario{Budget}->Period{Remove(Base(TotalPeriod,0),Adjust);Noperiod}" \
                            "->Version{Y1}->Tax{Notax}->Entity{%s}"\
                       % (self.fix["Year"],self.fix["Entity"])

        self.cube_bewg.delete(fix_del_act_Notax)
        self.cube_bewg.delete(fix_del_budget_Notax)

        # 复制一份，把 Tax 改成 Notax
        df_notax = df_insert.copy()
        df_notax['Tax'] = 'Notax'  # 改 Tax 列
        # df_notax['data'] = df_notax['data']  # 数值保持不变（可不写）

        # 上下合并
        df_insert = pd.concat([df_insert, df_notax], ignore_index=True)

        # 存数
        self.cube_bewg.save_unpivot(df_insert, unpivot_dim="Account")

def rename_wb1_keys(params):
    # Create a new dictionary to avoid modifying the original
    new_params = {}
    for key, value in params.items():
        # If key ends with '_wb1', remove the suffix; otherwise, keep the key as is
        new_key = key[:-4] if key.endswith('_wb1') else key
        new_key = new_key[:-4] if new_key.endswith('_wb2') else new_key
        new_params[new_key] = value
    return new_params

def main(p1, p2):
    p2 = rename_wb1_keys(p2)
    print(p2)
    try:
        begin = time.time()
        # 实例化
        revenue = Revenue(p2)
        # 新增实际数税率转换
        if p2["sheetId"] == "SHTc467b87b7841":
            revenue.actual_tax()
            # 计算新增收入科目的实际数汇总
            revenue.actual_noperiod()
            print("tax over")
            times = time.time() - begin
            print("实际数税率：", times)
        # 清数汇总
        revenue.del_cube()
        print("delete over")
        times = time.time() - begin
        print(times)
        # 计算收入逻辑
        revenue.calc_revenue()
        print("revenue over")
        times = time.time() - begin
        print(times)
        # 新增YW0104收费水量的计算
        revenue.YW0104_calc()
        times = time.time() - begin
        print(times)
        # 调用 water_price_revenue
        from budget.Python.biz.water_revenue.water_price_revenue import main as main_water
        if "Scenario" in revenue.fix:
            del revenue.fix["Scenario"]
        main_water(p1, revenue.fix)
        print("成功调用：water_price_revenue")
        times = time.time() - begin
        print("水价与收入：", times)
        # 新增审核指标计算，调用calc_audit_indicators
        # audit = time.time()
        # from budget.Python.biz.water_revenue.calc_audit_indicators import main as main_audit
        # main_audit(
        #     p1,
        #     revenue.fix,
        #     account_list=["PL0101"],
        #     year=p2["Year"],
        #     scenario_save="Budget",
        #     scenario_calcyear="Budget",
        #     scenario_lastyear="Actual",
        #     measure="Expenses",
        #     entity="IDescendant(1,0)",
        #     tax="Notax",
        # )
        # times = time.time() - audit
        # print("审核指标计算：", times)
        # 新增计算是否超保底运行(由于用户权限问题，改为前端完成)
        # from Python.biz.phaseII.newly.compare_save_dim import main as main_compare
        # main_compare(
        #     revenue.cube_bewg, revenue.fix, entity=p2["Entity"], year=p2["Year"]
        # )
        # 第七部分：计算毛利毛利率
        # gross = time.time()
        # from budget.Python.biz.phaseII.newly.gross_margin_calc import main as main_gross
        # d = {"Year": p2["Year"]}
        # revenue.fix.update(d)
        # main_gross(p1, p2)
        # times = time.time() - gross
        # print("毛利：", times)

    except Exception as e:
        traceback.print_exc()


# debug
if __name__ == "__main__":
    from common.__debug import para1

    p2 = {'elementName': 'Revenue', 'folderId': 'DIRacd99f1aefd0', 'sheetName': '水价与收入明细表', 'sheetId': 'SHT5d20722b555f49cbb3c6fb1ec054ab8e', 'Year_wb1': '2026', 'Entity_wb1': 'Y6120210005', 'Department_wb1': 'Operation', 'Tax_wb1': 'Tax', 'Version_wb2': 'Y1', 'Scenario_wb1': 'Actual'}


    main(para1, p2)