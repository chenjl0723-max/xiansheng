# 基础生产数据（批量）
# -*- coding: utf-8 -*-
# @Time : 2023/8/1 14:36
# @Author : LiYuXin
# @FileName: basic_production_data.py
# @Software: PyCharm
import asyncio
import time
import numpy as np
import pandas as pd
import warnings
from deepfos.element.finmodel import FinancialCube, AsyncFinancialCube
from deepfos.element.variable import Variable, AsyncVariable
from deepfos.element.dimension import Dimension

warnings.filterwarnings("ignore")


def get_cube():
    # 实例化财务模型
    cube = FinancialCube("WS_cube")
    return cube


def get_val():
    # 获取变量
    variable = Variable(element_name="Variable")
    val = variable.get_value("Forcast")
    return val


# A01 运营规模（万吨/d）全年计算封装函数
def calc_a01(df, year_a01, scenario_a01, mouth, tmp):
    # A01计算
    df_a01 = df.loc[(df["Year"] == year_a01) & (df["Scenario"] == scenario_a01) & (df["Period"] == mouth)]
    # df_a01.drop(columns=["A02", "A05", "A0801", "A0802", "A1001", "A1002"], inplace=True)
    df_a01.drop(columns=["YW0202", "YW0205", "YW020801", "YW020802", "YW021001", "YW021002"], inplace=True)
    # 用重命名列代替赋值
    # df_a01 = pd.merge(df_re, df_a01, how="inner", on=tmp)
    # df_a01.drop(columns="A01_x", inplace=True)
    # df_a01.rename(columns={"A01_y": "A01"}, inplace=True)
    df_a01['Period'] = "Noperiod"
    df_result = df_a01.copy(deep=True)
    return df_result


