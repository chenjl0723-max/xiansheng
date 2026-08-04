#!/usr/bin/env python
# 原材料费用、原材料单耗填报
# -*- coding: utf-8 -*-
# @Time : 2023/9/19 10:00
# @Author : LiYuXin
# @FileName: raw_material_calc.py
# @Software: PyCharm

import time
import os
import sys
import warnings
import numpy as np
import pandas as pd
from deepfos.element.finmodel import FinancialCube
from deepfos.element.variable import Variable

warnings.filterwarnings('ignore')
top_path = os.path.abspath(os.path.join(__file__, "../.."))
sys.path.append(top_path)
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)

def run_raw(p1, p2):
    """
        对原材料明细、中类、实际数以及处理审核指标逻辑

    :param p1: p1 参数
    :param p2: 前端传来的基础信息，包含 pov 的参数
    :return:
    """

    # # 脚本挂在到 material_to_cube 前预处理
    # p2_keys = list(p2.keys())
    #
    # if 'Scenario' in p2_keys:
    #     del p2['Scenario']
    # if 'Allocation' not in p2_keys:
    #     p2['Allocation'] = 'Original'
    # if 'Tax' not in p2_keys:
    #     p2['Tax'] = 'Tax'
    # if 'misc1' not in p2_keys:
    #     p2['misc1'] = 'Nomisc1'
    # if 'misc2' not in p2_keys:
    #     p2['misc2'] = 'Nomisc2'
    # if 'Measure' not in p2_keys:
    #     p2['Measure'] = 'Expenses'

    entity = p2['Entity']
    year = p2['Year']
    last_year = str(int(p2['Year']) - 1)
    # p2_copy = p2.copy()
    del p2['Year']

    # rename_map = {
    #     "Measure_wb1": "Measure",
    #     "Allocation_wb1": "Allocation",
    #     "Version_wb1": "Version",
    #     "Department_wb1": "Department",
    #     "Tax_wb1": "Tax",
    #     "Misc1_wb1": "Misc1",
    #     "Misc2_wb1": "Misc2"
    # }
    # p2_copy = {rename_map.get(key, key): value for key, value in p2_copy.items()}
    # print('run里的p2', p2_copy)

    middle = time.time()
    # 执行中类处理逻辑
    from budget.Python.biz.material.materials_middle_summary import do_middle_logic
    do_middle_logic(p1=p1, p2=p2, year=year, last_year=last_year, entity=entity)
    print("中类：", time.time() - middle)

    # config = time.time()
    # 处理审核指标逻辑
    # p2["year"] = year
    # p2["entity"] = entity
    # p2["sheet_id"] = p2['sheetId']
    # print(p2)
    # # audit.main(p1, p2)
    # print("配置表：", time.time() - config)


