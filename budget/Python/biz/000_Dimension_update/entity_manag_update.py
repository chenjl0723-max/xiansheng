"""
added by cjl
added in 20260226
added for 更新运营项目的维度
主要逻辑：
    根据entity_info 项目表，依次写入维度：
    大区、区域、管理组织\法人、项目
剩余问题：目前项目信息不完善，无法执行代码
"""

#部署时，这些要注释以及修改
# try:
#     from common._debug import para1, para2
#     print('1',para1)
# except ImportError:
#     para1 = para2 = {}


from deepfos.element.dimension import Dimension
from deepfos.db.mysql import MySQLClient
from deepfos.element.datatable import DataTableMySQL
import pandas as pd
from datetime import datetime
from deepfos.element.variable import Variable
# from add_entity_to_flow import main as add

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)

class UpdateEntityOrg:
    def __init__(self):
        # self.year = Variable(element_name='Variable').get_value('BudYear')
        self.year = Variable('Variable').get_value('BudYear')
        self.dim = Dimension("Entity_manag")
        self.df_entity_org = pd.DataFrame(
            self.dim.query(
                expression="IDescendant(#root,0)",
                fields=["name", "parent_name"],
                as_model=False)
        ).drop(columns=["id","expectedName"])

        # print('self.df_entity_org',self.df_entity_org)


        # 获取Entity_ZT_NEW的数据
        # self.df_source = rdb_.select(None, "Entity_ZT_NEW", path="/Datatable/Middle_Table/budget_Distribution/")
        self.df_entity_info = DataTableMySQL("entity_info")
        # where = ((self.df_entity_sj.table.region_name != '供水事业部')&(self.df_entity_sj.table.project_code =='Y4420221087'))
        # where = (self.df_entity_sj.table.region_name != '供水事业部')
        where = (
                # (self.df_entity_sj.table.region_name != '供水事业部') &
                (self.df_entity_info.table.region_name.notnull()) &
                (self.df_entity_info.table.region_code.notnull()) &
                (self.df_entity_info.table.area_code.notnull()) &
                (self.df_entity_info.table.area_name.notnull())&
                (self.df_entity_info.table.Entity_org_name.notnull())&
                (self.df_entity_info.table.Entity_org.notnull())
        )

        self.df_entity = pd.DataFrame(self.df_entity_info.select_raw(columns=None, where=where))

        self.df_source = self.df_entity.copy()

        print('维度现有的行数：',len(self.df_entity_org))
        print('entity_info现在的行数',len(self.df_source))
        # print(1)



    def update_entity_org(self, p1 ,p2):
        if self.df_source.empty:
            print("源数据表为空")
            return

        # 插入法人组织树
        df_org = self.df_source.copy()
        # 更新大区
        large_new = self.update_region(df_org,'D000001')
        # 更新区域
        area_new = self.update_area(df_org)
        # 更新管理组织
        manag_new = self.update_manage(df_org)
        # 更新项目
        project_org_new = self.update_manag_project(df_org)



    def update_region(self,df,parent_name):
        df_large_area = df[["region_name", "region_code"]]
        df_large_area_existing = df_large_area[
            df_large_area["region_code"].isin(self.df_entity_org["name"])]
        # print('已有大区',len(df_large_area_existing))
        df_large_area_new = df_large_area[
            ~df_large_area["region_code"].isin(self.df_entity_org["name"])]
        # print('新增大区', len(df_large_area_new))
        if not df_large_area_existing.empty:
            df_large_area_existing = df_large_area_existing.rename(columns={
                "region_code": "name",
                "region_name": "language_zh-cn",
            })
            # print(df_large_area_existing)
            df_large_area_existing["parent_name"] = parent_name
            df_large_area_existing["language_en"] = df_large_area_existing["language_zh-cn"]
            # df_large_area_existing["ud2"] = df_large_area_existing["language_zh-cn"]
            df_large_area_existing = df_large_area_existing.drop_duplicates(["name"], keep="first")
            # rsg = self.dim.load_dataframe(df_large_area_existing, "incr_replace")
            print("维度现有大区：", list(df_large_area_existing["name"]))

        if not df_large_area_new.empty:
            print(df_large_area_new)
            df_large_area_new = df_large_area_new.rename(columns={
                "region_code": "name",
                "region_name": "language_zh-cn",
            })
            df_large_area_new["parent_name"] = parent_name
            df_large_area_new["language_en"] = df_large_area_new["language_zh-cn"]
            # df_large_area_new["ud1"] = "Operation"
            # df_large_area_new["ud2"] = df_large_area_new["language_zh-cn"]
            # df_large_area_new["ud10"] = "P04"
            df_large_area_new["isActive"] = "Y"
            df_large_area_new = df_large_area_new.drop_duplicates(["name"], keep="first")
            rsg = self.dim.load_dataframe(df_large_area_new, "incr_replace")
            print("新增大区：", list(df_large_area_new["name"]))
            return list(df_large_area_new["name"])

    def update_area(self,df):
        df_area = df[["area_name", "area_code", "region_code","region_name"]]
        df_area_existing = df_area[
            df_area["area_code"].isin(self.df_entity_org["name"])]
        df_area_new = df_area[
            ~df_area["area_code"].isin(self.df_entity_org["name"])]
        if not df_area_existing.empty:
            df_area_existing = df_area_existing.rename(columns={
                "area_code": "name",
                "area_name": "language_zh-cn",
                "region_code": "parent_name",
            })
            df_area_existing["language_en"] = df_area_existing["language_zh-cn"]
            # df_area_existing["ud2"] = df_area_existing["region_name"]
            # df_area_existing["ud4"] = df_area_existing["language_zh-cn"]
            df_area_existing = df_area_existing.drop_duplicates(["name"], keep="first")
            # rsg = self.dim.load_dataframe(df_area_existing, "incr_replace")
            print("维度现有区域：", list(df_area_existing["name"]))
        if not df_area_new.empty:
            df_area_new = df_area_new.rename(columns={
                "area_code": "name",
                "area_name": "language_zh-cn",
                "region_code": "parent_name",
            })
            df_area_new["language_en"] = df_area_new["language_zh-cn"]
            # df_area_new["ud1"] = "Operation"
            # df_area_new["ud2"] = df_area_new["region_name"]
            # df_area_new["ud4"] = df_area_new["language_zh-cn"]
            # df_area_new["ud10"] = "P03"
            df_area_new["isActive"] = "Y"
            df_area_new = df_area_new.drop_duplicates(["name"], keep="first")
            rsg = self.dim.load_dataframe(df_area_new, "incr_replace")
            print("插入新增区域：", list(df_area_new["name"]))
            return list(df_area_new["name"])



    def update_manage(self,df):
        # df_manage = df[["Entity_manag", "Entity_manag_name", "area_name", "region_name","area_code"]]
        df_manage = df[
            (df["Entity_manag"] != df["area_code"]) &
            (df["Entity_manag"] != df["region_code"])
        ][["Entity_manag", "Entity_manag_name", "area_code"]]




        df_manage = df[
            (df["Entity_manag"] != df["area_code"].str.replace('^GL_', '', regex=True)) &
            (df["Entity_manag"] != df["region_code"].str.replace('^GL_', '', regex=True))
            ][["Entity_manag", "Entity_manag_name", "area_code"]]


        df_manage_existing = df_manage[
            df_manage["Entity_manag"].isin(self.df_entity_org["name"])]
        df_manage_new = df_manage[
            ~df_manage["Entity_manag"].isin(self.df_entity_org["name"])]

        if not df_manage_existing.empty:
            df_manage_existing = df_manage_existing.rename(columns={
                "Entity_manag": "name",
                "Entity_manag_name": "language_zh-cn",
                "area_code": "parent_name",
            })
            df_manage_existing["language_en"] = df_manage_existing["language_zh-cn"]
            # df_factory_existing["ud2"] = df_factory_existing["region_name"]
            # df_factory_existing["ud4"] = df_factory_existing["area_name"]
            df_manage_existing = df_manage_existing.drop_duplicates(["name"], keep="first")
            # rsg = self.dim.load_dataframe(df_factory_existing, "incr_replace")
            print("维度现有管理组织：", list(df_manage_existing["name"]))

        if not df_manage_new.empty:
            df_manage_new = df_manage_new.rename(columns={
                "Entity_manag": "name",
                "Entity_manag_name": "language_zh-cn",
                "area_code": "parent_name",
            })
            df_manage_new["language_en"] = df_manage_new["language_zh-cn"]
            # df_factory_new["ud1"] = "Operation"
            # df_factory_new["ud2"] = df_factory_new["region_name"]
            # df_factory_new["ud4"] = df_factory_new["area_name"]
            # df_factory_new["ud10"] = "P06"
            df_manage_new["isActive"] = "Y"
            df_manage_new = df_manage_new.drop_duplicates(["name"], keep="first")
            # print(df_factory)
            rsg = self.dim.load_dataframe(df_manage_new, "incr_replace")
            print("插入新增管理组织：", list(df_manage_new["name"]))
            return list(df_manage_new["name"])

    def update_manag_project(self,df):
        # 从源数据中筛选需要更新的项目
        df_project = df[
            ["project_code", "project_name", "Entity_manag"]]
        df_project_existing = df_project[df_project["project_code"].isin(self.df_entity_org["name"])]
        df_project_new = df_project[~df_project["project_code"].isin(self.df_entity_org["name"])]

        # 更新现有项目的数据
        if not df_project_existing.empty:
            # print('更新现有项目：',df_project_existing)
            # df_project_existing['start_date'] = pd.to_datetime(df_project_existing['start_date'], format='%Y-%m-%d %H:%M:%S')
            df_project_existing = df_project_existing.rename(columns={
                "project_code": "name",
                "project_name": "language_zh-cn",
                "Entity_manag": "parent_name",
            })
            df_project_existing["language_en"] = df_project_existing["language_zh-cn"]
            # df_project_existing["ud2"] = df_project_existing["region_name"]
            # df_project_existing["ud3"] = df_project_existing["sub_factory_name"]
            # df_project_existing["ud4"] = df_project_existing["area_name"]
            # df_project_existing["isActive"] = df_project_existing["project_status"].apply(
            #     lambda x: "Y" if x == "启用" else "N")
            df_project_existing = df_project_existing.drop_duplicates(["name"], keep="first")

            # 更新现有项目
            # rsg_existing = self.dim.load_dataframe(df_project_existing, "incr_replace")
            # return df_project_existing
            print("更新现有项目：", list(df_project_existing["name"]))




        # 插入新增的项目数据
        if not df_project_new.empty:
            df_project_new = df_project_new.rename(columns={
                "project_code": "name",
                "project_name": "language_zh-cn",
                "Entity_manag": "parent_name",
            })
            df_project_new["language_en"] = df_project_new["language_zh-cn"]
            # df_project_new["ud1"] = "Operation"
            # df_project_new["ud2"] = df_project_new["region_name"]
            # df_project_new["ud3"] = df_project_new["sub_factory_name"]
            # df_project_new["ud4"] = df_project_new["area_name"]
            # df_project_new["ud5"] = df_project_new["invest_model_name"]
            # df_project_new["ud6"] = "Invariant"
            # df_project_new["ud10"] = "P02"
            # df_project_new["ud11"] = 'N'
            # df_project_new["ud12"] = "SP01"
            # df_project_new["isActive"] = df_project_new["project_status"].apply(lambda x: "Y" if x == "启用" else "N")
            df_project_new["isActive"] = "Y"
            # df_project_new["sharedmember"] = False
            df_project_new = df_project_new.drop_duplicates(["name"], keep="first")

            rsg_new = self.dim.load_dataframe(df_project_new, "incr_replace")
            print("插入新项目：", list(df_project_new["name"]))





    def entity_mapping(self):
        entity_mapping = self.df_entity_org.query("name.str.startswith('XN')", engine='python')
        entity_mapping = entity_mapping.rename(columns={
            "parent_name": "Entity_code",
            "name": "Entity"
        })
        # entity_mapping = entity_mapping.drop(columns=['expectedName'])
        entity_mapping = entity_mapping.drop_duplicates(["Entity"], keep="first")
        # print(entity_mapping)
        print('映射表长度',len(entity_mapping))
        self.df_entity_mapping.insert_df(dataframe=entity_mapping,updatecol=self.col_entity_mapping)

def main(p1,p2):
    e = UpdateEntityOrg()
    e.update_entity_org(p1,p2)
    # e.entity_mapping()

if __name__ == "__main__":
    from common.__debug import para1, para2
    # print('1',para1)
    main(para1,para2)
