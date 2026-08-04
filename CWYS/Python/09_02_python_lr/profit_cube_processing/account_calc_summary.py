#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    描述：填报端-动态表-科目计算汇总脚本

    开发： pz

    日期： 2026/04/17 9:54

"""
import time
from deepfos.element.variable import Variable
from deepfos.element.finmodel import FinancialCube
import pandas as pd
import numpy as np
import os
import sys

top_path = os.path.abspath(os.path.join(__file__, "../../.."))
sys.path.append(top_path)

from CWYS.common.commons import *
# from BEWG.common.commons import *


class ITOA(object):
    def __init__(
            self,
    ):
        # cube 元素名
        # self.cube = "WS_cube"
        self.cube = "sub_profit_cube"
        # fix 表达式
        # self.fix（FIX 表达式）
        # 定义了一个格式化字符串，用于构建 FIX 表达式（通常用于 Essbase/MaxL 或其他财务计算引擎）。这个字符串包含多个占位符 {%s}，后续可以通过 .format() 或 % 格式化填充具体值
        # self.fix = (
        #     "Account{%s}->Year{%s}->Scenario{%s}->"
        #     "Measure{%s}->Period{%s}->Entity{%s}->"
        #     "Version{%s}->Material{%s}->Department{%s}->"
        #     "Allocation{%s}->Tax{%s}->Misc1{%s}->"
        #     "Misc2{%s}"
        # )
        self.fix = (
            "Entity_GL{%s}->Account_lirun{%s}->Year{%s}->"
            "Scenario{%s}->Period{%s}->Measure{%s}->"
            "Version{%s}->"
            "Comprehensive{%s}->Commercial{%s}->Misc1{%s}->"
            "Misc2{%s}"
        )

    def get_account_p2(self, p2):
        print('方法1开始，判断是哪张表 ----------')

        # ===================== 核心：在这里配置 表名 → 对应值 =====================
        sheet_account_map = {
            # "人力预算": "IDescendant(PL600601,0);IDescendant(PL60020201,0);IDescendant(PL600701,0);IDescendant(PL600801,0);PL60060215;PL60070313;PL60060213;PL60070312;PL6006020601;PL6007030601",
            "人力预算": "Base(PL600601,0);Base(PL60020201,0);Base(PL600701,0);Base(PL600801,0);PL60060215;PL60070313;PL60060213;PL60070312;PL6006020601;PL6007030601",
            "收入预算": "Base(PL600102,0)",
            "成本预算": "Base(PL60020202,0)",
            "销售费用预算": "Base(PL600703,0)",
            "12号解释准则调整": "Base(PL6015,0)",
            "管理费用预算": "Base(PL600602,0)",
            "非付现成本&非付现费用": "Base(PL6012,0);Base(PL6013,0);Base(PL6014,0);Base(PL6028,0)",
            # "利息收入&财务费用": "Base(PL601102,0);Base(PL6018,0);PL601505",
            # "利息收入&财务费用": "Base(PL601102,0);Base(PL6018,0);Base(PL601505,0)",
            "利息收入&财务费用预算": "Base(PL601102,0);Base(PL6018,0);Base(PL601505,0)",
            "税费预算": "Base(PL6003,0);Base(PL6002010305,0);Base(PL60060211,0);Base(QT0106,0);Base(QT03,0)",
            "其他经营&非经营费用净额": "Base(PL6005,0);Base(PL6010,0)",
            "研发费用预算": "Base(PL600802,0)",
            # "一次性及正向清单": "？？？",

            # 非四大区
            "管理费用": "Base(PL600602,0);Base(PL6013,0)",
            "研发费用": "Base(PL6008,0);Base(PL6028,0)",
            "税费": "Base(PL6003,0);Base(PL6019,0);QT0106;QT0101;PL60060211;QT0109",
            "人力": "YW0901;YW090201;Base(PL600601,0);Base(PL60020201,0)",
        }

        # 获取当前表名
        current_sheet = p2["sheetName"]
        print(current_sheet)

        # 从字典中匹配对应的值（找不到就给空字符串，避免报错）
        p2["Account_wb1"] = sheet_account_map.get(current_sheet, "")

        # 删除不需要的字段
        # del p2["sheetName"]
        # del p2["sheetId"]

        print('方法1结束 ------')
        print('p2 =', p2)
        return p2

    def amount_sum(self, pov, year, tax_var , fc_var1, fc_var2, fc_var3):
        print('方法1开始 实际数全年按月汇总 ----------')
        # 1. 删除旧的全年合计数据（Actual/Noperiod）
        del_fix = self.fix % (
            pov["Entity_GL_wb1"],
            pov["Account_wb1"],
            year,
            "Actual",
            "Noperiod",
            "Expenses",
            pov["Version_wb1"],
            # pov["Comprehensive_wb1"],
            tax_var,
            pov["Commercial_wb1"],
            pov["Misc1_wb1"],
            pov["Misc2_wb1"],
        )
        print(del_fix)
        cube_.delete(cube_name=self.cube, expression=del_fix)
        print('删cube 实际-金额-全年 ----------')

        # 2. 根据三个变量判断月份范围
        # actual的月份（取Actual场景）和forecast的月份（取Forecast场景）
        actual_months = []
        forecast_months = []

        # 10月
        if fc_var1 == "Actual":
            actual_months.append("10")
        else:
            forecast_months.append("10")
        # 11月
        if fc_var2 == "Actual":
            actual_months.append("11")
        else:
            forecast_months.append("11")
        # 12月
        if fc_var3 == "Actual":
            actual_months.append("12")
        else:
            forecast_months.append("12")

        # 1-9月永远是Actual场景
        actual_months += ["1", "2", "3", "4", "5", "6", "7", "8", "9"]
        print(f"Actual月份：{actual_months}")
        print(f"Forecast月份：{forecast_months}")

        # 3. 分别查询Actual和Forecast的数据
        calc_data_df = pd.DataFrame()

        # 查Actual场景数据
        if actual_months:
            actual_fix = self.fix % (
                pov["Entity_GL_wb1"],
                pov["Account_wb1"],
                year,
                "Actual",
                ";".join(actual_months),
                "Expenses",
                pov["Version_wb1"],
                # pov["Comprehensive_wb1"],
                tax_var,
                pov["Commercial_wb1"],
                pov["Misc1_wb1"],
                pov["Misc2_wb1"],
            )
            print('查cube 实际-金额 实际月份 ----------')
            actual_df = cube_.query_cube(cube_name=self.cube, fix=actual_fix)
            calc_data_df = pd.concat([calc_data_df, actual_df])

        # 查Forecast场景数据
        if forecast_months:
            forecast_fix = self.fix % (
                pov["Entity_GL_wb1"],
                pov["Account_wb1"],
                year,
                "Forecast",
                ";".join(forecast_months),
                "Expenses",
                pov["Version_wb1"],
                # pov["Comprehensive_wb1"],
                tax_var,
                pov["Commercial_wb1"],
                pov["Misc1_wb1"],
                pov["Misc2_wb1"],
            )
            print('查cube 预测-金额 预测月份 ----------')
            forecast_df = cube_.query_cube(cube_name=self.cube, fix=forecast_fix)
            calc_data_df = pd.concat([calc_data_df, forecast_df])

        # 4. 无数据直接结束
        if calc_data_df.empty:
            print('---------------------目前cube中无实际/预测数据，方法提前结束 -------------------------')
            return

        # 5. 汇总求和并写回cube
        calc_data_df["Period"] = "Noperiod"
        calc_data_df["Scenario"] = "Actual"
        calc_data_df = calc_data_df.groupby(
            by=[
                "Entity_GL",
                "Account_lirun",
                "Year",
                "Scenario",
                "Measure",
                "Period",
                "Version",
                "Comprehensive",
                "Commercial",
                "Misc1",
                "Misc2",
            ],
            as_index=False,
        ).sum()
        # 存数
        cube_.save_cube(cube_name=self.cube, df=calc_data_df)
        print('方法1结束 ----------')

    def calc_rate(self, pov, year, scenario, period):
        print('----------- 方法4开始 计算税率 本方法删不含税   获取当前科目Tax值，转换为Notax存储   -------------')
        # 获取税率信息
        rate_fix = self.fix % (
            pov["Account_wb1"],
            year,
            scenario,
            "Expenses",
            period,
            pov["Entity_wb1"],
            pov["Version_wb1"],
            pov["Material_wb1"],
            pov["Department_wb1"],
            pov["Allocation_wb1"],
            "Taxrate",
            pov["Misc1_wb1"],
            pov["Misc2_wb1"],
        )
        print('查cube 税率信息 ------------')
        rate_df = cube_.query_cube(cube_name=self.cube, fix=rate_fix)
        # 查出实际税率，当月份为1-12月时，给预测用
        if scenario == "Actual" and period == "Base(Oct,0)":
            scenario = "Forecast"
        # 删除数据  删不含税    将可以前端填报的含税数，转换一份不含税版本存cube
        del_fix = self.fix % (
            pov["Account_wb1"],
            year,
            scenario,
            "Expenses",
            period,
            pov["Entity_wb1"],
            pov["Version_wb1"],
            pov["Material_wb1"],
            pov["Department_wb1"],
            pov["Allocation_wb1"],
            "Notax",
            pov["Misc1_wb1"],
            pov["Misc2_wb1"],
        )
        print('删cube 不含税-金额 ----------')
        cube_.delete(cube_name=self.cube, expression=del_fix)

        # 获取含税金额
        tax_fix = self.fix % (
            pov["Account_wb1"],
            year,
            scenario,
            "Expenses",
            period,
            pov["Entity_wb1"],
            pov["Version_wb1"],
            pov["Material_wb1"],
            pov["Department_wb1"],
            pov["Allocation_wb1"],
            "Tax",
            pov["Misc1_wb1"],
            pov["Misc2_wb1"],
        )
        print('查cube pov场景-含税金额 --------')
        tax_df = cube_.query_cube(cube_name=self.cube, fix=tax_fix)
        # 如果含税金额为空 则方法停止
        if tax_df.empty:
            print('----------------------目前cube中无含税金额     方法4提前结束 -------------------------')
            return
        # 删除税率 scenario、tax列
        rate_df = rate_df.drop(columns=["Scenario", "Tax"])
        # 更改税率 data列 列名
        rate_df = rate_df.rename(columns={"data": "rate"})
        # 关联税率，含税金额, 关联列为(除了 scenario 、tax 和数值列)。
        notax_df = pd.merge(tax_df, rate_df, how="left").fillna(0)
        notax_df["data"] = notax_df["data"] / (1 + notax_df["rate"])
        # 删除无用列
        del notax_df["rate"]
        # 将 inf 替换为 0
        notax_df = notax_df.replace([np.inf, -np.inf], 0)
        notax_df = notax_df.fillna(0)
        notax_df = notax_df.rename(
            columns={
                "Misc1": "Misc1",
                "Misc2": "Misc2",
            }
        )
        notax_df["Tax"] = "Notax"
        # 存数
        print('存cube 含税转换不含税 2025 1-12 预算数 ---------')
        cube_.save_cube(cube_name=self.cube, df=notax_df)

    # 取不含税，删原本含税，再重新计算含税    如果不含税为空，删完含税之后直接return      Tax=Notax*(1+TaxRate)
    # 计算并处理税率相关的实际数据，包括从cube中获取税率信息、不含税金额信息，进行数据关联计算得到含税金额，最后将处理后的数据保存回cube
    def calc_rate_actual(self, pov, year, scenario, period):
        print('方法2开始 计算税率-实际 ----------')
        # 获取税率信息
        rate_fix = self.fix % (
            pov["Account_wb1"],
            year,
            scenario,
            "Expenses",
            period,
            # pov["Entity_wb1"],
            pov["Entity_GL_wb1"],
            pov["Version_wb1"],
            pov["Material_wb1"],
            pov["Department_wb1"],
            pov["Allocation_wb1"],
            "Taxrate",
            pov["Misc1_wb1"],
            pov["Misc2_wb1"],
        )
        rate_df = cube_.query_cube(cube_name=self.cube, fix=rate_fix)
        print('查cube pov传入的所有科目的税率信息 税率--------')
        print(rate_df)
        # 删除数据  删含税金额
        del_fix = self.fix % (
            pov["Account_wb1"],
            year,
            scenario,
            "Expenses",
            period,
            pov["Entity_wb1"],
            pov["Version_wb1"],
            pov["Material_wb1"],
            pov["Department_wb1"],
            pov["Allocation_wb1"],
            "Tax",
            pov["Misc1_wb1"],
            pov["Misc2_wb1"],
        )
        cube_.delete(cube_name=self.cube, expression=del_fix)
        print('删cube 含税-金额--------')

        # 获取不含税金额
        tax_fix = self.fix % (
            pov["Account_wb1"],
            year,
            scenario,
            "Expenses",
            period,
            pov["Entity_wb1"],
            pov["Version_wb1"],
            pov["Material_wb1"],
            pov["Department_wb1"],
            pov["Allocation_wb1"],
            "Notax",
            pov["Misc1_wb1"],
            pov["Misc2_wb1"],
        )
        notax_df = cube_.query_cube(cube_name=self.cube, fix=tax_fix)
        print('查cube 实际-不含税-金额 ---------')
        print(notax_df)
        # 如果不含税金额为空 则方法停止
        if notax_df.empty:
            print('--------------------------- 目前cube中无不含税金额    方法2提前结束 -----------------------')
            return
        # 删除税率 scenario、tax列
        rate_df = rate_df.drop(columns=["Scenario", "Tax"])
        # 更改税率 data列 列名
        rate_df = rate_df.rename(columns={"data": "rate"})
        # 关联税率，不含税金额, 关联列为(除了 scenario 、tax 和数值列)。   left join
        tax_df = pd.merge(notax_df, rate_df, how="left").fillna(0)
        tax_df["data"] = tax_df["data"] * (1 + tax_df["rate"])
        # 删除无用列
        del tax_df["rate"]
        # 将 inf 替换为 0
        tax_df = tax_df.replace([np.inf, -np.inf], 0)
        tax_df = tax_df.fillna(0)
        tax_df = tax_df.rename(
            columns={
                "Misc1": "Misc1",
                "Misc2": "Misc2",
            }
        )
        tax_df["Tax"] = "Tax"
        print(tax_df)
        print('----------- 存cube 含税-金额 ------------')
        # 存数
        cube_.save_cube(cube_name=self.cube, df=tax_df)
        # print('存cube ---------')
        # print(notax_df)
        # print('方法2结束 ---------')

    def calc_cost(self, pov, year, scenario):
        # 删除数据
        del_fix = self.fix % (
            "YW0404;YW0412",
            year,
            scenario,
            "Unit",
            "Noperiod",
            "IDescendant(1,0)",
            pov["Version_wb1"],
            pov["Material_wb1"],
            pov["Department_wb1"],
            pov["Allocation_wb1"],
            "Notax",
            pov["Misc1_wb1"],
            pov["Misc2_wb1"],
        )
        cube_.delete(cube_name=self.cube, expression=del_fix)

        # 获取基础生产数据 合计实际处理水量     查另一张表
        vol_fix = self.fix % (
            "YW0205",
            year,
            scenario,
            "Nomeasure",
            "Noperiod",
            "IDescendant(1,0)",
            pov["Version_wb1"],
            pov["Material_wb1"],
            pov["Department_wb1"],
            pov["Allocation_wb1"],
            "Tax",
            pov["Misc1_wb1"],
            pov["Misc2_wb1"],
        )
        vol_df = cube_.query_cube(cube_name=self.cube, fix=vol_fix)
        del vol_df["Measure"]
        del vol_df["Tax"]
        del vol_df["Account"]
        vol_df = vol_df.rename(columns={"data": "yw0205"})

        # 获取检验化验费、其他成本
        jq_fix = self.fix % (
            "PL010206;PL010218",
            year,
            scenario,
            "Expenses",
            "Noperiod",
            "IDescendant(1,0)",
            pov["Version_wb1"],
            pov["Material_wb1"],
            pov["Department_wb1"],
            pov["Allocation_wb1"],
            "Notax",
            pov["Misc1_wb1"],
            pov["Misc2_wb1"],
        )
        jq_df = cube_.query_cube(cube_name=self.cube, fix=jq_fix)
        jq_df["Measure"] = "Unit"
        # on 除去 measure tax account
        jq_vol_df = pd.merge(jq_df, vol_df, how="left").fillna(0)
        # 计算
        jq_vol_df["data"] = jq_vol_df["data"] / jq_vol_df["yw0205"]
        del jq_vol_df["yw0205"]
        # 将 inf 替换为 0
        jq_vol_df = jq_vol_df.replace([np.inf, -np.inf], 0)
        jq_vol_df = jq_vol_df.fillna(0)
        jq_vol_df = jq_vol_df.rename(
            columns={
                "Misc1": "Misc1",
                "Misc2": "Misc2",
            }
        )
        jq_vol_df.loc[jq_vol_df["Account"] == "PL010218", "Account"] = "YW0412"
        jq_vol_df.loc[jq_vol_df["Account"] == "PL010206", "Account"] = "YW0404"
        # 存数
        cube_.save_cube(cube_name=self.cube, df=jq_vol_df)

    def calc_increase(self, pov, year, last_year, account, scenario):
        fix_year = "%s;%s" % (year, last_year)

        del_fix = self.fix % (
            account,
            fix_year,
            scenario,
            "Increase;Riserate",
            "Noperiod",
            pov["Entity_wb1"],
            pov["Version_wb1"],
            pov["Material_wb1"],
            pov["Department_wb1"],
            pov["Allocation_wb1"],
            "Notax",
            pov["Misc1_wb1"],
            pov["Misc2_wb1"],
        )
        cube_.delete(cube_name=self.cube, expression=del_fix)

        query_fix = self.fix % (
            account,
            fix_year,
            scenario,
            "Expenses",
            "Noperiod",
            pov["Entity_wb1"],
            pov["Version_wb1"],
            pov["Material_wb1"],
            pov["Department_wb1"],
            pov["Allocation_wb1"],
            "Notax",
            pov["Misc1_wb1"],
            pov["Misc2_wb1"],
        )
        two_years_df = cube_.query_cube(
            cube_name=self.cube, fix=query_fix, pivot_dim="Year"
        )
        year_set = {year, last_year}
        diff_list = list(year_set.difference(two_years_df.columns))
        if two_years_df.empty:
            return
        if diff_list:
            year_set[diff_list] = [0] * len(diff_list)

        two_years_copy_df = two_years_df.copy()
        # 计算增长额
        two_years_df["data"] = two_years_df[year] - two_years_df[last_year]
        two_years_df["Measure"] = "Increase"
        # 计算增长率
        two_years_copy_df["data"] = (
                                            two_years_copy_df[year] - two_years_copy_df[last_year]
                                    ) / two_years_copy_df[last_year]
        two_years_copy_df["Measure"] = "Riserate"
        two_years_df = pd.concat([two_years_df, two_years_copy_df])

        # 将 inf 替换为 0
        two_years_df = two_years_df.replace([np.inf, -np.inf], 0)
        two_years_df = two_years_df.fillna(0)

        del two_years_df[year]
        del two_years_df[last_year]

        two_years_df["Year"] = year

        two_years_df = two_years_df.rename(
            columns={
                "Misc1": "Misc1",
                "Misc2": "Misc2",
            }
        )
        cube_.save_cube(cube_name=self.cube, df=two_years_df)

    def calc_noperiod_sum(self, pov, year, scenario, fc_var1, fc_var2, fc_var3):
        print('方法5开始 noperiod 不含税-年度汇总合计 ----------')

        # ==========================
        # 1. 删除旧数据（顺序 100% 匹配 fix）
        # ==========================
        del_fix = self.fix % (
            pov["Entity_GL_wb1"],
            pov["Account_wb1"],
            year,
            scenario,
            "Noperiod",
            "Expenses",
            pov["Version_wb1"],
            'NoTax',
            pov["Commercial_wb1"],
            pov["Misc1_wb1"],
            pov["Misc2_wb1"]
        )
        print('删cube 不含税全年旧数据-----------')
        cube_.delete(cube_name=self.cube, expression=del_fix)

        # ==========================
        # 2. 按三变量拆分月份
        # ==========================
        actual_months = []
        forecast_months = []

        if fc_var1 == "Actual":
            actual_months.append("10")
        else:
            forecast_months.append("10")

        if fc_var2 == "Actual":
            actual_months.append("11")
        else:
            forecast_months.append("11")

        if fc_var3 == "Actual":
            actual_months.append("12")
        else:
            forecast_months.append("12")

        actual_months += ["1", "2", "3", "4", "5", "6", "7", "8", "9"]

        print(f"Actual 月份: {actual_months}")
        print(f"Forecast 月份: {forecast_months}")

        # ==========================
        # 3. 查询所有数据，然后只保留 Notax（含税/不含税都能查）
        # ==========================
        df = pd.DataFrame()

        # 查询 Actual
        if actual_months:
            af = self.fix % (
                pov["Entity_GL_wb1"],
                pov["Account_wb1"],
                year,
                "Actual",
                ";".join(actual_months),
                "Expenses",
                pov["Version_wb1"],
                'NoTax',
                pov["Commercial_wb1"],
                pov["Misc1_wb1"],
                pov["Misc2_wb1"]
            )
            ad = cube_.query_cube(self.cube, fix=af)
            if not ad.empty:
                ad = ad[ad["Comprehensive"] == "Notax"]
            df = pd.concat([df, ad])

        # 查询 Forecast
        if forecast_months:
            ff = self.fix % (
                pov["Entity_GL_wb1"],
                pov["Account_wb1"],
                year,
                "Forecast",
                ";".join(forecast_months),
                "Expenses",
                pov["Version_wb1"],
                'NoTax',
                pov["Commercial_wb1"],
                pov["Misc1_wb1"],
                pov["Misc2_wb1"]
            )
            fd = cube_.query_cube(self.cube, fix=ff)
            if not fd.empty:
                fd = fd[fd["Comprehensive"] == "Notax"]
            df = pd.concat([df, fd])

        # ==========================
        # 4. 只要有任意一个月数据，就能算出全年！
        # ==========================
        if df.empty:
            print("❌ 无任何不含税数据")
            return

        # ==========================
        # 5. 正确汇总（必须包含 Tax）
        # ==========================
        df["Period"] = "Noperiod"
        df["Scenario"] = scenario
        df = df.groupby([
            "Entity_GL", "Account_lirun", "Year", "Scenario",
            "Measure", "Period", "Version",
            "Comprehensive", "Commercial", "Misc1", "Misc2", "Tax"
        ], as_index=False)["data"].sum()

        print(f"✅ 不含税全年计算成功：\n{df}")
        cube_.save_cube(self.cube, df=df)
        print("方法5结束 -----------")

    def amount_sum2(self, pov, year, fc_var):
        print(
            '方法4 开始 --------- 四期新增-预算年-预算数-检验化验费、其他成本 含税金额按月汇总至全年Noperiod ----------')
        # 删除已存在的数据
        del_fix = self.fix % (
            pov["Account_wb1"],
            year,
            "Budget",
            "Expenses",
            "Noperiod",
            pov["Entity_wb1"],
            pov["Version_wb1"],
            pov["Material_wb1"],
            pov["Department_wb1"],
            pov["Allocation_wb1"],
            pov["Tax_wb1"],
            pov["Misc1_wb1"],
            pov["Misc2_wb1"],
        )
        cube_.delete(cube_name=self.cube, expression=del_fix)
        print('删cube 预算数-金额-全年 ----------')
        calc_data_df = pd.DataFrame()
        if fc_var == "Forecast":
            # 获取1-9月 Budget数据
            fc_actual_fix = self.fix % (
                pov["Account_wb1"],
                year,
                "Budget",
                "Expenses",
                "1;2;3;4;5;6;7;8;9",
                pov["Entity_wb1"],
                pov["Version_wb1"],
                pov["Material_wb1"],
                pov["Department_wb1"],
                pov["Allocation_wb1"],
                pov["Tax_wb1"],
                pov["Misc1_wb1"],
                pov["Misc2_wb1"],
            )
            fc_actual_df = cube_.query_cube(cube_name=self.cube, fix=fc_actual_fix)
            print('查cube 预算-金额 1-9月 ----------')
            # 获取10-12月Budget数据
            fc_forecast_fix = self.fix % (
                pov["Account_wb1"],
                year,
                "Budget",
                "Expenses",
                "10;11;12",
                pov["Entity_wb1"],
                pov["Version_wb1"],
                pov["Material_wb1"],
                pov["Department_wb1"],
                pov["Allocation_wb1"],
                pov["Tax_wb1"],
                pov["Misc1_wb1"],
                pov["Misc2_wb1"],
            )
            print('查cube 预测数-金额 10-12月 ----------')
            fc_forecast_df = cube_.query_cube(cube_name=self.cube, fix=fc_forecast_fix)
            calc_data_df = pd.concat([fc_actual_df, fc_forecast_df])
            print('合并数据 ----------')
            print(calc_data_df)

        elif fc_var == "Actual":
            # 获取1-12月 Budget数据
            actual_fix = self.fix % (
                pov["Account_wb1"],
                year,
                "Budget",
                "Expenses",
                "1;2;3;4;5;6;7;8;9;10;11;12",
                pov["Entity_wb1"],
                pov["Version_wb1"],
                pov["Material_wb1"],
                pov["Department_wb1"],
                pov["Allocation_wb1"],
                pov["Tax_wb1"],
                pov["Misc1_wb1"],
                pov["Misc2_wb1"],
            )
            print('查cube 预算-金额 1-12月 ----------')
            calc_data_df = cube_.query_cube(cube_name=self.cube, fix=actual_fix)
            # print(calc_data_df)

        if calc_data_df.empty:
            print(calc_data_df)
            print('---------------------目前cube中无 预算数-金额 1-12月    方法3提前结束 -------------------------')
            return
            # 汇总求和
        calc_data_df["Period"] = "Noperiod"
        calc_data_df["Scenario"] = "Budget"
        calc_data_df = calc_data_df.groupby(
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
        calc_data_df = calc_data_df.rename(
            columns={
                "Misc1": "Misc1",
                "Misc2": "Misc2",
            }
        )
        # 存数
        cube_.save_cube(cube_name=self.cube, df=calc_data_df)
        print('---------- 方法4结束 ----------')

    # 新增需求：应该是预算年实际数的Noperiod全年合计复制到TotalPeriod？
    # def copy_noperiod_to_totalPeriod(self, pov, year, scenario, period):


def main(p1, p2):
    print('主程序方法main开始 -------')
    print('p2 =' + str(p2))
    begin = time.time()
    if "Material_wb1" not in p2:
        p2['Material_wb1'] = "Nomaterial"
    if "Material_wb1" not in p2:
        p2["Material_wb1"] = "Nomaterial"
    if "Allocation_wb1" not in p2:
        p2["Allocation_wb1"] = "Original"

    # 因为正常四大区表的税率筛选器的sheet页级别筛选器 Comprehensive_st1 ,没有wb1，就默认补一个
    if "Comprehensive_wb1" not in p2:
        p2["Comprehensive_wb1"] = "Tax"
    # if "Misc1_wb1" not in p2:
    #     p2["Misc1_wb1"] = "Nomisc1"
    # if "Misc2_wb1" not in p2:
    #     p2["Misc2_wb1"] = "Nomisc2"
    # 获取变量
    var = Variable("Variable")
    fc_var1 = var.get_value("10_scenario")
    fc_var2 = var.get_value("11_scenario")
    fc_var3 = var.get_value("12_scenario")
    year = p2["Year_wb1"]
    last_year = str(int(p2["Year_wb1"]) - 1)
    last_two_year = str(int(p2["Year_wb1"]) - 2)
    # 根据表单名称 确定执行检验化验费 还是 其他成本。     新表无需判断
    itoa = ITOA()
    p2 = itoa.get_account_p2(p2)
    # 计算去年税率Actual      清2024 1-12含税，查税率 + 不含税，重新计算含税并写入cube
    # itoa.calc_rate_actual(pov=p2, year=last_year, scenario="Actual", period="1;2;3;4;5;6;7;8;9;10;11;12")

    # 需求1 PY计算：实际数的全年合计的计算，保存后运行    按月汇总至实际年-实际数全年
    # 无含税不含税区分,仅看保存时当前筛选器的值为含税还是不含税

    # ==============================================
    # 🔹 只有 收入预算 / 成本预算 才执行第一个合计
    # ==============================================
    # current_sheet = para2.get("sheetName", "")  # 表名
    current_sheet = p2.get("sheetName", "")  # 表名
    print(current_sheet)

    if current_sheet in ["收入预算", "成本预算"]:

        # 根据筛选器是否为含税，区分 正常四大区表 和 非四大区表
        tax_var = p2["Comprehensive_wb1"]
        print(tax_var)
        if tax_var == "Tax":
            print('--------------- 当前筛选器为含税，证明当前表单为正常四大区表，启动含税全年合计计算 --------------')
            itoa.amount_sum(pov=p2, year=last_year, tax_var=tax_var, fc_var1=fc_var1, fc_var2=fc_var2, fc_var3=fc_var3)
    else:
        print("✅ 非收入/成本表，跳过第一个全年合计")

    # *四期新增 预算数-含税 1-12月合计汇总至预算年-全年Noperiod  存cube
    # itoa.amount_sum2(pov=p2, year=year, fc_var="Actual")

    # 需求3、税率计算：1）获取税率   2）获取当前科目Tax值，转换为Notax存储
    # 计算税率  去年 10,11,12 实际  +  本年 1-12 预算  +  本年
    # itoa.calc_rate(pov=p2, year=last_year, scenario="Actual", period="Base(Oct,0)")
    # itoa.calc_rate(
    #     pov=p2, year=year, scenario="Budget", period="1;2;3;4;5;6;7;8;9;10;11;12"
    # )
    # 求去年的批复新增  税率 - 全年
    # itoa.calc_rate(pov=p2, year=last_year, scenario="New", period="Noperiod")
    # itoa.calc_rate(pov=p2, year=last_year, scenario="Actual", period="1;2;3;4;5;6;7;8;9;10;11;12")
    # noperiod 不含税 - 汇总 - 全年

    # ==============================================
    # 🔹 第二个（不含税）所有表都执行
    # ==============================================
    tax_var = 'NoTax'
    itoa.amount_sum(pov=p2, year=last_year, tax_var=tax_var, fc_var1=fc_var1, fc_var2=fc_var2, fc_var3=fc_var3)
    # itoa.calc_noperiod_sum(pov=p2, year=last_year, scenario="Actual", fc_var=fc_var)
    # itoa.calc_noperiod_sum(pov=p2, year=last_year, scenario="Actual", fc_var1=fc_var1, fc_var2=fc_var2, fc_var3=fc_var3)
    # itoa.calc_noperiod_sum(pov=p2, year=year, scenario="Budget", fc_var="Actual")

    # 新增需求：计算并转化 预算年 1-12 不含税-实际数 -> 含税 存储
    # itoa.calc_rate_actual(pov=p2, year=year, scenario="Actual", period="1;2;3;4;5;6;7;8;9;10;11;12")

    print("主体：", time.time() - begin)

    # 检验化验费其他成本审计指标计算    Unit
    # audit = time.time()
    # from biz.finance.new_unit001 import main as main_audit
    # main_audit(p1, p2)
    # print("审核：", time.time() - audit)
    # # 计算毛利毛利率
    # gross = time.time()
    # from biz.phaseII.newly.gross_margin_calc import main as main_gross
    # main_gross(p1, p2)
    # print("毛利：", time.time() - gross)


if __name__ == "__main__":
    try:
        # from biz.config._debug import para1, para2
        # from biz.config._debug import para1, para2
        from CWYS._debug import para1, para2
    except:
        pass
    para2 = {'elementName': 'Revenue_budget_QT',
             'folderId': 'DIR5300240dd640',
             'sheetName': '收入预算',
             'sheetId': 'SHTd4d4547cf91945f39a137227d4a94d6c',
             'Year_wb1': '2026',
             'Entity_GL_wb1': 'Base(D000001,0)',
             'Version_wb1': 'V1',
             'Commercial_wb1': 'YT990101',
             'Misc1_wb1': 'nomisc1',
             'Misc2_wb1': 'nomisc2',
             'Comprehensive_st1': 'Tax'}

    main(para1, para2)
