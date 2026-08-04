"""
added by wlm
added in 20230807
added for 支付计划同步数据逻辑
主要逻辑：
    见：https://proinnova.yuque.com/zpkolg/edn0y5/hrb69esg12lnmsp1#LScb
剩余问题：
"""

from common.commons import *
from deepfos.element.finmodel import FinancialCube
from conf.config import key_map
from deliver_plan import *


import datetime
import pandas as pd


class consruction_zf:
    def __init__(self):
        # 初始化源、目标表名、历史数据表名
        self.source_table = "Construction_ZF"
        self.log_table = "Construction_ZF_log"
        self.source_url = "/ETL/Form_Business/"

        self.target_table = "2_Construction_ZF"
        self.basic_table = "Basic_Data_Full"
        self.target_url = "/Form/0_Business_Model/Full_Business_Model/"

        self.cube_name = "CUBE_BEWG"
        self.cube_url = "/Cube/"

        self.cube = FinancialCube(element_name="CUBE_BEWG", path="/Cube/")

        # 获取年份变量
        self.year = var_.get_variable("Variable", "Year")

        period = str(datetime.datetime.now().month)
        self.key = key_map[period]
        print(self.key)
        # 获取中间表数据
        df_data = rdb_.select(None, self.source_table, path=self.source_url)
        # 保存一下源表的字段
        self.cols = df_data.columns.drop(["_id"]).to_list()
        # 翻译大区、区域、法人公司
        dict_mapping = get_org_mapping()
        df_data["Region_ZF"] = df_data["Region_ZF"].map(dict_mapping)
        df_data["Regional_Company_ZF"] = df_data["Regional_Company_ZF"].map(
            dict_mapping
        )

        # 翻译Account维度
        dict_acc = get_account_mapping()
        df_data["Account"] = df_data["Account_ZF"].map(dict_acc)
        # 去掉Account为空的数据
        df_data = df_data[~pd.isnull(df_data["Account"])]

        # 处理数据
        if df_data.empty:
            self.source_data = pd.DataFrame()
        else:
            # self.source_data = control_df(df_data, "Entity_Construction_ZF", "支付计划")
            source_data = control_df(df_data, "Entity_Construction_ZF", "支付计划")
            if not source_data.empty:
                self.source_data = source_data.loc[source_data["name"].str.startswith("J")]
            else:
                self.source_data = pd.DataFrame()

    def save_business_data(self):
        """
        保存业务数据到主表及子表
        """
        # 判断，如果中间表数据为空，则直接返回
        if self.source_data.empty:
            print("支付计划中间表数据为空！")
            return
        # 保存主表数据
        # col = [
        #     "name",
        #     "Year",
        #     "Region_ZF",
        #     "Regional_Company_ZF",
        #     "parent_name",
        #     "Entity_Name_ZF",
        #     "Format_1_ZF",
        #     "Format_2_ZF",
        #     "Investment_ZF",
        # ]
        # df_basic = self.source_data[col].rename(
        #     columns={
        #         "name": "Entity_Number",
        #         "Region_ZF": "Region",
        #         "Regional_Company_ZF": "Regional_Company",
        #         "parent_name": "Incorporated_Company",
        #         "Entity_Name_ZF": "Entity_Name",
        #         "Format_1_ZF": "Format_1",
        #         "Format_2_ZF": "Format_2",
        #         "Investment_ZF": "Investment",
        #     }
        # )
        #
        # # 设置更新列
        # updatecol = list(set(df_basic.columns.drop(["Year", "Entity_Number"])))
        #
        # df_basic["Version"] = "WorkVersion"
        #
        # # 保存目标数据
        # rdb_.insert_sql(
        #     self.basic_table, df_basic, path=self.target_url, updatecol=updatecol
        # )

        # 保存子表数据
        col = [
            "name",
            "Year",
            "Scenario",
            "Entity_Construction_ZF",
            "Entity_Name_ZF",
            "Project_Status",
            "NYYXJS",
            "Construction_Type",
            "Account",
            "Y1_TotalYear_YCZ_M",
            "Y1_YCZ_Q1",
            "Y1_YCZ_Q2",
            "Y1_YCZ_Q3",
            "Y1_YCZ_Q4",
            "Y1_YCZ_Total_Q",
            "Y1_TotalYear_NCZ_M",
            "Y1_NCZ_Q1",
            "Y1_NCZ_Q2",
            "Y1_NCZ_Q3",
            "Y1_NCZ_Q4",
            "Y1_NCZ_Total_Q",
            "ETL_Audit_Status",
            "AccumulateZF_Total",
        ]
        df_consru = self.source_data[col].rename(
            columns={
                "name": "Entity_Number",
                "Entity_Construction_ZF": "Entity_Construction",
                "Entity_Name_ZF": "Entity_Name",
                "Account": "Account",
                "ETL_Audit_Status": "Examine_Status",
                "Y1_NCZ_Total_Q": "Y1_TotalYear_NCZ_Q",
                "Y1_YCZ_Total_Q": "Y1_TotalYear_YCZ_Q",
            }
        )
        df_consru["Version"] = "WorkVersion"
        updatecol = list(
            set(
                df_consru.columns.drop(
                    [
                        "Year",
                        "Scenario",
                        "Entity_Number",
                        "Entity_Construction",
                        "Account",
                        "Version",
                    ]
                )
            )
        )

        rdb_.insert_sql(
            self.target_table, df_consru, path=self.target_url, updatecol=updatecol
        )

        # 调用二次计算方法，计算相关字段
        self.calc_business_data_twice(df_consru)

        # 保存同步日志表
        df_log = self.source_data[self.cols]
        df_log["ETL_Datetime"] = datetime.datetime.now()

        updatecol = list(
            set(
                df_log.columns.drop(
                    [
                        "Year",
                        "Scenario",
                        "Entity_Construction_ZF",
                        "Account_ZF",
                    ]
                )
            )
        )

        rdb_.insert_sql(
            self.log_table, df_log, path=self.source_url, updatecol=updatecol
        )

        return "目标表数据同步成功！"

    def calc_business_data_twice(self, df):
        """
        支付计划同步到二维表后，二次计算逻辑
        """
        # 本次计算只针对科目为A01的数据
        df_acc = dim_.get_dim_attr(
            "Account", "Base(A01,0)", ["name"], path="/Dimension/"
        )
        list_acc = list(set(df_acc["name"]))
        df = df[df["Account"].isin(list_acc)]
        # 获取产值数据
        col = [
            "Year",
            "Entity_Number",
            "Entity_Construction",
            "Scenario",
            "Account",
            "Y1_Total_M",
            "Y1_Total_Q",
            "ZT_DQKJ",
            "ZT_TPNK",
            "Entity_Name",
            "Project_Status",
            "NYYXJS",
            "Construction_Type",
            "Examine_Status",
            "Version",
        ]
        df_cz = rdb_.select(col, "2_Construction_CZ", path=self.target_url)
        # 将产值与支付数据关联到一起
        df = pd.merge(
            df,
            df_cz,
            how="inner",
            on=[
                "Year",
                "Entity_Number",
                "Entity_Construction",
                "Scenario",
                "Account",
                "Version",
            ],
        ).rename(
            columns={
                "Entity_Name_x": "Entity_Name",
                "Project_Status_x": "Project_Status",
                "NYYXJS_x": "NYYXJS",
                "Construction_Type_x": "Construction_Type",
                "Examine_Status_x": "Examine_Status",
            }
        )
        # 将Account 设置为A01
        df["Account"] = "A01"
        # 获取保留字段
        col = col + [
            "Y1_TotalYear_YCZ_M",
            "Y1_TotalYear_NCZ_M",
            "Y1_TotalYear_YCZ_Q",
            "Y1_TotalYear_NCZ_Q",
            "AccumulateZF_Total",
        ]
        col1 = [
            "Y1_Total_M",
            "Y1_Total_Q",
            "ZT_DQKJ",
            "ZT_TPNK",
            "Y1_TotalYear_YCZ_M",
            "Y1_TotalYear_NCZ_M",
            "Y1_TotalYear_YCZ_Q",
            "Y1_TotalYear_NCZ_Q",
            "AccumulateZF_Total",
        ]

        # 设置保留字段并将空值赋值为0
        for i in col1:
            df[i] = df[i].fillna(0)
        # 分组汇总
        df = df.groupby(
            by=[
                "Year",
                "Entity_Number",
                "Entity_Construction",
                "Scenario",
                "Account",
                "Entity_Name",
                "Project_Status",
                "NYYXJS",
                "Construction_Type",
                "Examine_Status",
                "Version",
            ],
            as_index=False,
        ).sum()

        def calc_data(row):
            if row["Scenario"] == "Year":
                # 当期产值支付率
                if row["Y1_Total_M"] != 0:
                    row["DQCZZFL"] = (row["Y1_TotalYear_YCZ_M"]) / row["Y1_Total_M"]
                # 剩余未支付金额
                row["SYWZFJE"] = row["ZT_DQKJ"] - (
                    row["AccumulateZF_Total"]
                    + row["Y1_TotalYear_YCZ_M"]
                    + row["Y1_TotalYear_NCZ_M"]
                )
                # 综合产值支付率
                if row["ZT_TPNK"] != 0:
                    row["ZHCZZFL"] = (
                        row["Y1_TotalYear_YCZ_M"] + row["Y1_TotalYear_NCZ_M"]
                    ) / row["ZT_TPNK"]
            elif row["Scenario"] in ["Q2", "Q3", "Q4"]:
                # 当期产值支付率
                if row["Y1_Total_Q"] != 0:
                    row["DQCZZFL"] = (row["Y1_TotalYear_YCZ_Q"]) / row["Y1_Total_Q"]
                # 剩余未支付金额
                row["SYWZFJE"] = row["ZT_DQKJ"] - (
                    row["AccumulateZF_Total"]
                    + row["Y1_TotalYear_YCZ_Q"]
                    + row["Y1_TotalYear_NCZ_Q"]
                )
                # 综合产值支付率
                if row["ZT_TPNK"] != 0:
                    row["ZHCZZFL"] = (
                        row["Y1_TotalYear_YCZ_Q"] + row["Y1_TotalYear_NCZ_Q"]
                    ) / row["ZT_TPNK"]
            return row

        # 添加计算列并根据逻辑计算
        df["DQCZZFL"] = df["SYWZFJE"] = df["ZHCZZFL"] = 0
        df = df.apply(calc_data, axis=1)
        # 规范字段后入库
        df = df[
            [
                "Year",
                "Entity_Number",
                "Entity_Construction",
                "Entity_Name",
                "Project_Status",
                "NYYXJS",
                "Construction_Type",
                "Examine_Status",
                "Scenario",
                "Account",
                "DQCZZFL",
                "SYWZFJE",
                "ZHCZZFL",
                "Version",
            ]
        ]
        rdb_.insert_sql(
            self.target_table,
            df,
            path=self.target_url,
            updatecol=[
                "DQCZZFL",
                "SYWZFJE",
                "ZHCZZFL",
                "Entity_Name",
                "Project_Status",
                "NYYXJS",
                "Construction_Type",
                "Examine_Status",
            ],
        )

    def save_cube_data(self):
        """
        保存数据到cube中
        """
        if self.source_data.empty:
            print("支付计划中间表数据为空！")
            return

        # 处理总投信息
        col = [
            "Year",
            "Scenario",
            "name",
            "Account",
            "Full_ZF_Plan",
            "AccumulateZF_Total",
            "Q4_YCZZF",
            "Q4_NCZZF",
            "Y1_YCZ_Jan",
            "Y1_YCZ_Feb",
            "Y1_YCZ_Mar",
            "Y1_YCZ_Api",
            "Y1_YCZ_May",
            "Y1_YCZ_Jun",
            "Y1_YCZ_Jul",
            "Y1_YCZ_Aug",
            "Y1_YCZ_Sep",
            "Y1_YCZ_Oct",
            "Y1_YCZ_Nov",
            "Y1_YCZ_Dec",
            "Y1_YCZ_Q1",
            "Y1_YCZ_Q2",
            "Y1_YCZ_Q3",
            "Y1_YCZ_Q4",
            "Y1_NCZ_Jan",
            "Y1_NCZ_Feb",
            "Y1_NCZ_Mar",
            "Y1_NCZ_Api",
            "Y1_NCZ_May",
            "Y1_NCZ_Jun",
            "Y1_NCZ_Jul",
            "Y1_NCZ_Aug",
            "Y1_NCZ_Sep",
            "Y1_NCZ_Oct",
            "Y1_NCZ_Nov",
            "Y1_NCZ_Dec",
            "Y1_NCZ_Q1",
            "Y1_NCZ_Q2",
            "Y1_NCZ_Q3",
            "Y1_NCZ_Q4",
            "Y1_IN_YFWF",
            "Y1_IN_CZJT",
            "Y1_IN_JSK",
            "Y1_IN_ZBJ",
            "Y2_ZF_Q1",
            "Y2_ZF_Q2",
            "Y2_ZF_Q3",
            "Y2_ZF_Q4",
            "Y3_ZF_Q1",
            "Y3_ZF_Q2",
            "Y3_ZF_Q3",
            "Y3_ZF_Q4",
            "Y3_Residue_ZFPlan",
        ]
        df_zt = self.source_data[col].rename(columns={"name": "Entity"})
        # df_zt = df_zt[df_zt["Scenario"] != "Year"]

        # 将数据源从宽表转换成长表
        df_zt = pd.melt(
            df_zt, id_vars=["Scenario", "Year", "Entity", "Account"], var_name="Columns"
        )
        df_zt.loc[
            df_zt["Columns"].isin(
                [
                    "Y2_ZF_Q1",
                    "Y2_ZF_Q2",
                    "Y2_ZF_Q3",
                    "Y2_ZF_Q4",
                ]
            ),
            "Year",
        ] = (
            df_zt["Year"].astype(int) + 1
        )

        df_zt.loc[
            df_zt["Columns"].isin(
                ["Y3_ZF_Q1", "Y3_ZF_Q2", "Y3_ZF_Q3", "Y3_ZF_Q4", "Y3_Residue_ZFPlan"]
            ),
            "Year",
        ] = (
            df_zt["Year"].astype(int) + 2
        )

        df_zt.loc[
            df_zt["Columns"].isin(
                ["Full_ZF_Plan", "AccumulateZF_Total", "Q4_CZ_Plan", "Q4_NCZZF"]
            ),
            "Year",
        ] = (
            df_zt["Year"].astype(int) - 1
        )

        # df_zt.loc[
        #     df_zt["Columns"].isin(
        #         [
        #             "Y1_YCZ_Jan",
        #             "Y1_YCZ_Feb",
        #             "Y1_YCZ_Mar",
        #             "Y1_YCZ_Api",
        #             "Y1_YCZ_May",
        #             "Y1_YCZ_Jun",
        #             "Y1_YCZ_Jul",
        #             "Y1_YCZ_Aug",
        #             "Y1_YCZ_Sep",
        #             "Y1_YCZ_Oct",
        #             "Y1_YCZ_Nov",
        #             "Y1_YCZ_Dec",
        #             "Y1_YCZ_Q1",
        #             "Y1_YCZ_Q2",
        #             "Y1_YCZ_Q3",
        #             "Y1_YCZ_Q4",
        #             "Y1_NCZ_Jan",
        #             "Y1_NCZ_Feb",
        #             "Y1_NCZ_Mar",
        #             "Y1_NCZ_Api",
        #             "Y1_NCZ_May",
        #             "Y1_NCZ_Jun",
        #             "Y1_NCZ_Jul",
        #             "Y1_NCZ_Aug",
        #             "Y1_NCZ_Sep",
        #             "Y1_NCZ_Oct",
        #             "Y1_NCZ_Nov",
        #             "Y1_NCZ_Dec",
        #             "Y1_NCZ_Q1",
        #             "Y1_NCZ_Q2",
        #             "Y1_NCZ_Q3",
        #             "Y1_NCZ_Q4",
        #             "Y1_IN_YFWF",
        #             "Y1_IN_CZJT",
        #             "Y1_IN_JSK",
        #             "Y1_IN_ZBJ",
        #         ]
        #     ),
        #     "Year",
        # ] = (
        #     df_zt["Year"].astype(int) + 1
        # )

        # 准备转换字段map
        map_year = {
            "Full_ZF_Plan": self.year,
            "AccumulateZF_Total": self.year,
            "Q4_YCZZF": self.year,
            "Q4_NCZZF": self.year,
            "Y1_YCZ_Jan": str(int(self.year) + 1),
            "Y1_YCZ_Feb": str(int(self.year) + 1),
            "Y1_YCZ_Mar": str(int(self.year) + 1),
            "Y1_YCZ_Api": str(int(self.year) + 1),
            "Y1_YCZ_May": str(int(self.year) + 1),
            "Y1_YCZ_Jun": str(int(self.year) + 1),
            "Y1_YCZ_Jul": str(int(self.year) + 1),
            "Y1_YCZ_Aug": str(int(self.year) + 1),
            "Y1_YCZ_Sep": str(int(self.year) + 1),
            "Y1_YCZ_Oct": str(int(self.year) + 1),
            "Y1_YCZ_Nov": str(int(self.year) + 1),
            "Y1_YCZ_Dec": str(int(self.year) + 1),
            "Y1_YCZ_Q1": str(int(self.year) + 1),
            "Y1_YCZ_Q2": str(int(self.year) + 1),
            "Y1_YCZ_Q3": str(int(self.year) + 1),
            "Y1_YCZ_Q4": str(int(self.year) + 1),
            "Y1_NCZ_Jan": str(int(self.year) + 1),
            "Y1_NCZ_Feb": str(int(self.year) + 1),
            "Y1_NCZ_Mar": str(int(self.year) + 1),
            "Y1_NCZ_Api": str(int(self.year) + 1),
            "Y1_NCZ_May": str(int(self.year) + 1),
            "Y1_NCZ_Jun": str(int(self.year) + 1),
            "Y1_NCZ_Jul": str(int(self.year) + 1),
            "Y1_NCZ_Aug": str(int(self.year) + 1),
            "Y1_NCZ_Sep": str(int(self.year) + 1),
            "Y1_NCZ_Oct": str(int(self.year) + 1),
            "Y1_NCZ_Nov": str(int(self.year) + 1),
            "Y1_NCZ_Dec": str(int(self.year) + 1),
            "Y1_NCZ_Q1": str(int(self.year) + 1),
            "Y1_NCZ_Q2": str(int(self.year) + 1),
            "Y1_NCZ_Q3": str(int(self.year) + 1),
            "Y1_NCZ_Q4": str(int(self.year) + 1),
            "Y1_IN_YFWF": str(int(self.year) + 1),
            "Y1_IN_CZJT": str(int(self.year) + 1),
            "Y1_IN_JSK": str(int(self.year) + 1),
            "Y1_IN_ZBJ": str(int(self.year) + 1),
            "Y2_ZF_Q1": str(int(self.year) + 2),
            "Y2_ZF_Q2": str(int(self.year) + 2),
            "Y2_ZF_Q3": str(int(self.year) + 2),
            "Y2_ZF_Q4": str(int(self.year) + 2),
            "Y3_ZF_Q1": str(int(self.year) + 3),
            "Y3_ZF_Q2": str(int(self.year) + 3),
            "Y3_ZF_Q3": str(int(self.year) + 3),
            "Y3_ZF_Q4": str(int(self.year) + 3),
            "Y3_Residue_ZFPlan": str(int(self.year) + 3),
        }
        map_misc = {
            "Full_ZF_Plan": "CP_08",
            "AccumulateZF_Total": "CP_09",
            "Q4_YCZZF": "CP_0701",
            "Q4_NCZZF": "CP_0702",
            "Y1_YCZ_Jan": "CP_0701",
            "Y1_YCZ_Feb": "CP_0701",
            "Y1_YCZ_Mar": "CP_0701",
            "Y1_YCZ_Api": "CP_0701",
            "Y1_YCZ_May": "CP_0701",
            "Y1_YCZ_Jun": "CP_0701",
            "Y1_YCZ_Jul": "CP_0701",
            "Y1_YCZ_Aug": "CP_0701",
            "Y1_YCZ_Sep": "CP_0701",
            "Y1_YCZ_Oct": "CP_0701",
            "Y1_YCZ_Nov": "CP_0701",
            "Y1_YCZ_Dec": "CP_0701",
            "Y1_YCZ_Q1": "CP_0701",
            "Y1_YCZ_Q2": "CP_0701",
            "Y1_YCZ_Q3": "CP_0701",
            "Y1_YCZ_Q4": "CP_0701",
            "Y1_NCZ_Jan": "CP_0702",
            "Y1_NCZ_Feb": "CP_0702",
            "Y1_NCZ_Mar": "CP_0702",
            "Y1_NCZ_Api": "CP_0702",
            "Y1_NCZ_May": "CP_0702",
            "Y1_NCZ_Jun": "CP_0702",
            "Y1_NCZ_Jul": "CP_0702",
            "Y1_NCZ_Aug": "CP_0702",
            "Y1_NCZ_Sep": "CP_0702",
            "Y1_NCZ_Oct": "CP_0702",
            "Y1_NCZ_Nov": "CP_0702",
            "Y1_NCZ_Dec": "CP_0702",
            "Y1_NCZ_Q1": "CP_0702",
            "Y1_NCZ_Q2": "CP_0702",
            "Y1_NCZ_Q3": "CP_0702",
            "Y1_NCZ_Q4": "CP_0702",
            "Y1_IN_YFWF": "CP_1001",
            "Y1_IN_CZJT": "CP_1002",
            "Y1_IN_JSK": "CP_1003",
            "Y1_IN_ZBJ": "CP_1004",
            "Y2_ZF_Q1": "CP_07",
            "Y2_ZF_Q2": "CP_07",
            "Y2_ZF_Q3": "CP_07",
            "Y2_ZF_Q4": "CP_07",
            "Y3_ZF_Q1": "CP_07",
            "Y3_ZF_Q2": "CP_07",
            "Y3_ZF_Q3": "CP_07",
            "Y3_ZF_Q4": "CP_07",
            "Y3_Residue_ZFPlan": "CP_11",
        }
        map_period = {
            "Full_ZF_Plan": "NoPeriod",
            "AccumulateZF_Total": "NoPeriod",
            "Q4_YCZZF": "M4",
            "Q4_NCZZF": "M4",
            "Y1_YCZ_Jan": "January",
            "Y1_YCZ_Feb": "Febrary",
            "Y1_YCZ_Mar": "March",
            "Y1_YCZ_Api": "April",
            "Y1_YCZ_May": "May",
            "Y1_YCZ_Jun": "June",
            "Y1_YCZ_Jul": "July",
            "Y1_YCZ_Aug": "August",
            "Y1_YCZ_Sep": "September",
            "Y1_YCZ_Oct": "October",
            "Y1_YCZ_Nov": "November",
            "Y1_YCZ_Dec": "December",
            "Y1_YCZ_Q1": "M1",
            "Y1_YCZ_Q2": "M2",
            "Y1_YCZ_Q3": "M3",
            "Y1_YCZ_Q4": "M4",
            "Y1_NCZ_Jan": "January",
            "Y1_NCZ_Feb": "Febrary",
            "Y1_NCZ_Mar": "March",
            "Y1_NCZ_Api": "April",
            "Y1_NCZ_May": "May",
            "Y1_NCZ_Jun": "June",
            "Y1_NCZ_Jul": "July",
            "Y1_NCZ_Aug": "August",
            "Y1_NCZ_Sep": "September",
            "Y1_NCZ_Oct": "October",
            "Y1_NCZ_Nov": "November",
            "Y1_NCZ_Dec": "December",
            "Y1_NCZ_Q1": "M1",
            "Y1_NCZ_Q2": "M2",
            "Y1_NCZ_Q3": "M3",
            "Y1_NCZ_Q4": "M4",
            "Y1_IN_YFWF": "NoPeriod",
            "Y1_IN_CZJT": "NoPeriod",
            "Y1_IN_JSK": "NoPeriod",
            "Y1_IN_ZBJ": "NoPeriod",
            "Y2_ZF_Q1": "M1",
            "Y2_ZF_Q2": "M2",
            "Y2_ZF_Q3": "M3",
            "Y2_ZF_Q4": "M4",
            "Y3_ZF_Q1": "M1",
            "Y3_ZF_Q2": "M2",
            "Y3_ZF_Q3": "M3",
            "Y3_ZF_Q4": "M4",
            "Y3_Residue_ZFPlan": "NoPeriod",
        }

        # 根据各个字段的值，赋值维度的值
        # df_zt["Year"] = df_zt["Columns"]
        df_zt["Misc1"] = df_zt["Columns"]
        df_zt["Period"] = df_zt["Columns"]

        # df_zt["Year"] = df_zt["Year"].map(map_year)
        df_zt["Misc1"] = df_zt["Misc1"].map(map_misc)
        df_zt["Period"] = df_zt["Period"].map(map_period)

        # 补充固定的纬度值
        df_zt["Version"] = "WorkVersion"
        df_zt["Bak1"] = "NoBak1"
        del df_zt["Columns"]
        df_zt = df_zt.rename(columns={"value": "data"})

        # 保存cube信息
        del_fix = (
            "Year{%s}->Period{NoPeriod}->Scenario{%s}->Entity{Base(D000001,0)}->"
            "Version{WorkVersion}->Misc{CP_08;CP_09}->Account{Base(A01,0)}->Bak1{NoBak1}"
            % (str(int(self.year) - 1), self.key)
        )
        del_fix1 = (
            "Year{%s}->Period{M4}->Scenario{%s}->Entity{Base(D000001,0)}->"
            "Version{WorkVersion}->Misc{CP_0701;CP_0702}->Account{Base(A01,0)}->Bak1{NoBak1}"
            % (str(int(self.year) - 1), self.key)
        )
        del_fix2 = (
            "Year{%s}->Period{Base(TotalPeriod,0);Base(TotalMonth,0)}->Scenario{%s}->Entity{Base(D000001,0)}->"
            "Version{WorkVersion}->Misc{CP_0701;CP_0702}->Account{Base(A01,0)}->Bak1{NoBak1}"
            % (str(int(self.year)), self.key)
        )
        del_fix3 = (
            "Year{%s}->Period{NoPeriod}->Scenario{%s}->Entity{Base(D000001,0)}->"
            "Version{WorkVersion}->Misc{CP_1001;CP_1002;CP_1003;CP_1004}->Account{Base(A01,0)}->Bak1{NoBak1}"
            % (str(int(self.year)), self.key)
        )
        del_fix4 = (
            "Year{%s;%s}->Period{Base(TotalMonth,0)}->Scenario{%s}->Entity{Base(D000001,0)}->"
            "Version{WorkVersion}->Misc{CP_07}->Account{Base(A01,0)}->Bak1{NoBak1}"
            % (str(int(self.year) + 1), str(int(self.year) + 2), self.key)
        )
        del_fix5 = (
            "Year{%s}->Period{NoPeriod}->Scenario{%s}->Entity{Base(D000001,0)}->"
            "Version{WorkVersion}->Misc{CP_11}->Account{Base(A01,0)}->Bak1{NoBak1}"
            % (str(int(self.year) + 2), self.key)
        )
        self.cube.delete(del_fix, 200000)
        self.cube.delete(del_fix1, 200000)
        self.cube.delete(del_fix2, 200000)
        self.cube.delete(del_fix3, 200000)
        self.cube.delete(del_fix4, 200000)
        self.cube.delete(del_fix5, 200000)

        self.cube.save(df_zt)

        # cube_.delete(self.cube_name, del_fix1)
        # cube_.delete(self.cube_name, del_fix2)
        # cube_.delete(self.cube_name, del_fix3)
        # cube_.delete(self.cube_name, del_fix4)
        # cube_.delete(self.cube_name, del_fix5)
        #
        # return cube_.save_cube(df_zt, self.cube_name, del_fix=del_fix)


def main(p1, p2):
    cc = consruction_zf()
    # 保存mysql表中的数据
    cc.save_business_data()
    # 保存cube中的数据
    msg = cc.save_cube_data()
    print(msg)


# debug
if __name__ == "__main__":
    from business.__debug import para1
    p2 = {}

    main(para1, p2)

