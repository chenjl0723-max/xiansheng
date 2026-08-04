# -*- coding: utf-8 -*-
# @Time : 2025/12/17
# @Author : Your Name
# @FileName: energy_cost.py
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

class EnergyCostBasic(object):
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
            "SPL010202",       # 2）能源费（万元）
            "SPL01020201",     # 自来水费（万元）
            "SYW020501",       # 自来水用量合计（m3）
            "SYW020515",       # 自来水单价（元/m3）
            "SYW020503",       # 中水用量合计（m3）
            "SYW020516",       # 中水单价（元/m3）
            "SPL01020202",     # 动力电费（万元）
            "SPL0102020201",   # 基本电费（万元）
            "SPL0102020202",   # 电度电费（万元）
            "SYW020505",       # 电度电量合计（万kWh）
            "SYW020519",       # 平均电度单价（元/kWh）
            "SPL01020203",     # 取暖费（万元）
            "SYW020520",       # 数量(㎡)
            "SYW020521",       # 单价（元/㎡）
            "SPL01020204",     # 燃气费（万元）
            "SYW020513",       # 天然气用量合计（Nm3）
            "SYW020522",       # 天然气单价（元/Nm3）
            "SPL01020205",     # 燃油费（万元）
            "SYW020523",       # 数量(L)
            "SYW020524",       # 单价（元/L）
        ]
        self.ALL_ACCOUNTS = ";".join(self.all_accounts_list)

        # Actual 场景仅计算这三个单价（反算）
        self.calc_only_accounts_actual = [
            "SYW020521",       # 取暖单价
            "SYW020522",       # 天然气单价
            "SYW020524",       # 燃油单价
        ]
        self.CALC_ACTUAL_STR = ";".join(self.calc_only_accounts_actual)

        # Budget/Forecast 场景仅计算这五个费用（正算）
        self.calc_only_accounts_forecast_budget = [
            "SPL01020201",     # 自来水费
            "SPL0102020202",   # 电度电费
            "SPL01020203",     # 取暖费
            "SPL01020204",     # 燃气费
            "SPL01020205",     # 燃油费
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

        print("能源费清数完成：所有 Noperiod 已删除，计算科目月度已清除，手工录入数据保留")

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
        print("开始计算实际数月度明细（仅计算 SYW020521、SYW020522、SYW020524）...")

        df_actual_monthly = df[(df["Year"] == self.last_year) & (df["Scenario"] == "Actual") &
                        (df["Period"].isin(["1","2","3","4","5","6","7","8","9"]))].copy()

        if forecast_val == "Forecast":
            self.calc_forecast_monthly(df, forecast_val, cube)
        else:
            df_act_10_12 = df[(df["Year"] == self.last_year) & (df["Scenario"] == "Actual") &
                              (df["Period"].isin(["10", "11", "12"]))].copy()
            df_actual_monthly = pd.concat([df_actual_monthly, df_act_10_12], ignore_index=True)

        # df_actual_monthly = pd.concat([df_act_1_9, df_act_10_12], ignore_index=True)
        # df_actual_monthly.fillna(0, inplace=True)

        # 取暖单价 = 取暖费 * 10000 / 数量
        df_actual_monthly["SYW020521"] = np.where(df_actual_monthly["SYW020520"] != 0,
                                                  df_actual_monthly["SPL01020203"] * 10000 / df_actual_monthly["SYW020520"], 0)

        # 天然气单价 = 燃气费 * 10000 / 天然气量
        df_actual_monthly["SYW020522"] = np.where(df_actual_monthly["SYW020513"] != 0,
                                                  df_actual_monthly["SPL01020204"] * 10000 / df_actual_monthly["SYW020513"], 0)

        # 燃油单价 = 燃油费 * 10000 / 数量
        df_actual_monthly["SYW020524"] = np.where(df_actual_monthly["SYW020523"] != 0,
                                                  df_actual_monthly["SPL01020205"] * 10000 / df_actual_monthly["SYW020523"], 0)

        dim_cols = ["Year", "Scenario", "Period", "Entity", "Version", "Material", "Department",
                    "Tax", "Misc1", "Misc2", "Misc3", "Format", "Project_Type", "PM_Chars", "Measure"]

        df_to_save = df_actual_monthly[dim_cols + self.calc_only_accounts_actual].copy()
        cube.save_unpivot(df_to_save, unpivot_dim="Account")
        print("实际数月度明细计算完成（仅写入三个单价）")

    def calc_forecast_monthly(self, df, forecast_val, cube):
        if forecast_val != "Forecast":
            return

        df_forecast = df[(df["Year"] == self.last_year) & (df["Scenario"] == "Forecast") &
                         (df["Period"].isin(["10","11","12"]))].copy()
        if df_forecast.empty:
            return

        df_forecast.fillna(0, inplace=True)

        # 正算五个费用
        df_forecast["SPL01020201"] = (df_forecast["SYW020501"] * df_forecast["SYW020515"] +
                                      df_forecast["SYW020503"] * df_forecast["SYW020516"]) / 10000

        df_forecast["SPL0102020202"] = df_forecast["SYW020505"] * df_forecast["SYW020519"]

        df_forecast["SPL01020203"] = df_forecast["SYW020520"] * df_forecast["SYW020521"] / 10000

        df_forecast["SPL01020204"] = df_forecast["SYW020513"] * df_forecast["SYW020522"] / 10000

        df_forecast["SPL01020205"] = df_forecast["SYW020523"] * df_forecast["SYW020524"] / 10000

        dim_cols = ["Year", "Scenario", "Period", "Entity", "Version", "Material", "Department",
                    "Tax", "Misc1", "Misc2", "Misc3", "Format", "Project_Type", "PM_Chars", "Measure"]

        df_to_save = df_forecast[dim_cols + self.calc_only_accounts_forecast_budget].copy()
        cube.save_unpivot(df_to_save, unpivot_dim="Account")
        print("预测数10-12月计算完成（仅写入五个费用）")

    def calc_budget_monthly(self, df, cube):
        print("开始计算预算数月度明细（仅写入五个费用）...")

        df_budget = df[(df["Year"] == self.year) & (df["Scenario"] == "Budget") &
                       (df["Period"].isin(["1","2","3","4","5","6","7","8","9","10","11","12"]))].copy()
        if df_budget.empty:
            print("预算月度数据为空，跳过")
            return

        df_budget.fillna(0, inplace=True)

        # 正算五个费用
        df_budget["SPL01020201"] = (df_budget["SYW020501"] * df_budget["SYW020515"] +
                                    df_budget["SYW020503"] * df_budget["SYW020516"]) / 10000

        df_budget["SPL0102020202"] = df_budget["SYW020505"] * df_budget["SYW020519"]

        df_budget["SPL01020203"] = df_budget["SYW020520"] * df_budget["SYW020521"] / 10000

        df_budget["SPL01020204"] = df_budget["SYW020513"] * df_budget["SYW020522"] / 10000

        df_budget["SPL01020205"] = df_budget["SYW020523"] * df_budget["SYW020524"] / 10000

        dim_cols = ["Year", "Scenario", "Period", "Entity", "Version", "Material", "Department",
                    "Tax", "Misc1", "Misc2", "Misc3", "Format", "Project_Type", "PM_Chars", "Measure"]

        df_to_save = df_budget[dim_cols + self.calc_only_accounts_forecast_budget].copy()
        cube.save_unpivot(df_to_save, unpivot_dim="Account")
        print("预算数月度计算完成（仅写入五个费用）")

    def calc_noperiod_all_scenarios(self, cube, forecast_val):
        """
        统一计算所有场景的全年合计 Noperiod（纯求和 + 单价反算，无平均值科目）
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

        sum_accounts = ["SPL01020201","SPL0102020201", "SPL0102020202", "SPL01020203", "SPL01020204", "SPL01020205",
                        "SYW020501", "SYW020503", "SYW020505", "SYW020513", "SYW020523"]

        state_accounts = ['SYW020520']

        result_dfs = []

        is_forecast_mode = (forecast_val == "Forecast")

        # ==================== 处理 Actual 场景全年 ====================
        if is_forecast_mode:
            # 1-9月 Actual
            df_act_1_9 = df_monthly[
                (df_monthly["Year"] == self.last_year) &
                (df_monthly["Scenario"] == "Actual") &
                (df_monthly["Period"].isin(["1", "2", "3", "4", "5", "6", "7", "8", "9"]))
                ].copy()

            # 10-12月 Forecast（场景改为 Actual）
            df_fc_10_12 = df_monthly[
                (df_monthly["Year"] == self.last_year) &
                (df_monthly["Scenario"] == "Forecast") &
                (df_monthly["Period"].isin(["10", "11", "12"]))
                ].copy()
            df_fc_10_12["Scenario"] = "Actual"  # 统一为 Actual

            df_actual_all = pd.concat([df_act_1_9, df_fc_10_12], ignore_index=True)
        else:
            df_actual_all = df_monthly[
                (df_monthly["Year"] == self.last_year) &
                (df_monthly["Scenario"] == "Actual")
                ].copy()

        if not df_actual_all.empty:
            df_act_yearly = self._calc_one_scenario_yearly(df_actual_all, sum_accounts, [], state_accounts, "12", self.last_year,
                                                           "Actual")
            result_dfs.append(df_act_yearly)

        # ==================== 处理 Budget 场景全年 ====================
        df_budget = df_monthly[
            (df_monthly["Year"] == self.year) &
            (df_monthly["Scenario"] == "Budget")
            ].copy()

        if not df_budget.empty:
            df_budget_yearly = self._calc_one_scenario_yearly(df_budget, sum_accounts, [], state_accounts, "1", self.year, "Budget")
            result_dfs.append(df_budget_yearly)

        if not result_dfs:
            print("无全年数据生成")
            return

        df_all_yearly = pd.concat(result_dfs, ignore_index=True)

        # ==================== 全年反算单价 ====================
        df_all_yearly["SYW020519"] = np.where(df_all_yearly["SYW020505"] != 0,
                                              df_all_yearly["SPL0102020202"] / df_all_yearly["SYW020505"], 0)

        df_all_yearly["SYW020521"] = np.where(df_all_yearly["SYW020520"] != 0,
                                              df_all_yearly["SPL01020203"] * 10000 / df_all_yearly["SYW020520"], 0)

        df_all_yearly["SYW020522"] = np.where(df_all_yearly["SYW020513"] != 0,
                                              df_all_yearly["SPL01020204"] * 10000 / df_all_yearly["SYW020513"], 0)

        df_all_yearly["SYW020524"] = np.where(df_all_yearly["SYW020523"] != 0,
                                              df_all_yearly["SPL01020205"] * 10000 / df_all_yearly["SYW020523"], 0)


        # 补齐缺失科目
        for acc in self.all_accounts_list:
            if acc not in df_all_yearly.columns:
                df_all_yearly[acc] = 0

        save_cols = dim_cols + ["Period"] + self.all_accounts_list
        cube.save_unpivot(df_all_yearly[save_cols], unpivot_dim="Account")

        print("能源费全年合计（Noperiod）计算完成（纯求和 + 全年反算单价 + 汇总费用求和）")

    def _calc_one_scenario_yearly(self, df_source, sum_accounts, avg_accounts, state_accounts,
                                  take_month, year_val, scenario_val):
        """
        辅助函数：计算单个场景的全年合计（支持多实体，无 for 循环）
        - 内部使用 groupby("Entity") 处理所有实体
        - 支持求和、平均、取特定月
        """
        if df_source.empty:
            return pd.DataFrame()

        # 构建 agg 字典
        agg_dict = {}

        # 求和科目
        for acc in sum_accounts:
            agg_dict[acc] = 'sum'

        # 平均科目
        for acc in avg_accounts:
            agg_dict[acc] = 'mean'

        # 状态类科目：取指定月份的第一行值
        if state_accounts:
            df_specific = df_source[df_source["Period"] == take_month]
            if not df_specific.empty:
                state_agg = df_specific.groupby("Entity", as_index=False).agg({
                    acc: 'first' for acc in state_accounts
                })
            else:
                state_agg = pd.DataFrame(columns=state_accounts).assign(Entity=df_source["Entity"].unique())
                for acc in state_accounts:
                    state_agg[acc] = 0

        # 执行 groupby agg（求和 + 平均）
        if agg_dict:
            df_sum_avg = df_source.groupby("Entity", as_index=False).agg(agg_dict)
        else:
            df_sum_avg = df_source.groupby("Entity", as_index=False).agg(lambda x: 0)  # 空字典时占位

        # 合并状态类
        if state_accounts:
            df_sum_avg = df_sum_avg.merge(state_agg, on="Entity", how="left")

        # 填充维度（用 self 值）
        df_sum_avg["Year"] = year_val
        df_sum_avg["Scenario"] = scenario_val
        df_sum_avg["Period"] = "Noperiod"
        df_sum_avg["Version"] = self.version
        df_sum_avg["Material"] = self.material
        df_sum_avg["Department"] = self.department
        df_sum_avg["Tax"] = self.tax
        df_sum_avg["Misc1"] = self.misc1
        df_sum_avg["Misc2"] = self.misc2
        df_sum_avg["Misc3"] = self.misc3
        df_sum_avg["Format"] = self.format
        df_sum_avg["Project_Type"] = self.project_type
        df_sum_avg["PM_Chars"] = self.pm_chars
        df_sum_avg["Measure"] = "Expenses"

        return df_sum_avg

    def run_all(self, cube, forecast_val):
        print("能源费计算流程开始".center(70, "="))

        self.clear_data(cube)
        df_raw = self.query_data(cube)

        self.calc_actual_monthly(df_raw, forecast_val, cube)
        # self.calc_forecast_monthly(df_raw, forecast_val, cube)
        self.calc_budget_monthly(df_raw, cube)

        self.calc_noperiod_all_scenarios(cube, forecast_val)

        print("能源费计算全部完成".center(70, "="))

def main(p1, p2):
    start = time.time()
    cube = get_cube()
    forecast_val = get_forecast_val()

    energy = EnergyCostBasic(p2)
    energy.run_all(cube, forecast_val)

    print(f"总耗时: {time.time() - start:.2f} 秒")

if __name__ == "__main__":
    try:
        from BIZ._debug import para1, para2
    except:
        pass
    p2 = {'elementName': 'ProductData_Rural_Sewage_Dynamic',
          'folderId': 'DIRdced97a6ae02',
          'sheetName': '能源费',
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