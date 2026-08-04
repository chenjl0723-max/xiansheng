"""
added by wlm
added in 20230821
added for 关键节点、产值计划、支付计划计算逻辑test
主要逻辑：
    见：https://proinnova.yuque.com/zpkolg/edn0y5/hrb69esg12lnmsp1#LScb
剩余问题：
"""

from business.common.commons import *
from business.conf.config import key_map

import pandas as pd
import datetime


def get_org_mapping():
    """
    用于翻译大区、区域、法人代表从长ID换成短ID
    """
    # 获取组织架构信息，翻译主数据中的大区、区域、法人公司等字段
    df_org = rdb_.select(
        columns=["code", "pk_org"], tbl="org_data", path="/ETL/Form_Business/"
    )
    # 获取项目数据，并将法人公司由长ID换成短ID
    df_mapping = pd.DataFrame(
        {
            "key": list(df_org["pk_org"]),
            "value": list(df_org["code"]),
        }
    ).set_index("key")
    return df_mapping["value"].to_dict()


def get_account_mapping():
    """
    获取科目映射关系
    """
    df_acc = rdb_.select(
        ["Account_Name", "Account_ID"],
        "Account_Mapping_DAT",
        path="/ETL/Form_Business/",
    )

    # 获取项目数据，并将法人公司由长ID换成短ID
    df_mapping = pd.DataFrame(
        {
            "key": list(df_acc["Account_Name"]),
            "value": list(df_acc["Account_ID"]),
        }
    ).set_index("key")
    return df_mapping["value"].to_dict()


def get_entity():
    """
    获取entity维度信息
    """
    df_entity = dim_.get_dim_attr(
        "Entity", "Base(#root,0)", ["name", "parent_name", "ud2"], "/Dimension/"
    )
    if "ud2" not in df_entity.columns.to_list():
        df_entity["ud2"] = ""
    else:
        df_entity["ud2"] = df_entity["ud2"].fillna("")
    df_entity = df_entity[["name", "parent_name", "ud2"]]
    # print(df_entity)
    return df_entity


def control_df(df_data, column, type):
    """
    通用处理中间表与Entity的关系
    """
    # 获取年份变量
    year = var_.get_variable("Variable", "Year")

    df_entity = get_entity()

    period = str(datetime.datetime.now().month)

    # 删掉无用的字段
    if "_id" in df_data.columns.to_list():
        del df_data["_id"]
    # 特殊处理年度字段
    df_data["Year"] = df_data["Year"].astype(str)
    df_data.loc[df_data["Scenario"] == df_data["Year"].astype(str), "Scenario"] = "Year"

    # 不用额外处理场景
    # key = key_map[period]
    # list_scenario = key.split(";")
    # source_data = pd.DataFrame()
    # if len(list_scenario) == 2:
    #     source_data = df_data[
    #         (df_data["Year"] == year)
    #         & (df_data["Scenario"] == year)
    #     ]
    #     source_data["Scenario"] = list_scenario[1]
    # df_data = df_data[
    #     (df_data["Year"] == str(int(year))) & (df_data["Scenario"] == list_scenario[0])
    # ]
    # if not source_data.empty:
    #     source_data = df_data.append(source_data)
    # else:
    #     source_data = df_data

    source_data = df_data.copy()

    # 中间表数据与Entity维度关联
    if not source_data.empty:
        source_data = pd.merge(
            source_data,
            df_entity,
            how="left",
            left_on=[column],
            right_on=["name"],
        )
        # print('source_date1',source_data)
        # 获取未找到的项目编码并打印出来
        df_null = source_data[pd.isnull(source_data["name"])]
        # print('df_null',df_null)
        print("【%s】-未在Entity找到项目编码的数据为：%s" % (type, list(set(df_null[column]))))

        source_data = source_data[~pd.isnull(source_data["name"])]
        # print('source_data2',source_data)
        return source_data
    else:
        return pd.DataFrame()



def main(p1, p2):
    pass


# debug
if __name__ == "__main__":
    from conf._evn import p1, p2

    p2 = {"Year": "2023", "Scenario": "Year,M1,M2", "Incorporated_Company": "Ntest0101"}
    main(p1, p2)
