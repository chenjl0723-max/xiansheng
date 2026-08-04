# -*- coding: utf-8 -*-
# @Time : 2025/12/15
# @Author : Your Name
# @FileName: water_env_basic.py
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

class WaterEnvBasic(object):
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

        # ==================== 水环境版科目清单（仅明细 + 衍生计算科目，移除所有父级汇总科目） ====================
        self.all_accounts_list = [
            "SYW020101",      # 运行天数
            "SYW020401",      # 绿化面积(万m2）
            "SYW020402",      # 河道保洁面积(万m2)
            "SYW02011101",    # 污水管网(渠)长度(km)
            "SYW02011102",    # 雨水管网(渠)长度(km)
            "SYW02011201",    # 污水泵站数量(座)
            "SYW02011202",    # 雨水泵站数量(座)
            "SYW02011203",    # 其它泵站数量(座)
            "SYW020403",      # 机组规模（含备用）(m3/s)
            "SYW020404",      # 水闸数量（座）
            "SYW020405",      # 过闸流量(m3/s)
            "SYW020406",      # 孔口面积(m2)
            "SYW020102",      # 运营规模（万吨/天）
            "SYW020103",      # 收费水量（万吨）
            "SYW020104",      # 日均实际处理水量（万吨/天）
            "SYW020105",      # 合计实际处理水量(万吨)
            "SYW020106",      # 水力负荷(%)
            "SYW020107",      # 产泥系数（tDS/万m3）
            "SYW020108",      # 干泥量（吨）
            "SYW020109",      # 污泥含水率（%）
            "SYW020110",      # 湿泥产量（吨）
            "SYW020501",      # 自来水用量合计（m3）
            "SYW020503",      # 中水用量合计（m3）
            "SYW020505",      # 电度电量合计（万kWh）
            "SYW020506",      # 设备用电量（万kWh）
            "SYW020507",      # 照明用电量（万kWh）
            "SYW020510",      # 其他用电量（万kWh）
            "SYW020513",      # 天然气用量合计（Nm3）
        ]
        self.ALL_ACCOUNTS = ";".join(self.all_accounts_list)

        # Actual 场景计算科目（反算为主）
        self.calc_only_accounts_actual = [
            "SYW020104",      # 日均实际处理水量
            "SYW020106",      # 水力负荷
            "SYW020108",      # 干泥量
            "SYW020110",      # 湿泥产量
            "SYW020505",      # 电度电量合计
        ]
        self.CALC_ACTUAL_STR = ";".join(self.calc_only_accounts_actual)

        # Budget/Forecast 场景计算科目（正算为主）
        self.calc_only_accounts_forecast_budget = [
            "SYW020105",      # 合计实际处理水量
            "SYW020106",      # 水力负荷
            "SYW020108",      # 干泥量
            "SYW020110",      # 湿泥产量
            "SYW020505",      # 电度电量合计
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

        print("水环境清数完成：所有 Noperiod 已删除，计算科目月度已清除，手工数据保留")

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
        # 补齐缺失科目列为 0
        for acc in self.all_accounts_list:
            if acc not in df.columns:
                df[acc] = 0
        df.fillna(0, inplace=True)
        print(f"水环境查询完成，获取 {len(df)} 条记录")
        return df

    def calc_actual_monthly(self, df, forecast_val, cube):
        print("开始计算水环境实际数月度明细...")

        df_actual = df[(df["Year"] == self.last_year) & (df["Scenario"] == "Actual") &
                       (df["Period"].isin(["1","2","3","4","5","6","7","8","9"]))].copy()

        if forecast_val == "Forecast":
            self.calc_forecast_monthly(df, forecast_val, cube)
        else:
            df_act_10_12 = df[(df["Year"] == self.last_year) & (df["Scenario"] == "Actual") &
                              (df["Period"].isin(["10","11","12"]))].copy()
            df_actual = pd.concat([df_actual, df_act_10_12], ignore_index=True)

        if df_actual.empty:
            return

        df_actual.fillna(0, inplace=True)

        # 日均处理水量 = 合计 / 天数
        df_actual["SYW020104"] = np.where(df_actual["SYW020101"] != 0, df_actual["SYW020105"] / df_actual["SYW020101"], 0)

        # 水力负荷
        df_actual["SYW020106"] = np.where(df_actual["SYW020102"] != 0, df_actual["SYW020104"] / df_actual["SYW020102"], 0)

        # 干泥量
        df_actual["SYW020108"] = df_actual["SYW020107"] * df_actual["SYW020105"]

        # 湿泥产量
        df_actual["SYW020110"] = np.where((1 - df_actual["SYW020109"]) != 0, df_actual["SYW020108"] / (1 - df_actual["SYW020109"]), 0)

        # 电度合计 = 设备 + 照明 + 其他
        df_actual["SYW020505"] = df_actual["SYW020506"] + df_actual["SYW020507"] + df_actual["SYW020510"]

        dim_cols = ["Year", "Scenario", "Period", "Entity", "Version", "Material", "Department",
                    "Tax", "Misc1", "Misc2", "Misc3", "Format", "Project_Type", "PM_Chars", "Measure"]

        df_to_save = df_actual[dim_cols + self.calc_only_accounts_actual].copy()
        cube.save_unpivot(df_to_save, unpivot_dim="Account")
        print("水环境实际数月度计算完成（仅写计算科目）")

    def calc_forecast_monthly(self, df, forecast_val, cube):
        if forecast_val != "Forecast":
            return

        df_forecast = df[(df["Year"] == self.last_year) & (df["Scenario"] == "Forecast") &
                         (df["Period"].isin(["10","11","12"]))].copy()
        if df_forecast.empty:
            return

        df_forecast.fillna(0, inplace=True)

        # 合计实际处理水量 = 日均 * 天数
        df_forecast["SYW020105"] = df_forecast["SYW020104"] * df_forecast["SYW020101"]

        # 水力负荷
        df_forecast["SYW020106"] = np.where(df_forecast["SYW020102"] != 0, df_forecast["SYW020104"] / df_forecast["SYW020102"], 0)

        # 干泥量
        df_forecast["SYW020108"] = df_forecast["SYW020107"] * df_forecast["SYW020105"]

        # 湿泥产量
        df_forecast["SYW020110"] = np.where((1 - df_forecast["SYW020109"]) != 0, df_forecast["SYW020108"] / (1 - df_forecast["SYW020109"]), 0)

        # 电度合计 = 设备 + 照明 + 其他
        df_forecast["SYW020505"] = df_forecast["SYW020506"] + df_forecast["SYW020507"] + df_forecast["SYW020510"]

        dim_cols = ["Year", "Scenario", "Period", "Entity", "Version", "Material", "Department",
                    "Tax", "Misc1", "Misc2", "Misc3", "Format", "Project_Type", "PM_Chars", "Measure"]

        df_to_save = df_forecast[dim_cols + self.calc_only_accounts_forecast_budget].copy()
        cube.save_unpivot(df_to_save, unpivot_dim="Account")
        print("水环境预测数10-12月计算完成")

    def calc_budget_monthly(self, df, cube):
        print("开始计算水环境预算数月度明细...")

        df_budget = df[(df["Year"] == self.year) & (df["Scenario"] == "Budget") &
                       (df["Period"].isin(["1","2","3","4","5","6","7","8","9","10","11","12"]))].copy()
        if df_budget.empty:
            return

        df_budget.fillna(0, inplace=True)

        # 合计实际处理水量 = 日均 * 天数
        df_budget["SYW020105"] = df_budget["SYW020104"] * df_budget["SYW020101"]

        # 水力负荷
        df_budget["SYW020106"] = np.where(df_budget["SYW020102"] != 0, df_budget["SYW020104"] / df_budget["SYW020102"], 0)

        # 干泥量
        df_budget["SYW020108"] = df_budget["SYW020107"] * df_budget["SYW020105"]

        # 湿泥产量
        df_budget["SYW020110"] = np.where((1 - df_budget["SYW020109"]) != 0, df_budget["SYW020108"] / (1 - df_budget["SYW020109"]), 0)

        # 电度合计 = 设备 + 照明 + 其他
        df_budget["SYW020505"] = df_budget["SYW020506"] + df_budget["SYW020507"] + df_budget["SYW020510"]

        dim_cols = ["Year", "Scenario", "Period", "Entity", "Version", "Material", "Department",
                    "Tax", "Misc1", "Misc2", "Misc3", "Format", "Project_Type", "PM_Chars", "Measure"]

        df_to_save = df_budget[dim_cols + self.calc_only_accounts_forecast_budget].copy()
        cube.save_unpivot(df_to_save, unpivot_dim="Account")
        print("水环境预算数月度计算完成")

    def calc_noperiod_all_scenarios(self, cube, forecast_val):
        print("开始统一计算所有场景的全年合计（Noperiod）...")

        df_monthly_all = self.query_data(cube)
        df_monthly = df_monthly_all[
            df_monthly_all["Period"].isin(["1","2","3","4","5","6","7","8","9","10","11","12"])
        ].copy()

        if df_monthly.empty:
            print("月度数据为空，无法计算全年合计")
            return

        dim_cols = ["Year", "Scenario", "Entity", "Version", "Material", "Department",
                    "Tax", "Misc1", "Misc2", "Misc3", "Format", "Project_Type", "PM_Chars", "Measure"]

        # 求和类科目（总量类）
        sum_accounts = [
            "SYW020101", "SYW020103", "SYW020105", "SYW020108", "SYW020110",
            "SYW020501", "SYW020503", "SYW020505", "SYW020506", "SYW020507", "SYW020510", "SYW020513",
        ]

        # 平均类科目（含水率）
        avg_accounts = ["SYW020109"]

        # 状态类科目（取特定月份）
        state_accounts = [
            "SYW020401", "SYW020402", "SYW02011101", "SYW02011102", "SYW02011201", "SYW02011202", "SYW02011203",
            "SYW020403", "SYW020404", "SYW020405", "SYW020406", "SYW020102",
        ]

        result_dfs = []

        is_forecast_mode = (forecast_val == "Forecast")

        # ==================== 处理 Actual 场景全年 ====================
        if is_forecast_mode:
            df_act = df_monthly[
                (df_monthly["Year"] == self.last_year) &
                (df_monthly["Scenario"] == "Actual") &
                (df_monthly["Period"].isin(["1","2","3","4","5","6","7","8","9"]))
            ]
            df_fc = df_monthly[
                (df_monthly["Year"] == self.last_year) &
                (df_monthly["Scenario"] == "Forecast") &
                (df_monthly["Period"].isin(["10","11","12"]))
            ]
            df_actual_source = pd.concat([df_act, df_fc], ignore_index=True)
            scenario_name = "Actual"
            take_month = "12"
        else:
            df_actual_source = df_monthly[
                (df_monthly["Year"] == self.last_year) &
                (df_monthly["Scenario"] == "Actual")
            ]
            scenario_name = "Actual"
            take_month = "12"

        if not df_actual_source.empty:
            df_act_yearly = self._calc_one_scenario_yearly(
                df_actual_source, sum_accounts, avg_accounts, state_accounts,
                take_month, self.last_year, scenario_name, dim_cols
            )
            result_dfs.append(df_act_yearly)

        # ==================== 处理 Budget 场景全年 ====================
        df_budget_source = df_monthly[
            (df_monthly["Year"] == self.year) &
            (df_monthly["Scenario"] == "Budget")
        ]

        if not df_budget_source.empty:
            df_budget_yearly = self._calc_one_scenario_yearly(
                df_budget_source, sum_accounts, avg_accounts, state_accounts,
                "1", self.year, "Budget", dim_cols
            )
            result_dfs.append(df_budget_yearly)

        if not result_dfs:
            print("无全年数据生成")
            return

        df_all_yearly = pd.concat(result_dfs, ignore_index=True)

        # ==================== 日均、水力负荷、产泥系数等全年重新计算 ====================
        total_qty = df_all_yearly["SYW020105"]
        run_days = df_all_yearly["SYW020101"]
        scale = df_all_yearly["SYW020102"]

        df_all_yearly["SYW020104"] = np.where(run_days != 0, total_qty / run_days, 0)
        df_all_yearly["SYW020106"] = np.where(scale != 0, df_all_yearly["SYW020104"] / scale, 0)
        df_all_yearly["SYW020107"] = np.where(total_qty != 0, df_all_yearly["SYW020108"] / total_qty, 0)

        # 补齐缺失科目
        for acc in self.all_accounts_list:
            if acc not in df_all_yearly.columns:
                df_all_yearly[acc] = 0

        save_cols = dim_cols + ["Period"] + self.all_accounts_list
        cube.save_unpivot(df_all_yearly[save_cols], unpivot_dim="Account")

        print("水环境全年合计（Noperiod）计算完成")

    def _calc_one_scenario_yearly(self, df_source, sum_accounts, avg_accounts, state_accounts,
                                  take_month, year_val, scenario_val, dim_cols):
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

        # 执行求和/平均聚合
        df_sum_avg = df_source.groupby("Entity", as_index=False).agg(agg_dict)

        # 状态类科目：取指定月份的第一行值
        if state_accounts:
            df_specific = df_source[df_source["Period"] == take_month]
            if not df_specific.empty:
                df_state = df_specific.groupby("Entity", as_index=False).agg(
                    {acc: 'first' for acc in state_accounts}
                )
                df_sum_avg = df_sum_avg.merge(df_state, on="Entity", how="left")
                # 填充缺失为 0
                for acc in state_accounts:
                    df_sum_avg[acc].fillna(0, inplace=True)

        # 填充维度（用 self 值，保证一致）
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
        print("水环境基础生产数据计算流程开始".center(70, "="))

        self.clear_data(cube)
        df_raw = self.query_data(cube)

        self.calc_actual_monthly(df_raw, forecast_val, cube)
        self.calc_budget_monthly(df_raw, cube)

        self.calc_noperiod_all_scenarios(cube, forecast_val)

        print("水环境基础生产数据计算全部完成".center(70, "="))

def main(p1, p2):
    start = time.time()
    cube = get_cube()
    forecast_val = get_forecast_val()

    water_env = WaterEnvBasic(p2)
    water_env.run_all(cube, forecast_val)

    print(f"总耗时: {time.time() - start:.2f} 秒")

if __name__ == "__main__":
    try:
        from BIZ._debug import para1, para2
    except:
        pass
    p2 = {'elementName': 'ProductData_Rural_Sewage_Dynamic',
          'folderId': 'DIRdced97a6ae02',
          'sheetName': '基础生产数据-村镇污水',
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