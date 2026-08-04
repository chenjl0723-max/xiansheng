# 基础生产数据（批量）
# -*- coding: utf-8 -*-
# @Time : 2025/12/12 14:36
# @Author : Chenjinglei
# @FileName: town_water_basic.py
# @Software: PyCharm


import asyncio
import time
import numpy as np
import pandas as pd
import warnings
from deepfos.element.finmodel import FinancialCube  # Assuming this is the model class
from deepfos.element.variable import Variable
from deepfos.element.dimension import Dimension

warnings.filterwarnings("ignore")

def get_cube():
    cube = FinancialCube("S_Cube")  # New cube name for village sewage
    return cube

def get_forecast_val():
    variable = Variable(element_name="Variable")
    val = variable.get_value("Forcast")
    return val

class VillageBasic(object):
    def __init__(self, p2):
        self.year = p2["Year_wb1"]
        self.entity = p2["Entity_wb1"]
        self.version = p2["Version_wb1"]
        self.material = "Nomaterial"
        # self.allocation = "Original"
        self.tax = p2["Tax_wb1"]
        self.department = p2["Department_wb1"]
        self.misc1 = "Nomisc1"
        self.misc2 = "Nomisc2"
        self.misc3 = "Nomisc3"
        self.format = "NoFormat"
        self.project_type = "NoProject_Type"
        self.pm_chars = "NoPM_Chars"

        self.last_year = str(int(self.year) - 1)

        # ==================== 科目清单（全部用列表定义） ====================
        # 1.所有参与本表计算的科目（用于删Noperiod、查询等）
        self.all_accounts_list = [
            "SYW020101",  # 运行天数
            "SYW020102",  # 运营规模
            "SYW020103",  # 收费水量（备用）
            "SYW020104",  # 日均实际处理水量
            "SYW020105",  # 合计实际处理水量
            "SYW020106",  # 水力负荷
            "SYW020107",  # 产泥系数
            "SYW020108",  # 干泥量
            "SYW020109",  # 污泥含水率
            "SYW020110",  # 湿泥产量
            "SYW020201",  # 保底水量
            "SYW020202",  # 商运站点数（总）
            "SYW02020301",  # 分散式站点覆盖户数
            "SYW02020302",  # 纳管覆盖户数
            "SYW02011101",  # 污水管网长度
            "SYW02011102",  # 雨水管网长度
            "SYW02011201",  # 污水泵站数量
            "SYW02011202",  # 雨水泵站数量
            "SYW02011203",  # 其它泵站数量
            "SYW020501",  # 自来水用量
            "SYW020503",  # 中水用量
            "SYW020505",  # 电度电量合计（万kWh）
            "SYW020511",  # 吨水电度用电量
            "SYW020513",  # 天然气用量
        ]
        self.ALL_ACCOUNTS = ";".join(self.all_accounts_list)

        # 2.实际数需要计算的科目
        self.calc_only_accounts_actual = [
            "SYW020104",  # 日均实际处理水量
            # "SYW020105",  # 合计实际处理水量
            "SYW020106",  # 水力负荷
            "SYW020108",  # 干泥量
            "SYW020110",  # 湿泥产量
            # "SYW020505",  # 电度电量合计
            "SYW020511",  # 吨水电度用电量
        ]
        self.CALC_ACTUAL_STR = ";".join(self.calc_only_accounts_actual)

        # 3.预算、预测数需要计算的科目
        self.calc_only_accounts_forecast_budget = [
            # "SYW020104",  # 日均实际处理水量
            "SYW020105",   # 合计实际处理水量
            "SYW020106",  # 水力负荷
            "SYW020108",  # 干泥量
            "SYW020110",  # 湿泥产量
            "SYW020505",  # 电度电量合计
            # "SYW020511",  # 吨水电度用电量
        ]
        self.CALC_BUDGET_FORECAST_STR = ";".join(self.calc_only_accounts_forecast_budget)




    def clear_data(self, cube):
        """
        村镇污水专用精准清数逻辑（改进版）：
        1. 所有科目的 Noperiod（全年）必须100%删除重新计算
        2. 手工录入科目的 月度数据 必须100%保留
        3. 计算科目的 月度数据 也删除（避免残留），且将Actual和Forecast的月度删除分开处理
        """
        pov = {
            "Entity": self.entity,
            "Version": self.version,
            "Material": self.material,
            "Department": self.department,
            "Tax": self.tax,
            "Misc1": self.misc1,
            "Misc2": self.misc2,
            "Misc3": self.misc3,
            "Format": self.format,
            "Project_Type": self.project_type,
            "PM_Chars": self.pm_chars
        }

        delete_exps = []

        # =============== ① 所有科目的 Noperiod 必须全部删除（核心！） ===============
        delete_exps.append({
            "Year": f"{self.year}",
            "Scenario": "Budget",
            "Period": "Noperiod",
            "Account": self.all_accounts_list,
            "Measure": "Expenses"
        })

        delete_exps.append({
            "Year": f"{self.last_year}",
            "Scenario": "Actual",
            "Period": "Noperiod",
            "Account": self.all_accounts_list,
            "Measure": "Expenses"
        })

        # Budget 月度 (本年)
        delete_exps.append({
            "Year": self.year,
            "Scenario": "Budget",
            "Period": "1;2;3;4;5;6;7;8;9;10;11;12",
            "Account": self.calc_only_accounts_forecast_budget,
            "Measure": "Expenses"
        })

        # Actual 月度 (去年)
        delete_exps.append({
            "Year": self.last_year,
            "Scenario": "Actual",
            "Period": "1;2;3;4;5;6;7;8;9;10;11;12",
            "Account": self.calc_only_accounts_actual,
            "Measure": "Expenses"
        })

        # Forecast 月度 (去年)
        delete_exps.append({
            "Year": self.last_year,
            "Scenario": "Forecast",
            "Period": "10;11;12",
            "Account": self.calc_only_accounts_forecast_budget,
            "Measure": "Expenses"
        })

        # 执行删除
        for exp in delete_exps:
            exp.update(pov)
            cube.delete(exp)

        print("精准清数完成（改进版）：")
        print("   - 所有科目的 Noperiod 已全部清除并将重新计算")
        print("   - 用户手工录入的月度数据（如运行天数、运营规模、产泥系数、含水率等）完整保留")
        print("   - 所有计算科目月度数据已清空（Actual和Forecast分开删除），避免残留和过度删除")

    def query_data(self, cube):
        """
        查询所有需要的原始数据（包含手工录入 + 可能残留的旧计算值）
        """
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

        if df.empty:
            print("警告：查询返回空数据，请检查实体/版本/年份是否正确")
        else:
            print(f"查询完成，共获取 {len(df)} 条记录")
        return df

    def calc_actual_monthly(self, df, forecast_val, cube):
        """计算实际数月度明细（1-12月），预测场景保留为 Forecast"""
        print("开始计算实际数月度明细...")

        # 1-9月 Actual
        df_actual_monthly = df[(df["Year"] == self.last_year) & (df["Scenario"] == "Actual") &
                        (df["Period"].isin(["1", "2", "3", "4", "5", "6", "7", "8", "9"]))].copy()

        # 10-12月：根据变量选择
        if forecast_val == "Forecast":
            self.calc_forecast_monthly(df, forecast_val, cube)

        else:
            df_act_10_12 = df[(df["Year"] == self.last_year) & (df["Scenario"] == "Actual") &
                              (df["Period"].isin(["10", "11", "12"]))].copy()

            df_actual_monthly = pd.concat([df_actual_monthly, df_act_10_12], ignore_index=True)

        df_actual_monthly.fillna(0, inplace=True)

        # Actual 场景计算逻辑
        df_actual_monthly["SYW020104"] = df_actual_monthly.apply(
            lambda r: r["SYW020105"] / r["SYW020101"] if r["SYW020101"] != 0 else 0, axis=1)
        df_actual_monthly["SYW020106"] = df_actual_monthly.apply(
            lambda r: (r["SYW020104"] / r["SYW020102"]) if r["SYW020102"] != 0 else 0, axis=1)
        df_actual_monthly["SYW020108"] = df_actual_monthly["SYW020107"] * df_actual_monthly["SYW020105"]
        df_actual_monthly["SYW020110"] = df_actual_monthly.apply(
            lambda r: r["SYW020108"] / (1 - r["SYW020109"]) if r["SYW020109"] < 1 else 0, axis=1)
        df_actual_monthly["SYW020511"] = df_actual_monthly.apply(
            lambda r: r["SYW020505"] / r["SYW020105"] if r["SYW020105"] != 0 else 0, axis=1)

        dim_cols = ["Year", "Scenario", "Period", "Entity", "Version", "Material", "Department",
                    "Tax", "Misc1", "Misc2", "Misc3", "Format", "Project_Type", "PM_Chars", "Measure"]

        df_to_save = df_actual_monthly[dim_cols + self.calc_only_accounts_actual].copy()

        cube.save_unpivot(df_to_save, unpivot_dim="Account")
        print("实际数月度明细计算完成")

    def calc_forecast_monthly(self, df, forecast_val, cube):
        """单独计算 Forecast 场景 10-12月（仅当变量为 Forecast 时）"""
        if forecast_val != "Forecast":
            return

        df_forecast = df[(df["Year"] == self.last_year) & (df["Scenario"] == "Forecast") &
                         (df["Period"].isin(["10", "11", "12"]))].copy()
        if df_forecast.empty:
            return

        df_forecast.fillna(0, inplace=True)

        df_forecast["SYW020105"] = df_forecast["SYW020104"] * df_forecast["SYW020101"]
        df_forecast["SYW020106"] = df_forecast.apply(
            lambda r: (r["SYW020104"] / r["SYW020102"]) if r["SYW020102"] != 0 else 0, axis=1)
        df_forecast["SYW020108"] = df_forecast["SYW020107"] * df_forecast["SYW020105"]
        df_forecast["SYW020110"] = df_forecast.apply(
            lambda r: r["SYW020108"] / (1 - r["SYW020109"]) if r["SYW020109"] < 1 else 0, axis=1)
        df_forecast["SYW020505"] = df_forecast["SYW020511"] * df_forecast["SYW020105"]

        dim_cols = ["Year", "Scenario", "Period", "Entity", "Version", "Material", "Department",
                    "Tax", "Misc1", "Misc2", "Misc3", "Format", "Project_Type", "PM_Chars", "Measure"]

        df_to_save = df_forecast[dim_cols + self.calc_only_accounts_forecast_budget].copy()
        cube.save_unpivot(df_to_save, unpivot_dim="Account")
        print("预测数（Forecast）10-12月明细计算完成")

    def calc_budget_monthly(self, df, cube):
        """计算预算月度明细"""
        print("开始计算预算数月度明细...")

        df_budget = df[(df["Year"] == self.year) & (df["Scenario"] == "Budget") &
                       (df["Period"].isin(["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]))].copy()
        if df_budget.empty:
            print("预算月度数据为空，跳过")
            return

        df_budget.fillna(0, inplace=True)

        df_budget["SYW020105"] = df_budget["SYW020104"] * df_budget["SYW020101"]
        df_budget["SYW020106"] = df_budget.apply(
            lambda r: (r["SYW020104"] / r["SYW020102"]) if r["SYW020102"] != 0 else 0, axis=1)
        df_budget["SYW020108"] = df_budget["SYW020107"] * df_budget["SYW020105"]
        df_budget["SYW020110"] = df_budget.apply(
            lambda r: r["SYW020108"] / (1 - r["SYW020109"]) if r["SYW020109"] < 1 else 0, axis=1)
        df_budget["SYW020505"] = df_budget["SYW020511"] * df_budget["SYW020105"]

        dim_cols = ["Year", "Scenario", "Period", "Entity", "Version", "Material", "Department",
                    "Tax", "Misc1", "Misc2", "Misc3", "Format", "Project_Type", "PM_Chars", "Measure"]

        df_to_save = df_budget[dim_cols + self.calc_only_accounts_forecast_budget].copy()

        cube.save_unpivot(df_to_save, unpivot_dim="Account")
        print("预算数月度明细计算完成")

    def calc_noperiod_all_scenarios(self, cube, forecast_val):
        """
        村镇污水全年合计 Noperiod（最终版）
        - 求和科目：流量、总量等
        - 平均科目：含水率等
        - 状态类科目：运营规模等，Actual取12月，Budget取1月
        - 衍生科目：日均、水力负荷、产泥系数、电耗全年重新计算
        - 支持预测模式混合求和
        """
        print("开始计算全年合计（Noperiod）...")

        df_monthly_all = self.query_data(cube)
        df_monthly = df_monthly_all[
            df_monthly_all["Period"].isin(["1","2","3","4","5","6","7","8","9","10","11","12"])
        ].copy()

        if df_monthly.empty:
            print("无月度数据，跳过全年计算")
            return

        dim_cols = ["Year", "Scenario", "Entity", "Version", "Material", "Department",
                    "Tax", "Misc1", "Misc2", "Misc3", "Format", "Project_Type", "PM_Chars", "Measure"]

        # 求和科目
        sum_accounts = [
            "SYW020101", "SYW020103", "SYW020105", "SYW020108", "SYW020110",
            "SYW020201", "SYW020501", "SYW020503", "SYW020505", "SYW020513"
        ]

        # 平均科目（含水率）
        avg_accounts = ["SYW020109"]

        # 状态类科目（取特定月份）
        state_accounts = ["SYW020102", "SYW020202", "SYW02020301", "SYW02020302",
                          "SYW02011101", "SYW02011102", "SYW02011201", "SYW02011202", "SYW02011203"]

        result_dfs = []

        is_forecast_mode = (forecast_val == "Forecast")

        # ==================== 处理 Actual 场景全年 ====================
        if is_forecast_mode:
            df_act_1_9 = df_monthly[
                (df_monthly["Year"] == self.last_year) &
                (df_monthly["Scenario"] == "Actual") &
                (df_monthly["Period"].isin(["1","2","3","4","5","6","7","8","9"]))
            ]

            df_fc_10_12 = df_monthly[
                (df_monthly["Year"] == self.last_year) &
                (df_monthly["Scenario"] == "Forecast") &
                (df_monthly["Period"].isin(["10","11","12"]))
            ]

            df_actual_source = pd.concat([df_act_1_9, df_fc_10_12], ignore_index=True)
            take_month = "12"  # Actual 取12月
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
                df_actual_source, sum_accounts, avg_accounts, state_accounts,
                take_month, year_val, scenario_val, dim_cols
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
                "1", self.year, "Budget", dim_cols  # Budget 取1月
            )
            result_dfs.append(df_budget_yearly)

        if not result_dfs:
            print("无全年数据生成")
            return

        df_all_yearly = pd.concat(result_dfs, ignore_index=True)

        # ==================== 衍生科目全年重新计算 ====================
        df_all_yearly["SYW020104"] = np.where(df_all_yearly["SYW020101"] != 0,
                                              df_all_yearly["SYW020105"] / df_all_yearly["SYW020101"], 0)

        df_all_yearly["SYW020106"] = np.where(df_all_yearly["SYW020102"] != 0,
                                              (df_all_yearly["SYW020104"] / df_all_yearly["SYW020102"]) * 100, 0)

        df_all_yearly["SYW020107"] = np.where(df_all_yearly["SYW020105"] != 0,
                                              df_all_yearly["SYW020108"] / df_all_yearly["SYW020105"], 0)

        df_all_yearly["SYW020511"] = np.where(df_all_yearly["SYW020105"] != 0,
                                              df_all_yearly["SYW020505"]/ df_all_yearly["SYW020105"], 0)

        # 补齐缺失科目
        for acc in self.all_accounts_list:
            if acc not in df_all_yearly.columns:
                df_all_yearly[acc] = 0

        save_cols = dim_cols + ["Period"] + self.all_accounts_list
        cube.save_unpivot(df_all_yearly[save_cols], unpivot_dim="Account")

        print("村镇污水全年合计（Noperiod）计算完成")

    def _calc_one_scenario_yearly(self, df_source, sum_accounts, avg_accounts, state_accounts,
                                 take_month, year_val, scenario_val, dim_cols):
        """
        辅助函数：计算单个场景的全年合计（支持多实体）
        """
        if df_source.empty:
            return pd.DataFrame()

        # 按 Entity 分组聚合
        agg_dict = {}

        # 求和
        for acc in sum_accounts:
            agg_dict[acc] = 'sum'

        # 平均
        for acc in avg_accounts:
            agg_dict[acc] = 'mean'

        # 执行求和/平均聚合
        df_sum_avg = df_source.groupby("Entity", as_index=False).agg(agg_dict)

        # 状态类科目：取指定月份
        if state_accounts:
            df_specific = df_source[df_source["Period"] == take_month]
            if not df_specific.empty:
                df_state = df_specific.groupby("Entity", as_index=False).agg({acc: 'first' for acc in state_accounts})
                df_sum_avg = df_sum_avg.merge(df_state, on="Entity", how="left")

        # 填充状态类缺失值为 0
        for acc in state_accounts:
            if acc not in df_sum_avg.columns:
                df_sum_avg[acc] = 0

        # 填充维度
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
        print("开始执行村镇污水基础生产数据计算流程".center(60, "="))

        # 1. 清数
        self.clear_data(cube)

        # 2. 查询原始数据
        df_raw = self.query_data(cube)

        # 3. 计算实际数
        self.calc_actual_monthly(df_raw, forecast_val, cube)

        # 5. 计算预算数
        self.calc_budget_monthly(df_raw, cube)

        # 6. 计算汇总科目
        self.calc_noperiod_all_scenarios(cube, forecast_val)

        print("村镇污水基础生产数据计算全部完成".center(60, "="))

def main(p1, p2):
    start_time = time.time()
    cube = get_cube()
    forecast_val = get_forecast_val()

    village = VillageBasic(p2)
    village.run_all(cube, forecast_val)

    print(f"总耗时: {time.time() - start_time:.2f} 秒")



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