class Detail(object):
    def __init__(self, p2):
        self.cube = FinancialCube("WS_cube")
        self.fix = ("Account{%s}->Material{%s}->"
                    "Year{%s}->Scenario{%s}->Period{%s}->"
                    "Measure{%s}->Entity{%s}->Version{%s}->Department{%s}->Allocation{%s}->Tax{%s}->"
                    "Misc1{%s}->Misc2{%s}")
        # cube相关页面参数
        self.year = p2["Year_wb1"]
        self.last_year = str(int(p2["Year_wb1"]) - 1)
        self.entity = p2["Entity_wb1"]
        self.measure = p2["Measure_wb1"]
        self.version = p2["Version_wb1"]
        self.department = p2["Department_wb1"]
        self.allocation = p2["Allocation_wb1"]
        self.tax = p2["Tax_wb1"]
        self.misc2 = p2["Misc2_wb1"]
        # 获取全局变量
        var = Variable("Variable")
        self.fc_var = var.get_value("Forcast")

    def query_YW0205_YW0208(self):
        misc1 = "Nomisc1"
        material = "Nomaterial"
        measure = "Nomeasure"
        # 取数
        account = "YW0205;YW0208"
        year = self.year + ";" + self.last_year
        period = "1;2;3;4;5;6;7;8;9;10;11;12;Noperiod"
        scenario = "Budget;Forecast;Actual"
        exp = self.fix % (account, material, year, scenario, period, measure,
                          self.entity, self.version, self.department, self.allocation, self.tax,
                          misc1, self.misc2)
        df = self.cube.query(exp, compact=False)
        # 按Scenario切分
        df_bg = df.loc[(df["Scenario"] == "Budget")
                       & (df["Year"] == self.year)]
        df_fc = df.loc[(df["Scenario"] == "Forecast")
                       & (df["Year"] == self.last_year)
                       & (df["Period"].isin(["10", "11", "12", "Noperiod"]))]
        df_ac = df.loc[(df["Scenario"] == "Actual")
                       & (df["Year"] == self.last_year)
                       & (df["Period"] == "Noperiod")]
        df_YW0205_YW0208 = pd.concat([df_bg, df_fc, df_ac], axis=0)
        df_YW0205_YW0208.drop(columns=["Misc1", "Material", "Measure"], inplace=True)
        # 按Account切分
        df_YW0205 = df_YW0205_YW0208.loc[(df["Account"] == "YW0205")]
        df_YW0208 = df_YW0205_YW0208.loc[(df["Account"] == "YW0208")]
        return df_YW0205, df_YW0208

    def calc_year_sum(self, account):
        misc1 = "Base(#root,0)"
        material = "Base(MQ,0)"
        period = "Noperiod"
        # 清除数据
        del_fix = self.fix % (account, material, self.year, "Budget", period,
                              self.measure, self.entity, self.version, self.department, self.allocation, self.tax,
                              misc1, self.misc2)
        self.cube.delete(expression=del_fix)
        del_fix = self.fix % (account, material, self.last_year, "Actual", period,
                              self.measure, self.entity, self.version, self.department, self.allocation, self.tax,
                              misc1, self.misc2)
        self.cube.delete(expression=del_fix)
        # 取数
        year = self.year + ";" + self.last_year
        scenario = "Budget;Actual;Forecast"
        period = "1;2;3;4;5;6;7;8;9;10;11;12;TotalPeriod"
        exp = self.fix % (account, material, year, scenario, period,
                          self.measure, self.entity, self.version, self.department, self.allocation, self.tax,
                          misc1, self.misc2)
        df = self.cube.query(exp, compact=False)
        # 切分Budget
        df_bg = df.loc[(df["Scenario"] == "Budget")
                       & (df["Year"] == self.year)
                       & (df["Period"] == "TotalPeriod")]

        # 分析变量，切分Actual
        if self.fc_var == "Forecast":
            df_fc = df.loc[(df["Scenario"] == "Forecast")
                           & (df["Year"] == self.last_year)
                           & (df["Period"].isin(["10", "11", "12"]))]
            df_ac = df.loc[(df["Scenario"] == "Actual")
                           & (df["Year"] == self.last_year)
                           & (df["Period"].isin(["1", "2", "3", "4", "5", "6", "7", "8", "9"]))]
            df_ac = pd.concat([df_fc, df_ac], axis=0)
            df_ac["Scenario"] = "Actual"
            df_ac['Misc1'] = 'Nomisc1'
        else:
            df_ac = df.loc[(df["Scenario"] == "Actual")
                           & (df["Year"] == self.last_year)
                           & (df["Period"].isin(["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12"]))]

        group = ["Year", "Scenario", "Account", "Material",
                 "Entity", "Version", "Department", "Allocation", "Measure", "Tax", "Misc1", "Misc2"]
        df_sum = None

        if not df_ac.empty:
            df_ac = df_ac.groupby(group, as_index=False)["data"].sum()
            df_ac["Period"] = "Noperiod"
            df_sum = df_ac

        if not df_bg.empty:
            df_bg = df_bg.groupby(group, as_index=False)["data"].sum()
            df_bg["Period"] = "Noperiod"
            if df_sum is not None:
                df_sum = pd.concat([df_sum, df_bg], axis=0)
            else:
                df_sum = df_bg

        if df_sum is not None:
            print('df_sum', df_sum)
            self.cube.save(df_sum)

    def calc(self, account_calc, account_save, material, n_calc=1, operator="*",
             df_part=pd.DataFrame(), dict_period=None):

        if dict_period is None:
            dict_period = {"Budget": "", "Actual": "", "Forecast": ""}
        misc1 = "Base(#root,0)"

        # 清除数据
        for key, value in dict_period.items():
            if key == "Budget":
                del_fix = self.fix % (account_save, material, self.year, key, value, self.measure,
                                      self.entity, self.version, self.department, self.allocation, self.tax,
                                      misc1, self.misc2)
            else:
                del_fix = self.fix % (account_save, material, self.last_year, key, value, self.measure,
                                      self.entity, self.version, self.department, self.allocation, self.tax,
                                      misc1, self.misc2)
            self.cube.delete(expression=del_fix)

        # 取数
        year = self.year + ";" + self.last_year
        scenario_list = dict_period.keys()
        scenario = ';'.join(scenario_list)
        period = dict_period["Budget"]
        exp = self.fix % (account_calc, material, year, scenario, period, self.measure,
                          self.entity, self.version, self.department, self.allocation, self.tax,
                          misc1, self.misc2)
        df = self.cube.query(exp, compact=False)

        # 按Scenario切分
        df_bg = pd.DataFrame()
        for key, value in dict_period.items():
            period_list = value.split(";")
            if key == "Budget":
                df_scenario = df.loc[(df["Scenario"] == key)
                                     & (df["Year"] == self.year)
                                     & (df["Period"].isin(period_list))]
            else:
                df_scenario = df.loc[(df["Scenario"] == key)
                                     & (df["Year"] == self.last_year)
                                     & (df["Period"].isin(period_list))]
            df_bg = pd.concat([df_bg, df_scenario], axis=0)

        if not df_bg.empty:
            account_list = account_calc.split(";")
            if not df_part.empty:
                # 合并YW0205,YW0208
                group = ["Year", "Period", "Scenario",
                         "Entity", "Version", "Department", "Allocation", "Tax", "Misc2"]
                df_calc = pd.merge(df_bg, df_part, how="left", on=group)
                df_calc.rename(columns={"data_x": account_list[0], "data_y": account_list[1]}, inplace=True)
                df_calc.drop(columns=["Account_x", "Account_y"], inplace=True)
            else:
                # Account行转列
                group = ["Year", "Period", "Scenario", "Material", "Measure",
                         "Entity", "Version", "Department", "Allocation", "Tax", "Misc1", "Misc2"]
                df_calc = pd.pivot(df_bg, index=group, columns="Account", values="data")
                df_calc = df_calc.reset_index()
                for i in account_list:
                    if i not in df_calc.columns:
                        df_calc[i] = np.NaN
            # 计算逻辑
            if operator == "*":
                df_calc.loc[:, "data"] = df_calc.apply(lambda x: x[account_list[0]] * x[account_list[1]] / n_calc
                if pd.notnull(x[account_list[0]])
                   & pd.notnull(x[account_list[1]])
                else np.NaN, axis=1)
            elif operator == "/":
                df_calc.loc[:, "data"] = df_calc.apply(lambda x: x[account_list[0]] / x[account_list[1]] * n_calc
                if pd.notnull(x[account_list[0]])
                   & pd.notnull(x[account_list[1]])
                   & (x[account_list[1]] != 0)
                else np.NaN, axis=1)
            df_calc = df_calc.replace([np.inf, -np.inf], 0)
            df_calc.drop(columns=account_list, inplace=True)
            df_calc["Account"] = account_save
            print(df_calc)
            # 存数
            self.cube.save(df_calc)

    def calc_carbon(self):
        dict_period = {"Budget": "1;2;3;4;5;6;7;8;9;10;11;12;Noperiod",
                       "Forecast": "10;11;12;Noperiod",
                       "Actual": "Noperiod"}
        # 清除数据
        for key, value in dict_period.items():
            if key == "Budget":
                del_fix = self.fix % ("YW0309", "Base(MQ03,0)", self.year, key, value, self.measure,
                                      self.entity, self.version, self.department, self.allocation, self.tax,
                                      "Nomisc1", self.misc2)
            else:
                del_fix = self.fix % ("YW0309", "Base(MQ03,0)", self.last_year, key, value, self.measure,
                                      self.entity, self.version, self.department, self.allocation, self.tax,
                                      "Nomisc1", self.misc2)
            self.cube.delete(expression=del_fix)

        account = "YW0211;YW0212;YW0301;YW0304"
        material = "Nomaterial;Base(MQ03,0)"
        measure = self.measure + ";COD;TN"
        misc1 = "#root;Nomisc1"
        year = self.year + ";" + self.last_year
        scenario_list = dict_period.keys()
        scenario = ';'.join(scenario_list)
        period = dict_period["Budget"]
        # 取数
        exp = self.fix % (account, material, year, scenario, period, measure,
                          self.entity, self.version, self.department, self.allocation, self.tax, misc1, self.misc2)
        df = self.cube.query(exp, compact=False)
        # 按Scenario切分
        df_bg = pd.DataFrame()
        for key, value in dict_period.items():
            period_list = value.split(";")
            if key == "Budget":
                df_scenario = df.loc[(df["Scenario"] == key)
                                     & (df["Year"] == self.year)
                                     & (df["Period"].isin(period_list))]
            else:
                df_scenario = df.loc[(df["Scenario"] == key)
                                     & (df["Year"] == self.last_year)
                                     & (df["Period"].isin(period_list))]
            df_bg = pd.concat([df_bg, df_scenario], axis=0)
        # 按计算逻辑切分
        account_list = ["YW0211", "YW0212"]
        measure_list = ["COD", "TN"]
        df_other = df_bg.loc[(df["Material"] == "Nomaterial")
                             & (df["Misc1"] == "Nomisc1")
                             & (df["Account"].isin(account_list))
                             & (df["Measure"].isin(measure_list))]
        df_other.drop(columns=["Material", "Misc1"], inplace=True)
        if not df_other.empty:
            # Account行转列
            group = ["Year", "Period", "Scenario", "Measure",
                     "Entity", "Version", "Department", "Allocation", "Tax", "Misc2"]
            df_YW0211_YW0212 = pd.pivot(df_other, index=group, columns="Account", values="data")
            df_YW0211_YW0212.reset_index(inplace=True)
            # 填补空值
            df_YW0211_YW0212.fillna(value=0, inplace=True)
            for i in account_list:
                if i not in df_YW0211_YW0212.columns:
                    df_YW0211_YW0212[i] = 0
            # 计算差
            df_YW0211_YW0212.loc[:, "YW0211-YW0212"] = df_YW0211_YW0212.apply(lambda x: x["YW0211"] - x["YW0212"]
            if pd.notnull(x["YW0211"]) & pd.notnull(x["YW0212"])
            else np.NaN, axis=1)
            df_YW0211_YW0212.drop(columns=account_list, inplace=True)
            # Measure行转列
            group.remove("Measure")
            df_cod_tn = pd.pivot(df_YW0211_YW0212, index=group, columns="Measure", values="YW0211-YW0212")
            df_cod_tn.reset_index(inplace=True)
            # 填补空值
            df_cod_tn.fillna(value=0, inplace=True)
            for i in measure_list:
                if i not in df_cod_tn.columns:
                    df_cod_tn[i] = 0

            # 按计算逻辑切分
            account_list = ["YW0301", "YW0304"]
            df_main = df_bg.loc[(~(df["Material"] == "Nomaterial"))
                                & (df["Misc1"] == "#root")
                                & (df["Account"].isin(account_list))
                                & (df["Measure"] == self.measure)]
            if not df_main.empty:
                # Account行转列
                group = ["Year", "Period", "Scenario", "Material", "Measure",
                         "Entity", "Version", "Department", "Allocation", "Tax", "Misc1", "Misc2"]
                df_YW0301_YW0304 = pd.pivot(df_main, index=group, columns="Account", values="data")
                df_YW0301_YW0304.reset_index(inplace=True)
                # 填补空值
                df_YW0301_YW0304.fillna(value=0, inplace=True)
                for i in account_list:
                    if i not in df_YW0301_YW0304.columns:
                        df_YW0301_YW0304[i] = 0
                # 合并df_YW0301_YW0304,df_cod_tn
                group = ["Year", "Period", "Scenario",
                         "Entity", "Version", "Department", "Allocation", "Tax", "Misc2"]
                df_calc = pd.merge(df_YW0301_YW0304, df_cod_tn, how="left", on=group)
                df_calc.loc[:, "data"] = df_calc.apply(lambda x: (x["COD"] + x["YW0304"]) / x["TN"]
                if (x["TN"] != 0) & (x["YW0301"] != 0)
                else np.NaN, axis=1)
                df_calc.drop(columns=["COD", "TN", "YW0301", "YW0304"], inplace=True)
                df_calc["Account"] = "YW0309"
                df_calc["Misc1"] = "Nomisc1"
                # 存数
                self.cube.save(df_calc)
        return


