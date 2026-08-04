"""
added by wlm
added in 20231016
added for 版本复制
主要逻辑：
    将经营计划、低效计划数据复制到新版本中
剩余问题：
"""

import traceback
import pandas as pd

from common.commons import *
from copy_version_table_info import *
from deepfos.element.finmodel import FinancialCube

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)


class CopyVersion:
    def __init__(self, p2):
        # 获取参数
        if p2["Scenario"] == "Year":
            year_new = "Year"
        else:
            year_new = "YTD_Year"
        self.year = var_.get_variable("Variable", year_new)
        # self.year = var_.get_variable("Variable", "Year")
        self.param = p2
        self.scenario = p2["Scenario"]
        self.version_to = p2["Version_TO"]
        self.version_from = "WorkVersion"
        self.copy_type = p2["Copy_Type"]
        # 拼接where语句
        self.where = self.deal_where()

        # 获取要复制的表
        self.table_list = {}
        # 根据传入的复制类型获取要复制的表
        if self.copy_type == "copy_dx":
            self.table_list = table_dx
        elif self.copy_type == "copy_jy":
            self.table_list = table_jy

    def deal_where(self):
        """
        根据传入的参数，拼接where条件
        """
        where = " and Year = '%s'" % self.year
        if "Scenario" in self.param:
            where = where + " and Scenario = '%s'" % self.scenario
        if "Company" in self.param:
            if self.copy_type == "copy_dx":
                where = (
                        where + " and Incorporated_Company in (%s)" % self.param["Company"]
                )
            elif self.copy_type == "copy_jy":
                where = where + " and Entity_Number in (%s)" % self.param["Company"]

        return where

    def copy_table(self):
        """
        执行mysql版本复制
        """
        insert_sql = []
        delete_sql = []
        for key in self.table_list:
            # Basic_Data_Full 这个表没有scenario字段，所以需要特殊处理
            if key == "Basic_Data_Full":
                del_sql = "delete from ${%s} where Year='%s' and Version='%s'" % (
                    key,
                    self.year,
                    self.version_to,
                )
                sear_sql = (
                        "insert into ${%s} (%s,Version) select %s,'%s' as Version  from  "
                        "${%s} where Version='%s' and  Year='%s'"
                        % (
                            key,
                            ",".join(self.table_list[key]),
                            ",".join(self.table_list[key]),
                            self.version_to,
                            key,
                            self.version_from,
                            self.year,
                        )
                )
            else:
                del_sql = "delete from ${%s} where Version = '%s'  %s" % (
                    key,
                    self.version_to,
                    self.where,
                )
                sear_sql = (
                        "insert into ${%s} (%s,Version) select %s,'%s' as Version  from  ${%s} where Version='%s' %s"
                        % (
                            key,
                            ",".join(self.table_list[key]),
                            ",".join(self.table_list[key]),
                            self.version_to,
                            key,
                            self.version_from,
                            self.where,
                        )
                )
            delete_sql.append(del_sql)
            insert_sql.append(sear_sql)
            print(delete_sql)
            print(sear_sql)
        del_sql = ";".join(delete_sql)
        sear_sql = ";".join(insert_sql)
        rdb_.exec_sql(del_sql)
        msg = rdb_.exec_sql(sear_sql)
        print(msg)
        if self.copy_type == "copy_jy":
            # 经营计划复制cube中的数据
            self.copy_bewg()
        return msg

    def copy_bewg(self):
        """
        执行Cube版本复制
        """

        # 获取基础数据-Misc
        dim_misc = dim_.get_dim_attr(
            "Misc1", "Base(CP_10,0)", fields=["name"], path="/Dimension/"
        )
        dict_misc = list(set(dim_misc["name"]))

        # 获取基础数据-Period
        # 季度
        dict_period = ["M1", "M2", "M3", "M4"]
        # 月份
        dict_period_month = [
            "January",
            "Febrary",
            "March",
            "April",
            "May",
            "June",
            "July",
            "August",
            "September",
            "October",
            "December",
            "November",
        ]
        # 全部
        dict_period_root = dict_period + dict_period_month + ["NoPeriod"]

        misc = list(
            set(
                [
                    "CP_02",
                    "CP_03",
                    "CP_04",
                    "CP_05",
                    "CP_08",
                    "CP_09",
                    "CP_0701",
                    "CP_0702",
                    "CP_01",
                    "CP_01",
                    "CP_13",
                    "CP_14",
                    "CP_07",
                    "CP_0701",
                    "CP_0702",
                    "Base(CP_10, 0)",
                    "CP_15",
                    "CP_16",
                    "CP_17",
                    "CP_07",
                    "CP_01",
                    "CP_07",
                    "CP_11",
                    "CP_01",
                    "CP_06",
                    "CP_12",
                ]
            )
        )
        sear_fix = (
                "Year{%s;%s;%s;%s}->Version{WorkVersion}->Bak1{NoBak1}->Scenario{%s}->"
                "Entity{Base(#root,0)}->Account{Base(A01,0);CZJH_01}->Misc{%s}->Period{Base(#root,0)}"
                % (
                    (str(int(self.year) - 1)),
                    self.year,
                    (str(int(self.year) + 1)),
                    (str(int(self.year) + 2)),
                    self.scenario,
                    ";".join(misc),
                )
        )
        cube = FinancialCube("CUBE_BEWG", path="/Cube/")
        df_cube = cube.query(sear_fix, compact=False)
        # 去年要复制的数据
        df_cube_1 = df_cube[
            (df_cube["Year"] == str(int(self.year) - 1))
            & (df_cube["Period"].isin(["NoPeriod", "M4"]))
            & (
                df_cube["Misc"].isin(
                    [
                        "CP_02",
                        "CP_03",
                        "CP_04",
                        "CP_05",
                        "CP_08",
                        "CP_09",
                        "CP_0701",
                        "CP_0702",
                        "CP_01",
                    ]
                )
            )
            & (df_cube["Account"] != "CZJH_01")
            ]
        # 今年要复制的数据
        misc_curr = [
            "CP_01",
            "CP_13",
            "CP_14",
            "CP_07",
            "CP_0701",
            "CP_0702",
            "CP_15",
            "CP_16",
            "CP_17",
        ]
        misc_curr = misc_curr + dict_misc

        df_cube_curr = df_cube[
            (df_cube["Year"] == self.year)
            & (df_cube["Period"].isin(dict_period_root))
            & (df_cube["Misc"].isin(misc_curr))
            & (df_cube["Account"] != "CZJH_01")
            ]
        print(df_cube_curr)
        # 明年要复制的数据
        df_cube_2 = df_cube[
            (df_cube["Year"] == str(int(self.year) + 1))
            & (df_cube["Period"].isin(dict_period))
            & (df_cube["Misc"].isin(["CP_07", "CP_01"]))
            & (df_cube["Account"] != "CZJH_01")
            ]
        dict_period.append("NoPeriod")
        df_cube_3 = df_cube[
            (df_cube["Year"] == str(int(self.year) + 2))
            & (df_cube["Period"].isin(dict_period))
            & (df_cube["Misc"].isin(["CP_07", "CP_11", "CP_01", "CP_06"]))
            & (df_cube["Account"] != "CZJH_01")
            ]

        # 后续新增需求
        # 1、CZJH_01
        df_cube_4 = df_cube[
            (df_cube["Year"] == self.year)
            & (df_cube["Period"].isin(dict_period + dict_period_month))
            & (df_cube["Misc"] == "CP_01")
            & (df_cube["Account"] == "CZJH_01")
            ]
        df_cube_5 = df_cube[
            (df_cube["Year"] == self.year)
            & (df_cube["Period"].isin(dict_period))
            & (df_cube["Misc"].isin(["CP_12", "CP_14"]))
            & (df_cube["Account"] == "CZJH_01")
            ]
        df_cube_6 = df_cube[
            (df_cube["Year"] == self.year)
            & (df_cube["Period"].isin(dict_period))
            & (df_cube["Misc"] == "CP_12")
            & (df_cube["Account"] != "CZJH_01")
            ]

        df_cube = pd.concat(
            [
                df_cube_1,
                df_cube_2,
                df_cube_3,
                df_cube_curr,
                df_cube_4,
                df_cube_5,
                df_cube_6,
            ]
        )
        df_cube.loc[:, "Version"] = self.version_to

        del_fix = (
                "Year{%s}->Version{%s}->Bak1{NoBak1}->Scenario{%s}->"
                "Entity{Base(#root,0)}->Account{Base(A01,0)}->"
                "Misc{CP_02;CP_03;CP_04;CP_05;CP_08;CP_09;CP_0701;CP_0702;CP_01}->"
                "Period{NoPeriod;M4}"
                % (str(int(self.year) - 1), self.version_to, self.scenario)
        )
        del_fix1 = (
                "Year{%s}->Version{%s}->Bak1{NoBak1}->Scenario{%s}->"
                "Entity{Base(#root,0)}->Account{Base(A01,0)}->"
                "Misc{CP_01;CP_13;CP_14;CP_07;CP_0701;CP_0702;Base(CP_10,0);CP_15;CP_16;CP_17}->"
                "Period{Base(#root,0)}" % (self.year, self.version_to, self.scenario)
        )
        del_fix2 = (
                "Year{%s}->Version{%s}->Bak1{NoBak1}->Scenario{%s}->"
                "Entity{Base(#root,0)}->Account{Base(A01,0)}->"
                "Misc{CP_07;CP_01}->"
                "Period{Base(TotalMonth, 0)}"
                % (str(int(self.year) + 1), self.version_to, self.scenario)
        )
        del_fix3 = (
                "Year{%s}->Version{%s}->Bak1{NoBak1}->Scenario{%s}->"
                "Entity{Base(#root,0)}->Account{Base(A01,0)}->"
                "Misc{CP_07;CP_11;CP_01;CP_06}->"
                "Period{Base(TotalMonth,0);NoPeriod}"
                % (str(int(self.year) + 2), self.version_to, self.scenario)
        )
        del_fix4 = (
                "Year{%s}->Version{%s}->Bak1{NoBak1}->Scenario{%s}->"
                "Entity{Base(#root,0)}->Account{CZJH_01}->"
                "Misc{CP_01}->"
                "Period{%s}"
                % (
                    self.year,
                    self.version_to,
                    self.scenario,
                    ";".join(dict_period_month + dict_period),
                )
        )
        del_fix5 = (
                "Year{%s}->Version{%s}->Bak1{NoBak1}->Scenario{%s}->"
                "Entity{Base(#root,0)}->Account{CZJH_01}->"
                "Misc{CP_12;CP_14}->"
                "Period{%s}"
                % (self.year, self.version_to, self.scenario, ";".join(dict_period))
        )
        del_fix6 = (
                "Year{%s}->Version{%s}->Bak1{NoBak1}->Scenario{%s}->"
                "Entity{Base(#root,0)}->Account{Base(A01,0)}->"
                "Misc{CP_12}->"
                "Period{%s}"
                % (self.year, self.version_to, self.scenario, ";".join(dict_period))
        )

        # 删除cube中的数据
        cube.delete(del_fix, 200000)
        cube.delete(del_fix1, 200000)
        cube.delete(del_fix2, 200000)
        cube.delete(del_fix3, 200000)
        cube.delete(del_fix4, 200000)
        cube.delete(del_fix5, 200000)
        cube.delete(del_fix6, 200000)
        df_cube = df_cube.rename(columns={"Misc": "Misc1"})
        msg = cube.save(df_cube)
        print(msg)


def main(p1, p2):
    print(p2)
    for i in ["copy_jy", "copy_dx"]:
        # for i in ["copy_jy"]:
        para2 = {
            "Version_TO": p2['Version_TO'],
            "Year": p2['Year'],
            "Scenario": p2['Scenario'],
            "Copy_Type": i,
        }

        return_msg = {"code": "00000"}
        try:
            cv = CopyVersion(para2)
            cv.copy_table()

            return_msg["message"] = "版本复制成功"
            return_msg["data"] = "成功"
            return_msg["status"] = True
        except Exception as e:
            return_msg["message"] = "版本复制失败"
            return_msg["data"] = "失败"
            return_msg["status"] = True
            traceback.print_exc()

    return return_msg


# # debug
if __name__ == "__main__":
    from business.__debug import para1

    # 复制类型说明
    copy_type = ["copy_jy", "copy_dx"]

    p2 = {
        "Version_TO": "V3",
        "Year": "2026",
        "Scenario": "Year",
        "Copy_Type": "copy_jy",
    }
    main(para1, p2)


