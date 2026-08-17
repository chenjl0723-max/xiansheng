"""
added by cjl
added in 20241011
added for 设备、设施台账接入equipment_profile
主要逻辑：
    同步设备bewg_equipment_info、设施bewg_installation_info台账表、
    存入设备设施中间表equipment_profile
剩余问题：无
"""

try:
    from budegt.__debug import para1, para2
    print(para1)
except ImportError:
    para1 = para2 = {}
from budget.Python.common.commons import *
from budget.Python.conf.config import *
from deepfos.element.variable import Variable

"""
@file    : init_equipment_info.py
@Time    : 20240905
@Author  : Nehc
@Software: PyCharm
@Desc    : 读取设备、设施信息后同步到目标表中
"""
from deepfos.element.datatable import DataTableMySQL
from deepfos.db.mysql import MySQLClient
import pandas as pd
import datetime
import re

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)


class Equipment_tools:
    def __init__(self, p1):
        # 获取变量年
        self.year = Variable('Variable').get('BudYear')
        self.year_1 = str(int(self.year) - 1)
        self.year_2 = str(int(self.year) - 2)

        # 获取设备设施台账信息
        self.equipment_tab = DataTableMySQL("bewg_equipment_info",path="/05_Datatable/05_08_Equipment")
        self.installlation_tab = DataTableMySQL("bewg_installation_info",path="/05_Datatable/05_08_Equipment")
        # self.source_url = "/05_Datatable/5_0_Equipment/"

        self.target_tab_JG = DataTableMySQL("equipment_profile_JG",path="/05_Datatable/05_08_Equipment")
        self.target_tab_NJ = DataTableMySQL("equipment_profile_NJ",path="/05_Datatable/05_08_Equipment")
        self.backup_tab_JG = DataTableMySQL("equipment_profile_JG_his",path="/05_Datatable/05_08_Equipment")
        self.backup_tab_NJ = DataTableMySQL("equipment_profile_NJ_his",path="/05_Datatable/05_08_Equipment")

        jg_col = self.target_tab_JG.meta.datatableColumn
        self.jg_col = [item.name for item in jg_col if hasattr(item, 'name')]
        # self.jg_col = self.jg_col.remove('_id')
        columns_to_remove = ['_creator', '_create_time', '_modifier', '_modify_time', '_id']
        # 从列名列表中删除指定元素
        self.jg_col = [col for col in self.jg_col if col not in columns_to_remove]
        self.jg_col = ", ".join(self.jg_col)

        nj_col = self.target_tab_NJ.meta.datatableColumn
        self.nj_col = [item.name for item in nj_col if hasattr(item, 'name')]
        # self.nj_col = self.nj_col.remove('_id')
        columns_to_remove = ['_creator', '_create_time', '_modifier', '_modify_time', '_id']
        # 从列名列表中删除指定元素
        self.nj_col = [col for col in self.nj_col if col not in columns_to_remove]
        self.nj_col = ", ".join(self.nj_col)

        # self.target_url = "/05_Datatable/5_0_Equipment"

        # 运营项目表信息
        self.entity_tab = DataTableMySQL("Entity_ZT_NEW")
        self.entity_url = "/05_Datatable/05_02_Middle_Table/"

        # 创建MySQLClient类
        self.client = MySQLClient()

    def backup_equipment(self):
        """
        在profile表中只存year,year-1两年数据，把year-2年的数据迁移到历史表中
        """
        strsql_NJ = "insert into %s (%s) select %s from %s where year in (%s,%s) ON DUPLICATE KEY UPDATE code = VALUES(code),year = VALUES(year),version = VALUES(version)" % (
            self.backup_tab_NJ.table_name,
            self.nj_col,
            self.nj_col,
            self.target_tab_NJ.table_name,
            self.year_1,
            self.year_2

        )
        strsql_JG = "insert into %s (%s) select %s from %s where year in (%s,%s) ON DUPLICATE KEY UPDATE code = VALUES(code),year = VALUES(year),version = VALUES(version)" % (
            self.backup_tab_JG.table_name,
            self.jg_col,
            self.jg_col,
            self.target_tab_JG.table_name,
            self.year_1,
            self.year_2
        )
        insertsql = self.client.exec_sqls([strsql_NJ, strsql_JG])
        print(insertsql)

        # 清除技改、非技改
        self.target_tab_NJ.delete(where=self.target_tab_NJ.table.year == self.year_2)
        self.target_tab_JG.delete(where=self.target_tab_JG.table.year == self.year_2)


    def init_equipment(self):
        """
        从中间表中获取设备、设施数同步到目标表中
        """

        # 1、从中间表中获取设备信息，并rename字段
        # df_equipment = rdb_.select(None, self.equipment_tab, path=self.source_url)
        where = "Operation is not null"
        df_equipment = pd.DataFrame(self.equipment_tab.select_raw(where=where))
        # print(df_JG)
        # df_equipment = self.client.query_dfs("select * from ${%s}" % self.equipment_tab)
        df_equipment = df_equipment.rename(
            columns={
                "Operation": "entity",
                "equip_code": "code",
                "fresh_name": "name",
                "equip_mode": "model",
                "equip_name": "former_name",
                "type_name": "equipment_type",
                "fati_name": "location",
                "last_overhaul_time": "last_overhaul_time",
                "manufacturer": "manufacturer",
                "overhaul_period": "overhaul_period",
                "repurchase_period": "repurchase_period",
                "invocation_date": "start_time",
                "facility_period": "facility_period",
                "facility_seq": "facility_seq",
                "facility_no": "facility_no",
                "equip_name_short": "equip_name_short",
                "equip_seq": "equip_seq",
                "fati_code": "location_no"
                # "equip_"
            }
        )
        df_equipment["equipment_location"] = "el01"
        df_equipment["year"] = self.year
        df_equipment["scenario"] = "Budget"
        df_equipment["version"] = "Y1"
        # df_equipment["department"] = "Equipment"
        df_equipment["approve_status"] = "Status01"

        # 调整日期时间格式
        df_equipment["last_overhaul_time"] = pd.to_datetime(df_equipment["last_overhaul_time"], errors="coerce")
        df_equipment["start_time"] = pd.to_datetime(df_equipment["start_time"], errors="coerce")

        df_equipment["overhaul_judgement"] = df_equipment.apply(
            lambda row: "否" if pd.notnull(row["last_overhaul_time"]) and pd.notnull(row["overhaul_period"]) and (
                        row["last_overhaul_time"].year + float(row["overhaul_period"])) > int(self.year) else "是",
            axis=1
        )

        df_equipment["repurchase_judgement"] = df_equipment.apply(
            lambda row: "否" if pd.notnull(row["start_time"]) and pd.notnull(row["repurchase_period"]) and (
                        row["start_time"].year + float(row["repurchase_period"])) > int(self.year) else "是",
            axis=1
        )


        # 2、从中间表中获取设施信息，并rename字段

        df_installcation = pd.DataFrame(self.installlation_tab.select_raw(where=where))
        df_installcation = df_installcation.rename(
            columns={
                "Operation": "entity",
                "fati_code": "code",
                "fati_name": "name",
                "facility_period": "facility_period",
                "facility_seq": "facility_seq",
                "facility_no": "facility_no",
            }
        )
        df_installcation["equip_no"] = df_installcation["facility_no"]
        df_installcation["equipment_location"] = "el02"
        df_installcation["year"] = self.year
        df_installcation["scenario"] = "Budget"
        df_installcation["version"] = "Y1"
        df_installcation["location"] = df_installcation["name"]
        df_installcation["location_no"] = df_installcation["code"]
        # df_installcation["department"] = "Equipment"
        df_installcation["approve_status"] = "Status01"

        # print(df_installcation)

        # 3、 将表1、表2的补齐
        col = [
            "entity",
            "code",
            "name",
            "model",
            "former_name",
            "equipment_type",
            "location",
            "location_no",
            "last_overhaul_time",
            "manufacturer",
            "overhaul_period",
            "repurchase_period",
            "start_time",
            "equipment_location",
            "year",
            "scenario",
            "version",
            # "department",
            "approve_status",
            "overhaul_judgement",
            "repurchase_judgement",
            # "Operation_JG",
            "facility_period",
            "facility_seq",
            "facility_no",
            "equip_name_short",
            "equip_seq",
            "equip_no"
        ]
        for item in col:
            if item not in df_equipment:
                df_equipment[item] = None
            if item not in df_installcation:
                df_installcation[item] = None

        # 将数据源合并到一起
        df_profile = pd.concat([df_equipment, df_installcation], axis=0)
        df_profile = df_profile[col]
        print(df_profile)
        print("本次接口共增量接入%s条数据"% len(df_profile))

        # # 4、处理Entity字段，将”-“替换为"_“
        df_profile["entity"] = (
            df_profile["entity"].replace("-", "_", regex=True)
        )


        # 处理条线 和 技改分类
        df_jg = df_profile.copy()
        df_jg['department'] = 'Technical'
        df_jg['Operation_JG'] = 'N'

        df_nj = df_profile.copy()
        df_nj['department'] = 'Equipment'
        df_nj['Operation_JG'] = 'N'

        return df_jg, df_nj

    def insert_df(self,p1, jg, nj):
        try:
            # 插入技改数据
            updatecol = list(set(jg.columns) - {"code", "year", "approve_status","Operation_JG"})
            # print("技改更新字段：", updatecol_jg)
            self.target_tab_JG.insert_df(jg, updatecol, chunksize=500)

            # 插入非技改数据
            # updatecol_nj = list(set(nj.columns) - {"code", "year", "approve_status"})
            # print("非技改更新字段：", updatecol_nj)
            self.target_tab_NJ.insert_df(nj, updatecol, chunksize=500)

            # 合并判断状态是否全为空
            df_all = pd.concat([jg, nj], ignore_index=True)

            # 定义更新SQL模板
            sync_sql_tpl = (
                "UPDATE ${%s} AS t1 "
                "JOIN ("
                "SELECT entity, MAX(approve_status) AS max_status "
                "FROM ${%s} "
                "WHERE approve_status BETWEEN 'Status02' AND 'Status08' "
                "and year =%s "
                "GROUP BY entity"
                ") AS t2 ON t1.entity = t2.entity "
                "SET t1.approve_status = t2.max_status "
                "WHERE t1.year = %s"
            )

            # 同步审核状态到三张表
            # self.client.exec_sqls(sync_sql_tpl % "equipment_profile")
            self.client.exec_sqls(sync_sql_tpl % ("equipment_profile_JG","equipment_profile_JG",self.year,self.year))
            self.client.exec_sqls(sync_sql_tpl % ("equipment_profile_NJ","equipment_profile_NJ",self.year,self.year))


            print(f"插入成功的技改设备设施：{len(jg)} 条")
            print(f"插入成功的非技改设备设施：{len(nj)} 条")

        except Exception as e:
            print(f"插入数据时发生错误: {e}")

        # # 日志记录
        # total = len(jg) + len(nj)
        log = {
            "element_name": f"设备设施信息同步成功，共 {len(nj)} 条记录",
            "element_type": "2",
            "sync_user": p1["user"],
            "sync_datetime": datetime.datetime.now(),
            "sync_status": "true",
        }
        dt_log = pd.DataFrame(log, index=[0])
        return rdb_.insert_sql(tbl="bewg_python_log", data=dt_log, path="/05_Datatable/05_11_Log/")


def main(p1, p2):
    # 调用方法，完成数据备份及初始化
    eq = Equipment_tools(p1)
    # 备份equipment_profile表
    eq.backup_equipment()

    jg,nj = eq.init_equipment()

    eq.insert_df(p1,jg,nj)
    # return msg


if __name__ == "__main__":
    # from conf._evn import p1, p2
    from budget.__debug import para1, para2
    main(para1, para2)
