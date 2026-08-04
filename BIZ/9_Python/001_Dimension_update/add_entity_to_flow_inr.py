"""
added by chenjl
added in 20251010
added for 增量初始化流程数据
主要逻辑：

剩余问题：
"""
import traceback
import pandas as pd
import datetime

from deepfos.element.datatable import DataTableClickHouse as ck
from common.commons import *
from common.config import *


class Add_Entity:
    def __init__(self,entity):
         # 获取Entity数据，这里先默认写一个，后边从表里取或怎么样
        # entity = ['Y92025002311','Q92025002334']

        self.df_entity = pd.DataFrame({"Entity": entity})
        print(self.df_entity)
        # 年份
        self.year = var_.get_variable("Variable", "BudYear")
        list_year = [
            self.year,
            str(int(self.year) - 1),
            str(int(self.year) - 2),
            str(int(self.year) - 3),
        ]
        self.df_year = pd.DataFrame({"Year": list_year})
        # 版本
        self.df_version = dim_.get_dim_attr(
            "Version", "Base(#root, 0)", ["name"], "/2_Dimension/"
        )
        del self.df_version["expectedName"]
        # scenario
        scenario = [
            "Actual",
            "New",
            "Past",
            "Budget",
            "Difference",
            "Forecast",
            "Combinaion",
            "Adj03",
            "Adj06",
            "Adj09",
            "Adj11"
        ]
        self.df_scenario = pd.DataFrame({"Scenario": scenario})
        # department
        department = [
            "Nodepartment",
            "Totaldepartment",
            "Operation",
            "Equipment",
            "HR",
        ]
        self.df_department = pd.DataFrame({"Department": department})

        # 保留block数据
        self.df_block = pd.DataFrame()

    def init_block(self):
        """
        增量初始化datatable_block_control_BEWG
        """
        table = ck("datatable_block_control_S_Cube")
        df_data = pd.merge(self.df_entity, self.df_department, how="cross").rename(
            columns={
                "Entity": "datablock_seg_1_value",
                "Department": "datablock_seg_2_value",
            }
        )
        df_data["datablock_id"] = ""
        df_data["create_time"] = datetime.datetime.now()
        df_data["create_time"] = df_data["create_time"].astype(str)
        df_data["creater"] = "9caf31b7-4493-4bda-a99c-8e9fd48dd61b"

        # 生成主键ID
        def get_id(row):
            import string, random

            src_upp = string.ascii_uppercase
            src_let = string.ascii_lowercase
            src_num = string.digits
            # 先随机定义3种类型各自的个数（总数为8）
            upp_c = random.randint(1, 6)
            low_c = random.randint(1, 8 - upp_c - 1)
            num_c = 9 - (upp_c + low_c)
            # 随机生成密码
            password = (
                random.sample(src_upp, upp_c)
                + random.sample(src_let, low_c)
                + random.sample(src_num, num_c)
            )
            # 打乱列表元素
            random.shuffle(password)
            # 列表转换为字符串
            new_password = "".join(password)
            row["datablock_id"] = new_password
            print(new_password)
            return row

        df_data = df_data.apply(get_id, axis=1)
        i = table.insert_df(df_data)
        print("datatable_block_control_S_Cube", i)
        # 存一下，后边的方法使用
        self.df_block = df_data

    def init_process(self):
        """
        增量初始化process_control_S_Cube
        """
        table = ck("process_control_S_Cube")
        # 先将年份、Scenario、版本三个数据笛卡尔积
        df_data = pd.merge(self.df_year, self.df_scenario, how="cross")
        df_data = pd.merge(df_data, self.df_version, how="cross")
        df_data = pd.merge(df_data, self.df_block, how="cross").rename(
            columns={
                "Year": "process_seg_1_value",
                "Scenario": "process_seg_2_value",
                "name": "process_seg_3_value",
            }
        )
        df_data["process_status"] = "Status01"
        # 更新项目状态
        df_data.loc[
            df_data["process_seg_3_value"] != "Y1", "process_status"
        ] = "Status08"

        df_data.loc[
            (df_data["process_seg_3_value"] == "Y1")
            & (df_data["datablock_seg_2_value"] == "Totaldepartment"),
            "process_status",
        ] = "Status08"

        # 删除无用的列
        for item in ["datablock_seg_1_value", "datablock_seg_2_value"]:
            if item in df_data.columns.to_list():
                del df_data[item]

        i = table.insert_df(df_data)
        print("process_control_BEWG", i)

    def init_basic(self):
        """
        初始化basic_info表
        """
        # 获取新增信息中以PS开头的数据
        df_basic = self.df_entity[self.df_entity["Entity"].str.startswith("PS")]
        if df_basic.empty:
            return
        # 获取所有basic_info表中的数据
        df_target = rdb_.select(["entity"], "basic_info", path="/Datatable/")
        list_entity = list(set(df_target["entity"]))
        # 获取Entity中的数据
        entity_df = dim_.get_dim_attr(
            "Entity",
            "Level(1,0,3,3)",
            fields=["name", "ud2", "ud4"],
            path="/Dimension/",
        )

        # 处理数据
        df_basic = df_basic[~df_basic["Entity"].isin(list_entity)]
        df_basic = pd.merge(
            df_basic, entity_df, how="inner", left_on="Entity", right_on="name"
        )
        # 规范字段
        col = ["Entity", "ud2", "ud4"]
        df_basic = df_basic[col].rename(
            columns={"Entity": "entity", "ud2": "rgn", "ud4": "dist"}
        )
        df_basic["department"] = "Operation"
        df_basic["nature"] = "Invariant"
        df_basic["etl_data"] = datetime.datetime.now()

        msg = rdb_.insert_sql("basic_info", df_basic, path="/Datatable/")

        return msg

    def init_progress(self):
        """
        初始化审批记录表
        """

        df_pro = pd.merge(self.df_entity, self.df_department, how="cross").rename(
            columns={
                "Entity": "entity_id",
                "Department": "department_id",
            }
        )
        # print("init_progress的df_pro",df_pro)
        list_scenario = ["Budget"]
        df_sce = pd.DataFrame({"scenario_id": list_scenario})
        df_pro = pd.merge(df_pro, df_sce, how="cross")
        # df_pro["year_id"] = str(int(self.year) - 1)
        # df_budget = df_pro[
        #     (df_pro["scenario_id"] == "Budget")
        #     & (df_pro["department_id"] != "Totaldepartment")
        # ]
        df_pro["year_id"] = self.year
        # df_pro = pd.concat([df_pro, df_budget])
        df_pro["version_id"] = "Y1"
        df_pro["result_status"] = "Status01"
        # print("init_progress的df_pro1",df_pro)
        # 删除无用的数据集
        del df_sce
        # 获取审批记录表里的Entity_id
        df_app = rdb_.select(
            ["entity_id"], "Approval_Progress_Record", path="/8_Approval/"
        )
        list_app = list(set(df_app["entity_id"]))
        df_pro = df_pro[~df_pro["entity_id"].isin(list_app)]

        print("init_progress的df_pro2",df_pro)
        # 保存审批记录表
        msg = rdb_.insert_sql("Approval_Progress_Record", df_pro, path="/8_Approval/")
        return msg


def main(p1, p2, entity):
    e = Add_Entity(entity)
    try:
        e.init_block()
        e.init_process()
        # e.init_basic()
        e.init_progress()

    except Exception as e:
        traceback.print_exc()


# debug
if __name__ == "__main__":
    from conf._evn import p1, p2

    main(p1, p2)
