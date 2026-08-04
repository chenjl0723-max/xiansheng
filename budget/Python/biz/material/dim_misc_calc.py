"""
@file    : dim_misc_calc.py
@Time    : 20230725
@Author  : wlm
@Software: PyCharm
@Desc    :1、读取中间表数据；2、生成misc维度；3、生成业务数据
"""
import pandas as pd
import datetime

from common.commons import *
from deepfos.element.dimension import Dimension

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)
def get_data():
    """
    获取中间表数据
    """
    columns = [
        # "Company",
        # "Company_name",
        "Entity",
        # "Entity_name",
        "Material",
        # "Material_name",
        "Misc1",
        "Commodity_name",
        "Price",
        "Year",
    ]
    tbl = "bewg_price_data"
    df = rdb_.select(columns, tbl)

    # 输出日志
    sum_num = df.shape[0]
    # 获取错误数据
    df_error = df[
        # (pd.isnull(df["Company"]))
        # | (pd.isnull(df["Company_name"]))
        (pd.isnull(df["Entity"]))
        # | (pd.isnull(df["Entity_name"]))
        | (pd.isnull(df["Material"]))
        # | (pd.isnull(df["Material_name"]))
        | (pd.isnull(df["Misc1"]))
        | (pd.isnull(df["Commodity_name"]))
        | (pd.isnull(df["Price"]))
        | (pd.isnull(df["Year"]))
    ]
    # 过滤掉错误数据
    df = df[
        # (~pd.isnull(df["Company"]))
        # & (~pd.isnull(df["Company_name"]))
        (~pd.isnull(df["Entity"]))
        # & (~pd.isnull(df["Entity_name"]))
        & (~pd.isnull(df["Material"]))
        # & (~pd.isnull(df["Material_name"]))
        & (~pd.isnull(df["Misc1"]))
        & (~pd.isnull(df["Commodity_name"]))
        & (~pd.isnull(df["Price"]))
        & (~pd.isnull(df["Year"]))
    ]
    err_code = list(set(df_error["Entity"]))
    err_msg = "本次接口共同步[%s]条数据，其中成功[%s]条，失败[%s]条，失败Entity为[%s]！" % (
        str(sum_num),
        str(df.shape[0]),
        str(df_error.shape[0]),
        err_code,
    )
    print(err_msg)
    # 特殊符号处理
    # df["Misc1"] = df["Misc1"].replace("-", "_", regex=True)
    # df["Entity"] = df["Entity"].replace("-", "_", regex=True)
    print(df)
    return df


def control_misc(df, p1):
    """
    操作Misc1维度，维度中有则更新，没有则新增
    """
    # 获取维度的编码及名称
    dim_misc = df[["Misc1", "Commodity_name"]].rename(
        columns={"Misc1": "name", "Commodity_name": "language_zh-cn"}
    )
    # 删除重复数据
    dim_misc = dim_misc.drop_duplicates(["name"], keep="first")

    # # 获取Material字段，根据Material获取ud系列字段
    # dim_temp = df[["Commodity", "Material"]]
    #
    # # 删除重复字段
    # dim_temp = dim_temp.drop_duplicates(["Commodity", "Material"],keep="first")
    #
    # # 获取Material维度
    # dim_material = dim_.get_dim_attr("Material", "Base(MQ,0)", ["name"])
    # dim_material.loc[:, "name"] = dim_material["name"].str[4:]
    #
    # dim_temp = pd.merge(
    #     dim_temp, dim_material, how="left", left_on=["Material"], right_on=["name"]
    # )
    # # 将关联不上的用“”填充
    # dim_temp = dim_temp.fillna("")
    # dim_temp = dim_temp.groupby("Commodity", as_index=False)["expectedName"].apply(
    #     lambda x: ",".join(x)
    # )
    #
    # # 做一个中间表，判断需要设置几个ud
    # dim_ud = dim_temp["expectedName"].str.split(",", expand=True)
    # for i in range(0, 8):
    #     if i in dim_ud.columns.to_list():
    #         dim_ud = dim_ud.rename(columns={i: "ud%s" % (i + 1)})
    # # 将拆分好的ud，拆到temp表中
    # dim_temp[dim_ud.columns.to_list()] = dim_temp["expectedName"].str.split(
    #     ",", expand=True
    # )
    # # 将找到的ud与主表关联
    # dim_misc = pd.merge(
    #     dim_misc, dim_temp, how="left", left_on="name", right_on="Commodity"
    # )
    #
    # # 删除无用的数据集
    # del dim_ud, dim_temp, dim_material
    #
    # # 删除多余的字段
    # for item in ["Commodity", "expectedName"]:
    #     if item in dim_misc.columns.to_list():
    #         del dim_misc[item]

    # 补充字段
    # dim_misc["parent_name"] = "#root"
    dim_misc["language_en"] = dim_misc["language_zh-cn"]
    dim_misc["is_active"] = "1"
    dim_misc["parent_name"] = "Centralized_Agreement"

    # 排序
    dim_misc = dim_misc.sort_values(by=["name"], axis=0, ascending=True).fillna("")

    # 初始化维度，并保存数据
    dim = Dimension("Misc1")
    print(dim_misc)
    rsg = dim.load_dataframe(dim_misc, "incr_replace")

    # 记录日志
    log = {
        "element_name": "Misc1维度同步成功",
        "element_type": "2",
        "sync_user": p1["user"],
        "sync_datetime": datetime.datetime.now(),
        "sync_status": "true",
    }
    dt_log = pd.DataFrame(log, index=[0])
    rdb_.insert_sql(tbl="bewg_python_log", data=dt_log, path="/05_Datatable/5_8_Log/")
    return rsg


