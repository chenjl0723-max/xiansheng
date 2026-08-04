# -*- coding: utf-8 -*-
# @Time : 2023/8/9 13:43
# @Author : LiYuXin
# @FileName: calc_audit_indicators.py
# @Software: PyCharm

# 被base_production_data_batch(基础生产数据)
# 和budget_revenue_calc_batch(水价与收入)
# 和indicators_equipment(设备审核指标)调用

import pandas as pd
import warnings
from deepfos.element.finmodel import FinancialCube
warnings.filterwarnings("ignore")


def get_cube():
    # 实例化财务模型
    cube = FinancialCube("WS_cube")
    return cube


def df_processing(df, year, last_year, scenario_year, scenario_lastyear,
                  period_year=None, period_lastyear=None):
    if (period_year is None) and (period_lastyear is None):
        df_save = df.loc[(df["Scenario"] == scenario_year)
                         & (df["Year"] == year)]
        df_calc = df.loc[(df["Scenario"] == scenario_lastyear)
                         & (df["Year"] == last_year)]
    else:
        df_save = df.loc[(df["Scenario"] == scenario_year)
                         & (df["Year"] == year)
                         & (df["Period"] == period_year)]
        df_calc = df.loc[(df["Scenario"] == scenario_lastyear)
                         & (df["Year"] == last_year)
                         & (df["Period"] == period_lastyear)]
        df_calc["Period"] = period_year

    df_calc = pd.concat([df_save, df_calc], axis=0)
    df_calc.drop(columns=["Scenario"], inplace=True)
    df_calc_series = pd.pivot(
        df_calc,
        index=["Entity", "Version", "Material", "Department", "Allocation", "Tax",
               "Misc1", "Misc2", "Measure", "Period", "Account"],
        columns="Year",
        values="data",
    )
    df_calc = df_calc_series.reset_index()
    return df_calc


def calc_increase_riserate(df, op_year, op_last_year, year_save, scenario_save):
    # 计算Increase，Riserate
    if not df.empty:
        for j in [op_year, op_last_year]:
            if j not in df.columns:
                df[j] = 0
        # 计算逻辑
        df.loc[:, "Increase"] = df.apply(lambda x: x[op_year] - x[op_last_year], axis=1)
        df.loc[:, "Riserate"] = df.apply(
            lambda x: (x[op_year] - x[op_last_year]) / x[op_last_year]
            if x[op_last_year] != 0
            else 0,
            axis=1,
        )
        df.drop(columns=[op_year, op_last_year, "Measure"], inplace=True)
        df["Year"] = year_save
        df["Scenario"] = scenario_save
    else:
        df_result = pd.DataFrame()
    return df


def main(p1, p2, account_list, year, scenario_save, scenario_calcyear, scenario_lastyear, measure, tax,
         entity=None, year_save=None, period=None):
    # 第四部分：计算审核指标：实际处理水量、干泥量增加额、增长率

    cube = get_cube()

    # 页面维度 Year Entity Version Material Allocation Tax Department Misc1 Misc2 Account Scenario Measure Period
    version = p2["Version"]
    material = p2["Material"]
    allocation = p2["Allocation"]
    department = p2["Department"]
    misc1 = p2["Misc1"]
    misc2 = p2["Misc2"]
    last_year = str(int(year) - 1)
    if year_save is None:
        year_save = year
    if period is None:
        period = "Noperiod"
    if entity is None:
        entity = "IDescendant(1,0)"

    acco = "{"
    for i in account_list:
        acco += i
        acco += ";"
    # Python_prd rfind()返回字符串最后一次出现的位置
    idx = acco.rfind(";")
    # 提取前一部分字符不替换，取后一部分字符进行替换
    # 这里用到了字符串切片的方式
    account = acco[:idx] + str.replace(acco[idx:], ";", "}")

    # 模型中取数
    exp = ("Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->Tax{%s}->Misc1{%s}->Misc2{%s}->"
           "Year{%s;%s}->Account%s->Scenario{Budget;Combinaion;Actual}->Entity{%s}->Measure{%s}->Period{%s}"
           % (version, material, department, allocation, tax, misc1, misc2,
              year, last_year, account, entity, measure, period))
    df = cube.query(expression=exp, compact=False)
    # print(df.columns)

    # 为了设备审核指标单独切片,新增的判断
    if period == "TotalPeriod;Noperiod":
        df_calc = df_processing(df=df, year=year, last_year=last_year,
                                scenario_lastyear=scenario_lastyear, scenario_year=scenario_calcyear,
                                period_lastyear="Noperiod", period_year="TotalPeriod")
    else:
        # df切片
        df_calc = df_processing(df=df, year=year, last_year=last_year,
                                scenario_lastyear=scenario_lastyear, scenario_year=scenario_calcyear)

    # 计算increase，riserate
    df_save = calc_increase_riserate(df=df_calc, op_year=year, op_last_year=last_year,
                                     year_save=year_save, scenario_save=scenario_save)

    # 清数
    exp_clear = ("Version{%s}->Material{%s}->Department{%s}->Allocation{%s}->Tax{%s}->Misc1{%s}->Misc2{%s}->"
                 "Year{%s}->Account%s->Scenario{%s}->Entity{%s}->Measure{Increase;Riserate}->Period{%s}"
                 % (version, material, department, allocation, tax, misc1, misc2,
                    year_save, account, scenario_save, entity, period))
    cube.delete(exp_clear)
    # 存入数据
    cube.save_unpivot(df_save, unpivot_dim="Measure")
    print("%s场景下的%s审核指标计算完成" % (scenario_save, account))

    return

# if __name__ == '__main__':
#     main(p1, p2, account, year, scenario_save, scenario_calc, measure, entity, tax)


