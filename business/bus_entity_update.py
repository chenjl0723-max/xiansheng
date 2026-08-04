"""
added by cjl
added in 20241106
added for 更新经营计划的运营项目的维度
主要逻辑：
    根据Entity_ZT_NEW运营项目表，依次写入维度：
    大区、区域、水厂、子水厂、虚拟子水厂、项目
剩余问题：目前项目信息不完善，无法执行代码
"""

#部署时，这些要注释以及修改
try:
    from _debug import para1, para2
    print(para1)
except ImportError:
    para1 = para2 = {}
from common.commons import *
from conf.config import *
######################################################################


# from numpy.distutils.system_info import dfftw_info
from deepfos.element.dimension import Dimension
from deepfos.db.mysql import MySQLClient
from deepfos.element.datatable import DataTableMySQL
import pandas as pd
from datetime import datetime

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)

class UpdateEntityV3:
    def __init__(self):
        self.dim = Dimension("Entity")
        self.df_entity_v3 = dim_.get_dim_attr("Entity", "IDescendant(D000001,0)", fields=["name", "parent_name"])
        # print(self.df_entity_v3)
        # 获取Entity_ZT_NEW的数据
        # self.df_source = rdb_.select(None, "Entity_ZT_NEW", path="/Datatable/Middle_Table/budget_Distribution/")
        self.df_entity_sj = DataTableMySQL("Entity_ZT_NEW")

        where = (
                # (self.df_entity_sj.table.region_name != '供水事业部') &
                (self.df_entity_sj.table.region_name.notnull()) &
                (self.df_entity_sj.table.region_code.notnull()) &
                (self.df_entity_sj.table.area_code.notnull()) &
                (self.df_entity_sj.table.area_name.notnull())&
                (self.df_entity_sj.table.org_code.notnull())&
                (self.df_entity_sj.table.org_name.notnull())

        )
        cols = ['project_code','project_name','org_code','org_name','area_code','area_name','region_code','region_name','project_status']
        self.df_entity = pd.DataFrame(self.df_entity_sj.select_raw(columns=cols, where=where))
        print(self.df_entity)
        print('维度现有的行数：',len(self.df_entity_v3))
        self.df_source = self.df_entity.copy()
        print('entity_zt_new现在的行数',len(self.df_source))


    def update_entity_v3(self):
        if self.df_source.empty:
            print("源数据表为空")
            return

        # 更新大区
        self.update_large_area()
        # 更新区域
        self.update_area()
        # 更新组织
        self.update_org()
        # 更新项目
        self.update_project()

    def update_large_area(self):
        df_large_area = self.df_source[["region_name", "region_code"]]
        df_large_area_existing = df_large_area[
            df_large_area["region_code"].isin(self.df_entity_v3["name"])]
        print('已有大区',len(df_large_area_existing))
        df_large_area_new = df_large_area[
            ~df_large_area["region_code"].isin(self.df_entity_v3["name"])]
        print('新增大区', len(df_large_area_new))
        if not df_large_area_existing.empty:

            df_large_area_existing = df_large_area_existing.rename(columns={
                "region_code": "name",
                "region_name": "language_zh-cn",
            })
            # print(df_large_area_existing)
            df_large_area_existing["parent_name"] = "D000001"
            df_large_area_existing["language_en"] = df_large_area_existing["language_zh-cn"]
            df_large_area_existing = df_large_area_existing.drop_duplicates(["name"], keep="first")
            rsg = self.dim.load_dataframe(df_large_area_existing, "incr_replace")
            print("修改现有大区：", list(df_large_area_existing["name"]))
        if not df_large_area_new.empty:
            # print(df_large_area_new)
            df_large_area_new = df_large_area_new.rename(columns={
                "region_code": "name",
                "region_name": "language_zh-cn",
            })
            df_large_area_new["parent_name"] = "D000001"
            df_large_area_new["language_en"] = df_large_area_new["language_zh-cn"]
            df_large_area_new["ud7"] = "大区"
            df_large_area_new["isActive"] = "Y"
            df_large_area_new = df_large_area_new.drop_duplicates(["name"], keep="first")
            # print(df_large_area)
            rsg = self.dim.load_dataframe(df_large_area_new, "incr_replace")
            print("新增大区：", list(df_large_area_new["name"]))

    def update_area(self):
        df_area = self.df_source[["area_name", "area_code", "region_code","region_name"]]
        df_area_existing = df_area[
            df_area["area_code"].isin(self.df_entity_v3["name"])]
        df_area_new = df_area[
            ~df_area["area_code"].isin(self.df_entity_v3["name"])]
        if not df_area_existing.empty:
            df_area_existing = df_area_existing.rename(columns={
                "area_code": "name",
                "area_name": "language_zh-cn",
                "region_code": "parent_name",
            })
            df_area_existing["language_en"] = df_area_existing["language_zh-cn"]
            df_area_existing = df_area_existing.drop_duplicates(["name"], keep="first")
            rsg = self.dim.load_dataframe(df_area_existing, "incr_replace")
            print("修改现有区域：", list(df_area_existing["name"]))
        if not df_area_new.empty:
            df_area_new = df_area_new.rename(columns={
                "area_code": "name",
                "area_name": "language_zh-cn",
                "region_code": "parent_name",
            })
            df_area_new["language_en"] = df_area_new["language_zh-cn"]
            df_area_new["ud7"] = "区域公司"
            df_area_new["isActive"] = "Y"
            df_area_new = df_area_new.drop_duplicates(["name"], keep="first")
            # print(df_area)
            rsg = self.dim.load_dataframe(df_area_new, "incr_replace")
            print("插入新增区域：", list(df_area_new["name"]))

    def update_org(self):
        df_org = self.df_source[["org_name", "org_code", "area_name", "region_name","area_code","region_code"]]
        df_org_existing = df_org[
            df_org["org_code"].isin(self.df_entity_v3["name"])]
        df_org_new = df_org[
            ~df_org["org_code"].isin(self.df_entity_v3["name"])]

        if not df_org_existing.empty:
            if (df_org_existing["org_code"] == df_org_existing["area_code"]).any():
                df_org_existing = df_org_existing[df_org_existing["org_code"] == df_org_existing["area_code"]]
                print("修改原有组织：直接挂到大区下面的组织有%s条：" % len(df_org_existing["org_code"]),list(df_org_existing["org_code"]))
                # df_org_existing = df_org_existing.rename(columns={
                #     "org_code": "name",
                #     "org_name": "language_zh-cn",
                #     "region_code": "parent_name",
                # })
                # df_org_existing["language_en"] = df_org_existing["language_zh-cn"]
                # df_org_existing = df_org_existing.drop_duplicates(["name"], keep="first")
                # # print(df_factory)
                # rsg = self.dim.load_dataframe(df_org_existing, "incr_replace")
                # print("修改现有组织1、", list(df_org_existing["name"]))

            df_org_existing = df_org_existing[df_org_existing["org_code"] != df_org_existing["area_code"]]
            df_org_existing = df_org_existing.rename(columns={
                "org_code": "name",
                "org_name": "language_zh-cn",
                "area_code": "parent_name",
            })
            df_org_existing["language_en"] = df_org_existing["language_zh-cn"]
            df_org_existing = df_org_existing.drop_duplicates(["name"], keep="first")
            # print(df_factory)
            rsg = self.dim.load_dataframe(df_org_existing, "incr_replace")
            print("修改现有组织：", list(df_org_existing["name"]))

        if not df_org_new.empty:
            if (df_org_new["org_code"] == df_org_new["area_code"]).any():
                df_org_new = df_org_new[df_org_new["org_code"] == df_org_new["area_code"]]
                print("直接挂到大区下面的组织有：", df_org_new["org_code"])
                # df_org_new = df_org_new.rename(columns={
                #     "org_code": "name",
                #     "org_name": "language_zh-cn",
                #     "region_code": "parent_name",
                # })
                # df_org_new["language_en"] = df_org_new["language_zh-cn"]
                # df_org_new["isActive"] = "Y"
                # df_org_new = df_org_new.drop_duplicates(["name"], keep="first")
                # # print(df_factory)
                # rsg = self.dim.load_dataframe(df_org_new, "incr_replace")
                # print("插入新增组织1、", list(df_org_new["name"]))
            df_org_new = df_org_new[df_org_new["org_code"] != df_org_new["area_code"]]
            df_org_new = df_org_new.rename(columns={
                "org_code": "name",
                "org_name": "language_zh-cn",
                "area_code": "parent_name",
            })
            df_org_new["language_en"] = df_org_new["language_zh-cn"]
            df_org_new["isActive"] = "Y"
            df_org_new = df_org_new.drop_duplicates(["name"], keep="first")
            # print(df_factory)
            rsg = self.dim.load_dataframe(df_org_new, "incr_replace")
            print("插入新增组织：", list(df_org_new["name"]))


    def update_project(self):
        # 从源数据中筛选需要更新的项目
        df_project = self.df_source[
            ["project_code", "project_name", "org_name", "org_code", "area_name", "region_name","area_code","project_status"]]

        df_project_existing = df_project[df_project["project_code"].isin(self.df_entity_v3["name"])]
        df_project_new = df_project[~df_project["project_code"].isin(self.df_entity_v3["name"])]

        # 更新现有项目的数据
        if not df_project_existing.empty:
            # print('更新现有项目：',df_project_existing)
            df_project_existing = df_project_existing.rename(columns={
                "project_code": "name",
                "project_name": "language_zh-cn",
                "org_code": "parent_name",
            })
            df_project_existing["language_en"] = df_project_existing["language_zh-cn"]
            df_project_existing["ud6"] = "项目"
            df_project_existing["ud9"] = "010103"
            df_project_existing["ud11"] = df_project_existing["project_status"]
            df_project_existing["isActive"] = df_project_existing["project_status"].apply(
                lambda x: "Y" if x == "启用" else "N")
            df_project_existing = df_project_existing.drop_duplicates(["name"], keep="first")

            # 更新现有项目
            rsg_existing = self.dim.load_dataframe(df_project_existing, "incr_replace")
            # print(df_project_existing)
            print("更新现有项目：", list(df_project_existing["name"]))


        # 插入新增的项目数据
        if not df_project_new.empty:
            df_project_new = df_project_new.rename(columns={
                "project_code": "name",
                "project_name": "language_zh-cn",
                "org_code": "parent_name",
            })
            df_project_new["language_en"] = df_project_new["language_zh-cn"]
            df_project_new["ud6"] = "项目"
            df_project_new["ud9"] = "010103"
            df_project_new["ud11"] = df_project_new["project_status"]
            df_project_new["isActive"] = df_project_new["project_status"].apply(lambda x: "Y" if x == "启用" else "N")
            df_project_new = df_project_new.drop_duplicates(["name"], keep="first")
            # 插入新增项目
            rsg_new = self.dim.load_dataframe(df_project_new, "incr_replace")
            print("插入新项目：", list(df_project_new["name"]))



def main(p1,p2):
    e = UpdateEntityV3()
    e.update_entity_v3()

if __name__ == "__main__":
    # print(para1)
    main(para1,para2)