def deal_data(df, p1):
    # 获取Material字段，根据Material获取ud系列字段
    # df = df[["Commodity", "Material", "Entity", "Price", "Year"]].rename(
    #     columns={"Commodity": "Misc1"}
    # )

    # 获取Material、Entity维度
    dim = Dimension("Material")
    dim_col = ["name", "parent_name", "is_active", "ud1"]
    dim_material = dim_.get_dim_attr(
        "Material", "Base(MQ,0)", dim_col, path="/02_Dimension/"
    )
    # 这块逻辑，是将所有的material的ud1字段设置为空，后边将能关联上的Material的ud1设置为集采
    df_material = dim_material.copy()
    del df_material["expectedName"]
    print(df_material)
    df_material["ud1"] = ""
    dim.load_dataframe(df_material, "incr_replace")
    # dim_material.loc[:, "name"] = dim_material["name"].str[4:]
    print(dim_material)

    dim_entity = dim_.get_dim_attr(
        "Entity", "Base(1,0)", ["name", "parent_name"], path="/02_Dimension/"
    )
    dim_entity = dim_entity[dim_entity["name"].str.startswith("XN")].rename(
        columns={"name": "entity_name"}
    )
    # 删除多余的字段
    if "expectedName" in dim_entity.columns.to_list():
        del dim_entity["expectedName"]
    # 获取商品对应的药品药剂
    df = pd.merge(df, dim_material, how="left", left_on=["Material"], right_on=["name"])
    # 获取映射不上的material,并打印到运行日志中
    df_null = df[pd.isnull(df["name"])]
    print("未找到的Material：%s" % list(set(df_null["Material"])))
    df = df[~pd.isnull(df["name"])]

    # 将能关联上的Material回写到Material维度中
    dim_col.append("expectedName")
    dim_col.remove("name")
    df_material = df[dim_col].rename(columns={"expectedName": "name"})
    df_material["ud1"] = "Centralized"
    df_material = df_material.drop_duplicates(["name"], keep="first")
    print(df_material)
    msg = dim.load_dataframe(df_material, "incr_replace")
    print("更新Material维度ud1结果：%s" % msg)

    # 获取组织架构信息，
    # for item in ["ud1", "parent_name", "is_active"]:
    #     if item in df.columns.to_list():
    #         del df[item]
    # df = pd.merge(
    #     df, dim_entity, how="left", left_on=["Entity"], right_on=["parent_name"]
    # )
    # # 获取映射不上的material,并打印到运行日志中
    # df_null = df[pd.isnull(df["entity_name"])]
    # print("未找到的Entity：%s" % list(set(df_null["Entity"])))
    # df = df[~pd.isnull(df["entity_name"])]
    #
    # # 将XN的节点赋值给水厂
    # df["Entity"] = df["entity_name"]
    #
    # # 删除中间表
    # del df_null
    #
    # # 删除无用的字段
    # for col in ["Material", "name", "entity_name", "parent_name"]:
    #     if col in df.columns.to_list():
    #         del df[col]
    # # 重命名字段，并添加默认值字段
    # df = df.rename(columns={"expectedName": "Material"})
    # df["Scenario"] = "Budget"
    # df["Version"] = "Y1"
    # df["push_data_time"] = datetime.datetime.now()
    # df["Department"] = "Operation"
    #
    # # 删掉重复值
    # df = df.drop_duplicates(["Material", "Misc1", "Year", "Entity"], keep="first")
    #
    # updatecol = df.drop(
    #     columns={"Material", "Misc1", "Year", "Entity"}
    # ).columns.to_list()
    # 清空并保存数据
    # tbl = "bewg_price_data"
    # del_sql = "delete from ${%s} where 1=1" % tbl
    # rdb_.exec_sql(del_sql)
    # rmsg = rdb_.insert_sql(
    #     tbl=tbl,
    #     data=df,
    #     path="/05_Datatable/5_3_Middle_Table_Target/",
    #     updatecol=updatecol,
    # )

    # 记录日志
    log = {
        "element_name": "商品价格信息表【bewg_price_data】保存成功",
        "element_type": "2",
        "sync_user": p1["user"],
        "sync_datetime": datetime.datetime.now(),
        "sync_status": "true",
    }
    dt_log = pd.DataFrame(log, index=[0])
    rdb_.insert_sql(tbl="bewg_python_log", data=dt_log, path="/05_Datatable/5_8_Log/")

    # return rmsg


def main(p1, p2):
    # 1、获取中间表数据
    df_data = get_data()

    if len(df_data) == 0:
        print("中间表数据为空")
        return

    # 2、生成misc维度逻辑
    _bo = control_misc(df_data, p1)

    # 3、生成业务数据
    _bo = deal_data(df_data, p1)


# debug
if __name__ == "__main__":
    from common._debug import para1, para2

    main(para1, para2)