class Basic(object):

    def __init__(self, p2):
        # 页面维度 Year Entity Version Material Allocation Tax Department misc1 misc2 Account Scenario Measure Period
        self.year = p2["Year_wb1"]
        self.entity = p2["Entity_wb1"]
        self.version = p2["Version_wb1"]
        # self.material = p2["Material_wb1"]
        self.material = "Nomaterial"
        # self.allocation = p2["Allocation_wb1"]
        self.allocation = "Original"
        self.tax = p2["Tax_wb1"]
        self.department = p2["Department_wb1"]
        # self.misc1 = p2["Misc1_wb1"]
        self.misc1 = "Nomisc1"
        # self.misc2 = p2["Misc2_wb1"]
        self.misc2 = "Nomisc2"
        # Account = p2['Account']
        # Scenario = p2['Scenario']
        # Measure = p2['Measure']
        # Period = p2['Period']
        self.last_year = str(int(self.year) - 1)
        self.two_years_ago = str(int(self.year) - 2)

    def del_cube(self, cube):
        # 第一部分：清数
        pov_clear = {
            "Entity": self.entity,
            "Version": self.version,
            "Material": self.material,
            "Department": self.department,
            "Allocation": self.allocation,
            "Tax": self.tax,
            "Misc1": self.misc1,
            "Misc2": self.misc2,
        }
        l_exp = []
        # 这几个科目 清每个月的 + 调整的 + 全年的
        # l_exp.append(
        #     {
        #         # "Account": "A05;A03;A0801;A0802;A1001;A1002",
        #         "Account": "YW0205;YW0203;YW020801;YW020802;YW021001;YW021002",
        #         "Year": self.year,
        #         "Scenario": "Budget",
        #         "Period": "Remove(Base(TotalPeriod,0),Adjust);Noperiod",
        #         "Measure": "Nomeasure"
        #     }
        # )
        # l_exp.append(
        #     {
        #         "Account": "YW0205;YW0203;YW020801;YW020802;YW021001;YW021002",
        #         "Year": self.last_year,
        #         "Scenario": "Forecast",
        #         "Period": "Base(Oct,0)",
        #         "Measure": "Nomeasure"
        #     }
        # )
        # exp_clear_3 = {
        #     "Account": "A01;A02;A03;A04;A05;A06;A0801;A0802;A1001;A1002",
        #     "Year": year,
        #     "Scenario": "Budget",
        #     "Period": "Noperiod"
        # }
        # 这几个科目清全年的
        # l_exp.append(
        #     {
        #         # "Account": "A01;A02;A04;A06",
        #         "Account": "YW0201;YW0202;YW0204;YW0206",
        #         "Year": self.year,
        #         "Scenario": "Budget",
        #         "Period": "Noperiod",
        #         "Measure": "Nomeasure"
        #     }
        # )
        # 这几个科目清全年的
        # l_exp.append(
        #     {
        #         # "Account": "A01;A02;A03;A04;A05;A06;A0801;A0802;A1001;A1002",
        #         "Account": "YW0201;YW0202;YW0203;YW0204;YW0205;YW0206;YW020801;YW020802;YW021001;YW021002",
        #         "Year": self.last_year,
        #         "Scenario": "Actual",
        #         "Period": "Noperiod",
        #         "Measure": "Nomeasure"
        #     }
        # )
        # 这几个科目清全年的
        # l_exp.append(
        #     {
        #         # "Account": "A03;A05;A1001;A1002",
        #         "Account": "YW0203;YW0205;YW021001;YW021002",
        #         # "Year": self.last_year,
        #         "Year": self.year,
        #         "Scenario": "New",
        #         "Period": "Noperiod",
        #         "Measure": "Nomeasure"
        #     }
        # )
        # 这几个科目清全年的
        l_exp.append(
            {
                # "Account": "A11",
                "Account": "YW0211",
                "Year": self.last_year,
                "Scenario": "Actual",
                "Period": "Noperiod",
                "Measure": "COD;BOD5;SS;NH3N;TN;TP;BC"
            }
        )
        l_exp.append(
            {
                # "Account": "A11",
                "Account": "YW0211",
                "Year": self.year,
                "Scenario": "Budget",
                "Period": "Noperiod",
                "Measure": "COD;BOD5;SS;NH3N;TN;TP;BC"
            }
        )
        l_exp.append(
            {
                # "Account": "A12",
                "Account": "YW0212",
                "Year": self.last_year,
                "Scenario": "Actual",
                "Period": "Noperiod",
                "Measure": "COD;BOD5;SS;NH3N;TN;TP;ETP"
            }
        )
        l_exp.append(
            {
                # "Account": "A12",
                "Account": "YW0212",
                "Year": self.year,
                "Scenario": "Budget",
                "Period": "Noperiod",
                "Measure": "COD;BOD5;SS;NH3N;TN;TP;ETP"
            }
        )
        l_exp.append(
            {
                # "Account": "A13",
                "Account": "YW0213",
                "Year": self.last_year,
                "Scenario": "Actual",
                "Period": "Noperiod",
                "Measure": "CT"
            }
        )
        l_exp.append(
            {
                # "Account": "A13",
                "Account": "YW0213",
                "Year": self.year,
                "Scenario": "Budget",
                "Period": "Noperiod",
                "Measure": "CT"
            }
        )
        for i in l_exp:
            i = i.update(pov_clear)

        # 划定取数范围
        # expression = (
        #         "Entity{%s}->Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->Tax{%s}->Misc1{%s}->Misc2{%s}->"
        #         "Year{%s;%s}->Account{YW0202;YW0204;YW0201;YW020801;YW020901;YW020802;YW020902;YW0206;YW020701;YW020702}->Scenario{Forecast;New;Budget}->"
        #         "Measure{Nomeasure}->Period{Base(Oct,0);Noperiod;Remove(Base(TotalPeriod,0),Adjust)}"
        #         % (self.entity, self.version, self.material, self.department, self.allocation, self.tax,
        #            self.misc1, self.misc2, self.year, self.last_year)
        # )

        # 模型中清数,取数  按照科目维度
        def cube_deal():
            bewg_cube = FinancialCube("WS_cube")
            results = []
            for exp in l_exp:
                result = bewg_cube.delete(exp)
                results.append(result)
            # query_result = bewg_cube.query(expression, compact=False, pivot_dim="Account")
            # results.append(query_result)
            return results

        result = cube_deal()

        print('--------- 第一部分结束 ----------')
        return result

    def calc_wet_mud_yield(self, cube, result):
        # 第二部分：按顺序计算合计实际处理水量、水力负荷、湿泥产量（10-12月、批复新增、预算1-12）

        # 模型中取数
        df = result[11]
        # print(df.columns)
        # for i in ["A02", "A04", "A01", "A0901", "A0902", "A06", "A0701", "A0702", "A0801", "A0802"]:
        for i in ["YW0202", "YW0204", "YW0201", "YW020901", "YW020902", "YW0206", "YW020701", "YW020702", "YW020801",
                  "YW020802"]:
            if i not in df.columns:
                df[i] = np.nan
        # df切片 切1.去年预测场景(10-12) + 2.去年批复新增场景(Noperiod) + 3.预算场景（1-12）
        # drop不需要计算的列
        df_forecast = df.loc[
            (df["Year"] == self.last_year)
            & (df["Scenario"] == "Forecast")
            & ((df["Period"] == "10") | (df["Period"] == "11") | (df["Period"] == "12"))
            ]
        # df_forecast.drop(columns=["A0801", "A0802"], inplace=True)
        df_forecast.drop(columns=["YW020801", "YW020802"], inplace=True)
        df_new = df.loc[
            # (df["Year"] == self.last_year)
            (df["Year"] == self.year)
            & (df["Scenario"] == "New")
            & (df["Period"] == "Noperiod")
            ]
        # df_new.drop(columns=["A06", "A0701", "A0702"], inplace=True)
        df_new.drop(columns=["YW0206", "YW020701", "YW020702"], inplace=True)
        df_budget = df.loc[
            (df["Year"] == self.year)
            & (df["Scenario"] == "Budget")
            & (df["Period"].isin(["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]))
            ]
        df_budget.drop(columns=["YW020801", "YW020802"], inplace=True)
        # 预测 + 预算混合计算
        l_df = [df_forecast, df_budget]
        for i in l_df:
            if not i.empty:
                # for j in ["A02", "A04", "A01", "A0901", "A0902", "A06", "A0701", "A0702"]:
                for j in ["YW0202", "YW0204", "YW0201", "YW020901", "YW020902", "YW0206", "YW020701", "YW020702"]:
                    if j not in i.columns:
                        i[j] = 0
                # 计算逻辑
                i.loc[:, "YW0205"] = i.apply(lambda x: x["YW0202"] * x["YW0204"], axis=1)
                i.loc[:, "YW0203"] = i.apply(
                    lambda x: x["YW0205"] / (x["YW0202"] * x["YW0201"])
                    if x["YW0202"] != 0 and x["YW0201"] != 0
                    else 0,
                    axis=1,
                )
                i.loc[:, "YW020801"] = i.apply(lambda x: x["YW0206"] * x["YW0205"] * x["YW020701"], axis=1)
                i.loc[:, "YW020802"] = i.apply(lambda x: x["YW0206"] * x["YW0205"] * x["YW020702"], axis=1)
                i.loc[:, "YW021001"] = i.apply(
                    lambda x: x["YW020801"] / (1 - x["YW020901"]) if x["YW020901"] != 1 else 0, axis=1)
                i.loc[:, "YW021002"] = i.apply(
                    lambda x: x["YW020802"] / (1 - x["YW020902"]) if x["YW020902"] != 1 else 0, axis=1)
                # 删除多余的列
                i.drop(columns=["YW0202", "YW0204", "YW0201", "YW020901", "YW020902", "YW0206", "YW020701", "YW020702"],
                       inplace=True)
            else:
                i = pd.DataFrame()

        if not df_new.empty:
            # for j in ["A02", "A04", "A01", "A0801", "A0901", "A0802", "A0902"]:
            for j in ["YW0202", "YW0204", "YW0201", "YW020801", "YW020901", "YW020802", "YW020902"]:
                if j not in df_new.columns:
                    df_new[j] = 0
            # 计算逻辑
            df_new.loc[:, "YW0205"] = df_new.apply(lambda x: x["YW0202"] * x["YW0204"], axis=1)
            df_new.loc[:, "YW0203"] = df_new.apply(
                lambda x: x["YW0205"] / (x["YW0202"] * x["YW0201"])
                if x["YW0202"] != 0 and x["YW0201"] != 0
                else 0,
                axis=1,
            )
            df_new.loc[:, "YW021001"] = df_new.apply(
                lambda x: x["YW020801"] / (1 - x["YW020901"]) if x["YW020901"] != 1 else 0,
                axis=1)
            df_new.loc[:, "YW021002"] = df_new.apply(
                lambda x: x["YW020802"] / (1 - x["YW020902"]) if x["YW020902"] != 1 else 0,
                axis=1)
            # 删除多余的列
            df_new.drop(columns=["YW0202", "YW0204", "YW0201", "YW020901", "YW020902", "YW020801", "YW020802"],
                        inplace=True)
        else:
            df_new = pd.DataFrame()

        df_forecast = l_df[0].copy(deep=True)
        df_budget = l_df[1].copy(deep=True)
        df_fc_bg = pd.concat([df_forecast, df_budget], axis=0)

        # 存入数据
        cube.save_unpivot(df_fc_bg, unpivot_dim="Account")
        cube.save_unpivot(df_new, unpivot_dim="Account")
        # print(df_fc_bg)
        # print(df_new)
        print('--------- 第二部分结束 ----------')

    def calc_noperiod(self, cube, val):
        # 第三部分：计算全年（按照科目顺序执行）
        exp = (
                "Entity{%s}->Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->Tax{%s}->Misc1{%s}->Misc2{%s}->"
                "Year{%s;%s}->Account{YW0201;YW0202;YW0205;YW020801;YW020802;YW021001;YW021002}->Scenario{Budget;Actual;Forecast}->"
                "Measure{Nomeasure}->Period{TotalPeriod;Noperiod;1;2;3;4;5;6;7;8;9;10;11;12}"
                % (self.entity, self.version, self.material, self.department, self.allocation, self.tax,
                   self.misc1, self.misc2, self.year, self.last_year)
        )
        # 模型中取数
        df = cube.query(expression=exp, compact=False, pivot_dim="Account")
        # print(df.columns)

        if not df.empty:
            # for j in ["A01", "A02", "A05", "A0801", "A1001", "A0802", "A1002"]:
            for j in ["YW0201", "YW0202", "YW0205", "YW020801", "YW021001", "YW020802", "YW021002"]:
                if j not in df.columns:
                    df[j] = 0
        else:
            return

        # 计算A01 运营规模（万吨/d） 全年合计
        tmp = ["Scenario", "Year", "Entity", "Version", "Material", "Department", "Allocation",
               "Tax", "Misc1", "Misc2", "Measure"]
        df_budget = calc_a01(df=df, year_a01=self.year, scenario_a01="Budget", mouth="1", tmp=tmp)

        # 计算A02,A05,A0801,A0802,A1001,A1002     预算全年
        df_other = df.loc[
            (df["Year"] == self.year)
            & (df["Scenario"] == "Budget")
            & (df["Period"] == "TotalPeriod")
            ]
        df_other.drop(columns=["YW0201"], inplace=True)

        if not df_budget.empty:
            df_other = pd.merge(df_budget, df_other, how="inner", on=tmp)
            df_other.drop(columns=["Period_y"], inplace=True)
            df_other.rename(columns={"Period_x": "Period"}, inplace=True)
        else:
            df_other['Period'] = "Noperiod"

        df_budget = df_other.copy(deep=True)

        # 计算A02,A05,A0801,A0802,A1001,A1002    实际 + 预测 全年
        df_other_sepmtd = df.loc[
            (df["Year"] == self.last_year)
            & (df["Scenario"] == "Actual")
            & (df['Period'].isin(['1', '2', '3', '4', '5', '6', '7', '8', '9']))
            ]
        df_other_sepmtd.drop(columns=["YW0201", "Scenario"], inplace=True)
        df_other_acoct = df.loc[
            (df["Year"] == self.last_year)
            & (df["Scenario"] == "Actual")
            & (df["Period"].isin(['10', '11', '12']))
            ]
        df_other_acoct.drop(columns=["YW0201", "Scenario"], inplace=True)
        df_other_fcoct = df.loc[
            (df["Year"] == self.last_year)
            & (df["Scenario"] == "Forecast")
            & (df["Period"].isin(['10', '11', '12']))
            ]
        df_other_fcoct.drop(columns=["YW0201", "Scenario"], inplace=True)
        # 根据变量的值分情况计算   全年
        if val == "Forecast":
            df_other = pd.concat([df_other_sepmtd, df_other_fcoct], axis=0).drop(columns=["Period"], inplace=False)
            # 计算A01     默认等于本年12月份的数据
            df_actual = calc_a01(df=df, year_a01=self.last_year, scenario_a01="Forecast", mouth="12",
                                 tmp=tmp)
        else:
            df_other = pd.concat([df_other_sepmtd, df_other_acoct], axis=0).drop(columns=["Period"], inplace=False)
            # 计算A01
            df_actual = calc_a01(df=df, year_a01=self.last_year, scenario_a01="Actual", mouth="12",
                                 tmp=tmp)
        # 分组聚合，重置索引
        # group = ["Year", "Entity", "Version", "Material", "Department", "Allocation", "Tax", "Misc1", "Misc2", "Measure"]
        # group = ["Year"]
        group = ["Year", "Entity", "Version", "Material", "Department", "Allocation", "Tax", "Misc1", "Misc2",
                 "Measure"]
        # 检查group变量类型   需要为列表类型,元组类型会报错
        # print(type(group))  # 确保输出：<class 'list'>
        # print("所有列名:")
        # print(df_other.columns.tolist())
        # print("数据基本信息:")
        # df_other.info()
        # print(df_other)

        df_other_sum = df_other.groupby(
            group,
            as_index=False,
        )["YW0202", "YW0205", "YW020801", "YW020802", "YW021001", "YW021002"].sum()
        # print(df_other_sum)

        if not df_actual.empty:
            df_other = pd.merge(df_actual, df_other_sum, how="inner", on=group)
            df_other['Scenario'] = "Actual"
        else:
            df_other = df_other_sum
            df_other['Period'] = "Noperiod"
            df_other['Scenario'] = "Actual"

        df_actual = df_other.copy(deep=True)

        # 计算A03，A04，A05
        l = [df_budget, df_actual]
        for i in l:
            if not i.empty:
                # for j in ["A01", "A02", "A05", "A0801", "A1001", "A0802", "A1002"]:
                for j in ["YW0201", "YW0202", "YW0205", "YW020801", "YW021001", "YW020802", "YW021002"]:
                    if j not in i.columns:
                        i[j] = 0
                # 计算逻辑
                i.loc[:, "YW0204"] = i.apply(lambda x: x["YW0205"] / x["YW0202"] if x["YW0202"] != 0 else 0, axis=1)
                i.loc[:, "YW0203"] = i.apply(
                    lambda x: x["YW0205"] / (x["YW0202"] * x["YW0201"])
                    if x["YW0202"] != 0 and x["YW0201"] != 0
                    else 0,
                    axis=1,
                )
                i["YW020801"] = i["YW020801"].fillna(0)
                i["YW020802"] = i["YW020802"].fillna(0)
                i.loc[:, "YW0206"] = i.apply(
                    lambda x: (x["YW020801"] + x["YW020802"]) / x["YW0205"] if x["YW0205"] != 0 else 0,
                    axis=1)
            else:
                # print('empty')
                i = pd.DataFrame()

        df_budget = l[0].copy(deep=True)
        df_actual = l[1].copy(deep=True)
        df_bd_ac = pd.concat([df_budget, df_actual], axis=0)
        # 存入数据
        cube.save_unpivot(df_bd_ac, unpivot_dim="Account")
        # print(df_bd_ac)
        print('--------- 第三部分结束 ----------')

    def calc_compare(self, cube):
        # 查询维度中父级节点
        entity_dim = Dimension("Entity")
        entity_parent = entity_dim.query(self.entity, fields=['parent_name'], as_model=False)
        df_dim = pd.DataFrame(data=entity_parent)
        parent_name = df_dim.loc[0, "parent_name"]

        exp = (
                "Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->Tax{Tax}->Misc1{%s}->Misc2{%s}->Year{%s}->"
                "Account{A04;A300102}->Scenario{Budget}->Entity{%s}->Measure{Nomeasure;Expenses}->Period{Noperiod}"
                % (self.version, self.material, self.department, self.allocation,
                   self.misc1, self.misc2, self.year, parent_name)
        )
        # 模型中取数
        df = cube.query(expression=exp, compact=False)
        # df切片
        df_a300102 = df.loc[(df["Account"] == "A300102")
                            & (df["Measure"] == "Expenses")]
        df_a04 = df.loc[(df["Account"] == "A04")
                        & (df["Measure"] == "Nomeasure")]

        if not (df_a04.empty or df_a300102.empty):
            if float(df_a04["data"]) > float(df_a300102["data"]):
                result = "是"
                entity_dim.update(parent_name, ud13=result)
            else:
                result = "否"
                entity_dim.update(parent_name, ud13=result)
            entity_dim.save()
            print("已写入维度ud13")
        else:
            print("存在A04或A300102值为空，无法比较")

    def calc_water_quality(self, cube, val):
        print('--------- 第六部分：计算水质全年（简单平均法） 开始 -----------')

        # 1. 取数表达式（只取有浓度指标的那些 Measure）
        exp = (
                "Entity{%s}->Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->Misc1{%s}->Misc2{%s}->"
                "Tax{Tax}->Year{%s;%s}->Account{YW0211;YW0212;YW0213}->"
                "Measure{COD;BOD5;SS;NH3N;TN;TP;BC;ETP;CT}->"
                "Scenario{Budget;Actual;Forecast}->Period{1;2;3;4;5;6;7;8;9;10;11;12}"
                % (self.entity, self.version, self.material, self.department, self.allocation,
                   self.misc1, self.misc2, self.year, self.last_year)
        )

        df = cube.query(expression=exp, compact=False)

        if df.empty:
            print("水质月度数据为空，无需计算全年平均")
            return

        # 2. 根据 val 决定实际年用 Actual 还是 Forecast（10-12月）
        if val == "Forecast":
            # 去年1-9月 Actual + 去年10-12月 Forecast → 拼成“实际年”
            df_actual = df[
                ((df["Year"] == self.last_year) & (df["Scenario"] == "Actual") & (
                    df["Period"].isin(["1", "2", "3", "4", "5", "6", "7", "8", "9"]))) |
                ((df["Year"] == self.last_year) & (df["Scenario"] == "Forecast") & (
                    df["Period"].isin(["10", "11", "12"])))
                ].copy()
            df_actual["Year"] = self.last_year
            df_actual["Scenario"] = "Actual"
        else:
            # 全部用 Actual（1-12月）
            df_actual = df[
                (df["Year"] == self.last_year) & (df["Scenario"] == "Actual")
                ].copy()

        # 预算年：直接取本年 Budget 的 1-12 月
        df_budget = df[
            (df["Year"] == self.year) & (df["Scenario"] == "Budget")
            ].copy()

        # 合并预算 + 实际（预测）
        df_all = pd.concat([df_budget, df_actual], ignore_index=True)

        # 3. 简单平均：按 Year/Scenario/Account/Measure 组内对 12 个月取均值
        group_cols = ["Year", "Scenario", "Entity", "Version", "Material", "Department",
                      "Allocation", "Tax", "Misc1", "Misc2", "Account", "Measure"]

        df_result = df_all.groupby(group_cols, as_index=False)["data"].mean()

        # 4. 补充必要字段 + Period 改为 Noperiod
        df_result["Period"] = "Noperiod"
        df_result["Measure"] = df_result["Measure"]  # 已经是正确的 Measure

        print("水质全年简单平均计算完成，结果预览：")
        print(df_result[["Year", "Scenario", "Account", "Measure", "data"]].head(20))

        # 5. 存回模型
        cube.save(df_result)

        print('--------- 第六部分：计算水质全年（简单平均法） 结束 -----------')

        # return


def water_calc(p2, cube):
    print(1)
    Entity = p2['Entity_wb1']
    Year = p2['Year_wb1']

    # material_expr = f"Material{{Remove(IDescendant(MQ,0),{','.join(project_materials)})}}"
    exp = f"Entity{{{Entity}}}->Year{{{Year}}}->Account{{YW0201;YW0203;YW0204;YW0205;YW0206}}->Tax{{Tax}}->Period{{1;2;3;4;5;6;7;8;9;10;11;12;Noperiod}}->Measure{{Nomeasure}}->Scenario{{Budget}}->Version{{Y1}}"
    exp_lastyear = f"Entity{{{Entity}}}->Year{{{str(int(Year) - 1)}}}->Account{{YW0201;YW0203;YW0204;YW0205;YW0206}}->Tax{{Tax}}->Period{{1;2;3;4;5;6;7;8;9;10;11;12;Noperiod}}->Measure{{Nomeasure}}->Scenario{{Forecast;Actual}}->Version{{Y1}}"
    df1 = cube.query(exp, compact=False)
    df2 = cube.query(exp_lastyear, compact=False)
    df = pd.concat([df1, df2], ignore_index=True)
    df['Tax'] = 'Notax'
    print(1)
    delete_exp = f"Entity{{{Entity}}}->Year{{{Year}}}->Account{{YW0201;YW0203;YW0204;YW0205}}->Tax{{Notax}}->Period{{1;2;3;4;5;6;7;8;9;10;11;12;Noperiod}}->Measure{{Nomeasure}}->Scenario{{Budget}}->Version{{Y1}}"
    delete_exp_lastyear = f"Entity{{{Entity}}}->Year{{{str(int(Year) - 1)}}}->Account{{YW0201;YW0203;YW0204;YW0205}}->Tax{{Notax}}->Period{{1;2;3;4;5;6;7;8;9;10;11;12;Noperiod}}->Measure{{Nomeasure}}->Scenario{{Forecast;Actual}}->Version{{Y1}}"
    cube.delete(delete_exp)
    cube.delete(delete_exp_lastyear)
    cube.save(df)


def YW0206_calc(p2, cube):
    print(1)
    Entity = p2['Entity_wb1']
    Year = p2['Year_wb1']

    # material_expr = f"Material{{Remove(IDescendant(MQ,0),{','.join(project_materials)})}}"
    exp = f"Entity{{{Entity}}}->Year{{{Year}}}->Account{{YW0206}}->Tax{{Tax}}->Period{{Noperiod}}->Measure{{Unit}}->Scenario{{Budget}}->Version{{Y1}}"
    exp_lastyear = f"Entity{{{Entity}}}->Year{{{str(int(Year) - 1)}}}->Account{{YW0206}}->Tax{{Tax}}->Period{{Noperiod}}->Measure{{Unit}}->Scenario{{Forecast;Actual}}->Version{{Y1}}"
    df1 = cube.query(exp, compact=False)
    df2 = cube.query(exp_lastyear, compact=False)
    df = pd.concat([df1, df2], ignore_index=True)
    df['Tax'] = 'Notax'
    print(1)
    delete_exp = f"Entity{{{Entity}}}->Year{{{Year}}}->Account{{YW0206}}->Tax{{Notax}}->Period{{Noperiod}}->Measure{{Unit}}->Scenario{{Budget}}->Version{{Y1}}"
    delete_exp_lastyear = f"Entity{{{Entity}}}->Year{{{str(int(Year) - 1)}}}->Account{{YW0206}}->Tax{{Notax}}->Period{{Noperiod}}->Measure{{Unit}}->Scenario{{Forecast;Actual}}->Version{{Y1}}"
    cube.delete(delete_exp)
    cube.delete(delete_exp_lastyear)
    cube.save(df)


def main(p1, p2):
    # p2 = {'Year': '2023', 'Entity': 'XN13001_01', 'Version': 'Y1', 'Material': 'Nomaterial', 'Allocation': 'Original', 'Tax': 'Tax', 'Department': 'Operation', 'misc1': 'Nomisc1', 'misc2': 'Nomisc2', 'sheetName': '基础生产数据-水量、泥量', 'sheetId': 'SHTb4ed3d626a2d', 'elementName': 'ProductData', 'folderId': 'DIRfd5a95b6f89c'}
    begin = time.time()
    cube = get_cube()
    val = get_val()
    # 第一部分：清数及取第二部分的数据  20250729修改清数逻辑（只保留水质信息的清数）
    result = Basic(p2).del_cube(cube=cube)
    # 第二部分：按顺序计算合计实际处理水量、水力负荷、湿泥产量（10-12月、批复新增、预算1-12）
    # Basic(p2).calc_wet_mud_yield(cube=cube, result=result)
    # 第三部分：计算全年（按照科目顺序执行）
    Basic(p2).calc_noperiod(cube=cube, val=val)
    print(time.time() - begin)
    water_calc(p2, cube)
    # 第四部分：计算审核指标：实际处理水量、干泥量增加额、增长率
    # from Python.biz.phaseII.newly.calc_audit_indicators import main as main_audit
    # main_audit(p1, p2, account_list=["A05", "A08"], year=p2["Year"],
    #            scenario_save="Budget", scenario_calcyear="Budget", scenario_lastyear="Actual",
    #            measure="Nomeasure", entity="IDescendant(1,0)", tax=p2["Tax"])
    # main_audit(p1, p2, account_list=["A08"], year=p2["Year"], year_save=str(int(p2["Year"]) - 1),
    #           scenario_save="Combinaion", scenario_calcyear="Budget", scenario_lastyear="Combinaion",
    #           measure="Nomeasure", entity="IDescendant(1,0)", tax=p2["Tax"])
    audit = time.time()
    from budget.Python.biz.basic_produce_data.new_unit002 import main as main_audit
    main_audit(p1, p2)
    print("Unit 审核：", time.time() - audit)
    YW0206_calc(p2, cube)
    # 第五部分：计算是否超保底运行(由于用户权限问题，改为前端完成)
    # from Python.biz.phaseII.newly.compare_save_dim import main as main_compare
    # main_compare(cube, p2, entity=p2["Entity"], year=p2["Year"])
    # print(time.time() - begin)

    # 第六部分：计算水质全年
    Basic(p2).calc_water_quality(cube=cube, val=val)
    print(time.time() - begin)

    # 第七部分：计算毛利毛利率
    # if p2["sheetName"] != "串行":
    #     from Python.biz.phaseII.newly.gross_margin_calc import main as main_gross
    #     main_gross(p1, p2)
    # print(time.time() - begin)
    return


if __name__ == "__main__":
    # from conf._evn import p1, p2
    from common._debug import p1

    # p2 = {'Year': '2024', 'Entity': 'XN23002_01', 'Version': 'Y1', 'Material': 'Nomaterial', 'Allocation': 'Original', 'Tax': 'Tax', 'Department': 'Operation', 'misc1': 'Nomisc1', 'misc2': 'Nomisc2', 'sheetName': '基础生产数据-水量、泥量', 'sheetId': 'SHTb4ed3d626a2d', 'elementName': 'ProductData', 'folderId': 'DIRfd5a95b6f89c'}
    p2 = {'Year_wb1': '2025', 'Entity_wb1': 'Base(1,0)', 'Version_wb1': 'Y1', 'Material_wb1': 'Nomaterial',
          'Allocation_wb1': 'Original',
          'Tax_wb1': 'Tax', 'Department_wb1': 'Operation', 'Misc1_wb1': 'Nomisc1', 'Misc2_wb1': 'Nomisc2',
          'sheetName': '基础生产数据-水量、泥量', 'sheetId': 'SHTb4ed3d626a2d', 'elementName': 'ProductData',
          'folderId': 'DIRe437ed8262b4'}

    main(p1, p2)


