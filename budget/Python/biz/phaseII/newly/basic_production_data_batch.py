# -*- coding: utf-8 -*-
# @Time : 2023/8/1 14:36
# @Author : LiYuXin
# @FileName: basic_production_data.py
# @Software: PyCharm

try:
    from _debug import para1, para2
    # print(para1)
except ImportError:
    para1 = para2 = {}
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
    cube = FinancialCube("BEWG")
    return cube


def get_val():
    # 获取变量
    variable = Variable(element_name="Variable")
    val = variable.get_value("Forcast")
    return val


def calc_a01(df, year_a01, scenario_a01, mouth, tmp):
    # A01计算
    df_a01 = df.loc[(df["Year"] == year_a01) & (df["Scenario"] == scenario_a01) & (df["Period"] == mouth)]
    df_a01.drop(columns=["A02", "A05", "A0801", "A0802", "A1001", "A1002"], inplace=True)
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
        self.year = p2["Year"]
        self.entity = p2["Entity"]
        self.version = p2["Version"]
        self.material = p2["Material"]
        self.allocation = p2["Allocation"]
        self.tax = p2["Tax"]
        self.department = p2["Department"]
        self.misc1 = p2["misc1"]
        self.misc2 = p2["misc2"]
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
            "misc1": self.misc1,
            "misc2": self.misc2,
        }
        l_exp = []
        l_exp.append(
            {
                "Account": "A05;A03;A0801;A0802;A1001;A1002",
                "Year": self.year,
                "Scenario": "Budget",
                "Period": "Remove(Base(TotalPeriod,0),Adjust);Noperiod",
                "Measure": "Nomeasure"
            }
        )
        l_exp.append(
            {
                "Account": "A05;A03;A0801;A0802;A1001;A1002",
                "Year": self.last_year,
                "Scenario": "Forecast",
                "Period": "Base(Oct,0)",
                "Measure": "Nomeasure"
            }
        )
        # exp_clear_3 = {
        #     "Account": "A01;A02;A03;A04;A05;A06;A0801;A0802;A1001;A1002",
        #     "Year": year,
        #     "Scenario": "Budget",
        #     "Period": "Noperiod"
        # }
        l_exp.append(
            {
                "Account": "A01;A02;A04;A06",
                "Year": self.year,
                "Scenario": "Budget",
                "Period": "Noperiod",
                "Measure": "Nomeasure"
            }
        )
        l_exp.append(
            {
                "Account": "A01;A02;A03;A04;A05;A06;A0801;A0802;A1001;A1002",
                "Year": self.last_year,
                "Scenario": "Actual",
                "Period": "Noperiod",
                "Measure": "Nomeasure"
            }
        )
        l_exp.append(
            {
                "Account": "A03;A05;A1001;A1002",
                "Year": self.last_year,
                "Scenario": "New",
                "Period": "Noperiod",
                "Measure": "Nomeasure"
            }
        )
        l_exp.append(
            {
                "Account": "A11",
                "Year": self.last_year,
                "Scenario": "Actual",
                "Period": "Noperiod",
                "Measure": "COD;BOD5;SS;NH3N;TN;TP;BC"
            }
        )
        l_exp.append(
            {
                "Account": "A11",
                "Year": self.year,
                "Scenario": "Budget",
                "Period": "Noperiod",
                "Measure": "COD;BOD5;SS;NH3N;TN;TP;BC"
            }
        )
        l_exp.append(
            {
                "Account": "A12",
                "Year": self.last_year,
                "Scenario": "Actual",
                "Period": "Noperiod",
                "Measure": "COD;BOD5;SS;NH3N;TN;TP;ETP"
            }
        )
        l_exp.append(
            {
                "Account": "A12",
                "Year": self.year,
                "Scenario": "Budget",
                "Period": "Noperiod",
                "Measure": "COD;BOD5;SS;NH3N;TN;TP;ETP"
            }
        )
        l_exp.append(
            {
                "Account": "A13",
                "Year": self.last_year,
                "Scenario": "Actual",
                "Period": "Noperiod",
                "Measure": "CT"
            }
        )
        l_exp.append(
            {
                "Account": "A13",
                "Year": self.year,
                "Scenario": "Budget",
                "Period": "Noperiod",
                "Measure": "CT"
            }
        )
        for i in l_exp:
            i = i.update(pov_clear)

        expression = (
                "Entity{%s}->Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->Tax{%s}->misc1{%s}->misc2{%s}->"
                "Year{%s;%s}->Account{A02;A04;A01;A0801;A0901;A0802;A0902;A06;A0701;A0702}->Scenario{Forecast;New;Budget}->"
                "Measure{Nomeasure}->Period{Base(Oct,0);Noperiod;Remove(Base(TotalPeriod,0),Adjust)}"
                % (self.entity, self.version, self.material, self.department, self.allocation, self.tax,
                   self.misc1, self.misc2, self.year, self.last_year)
        )

        # 模型中清数,取数
        async def cube_deal():
            bewg_cube = AsyncFinancialCube("BEWG")
            results = await asyncio.gather(
                * [bewg_cube.delete(exp) for exp in l_exp],
                bewg_cube.query(expression, compact=False, pivot_dim="Account")
            )
            return results
        result = asyncio.run(cube_deal())
        return result

    def calc_wet_mud_yield(self, cube, result):
        # 第二部分：按顺序计算合计实际处理水量、水力负荷、湿泥产量（10-12月、批复新增、预算1-12）

        # 模型中取数
        df = result[11]
        # print(df.columns)
        for i in ["A02", "A04", "A01", "A0901", "A0902", "A06", "A0701", "A0702", "A0801", "A0802"]:
            if i not in df.columns:
                df[i] = np.nan
        # df切片
        df_forecast = df.loc[
            (df["Year"] == self.last_year)
            & (df["Scenario"] == "Forecast")
            & ((df["Period"] == "10") | (df["Period"] == "11") | (df["Period"] == "12"))
            ]
        df_forecast.drop(columns=["A0801", "A0802"], inplace=True)
        df_new = df.loc[
            (df["Year"] == self.last_year)
            & (df["Scenario"] == "New")
            & (df["Period"] == "Noperiod")
            ]
        df_new.drop(columns=["A06", "A0701", "A0702"], inplace=True)
        df_budget = df.loc[
            (df["Year"] == self.year)
            & (df["Scenario"] == "Budget")
            & (df["Period"].isin(["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]))
            ]
        df_budget.drop(columns=["A0801", "A0802"], inplace=True)

        l_df = [df_forecast, df_budget]
        for i in l_df:
            if not i.empty:
                for j in ["A02", "A04", "A01", "A0901", "A0902", "A06", "A0701", "A0702"]:
                    if j not in i.columns:
                        i[j] = 0
                # 计算逻辑
                i.loc[:, "A05"] = i.apply(lambda x: x["A02"] * x["A04"], axis=1)
                i.loc[:, "A03"] = i.apply(
                    lambda x: x["A05"] / (x["A02"] * x["A01"])
                    if x["A02"] != 0 and x["A01"] != 0
                    else 0,
                    axis=1,
                )
                i.loc[:, "A0801"] = i.apply(lambda x: x["A06"] * x["A05"] * x["A0701"], axis=1)
                i.loc[:, "A0802"] = i.apply(lambda x: x["A06"] * x["A05"] * x["A0702"], axis=1)
                i.loc[:, "A1001"] = i.apply(lambda x: x["A0801"] / (1 - x["A0901"]) if x["A0901"] != 1 else 0, axis=1)
                i.loc[:, "A1002"] = i.apply(lambda x: x["A0802"] / (1 - x["A0902"]) if x["A0902"] != 1 else 0, axis=1)
                # 删除多余的列
                i.drop(columns=["A02", "A04", "A01", "A0901", "A0902", "A06", "A0701", "A0702"], inplace=True)
            else:
                i = pd.DataFrame()

        if not df_new.empty:
            for j in ["A02", "A04", "A01", "A0801", "A0901", "A0802", "A0902"]:
                if j not in df_new.columns:
                    df_new[j] = 0
            # 计算逻辑
            df_new.loc[:, "A05"] = df_new.apply(lambda x: x["A02"] * x["A04"], axis=1)
            df_new.loc[:, "A03"] = df_new.apply(
                lambda x: x["A05"] / (x["A02"] * x["A01"])
                if x["A02"] != 0 and x["A01"] != 0
                else 0,
                axis=1,
            )
            df_new.loc[:, "A1001"] = df_new.apply(lambda x: x["A0801"] / (1 - x["A0901"]) if x["A0901"] != 1 else 0,
                                                  axis=1)
            df_new.loc[:, "A1002"] = df_new.apply(lambda x: x["A0802"] / (1 - x["A0902"]) if x["A0902"] != 1 else 0,
                                                  axis=1)
            # 删除多余的列
            df_new.drop(columns=["A02", "A04", "A01", "A0901", "A0902", "A0801", "A0802"], inplace=True)
        else:
            df_new = pd.DataFrame()

        df_forecast = l_df[0].copy(deep=True)
        df_budget = l_df[1].copy(deep=True)
        df_fc_bg = pd.concat([df_forecast, df_budget], axis=0)

        # 存入数据
        cube.save_unpivot(df_fc_bg, unpivot_dim="Account")
        cube.save_unpivot(df_new, unpivot_dim="Account")

    def calc_noperiod(self, cube, val):
        # 第三部分：计算全年（按照科目顺序执行）
        exp = (
                "Entity{%s}->Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->Tax{%s}->misc1{%s}->misc2{%s}->"
                "Year{%s;%s}->Account{A01;A02;A05;A0801;A0802;A1001;A1002}->Scenario{Budget;Actual;Forecast}->"
                "Measure{Nomeasure}->Period{TotalPeriod;Noperiod;1;2;3;4;5;6;7;8;9;10;11;12}"
                % (self.entity, self.version, self.material, self.department, self.allocation, self.tax,
                   self.misc1, self.misc2, self.year, self.last_year)
        )
        # 模型中取数
        df = cube.query(expression=exp, compact=False, pivot_dim="Account")
        # print(df.columns)

        if not df.empty:
            for j in ["A01", "A02", "A05", "A0801", "A1001", "A0802", "A1002"]:
                if j not in df.columns:
                    df[j] = 0
        else:
            return

        # 计算A01
        tmp = ["Scenario", "Year", "Entity", "Version", "Material", "Department", "Allocation",
               "Tax", "misc1", "misc2", "Measure"]
        df_budget = calc_a01(df=df, year_a01=self.year, scenario_a01="Budget", mouth="1", tmp=tmp)

        # 计算A02,A05,A0801,A0802,A1001,A1002
        df_other = df.loc[
            (df["Year"] == self.year)
            & (df["Scenario"] == "Budget")
            & (df["Period"] == "TotalPeriod")
            ]
        df_other.drop(columns=["A01"], inplace=True)

        if not df_budget.empty:
            df_other = pd.merge(df_budget, df_other, how="inner", on=tmp)
            df_other.drop(columns=["Period_y"], inplace=True)
            df_other.rename(columns={"Period_x": "Period"}, inplace=True)
        else:
            df_other['Period'] = "Noperiod"

        df_budget = df_other.copy(deep=True)

        # 计算A02,A05,A0801,A0802,A1001,A1002
        df_other_sepmtd = df.loc[
            (df["Year"] == self.last_year)
            & (df["Scenario"] == "Actual")
            & (df['Period'].isin(['1', '2', '3', '4', '5', '6', '7', '8', '9']))
            ]
        df_other_sepmtd.drop(columns=["A01", "Scenario"], inplace=True)
        df_other_acoct = df.loc[
            (df["Year"] == self.last_year)
            & (df["Scenario"] == "Actual")
            & (df["Period"].isin(['10', '11', '12']))
            ]
        df_other_acoct.drop(columns=["A01", "Scenario"], inplace=True)
        df_other_fcoct = df.loc[
            (df["Year"] == self.last_year)
            & (df["Scenario"] == "Forecast")
            & (df["Period"].isin(['10', '11', '12']))
            ]
        df_other_fcoct.drop(columns=["A01", "Scenario"], inplace=True)
        # 根据变量的值分情况计算
        if val == "Forecast":
            df_other = pd.concat([df_other_sepmtd, df_other_fcoct], axis=0).drop(columns=["Period"], inplace=False)
            # 计算A01
            df_actual = calc_a01(df=df, year_a01=self.last_year, scenario_a01="Forecast", mouth="12",
                                 tmp=tmp)
        else:
            df_other = pd.concat([df_other_sepmtd, df_other_acoct], axis=0).drop(columns=["Period"], inplace=False)
            # 计算A01
            df_actual = calc_a01(df=df, year_a01=self.last_year, scenario_a01="Actual", mouth="12",
                                 tmp=tmp)
        # 分组聚合，重置索引
        group = ["Year", "Entity", "Version", "Material", "Department", "Allocation", "Tax", "misc1", "misc2",
                 "Measure"]
        df_other_sum = df_other.groupby(
            group,
            as_index=False,
        )["A02", "A05", "A0801", "A0802", "A1001", "A1002"].sum()
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
                for j in ["A01", "A02", "A05", "A0801", "A1001", "A0802", "A1002"]:
                    if j not in i.columns:
                        i[j] = 0
                # 计算逻辑
                i.loc[:, "A04"] = i.apply(lambda x: x["A05"] / x["A02"] if x["A02"] != 0 else 0, axis=1)
                i.loc[:, "A03"] = i.apply(
                    lambda x: x["A05"] / (x["A02"] * x["A01"])
                    if x["A02"] != 0 and x["A01"] != 0
                    else 0,
                    axis=1,
                )
                i["A0801"] = i["A0801"].fillna(0)
                i["A0802"] = i["A0802"].fillna(0)
                i.loc[:, "A06"] = i.apply(lambda x: (x["A0801"] + x["A0802"]) / x["A05"] if x["A05"] != 0 else 0,
                                          axis=1)
            else:
                # print('empty')
                i = pd.DataFrame()

        df_budget = l[0].copy(deep=True)
        df_actual = l[1].copy(deep=True)
        df_bd_ac = pd.concat([df_budget, df_actual], axis=0)
        # 存入数据
        cube.save_unpivot(df_bd_ac, unpivot_dim="Account")

    def calc_compare(self, cube):
        # 查询维度中父级节点
        entity_dim = Dimension("Entity")
        entity_parent = entity_dim.query(self.entity, fields=['parent_name'], as_model=False)
        df_dim = pd.DataFrame(data=entity_parent)
        parent_name = df_dim.loc[0, "parent_name"]

        exp = (
                "Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->Tax{Tax}->misc1{%s}->misc2{%s}->Year{%s}->"
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
        # 第六部分：计算水质全年
        # 取数
        exp = (
                "Entity{%s}->Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->misc1{%s}->misc2{%s}->"
                "Tax{Tax}->Year{%s;%s}->Account{A11;A12;A13;A05}->Scenario{Budget;Actual;Forecast}->"
                "Measure{Nomeasure;COD;BOD5;SS;NH3N;TN;TP;BC;ETP;CT;Nomeasure}->"
                "Period{Noperiod;1;2;3;4;5;6;7;8;9;10;11;12}"
                % (self.entity, self.version, self.material, self.department, self.allocation,
                   self.misc1, self.misc2, self.year, self.last_year)
        )
        # 模型中取数
        df = cube.query(expression=exp, compact=False)

        # 切分分母
        df_ac = df.loc[(df["Account"] == "A05")
                           & (df["Scenario"] == "Actual")
                           & (df["Year"] == self.last_year)
                           & (df["Measure"] == "Nomeasure")
                           & (df["Period"] == "Noperiod")]
        df_bg = df.loc[(df["Account"] == "A05")
                           & (df["Scenario"] == "Budget")
                           & (df["Year"] == self.year)
                           & (df["Measure"] == "Nomeasure")
                           & (df["Period"] == "Noperiod")]
        df_a05_numerator = pd.concat([df_ac, df_bg], axis=0)
        df_a05_numerator.drop(columns=["Account", "Measure", "Period"], inplace=True)

        # 分析变量，切分分子
        df_bg = df.loc[(df["Scenario"] == "Budget")
                       & (df["Year"] == self.year)
                       & (df["Period"].isin(["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]))]
        if val == "Forecast":
            df_fc = df.loc[(df["Scenario"] == "Forecast")
                           & (df["Year"] == self.last_year)
                           & (df["Period"].isin(["10", "11", "12"]))]
            df_ac = df.loc[(df["Scenario"] == "Actual")
                           & (df["Year"] == self.last_year)
                           & (df["Period"].isin(["1", "2", "3", "4", "5", "6", "7", "8", "9"]))]
            df_ac = pd.concat([df_fc, df_ac], axis=0)
            df_ac["Scenario"] = "Actual"
        else:
            df_ac = df.loc[(df["Scenario"] == "Actual")
                           & (df["Year"] == self.last_year)
                           & (df["Period"].isin(["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]))]
        df = pd.concat([df_bg, df_ac], axis=0)

        df_a05 = df.loc[(df["Account"] == "A05")
                        & (df["Measure"] == "Nomeasure")]
        df_a05.drop(columns=["Account", "Measure"], inplace=True)
        df_a11 = df.loc[(df["Account"] == "A11")
                        & (df["Measure"].isin(["COD", "BOD5", "SS", "NH3N", "TN", "TP", "BC"]))]
        df_a12 = df.loc[(df["Account"] == "A12")
                        & (df["Measure"].isin(["COD", "BOD5", "SS", "NH3N", "TN", "TP", "ETP"]))]
        df_a13 = df.loc[(df["Account"] == "A13")
                        & (df["Measure"] == "CT")]
        df_a1x = pd.concat([df_a11, df_a12, df_a13], axis=0)

        # Σ(decimal1*decimal2)/decimal3
        # 计算相乘
        group = ["Year", "Period", "Scenario",
                 "Entity", "Version", "Material", "Department", "Allocation", "Tax", "misc1", "misc2"]
        df_calc = pd.merge(df_a1x, df_a05, how="left", on=group)
        if not df_calc.empty:
            df_calc.loc[:, "data"] = df_calc.apply(lambda x: x["data_x"] * x["data_y"]
                                                   if pd.notnull(x["data_x"]) & pd.notnull(x["data_y"])
                                                   else np.NaN,
                                                   axis=1)
            df_calc.drop(columns=["data_x", "data_y"], inplace=True)
            # 计算合计
            group.remove("Period")
            group.append("Account")
            group.append("Measure")
            df_calc_sum = df_calc.groupby(group, as_index=False)["data"].sum()
            df_calc_sum["Period"] = "Noperiod"
            # 计算相除
            group.remove("Account")
            group.remove("Measure")
            df_calc = pd.merge(df_calc_sum, df_a05_numerator, how="left", on=group)
            df_calc.loc[:, "data"] = df_calc.apply(lambda x: x["data_x"] / x["data_y"]
                                                   if pd.notnull(x["data_x"]) & pd.notnull(x["data_y"]) & (x["data_y"] != 0)
                                                   else np.NaN,
                                                   axis=1)
            df_calc.drop(columns=["data_x", "data_y"], inplace=True)
            df = df_calc.copy(deep=True)

            # 存数
            cube.save(df)

        return


def main(p1, p2):
    # p2 = {'Year': '2023', 'Entity': 'XN13001_01', 'Version': 'Y1', 'Material': 'Nomaterial', 'Allocation': 'Original', 'Tax': 'Tax', 'Department': 'Operation', 'misc1': 'Nomisc1', 'misc2': 'Nomisc2', 'sheetName': '基础生产数据-水量、泥量', 'sheetId': 'SHTb4ed3d626a2d', 'elementName': 'ProductData', 'folderId': 'DIRfd5a95b6f89c'}
    begin = time.time()
    cube = get_cube()
    val = get_val()
    # 第一部分：清数及取第二部分的数据
    result = Basic(p2).del_cube(cube=cube)
    # 第二部分：按顺序计算合计实际处理水量、水力负荷、湿泥产量（10-12月、批复新增、预算1-12）
    Basic(p2).calc_wet_mud_yield(cube=cube, result=result)
    # 第三部分：计算全年（按照科目顺序执行）
    Basic(p2).calc_noperiod(cube=cube, val=val)
    print(time.time() - begin)
    # 第四部分：计算审核指标：实际处理水量、干泥量增加额、增长率
    from Python_prd.biz.phaseII.newly.calc_audit_indicators import main as main_audit
    main_audit(p1, p2, account_list=["A05", "A08"], year=p2["Year"],
               scenario_save="Budget", scenario_calcyear="Budget", scenario_lastyear="Actual",
               measure="Nomeasure", entity="IDescendant(1,0)", tax=p2["Tax"])
    main_audit(p1, p2, account_list=["A08"], year=p2["Year"], year_save=str(int(p2["Year"]) - 1),
               scenario_save="Combinaion", scenario_calcyear="Budget", scenario_lastyear="Combinaion",
               measure="Nomeasure", entity="IDescendant(1,0)", tax=p2["Tax"])
    # 第五部分：计算是否超保底运行(由于用户权限问题，改为前端完成)
    # from Python_prd.biz.phaseII.newly.compare_save_dim import main as main_compare
    # main_compare(cube, p2, entity=p2["Entity"], year=p2["Year"])
    # print(time.time() - begin)
    # 第六部分：计算水质全年
    Basic(p2).calc_water_quality(cube=cube, val=val)
    print(time.time() - begin)
    # 第七部分：计算毛利毛利率
    if p2["sheetName"] != "串行":
        from Python_prd.biz.phaseII.newly.gross_margin_calc import main as main_gross
        main_gross(p1, p2)
    print(time.time() - begin)
    return


if __name__ == "__main__":
    # from conf._evn import p1, p2

    # p2 = {'Year': '2024', 'Entity': 'XN23002_01', 'Version': 'Y1', 'Material': 'Nomaterial', 'Allocation': 'Original', 'Tax': 'Tax', 'Department': 'Operation', 'misc1': 'Nomisc1', 'misc2': 'Nomisc2', 'sheetName': '基础生产数据-水量、泥量', 'sheetId': 'SHTb4ed3d626a2d', 'elementName': 'ProductData', 'folderId': 'DIRfd5a95b6f89c'}
    p2 = {'Year': '2024', 'Entity': 'Base(1,0)', 'Version': 'Y1', 'Material': 'Nomaterial', 'Allocation': 'Original',
          'Tax': 'Tax', 'Department': 'Operation', 'misc1': 'Nomisc1', 'misc2': 'Nomisc2',
          'sheetName': '基础生产数据-水量、泥量', 'sheetId': 'SHTb4ed3d626a2d', 'elementName': 'ProductData',
          'folderId': 'DIRe437ed8262b4'}

    main(para1, p2)

