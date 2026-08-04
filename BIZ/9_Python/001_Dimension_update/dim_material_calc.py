"""
@file    : dim_material_calc.py
@Time    : 20230712
@Author  : wlm
@Software: PyCharm
@Desc    : 1、调用kafka接口全量获取material数据；2、将maiterial数据保存到中间表；3、将中间表数据同步到material维度中
"""

import datetime
import pandas as pd



from deepfos.element.dimension import Dimension
from common.commons import *


class kafka_material:
    def __init__(self, p1):
        self.p1 = p1
        self.df = pd.DataFrame()
        self.table_name = "bewg_material_data"
        self.path = "/3_Datatable/Middle_Table/Material_data/"

    def get_material_from_table(self):
        """
        为方便测试，新增一个从中间表读取数据的方法
        """
        columns = ["CODE", "DESC7", "DESC14", "DESC11", "DESC12", "DESC13", "status","freezeflag"]
        df = rdb_.select(columns, self.table_name, path=self.path)
        df = df[df["status"] != "1"]

        return df

    def save_material_to_dim(self, df_material):
        """
        将获取到的数据保存到material维度中
        df_material: 通过kafka接口获取到的物料主数据
        """

        # 输出日志
        sum_num = df_material.shape[0]
        # 获取错误数据
        df_error = df_material[
            (pd.isnull(df_material["DESC7"]))
            | (pd.isnull(df_material["DESC14"]))
            | (pd.isnull(df_material["DESC13"]))
        ]
        # 过滤掉错误数据
        df_material = df_material[
            (~pd.isnull(df_material["DESC7"]))
            & (~pd.isnull(df_material["DESC14"]))
            & (~pd.isnull(df_material["DESC13"]))
        ]
        err_code = list(set(df_error["CODE"]))
        err_msg = "本次接口共同步[%s]条数据，其中成功[%s]条，失败[%s]条，失败CODE为[%s]！" % (
            str(sum_num),
            str(df_material.shape[0]),
            str(df_error.shape[0]),
            err_code,
        )
        print(err_msg)

        # 处理中类/用途数据 维度第一层数据处理
        df_zl = rdb_.select(
            columns={"Material_name", "Material_code"},
            tbl="material_funcition",
            path="/3_Datatable/Middle_Table/Material_data/",
        )
        df_zl = df_zl.rename(
            columns={"Material_code": "name", "Material_name": "language_zh-cn"}
        )
        # 设置index排序字段
        df_zl["index"] = df_zl["name"].str[-1:]

        #  设置其他字段值
        df_zl["language_en"] = df_zl["language_zh-cn"]
        df_zl["ud3"] = df_zl["language_zh-cn"]
        df_zl["parent_name"] = "MQ"
        df_zl["is_active"] = 1

        # 药品药剂信息展示 维度第二次数据处理
        df_temp = df_material[["CODE", "DESC14"]]
        # 使用爆炸函数，将desc14 用，分割的数据拆开
        df_temp["DESC14"] = df_temp["DESC14"].replace("，", ",", regex=True)
        df_temp["parent"] = df_temp["DESC14"].str.split(",")
        df_temp = df_temp.explode("parent")

        # 与df_zl关联，用父级的名字关联，获取父级的Code
        df_temp = pd.merge(
            df_temp, df_zl, how="inner", left_on="parent", right_on="language_zh-cn"
        ).rename(columns={"name": "parent_zl"})[["CODE", "parent_zl", "language_zh-cn"]]
        # 与源数据关联，将Parent_name关联到数据源中
        df_material = pd.merge(df_temp, df_material, how="left", on="CODE").rename(
            columns={"language_zh-cn": "ud3"}
        )
        # 拼接药品的name字段
        df_material["CODE"] = df_material[["parent_zl", "CODE"]].apply("".join, axis=1)

        # 设置字段值
        df_material["DESC"] = (
            df_material["DESC"]
            .apply(lambda x: x.replace("--", ""))
            .apply(lambda x: x.replace("≥", ">="))
            .apply(lambda x: x.replace("≤", "<="))
        )
        df_material["is_active"] = "1"
        df_material["language_en"] = df_material["DESC"]
        # 获取最终保留字段
        df_material = df_material[
            [
                "CODE",
                "parent_zl",
                "DESC",
                "is_active",
                "DESC7",
                "ud3",
                "language_en",
                "freezeflag"
            ]
        ].rename(
            columns={
                "CODE": "name",
                "parent_zl": "parent_name",
                "DESC": "language_zh-cn",
                "DESC7": "ud2",
                "freezeflag": "ud4"
            }
        )
        df_material["index"] = df_material["name"].str[-4:]
        # 将中类和药品合并到一起保存
        df_material = (
            pd.concat([df_zl, df_material])
            .sort_values(by=["parent_name", "name"], axis=0, ascending=True)
            .fillna("")
        )

        dim = Dimension("Material")

        rsg = dim.load_dataframe(df_material, "incr_replace")
        return rsg

    def change_status(self, df_material):
        """
        修改已同步数据status
        """

        df_material = df_material[["CODE"]]
        df_material["status"] = "1"
        updatecol = ["status"]

        return rdb_.insert_sql(self.table_name, df_material, self.path, updatecol)


def main(p1, p2):
    # 1、调用kafka接口获取material主数据并存到中间表

    km = kafka_material(p1)

    # 从中间表中取数
    df_material = km.get_material_from_table()
    # 将 None 或 NaN 替换为空字符串
    df_material[["DESC7", "DESC11", "DESC12", "DESC13"]] = df_material[["DESC7", "DESC11", "DESC12", "DESC13"]].fillna(
        "")
    # 连接列值
    # df_material["DESC"] = df_material[["DESC7", "DESC11", "DESC12", "DESC13"]].apply("-".join, axis=1)
    df_material["DESC"] = df_material[["DESC7", "DESC11", "DESC12", "DESC13"]].apply(
        "-".join, axis=1
    )

    if df_material.empty:
        print("kafka接口获取物料数据为空！")
        return

    # df_material = pd.DataFrame()

    # 2、 调用系统接口，将中间表中的数据保存到维度中
    _bo = km.save_material_to_dim(df_material)

    _bo = km.change_status(df_material)
    return _bo


# debug
if __name__ == "__main__":
    from BIZ.__debug import para1, para2

    main(para1, para2)
