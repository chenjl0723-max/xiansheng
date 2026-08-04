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
        self.dim = Dimension("Entity_org")
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

        # 插入管理组织树
        df_GL = self.df_source.copy()
        # 更新大区
        large_new = self.update_region(df_GL,'D000001')
        # 更新区域
        area_new = self.update_area(df_GL)
        # 更新管理组织
        manage_new = self.update_manage(df_GL)
        # 更新项目
        project_new = self.update_org_project(df_GL)


        # 插入法人组织树
        df_ORG = self.df_source.copy()
        df_ORG['region_code'] = 'ORG_' + df_ORG['region_code'].astype(str)
        df_ORG['area_code'] = 'ORG_' + df_ORG['area_code'].astype(str)

        # 更新大区
        ORG_large_new = self.update_region(df_ORG,'ORG_D000001')
        # 更新区域
        ORG_area_new = self.update_area(df_ORG)
        # 更新法人组织
        ORG_org_new = self.update_org(df_ORG)
        # 更新项目
        ORG_project_new = self.update_manage_project(df_ORG)


        all_df = pd.concat([large_new, area_new, manage_new,ORG_large_new,ORG_area_new,ORG_org_new,project_new,ORG_project_new], ignore_index=True)
        data = {
            "language_zh-cn": [
                "北控水务集团（法人组织）",
                "北控水务集团（管理组织）"
            ],
            "name": [
                "ORG_D000001",
                "D000001"
            ],
            "parent_name": [
                "#root",
                "#root"
            ],
            "language_en": [
                "北控水务集团（法人组织）",
                "北控水务集团（管理组织）"
            ],
            "sharedmember": [
                False,
                False
            ]
        }
        all_df = pd.concat([pd.DataFrame(data),all_df ], ignore_index=True)
        # all_df = all_df.drop_duplicates(subset=['name',  'sharedmember'], keep='first')

        rsg_new = self.dim.load_dataframe(all_df, "full_replace")


        return rsg_new

    def update_region(self,df,parent_name):
        df_large_area = df[["region_name", "region_code"]]

        df_large_area = df_large_area.rename(columns={
            "region_code": "name",
            "region_name": "language_zh-cn",
        })
        df_large_area["parent_name"] = parent_name
        df_large_area["language_en"] = df_large_area["language_zh-cn"]
        # df_large_area["ud1"] = "Operation"
        # df_large_area["ud2"] = df_large_area["language_zh-cn"]
        # df_large_area["ud10"] = "P04"
        # df_large_area["isActive"] = "Y"
        df_large_area["sharedmember"] = False
        df_large_area = df_large_area.drop_duplicates(["name"], keep="first")
        # rsg = self.dim.load_dataframe(df_large_area, "incr_replace")
        print("新增大区：%s 条"%len(df_large_area), list(df_large_area["name"]))
        return df_large_area




    def update_area(self,df):
        df_area = df[["area_name", "area_code", "region_code"]]
        df_area = df_area.rename(columns={
            "area_code": "name",
            "area_name": "language_zh-cn",
            "region_code": "parent_name",
        })
        df_area["language_en"] = df_area["language_zh-cn"]
        # df_area["ud1"] = "Operation"
        # df_area["ud2"] = df_area["region_name"]
        # df_area["ud4"] = df_area["language_zh-cn"]
        # df_area["ud10"] = "P03"
        # df_area["isActive"] = "Y"
        df_area["sharedmember"] = False
        df_area = df_area.drop_duplicates(["name"], keep="first")
        # rsg = self.dim.load_dataframe(df_area, "incr_replace")
        print("插入新增区域：%s 条"%len(df_area), list(df_area["name"]))
        return df_area


    def update_org(self,df):
        df_org = df[["Entity_org_name", "Entity_org","area_code"]]

        # 去除GL_前缀进行比较
        # df_org = df[
        #     (df["Entity_org"] != df["area_code"].str.replace('^ORG_', '', regex=True)) &
        #     (df["Entity_org"] != df["region_code"].str.replace('^ORG_', '', regex=True))
        #     ][["Entity_org", "Entity_org_name", "area_code"]]


        df_org = df_org.rename(columns={
            "Entity_org": "name",
            "Entity_org_name": "language_zh-cn",
            "area_code": "parent_name",
        })
        df_org["language_en"] = df_org["language_zh-cn"]
        # df_org["ud1"] = "Operation"
        # df_org["ud2"] = df_org["region_name"]
        # df_org["ud4"] = df_org["area_name"]
        # df_org["ud10"] = "P06"
        # df_org["isActive"] = "Y"
        df_org["sharedmember"] = False
        df_org = df_org.drop_duplicates(["name"], keep="first")
        # print(df_factory)
        # rsg = self.dim.load_dataframe(df_org, "incr_replace")
        print("插入新增法人组织：%s 条"%len(df_org), list(df_org["name"]))
        return df_org




    def update_manage(self,df):

        df_manage = df[["Entity_manag", "Entity_manag_name","area_code","region_code"]]

        # 去除GL_前缀进行比较
        df_manage = df[
            (df["Entity_manag"] != df["area_code"]) &
            (df["Entity_manag"] != df["region_code"])
            ][["Entity_manag", "Entity_manag_name", "area_code"]]



        df_manage = df_manage.rename(columns={
            "Entity_manag": "name",
            "Entity_manag_name": "language_zh-cn",
            "area_code": "parent_name",
        })
        df_manage["language_en"] = df_manage["language_zh-cn"]
        # df_manage["ud1"] = "Operation"
        # df_manage["ud2"] = df_manage["region_name"]
        # df_manage["ud4"] = df_manage["area_name"]
        # df_manage["ud10"] = "P06"
        # df_manage["isActive"] = "Y"
        df_manage["sharedmember"] = False
        df_manage = df_manage.drop_duplicates(["name"], keep="first")
        # print(df_factory)
        # rsg = self.dim.load_dataframe(df_manage, "incr_replace")
        print("插入新增管理组织：%s 条"%len(df_manage), list(df_manage["name"]))
        return df_manage



    def update_org_project(self,df):
        # 从源数据中筛选需要更新的项目
        df_project = df[
            ["project_code", "project_name", "Entity_org"]]

        df_project = df_project.rename(columns={
            "project_code": "name",
            "project_name": "language_zh-cn",
            "Entity_org": "parent_name",
        })
        df_project["language_en"] = df_project["language_zh-cn"]

        # df_project["isActive"] = "Y"
        df_project["sharedmember"] = True
        # df_project["shared_member"] = "false"
        df_project = df_project.drop_duplicates(["name"], keep="first")
        # 插入新增项目
        # self.update_manage_project()
        # rsg_new = self.dim.load_dataframe(df_project, "incr_replace")
        print("插入新项目：%s 条" % len(df_project), list(df_project["name"]))
        return df_project
        # print("插入新项目：%s 条"%len(df_project),list(df_project["name"]))




    def update_manage_project(self,df):
        # 从源数据中筛选需要更新的项目
        df_project = df[
            ["project_code", "project_name","Entity_manag","area_code","region_code"]]

        # 检查管理组织编码是否等于大区或区域编码的后缀
        # df_project['Entity_manag'] = df_project.apply(
        #     lambda row: 'GL_' + row['Entity_manag']
        #     if row['Entity_manag'] in [row['region_code'].replace('GL_', ''), row['area_code'].replace('GL_', '')]
        #     else row['Entity_manag'],
        #     axis=1
        # )

        df_project = df_project.rename(columns={
            "project_code": "name",
            "project_name": "language_zh-cn",
            "Entity_manag": "parent_name",
        })[["name", "language_zh-cn", "parent_name"]]
        df_project["language_en"] = df_project["language_zh-cn"]
        # df_project["isActive"] = "Y"
        df_project["sharedmember"] = False
        df_project = df_project.drop_duplicates(["name"], keep="first")
        # df = df_project.head(1)
        # rsg_new = self.dim.load_dataframe(df_project, "full_replace")
        print("插入新项目：%s 条" % len(df_project), list(df_project["name"]))
        return df_project






def main(p1,p2):
    e = UpdateEntityOrg()
    e.update_entity_org(p1,p2)


if __name__ == "__main__":
    from common.__debug import para1, para2
    # print('1',para1)
    main(para1,para2)
