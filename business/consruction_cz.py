"""
added by wlm
added in 20230807
added for 产值计划同步数据逻辑
主要逻辑：
    见：https://proinnova.yuque.com/zpkolg/edn0y5/hrb69esg12lnmsp1#fvPl
剩余问题：

"""

from common.commons import *
# from deepfos.element.finmodel import FinancialCube
from conf.config import key_map
from deliver_plan import *
from deepfos.element.finmodel import FinancialCube

import datetime
import pandas as pd

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)
class ConstructionCZ:
    def __init__(self):
        # 初始化源、目标表名、历史数据表名
        self.source_table = "Consruction_CZ"
        self.log_table = "Consruction_CZ_log"
        self.source_url = "/ETL/Form_Business/"

        self.target_table = "2_Construction_CZ"
        self.basic_table = "Basic_Data_Full"
        self.target_url = "/Form/0_Business_Model/Full_Business_Model/"

        self.cube_name = "CUBE_BEWG"
        self.cube_url = "/Cube/"

        self.cube = FinancialCube(element_name="CUBE_BEWG", path="/Cube/")

        # 获取年份变量
        self.year = var_.get_variable("Variable", "Year")

        period = str(datetime.datetime.now().month)
        self.key = key_map[period]
        # 获取中间表数据
        df_data = rdb_.select(None, self.source_table, path=self.source_url)
        # 保存一下源表的字段
        self.cols = df_data.columns.drop(["_id"]).to_list()
        # 翻译大区、区域、法人公司
        dict_mapping = get_org_mapping()
        df_data["Region_CZ"] = df_data["Region_CZ"].map(dict_mapping)
        df_data["Regional_Company_CZ"] = df_data["Regional_Company_CZ"].map(
            dict_mapping
        )
        df_data["Incorporated_Company_CZ"] = df_data["Incorporated_Company_CZ"].map(
            dict_mapping
        )

        # 翻译Account维度
        # 引用交付计划通用逻辑
        dict_acc = get_account_mapping()
        df_data["Account"] = df_data["Account_CZ"].map(dict_acc)
        # 去掉Account为空的数据
        df_data = df_data[~pd.isnull(df_data["Account"])]

        # 处理数据
        source_data = control_df(df_data, "Entity_Construction_CZ", "产值计划")
        if not source_data.empty:
            self.source_data = source_data.loc[source_data["name"].str.startswith("J")]
        else:
            self.source_data = source_data.copy()
        pass

    def save_business_data(self):
        """
        保存业务数据到主表及子表
        """
        # 判断，如果中间表数据为空，则直接返回
        if self.source_data.empty:
            print("产值计划中间表数据为空")
            return
        # 保存主表数据
        # col = [
        #     "name",
        #     "Year",
        #     "Region_CZ",
        #     "Regional_Company_CZ",
        #     "parent_name",
        #     "Entity_Name_CZ",
        #     "Format_1_CZ",
        #     "Format_2_CZ",
        #     "Investment_CZ",
        # ]
        # df_basic = self.source_data[col].rename(
        #     columns={
        #         "name": "Entity_Number",
        #         "Region_CZ": "Region",
        #         "Regional_Company_CZ": "Regional_Company",
        #         "parent_name": "Incorporated_Company",
        #         "Entity_Name_CZ": "Entity_Name",
        #         "Format_1_CZ": "Format_1",
        #         "Format_2_CZ": "Format_2",
        #         "Investment_CZ": "Investment",
        #     }
        # )
        # df_basic["Version"] = "WorkVersion"
        #
        # # 设置更新列
        # updatecol = list(set(df_basic.columns.drop(["Year", "Entity_Number"])))
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
            "Entity_Construction_CZ",
            "Entity_Name_CZ",
            "Project_Status",
            "NYYXJS",
            "Construction_Type",
            "YN_JCLRXM",
            "Account",
            "ZT_DQKJ",
            "ZT_TPNK",
            "Y1_Total_M",
            "Y1_Q1",
            "Y1_Q2",
            "Y1_Q3",
            "Y1_Q4",
            "Y1_Total_Q",
            "JSZT_AdjustReason",
            "ETL_Audit_Status",
            "Tax_Rate",
            "Project_Nature",
            "is_budget_project",
            "budget_total",
            "water_price_adjust"
        ]
        df_consru = self.source_data[col].rename(
            columns={
                "name": "Entity_Number",
                "Entity_Construction_CZ": "Entity_Construction",
                "Entity_Name_CZ": "Entity_Name",
                "ETL_Audit_Status": "Examine_Status",
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
                    ]
                )
            )
        )
        print('插入目标表前：',df_consru)
        rdb_.insert_sql(
            self.target_table, df_consru, path=self.target_url, updatecol=updatecol
        )


        # 保存同步日志表
        df_log = self.source_data[self.cols]
        df_log["ETL_Datetime"] = datetime.datetime.now()

        updatecol = list(
            set(
                df_log.columns.drop(
                    [
                        "Year",
                        "Scenario",
                        "Entity_Construction_CZ",
                        "Account_CZ",
                    ]
                )
            )
        )
        df_log["Ratio_CZ"] = df_log["Ratio_CZ"].astype(str)

        rdb_.insert_sql(
            self.log_table, df_log, path=self.source_url, updatecol=updatecol
        )

        return "目标表数据同步成功！"

    def save_cube_data(self):
        """
        保存数据到cube中
        """
        if self.source_data.empty:
            print("产值计划中间表数据为空")
            return

        # # 新增逻辑：处理产值计划额外对接数据
        # map_cz = {"1": "Q1", "2": "Q1", "3": "Q1", "4": "Q2", "5": "Q2", "6": "Q2",
        #           "7": "Q3", "8": "Q3", "9": "Q3", "10": "Q4", "11": "Q4", "12": "Q4"}
        # period = str(datetime.datetime.now().month)
        # scenario_other = 'M' + period
        # self.source_data.loc[:, "Scenario"] = self.source_data.apply(
        #     lambda x: scenario_other
        #     if (x["Year"] == self.year) & (x["Scenario"] == map_cz[period])
        #     else x["Scenario"], axis=1)

        # 处理总投信息
        col = [
            "Year",
            "Scenario",
            "name",
            "Account",
            "ZT_DQKJ",
            "ZT_TPNK",
            "Full_CZ_Total",
            "AccumulateCZ_Total",
            "Q4_CZ_Plan",
            "Y1_Jan",
            "Y1_Feb",
            "Y1_Mar",
            "Y1_Api",
            "Y1_May",
            "Y1_Jun",
            "Y1_Jul",
            "Y1_Aug",
            "Y1_Sep",
            "Y1_Oct",
            "Y1_Nov",
            "Y1_Dec",
            "Y1_Q1",
            "Y1_Q2",
            "Y1_Q3",
            "Y1_Q4",
            "Y2_Q1",
            "Y2_Q2",
            "Y2_Q3",
            "Y2_Q4",
            "Y3_Q1",
            "Y3_Q2",
            "Y3_Q3",
            "Y3_Q4",
            "Y3_Residue_CZPlan",
        ]
        df_zt = self.source_data[col].rename(columns={"name": "Entity"})

        # 将数据源从宽表转换成长表
        df_zt = pd.melt(
            df_zt, id_vars=["Scenario", "Year", "Entity", "Account"], var_name="Columns"
        )

        df_zt.loc[
            df_zt["Columns"].isin(
                [
                    "Y2_Q1",
                    "Y2_Q2",
                    "Y2_Q3",
                    "Y2_Q4",
                ]
            ),
            "Year",
        ] = (
            df_zt["Year"].astype(int) + 1
        )

        df_zt.loc[
            df_zt["Columns"].isin(
                [
                    "Y3_Q1",
                    "Y3_Q2",
                    "Y3_Q3",
                    "Y3_Q4",
                    "Y3_Residue_CZPlan",
                ]
            ),
            "Year",
        ] = (
            df_zt["Year"].astype(int) + 2
        )

        df_zt.loc[
            df_zt["Columns"].isin(
                [
                    "ZT_DQKJ",
                    "ZT_TPNK",
                    "Full_CZ_Total",
                    "AccumulateCZ_Total",
                    "Q4_CZ_Plan",
                ]
            ),
            "Year",
        ] = (
            df_zt["Year"].astype(int) - 1
        )

        # df_zt.loc[
        #     df_zt["Columns"].isin(
        #         [
        #             "Y1_Jan",
        #             "Y1_Feb",
        #             "Y1_Mar",
        #             "Y1_Api",
        #             "Y1_May",
        #             "Y1_Jun",
        #             "Y1_Jul",
        #             "Y1_Aug",
        #             "Y1_Sep",
        #             "Y1_Oct",
        #             "Y1_Nov",
        #             "Y1_Dec",
        #             "Y1_Q1",
        #             "Y1_Q2",
        #             "Y1_Q3",
        #             "Y1_Q4",
        #         ]
        #     ),
        #     "Year",
        # ] = (
        #     df_zt["Year"].astype(int) + 1
        # )

        # 准备转换字段map
        map_year = {
            "ZT_DQKJ": self.year,
            "ZT_TPNK": self.year,
            "Full_CZ_Total": self.year,
            "AccumulateCZ_Total": self.year,
            "Q4_CZ_Plan": self.year,
            "Y1_Jan": str(int(self.year) + 1),
            "Y1_Feb": str(int(self.year) + 1),
            "Y1_Mar": str(int(self.year) + 1),
            "Y1_Api": str(int(self.year) + 1),
            "Y1_May": str(int(self.year) + 1),
            "Y1_Jun": str(int(self.year) + 1),
            "Y1_Jul": str(int(self.year) + 1),
            "Y1_Aug": str(int(self.year) + 1),
            "Y1_Sep": str(int(self.year) + 1),
            "Y1_Oct": str(int(self.year) + 1),
            "Y1_Nov": str(int(self.year) + 1),
            "Y1_Dec": str(int(self.year) + 1),
            "Y1_Q1": str(int(self.year) + 1),
            "Y1_Q2": str(int(self.year) + 1),
            "Y1_Q3": str(int(self.year) + 1),
            "Y1_Q4": str(int(self.year) + 1),
            "Y2_Q1": str(int(self.year) + 2),
            "Y2_Q2": str(int(self.year) + 2),
            "Y2_Q3": str(int(self.year) + 2),
            "Y2_Q4": str(int(self.year) + 2),
            "Y3_Q1": str(int(self.year) + 3),
            "Y3_Q2": str(int(self.year) + 3),
            "Y3_Q3": str(int(self.year) + 3),
            "Y3_Q4": str(int(self.year) + 3),
            "Y3_Residue_CZPlan": str(int(self.year) + 3),
        }
        map_misc = {
            "ZT_DQKJ": "CP_02",
            "ZT_TPNK": "CP_03",
            "Full_CZ_Total": "CP_04",
            "AccumulateCZ_Total": "CP_05",
            "Q4_CZ_Plan": "CP_01",
            "Y1_Jan": "CP_01",
            "Y1_Feb": "CP_01",
            "Y1_Mar": "CP_01",
            "Y1_Api": "CP_01",
            "Y1_May": "CP_01",
            "Y1_Jun": "CP_01",
            "Y1_Jul": "CP_01",
            "Y1_Aug": "CP_01",
            "Y1_Sep": "CP_01",
            "Y1_Oct": "CP_01",
            "Y1_Nov": "CP_01",
            "Y1_Dec": "CP_01",
            "Y1_Q1": "CP_01",
            "Y1_Q2": "CP_01",
            "Y1_Q3": "CP_01",
            "Y1_Q4": "CP_01",
            "Y2_Q1": "CP_01",
            "Y2_Q2": "CP_01",
            "Y2_Q3": "CP_01",
            "Y2_Q4": "CP_01",
            "Y3_Q1": "CP_01",
            "Y3_Q2": "CP_01",
            "Y3_Q3": "CP_01",
            "Y3_Q4": "CP_01",
            "Y3_Residue_CZPlan": "CP_06",
        }
        map_period = {
            "ZT_DQKJ": "NoPeriod",
            "ZT_TPNK": "NoPeriod",
            "Full_CZ_Total": "NoPeriod",
            "AccumulateCZ_Total": "NoPeriod",
            "Q4_CZ_Plan": "M4",
            "Y1_Jan": "January",
            "Y1_Feb": "Febrary",
            "Y1_Mar": "March",
            "Y1_Api": "April",
            "Y1_May": "May",
            "Y1_Jun": "June",
            "Y1_Jul": "July",
            "Y1_Aug": "August",
            "Y1_Sep": "September",
            "Y1_Oct": "October",
            "Y1_Nov": "November",
            "Y1_Dec": "December",
            "Y1_Q1": "M1",
            "Y1_Q2": "M2",
            "Y1_Q3": "M3",
            "Y1_Q4": "M4",
            "Y2_Q1": "M1",
            "Y2_Q2": "M2",
            "Y2_Q3": "M3",
            "Y2_Q4": "M4",
            "Y3_Q1": "M1",
            "Y3_Q2": "M2",
            "Y3_Q3": "M3",
            "Y3_Q4": "M4",
            "Y3_Residue_CZPlan": "NoPeriod",
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

        # 设置data字段
        df_zt["data"] = df_zt["data"].fillna(0)

        # 保存cube信息
        del_fix = (
            "Year{%s}->Period{NoPeriod}->Scenario{%s}->Entity{Base(D000001,0)}->"
            "Version{WorkVersion}->Misc{CP_02;CP_03;CP_04;CP_05}->Account{Base(A01,0)}->Bak1{NoBak1}"
            % (str(int(self.year) - 1), self.key)
        )
        del_fix1 = (
            "Year{%s}->Period{M4}->Scenario{%s}->Entity{Base(D000001,0)}->"
            "Version{WorkVersion}->Misc{CP_01}->Account{Base(A01,0)}->Bak1{NoBak1}"
            % (str(int(self.year) - 1), self.key)
        )
        del_fix2 = (
            "Year{%s}->Period{Base(TotalPeriod,0);Base(TotalMonth,0)}->Scenario{%s}->Entity{Base(D000001,0)}->"
            "Version{WorkVersion}->Misc{CP_01}->Account{Base(A01,0)}->Bak1{NoBak1}"
            % (str(int(self.year)), self.key)
        )
        del_fix3 = (
            "Year{%s;%s}->Period{Base(TotalMonth,0)}->Scenario{%s}->Entity{Base(D000001,0)}->"
            "Version{WorkVersion}->Misc{CP_01}->Account{Base(A01,0)}->Bak1{NoBak1}"
            % (str(int(self.year) + 1), str(int(self.year) + 3), self.key)
        )

        del_fix4 = (
            "Year{%s}->Period{NoPeriod}->Scenario{%s}->Entity{Base(D000001,0)}->"
            "Version{WorkVersion}->Misc{CP_06}->Account{Base(A01,0)}->Bak1{NoBak1}"
            % (
                str(int(self.year) + 2),
                self.key,
            )
        )
        self.cube.delete(del_fix, 200000)
        self.cube.delete(del_fix1, 200000)
        self.cube.delete(del_fix2, 200000)
        self.cube.delete(del_fix3, 200000)
        self.cube.delete(del_fix4, 200000)
        self.cube.save(df_zt)

        # cube_.delete(self.cube_name, del_fix1)
        # cube_.delete(self.cube_name, del_fix2)
        # cube_.delete(self.cube_name, del_fix3)
        # cube_.delete(self.cube_name, del_fix4)
        #
        # return cube_.save_cube(df_zt, self.cube_name, del_fix=del_fix)

    def calc_data_cube(self):
        """
        数据进入cube后，计算CZJH_01 有加成利润产值 = 产值/支付小计（A01） - 二类费征地拆迁（A010202） - 建设期利息（A0103）
        问题：这块还需要个加成率需要确认怎么取
        """
        #### 获取数据 用于计算加成利润产值 开始 update in 20230821 updated for  计算逻辑新增A010301科目####
        # scenario_other = 'M' + str(datetime.datetime.now().month)
        sear_fix = (
            "Year{%s}->Period{Base(TotalMonth,0);Remove(Base(TotalPeriod,0),NoPeriod)}->"
            "Scenario{%s}->Entity{Base(D000001,0)}->Version{WorkVersion}->Misc{CP_01}->"
            "Account{A01;A010202;A0103;A010301}->Bak1{NoBak1}"
            % (str(int(self.year)), self.key)
        )
        df_cube = self.cube.query(sear_fix, compact=False, pivot_dim="Account")
        # df_cube = cube_.query_cube(
        #     cube_name=self.cube_name, fix=sear_fix, pivot_dim="Account"
        # )

        col_item = ["A01", "A010202", "A0103", "A010301"]
        if df_cube.empty:
            print("未找到用于计算的科目数据")
            return
        # 判断科目无值的话，补充列并用0填充
        for col in col_item:
            if col not in df_cube.columns.to_list():
                df_cube[col] = 0
            else:
                df_cube[col] = df_cube[col].fillna(0)

        # 计算
        df_cube.loc[:, "CZJH_01"] = (
            df_cube["A01"] - df_cube["A010202"] - df_cube["A0103"] - df_cube["A010301"]
        )
        # 删除无用的字段
        for col in col_item:
            del df_cube[col]
        #### 获取数据 用于计算加成利润产值 结束，这里df_cube 可以入库了，为了效率，计算完步骤2后一起入库 ####

        df_copy = df_cube.copy()
        # 获取基础数据
        df_basic = rdb_.select(
            ["Year", "Entity_Number", "Ratio", "TaxRate", "Investment"],
            self.basic_table,
            path=self.target_url,
        ).rename(columns={"Entity_Number": "Entity"})

        # 获取加成率数据
        df_jcl = rdb_.select(
            ["Entity_Number", "Year", "Mark_Up"],
            "Form_Maintenance",
            path="/Form/7_Maintenance/",
        )

        # 直接取下一年的数据
        df_basic = df_basic[df_basic["Year"] == str(int(self.year))]
        df_jcl = df_jcl[df_jcl["Year"] == str(int(self.year))]

        # 设置Misc维度值
        df_copy.loc[df_copy["Period"].isin(["M1", "M2", "M3", "M4"]), "Misc"] = "CP_14"
        df_copy.loc[~df_copy["Period"].isin(["M1", "M2", "M3", "M4"]), "Misc"] = "CP_12"
        # Period维度映射
        map_period = {
            "January": "M1",
            "Febrary": "M1",
            "March": "M1",
            "April": "M2",
            "May": "M2",
            "June": "M2",
            "July": "M3",
            "August": "M3",
            "September": "M3",
            "October": "M4",
            "December": "M4",
            "November": "M4",
            "M1": "M1",
            "M2": "M2",
            "M3": "M3",
            "M4": "M4",
        }
        df_copy["Period"] = df_copy["Period"].map(map_period)
        # 映射后做汇总处理
        list_col = df_copy.columns.to_list()
        list_col.remove("CZJH_01")
        df_copy = df_copy.groupby(by=list_col, as_index=False)["CZJH_01"].sum()

        # 将数据源关联到一起，进行计算
        df_copy = pd.merge(df_copy, df_basic, how="inner", on=["Entity"]).rename(
            columns={"Year_x": "Year"}
        )
        df_copy = pd.merge(
            df_copy,
            df_jcl,
            how="left",
            left_on=["Entity"],
            right_on=["Entity_Number"],
        ).rename(columns={"Year_x": "Year"})
        # 如果用于计算的值为空，则赋值为0
        df_copy["Ratio"] = df_copy["Ratio"].astype(float).fillna(0.0)
        df_copy["TaxRate"] = df_copy["TaxRate"].astype(float).fillna(0.0)
        df_copy["Mark_Up"] = df_copy["Mark_Up"].astype(float).fillna(0.0)
        # 新增逻辑，只有Investment 值为BOT时，才计算
        df_copy = df_copy[df_copy["Investment"] == "BOT"]
        df_copy["CZJH_01"] = (
            df_copy["CZJH_01"]
            * df_copy["Ratio"]
            * df_copy["TaxRate"]
            * df_copy["Mark_Up"]
        )

        # 规范字段
        list_col.append("CZJH_01")
        df_copy = df_copy[list_col]

        # 将计算的结果合并到一起
        df_cube = pd.concat([df_copy, df_cube])

        # 拼接删除fix，并保存数据
        del_fix = (
            "Year{%s}->Period{Base(TotalMonth,0);Remove(Base(TotalPeriod,0),NoPeriod)}->"
            "Scenario{%s}->Entity{Base(D000001,0)}->Version{WorkVersion}->Misc{CP_01}->Account{CZJH_01}->Bak1{NoBak1}"
            % (str(int(self.year)), self.key)
        )
        del_fix1 = (
            "Year{%s}->Period{Base(TotalMonth,0)}->Scenario{%s}->Entity{Base(D000001,0)}->Version{WorkVersion}->"
            "Misc{CP_12;CP_14}->Account{CZJH_01}->Bak1{NoBak1}"
            % (str(int(self.year)), self.key)
        )
        self.cube.delete(del_fix)
        self.cube.delete(del_fix1)

        self.cube.save_unpivot(df_cube, "Account")

        # cube_.delete(self.cube_name, del_fix1)
        # cube_.delete(self.cube_name, del_fix2)
        # cube_.pivot_data_to_cube(self.cube_name, df_cube, "Account", del_fix)


def main(p1, p2):
    cc = ConstructionCZ()
    # 保存mysql表中的数据
    cc.save_business_data()
    # 保存cube中的数据
    cc.save_cube_data()
    # 计算加成利润产值、年产值利润
    cc.calc_data_cube()


# debug
if __name__ == "__main__":
    from business._debug import para1
    p2 = {}

    main(para1, p2)

