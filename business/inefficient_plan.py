"""
added by wlm
added in 20230803
added for 低效计划接口
主要逻辑：
    读取中间表Inefficient_Plan中的数据，过滤条件为Scenario = 拼接的参数 & 法人公司（Incorporated_Company） in (传入的参数，需把结尾的_C去掉)
    根据文档：https://proinnova.yuque.com/zpkolg/edn0y5/dgtrxu8xp6dxufc6#l7wCz 中的逻辑，将数据同步到相应的表中
剩余问题：
"""
try:
    from _debug import para1, para2
    print(para1)
except ImportError:
    para1 = para2 = {}
from common.commons import *
from conf.config import *

import pandas as pd
import datetime

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)
class inefficient_plan:
    def __init__(self, p2):
        # 初始化源、目标表名、历史数据表名
        self.source_table = "Inefficient_Plan"
        self.source_url = "/ETL/Form_Business/"
        self.log_table = "Inefficient_Plan_log"
        # 目标表信息
        self.target_table = "Basic_Data_DX"
        self.target_table_ks = "4_IP_KS"  # 亏损子表
        self.target_table_tc = "4_IP_TCJH"  # 退出计划子表
        self.target_table_dsy = "4_IP_DSY"  # 低收益子表
        self.target_url = "/Form/0_Business_Model/DX_Business_Model/"

        self.year = p2["Year"]
        self.comp = p2["Incorporated_Company"]

        # 拼接公司,后边写删除sql语句（获取全部境外公司）
        str_company = ""
        for item in self.comp:
            if str_company == "":
                str_company = "'%s'" % item
            else:
                str_company = str_company + ",'%s'" % item
        self.company = str_company
        print(self.company)
        # 获取全量低效数据
        df_temp = rdb_.select(None, self.source_table, path=self.source_url)
        print('df_temp',df_temp)

        # 过滤
        month = datetime.datetime.now().month
        self.scenario = "M" + str(month)

        # 获取月份数据
        self.df_ineffic = df_temp[df_temp["Scenario"].str.contains("-")]
        self.df_ineffic["Scenario"] = self.scenario
        print('self.df_ineffic',self.df_ineffic)
        # 获取年份数据
        df_year = pd.DataFrame()
        if month >= 9 or month == 1 or month == 2:
            df_year = df_temp[df_temp["Scenario"] == self.year]
            df_year["Scenario"] = "Year"
            print('df_year',df_year)

        if not df_year.empty:
            self.df_ineffic = self.df_ineffic.append(df_year)

        # 特殊逻辑，将公司编码添加DX_前缀
        self.df_ineffic.loc[:, "Incorporated_Company_DX"] = "DX_" + self.df_ineffic[
            "Incorporated_Company_DX"
        ].astype(str)

        self.df_ineffic = self.df_ineffic[
            self.df_ineffic["Incorporated_Company_DX"].isin(self.comp)
        ]
        print('self.comp', self.comp)
        print('self.df_ineffic', self.df_ineffic)
        pass

    def get_basic_decision(self):
        """
        获取退出计划主数据
        """
        # period = ["M9", "M10", "M11", "M12"]
        period = ["M9", "M10", "M11", "M12", "M1", "M2"]
        # 调用删除方法，先把主表及子表的数据删除掉 (如果是1月份，那么就删除本年度，和上一年当月，需要调整）
        if self.scenario in period:
            self.del_data(self.target_table, self.year, "Year")
            # self.del_data(self.target_table_tc, self.year, "Year")
            # self.del_data(self.target_table_ks, self.year, "Year")
            # self.del_data(self.target_table_dsy, self.year, "Year")
            self.del_data(self.target_table, str(int(self.year) - 1), self.scenario)
            # self.del_data(self.target_table_tc, str(int(self.year) - 1), self.scenario)
            # self.del_data(self.target_table_ks, str(int(self.year) - 1), self.scenario)
            # self.del_data(self.target_table_dsy, str(int(self.year) - 1), self.scenario)
        else:
            self.del_data(self.target_table, self.year, self.scenario)
            # self.del_data(self.target_table_tc, self.year, self.scenario)
            # self.del_data(self.target_table_ks, self.year, self.scenario)
            # self.del_data(self.target_table_dsy, self.year, self.scenario)

        msg = "低效计划同步成功！"
        # 获取主表数据
        df_dcsion = rdb_.select(
            None, "Basic_Decision_Data", path="/Form/4_Inefficient_Plan/"
        )
        print(df_dcsion)
        df_dcsion = df_dcsion[
            (df_dcsion["Year"] == self.year)
            & (df_dcsion["Incorporated_Company"].isin(self.comp))
            & (df_dcsion["Type_DX"].isin(["DX_0301", "DX_0302", "DX_0303", "DX_0304"]))
            ]
        print('Basic_Decision_Data表里填的低效项目：', df_dcsion)
        if df_dcsion.empty:
            return msg

        # 主表与中间表关联，获取数据
        df_dcsion = pd.merge(
            df_dcsion,
            self.df_ineffic,
            how="left",
            left_on=["Incorporated_Company"],
            right_on=["Incorporated_Company_DX"],
        ).rename(columns={"Ratio_x": "Ratio"})
        # 获取未在中间表中关联到的公司编码
        df_null = df_dcsion[pd.isnull(df_dcsion["Incorporated_Company_DX"])]
        print('df_null', df_null)
        if not df_null.empty:
            msg = "未在中台找到数据的公司编码如下：【%s】" % list(set(df_null["Incorporated_Company"]))

        # 删掉未找到的公司数据
        df_dcsion = df_dcsion[~pd.isnull(df_dcsion["Incorporated_Company_DX"])]

        # 新增未找到的公司数据的scenario处理
        df_null.loc[:, "Incorporated_Company_DX"] = df_null.apply(lambda x: x["Incorporated_Company"], axis=1)
        df_null["Scenario"] = self.scenario
        month = datetime.datetime.now().month

        # （陈：如果月份为1、2月那么存的时候 存为M1、M2，需要修改）
        if month >= 9 or month == 1 or month == 2:
            df_null_year = df_null.copy(deep=True)
            df_null_year["Scenario"] = "Year"
            df_null = pd.concat([df_null, df_null_year], axis=0)
        df_dcsion = pd.concat([df_null, df_dcsion], axis=0).reset_index(drop=True)

        # 如果scenario 为年度，则判断状态：状态 = 1 保留；状态 ！= 1 不更新
        # df_dcsion = df_dcsion[
        #     ~((df_dcsion["Scenario"] == "Year") & (df_dcsion["Approve_Status"] != "1"))
        # ]

        # 判断，如果scenario 在M9 - M2 中，则数据的年份要 - 1
        # （陈：主要是这 插入的时候 如果是1、2月，则年份减1年）
        df_dcsion.loc[df_dcsion["Scenario"].isin(period), "Year"] = (
                df_dcsion["Year"].astype(int) - 1
        )

        # 把计算好的年份设置为字符串类型
        df_dcsion["Year"] = df_dcsion["Year"].astype(str)

        if df_dcsion.empty:
            return "未在中台找到数据，请联系管理员！"

        df_basic = df_dcsion[
            [
                "Year",
                "Incorporated_Company",
                "Regional_Company",
                "Region",
                "Format_1",
                "Format_2",
                "Investment",
                "Ratio",
                "Project_Investment_DW",
                "Scenario",
                "Type_DX",
            ]
        ]

        df_basic["Version"] = "WorkVersion"

        updatecol = list(
            set(
                df_basic.columns.drop(
                    [
                        "Year",
                        "Incorporated_Company",
                    ]
                )
            )
        )
        print('df_basic', df_basic)
        # 保存主数据
        rdb_.insert_sql(
            tbl=self.target_table,
            data=df_basic,
            path=self.target_url,
            updatecol=updatecol,
        )

        # 统一加一下Version
        df_dcsion["Version"] = "WorkVersion"

        # 获取退出计划数据
        df_tc = df_dcsion[df_dcsion["Type_DX"] == "DX_0301"]
        # 获取亏损计划数据
        df_ks = df_dcsion[df_dcsion["Type_DX"] == "DX_0302"]
        # 获取低收益计划数据
        df_dsy = df_dcsion[df_dcsion["Type_DX"] == "DX_0303"]

        # 退出计划同步数据
        if not df_tc.empty:
            self.save_tc(df_tc)

        # 亏损计划同步数据
        if not df_ks.empty:
            self.save_ks(df_ks)

        # 低收益计划同步数据
        if not df_dsy.empty:
            self.save_dsy(df_dsy)

        return msg

    def save_tc(self, df_tc):
        """
        获取退出计划并保存到子表
        """
        # 获取数据表中的数据
        col = ["Year", "Scenario", "Incorporated_Company", "PHP_Y_JQ_Profit"]
        df_target_tc = rdb_.select(col, self.target_table_tc, path=self.target_url)

        columns = [
            "Year",
            "Scenario",
            "Incorporated_Company",
            "CIS_ZCZBJ",
            "CIS_XMDKYE",
            "CIS_LJJTNBJK",
            "CIS_LJYSKYE",
            "PHP_Y_2_JQ_Profit",
            "PHP_Y_1_JQ_Profit",
            "PHP_Y_JQ_Profit",
            "EIS_Actual_IAmount",
            "Version",
        ]
        df_tc = df_tc[columns]

        df_tc_log = df_tc.copy()

        df_tc = pd.merge(
            df_tc,
            df_target_tc,
            how="left",
            on=[
                "Year",
                "Scenario",
                "Incorporated_Company",
            ],
        )
        df_tc.loc[pd.isnull(df_tc["PHP_Y_JQ_Profit_x"]), "PHP_Y_JQ_Profit_x"] = df_tc[
            "PHP_Y_JQ_Profit_y"
        ]
        df_tc = df_tc.rename(columns={"PHP_Y_JQ_Profit_x": "PHP_Y_JQ_Profit"})
        del df_tc["PHP_Y_JQ_Profit_y"]

        updatecol = list(
            set(df_tc.columns.drop(["Year", "Scenario", "Incorporated_Company"]))
        )
        rdb_.insert_sql(self.target_table_tc, df_tc, self.target_url, updatecol)
        self.save_log(df_tc_log)

    def save_ks(self, df_ks):
        """
        获取亏损计划并保存到子表
        """
        # 获取数据表中的数据
        col = ["Year", "Scenario", "Incorporated_Company", "PHP_Y_JQ_Profit"]
        df_target_ks = rdb_.select(col, self.target_table_ks, path=self.target_url)
        columns = [
            "Year",
            "Scenario",
            "Incorporated_Company",
            "PHP_Y_2_JQ_Profit",
            "PHP_Y_1_JQ_Profit",
            "PHP_Y_JQ_Profit",
            "EIS_Actual_IAmount",
            "Version",
        ]
        df_ks = df_ks[columns]
        df_ks_log = df_ks.copy()
        df_ks = pd.merge(
            df_ks,
            df_target_ks,
            how="left",
            on=[
                "Year",
                "Scenario",
                "Incorporated_Company",
            ],
        )
        df_ks.loc[pd.isnull(df_ks["PHP_Y_JQ_Profit_x"]), "PHP_Y_JQ_Profit_x"] = df_ks[
            "PHP_Y_JQ_Profit_y"
        ]
        df_ks = df_ks.rename(columns={"PHP_Y_JQ_Profit_x": "PHP_Y_JQ_Profit"})
        del df_ks["PHP_Y_JQ_Profit_y"]
        updatecol = list(
            set(df_ks.columns.drop(["Year", "Scenario", "Incorporated_Company"]))
        )
        rdb_.insert_sql(self.target_table_ks, df_ks, self.target_url, updatecol)
        self.save_log(df_ks_log)

    def save_dsy(self, df_dsy):
        """
        获取低收益计划并保存到子表
        """
        columns = [
            "Year",
            "Scenario",
            "Incorporated_Company",
            "PHP_Y_ZMProfit",
            "Version",
        ]
        df_dsy = df_dsy[columns]
        updatecol = list(
            set(df_dsy.columns.drop(["Year", "Scenario", "Incorporated_Company"]))
        )
        rdb_.insert_sql(self.target_table_dsy, df_dsy, self.target_url, updatecol)
        self.save_log(df_dsy)

    def del_data(self, table_name, year, scenario):
        """
        删除数据
        """
        # 删除主表
        del_sql = (
                "delete from ${%s} where Year='%s' and Scenario = '%s' "
                "and Incorporated_Company in (%s) and (Approve_Status = '1' or Approve_Status is null)"
                % (table_name, year, scenario, self.company)
        )

        return rdb_.exec_sql(del_sql)

    def save_log(self, df):
        """
        保存日志信息
        """
        # 重命名参数
        if "Incorporated_Company" in df.columns.to_list():
            df = df.rename(columns={"Incorporated_Company": "Incorporated_Company_DX"})
        if "Version" in df.columns.to_list():
            del df["Version"]
        df["ETL_Datetime"] = datetime.datetime.now()
        updatecol = list(
            set(df.columns.drop(["Year", "Scenario", "Incorporated_Company_DX"]))
        )
        rdb_.insert_sql(self.log_table, df, self.source_url, updatecol)


def main(p1, p2):
    ip = inefficient_plan(p2)
    return_msg = {"code": "00000"}
    if ip.df_ineffic.empty:
        return_msg["message"] = "未在中台找到数据，请联系管理员！"
        return_msg["status"] = True
        return return_msg
    try:
        msg = ip.get_basic_decision()
        return_msg["message"] = msg
        return_msg["status"] = True
    except Exception:
        return_msg["message"] = "低效计划同步失败，请联系管理员"
        return_msg["status"] = False
    return return_msg


# debug
if __name__ == "__main__":
    # from conf._evn import p1, p2

    p2 = {
        "Year": "2025",
        "Incorporated_Company": [
            "DX_91320300583747244T",
            "DX_91440700MAC28K1Q84"

        ],
    }
    main(para1, p2)
