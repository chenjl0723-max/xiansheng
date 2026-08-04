"""
added by cjl
added in 20241011
added for 增量计划接口
主要逻辑：
    读取中间表Investment_AddPlan中的数据，
    年份取变量Year，Scenario根据当前时间的月份取范围，其他字段不变。
    保存到目标表后，日志表在保存一份
剩余问题：需要确认在同步年份数据的时候，Year字段的取值逻辑
"""
from idlelib.iomenu import encoding

from pandas.core.dtypes.common import ensure_int8

try:
    from _debug import para1, para2
    print(para1)
except ImportError:
    para1 = para2 = {}

from common.commons import *
from conf.config import *
from deepfos.options import OPTION
import pandas as pd
import datetime

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)

class investment_add:
    def __init__(self,p1):
        # 初始化源、目标表名、历史数据表名
        p1['app'] = 'yhacsq004'
        OPTION.api.header = p1
        self.source_table = "Investment_AddPlan"
        self.source_url = "/ETL/Form_Business/"
        self.target_table = "1_Investment_Add_copy"
        self.target_url = "/Form/1_Investment/"
        self.log_table = "Investment_AddPlan_log"
        # 获取年份变量
        self.year = var_.get_variable("Variable", "Year")

        # 如果当前月份大于 9 月，则预算年度 - 1
        if datetime.datetime.now().month >= 9 or datetime.datetime.now().month == 1 or datetime.datetime.now().month == 2:
            self.year = str(int(self.year) - 1)
        # print(self.year)
        period = str(datetime.datetime.now().month)
        self.key = key_map[period]

        # 获取判断季度的时间
        df_maintenance = rdb_.select(
            [
                "Key_1",
                "Key_2",
                "Key_3",
                "Key_4",
                "Year",
                "Investment",
                "Investment_Sort",
            ],
            "Form_Maintenance",
            path="/Form/7_Maintenance/",
        )

        # print(df_maintenance)
        df_maintenance = df_maintenance[(df_maintenance["Year"] == self.year)]

        df_key = df_maintenance[~pd.isna(df_maintenance["Key_1"])]
        print("df_key",df_key)
        if not df_key.empty:
            self.key1 = df_key.iloc[0, 0]
            print(self.key1)
            self.key2 = df_key.iloc[0, 1]
            print(self.key2)
            self.key3 = df_key.iloc[0, 2]
            print(self.key3)
            self.key4 = df_key.iloc[0, 3]
            print(self.key4)
        # 获取经营模式列表
        df_invest = df_maintenance[["Investment", "Investment_Sort"]]
        df_mapping = pd.DataFrame(
            {
                "key": list(df_invest["Investment"]),
                "value": list(df_invest["Investment_Sort"]),
            }
        ).set_index("key")
        self.dict_invest = df_mapping["value"].to_dict()
        # print(self.dict_invest)

    def get_plan_data(self,p1):
        # print(p1)
        df_data = rdb_.select(columns=None, tbl=self.source_table, path=self.source_url)
        # print('df_data',df_data)

        df_data.to_csv("df_data.csv",encoding='gbk')
        if df_data.empty:
            print("增量计划中间表数据为空")
            return
        # 将年份、情景变量进行赋值
        if "_id" in df_data.columns.to_list():
            del df_data["_id"]
        df_data["Year"] = self.year
        df_result = pd.DataFrame()
        # 循环Scenario，给数据源赋值
        for scenario in self.key.split(";"):
            # Q4同步的是下一年的数据，所以需要年度+1
            if scenario == "Year":
                df_data["Year"] = str(int(self.year) + 1)
            df_data["Scenario"] = scenario
            df_result = df_result.append(df_data)
        df_result.to_csv("df_result.csv",encoding='gbk')
        # print(df_result)

        # 记录一下原始表结构，后边存log表用
        list_col = df_data.columns.to_list()

        # 字段特殊处理  https://proinnova.yuque.com/zpkolg/edn0y5/hp4plhqxtcgub3de#e5Wn9 7.1段 1-5逻辑

        # 预计签约所属年份YJQY_Year = Year（合同签约计划时间Time_HTQYJH）；取该字段中年份部分，例如2024/1/1，那么取值为2024
        def apply_row_data(row):
            if not pd.isna(row["Time_HTQYJH"]):
                if not pd.isnull(row["Time_HTQYJH"]):
                    row["YJQY_Year"] = str(pd.to_datetime(row["Time_HTQYJH"]).year)
                if pd.to_datetime(row["Time_HTQYJH"]) <= self.key2:
                    row["YJQY_Q"] = "一季度"
                elif pd.to_datetime(row["Time_HTQYJH"]) <= self.key3:
                    row["YJQY_Q"] = "二季度"
                elif pd.to_datetime(row["Time_HTQYJH"]) <= self.key4:
                    row["YJQY_Q"] = "三季度"
                else:
                    row["YJQY_Q"] = "四季度"
            if not pd.isna(row["Time_HTQYSJWC"]):
                if pd.to_datetime(row["Time_HTQYSJWC"]) <= self.key2:
                    row["SJQY_Q"] = "一季度"
                elif pd.to_datetime(row["Time_HTQYSJWC"]) <= self.key3:
                    row["SJQY_Q"] = "二季度"
                elif pd.to_datetime(row["Time_HTQYSJWC"]) <= self.key4:
                    row["SJQY_Q"] = "三季度"
                else:
                    row["SJQY_Q"] = "四季度"
            if pd.isnull(row["SJQY_Q"]):
                row["GDJH_Q"] = row["YJQY_Q"]
            else:
                row["GDJH_Q"] = row["SJQY_Q"]

            return row

        # 添加没有的列
        df_result["SJQY_Q"] = ""

        df_result = df_result.apply(apply_row_data, axis=1)
        # 翻译经营模式
        df_result["GDJH_Q"] = df_result["Investment"].map(self.dict_invest)

        # 需要格式化的float字段
        float_col = [
            "GW_JCQYFWFDJ",
            "Total_Investment",
            "WFCZ_Amount",
            "QYRZ_Amount",
            "ZFCZ_Amount",
            "XMRZ_Amount",
            "QTZJLY_Amount",
            "WS_JQTZ",
            "WS_XYSJ",
            "GS_JQTZ",
            "GS_YJGDGQBL",
            "GS_XYSJ",
            "GW_JQTZ",
            "GW_KYXFWF",
            "GW_YWFWFDJ",
            "WN_JQTZ",
            "WN_XYNJ",
            "ZSS_JQTZ",
            "ZSS_XYSJ",
            "Amount_TZ_Q1",
            "Amount_TZ_Q2",
            "Amount_TZ_Q3",
            "Amount_TZ_Q4",
            "Amount_TZ_Total",
            "YJJNZCZBJ_M1",
            "YJJNZCZBJ_M2",
            "YJJNZCZBJ_M3",
            "YJJNZCZBJ_M4",
            "YJJNZCZBJ_M5",
            "YJJNZCZBJ_M6",
            "YJJNZCZBJ_M7",
            "YJJNZCZBJ_M8",
            "YJJNZCZBJ_M9",
            "YJJNZCZBJ_M10",
            "YJJNZCZBJ_M11",
            "YJJNZCZBJ_M12",
            "YJJNZCZBJ_Total",
            "ZRKZFJH_M1",
            "ZRKZFJH_M2",
            "ZRKZFJH_M3",
            "ZRKZFJH_M4",
            "ZRKZFJH_M5",
            "ZRKZFJH_M6",
            "ZRKZFJH_M7",
            "ZRKZFJH_M8",
            "ZRKZFJH_M9",
            "ZRKZFJH_M10",
            "ZRKZFJH_M11",
            "ZRKZFJH_M12",
            "ZRKZFJH_Total",
            "Amount_BZJ",
            "Amount_CZKS_Total",
            "JSQFKKS_Q1",
            "JSQFKKS_Q2",
            "JSQFKKS_Q3",
            "JSQFKKS_Q4",
            "JSQFKKS_Total",
            "JSQFKZJLY_TotalAmount",
            "JSQFKZJLY_WFCZ",
            "JSQFKZJLY_QYRZ",
            "JSQFKZJLY_ZFCZ",
            "JSQFKZJLY_XMJK",
            "JSQFKZJLY_QT",
            "GZKZJLY_TotalAmount",
            "GZKZJLY_WFCZ",
            "GZKZJLY_QYRZ",
            "GZKZJLY_ZFCZ",
            "GZKZJLY_XMJK",
            "GZKZJLY_QT",
            "TXKZJLY_TotalAmount",
            "TXKZJLY_WFCZ",
            "TXKZJLY_QYRZ",
            "TXKZJLY_ZFCZ",
            "TXKZJLY_XMJK",
            "TXKZJLY_QT",
            "Amount_TPNKXMZTZ",
            "Amount_YLFZB",
            "Price_DS",
            "Cost_DS",
            "Amount_QTFDS_Revenue",
            "Amount_QTFDS_Cost",
            "BG_Amount",
            "WN_HTSR",
        ]
        # 需要格式化的datetime字段
        date_col = [
            "Time_YXXSJH",
            "Time_LXJH",
            "Time_FACHJH",
            "Time_TBJH",
            "Time_ZSPSJH",
            "Time_HTQYJH",
            "Time_YXXSSJWC",
            "Time_LXSJWC",
            "Time_FACHSJWC",
            "Time_TBSJWC",
            "Time_ZSPSSJWC",
            "Time_HTQYSJWC",
            "Time_ZB",
            "Time_QY",
            "Time_YJZF",
            "Time_YJHS",
            "Time_GCKG",
            "Time_WGYS",
            "Time_ZSY",
        ]
        # 字段类型处理
        for col in float_col:
            df_result[col] = df_result[col].astype(float).fillna(0.0)
        for col in date_col:
            df_result[col] = df_result[col].astype("datetime64")
        for col in list(
            set(df_result.columns.to_list()) - set(float_col) - set(date_col)
        ):
            df_result[col] = df_result[col].astype(str).fillna("")

        df_result["version"] = "WorkVersion"
        # 保存数据入库
        updatecol = list(
            set(
                df_result.columns.drop(
                    ["Year", "Scenario", "Entity_Investment", "Status", "version"]
                )
            )
        )
        print(df_result)

        # 保存目标数据
        rdb_.insert_sql(
            self.target_table, df_result, path=self.target_url, updatecol=updatecol
        )

        # 保存历史数据，有则更新，没有则加入
        df_result = df_result[list_col]
        df_result["ETL_Datetime"] = datetime.datetime.now()

        updatecol = list(
            set(
                df_result.columns.drop(
                    ["Year", "Scenario", "Entity_Investment", "Status"]
                )
            )
        )
        updatecol.append("ETL_Datetime")

        rdb_.insert_sql(
            self.log_table, df_result, path=self.source_url, updatecol=updatecol
        )
        print("共同步【%s】条增量计划数据" % df_result.shape[0])


def main(p1, p2):
    # 1、获取中间表数据及年份、Scenario值
    investment = investment_add(p1)
    # 读取中间表数据，并保存到目标表中
    investment.get_plan_data(p1)


# debug
if __name__ == "__main__":
    # from conf._evn import p1, p2
    main(para1, para2)
