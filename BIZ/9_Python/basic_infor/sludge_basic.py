# -*- coding: utf-8 -*-
# @Time : 2025/12/15
# @Author : Your Name
# @FileName: sludge_basic.py
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

class SludgeBasic(object):
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

        # ==================== 污泥版科目清单（仅明细 + 衍生计算科目，移除所有父级汇总科目） ====================
        self.all_accounts_list = [
            "SYW020101",      # 运行天数
            "SYW020301",      # 运营规模（吨/日）
            "SYW02030201",    # 收费处理量（吨）
            "SYW0203020201",  # 厂内处理量（吨）
            "SYW0203020202",  # 外协处理量（吨）
            "SYW02030301",    # 收费污泥平均含水率
            "SYW02030302",    # 厂内实际处理平均含水率
            "SYW02030303",    # 外协实际处理平均含水率
            "SYW02030401",    # 日均厂内实际处理量
            "SYW02030402",    # 日均外协实际处理量
            "SYW020305",      # 日均处理负荷%
            "SYW02030601",    # 厂内实际处理干泥量
            "SYW02030602",    # 外协实际处理干泥量
            "SYW02030701",    # 好氧堆肥产物
            "SYW02030702",    # 板框脱水后泥饼/沼渣
            "SYW02030703",    # 干化后污泥
            "SYW02030704",    # 沼气产量
            "SYW02030705",    # 污泥焚烧炉渣
            "SYW02030706",    # 污泥炭化炭渣
            "SYW02030707",    # 其他
            "SYW020501",      # 自来水用量合计
            "SYW020502",      # 吨泥自来水用量
            "SYW020503",      # 中水用量合计
            "SYW020504",      # 吨泥中水用量
            "SYW020505",      # 电度电量合计（万kWh）
            "SYW020512",      # 吨泥电度用电量
            "SYW020513",      # 天然气用量合计
            "SYW020514",      # 吨泥天然气用量
        ]
        self.ALL_ACCOUNTS = ";".join(self.all_accounts_list)

        # Actual 场景计算科目（反算为主）
        self.calc_only_accounts_actual = [
            "SYW02030401", "SYW02030402", "SYW020305",
            "SYW02030601", "SYW02030602",
            "SYW020502", "SYW020504", "SYW020512", "SYW020514",
        ]
        self.CALC_ACTUAL_STR = ";".join(self.calc_only_accounts_actual)

        # Budget/Forecast 场景计算科目（正算为主）
        self.calc_only_accounts_forecast_budget = [
            "SYW02030401", "SYW02030402", "SYW020305",
            "SYW02030601", "SYW02030602",
            "SYW020501", "SYW020503", "SYW020505", "SYW020513",
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

        print("污泥清数完成：仅处理明细科目，父级汇总科目已移除")

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
        print(f"污泥查询完成，获取 {len(df)} 条记录")
        return df

    def calc_actual_monthly(self, df, forecast_val, cube):
        print("开始计算污泥实际数月度明细...")

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

        total_qty = df_actual["SYW0203020201"] + df_actual["SYW0203020202"]

        # 日均
        df_actual["SYW02030401"] = np.where(df_actual["SYW020101"] != 0, df_actual["SYW0203020201"] / df_actual["SYW020101"],0)
        df_actual["SYW02030402"] = np.where(df_actual["SYW020101"] != 0, df_actual["SYW0203020202"] / df_actual["SYW020101"],0)
        df_actual["SYW020305"] = np.where(df_actual["SYW020301"] != 0, (df_actual["SYW02030401"] + df_actual["SYW02030402"]) / df_actual["SYW020301"],0)

        # 干泥量
        df_actual["SYW02030601"] = df_actual["SYW0203020201"] * (1 - df_actual["SYW02030302"])
        df_actual["SYW02030602"] = df_actual["SYW0203020202"] * (1 - df_actual["SYW02030303"])

        # 能源类运行指标
        df_actual["SYW020502"] = np.where(total_qty != 0, df_actual["SYW020501"] / total_qty, 0)
        df_actual["SYW020504"] = np.where(total_qty != 0, df_actual["SYW020503"] / total_qty, 0)
        df_actual["SYW020512"] = np.where(total_qty != 0, df_actual["SYW020505"] * 10000 / total_qty, 0)
        df_actual["SYW020514"] = np.where(df_actual["SYW0203020201"] != 0, df_actual["SYW020513"] / df_actual["SYW0203020201"], 0)


        dim_cols = ["Year", "Scenario", "Period", "Entity", "Version", "Material", "Department",
                    "Tax", "Misc1", "Misc2", "Misc3", "Format", "Project_Type", "PM_Chars", "Measure"]

        df_to_save = df_actual[dim_cols + self.calc_only_accounts_actual].copy()
        cube.save_unpivot(df_to_save, unpivot_dim="Account")
        print("污泥实际数月度计算完成（仅写计算科目）")

    def calc_forecast_monthly(self, df, forecast_val, cube):
        if forecast_val != "Forecast":
            return

        df_forecast = df[(df["Year"] == self.last_year) & (df["Scenario"] == "Forecast") &
                         (df["Period"].isin(["10","11","12"]))].copy()
        if df_forecast.empty:
            return

        df_forecast.fillna(0, inplace=True)

        total_qty = df_forecast["SYW0203020201"] + df_forecast["SYW0203020202"]

        # 日均
        df_forecast["SYW02030401"] = np.where(df_forecast["SYW020101"] != 0,df_forecast["SYW0203020201"] / df_forecast["SYW020101"],0)
        df_forecast["SYW02030402"] = np.where(df_forecast["SYW020101"] != 0,df_forecast["SYW0203020202"] / df_forecast["SYW020101"],0)
        df_forecast["SYW020305"] = np.where(df_forecast["SYW020301"] != 0,
                                          (df_forecast["SYW02030401"] + df_forecast["SYW02030402"]) / df_forecast[
                                              "SYW020301"], 0)

        # 干泥量
        df_forecast["SYW02030601"] = df_forecast["SYW0203020201"] * (1 - df_forecast["SYW02030302"])
        df_forecast["SYW02030602"] = df_forecast["SYW0203020202"] * (1 - df_forecast["SYW02030303"])

        # 能源类运行指标
        df_forecast["SYW020501"] = df_forecast["SYW020502"] * total_qty
        df_forecast["SYW020503"] = df_forecast["SYW020504"] * total_qty
        df_forecast["SYW020505"] = df_forecast["SYW020512"] * total_qty / 10000
        df_forecast["SYW020513"] = df_forecast["SYW020514"] * df_forecast["SYW0203020201"]

        dim_cols = ["Year", "Scenario", "Period", "Entity", "Version", "Material", "Department",
                    "Tax", "Misc1", "Misc2", "Misc3", "Format", "Project_Type", "PM_Chars", "Measure"]

        df_to_save = df_forecast[dim_cols + self.calc_only_accounts_forecast_budget].copy()
        cube.save_unpivot(df_to_save, unpivot_dim="Account")
        print("污泥预测数10-12月计算完成")

    def calc_budget_monthly(self, df, cube):
        print("开始计算污泥预算数月度明细...")

        df_budget = df[(df["Year"] == self.year) & (df["Scenario"] == "Budget") &
                       (df["Period"].isin(["1","2","3","4","5","6","7","8","9","10","11","12"]))].copy()
        if df_budget.empty:
            return

        df_budget.fillna(0, inplace=True)

        total_qty = df_budget["SYW0203020201"] + df_budget["SYW0203020202"]

        df_budget["SYW02030401"] = np.where(df_budget["SYW020101"] != 0,df_budget["SYW0203020201"] / df_budget["SYW020101"],0)
        df_budget["SYW02030402"] = np.where(df_budget["SYW020101"] != 0,df_budget["SYW0203020202"] / df_budget["SYW020101"],0)
        df_budget["SYW020305"] = np.where(df_budget["SYW020301"] != 0,
                                          (df_budget["SYW02030401"] + df_budget["SYW02030402"]) / df_budget[
                                              "SYW020301"], 0)

        # 干泥量
        df_budget["SYW02030601"] = df_budget["SYW0203020201"] * (1 - df_budget["SYW02030302"])
        df_budget["SYW02030602"] = df_budget["SYW0203020202"] * (1 - df_budget["SYW02030303"])

        # 能源类运行指标
        df_budget["SYW020501"] = df_budget["SYW020502"] * total_qty
        df_budget["SYW020503"] = df_budget["SYW020504"] * total_qty
        df_budget["SYW020505"] = df_budget["SYW020512"] * total_qty / 10000
        df_budget["SYW020513"] = df_budget["SYW020514"] * df_budget["SYW0203020201"]

        dim_cols = ["Year", "Scenario", "Period", "Entity", "Version", "Material", "Department",
                    "Tax", "Misc1", "Misc2", "Misc3", "Format", "Project_Type", "PM_Chars", "Measure"]

        df_to_save = df_budget[dim_cols + self.calc_only_accounts_forecast_budget].copy()
        cube.save_unpivot(df_to_save, unpivot_dim="Account")
        print("污泥预算数月度计算完成")

    def calc_noperiod_all_scenarios(self, cube, forecast_val):
        """
        污泥版全年合计 Noperiod（最终版）
        - 求和科目：流量、总量等
        - 平均科目：含水率等
        - 状态类科目：运营规模 SYW020301，Actual取12月，Budget取1月
        - 吨泥指标（502/504/512/514）及日均/负荷全年重新计算
        - 支持预测模式混合求和 + 多实体独立计算
        """
        print("开始计算污泥全年合计（Noperiod）...")

        df_monthly_all = self.query_data(cube)
        df_monthly = df_monthly_all[
            df_monthly_all["Period"].isin(["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"])
        ].copy()

        if df_monthly.empty:
            print("无月度数据，跳过全年计算")
            return

        # 求和科目
        sum_accounts = [
            "SYW020101",  # 运行天数
            "SYW02030201",  # 收费处理量
            "SYW0203020201",  # 厂内处理量
            "SYW0203020202",  # 外协处理量
            "SYW02030601", "SYW02030602",
            "SYW02030701", "SYW02030702", "SYW02030703", "SYW02030704",
            "SYW02030705", "SYW02030706", "SYW02030707",
            "SYW020501", "SYW020503", "SYW020505", "SYW020513",
        ]

        # 平均科目（含水率）
        avg_accounts = ["SYW02030301", "SYW02030302", "SYW02030303"]

        # 状态类科目（取特定月份）
        state_accounts = ["SYW020301"]  # 运营规模（吨/日）

        result_dfs = []

        is_forecast_mode = (forecast_val == "Forecast")

        # ==================== 处理 Actual 场景全年 ====================
        if is_forecast_mode:
            df_act_1_9 = df_monthly[
                (df_monthly["Year"] == self.last_year) &
                (df_monthly["Scenario"] == "Actual") &
                (df_monthly["Period"].isin(["1", "2", "3", "4", "5", "6", "7", "8", "9"]))
                ]

            df_fc_10_12 = df_monthly[
                (df_monthly["Year"] == self.last_year) &
                (df_monthly["Scenario"] == "Forecast") &
                (df_monthly["Period"].isin(["10", "11", "12"]))
                ]

            df_actual_source = pd.concat([df_act_1_9, df_fc_10_12], ignore_index=True)
            take_month = "12"
            scenario_val = "Actual"
            year_val = self.last_year
        else:
            df_actual_source = df_monthly[
                (df_monthly["Year"] == self.last_year) &
                (df_monthly["Scenario"] == "Actual")
                ]
            take_month = "12"
            scenario_val = "Actual"
            year_val = self.last_year

        if not df_actual_source.empty:
            df_act_yearly = self._calc_one_scenario_yearly(
                df_source=df_actual_source,
                sum_accounts=sum_accounts,
                avg_accounts=avg_accounts,
                state_accounts=state_accounts,
                take_month=take_month,
                year_val=year_val,
                scenario_val=scenario_val
            )
            result_dfs.append(df_act_yearly)

        # ==================== 处理 Budget 场景全年 ====================
        df_budget_source = df_monthly[
            (df_monthly["Year"] == self.year) &
            (df_monthly["Scenario"] == "Budget")
            ]

        if not df_budget_source.empty:
            df_budget_yearly = self._calc_one_scenario_yearly(
                df_source=df_budget_source,
                sum_accounts=sum_accounts,
                avg_accounts=avg_accounts,
                state_accounts=state_accounts,
                take_month="1",
                year_val=self.year,
                scenario_val="Budget"
            )
            result_dfs.append(df_budget_yearly)

        if not result_dfs:
            print("无全年数据生成")
            return

        df_all_yearly = pd.concat(result_dfs, ignore_index=True)

        # ==================== 吨泥指标及日均/负荷全年重新计算 ====================
        total_qty = df_all_yearly["SYW0203020201"] + df_all_yearly["SYW0203020202"]
        run_days = df_all_yearly["SYW020101"]
        scale = df_all_yearly["SYW020301"]

        # 日均厂内、外协
        df_all_yearly["SYW02030401"] = np.where(run_days > 0, df_all_yearly["SYW0203020201"] / run_days, 0)
        df_all_yearly["SYW02030402"] = np.where(run_days > 0, df_all_yearly["SYW0203020202"] / run_days, 0)

        daily_total = df_all_yearly["SYW02030401"] + df_all_yearly["SYW02030402"]
        df_all_yearly["SYW020305"] = np.where(scale != 0, daily_total / scale, 0)

        # 吨泥能源指标
        df_all_yearly["SYW020502"] = np.where(total_qty > 0, df_all_yearly["SYW020501"] / total_qty, 0)
        df_all_yearly["SYW020504"] = np.where(total_qty > 0, df_all_yearly["SYW020503"] / total_qty, 0)
        df_all_yearly["SYW020512"] = np.where(total_qty > 0, df_all_yearly["SYW020505"] * 10000 / total_qty, 0)
        df_all_yearly["SYW020514"] = np.where(df_all_yearly["SYW0203020201"] > 0,
                                              df_all_yearly["SYW020513"] / df_all_yearly["SYW0203020201"], 0)

        # 补齐缺失科目
        for acc in self.all_accounts_list:
            if acc not in df_all_yearly.columns:
                df_all_yearly[acc] = 0

        save_cols = ["Entity", "Year", "Scenario", "Version", "Material", "Department",
                     "Tax", "Misc1", "Misc2", "Misc3", "Format", "Project_Type", "PM_Chars",
                     "Measure", "Period"] + self.all_accounts_list

        cube.save_unpivot(df_all_yearly[save_cols], unpivot_dim="Account")

        print("污泥全年合计（Noperiod）计算完成（吨泥指标已全年重新计算）")

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
        agg_dict = {acc: 'sum' for acc in sum_accounts}
        agg_dict.update({acc: 'mean' for acc in avg_accounts})

        # 执行求和/平均聚合
        df_sum_avg = df_source.groupby("Entity", as_index=False).agg(agg_dict)

        # 状态类科目：取指定月份
        if state_accounts:
            df_specific = df_source[df_source["Period"] == take_month]
            if not df_specific.empty:
                df_state = df_specific.groupby("Entity", as_index=False).agg(
                    {acc: 'first' for acc in state_accounts}
                )
                df_sum_avg = df_sum_avg.merge(df_state, on="Entity", how="left")
                # 填充缺失状态类为 0
                for acc in state_accounts:
                    df_sum_avg[acc].fillna(0, inplace=True)

        # 填充固定维度（用 self 值）
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
        print("污泥基础生产数据计算流程开始".center(70, "="))

        self.clear_data(cube)
        df_raw = self.query_data(cube)

        self.calc_actual_monthly(df_raw, forecast_val, cube)
        self.calc_budget_monthly(df_raw, cube)

        self.calc_noperiod_all_scenarios(cube, forecast_val)

        print("污泥基础生产数据计算全部完成".center(70, "="))

def main(p1, p2):
    start = time.time()
    cube = get_cube()
    forecast_val = get_forecast_val()

    sludge = SludgeBasic(p2)
    sludge.run_all(cube, forecast_val)

    print(f"总耗时: {time.time() - start:.2f} 秒")


if __name__ == '__main__':
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
