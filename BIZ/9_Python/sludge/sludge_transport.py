# -*- coding: utf-8 -*-
# @Time : 2025/12/16
# @Author : Your Name
# @FileName: sludge_transport.py
# 污泥运输费
# @Software: PyCharm

import time
import numpy as np
import pandas as pd
import warnings
from deepfos.element.finmodel import FinancialCube
from deepfos.element.variable import Variable

warnings.filterwarnings("ignore")

def get_cube():
    return FinancialCube("S_Cube")

def get_forecast_val():
    variable = Variable(element_name="Variable")
    return variable.get_value("Forcast")  # "Forecast" 或其他

class SludgeTransportBasic(object):
    def __init__(self, p2):
        self.year = p2["Year_wb1"]
        self.entity = p2["Entity_wb1"]
        self.version = p2["Version_wb1"]
        self.material = "Nomaterial"
        self.tax = p2["Tax_wb1"]
        self.department = p2["Department_wb1"]
        self.misc1 = "Nomisc1"
        self.misc2 = "Nomisc2"
        self.misc3 = "Nomisc3"
        self.format = "NoFormat"
        self.project_type = "NoProject_Type"
        self.pm_chars = "NoPM_Chars"
        self.last_year = str(int(self.year) - 1)

        # ==================== 科目清单 ====================
        self.all_accounts_list = [
            "SPL01020301",  # 污泥运输费（万元）
            "SYW020601",    # （1）湿污泥运输费（万元）
            "SYW020602",    # 湿污泥运输量（吨）
            "SYW020603",    # 湿污泥运输单价（元/吨）
            "SYW020604",    # （2）污泥处理产品运输费（万元）
            "SYW020605",    # 污泥处理产品运输量（吨）
            "SYW020606",    # 污泥处理产品运输单价（元/吨）
        ]
        self.ALL_ACCOUNTS = ";".join(self.all_accounts_list)

        # Actual 场景计算科目（反算单价）
        self.calc_only_accounts_actual = [
            "SYW020603",    # 湿污泥运输单价（元/吨）
            "SYW020606",    # 污泥处理产品运输单价（元/吨）
            # "SPL01020301",  # 总费
        ]
        self.CALC_ACTUAL_STR = ";".join(self.calc_only_accounts_actual)

        # Budget/Forecast 场景计算科目（正算费用）
        self.calc_only_accounts_forecast_budget = [
            "SYW020601",    # 湿费用
            "SYW020604",    # 产品费用
            "SPL01020301",  # 总费
        ]
        self.CALC_BUDGET_FORECAST_STR = ";".join(self.calc_only_accounts_forecast_budget)

    def clear_data(self, cube):
        pov = {
            "Entity": self.entity, "Version": self.version, "Material": self.material,
            "Department": self.department, "Tax": self.tax, "Misc1": self.misc1,
            "Misc2": self.misc2, "Misc3": self.misc3, "Format": self.format,
            "Project_Type": self.project_type, "PM_Chars": self.pm_chars,
        }

        delete_exps = []

        # 删除所有 Noperiod
        delete_exps += [
            {"Year": self.year, "Scenario": "Budget", "Period": "Noperiod", "Account": self.ALL_ACCOUNTS, "Measure": "Expenses"},
            {"Year": self.last_year, "Scenario": "Actual", "Period": "Noperiod", "Account": self.ALL_ACCOUNTS, "Measure": "Expenses"},
            # {"Year": self.last_year, "Scenario": "Forecast", "Period": "Noperiod", "Account": self.ALL_ACCOUNTS, "Measure": "Expenses"},
        ]

        # 删除月度计算科目
        delete_exps += [
            {"Year": self.year, "Scenario": "Budget", "Period": "1;2;3;4;5;6;7;8;9;10;11;12", "Account": self.CALC_BUDGET_FORECAST_STR, "Measure": "Expenses"},
            {"Year": self.last_year, "Scenario": "Actual", "Period": "1;2;3;4;5;6;7;8;9;10;11;12", "Account": self.CALC_ACTUAL_STR, "Measure": "Expenses"},
            {"Year": self.last_year, "Scenario": "Forecast", "Period": "10;11;12", "Account": self.CALC_BUDGET_FORECAST_STR, "Measure": "Expenses"},
        ]

        for exp in delete_exps:
            exp.update(pov)
            cube.delete(exp)

        print("污泥运输费清数完成：所有 Noperiod 已删除，计算科目月度已清除，手工录入数据保留")

    def query_data(self, cube):
        exp = (
            f"Entity{{{self.entity}}}->Version{{{self.version}}}->Material{{{self.material}}}->"
            f"Department{{{self.department}}}->Tax{{{self.tax}}}->Misc1{{{self.misc1}}}->"
            f"Misc2{{{self.misc2}}}->Misc3{{{self.misc3}}}->Format{{{self.format}}}->"
            f"Project_Type{{{self.project_type}}}->PM_Chars{{{self.pm_chars}}}->"
            f"Year{{{self.year};{self.last_year}}}->Account{{{self.ALL_ACCOUNTS}}}->"
            f"Scenario{{Budget;Actual;Forecast}}->Measure{{Expenses}}->"
            f"Period{{1;2;3;4;5;6;7;8;9;10;11;12;Noperiod}}"
        )
        df = cube.query(expression=exp, compact=False, pivot_dim="Account")
        for acc in self.all_accounts_list:
            if acc not in df.columns:
                df[acc] = 0
        df.fillna(0, inplace=True)
        print(f"查询完成，获取 {len(df)} 条记录")
        return df

    def calc_actual_monthly(self, df, forecast_val, cube):
        print("开始计算实际数月度明细（仅写入计算科目）...")

        df_actual = df[(df["Year"] == self.last_year) & (df["Scenario"] == "Actual") &
                        (df["Period"].isin(["1","2","3","4","5","6","7","8","9"]))].copy()

        if forecast_val == "Forecast":
            self.calc_forecast_monthly(df, forecast_val, cube)
        else:
            df_act_10_12 = df[(df["Year"] == self.last_year) & (df["Scenario"] == "Actual") &
                              (df["Period"].isin(["10","11","12"]))].copy()

            df_actual = pd.concat([df_actual, df_act_10_12], ignore_index=True)
        # df_actual_monthly.fillna(0, inplace=True)

        # 湿单价 = 湿费用 * 10000 / 湿量
        df_actual["SYW020603"] = np.where(df_actual["SYW020602"] != 0,
                                                  df_actual["SYW020601"] * 10000 / df_actual["SYW020602"], 0)

        # 产品单价 = 产品费用 * 10000 / 产品量
        df_actual["SYW020606"] = np.where(df_actual["SYW020605"] != 0,
                                                  df_actual["SYW020604"] * 10000 / df_actual["SYW020605"], 0)

        # 总费 = 湿费用 + 产品费用
        df_actual["SPL01020301"] = df_actual["SYW020601"] + df_actual["SYW020604"]

        dim_cols = ["Year", "Scenario", "Period", "Entity", "Version", "Material", "Department",
                    "Tax", "Misc1", "Misc2", "Misc3", "Format", "Project_Type", "PM_Chars", "Measure"]

        df_to_save = df_actual[dim_cols + self.calc_only_accounts_actual].copy()
        cube.save_unpivot(df_to_save, unpivot_dim="Account")
        print("实际数月度明细计算完成（仅写入计算科目）")

    def calc_forecast_monthly(self, df, forecast_val, cube):
        if forecast_val != "Forecast":
            return

        df_forecast = df[(df["Year"] == self.last_year) & (df["Scenario"] == "Forecast") &
                         (df["Period"].isin(["10","11","12"]))].copy()
        if df_forecast.empty:
            return

        df_forecast.fillna(0, inplace=True)

        # 湿费用 = 湿量 * 湿单价 / 10000
        df_forecast["SYW020601"] = df_forecast["SYW020602"] * df_forecast["SYW020603"] / 10000

        # 产品费用 = 产品量 * 产品单价 / 10000
        df_forecast["SYW020604"] = df_forecast["SYW020605"] * df_forecast["SYW020606"] / 10000

        # 总费 = 湿费用 + 产品费用
        df_forecast["SPL01020301"] = df_forecast["SYW020601"] + df_forecast["SYW020604"]

        dim_cols = ["Year", "Scenario", "Period", "Entity", "Version", "Material", "Department",
                    "Tax", "Misc1", "Misc2", "Misc3", "Format", "Project_Type", "PM_Chars", "Measure"]

        df_to_save = df_forecast[dim_cols + self.calc_only_accounts_forecast_budget].copy()
        cube.save_unpivot(df_to_save, unpivot_dim="Account")
        print("预测数10-12月计算完成（仅写入计算科目）")

    def calc_budget_monthly(self, df, cube):
        print("开始计算预算数月度明细（仅写入计算科目）...")

        df_budget = df[(df["Year"] == self.year) & (df["Scenario"] == "Budget") &
                       (df["Period"].isin(["1","2","3","4","5","6","7","8","9","10","11","12"]))].copy()
        if df_budget.empty:
            print("预算月度数据为空，跳过")
            return

        df_budget.fillna(0, inplace=True)

        # 湿费用 = 湿量 * 湿单价 / 10000
        df_budget["SYW020601"] = df_budget["SYW020602"] * df_budget["SYW020603"] / 10000

        # 产品费用 = 产品量 * 产品单价 / 10000
        df_budget["SYW020604"] = df_budget["SYW020605"] * df_budget["SYW020606"] / 10000

        # 总费 = 湿费用 + 产品费用
        df_budget["SPL01020301"] = df_budget["SYW020601"] + df_budget["SYW020604"]

        dim_cols = ["Year", "Scenario", "Period", "Entity", "Version", "Material", "Department",
                    "Tax", "Misc1", "Misc2", "Misc3", "Format", "Project_Type", "PM_Chars", "Measure"]

        df_to_save = df_budget[dim_cols + self.calc_only_accounts_forecast_budget].copy()
        cube.save_unpivot(df_to_save, unpivot_dim="Account")
        print("预算数月度计算完成（仅写入计算科目）")

    def calc_noperiod_all_scenarios(self, cube, forecast_val):
        """
        统一计算所有场景的全年合计 Noperiod（仅求和，无平均值科目）
        当 forecast_val == "Forecast" 时：
            Actual 场景全年 = 1-9月 Actual + 10-12月 Forecast（混合求和）
            不额外生成 Forecast 场景的全年
        """
        print("开始统一计算所有场景的全年合计（Noperiod）...")

        df_monthly_all = self.query_data(cube)
        df_monthly = df_monthly_all[
            df_monthly_all["Period"].isin(["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"])
        ].copy()

        if df_monthly.empty:
            print("月度数据为空，无法计算全年合计")
            return

        dim_cols = ["Year", "Scenario", "Entity", "Version", "Material", "Department",
                    "Tax", "Misc1", "Misc2", "Misc3", "Format", "Project_Type", "PM_Chars", "Measure"]

        # 所有科目都是求和类（费用、量都是累计值，无需平均）
        sum_accounts = ["SPL01020301","SYW020601","SYW020602","SYW020604","SYW020605"]  # 直接用所有科目求和

        result_dfs = []

        is_forecast_mode = (forecast_val == "Forecast")

        # ==================== 处理 Actual 场景全年 ====================
        if is_forecast_mode:
            # 1-9月 Actual
            df_act_1_9 = df_monthly[
                (df_monthly["Year"] == self.last_year) &
                (df_monthly["Scenario"] == "Actual") &
                (df_monthly["Period"].isin(["1", "2", "3", "4", "5", "6", "7", "8", "9"]))
                ]

            # 10-12月 Forecast
            df_fc_10_12 = df_monthly[
                (df_monthly["Year"] == self.last_year) &
                (df_monthly["Scenario"] == "Forecast") &
                (df_monthly["Period"].isin(["10", "11", "12"]))
                ]

            df_actual_source = pd.concat([df_act_1_9, df_fc_10_12], ignore_index=True)
            df_actual_source["Scenario"] = "Actual"

        else:
            df_actual_source = df_monthly[
                (df_monthly["Year"] == self.last_year) &
                (df_monthly["Scenario"] == "Actual")
                ]

        if not df_actual_source.empty:
            # 按 Entity 求和（支持多项目）
            df_act_yearly = df_actual_source.groupby("Entity", as_index=False).agg({
                **{acc: 'sum' for acc in sum_accounts},
                **{col: 'first' for col in dim_cols if col != "Entity"}# 保留维度（取第一行即可）
            })

            df_act_yearly["Period"] = "Noperiod"

            result_dfs.append(df_act_yearly)

        # ==================== 处理 Budget 场景全年 ====================
        df_budget_source = df_monthly[
            (df_monthly["Year"] == self.year) &
            (df_monthly["Scenario"] == "Budget")
            ]

        if not df_budget_source.empty:
            # df_budget_yearly = pd.DataFrame()

            df_budget_yearly = df_budget_source.groupby("Entity", as_index=False).agg({
                **{acc: 'sum' for acc in sum_accounts},
                **{col: 'first' for col in dim_cols if col != "Entity"}  # 保留维度（取第一行即可）
            })

            df_budget_yearly["Period"] = "Noperiod"

            result_dfs.append(df_budget_yearly)

        if not result_dfs:
            print("无全年数据生成")
            return

        df_all_yearly = pd.concat(result_dfs, ignore_index=True)

        # ==================== 单价全年重新计算（反算） ====================
        df_all_yearly["SYW020603"] = np.where(df_all_yearly["SYW020602"] != 0,
                                              df_all_yearly["SYW020601"] * 10000 / df_all_yearly["SYW020602"], 0)

        df_all_yearly["SYW020606"] = np.where(df_all_yearly["SYW020605"] != 0,
                                              df_all_yearly["SYW020604"] * 10000 / df_all_yearly["SYW020605"], 0)


        # 补齐缺失科目
        for acc in self.all_accounts_list:
            if acc not in df_all_yearly.columns:
                df_all_yearly[acc] = 0

        save_cols = dim_cols + ["Period"] + self.all_accounts_list
        cube.save_unpivot(df_all_yearly[save_cols], unpivot_dim="Account")

        print("污泥运输费全年合计（Noperiod）计算完成")

    def _calc_one_scenario_yearly(self, df_source, sum_accounts, avg_accounts, year_val, scenario_val, dim_cols):
        df_y = pd.DataFrame()

        # 求和
        for acc in sum_accounts:
            df_y[acc] = [df_source[acc].sum() if acc in df_source.columns else 0]

        # 平均
        for acc in avg_accounts:
            df_y[acc] = [df_source[acc].mean() if acc in df_source.columns else 0]

        # 维度
        for col in dim_cols:
            df_y[col] = [df_source.iloc[0][col]]
        df_y["Year"] = [year_val]
        df_y["Scenario"] = [scenario_val]
        df_y["Period"] = ["Noperiod"]

        return df_y

    def run_all(self, cube, forecast_val):
        print("污泥运输费计算流程开始".center(70, "="))

        self.clear_data(cube)
        df_raw = self.query_data(cube)

        self.calc_actual_monthly(df_raw, forecast_val, cube)

        self.calc_budget_monthly(df_raw, cube)

        self.calc_noperiod_all_scenarios(cube, forecast_val)

        print("污泥运输费计算全部完成".center(70, "="))

def main(p1, p2):
    start = time.time()
    cube = get_cube()
    forecast_val = get_forecast_val()

    sludge = SludgeTransportBasic(p2)
    sludge.run_all(cube, forecast_val)

    print(f"总耗时: {time.time() - start:.2f} 秒")

if __name__ == "__main__":
    try:
        from BIZ._debug import para1, para2
    except:
        pass
    p2 = {'elementName': 'ProductData_Rural_Sewage_Dynamic',
          'folderId': 'DIRdced97a6ae02',
          'sheetName': '污泥运输费',
          'sheetId': 'SHTcdf7c6782b9b4b329a83a8d91efa21f5',
          'Year_wb1': '2026',
          'Entity_wb1': 'Base(1,0)',
          'Department_wb1': 'Operation',
          'Format_wb1': 'NoFormat',
          'Project_Type_wb1': 'NoProject_Type',
          'PM_Chars_wb1': 'NoPM_Chars',
          'Tax_wb1': 'Tax',
          'Version_wb1': 'Y1',
          'Scenario_wb1': 'Actual'}
    main(para1, p2)