def main(p1, p2):
    print(p2)
    # p2 = {'Year': '2023', 'Entity': 'IDescendant(1,0)', 'Version': 'Y1', 'Allocation': 'Original', 'Tax': 'Tax',
    #          'misc2': 'Nomisc2', 'Department': 'Operation', 'Measure': 'Expenses',
    #          'sheetName': '原材料单耗填报（集采药剂）', 'sheetId': 'SHT1ff5da80ca67', 'elementName': 'Material',
    #          'folderId': 'DIRfd5a95b6f89c'}
    begin = time.time()
    # for i in ['elementName', 'folderId', 'sheetName', 'sheetId']:
    #     if i in p2:
    #         del p2[i]
    detail = Detail(p2)

    dict_period1 = {"Budget": "1;2;3;4;5;6;7;8;9;10;11;12",
                    "Forecast": "10;11;12"}
    dict_period2 = {"Budget": "Noperiod",
                    "Actual": "Noperiod"}
    dict_period3 = {"Budget": "1;2;3;4;5;6;7;8;9;10;11;12;Noperiod",
                    "Forecast": "10;11;12;Noperiod",
                    "Actual": "Noperiod"}
    material1 = "Base(MQ01,0);Base(MQ02,0);Base(MQ03,0);Base(MQ04,0);Base(MQ99,0)"
    material2 = "Base(MQ05,0);Base(MQ98,0)"
    material3 = "Base(MQ03,0)"
    material4 = "Base(MQ,0)"

    # 1、药量、吨水药耗计算
    df_YW0205, df_YW0208 = detail.query_YW0205_YW0208()
    # （1）药量（明细月份）:
    # YW0301=YW0304*YW0205/100
    detail.calc(account_calc="YW0304;YW0205", account_save="YW0301", n_calc=100, operator="*", df_part=df_YW0205,
                material=material1, dict_period=dict_period1)
    # YW0301=YW0316*YW0208/1000
    detail.calc(account_calc="YW0316;YW0208", account_save="YW0301", n_calc=1000, operator="*", df_part=df_YW0208,
                material=material2, dict_period=dict_period1)
    # （2）药量（全年）:
    detail.calc_year_sum(account="YW0301")
    # （3）吨水 / 干泥药耗（全年）:
    # YW0304=YW0301/YW0205*100
    detail.calc(account_calc="YW0301;YW0205", account_save="YW0304", n_calc=100, operator="/", df_part=df_YW0205,
                material=material1, dict_period=dict_period2)
    # YW0316=YW0301/YW0208*1000
    detail.calc(account_calc="YW0301;YW0208", account_save="YW0316", n_calc=1000, operator="/", df_part=df_YW0208,
                material=material2, dict_period=dict_period2)
    # （4）吨水有效成份药耗计算（明细月份 + 全年）:
    # YW0305=YW0302*YW0304
    detail.calc(account_calc="YW0302;YW0304", account_save="YW0305", n_calc=1, operator="*",
                material=material1, dict_period=dict_period3)

    # （5）碳源折合COD单耗计算（明细月份+全年）:
    # YW0310=YW0305*YW0307
    detail.calc(account_calc="YW0305;YW0307", account_save="YW0310", n_calc=1, operator="*",
                material=material3, dict_period=dict_period3)

    # 2、原材料费用、吨水成本计算
    # （1）费用（明细月份）:
    # PL01020101=YW0301*YW0303/10000
    detail.calc(account_calc="YW0301;YW0303", account_save="PL01020101", n_calc=10000, operator="*",
                material=material4, dict_period=dict_period1)
    # （2）费用（全年）:
    detail.calc_year_sum(account="PL01020101")
    # （3）吨水/干泥成本（明细月份+全年）:
    # YW0306=PL01020101/YW0205
    detail.calc(account_calc="PL01020101;YW0205", account_save="YW0306", n_calc=1, operator="/", df_part=df_YW0205,
                material=material4, dict_period=dict_period3)
    # # A80=PL01020101/YW0208
    # detail.calc(account_calc="PL01020101;YW0208", account_save="A80", n_calc=1, operator="/", df_part=df_YW0208,
    #             material=material2, dict_period=dict_period3)
    # （4）单价（全年）:
    # YW0303=PL01020101/YW0301*10000
    detail.calc(account_calc="PL01020101;YW0301", account_save="YW0303", n_calc=10000, operator="/",
                material=material4, dict_period=dict_period2)

    # 3、加碳源后△COD/△TN计算
    detail.calc_carbon()
    print("明细：", time.time() - begin)
    rename_map = {
        "Entity_wb1":"Entity",
        "Year_wb1":"Year",
        "Measure_wb1": "Measure",
        "Allocation_wb1": "Allocation",
        "Version_wb1": "Version",
        "Department_wb1": "Department",
        "Tax_wb1": "Tax",
        "Misc1_wb1": "Misc1",
        "Misc2_wb1": "Misc2"
    }
    p2 = {rename_map.get(key, key): value for key, value in p2.items()}
    # print('p2--', p2)
    p2_copy = p2.copy()
    run_raw(p1, p2_copy)

    # 计算毛利毛利率
    # if p2["sheetName"] != "串行":
    #     gross = time.time()
    #     from budget.Python.biz.phaseII.newly.gross_margin_calc import main as main_gross
    #     print('p2--', p2)
    #     main_gross(p1, p2)
    #     print("毛利：", time.time() - gross)


if __name__ == "__main__":
    try:
        from common._debug import para1
    except:
        pass
    para2 = {'elementName': '_Material_Unit', 'folderId': 'DIRacd99f1aefd0', 'sheetName': '原材料单耗填报（非集采药剂）', 'sheetId': 'SHTdb258039787a486589a8827c08a1eafb', 'Year_wb1': '2026', 'Entity_wb1': 'XN61001_01', 'Department_wb1': 'Operation', 'Tax_wb1': 'Tax', 'Version_wb1': 'Y1', 'Material_wb1': 'Nomaterial', 'Allocation_wb1': 'Original', 'Measure_wb1': 'Expenses', 'Misc1_wb1': 'Nomisc1', 'Misc2_wb1': 'Nomisc2'}

    main(para1, para2)


