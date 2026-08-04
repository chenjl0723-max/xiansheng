#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    描述：污水二期 电费&污泥费

    开发： 陈 小

    日期： 2023/8/2 11:20

"""
import time

import pandas as pd
import numpy as np
import warnings
import os
import sys

top_path = os.path.abspath(os.path.join(__file__, "../../../.."))
sys.path.append(top_path)

warnings.filterwarnings("ignore")

from deepfos.element.variable import Variable
from common.commons import *


class EAS(object):
    def __init__(
            self,
    ):
        # cube 元素名
        self.cube = "BEWG"
        # fix 表达式
        self.fix = (
            "Account{%s}->Year{%s}->Scenario{%s}->"
            "Measure{%s}->Period{%s}->Entity{%s}->"
            "Version{%s}->Material{%s}->Department{%s}->"
            "Allocation{%s}->Tax{%s}->misc1{%s}->"
            "misc2{%s}"
        )

    def del_data(self, pov, last_year):
        del_fix = self.fix % (
            "A310103;A3101020203;A310105;A3101040102;A31010402;A31010202",
            last_year,
            "Forecast",
            "Expenses",
            "Base(Oct, 0)",
            pov["Entity"],
            pov["Version"],
            pov["Material"],
            pov["Department"],
            pov["Allocation"],
            pov["Tax"],
            pov["misc1"],
            pov["misc2"],
        )
        cube_.delete(cube_name=self.cube, expression=del_fix)
        del_fix = self.fix % (
            "A3101020203;A3101040102;A310103;A310105;"
            "A31010402;A31010201;A3101020201;A3101020202;"
            "A3101040101;A310104010201;A3101040201;A31010202",
            pov["Year"],
            "Budget",
            "Expenses",
            "Noperiod",
            pov["Entity"],
            pov["Version"],
            pov["Material"],
            pov["Department"],
            pov["Allocation"],
            pov["Tax"],
            pov["misc1"],
            pov["misc2"],
        )
        cube_.delete(cube_name=self.cube, expression=del_fix)
        del_fix = self.fix % (
            "A3101020203;A3101040102;A310103;A310105;"
            "A31010402;A31010201;A3101020201;A3101020202;"
            "A3101040101;A310104010201;A3101040201;A31010202",
            last_year,
            "Actual",
            "Expenses",
            "Noperiod",
            pov["Entity"],
            pov["Version"],
            pov["Material"],
            pov["Department"],
            pov["Allocation"],
            pov["Tax"],
            pov["misc1"],
            pov["misc2"],
        )
        cube_.delete(cube_name=self.cube, expression=del_fix)

        del_fix = self.fix % (
            "A310103;A3101020203;A310105;A3101040102;A31010402;A31010202",
            pov["Year"],
            "Budget",
            "Expenses",
            "Remove(Base(TotalPeriod,0),Adjust)",
            pov["Entity"],
            pov["Version"],
            pov["Material"],
            pov["Department"],
            pov["Allocation"],
            pov["Tax"],
            pov["misc1"],
            pov["misc2"],
        )
        cube_.delete(cube_name=self.cube, expression=del_fix)

        del_fix = self.fix % (
            "A310104010201;A3101040201;A3101020201",
            last_year,
            "Actual",
            "Expenses",
            "1;2;3;4;5;6;7;8;9",
            pov["Entity"],
            pov["Version"],
            pov["Material"],
            pov["Department"],
            pov["Allocation"],
            pov["Tax"],
            pov["misc1"],
            pov["misc2"],
        )
        cube_.delete(cube_name=self.cube, expression=del_fix)

    def _query_cube_data(self, pov, customer_pov, last_year=None):
        if last_year:
            pov["Year"] = last_year
        query_fix = self.fix % (
            customer_pov["Account"],
            pov["Year"],
            customer_pov["Scenario"],
            customer_pov["Measure"],
            customer_pov["Period"],
            pov["Entity"],
            pov["Version"],
            pov["Material"],
            pov["Department"],
            pov["Allocation"],
            pov["Tax"],
            pov["misc1"],
            pov["misc2"],
        )
        res_df = cube_.query_cube(
            cube_name=self.cube, fix=query_fix, pivot_dim="Account"
        )
        # 补 全列
        account_set = set(customer_pov["Account"].split(";"))
        diff_list = list(account_set.difference(res_df.columns))
        if diff_list:
            res_df[diff_list] = [0] * len(diff_list)
        return res_df

    def calc_budget_forecast(self, pov, year, scenario, period):
        # 获取 【基础生产数据】合计实际处理水量 湿泥产量
        basic_data_pov = {
            "Account": "A05;A1001;A1002",
            "Scenario": scenario,
            "Measure": "Nomeasure",
            "Period": period,
        }
        basic_data_df = self._query_cube_data(pov, basic_data_pov, year)
        # 获取计算数据
        calc_data_pov = {
            "Account": "A3101020201;A3101020203;A31010201;A31010202;A3101020202;A310104010201;A3101040201;A310104;A31010401",
            "Scenario": scenario,
            "Measure": "Expenses",
            "Period": period,
        }
        calc_data_df = self._query_cube_data(pov, calc_data_pov, year)
        if calc_data_df.empty:
            return
        # 关联 basic_data_df 和 calc_data_df
        # 除 Measu Account 其余全为关联依据
        del basic_data_df["Measure"]
        calc_basic_df = pd.merge(calc_data_df, basic_data_df, how="left").fillna(0)
        account_set = set(basic_data_pov["Account"].split(";"))
        diff_list = list(account_set.difference(calc_basic_df.columns))
        if diff_list:
            calc_basic_df[diff_list] = [0] * len(diff_list)
        # 电度电量：吨水电耗*【基础生产数据】合计实际处理水量
        calc_basic_df["A3101020203"] = (
                calc_basic_df["A3101020202"] * calc_basic_df["A05"]
        )
        # 电度电费=综合电价 * 电度电量
        calc_basic_df["A31010202"] = (
                calc_basic_df["A3101020201"] * calc_basic_df["A3101020203"]
        )
        # 吨水电费（元/吨）：（基本电费+电度电费）/【基础生产数据】合计实际处理水量
        calc_basic_df["A310103"] = (
                                           calc_basic_df["A31010201"] + calc_basic_df["A31010202"]
                                   ) / calc_basic_df["A05"]

        # 委外车辆运输：运输单价*【基础生产数据】湿泥产量
        calc_basic_df["A3101040102"] = calc_basic_df["A310104010201"] * (
                calc_basic_df["A1001"] + calc_basic_df["A1002"]
        ) / 10000
        # 污泥处置费：处置单价*【基础生产数据】湿泥产量
        calc_basic_df["A31010402"] = calc_basic_df["A3101040201"] * (
                calc_basic_df["A1001"] + calc_basic_df["A1002"]
        ) / 10000
        # 污泥处理费吨水费用：污泥处理费/【基础生产数据】合计实际处理水量
        calc_basic_df["A310105"] = (
                                           calc_basic_df["A31010402"]
                                           + calc_basic_df["A3101040102"]
                                           + calc_basic_df["A31010401"]
                                   ) / calc_basic_df["A05"]
        # 将 inf 替换为 0
        calc_basic_df = calc_basic_df.replace([np.inf, -np.inf], 0)
        calc_basic_df = calc_basic_df.fillna(0)
        # 存数
        # 剔除不需要存的列
        calc_basic_df.drop(
            columns=[
                "A05",
                "A1001",
                "A1002",
                "A31010201",
                "A3101020202",
                "A310104",
                "A310104010201",
                "A3101040201",
                "A3101020201",
                "A31010401",
            ],
            inplace=True,
        )
        cube_.pivot_data_to_cube(cube=self.cube, data=calc_basic_df, pivot="Account")

    def calc_actual(self, pov, last_year):
        # 获取 【基础生产数据】合计实际处理水量 湿泥产量
        basic_data_pov = {
            "Account": "A1001;A1002",
            "Scenario": "Actual",
            "Measure": "Nomeasure",
            "Period": "Remove(Base(TotalPeriod,0),Adjust)",
        }
        basic_data_df = self._query_cube_data(pov, basic_data_pov, last_year)
        # 获取计算数据
        calc_data_pov = {
            "Account": "A3101040102;A31010402;A31010202;A3101020203",
            "Scenario": "Actual",
            "Measure": "Expenses",
            "Period": "Remove(Base(TotalPeriod,0),Adjust)",
        }
        calc_data_df = self._query_cube_data(pov, calc_data_pov, last_year)
        if calc_data_df.empty:
            return
        # 关联 basic_data_df 和 calc_data_df
        # 除 Measu Account 其余全为关联依据
        del basic_data_df["Measure"]
        calc_basic_df = pd.merge(calc_data_df, basic_data_df, how="left").fillna(0)
        account_set = set(basic_data_pov["Account"].split(";"))
        diff_list = list(account_set.difference(calc_basic_df.columns))
        if diff_list:
            calc_basic_df[diff_list] = [0] * len(diff_list)
        # 运输单价（实际数）=委外车辆运输/【基础生产数据】湿泥产量
        calc_basic_df["A310104010201"] = calc_basic_df["A3101040102"] / (
                calc_basic_df["A1001"] + calc_basic_df["A1002"]
        ) * 10000
        # 处置单价（实际数）=污泥处置费/【基础生产数据】湿泥产量
        calc_basic_df["A3101040201"] = calc_basic_df["A31010402"] / (
                calc_basic_df["A1001"] + calc_basic_df["A1002"]
        ) * 10000
        # 综合电价=电度电费/电度电量
        calc_basic_df["A3101020201"] = (
                calc_basic_df["A31010202"] / calc_basic_df["A3101020203"]
        )
        # 将 inf 替换为 0
        calc_basic_df = calc_basic_df.replace([np.inf, -np.inf], 0)
        calc_basic_df = calc_basic_df.fillna(0)
        # 存数
        # 剔除不需要存的列
        calc_basic_df.drop(
            columns=[
                "A1001",
                "A1002",
                "A3101040102",
                "A31010402",
                "A31010202",
                "A3101020203",
            ],
            inplace=True,
        )
        cube_.pivot_data_to_cube(cube=self.cube, data=calc_basic_df, pivot="Account")

    def calc_fa_noperiod(self, pov, fc_var, last_year):
        calc_data_df = pd.DataFrame()
        basic_data_df = pd.DataFrame()
        basic_data_pov = {}
        if fc_var == "Forecast":
            # 获取 【基础生产数据】合计实际处理水量 湿泥产量
            basic_data_pov = {
                "Account": "A05;A1001;A1002",
                "Scenario": "Actual",
                "Measure": "Nomeasure",
                "Period": "Noperiod",
            }
            basic_data_df = self._query_cube_data(pov, basic_data_pov, last_year)
            # 获取计算数据
            calc_actual_data_pov = {
                "Account": "A31010201;A31010202;A3101020203;A3101020201;A3101040101;A3101040102;A31010402",
                "Scenario": "Actual",
                "Measure": "Expenses",
                "Period": "1;2;3;4;5;6;7;8;9",
            }
            calc_actual_data_df = self._query_cube_data(
                pov, calc_actual_data_pov, last_year
            )
            calc_forecast_data_pov = {
                "Account": "A31010201;A31010202;A3101020203;A3101020201;A3101040101;A3101040102;A31010402;A31010401",
                "Scenario": "Forecast",
                "Measure": "Expenses",
                "Period": "10;11;12",
            }
            calc_Forecast_data_df = self._query_cube_data(
                pov, calc_forecast_data_pov, last_year
            )
            calc_data_df = pd.concat([calc_actual_data_df, calc_Forecast_data_df])
        elif fc_var == "Actual":
            # 获取 【基础生产数据】合计实际处理水量 湿泥产量
            basic_data_pov = {
                "Account": "A05;A1001;A1002",
                "Scenario": "Actual",
                "Measure": "Nomeasure",
                "Period": "Noperiod",
            }
            basic_data_df = self._query_cube_data(pov, basic_data_pov, last_year)
            # 获取计算数据
            calc_data_pov = {
                "Account": "A31010201;A31010202;A3101020203;A3101020201;A3101040101;A3101040102;A31010402;A31010401",
                "Scenario": "Actual",
                "Measure": "Expenses",
                "Period": "1;2;3;4;5;6;7;8;9;10;11;12",
            }
            calc_data_df = self._query_cube_data(pov, calc_data_pov, last_year)
        if calc_data_df.empty:
            return
        # 关联 basic_data_df 和 calc_data_df
        # 除 Measu Account period scenario 其余全为关联依据
        del basic_data_df["Measure"]
        del basic_data_df["Period"]
        del basic_data_df["Scenario"]
        calc_basic_df = pd.merge(calc_data_df, basic_data_df, how="left").fillna(0)
        account_set = set(basic_data_pov["Account"].split(";"))
        diff_list = list(account_set.difference(calc_basic_df.columns))
        if diff_list:
            calc_basic_df[diff_list] = [0] * len(diff_list)
        # 吨水电费（元/吨）：（基本电费+电度电费）/【基础生产数据】合计实际处理水量
        calc_basic_df["A310103"] = (
                                           calc_basic_df["A31010201"] + calc_basic_df["A31010202"]
                                   ) / calc_basic_df["A05"]
        # 吨水电耗:电度电量/【基础生产数据】合计实际处理水量
        calc_basic_df["A3101020202"] = (
                calc_basic_df["A3101020203"] / calc_basic_df["A05"]
        )
        # 运输单价（实际数）=委外车辆运输/【基础生产数据】湿泥产量
        calc_basic_df["A310104010201"] = calc_basic_df["A3101040102"] / (
                calc_basic_df["A1001"] + calc_basic_df["A1002"]
        )
        # 处置单价（实际数）=污泥处置费 /【基础生产数据】湿泥产量
        calc_basic_df["A3101040201"] = calc_basic_df["A31010402"] / (
                calc_basic_df["A1001"] + calc_basic_df["A1002"]
        )
        # 污泥处理费吨水费用：污泥处理费 /【基础生产数据】合计实际处理水量
        calc_basic_df["A310105"] = (
                                           calc_basic_df["A31010402"] + calc_basic_df["A31010401"]
                                   ) / calc_basic_df["A05"]
        # 将 inf 替换为 0
        calc_basic_df = calc_basic_df.replace([np.inf, -np.inf], 0)
        calc_basic_df = calc_basic_df.fillna(0)
        # 存数
        # 剔除不需要存的列
        calc_basic_df.drop(
            columns=[
                "A05",
                "A1001",
                "A1002",
                "A31010401",
            ],
            inplace=True,
        )
        # 汇总求和
        calc_basic_df["Period"] = "Noperiod"
        calc_basic_df["Scenario"] = "Actual"
        calc_basic_df = calc_basic_df.groupby(
            by=[
                "Year",
                "Scenario",
                "Period",
                "Measure",
                "Entity",
                "Version",
                "Material",
                "Department",
                "Allocation",
                "Tax",
                "misc1",
                "misc2",
            ],
            as_index=False,
        ).sum()
        # 综合电价
        calc_basic_df["A3101020201"] = (
                calc_basic_df["A31010202"] / calc_basic_df["A3101020203"]
        )
        # 将 inf 替换为 0
        calc_basic_df = calc_basic_df.replace([np.inf, -np.inf], 0)
        calc_basic_df = calc_basic_df.fillna(0)
        cube_.pivot_data_to_cube(cube=self.cube, data=calc_basic_df, pivot="Account")

    def calc_ac_noperiod(self, pov):
        # 获取 【基础生产数据】合计实际处理水量 湿泥产量
        basic_data_pov = {
            "Account": "A05;A1001;A1002",
            "Scenario": "Budget",
            "Measure": "Nomeasure",
            "Period": "Noperiod",
        }
        basic_data_df = self._query_cube_data(pov, basic_data_pov)
        # 获取计算数据
        calc_data_pov = {
            "Account": "A31010201;A31010202;A3101020203;A3101020201;A3101040101;A3101040102;A31010402;A31010401",
            "Scenario": "Budget",
            "Measure": "Expenses",
            "Period": "1;2;3;4;5;6;7;8;9;10;11;12",
        }
        calc_data_df = self._query_cube_data(pov, calc_data_pov)
        if calc_data_df.empty:
            return
        # 关联 basic_data_df 和 calc_data_df
        # 除 Measu Account period 其余全为关联依据
        del basic_data_df["Measure"]
        del basic_data_df["Period"]
        # del basic_data_df["Account"]
        calc_basic_df = pd.merge(calc_data_df, basic_data_df, how="left").fillna(0)
        account_set = set(basic_data_pov["Account"].split(";"))
        diff_list = list(account_set.difference(calc_basic_df.columns))
        if diff_list:
            calc_basic_df[diff_list] = [0] * len(diff_list)
        # 吨水电费（元/吨）：（基本电费+电度电费）/【基础生产数据】合计实际处理水量
        calc_basic_df["A310103"] = (
                                           calc_basic_df["A31010201"] + calc_basic_df["A31010202"]
                                   ) / calc_basic_df["A05"]
        # 吨水电耗:电度电量/【基础生产数据】合计实际处理水量
        calc_basic_df["A3101020202"] = (
                calc_basic_df["A3101020203"] / calc_basic_df["A05"]
        )
        # 运输单价（实际数）=委外车辆运输/【基础生产数据】湿泥产量
        calc_basic_df["A310104010201"] = calc_basic_df["A3101040102"] / (
                calc_basic_df["A1001"] + calc_basic_df["A1002"]
        )
        # 处置单价（实际数）=污泥处置费 /【基础生产数据】湿泥产量
        calc_basic_df["A3101040201"] = calc_basic_df["A31010402"] / (
                calc_basic_df["A1001"] + calc_basic_df["A1002"]
        )
        # 污泥处理费吨水费用：污泥处理费 /【基础生产数据】合计实际处理水量
        calc_basic_df["A310105"] = (
                                           calc_basic_df["A31010402"] + calc_basic_df["A31010401"]
                                   ) / calc_basic_df["A05"]
        # 将 inf 替换为 0
        calc_basic_df = calc_basic_df.replace([np.inf, -np.inf], 0)
        calc_basic_df = calc_basic_df.fillna(0)
        # 存数
        # 剔除不需要存的列
        calc_basic_df.drop(
            columns=[
                "A05",
                "A1001",
                "A1002",
                "A31010401",
            ],
            inplace=True,
        )
        # 汇总求和
        calc_basic_df["Period"] = "Noperiod"
        calc_basic_df = calc_basic_df.groupby(
            by=[
                "Year",
                "Scenario",
                "Period",
                "Measure",
                "Entity",
                "Version",
                "Material",
                "Department",
                "Allocation",
                "Tax",
                "misc1",
                "misc2",
            ],
            as_index=False,
        ).sum()
        # 综合电价
        calc_basic_df["A3101020201"] = (
                calc_basic_df["A31010202"] / calc_basic_df["A3101020203"]
        )
        cube_.pivot_data_to_cube(cube=self.cube, data=calc_basic_df, pivot="Account")

    def calc_notax(self, pov, year, scenario, period):
        # 获取 税率
        fix = self.fix % (
            "Base(A310102,0);Base(A310104,0)",
            year,
            scenario,
            "Expenses",
            period,
            pov["Entity"],
            pov["Version"],
            pov["Material"],
            pov["Department"],
            pov["Allocation"],
            "Taxrate",
            pov["misc1"],
            pov["misc2"],
        )
        tax_rate_df = cube_.query_cube(cube_name=self.cube, fix=fix)
        if scenario == "Actual" and period == "Base(Oct,0)":
            scenario = "Forecast"
        # 清除数据
        del_fix = self.fix % (
            "Base(A310102,0);Base(A310104,0)",
            year,
            scenario,
            "Expenses",
            period,
            pov["Entity"],
            pov["Version"],
            pov["Material"],
            pov["Department"],
            pov["Allocation"],
            "Notax",
            pov["misc1"],
            pov["misc2"],
        )
        cube_.delete(cube_name=self.cube, expression=del_fix)
        del tax_rate_df["Tax"]
        del tax_rate_df["Scenario"]
        # 给 data 重命名 taxrate
        tax_rate_df = tax_rate_df.rename(columns={"data": "taxrate"})
        # 获取含税金额
        fix = self.fix % (
            "Base(A310102,0);Base(A310104,0)",
            year,
            scenario,
            "Expenses",
            period,
            pov["Entity"],
            pov["Version"],
            pov["Material"],
            pov["Department"],
            pov["Allocation"],
            "Tax",
            pov["misc1"],
            pov["misc2"],
        )
        tax_amount_df = cube_.query_cube(cube_name=self.cube, fix=fix)

        rate_amount_df = pd.merge(tax_amount_df, tax_rate_df, how="left").fillna(0)
        rate_amount_df["data"] = rate_amount_df["data"] / (
                1 + rate_amount_df["taxrate"]
        )
        del rate_amount_df["taxrate"]
        rate_amount_df["Tax"] = "Notax"
        # 将 inf 替换为 0
        rate_amount_df = rate_amount_df.replace([np.inf, -np.inf], 0)
        rate_amount_df = rate_amount_df.fillna(0)
        # del_fix = self.fix % (
        #     "Base(A310102,0);Base(A310104,0)",
        #     pov["Year"],
        #     "Forecast",
        #     "Expenses",
        #     "Base(Oct,0)",
        #     pov["Entity"],
        #     pov["Version"],
        #     pov["Material"],
        #     pov["Department"],
        #     pov["Allocation"],
        #     "Notax",
        #     pov["misc1"],
        #     pov["misc2"],
        # )
        cube_.data_to_cube(cube=self.cube, del_fix=del_fix, data=rate_amount_df)

    def calc_tax_actual(self, pov, year, scenario, period):
        # 获取 税率
        fix = self.fix % (
            "Base(A310102,0);Base(A310104,0)",
            year,
            scenario,
            "Expenses",
            period,
            pov["Entity"],
            pov["Version"],
            pov["Material"],
            pov["Department"],
            pov["Allocation"],
            "Taxrate",
            pov["misc1"],
            pov["misc2"],
        )
        tax_rate_df = cube_.query_cube(cube_name=self.cube, fix=fix)
        # 清除数据
        del_fix = self.fix % (
            "Base(A310102,0);Base(A310104,0)",
            year,
            scenario,
            "Expenses",
            period,
            pov["Entity"],
            pov["Version"],
            pov["Material"],
            pov["Department"],
            pov["Allocation"],
            "Tax",
            pov["misc1"],
            pov["misc2"],
        )
        # cube_.delete(cube_name=self.cube, expression=del_fix)
        del tax_rate_df["Tax"]
        del tax_rate_df["Scenario"]
        # 给 data 重命名 taxrate
        tax_rate_df = tax_rate_df.rename(columns={"data": "taxrate"})
        # 获取不含税金额
        fix = self.fix % (
            "Base(A310102,0);Base(A310104,0)",
            year,
            scenario,
            "Expenses",
            period,
            pov["Entity"],
            pov["Version"],
            pov["Material"],
            pov["Department"],
            pov["Allocation"],
            "Notax",
            pov["misc1"],
            pov["misc2"],
        )
        tax_amount_df = cube_.query_cube(cube_name=self.cube, fix=fix)

        rate_amount_df = pd.merge(tax_amount_df, tax_rate_df, how="left").fillna(0)
        rate_amount_df["data"] = rate_amount_df["data"] * (
                1 + rate_amount_df["taxrate"]
        )
        del rate_amount_df["taxrate"]
        rate_amount_df["Tax"] = "Tax"
        # 将 inf 替换为 0
        rate_amount_df = rate_amount_df.replace([np.inf, -np.inf], 0)
        rate_amount_df = rate_amount_df.fillna(0)
        cube_.data_to_cube(cube=self.cube, del_fix=del_fix, data=rate_amount_df)

    def calc_audit_dsdf_dsfy(self, pov, scenario, year):
        pov["Entity"] = "IDescendant(1,0)"
        # 删除数据
        del_fix = self.fix % (
            "A310103;A310105;A3101020202",
            year,
            scenario,
            "Unit",
            "Noperiod",
            "IDescendant(1,0)",
            pov["Version"],
            pov["Material"],
            pov["Department"],
            pov["Allocation"],
            "Notax",
            pov["misc1"],
            pov["misc2"],
        )
        cube_.delete(cube_name=self.cube, expression=del_fix)
        if year:
            pov["Year"] = year
        # 获取 a05
        a05_pov = {
            "Account": "A05",
            "Scenario": scenario,
            "Measure": "Nomeasure",
            "Period": "Noperiod",
        }
        pov["Tax"] = "Tax"
        a05_df = self._query_cube_data(pov, a05_pov, year)
        del a05_df["Measure"]
        del a05_df["Tax"]
        # 获取 计算数据
        calc_pov = {
            "Account": "A31010201;A31010202;A310104",
            "Scenario": scenario,
            "Measure": "Expenses",
            "Period": "Noperiod",
        }
        pov["Tax"] = "Notax"
        calc_df = self._query_cube_data(pov, calc_pov, year)

        calc_tax_pov = {
            "Account": "A3101020203",
            "Scenario": scenario,
            "Measure": "Expenses",
            "Period": "Noperiod",
        }
        pov["Tax"] = "Tax"
        calc_tax_df = self._query_cube_data(pov, calc_tax_pov, year)
        calc_tax_df['Tax'] = "Notax"

        calc_df = pd.merge(calc_df, calc_tax_df, how='outer')

        a05_calc_df = pd.merge(calc_df, a05_df, how="left").fillna(0)
        if a05_calc_df.empty:
            return
        a05_calc_df["Measure"] = "Unit"
        account_set = set(calc_pov["Account"].split(";"))
        diff_list = list(account_set.difference(a05_calc_df.columns))
        if diff_list:
            a05_calc_df[diff_list] = [0] * len(diff_list)
        # 吨水电费（元/吨）：（基本电费+电度电费）/【基础生产数据】合计实际处理水量
        a05_calc_df["A310103"] = (
                                         a05_calc_df["A31010201"] + a05_calc_df["A31010202"]
                                 ) / a05_calc_df["A05"]
        # 污泥处理费吨水费用：污泥处理费/【基础生产数据】合计实际处理水量
        a05_calc_df["A310105"] = a05_calc_df["A310104"] / a05_calc_df["A05"]
        # 吨水电耗:电度电量/【基础生产数据】合计实际处理水量
        a05_calc_df["A3101020202"] = a05_calc_df["A3101020203"] / a05_calc_df["A05"]
        # 将 inf 替换为 0
        a05_calc_df = a05_calc_df.replace([np.inf, -np.inf], 0)
        a05_calc_df = a05_calc_df.fillna(0)
        # 存数
        # 剔除不需要存的列
        a05_calc_df.drop(
            columns=["A05", "A31010201", "A31010202", "A310104", "A3101020203"],
            inplace=True,
        )
        cube_.pivot_data_to_cube(cube=self.cube, data=a05_calc_df, pivot="Account")

    def calc_noperiod_sum(self, pov, year, scenario, fc_var):
        # 删除
        del_fix = self.fix % (
            "Base(A310102,0);Base(A310104,0)",
            year,
            scenario,
            "Expenses",
            "Noperiod",
            pov["Entity"],
            pov["Version"],
            pov["Material"],
            pov["Department"],
            pov["Allocation"],
            "Notax",
            pov["misc1"],
            pov["misc2"],
        )
        cube_.delete(cube_name=self.cube, expression=del_fix)
        if fc_var == "Forecast":
            forecast_fix = self.fix % (
                "Base(A310102,0);Base(A310104,0)",
                year,
                scenario,
                "Expenses",
                "1;2;3;4;5;6;7;8;9",
                pov["Entity"],
                pov["Version"],
                pov["Material"],
                pov["Department"],
                pov["Allocation"],
                "Notax",
                pov["misc1"],
                pov["misc2"],
            )
            forecast_data = cube_.query_cube(cube_name=self.cube, fix=forecast_fix)
            actual_fix = self.fix % (
                "Base(A310102,0);Base(A310104,0)",
                year,
                "Forecast",
                "Expenses",
                "10;11;12",
                pov["Entity"],
                pov["Version"],
                pov["Material"],
                pov["Department"],
                pov["Allocation"],
                "Notax",
                pov["misc1"],
                pov["misc2"],
            )
            actual_data = cube_.query_cube(cube_name=self.cube, fix=actual_fix)
            df = pd.concat([forecast_data, actual_data])
            df["Scenario"] = "Actual"
        else:
            actual_fix = self.fix % (
                "Base(A310102,0);Base(A310104,0)",
                year,
                scenario,
                "Expenses",
                "1;2;3;4;5;6;7;8;9;10;11;12",
                pov["Entity"],
                pov["Version"],
                pov["Material"],
                pov["Department"],
                pov["Allocation"],
                "Notax",
                pov["misc1"],
                pov["misc2"],
            )
            df = cube_.query_cube(cube_name=self.cube, fix=actual_fix)
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
                "misc1",
                "misc2",
            ],
            as_index=False,
        ).sum()
        df = df.rename(
            columns={
                "misc1": "Misc1",
                "misc2": "Misc2",
            }
        )
        cube_.save_cube(cube_name=self.cube, df=df)


def main(p1, p2):
    begin = time.time()
    p2["Tax"] = "Tax"
    # 年份减一
    year = p2["Year"]
    last_year = str(int(p2["Year"]) - 1)

    # 获取变量
    var = Variable("Variable")
    fc_var = var.get_value("Forcast")

    es = EAS()
    # 1、先按照下列条件范围执行数据删除
    es.del_data(p2, last_year)
    # 4、Actual税率转换
    es.calc_tax_actual(pov=p2, year=last_year, scenario="Actual", period="1;2;3;4;5;6;7;8;9;10;11;12")
    # 2、计算1-12月预算数&预测数&实际数：
    es.calc_budget_forecast(
        pov=p2, year=last_year, scenario="Forecast", period="Base(Oct,0)"
    )
    p2["Year"] = year
    es.calc_budget_forecast(p2, year, "Budget", "Remove(Base(TotalPeriod,0),Adjust)")
    es.calc_actual(p2, last_year)
    p2["Year"] = year
    # 3、计算全年Noperiod（按顺序执行）
    es.calc_fa_noperiod(p2, fc_var, last_year)
    p2["Year"] = year
    es.calc_ac_noperiod(p2)
    # 4、税率转换：
    es.calc_notax(pov=p2, year=last_year, scenario="Actual", period="Base(Oct,0)")
    es.calc_notax(
        pov=p2, year=year, scenario="Budget", period="1;2;3;4;5;6;7;8;9;10;11;12"
    )
    es.calc_notax(pov=p2, year=last_year, scenario="New", period="Noperiod")
    # es.calc_notax(pov=p2, year=last_year, scenario="Actual", period="1;2;3;4;5;6;7;8;9;10;11;12")
    # 挪到1、删数后面了
    # es.calc_tax_actual(pov=p2, year=last_year, scenario="Actual", period="1;2;3;4;5;6;7;8;9;10;11;12")
    # noperiod 不含税 汇总
    es.calc_noperiod_sum(pov=p2, year=last_year, scenario="Actual", fc_var=fc_var)
    es.calc_noperiod_sum(pov=p2, year=year, scenario="Budget", fc_var="Actual")
    print("电费：", time.time() - begin)

    audit = time.time()
    from budget.Python.biz.phaseII.newly.indicators_electricity import main as main_audit
    main_audit(p1, p2)
    print("审核：", time.time() - audit)
    # 计算毛利毛利率
    if p2["sheetName"] != "串行":
        gross = time.time()
        from budget.Python.biz.phaseII.newly.gross_margin_calc import main as main_gross
        main_gross(p1, p2)
        print("毛利：", time.time() - gross)


if __name__ == "__main__":
    try:
        from common._debug import para1
    except BaseException:
        pass

    para2 = {'Year': '2024', 'Entity': 'XN23004_01', 'Version': 'Y1', 'Material': 'Nomaterial',
             'Allocation': 'Original', 'Tax': 'Tax', 'Department': 'Operation', 'misc1': 'Nomisc1', 'misc2': 'Nomisc2',
             'sheetName': '电费&污泥费', 'sheetId': 'SHT2dee513bd945', 'elementName': 'Electricity',
             'folderId': 'DIRfd5a95b6f89c'}

    main(para1, para2)
