#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    描述：污水二期 电费&污泥费

    开发： 陈 小

    日期： 2023/8/2 11:20

"""
import time
from deepfos.element.finmodel import FinancialCube, AsyncFinancialCube
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

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)


class EAS(object):
    def __init__(
            self,
    ):
        # cube 元素名
        self.cube = "WS_cube"
        # fix 表达式
        self.fix = (
            "Account{%s}->Year{%s}->Scenario{%s}->"
            "Measure{%s}->Period{%s}->Entity{%s}->"
            "Version{%s}->Material{%s}->Department{%s}->"
            "Allocation{%s}->Tax{%s}->Misc1{%s}->"
            "Misc2{%s}"
        )

    def _query_cube_data(self, pov, customer_pov, year):
        """Query data from cube with specified dimensions."""
        query_fix = self.fix % (
            customer_pov["Account"],
            year,
            customer_pov["Scenario"],
            customer_pov["Measure"],
            customer_pov["Period"],
            pov["Entity"],
            pov["Version"],
            pov["Material"],
            pov["Department"],
            pov["Allocation"],
            customer_pov["Tax"],
            pov["Misc1"],
            pov["Misc2"],
        )
        try:
            res_df = cube_.query_cube(cube_name=self.cube, fix=query_fix, pivot_dim="Account")
            account_set = set(customer_pov["Account"].split(";"))
            diff_list = list(account_set.difference(res_df.columns))
            if diff_list:
                res_df[diff_list] = 0
            # logger.info(
            #     f"Queried data for {customer_pov['Account']} ({customer_pov['Tax']}, {customer_pov['Scenario']}, {year}):\n{res_df}")
            return res_df
        except Exception as e:
            print(e)
            # logger.error(f"Error querying cube for {query_fix}: {e}")
            return pd.DataFrame()

    def calc_notax(self, pov, year, scenario, period):
        Account = "Base(PL010202,0);Base(PL010203,0)"
        # 获取 税率
        fix = self.fix % (
            Account,
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
            pov["Misc1"],
            pov["Misc2"],
        )
        tax_rate_df = cube_.query_cube(cube_name=self.cube, fix=fix)
        print('tax_rate_df',tax_rate_df)
        if scenario == "Actual" and period == "Base(Oct,0)":
            scenario = "Forecast"
        if scenario == "Actual" and period == "1;2;3;4;5;6;7;8;9;10;11;12":
            # Account = "PL0102020202;PL0102030102;PL01020302"
            Account = "PL0102020202;PL0102030102;PL01020302"

        # 清除数据
        del_fix = self.fix % (
            Account,
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
            pov["Misc1"],
            pov["Misc2"],
        )
        # cube_.delete(cube_name=self.cube, expression=del_fix)
        del tax_rate_df["Tax"]
        del tax_rate_df["Scenario"]
        # 给 data 重命名 taxrate
        tax_rate_df = tax_rate_df.rename(columns={"data": "taxrate"})
        # 获取含税金额
        fix = self.fix % (
            Account,
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
            pov["Misc1"],
            pov["Misc2"],
        )
        tax_amount_df = cube_.query_cube(cube_name=self.cube, fix=fix)
        # print('tax_amount_df', tax_amount_df)

        rate_amount_df = pd.merge(tax_amount_df, tax_rate_df, how="left").fillna(0)
        rate_amount_df["data"] = rate_amount_df["data"] / (
                1 + rate_amount_df["taxrate"]
        )
        # print('rate_amount_df', rate_amount_df)
        del rate_amount_df["taxrate"]
        rate_amount_df["Tax"] = "Notax"
        # 将 inf 替换为 0
        rate_amount_df = rate_amount_df.replace([np.inf, -np.inf], 0)
        rate_amount_df = rate_amount_df.fillna(0)
        print(rate_amount_df)
        cube_.data_to_cube(cube=self.cube, del_fix=del_fix, data=rate_amount_df)

    def calc_tax_actual(self, pov, year, scenario, period):
        # 获取 税率
        fix = self.fix % (
            "Base(PL010202,0);Base(PL010203,0)",
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
            pov["Misc1"],
            pov["Misc2"],
        )
        tax_rate_df = cube_.query_cube(cube_name=self.cube, fix=fix)
        # 清除数据
        del_fix = self.fix % (
            "Base(PL010202,0);Base(PL010203,0)",
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
            pov["Misc1"],
            pov["Misc2"],
        )
        # cube_.delete(cube_name=self.cube, expression=del_fix)
        del tax_rate_df["Tax"]
        del tax_rate_df["Scenario"]
        # 给 data 重命名 taxrate
        tax_rate_df = tax_rate_df.rename(columns={"data": "taxrate"})
        # 获取不含税金额
        fix = self.fix % (
            "Base(PL010202,0);Base(PL010203,0)",
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
            pov["Misc1"],
            pov["Misc2"],
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

    def calc_noperiod_sum(self, pov, year, scenario, fc_var):
        # 删除
        del_fix = self.fix % (
            "Base(PL010202,0);Base(PL010203,0);YW0215",
            year,
            scenario,
            "Expenses",
            "Noperiod",
            pov["Entity"],
            pov["Version"],
            pov["Material"],
            pov["Department"],
            pov["Allocation"],
            "Notax;Tax",
            pov["Misc1"],
            pov["Misc2"],
        )
        cube_.delete(cube_name=self.cube, expression=del_fix)
        if fc_var == "Forecast":
            forecast_fix = self.fix % (
                "Base(PL010202,0);Base(PL010203,0);YW0215",
                year,
                scenario,
                "Expenses",
                "1;2;3;4;5;6;7;8;9",
                pov["Entity"],
                pov["Version"],
                pov["Material"],
                pov["Department"],
                pov["Allocation"],
                "Notax;Tax",
                pov["Misc1"],
                pov["Misc2"],
            )
            forecast_data = cube_.query_cube(cube_name=self.cube, fix=forecast_fix)
            actual_fix = self.fix % (
                "Base(PL010202,0);Base(PL010203,0);YW0215",
                year,
                "Forecast",
                "Expenses",
                "10;11;12",
                pov["Entity"],
                pov["Version"],
                pov["Material"],
                pov["Department"],
                pov["Allocation"],
                "Notax;Tax",
                pov["Misc1"],
                pov["Misc2"],
            )
            actual_data = cube_.query_cube(cube_name=self.cube, fix=actual_fix)
            df = pd.concat([forecast_data, actual_data])
            df["Scenario"] = "Actual"
        else:
            actual_fix = self.fix % (
                "Base(PL010202,0);Base(PL010203,0);YW0215",
                year,
                scenario,
                "Expenses",
                "1;2;3;4;5;6;7;8;9;10;11;12",
                pov["Entity"],
                pov["Version"],
                pov["Material"],
                pov["Department"],
                pov["Allocation"],
                "Notax;Tax",
                pov["Misc1"],
                pov["Misc2"],
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
                "Misc1",
                "Misc2",
            ],
            as_index=False,
        ).sum()
        cube_.save_cube(cube_name=self.cube, df=df)

    def calc_unit_measure(self, pov, year, scenario, calculations):
        """Calculate Unit measure for specified accounts with flexible formulas."""
        # logger.info(f"Calculating Unit measures for Year={year}, Scenario={scenario}")
        pov["Entity"] = "IDescendant(1,0)"

        # 过滤与目标 scenario 匹配的计算
        calcs = [calc for calc in calculations if calc["scenario"] == scenario]
        if not calcs:
            # logger.warning(f"No calculations for Year={year}, Scenario={scenario}")
            return

        # 删除旧 Unit 数据
        accounts = ";".join(calc["account"] for calc in calcs)
        for tax in ["Notax", "Tax"]:
            del_fix = self.fix % (
                accounts,
                year,
                scenario,
                "Unit",
                "Noperiod",
                pov["Entity"],
                pov["Version"],
                pov["Material"],
                pov["Department"],
                pov["Allocation"],
                tax,
                pov["Misc1"],
                pov["Misc2"],
            )
            try:
                cube_.delete(cube_name=self.cube, expression=del_fix)
            except Exception as e:
                # logger.error(f"Error deleting Unit data for {del_fix}: {e}")

                print(e)

        result_df = pd.DataFrame()
        for calc in calcs:
            account = calc["account"]
            formula = calc["formula"]
            taxes = calc["taxes"]
            variables = calc["variables"]

            for tax in taxes:
                # 查询变量数据
                var_dfs = []
                for var_name, var_config in variables.items():
                    var_pov = {
                        "Account": var_config["account"],
                        "Scenario": var_config["scenario"],
                        "Measure": var_config["measure"],
                        "Period": "Noperiod",
                        "Tax": var_config["tax"]
                    }
                    var_df = self._query_cube_data(pov, var_pov, year)
                    if var_df.empty:
                        # logger.warning(f"No data for {var_name} ({var_config['account']}, {var_config['tax']}, {var_config['scenario']}, {year})")
                        continue
                    var_df = var_df.rename(columns={var_config["account"]: var_name})
                    var_dfs.append(var_df)

                if not var_dfs:
                    # logger.warning(f"No variable data for {account} ({tax}, {year}, {scenario})")
                    continue

                # 合并变量数据
                calc_df = var_dfs[0]
                for df in var_dfs[1:]:
                    calc_df = pd.merge(calc_df, df, how="outer", on=[
                        "Year", "Scenario", "Period", "Entity", "Version",
                        "Material", "Department", "Allocation", "Misc1", "Misc2"
                    ]).fillna(0)

                # 计算公式
                try:
                    formula_expr = formula
                    for var_name in variables:
                        formula_expr = formula_expr.replace(var_name, f"calc_df['{var_name}']")
                    calc_df["data"] = eval(formula_expr, {"calc_df": calc_df, "np": np})
                    calc_df["data"] = np.where(calc_df["data"].notnull(), calc_df["data"], 0)
                    # logger.info(f"Calculated {account} ({tax}, {year}, {scenario}): {formula_expr}")
                except Exception as e:
                    # logger.error(f"Error evaluating formula {formula} for {account}: {e}")
                    continue

                calc_df["Account"] = account
                calc_df["Scenario"] = scenario
                calc_df["Measure"] = "Unit"
                calc_df["Tax"] = tax

                calc_df = calc_df[[
                    "Account", "Year", "Scenario", "Measure", "Period", "Entity",
                    "Version", "Material", "Department", "Allocation", "Tax", "Misc1", "Misc2", "data"
                ]]
                result_df = pd.concat([result_df, calc_df])

        result_df = result_df.replace([np.inf, -np.inf], 0).fillna(0)
        if not result_df.empty:
            try:
                # logger.info(f"Saving Unit results for {year}, {scenario}:\n{result_df}")
                print(result_df)
                cube_.save_cube(df=result_df, cube_name=self.cube)
            except Exception as e:
                # logger.error(f"Error saving Unit data for {year}, {scenario}: {e}")
                print(e)


    def calc_measure(self, pov, year, scenario, calculations,period):
        """Calculate measures for specified accounts and periods."""
        if period != "Noperiod":
            period = "10;11;12" if scenario == "Forecast" else "1;2;3;4;5;6;7;8;9;10;11;12"
        print(f"Calculating measures for Year={year}, Scenario={scenario}, Period={period}")
        # pov["Entity"] = "IDescendant(1,0)"

        calcs = [calc for calc in calculations if calc["scenario"] == scenario]
        if not calcs:
            print(f"No calculations for Year={year}, Scenario={scenario}")
            return

        accounts = ";".join(calc["account"] for calc in calcs)
        for tax in ["Notax", "Tax"]:
            del_fix = self.fix % (
                accounts,
                year,
                scenario,
                "Expenses",
                period,
                pov["Entity"],
                pov["Version"],
                pov["Material"],
                pov["Department"],
                pov["Allocation"],
                tax,
                pov["Misc1"],
                pov["Misc2"],
            )
            try:
                cube_.delete(cube_name=self.cube, expression=del_fix)
                print(f"Deleted old data for {del_fix}")
            except Exception as e:
                print(f"Error deleting data for {del_fix}: {e}")

        result_df = pd.DataFrame()
        for calc in calcs:
            account = calc["account"]
            formula = calc["formula"]
            taxes = calc["taxes"]
            variables = calc["variables"]
            print(f"Processing calculation for Account={account}, Scenario={scenario}, Taxes={taxes}")

            for tax in taxes:
                var_dfs = []
                for var_name, var_config in variables.items():
                    var_pov = {
                        "Account": var_config["account"],
                        "Scenario": var_config["scenario"],
                        "Measure": var_config["measure"],
                        "Period": period,
                        "Tax": var_config["tax"]
                    }
                    print(f"Querying data for {var_name}: {var_pov}")
                    var_df = self._query_cube_data(pov, var_pov, year)
                    if var_df.empty:
                        print(f"No data for {var_name} ({var_config['account']}, {var_config['tax']}, {var_config['scenario']}, {year})")
                        continue
                    var_df = var_df.rename(columns={var_config["account"]: var_name})
                    print(f"Queried data for {var_name}:\n{var_df.head()}")
                    var_dfs.append(var_df)

                if not var_dfs:
                    print(f"No variable data for {account} ({tax}, {year}, {scenario})")
                    continue

                calc_df = var_dfs[0]
                for df in var_dfs[1:]:
                    calc_df = pd.merge(calc_df, df, how="outer", on=[
                        "Year", "Scenario", "Period", "Entity", "Version",
                        "Material", "Department", "Allocation", "Misc1", "Misc2"
                    ]).fillna(0)

                missing_vars = [var for var in variables if var not in calc_df.columns]
                if missing_vars:
                    print(f"Missing variables in calc_df for {account} ({tax}): {missing_vars}")
                    continue

                try:
                    formula_expr = formula
                    for var_name in variables:
                        formula_expr = formula_expr.replace(var_name, f"calc_df['{var_name}']")
                    calc_df["data"] = eval(formula_expr, {"calc_df": calc_df, "np": np})
                    calc_df["data"] = np.where(calc_df["data"].notnull(), calc_df["data"], 0)
                    print(f"Calculated {account} ({tax}, {year}, {scenario}): {formula_expr}")
                except Exception as e:
                    print(f"Error evaluating formula {formula} for {account} ({tax}): {e}")
                    continue

                calc_df["Account"] = account
                calc_df["Scenario"] = scenario
                calc_df["Measure"] = "Expenses"
                calc_df["Tax"] = tax

                calc_df = calc_df[[
                    "Account", "Year", "Scenario", "Measure", "Period", "Entity",
                    "Version", "Material", "Department", "Allocation", "Tax", "Misc1", "Misc2", "data"
                ]]
                result_df = pd.concat([result_df, calc_df])

        result_df = result_df.replace([np.inf, -np.inf], 0).fillna(0)
        if not result_df.empty:
            try:
                print(f"Saving results for {year}, {scenario}:\n{result_df}")
                cube_.save_cube(df=result_df, cube_name=self.cube)
            except Exception as e:
                print(f"Error saving data for {year}, {scenario}: {e}")
        else:
            print(f"No results to save for Year={year}, Scenario={scenario}")

    def electricity_calc(self,p2,Account,Measure):
        cube = FinancialCube('WS_cube')
        Entity = p2['Entity']
        Year = p2['Year']
        # material_expr = f"Material{{Remove(IDescendant(MQ,0),{','.join(project_materials)})}}"
        exp = f"Entity{{{Entity}}}->Year{{{Year}}}->Account{{{Account}}}->Tax{{Tax}}->Period{{Noperiod}}->Measure{{{Measure}}}->Scenario{{Budget}}->Version{{Y1}}"
        exp_lastyear = f"Entity{{{Entity}}}->Year{{{str(int(Year) - 1)}}}->Account{{{Account}}}->Tax{{Tax}}->Period{{Noperiod}}->Measure{{{Measure}}}->Scenario{{Actual}}->Version{{Y1}}"
        df1 = cube.query(exp, compact=False)
        df2 = cube.query(exp_lastyear, compact=False)
        df = pd.concat([df1, df2], ignore_index=True)
        df['Tax'] = 'Notax'
        print(1)
        cube.save(df)


def main(p1, p2):

    # 标准化参数
    rename_map = {
        "Entity_wb1": "Entity",
        "Year_wb1": "Year",
        "Measure_wb1": "Measure",
        "Material_wb1":"Material",
        "Scenario_wb1": "Scenario",
        "Allocation_wb1": "Allocation",
        "Version_wb1": "Version",
        "Department_wb1": "Department",
        "Tax_wb1": "Tax",
        "Misc1_wb1": "Misc1",
        "Misc2_wb1": "Misc2"
    }
    p2 = {rename_map.get(key, key): value for key, value in p2.items()}
    print(p2)
    if p2["Tax"] == "Notax":
        print("这是不含税的表单，退出程序不计算")
        return

    begin = time.time()
    p2["Tax"] = "Tax"
    # 年份减一
    year = p2["Year"]
    last_year = str(int(p2["Year"]) - 1)

    # 获取变量
    var = Variable("Variable")
    fc_var = var.get_value("Forcast")

    es = EAS()


    # 计算  电度电量（万度）、电度电费、委外车辆运输、污泥处置费  10-12 预测数
    forecast_calculations = [
        {
            "account": "PL0102020202",
            "scenario": "Forecast",
            "formula": "YW0214 * YW0401 * YW0205",
            "taxes": ["Tax"],
            "variables": {
                "YW0214": {"account": "YW0214", "scenario": "Forecast", "measure": "Expenses", "tax": "Tax"},
                "YW0401": {"account": "YW0401", "scenario": "Forecast", "measure": "Expenses", "tax": "Tax"},
                "YW0205": {"account": "YW0205", "scenario": "Forecast", "measure": "Nomeasure", "tax": "Tax"}
            }
        },

        {
            "account": "YW0215",
            "scenario": "Forecast",
            "formula": "YW0401 * YW0205",
            "taxes": ["Tax"],
            "variables": {
                "YW0401": {"account": "YW0401", "scenario": "Forecast", "measure": "Expenses", "tax": "Tax"},
                "YW0205": {"account": "YW0205", "scenario": "Forecast", "measure": "Nomeasure", "tax": "Tax"}
            }
        },
        {
            "account": "PL0102030102",
            "scenario": "Forecast",
            "formula": "YW0217 * YW0210 / 10000",
            "taxes": ["Tax"],
            "variables": {
                "YW0217": {"account": "YW0217", "scenario": "Forecast", "measure": "Expenses", "tax": "Tax"},
                "YW0210": {"account": "YW0210", "scenario": "Forecast", "measure": "Nomeasure", "tax": "Tax"}
            }
        },
        {
            "account": "PL01020302",
            "scenario": "Forecast",
            "formula": "YW0216 * YW0210 / 10000",
            "taxes": ["Tax"],
            "variables": {
                "YW0216": {"account": "YW0216", "scenario": "Forecast", "measure": "Expenses", "tax": "Tax"},
                "YW0210": {"account": "YW0210", "scenario": "Forecast", "measure": "Nomeasure", "tax": "Tax"}
            }
        }
    ]
    # 计算 吨水电费（元/吨）、污泥处理费吨水费用（元/吨） 10-12 预测数
    forecast_calculations_s = [
        {
            "account": "YW0403",
            "scenario": "Forecast",
            "formula": "PL010203 / YW0205",
            "taxes": ["Tax"],
            "variables": {
                "PL010203": {"account": "PL010203", "scenario": "Forecast", "measure": "Expenses", "tax": "Tax"},
                "YW0205": {"account": "YW0205", "scenario": "Forecast", "measure": "Nomeasure", "tax": "Tax"}
            }
        },
        {
            "account": "YW0402",
            "scenario": "Forecast",
            "formula": "PL01020202 / YW0205",
            "taxes": ["Tax"],
            "variables": {
                "PL01020202": {"account": "PL01020202", "scenario": "Forecast", "measure": "Expenses", "tax": "Tax"},
                "YW0205": {"account": "YW0205", "scenario": "Forecast", "measure": "Nomeasure", "tax": "Tax"}
            }
        }
    ]


    # 计算  电度电量（万度）、电度电费、委外车辆运输、污泥处置费  1-12 预算数
    budget_calculations = [
        {
            "account": "PL0102020202",
            "scenario": "Budget",
            "formula": "YW0214 * YW0401 * YW0205",
            "taxes": ["Tax"],
            "variables": {
                "YW0214": {"account": "YW0214", "scenario": "Budget", "measure": "Expenses", "tax": "Tax"},
                "YW0401": {"account": "YW0401", "scenario": "Budget", "measure": "Expenses", "tax": "Tax"},
                "YW0205": {"account": "YW0205", "scenario": "Budget", "measure": "Nomeasure", "tax": "Tax"}
            }
        },

        {
            "account": "YW0215",
            "scenario": "Budget",
            "formula": "YW0401 * YW0205",
            "taxes": ["Tax"],
            "variables": {
                "YW0401": {"account": "YW0401", "scenario": "Budget", "measure": "Expenses", "tax": "Tax"},
                "YW0205": {"account": "YW0205", "scenario": "Budget", "measure": "Nomeasure", "tax": "Tax"}
            }
        },
        {
            "account": "PL0102030102",
            "scenario": "Budget",
            "formula": "YW0217 * YW0210 / 10000",
            "taxes": ["Tax"],
            "variables": {
                "YW0217": {"account": "YW0217", "scenario": "Budget", "measure": "Expenses", "tax": "Tax"},
                "YW0210": {"account": "YW0210", "scenario": "Budget", "measure": "Nomeasure", "tax": "Tax"}
            }
        },
        {
            "account": "PL01020302",
            "scenario": "Budget",
            "formula": "YW0216 * YW0210 / 10000",
            "taxes": ["Tax"],
            "variables": {
                "YW0216": {"account": "YW0216", "scenario": "Budget", "measure": "Expenses", "tax": "Tax"},
                "YW0210": {"account": "YW0210", "scenario": "Budget", "measure": "Nomeasure", "tax": "Tax"}
            }
        }
    ]
    # 计算  吨水电费（元/吨）、污泥处理费吨水费用（元/吨）  1-12 预算数
    budget_calculations_s = [
        {
            "account": "YW0403",
            "scenario": "Budget",
            "formula": "PL010203 / YW0205",
            "taxes": ["Tax"],
            "variables": {
                "PL010203": {"account": "PL010203", "scenario": "Budget", "measure": "Expenses", "tax": "Tax"},
                "YW0205": {"account": "YW0205", "scenario": "Budget", "measure": "Nomeasure", "tax": "Tax"}
            }
        },
        {
            "account": "YW0402",
            "scenario": "Budget",
            "formula": "PL01020202 / YW0205",
            "taxes": ["Tax"],
            "variables": {
                "PL01020202": {"account": "PL01020202", "scenario": "Budget", "measure": "Expenses", "tax": "Tax"},
                "YW0205": {"account": "YW0205", "scenario": "Budget", "measure": "Nomeasure", "tax": "Tax"}
            }
        }
    ]

    # 计算  电度电量（万度）、电度电费、委外车辆运输、污泥处置费  批复新增
    new_calculations = [
        {
            "account": "PL0102020202",
            "scenario": "New",
            "formula": "YW0214 * YW0401 * YW0205",
            "taxes": ["Tax"],
            "variables": {
                "YW0214": {"account": "YW0214", "scenario": "New", "measure": "Expenses", "tax": "Tax"},
                "YW0401": {"account": "YW0401", "scenario": "New", "measure": "Expenses", "tax": "Tax"},
                "YW0205": {"account": "YW0205", "scenario": "New", "measure": "Nomeasure", "tax": "Tax"}
            }
        },

        {
            "account": "YW0215",
            "scenario": "New",
            "formula": "YW0401 * YW0205",
            "taxes": ["Tax"],
            "variables": {
                "YW0401": {"account": "YW0401", "scenario": "New", "measure": "Expenses", "tax": "Tax"},
                "YW0205": {"account": "YW0205", "scenario": "New", "measure": "Nomeasure", "tax": "Tax"}
            }
        },
        {
            "account": "PL0102030102",
            "scenario": "New",
            "formula": "YW0217 * YW0210 / 10000",
            "taxes": ["Tax"],
            "variables": {
                "YW0217": {"account": "YW0217", "scenario": "New", "measure": "Expenses", "tax": "Tax"},
                "YW0210": {"account": "YW0210", "scenario": "New", "measure": "Nomeasure", "tax": "Tax"}
            }
        },
        {
            "account": "PL01020302",
            "scenario": "New",
            "formula": "YW0216 * YW0210 / 10000",
            "taxes": ["Tax"],
            "variables": {
                "YW0216": {"account": "YW0216", "scenario": "New", "measure": "Expenses", "tax": "Tax"},
                "YW0210": {"account": "YW0210", "scenario": "New", "measure": "Nomeasure", "tax": "Tax"}
            }
        }
    ]
    # 计算  吨水电费（元/吨）、污泥处理费吨水费用（元/吨）  批复新增
    new_calculations_s = [
        {
            "account": "YW0403",
            "scenario": "New",
            "formula": "PL010203 / YW0205",
            "taxes": ["Tax"],
            "variables": {
                "PL010203": {"account": "PL010203", "scenario": "New", "measure": "Expenses", "tax": "Tax"},
                "YW0205": {"account": "YW0205", "scenario": "New", "measure": "Nomeasure", "tax": "Tax"}
            }
        },
        {
            "account": "YW0402",
            "scenario": "New",
            "formula": "PL01020202 / YW0205",
            "taxes": ["Tax"],
            "variables": {
                "PL01020202": {"account": "PL01020202", "scenario": "New", "measure": "Expenses", "tax": "Tax"},
                "YW0205": {"account": "YW0205", "scenario": "New", "measure": "Nomeasure", "tax": "Tax"}
            }
        }
    ]

    # 计算 吨水电费（元/吨）、综合电价、吨水电耗、运输单价、处置单价、污泥处理费吨水费用 实际数全年合计

    actual_YW_noperiod = [
        {
            "account": "YW0402",
            "scenario": "Actual",
            "formula": "PL01020202 / YW0205",
            "taxes": ["Tax"],
            "variables": {
                "PL01020202": {"account": "PL01020202", "scenario": "Actual", "measure": "Expenses", "tax": "Tax"},
                "YW0205": {"account": "YW0205", "scenario": "Actual", "measure": "Nomeasure", "tax": "Tax"}
            }
        },
        {
            "account": "YW0214",
            "scenario": "Actual",
            "formula": "PL0102020202 / YW0215",
            "taxes": ["Tax"],
            "variables": {
                "PL0102020202": {"account": "PL0102020202", "scenario": "Actual", "measure": "Expenses", "tax": "Tax"},
                "YW0215": {"account": "YW0215", "scenario": "Actual", "measure": "Expenses", "tax": "Tax"}
            }
        },
        {
            "account": "YW0401",
            "scenario": "Actual",
            "formula": "YW0215 / YW0205",
            "taxes": ["Tax"],
            "variables": {
                "YW0215": {"account": "YW0215", "scenario": "Actual", "measure": "Expenses", "tax": "Tax"},
                "YW0205": {"account": "YW0205", "scenario": "Actual", "measure": "Nomeasure", "tax": "Tax"}
            }
        },
        {
            "account": "YW0217",
            "scenario": "Actual",
            "formula": "PL0102030102 / YW0210 * 10000",
            "taxes": ["Tax"],
            "variables": {
                "PL0102030102": {"account": "PL0102030102", "scenario": "Actual", "measure": "Expenses", "tax": "Tax"},
                "YW0210": {"account": "YW0210", "scenario": "Actual", "measure": "Nomeasure", "tax": "Tax"}
            }
        },
        {
            "account": "YW0216",
            "scenario": "Actual",
            "formula": "PL01020302 / YW0210  * 10000",
            "taxes": ["Tax"],
            "variables": {
                "PL01020302": {"account": "PL01020302", "scenario": "Actual", "measure": "Expenses", "tax": "Tax"},
                "YW0210": {"account": "YW0210", "scenario": "Actual", "measure": "Nomeasure", "tax": "Tax"}
            }
        },
        {
            "account": "YW0403",
            "scenario": "Actual",
            "formula": "PL010203 / YW0205",
            "taxes": ["Tax"],
            "variables": {
                "PL010203": {"account": "PL010203", "scenario": "Actual", "measure": "Expenses", "tax": "Tax"},
                "YW0205": {"account": "YW0205", "scenario": "Actual", "measure": "Nomeasure", "tax": "Tax"}
            }
        },
    ]


    # 计算 吨水电费（元/吨）、综合电价、吨水电耗、运输单价、处置单价、污泥处理费吨水费用 预算数全年合计
    budget_YW_noperiod = [
        {
            "account": "YW0402",
            "scenario": "Budget",
            "formula": "PL01020202 / YW0205",
            "taxes": ["Tax"],
            "variables": {
                "PL01020202": {"account": "PL01020202", "scenario": "Budget", "measure": "Expenses", "tax": "Tax"},
                "YW0205": {"account": "YW0205", "scenario": "Budget", "measure": "Nomeasure", "tax": "Tax"}
            }
        },
        {
            "account": "YW0214",
            "scenario": "Budget",
            "formula": "PL0102020202 / YW0215",
            "taxes": ["Tax"],
            "variables": {
                "PL0102020202": {"account": "PL0102020202", "scenario": "Budget", "measure": "Expenses", "tax": "Tax"},
                "YW0215": {"account": "YW0215", "scenario": "Budget", "measure": "Expenses", "tax": "Tax"}
            }
        },
        {
            "account": "YW0401",
            "scenario": "Budget",
            "formula": "YW0215 / YW0205",
            "taxes": ["Tax"],
            "variables": {
                "YW0215": {"account": "YW0215", "scenario": "Budget", "measure": "Expenses", "tax": "Tax"},
                "YW0205": {"account": "YW0205", "scenario": "Budget", "measure": "Nomeasure", "tax": "Tax"}
            }
        },
        {
            "account": "YW0217",
            "scenario": "Budget",
            "formula": "PL0102030102 / YW0210 * 10000",
            "taxes": ["Tax"],
            "variables": {
                "PL0102030102": {"account": "PL0102030102", "scenario": "Budget", "measure": "Expenses", "tax": "Tax"},
                "YW0210": {"account": "YW0210", "scenario": "Budget", "measure": "Nomeasure", "tax": "Tax"}
            }
        },
        {
            "account": "YW0216",
            "scenario": "Budget",
            "formula": "PL01020302 / YW0210 * 10000",
            "taxes": ["Tax"],
            "variables": {
                "PL01020302": {"account": "PL01020302", "scenario": "Budget", "measure": "Expenses", "tax": "Tax"},
                "YW0210": {"account": "YW0210", "scenario": "Budget", "measure": "Nomeasure", "tax": "Tax"}
            }
        },
        {
            "account": "YW0403",
            "scenario": "Budget",
            "formula": "PL010203 / YW0205",
            "taxes": ["Tax"],
            "variables": {
                "PL010203": {"account": "PL010203", "scenario": "Budget", "measure": "Expenses", "tax": "Tax"},
                "YW0205": {"account": "YW0205", "scenario": "Budget", "measure": "Nomeasure", "tax": "Tax"}
            }
        },
    ]

    if fc_var == "Forecast":
        es.calc_measure(pov=p2, year=last_year, scenario="Forecast", calculations=forecast_calculations, period=None)
        es.calc_measure(pov=p2, year=last_year, scenario="Forecast", calculations=forecast_calculations_s, period=None)

    es.calc_measure(pov=p2, year=year, scenario="Budget", calculations=budget_calculations, period=None)
    es.calc_measure(pov=p2, year=year, scenario="Budget", calculations=budget_calculations_s, period=None)


    # 1、Actual税率转换 --不含税计算含税
    es.calc_tax_actual(pov=p2, year=last_year, scenario="Actual", period="1;2;3;4;5;6;7;8;9;10;11;12")

    # 计算电度电费（万元）、委外车辆运输、污泥处置费（万元）实际数含税转换不含税
    # es.calc_notax(pov=p2, year=last_year, scenario="Actual", period="1;2;3;4;5;6;7;8;9;10;11;12")

    # 2.1、税率转换： 10-12月预测数 含税计算不含税
    es.calc_notax(pov=p2, year=last_year, scenario="Actual", period="Base(Oct,0)")


    # 2.2、税率转换： 1-12月预算数 含税计算不含税
    es.calc_notax(pov=p2, year=year, scenario="Budget", period="1;2;3;4;5;6;7;8;9;10;11;12")

    # 2.3、税率转换： Noperiod批复新增 含税计算不含税
    es.calc_notax(pov=p2, year=last_year, scenario="New", period="Noperiod")

    # noperiod 含税、不含税 汇总
    es.calc_noperiod_sum(pov=p2, year=last_year, scenario="Actual", fc_var=fc_var)
    es.calc_noperiod_sum(pov=p2, year=year, scenario="Budget", fc_var="Actual")

    es.calc_measure(pov=p2, year=last_year, scenario="Actual", calculations=actual_YW_noperiod,period = 'Noperiod')
    es.calc_measure(pov=p2, year=year, scenario="Budget", calculations=budget_YW_noperiod,period = 'Noperiod')
    es.calc_measure(pov=p2, year=year, scenario="New", calculations=new_calculations,period = 'Noperiod')
    es.calc_measure(pov=p2, year=year, scenario="New", calculations=new_calculations_s,period = 'Noperiod')

    # 定义 Unit 计算配置
    unit_calculations = [
        # 计算 吨水电费 实际、预算 含税、不含税 指标
        {
            "account": "YW0402",
            "scenario": "Actual",
            "formula": "PL01020202 / YW0205",
            "taxes": ["Notax"],
            "variables": {
                "PL01020202": {"account": "PL01020202", "scenario": "Actual", "measure": "Expenses", "tax": "Notax"},
                "YW0205": {"account": "YW0205", "scenario": "Actual", "measure": "Nomeasure", "tax": "Tax"}
            }
        },
        {
            "account": "YW0402",
            "scenario": "Actual",
            "formula": "PL01020202 / YW0205",
            "taxes": ["Tax"],
            "variables": {
                "PL01020202": {"account": "PL01020202", "scenario": "Actual", "measure": "Expenses", "tax": "Tax"},
                "YW0205": {"account": "YW0205", "scenario": "Actual", "measure": "Nomeasure", "tax": "Tax"}
            }
        },
        {
            "account": "YW0402",
            "scenario": "Budget",
            "formula": "PL01020202 / YW0205",
            "taxes": ["Notax"],
            "variables": {
                "PL01020202": {"account": "PL01020202", "scenario": "Budget", "measure": "Expenses", "tax": "Notax"},
                "YW0205": {"account": "YW0205", "scenario": "Budget", "measure": "Nomeasure", "tax": "Tax"}
            }
        },
        {
            "account": "YW0402",
            "scenario": "Budget",
            "formula": "PL01020202 / YW0205",
            "taxes": ["Tax"],
            "variables": {
                "PL01020202": {"account": "PL01020202", "scenario": "Budget", "measure": "Expenses", "tax": "Tax"},
                "YW0205": {"account": "YW0205", "scenario": "Budget", "measure": "Nomeasure", "tax": "Tax"}
            }

        },
        {
            "account": "YW0402",
            "scenario": "New",
            "formula": "PL01020202 / YW0205",
            "taxes": ["Tax"],
            "variables": {
                "PL01020202": {"account": "PL01020202", "scenario": "New", "measure": "Expenses", "tax": "Tax"},
                "YW0205": {"account": "YW0205", "scenario": "New", "measure": "Nomeasure", "tax": "Tax"}
            }

        },

        # 计算 吨水污泥处理费 实际、预算 含税、不含税 指标
        {
            "account": "YW0403",
            "scenario": "Actual",
            "formula": "PL010203 / YW0205",
            "taxes": ["Notax"],
            "variables": {
                "PL010203": {"account": "PL010203", "scenario": "Actual", "measure": "Expenses", "tax": "Notax"},
                "YW0205": {"account": "YW0205", "scenario": "Actual", "measure": "Nomeasure", "tax": "Tax"}
            }
        },
        {
            "account": "YW0403",
            "scenario": "Actual",
            "formula": "PL010203 / YW0205",
            "taxes": ["Tax"],
            "variables": {
                "PL010203": {"account": "PL010203", "scenario": "Actual", "measure": "Expenses", "tax": "Tax"},
                "YW0205": {"account": "YW0205", "scenario": "Actual", "measure": "Nomeasure", "tax": "Tax"}
            }
        },
        {
            "account": "YW0403",
            "scenario": "Budget",
            "formula": "PL010203 / YW0205",
            "taxes": ["Notax"],
            "variables": {
                "PL010203": {"account": "PL010203", "scenario": "Budget", "measure": "Expenses", "tax": "Notax"},
                "YW0205": {"account": "YW0205", "scenario": "Budget", "measure": "Nomeasure", "tax": "Tax"}
            }
        },
        {
            "account": "YW0403",
            "scenario": "Budget",
            "formula": "PL010203 / YW0205",
            "taxes": ["Tax"],
            "variables": {
                "PL010203": {"account": "PL010203", "scenario": "Budget", "measure": "Expenses", "tax": "Tax"},
                "YW0205": {"account": "YW0205", "scenario": "Budget", "measure": "Nomeasure", "tax": "Tax"}
            }
        },

        # 计算 吨水电度电量 实际、预算 含税 指标
       {
            "account": "YW0401",
            "scenario": "Actual",
            "formula": "YW0215 / YW0205",
            "taxes": ["Tax"],
            "variables": {
                "YW0215": {"account": "YW0215", "scenario": "Actual", "measure": "Expenses", "tax": "Tax"},
                "YW0205": {"account": "YW0205", "scenario": "Actual", "measure": "Nomeasure", "tax": "Tax"}
            }
        },
        {
            "account": "YW0401",
            "scenario": "Budget",
            "formula": "YW0215 / YW0205",
            "taxes": ["Tax"],
            "variables": {
                "YW0215": {"account": "YW0215", "scenario": "Budget", "measure": "Expenses", "tax": "Tax"},
                "YW0205": {"account": "YW0205", "scenario": "Budget", "measure": "Nomeasure", "tax": "Tax"}
            }
        },

        # 计算 综合电价 实际、预算 含税、不含税 指标
        {
            "account": "YW0214",
            "scenario": "Actual",
            "formula": "PL0102020202 / YW0215",
            "taxes": ["Notax"],
            "variables": {
                "PL0102020202": {"account": "PL0102020202", "scenario": "Actual", "measure": "Expenses", "tax": "Notax"},
                "YW0215": {"account": "YW0215", "scenario": "Actual", "measure": "Expenses", "tax": "Tax"}
            }
        },
        {
            "account": "YW0214",
            "scenario": "Actual",
            "formula": "PL0102020202 / YW0215",
            "taxes": ["Tax"],
            "variables": {
                "PL0102020202": {"account": "PL0102020202", "scenario": "Actual", "measure": "Expenses", "tax": "Tax"},
                "YW0215": {"account": "YW0215", "scenario": "Actual", "measure": "Expenses", "tax": "Tax"}
            }
        },
        {
            "account": "YW0214",
            "scenario": "Budget",
            "formula": "PL0102020202 / YW0215",
            "taxes": ["Notax"],
            "variables": {
                "PL0102020202": {"account": "PL0102020202", "scenario": "Budget", "measure": "Expenses", "tax": "Notax"},
                "YW0215": {"account": "YW0215", "scenario": "Budget", "measure": "Expenses", "tax": "Tax"}
            }
        },
        {
            "account": "YW0214",
            "scenario": "Budget",
            "formula": "PL0102020202 / YW0215",
            "taxes": ["Tax"],
            "variables": {
                "PL0102020202": {"account": "PL0102020202", "scenario": "Budget", "measure": "Expenses", "tax": "Tax"},
                "YW0215": {"account": "YW0215", "scenario": "Budget", "measure": "Expenses", "tax": "Tax"}
            }
        }
    ]

    # 计算 Unit 度量：2024 Actual 和 2025 Budget
    es.calc_unit_measure(pov=p2, year=last_year, scenario="Actual", calculations=unit_calculations)
    es.calc_unit_measure(pov=p2, year=year, scenario="Budget", calculations=unit_calculations)
    es.calc_unit_measure(pov=p2, year=year, scenario="New", calculations=unit_calculations)

    # 计算YW0215-电度电量（万度）和 YW0401-电度电量吨水电耗（度/吨） 不含税数据
    es.electricity_calc(p2,Account='YW0401',Measure='Unit')
    es.electricity_calc(p2,Account='YW0215',Measure='Expenses')
    print("电费：", time.time() - begin)


if __name__ == "__main__":
    try:
        from common._debug import para1
    except BaseException:
        pass

    para2 =  {'elementName': 'Electricity',
              'folderId': 'DIRb6550dd20485',
              'sheetName': '电费&污泥费',
              'sheetId': 'SHT8f94a382ea18426cba26b784cdde54e9',
              'Year_wb1': '2025',
              'Entity_wb1': 'XN61001_01',
              'Version_wb1': 'Y1',
              'Tax_wb1': 'Tax',
              'Scenario_wb1': 'Actual',
              'Department_wb1': 'Operation',
              'Material_wb1': 'Nomaterial',
              'Allocation_wb1': 'Original',
              'Misc1_wb1': 'Nomisc1',
              'Misc2_wb1': 'Nomisc2'}


    main(para1, para2)
