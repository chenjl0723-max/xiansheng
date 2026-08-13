"""
added by cjl
added in 20260130
added for 更新分析模型的Entity维度
主要逻辑：
    取小业态项目数据中间表和污水业务预算项目中间表进Entity_analysis维度
剩余问题：
"""

#部署时，这些要注释以及修改
# try:
#     from common._debug import para1, para2
#     print('1',para1)
# except ImportError:
#     para1 = para2 = {}

# from numpy.distutils.system_info import dfftw_info
from deepfos.element.dimension import Dimension
from deepfos.db.mysql import MySQLClient
from deepfos.element.datatable import DataTableMySQL
from deepfos.element.finmodel import FinancialCube
from deepfos.element.datatable import DataTableClickHouse
import pandas as pd
import numpy as np
from datetime import datetime
from deepfos.element.variable import Variable
from deepfos.options import OPTION

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)


class UpdateEntityV3:
    def __init__(self):
        # self.year = Variable(element_name='Variable').get_value('BudYear')
        self.year = Variable('Variable').get_value('BudYear')
        self.dim = Dimension("Entity")
        self.df_entity_v3 = pd.DataFrame(
            self.dim.query(
                expression="Descendant(1,0)",
                fields=["name", "parent_name"],
                as_model=False)
        ).drop(columns=["id", "expectedName"])

        print('self.df_entity_v3', self.df_entity_v3)

        # self.df_entity_v3 = dim_.get_dim_attr("Entity", "Descendant(1,0)", fields=["name", "parent_name"])
        # print('self.df_entity_v3',self.df_entity_v3)
        # 获取Entity_ZT_NEW的数据
        # self.df_source = rdb_.select(None, "Entity_ZT_NEW", path="/Datatable/Middle_Table/budget_Distribution/")
        self.df_entity_sj = DataTableMySQL("Entity_ZT_NEW")
        # where = ((self.df_entity_sj.table.region_name != '供水事业部')&(self.df_entity_sj.table.project_code =='Y4420221087'))
        # where = (self.df_entity_sj.table.region_name != '供水事业部')
        where = (
            # (self.df_entity_sj.table.region_name != '供水事业部') &
                (self.df_entity_sj.table.region_name.notnull()) &
                (self.df_entity_sj.table.region_code.notnull()) &
                (self.df_entity_sj.table.area_code.notnull()) &
                (self.df_entity_sj.table.area_name.notnull()) &
                (self.df_entity_sj.table.factory_code.notnull()) &
                (self.df_entity_sj.table.factory_name.notnull()) &
                (self.df_entity_sj.table.sub_factory_code.notnull()) &
                (self.df_entity_sj.table.sub_factory_name.notnull())
        )
        self.df_entity = pd.DataFrame(self.df_entity_sj.select_raw(columns=None, where=where))
        # 替换 `name` 列中 '-' 为 '_'
        self.df_entity["sub_factory_code"] = self.df_entity["sub_factory_code"].str.replace("-", "_")
        print('维度现有的行数：', len(self.df_entity_v3))
        self.df_source = self.df_entity.copy()

        print('entity_zt_new现在的行数', len(self.df_source))
        # print(1)

        # 水厂项目分摊比例表
        self.df_wpa = DataTableMySQL("works_project_apportion")
        # self.dt_wpa_data = pd.DataFrame(self.df_wpa.select_raw(columns=['Operating_the_project']))
        # self.df_wpa_col = pd.DataFrame(self.df_wpa.select_raw()).columns

        # 组织映射关系表
        self.df_entity_mapping = DataTableMySQL("Entity_mapping")
        self.dt_entity_mapping = pd.DataFrame(self.df_entity_mapping.select_raw(columns=['Entity', 'Entity_code']))
        self.col_entity_mapping = self.dt_entity_mapping.columns

        # 水厂基本信息表
        self.df_basic = DataTableMySQL("basic_info")

    def update_entity_v3(self, p1, p2):
        if self.df_source.empty:
            print("源数据表为空")
            return

        # 更新大区
        large_new = self.update_large_area()
        # 更新区域
        area_new = self.update_area()
        # 更新水厂
        factory_new = self.update_factory()
        # 更新子水厂
        sub_factory_new = self.update_sub_factory()
        # 更新虚拟子水厂
        virtual_sub_factory_new = self.update_virtual_sub_factory()
        # 更新项目
        project_new = self.update_project()

        combined_updates = (large_new or []) + (area_new or []) + \
                           (sub_factory_new or []) + (virtual_sub_factory_new or []) + (project_new or [])

        if combined_updates:
            print("所有更新的维度列表：", combined_updates)
        # combined_updates = ['Y3220210083']
        # add(p1,p2,combined_updates)

    def update_large_area(self):
        df_large_area = self.df_source[["region_name", "region_code"]]
        df_large_area_existing = df_large_area[
            df_large_area["region_code"].isin(self.df_entity_v3["name"])]
        # print('已有大区',len(df_large_area_existing))
        df_large_area_new = df_large_area[
            ~df_large_area["region_code"].isin(self.df_entity_v3["name"])]
        # print('新增大区', len(df_large_area_new))
        if not df_large_area_existing.empty:
            df_large_area_existing = df_large_area_existing.rename(columns={
                "region_code": "name",
                "region_name": "language_zh-cn",
            })
            # print(df_large_area_existing)
            df_large_area_existing["parent_name"] = "1"
            df_large_area_existing["language_en"] = df_large_area_existing["language_zh-cn"]
            df_large_area_existing["ud2"] = df_large_area_existing["language_zh-cn"]
            df_large_area_existing = df_large_area_existing.drop_duplicates(["name"], keep="first")
            # rsg = self.dim.load_dataframe(df_large_area_existing, "incr_replace")
            print("维度现有大区：", list(df_large_area_existing["name"]))

        if not df_large_area_new.empty:
            print(df_large_area_new)
            df_large_area_new = df_large_area_new.rename(columns={
                "region_code": "name",
                "region_name": "language_zh-cn",
            })
            df_large_area_new["parent_name"] = "1"
            df_large_area_new["language_en"] = df_large_area_new["language_zh-cn"]
            df_large_area_new["ud1"] = "Operation"
            df_large_area_new["ud2"] = df_large_area_new["language_zh-cn"]
            df_large_area_new["ud10"] = "P04"
            df_large_area["isActive"] = "Y"
            df_large_area_new = df_large_area_new.drop_duplicates(["name"], keep="first")
            rsg = self.dim.load_dataframe(df_large_area_new, "incr_replace")
            print("新增大区：", list(df_large_area_new["name"]))
            return list(df_large_area_new["name"])

    def update_area(self):
        df_area = self.df_source[["area_name", "area_code", "region_code", "region_name"]]
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
            df_area_existing["ud2"] = df_area_existing["region_name"]
            df_area_existing["ud4"] = df_area_existing["language_zh-cn"]
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
            df_area_new["ud1"] = "Operation"
            df_area_new["ud2"] = df_area_new["region_name"]
            df_area_new["ud4"] = df_area_new["language_zh-cn"]
            df_area_new["ud10"] = "P03"
            df_area_new["isActive"] = "Y"
            df_area_new = df_area_new.drop_duplicates(["name"], keep="first")
            rsg = self.dim.load_dataframe(df_area_new, "incr_replace")
            print("插入新增区域：", list(df_area_new["name"]))
            return list(df_area_new["name"])

    def update_factory(self):
        df_factory = self.df_source[["factory_name", "factory_code", "area_name", "region_name", "area_code"]]
        df_factory_existing = df_factory[
            df_factory["factory_code"].isin(self.df_entity_v3["name"])]
        df_factory_new = df_factory[
            ~df_factory["factory_code"].isin(self.df_entity_v3["name"])]

        if not df_factory_existing.empty:
            df_factory_existing = df_factory_existing.rename(columns={
                "factory_code": "name",
                "factory_name": "language_zh-cn",
                "area_code": "parent_name",
            })
            df_factory_existing["language_en"] = df_factory_existing["language_zh-cn"]
            df_factory_existing["ud2"] = df_factory_existing["region_name"]
            df_factory_existing["ud4"] = df_factory_existing["area_name"]
            df_factory_existing = df_factory_existing.drop_duplicates(["name"], keep="first")
            # rsg = self.dim.load_dataframe(df_factory_existing, "incr_replace")
            print("维度现有水厂：", list(df_factory_existing["name"]))

        if not df_factory_new.empty:
            df_factory_new = df_factory_new.rename(columns={
                "factory_code": "name",
                "factory_name": "language_zh-cn",
                "area_code": "parent_name",
            })
            df_factory_new["language_en"] = df_factory_new["language_zh-cn"]
            df_factory_new["ud1"] = "Operation"
            df_factory_new["ud2"] = df_factory_new["region_name"]
            df_factory_new["ud4"] = df_factory_new["area_name"]
            df_factory_new["ud10"] = "P06"
            df_factory_new["isActive"] = "Y"
            df_factory_new = df_factory_new.drop_duplicates(["name"], keep="first")
            # print(df_factory)
            rsg = self.dim.load_dataframe(df_factory_new, "incr_replace")
            print("插入新增水厂：", list(df_factory_new["name"]))
            return list(df_factory_new["name"])

    def update_sub_factory(self):
        df_sub_factory = self.df_source[
            ["sub_factory_name", "sub_factory_code", "factory_code", "region_name", "area_name"]]
        df_sub_factory_existing = df_sub_factory[
            df_sub_factory["sub_factory_code"].isin(self.df_entity_v3["name"])]
        df_sub_factory_new = df_sub_factory[
            ~df_sub_factory["sub_factory_code"].isin(self.df_entity_v3["name"])]

        if not df_sub_factory_existing.empty:
            df_sub_factory_existing = df_sub_factory_existing.rename(columns={
                "sub_factory_code": "name",
                "sub_factory_name": "language_zh-cn",
                "factory_code": "parent_name",
            })
            df_sub_factory_existing["language_en"] = df_sub_factory_existing["language_zh-cn"]
            df_sub_factory_existing["ud2"] = df_sub_factory_existing["region_name"]
            df_sub_factory_existing["ud3"] = df_sub_factory_existing["language_zh-cn"]
            df_sub_factory_existing["ud4"] = df_sub_factory_existing["area_name"]
            df_sub_factory_existing = df_sub_factory_existing.drop_duplicates(["name"], keep="first")
            # rsg = self.dim.load_dataframe(df_sub_factory_existing, "incr_replace")
            print("维度现有子水厂：", list(df_sub_factory_existing["name"]))

        if not df_sub_factory_new.empty:
            df_sub_factory_new = df_sub_factory_new.rename(columns={
                "sub_factory_code": "name",
                "sub_factory_name": "language_zh-cn",
                "factory_code": "parent_name",
            })
            df_sub_factory_new["language_en"] = df_sub_factory_new["language_zh-cn"]
            df_sub_factory_new["ud1"] = "Operation"
            df_sub_factory_new["ud2"] = df_sub_factory_new["region_name"]
            df_sub_factory_new["ud3"] = df_sub_factory_new["language_zh-cn"]
            df_sub_factory_new["ud4"] = df_sub_factory_new["area_name"]
            df_sub_factory_new["ud6"] = "Invariant"
            df_sub_factory_new["ud10"] = "P05"
            df_sub_factory_new["isActive"] = "Y"
            df_sub_factory_new = df_sub_factory_new.drop_duplicates(["name"], keep="first")
            rsg = self.dim.load_dataframe(df_sub_factory_new, "incr_replace")
            print("插入新增子水厂：", list(df_sub_factory_new["name"]))
            return list(df_sub_factory_new["name"])

            # 新增子水厂时，更新水厂基本信息填报表
            df_basic = df_sub_factory_new[["name", "area_name", "region_name", "ud1", "ud6"]]
            df_basic = df_basic.rename(columns={
                "name": "entity",
                "area_name": "dist",
                "region_name": "rgn",
                "ud1": "department",
                "ud6": "nature"
            })
            df_basic["inv_pattern"] = "BOT"
            df_basic["special_type"] = "SP01"
            df_basic["Year"] = self.year
            self.df_basic.insert_df(df_basic, ["dist", "rgn", "department", "nature", "inv_pattern", "special_type"])
            return list(df_sub_factory_new["name"])

    def update_virtual_sub_factory(self):
        df_virtual_sub_factory = self.df_source[
            ["sub_factory_name", "sub_factory_code", "factory_code", "region_name", "area_name"]].copy()

        # 使用 .loc 进行安全的赋值操作
        df_virtual_sub_factory.loc[:, "name"] = df_virtual_sub_factory["sub_factory_code"].apply(
            lambda x: x.replace("PS", "XN") if x.startswith("PS") else x)
        print(df_virtual_sub_factory)
        df_virtual_sub_factory_existing = df_virtual_sub_factory[
            df_virtual_sub_factory["sub_factory_code"].isin(self.df_entity_v3["name"])]
        df_virtual_sub_factory_new = df_virtual_sub_factory[
            ~df_virtual_sub_factory["sub_factory_code"].isin(self.df_entity_v3["name"])]

        # 修改原有虚拟子水厂
        if not df_virtual_sub_factory_existing.empty:
            # df_virtual_sub_factory_existing["name"] = df_virtual_sub_factory_existing["sub_factory_code"].apply(lambda x: x.replace("PS", "XN"))
            df_virtual_sub_factory_existing = df_virtual_sub_factory_existing.rename(columns={
                "sub_factory_name": "language_zh-cn",
                "sub_factory_code": "parent_name",
            })
            df_virtual_sub_factory_existing["language_en"] = df_virtual_sub_factory_existing["language_zh-cn"]
            df_virtual_sub_factory_existing["ud2"] = df_virtual_sub_factory_existing["region_name"]
            df_virtual_sub_factory_existing["ud4"] = df_virtual_sub_factory_existing["area_name"]
            df_virtual_sub_factory_existing = df_virtual_sub_factory_existing.drop_duplicates(["name"], keep="first")
            # rsg = self.dim.load_dataframe(df_virtual_sub_factory_existing, "incr_replace")
            print("维度现有虚拟子水厂：", list(df_virtual_sub_factory_existing["name"]))
            # print("维度现有虚拟子水厂：", df_virtual_sub_factory_existing)

        # 新增虚拟子水厂
        if not df_virtual_sub_factory_new.empty:
            # df_virtual_sub_factory["name"] = df_virtual_sub_factory["sub_factory_no"].apply(lambda x: x.replace("PS", "XN"))
            # df_virtual_sub_factory_new["name"] = df_virtual_sub_factory_new["sub_factory_code"].apply(lambda x: x.replace("PS", "XN"))
            df_virtual_sub_factory_new = df_virtual_sub_factory_new.rename(columns={
                "sub_factory_name": "language_zh-cn",
                "sub_factory_code": "parent_name",
            })
            df_virtual_sub_factory_new["language_en"] = df_virtual_sub_factory_new["language_zh-cn"]
            df_virtual_sub_factory_new["ud1"] = "Operation"
            df_virtual_sub_factory_new["ud2"] = df_virtual_sub_factory_new["region_name"]
            df_virtual_sub_factory_new["ud4"] = df_virtual_sub_factory_new["area_name"]
            df_virtual_sub_factory_new["ud6"] = "Invariant"
            df_virtual_sub_factory_new["ud10"] = "P01"
            df_virtual_sub_factory_new["isActive"] = "Y"
            df_virtual_sub_factory_new = df_virtual_sub_factory_new.drop_duplicates(["name"], keep="first")

            rsg = self.dim.load_dataframe(df_virtual_sub_factory_new, "incr_replace")
            print("插入新增虚拟子水厂：", list(df_virtual_sub_factory_new["name"]))
            return list(df_virtual_sub_factory_new["name"])

    def update_project(self):
        # 获取现有的项目数据
        existing_projects = self.df_entity_v3[self.df_entity_v3["name"].isin(self.df_source["project_code"])]

        # 从源数据中筛选需要更新的项目
        df_project = self.df_source[
            ["project_code", "project_name", "sub_factory_code", "sub_factory_name", "region_name", "area_name",
             "invest_model_name",
             "start_date", "project_status", "is_JG"]]
        df_project_existing = df_project[df_project["project_code"].isin(self.df_entity_v3["name"])]
        df_project_new = df_project[~df_project["project_code"].isin(self.df_entity_v3["name"])]

        # 更新现有项目的数据
        if not df_project_existing.empty:
            # print('更新现有项目：',df_project_existing)
            # df_project_existing['start_date'] = pd.to_datetime(df_project_existing['start_date'], format='%Y-%m-%d %H:%M:%S')
            df_project_existing = df_project_existing.rename(columns={
                "project_code": "name",
                "project_name": "language_zh-cn",
                "sub_factory_code": "parent_name",
            })
            df_project_existing["language_en"] = df_project_existing["language_zh-cn"]
            df_project_existing["ud2"] = df_project_existing["region_name"]
            df_project_existing["ud3"] = df_project_existing["sub_factory_name"]
            df_project_existing["ud4"] = df_project_existing["area_name"]
            df_project_existing["isActive"] = df_project_existing["project_status"].apply(
                lambda x: "Y" if x == "启用" else "N")
            df_project_existing = df_project_existing.drop_duplicates(["name"], keep="first")

            # 更新现有项目
            # rsg_existing = self.dim.load_dataframe(df_project_existing, "incr_replace")
            print("更新现有项目：", list(df_project_existing["name"]))

            # 插入水厂分摊比例表
            df_work = df_project_existing[["name", "parent_name"]]
            # # df_work = df_project_existing[["language_zh-cn", "parent_name"]]
            df_work = df_work.rename(columns={
                "parent_name": "water_works",
                "name": "Operating_the_project"
            })
            df_work["water_works"] = df_work["water_works"].str.replace("^PS", "XN", regex=True)
            df_work["department"] = "Operation"
            df_work["Year"] = self.year
            df_work["Version"] = "Y1"
            # print('df_work',df_work)
            self.df_wpa.insert_df(df_work, ['water_works', 'department'])
            print('现有项目插入水厂分摊比例', df_work)

        # 插入新增的项目数据
        if not df_project_new.empty:
            df_project_new = df_project_new.rename(columns={
                "project_code": "name",
                "project_name": "language_zh-cn",
                "sub_factory_code": "parent_name",
            })
            df_project_new["language_en"] = df_project_new["language_zh-cn"]
            df_project_new["ud1"] = "Operation"
            df_project_new["ud2"] = df_project_new["region_name"]
            df_project_new["ud3"] = df_project_new["sub_factory_name"]
            df_project_new["ud4"] = df_project_new["area_name"]
            df_project_new["ud5"] = df_project_new["invest_model_name"]
            df_project_new["ud6"] = "Invariant"
            df_project_new["ud10"] = "P02"
            df_project_new["ud11"] = 'N'
            df_project_new["ud12"] = "SP01"
            df_project_new["isActive"] = df_project_new["project_status"].apply(lambda x: "Y" if x == "启用" else "N")
            df_project_new = df_project_new.drop_duplicates(["name"], keep="first")
            # 插入新增项目
            rsg_new = self.dim.load_dataframe(df_project_new, "incr_replace")
            print("插入新项目：", list(df_project_new["name"]))

            # 插入水厂分摊比例表
            df_work = df_project_new[["name", "parent_name"]]
            # # df_work = df_project_existing[["language_zh-cn", "parent_name"]]
            df_work = df_work.rename(columns={
                "parent_name": "water_works",
                "name": "Operating_the_project"
            })
            df_work["water_works"] = df_work["water_works"].str.replace("^PS", "XN", regex=True)
            df_work["department"] = "Operation"
            df_work["Year"] = self.year
            df_work["Version"] = "Y1"
            # print('df_work',df_work)
            self.df_wpa.insert_df(df_work, ['water_works', 'department'])
            print('新项目插入水厂分摊比例', df_work)
            return list(df_project_new["name"])

    def entity_mapping(self):
        entity_mapping = self.df_entity_v3.query("name.str.startswith('XN')", engine='python')
        entity_mapping = entity_mapping.rename(columns={
            "parent_name": "Entity_code",
            "name": "Entity"
        })
        # entity_mapping = entity_mapping.drop(columns=['expectedName'])
        entity_mapping = entity_mapping.drop_duplicates(["Entity"], keep="first")
        # print(entity_mapping)
        print('映射表长度', len(entity_mapping))
        self.df_entity_mapping.insert_df(dataframe=entity_mapping, updatecol=self.col_entity_mapping)


def main(p1, p2):
    # 小业态应用
    p1['app'] = 'eemapg012'
    OPTION.api.header = p1
    # 获取小业态项目中间表全量数据
    XYT_dt = DataTableMySQL('Project_Basic_Information')
    cols = ['manage_region_cd', 'manage_region_name', 'manage_area_cd', 'manage_area_name', 'project_corp_cd',
            'project_corp_name', 'manage_org_cd', 'manage_org_name', 'project_cd', 'project_name', 'format_cd',
            'format', 'inv_pattern', 'Project_Type_code', 'Project_Type_name', 'pro_characteristics', 'inc_ext_idtf']
    XYT_df = XYT_dt.select(columns=cols)
    XYT_df = XYT_df.rename(columns={
        'manage_region_cd': 'region_code',
        'manage_region_name': 'region_name',
        'manage_area_cd': 'area_code',
        'manage_area_name': 'area_name',
        'project_corp_cd': 'Entity_org',
        'project_corp_name': 'Entity_org_name',
        'manage_org_cd': 'Entity_manag',
        'manage_org_name': 'Entity_manag_name',
        'project_cd': 'project_code',
        'project_name': 'project_name',
        'format_cd': 'Format',
        'format': 'Format_name',
        'inv_pattern': 'Pattern',
        'Project_Type_code': 'Project_Type',
        'Project_Type_name': 'Project_Type_name',
        'pro_characteristics': 'PM_Chars',
        'inc_ext_idtf': 'Consv_Incrmt',
    })
    XYT_df['PM_Chars'] = XYT_df['PM_Chars'].fillna('NoPM_Chars')
    XYT_df['Pattern'] = XYT_df['Pattern'].fillna('NoPattern')
    XYT_df['Consv_Incrmt'] = XYT_df['Consv_Incrmt'].fillna('NoConsv_Incrmt')

    # 业务预算应用
    p1['app'] = 'eemapg011'
    OPTION.api.header = p1
    # 将小业态项目数据写入业务预算
    YWYS_dt = DataTableMySQL('Entity_ZT_NEW')
    cols = ['region_code', 'region_name', 'area_code', 'area_name', 'company_code', 'company_name', 'org_code',
            'org_name', 'project_code', 'project_name', 'M_BIZ_TYPE_CODE', 'M_BIZ_TYPE_NAME', 'invest_model_name',
            'project_category_lv3_cd', 'project_category_lv3_name', 'prod_serv_type_cd', 'inc_ext_idtf']
    YWYS_df = YWYS_dt.select(columns=cols)
    YWYS_df = YWYS_df.rename(columns={
        # 'manage_region_cd' : 'region_code',
        # 'manage_region_name' : 'region_name',
        # 'manage_area_cd' : 'area_code',
        # 'manage_area_name' : 'area_name',
        'company_code': 'Entity_org',
        'company_name': 'Entity_org_name',
        'org_code': 'Entity_manag',
        'org_name': 'Entity_manag_name',
        'project_code': 'project_code',
        'project_name': 'project_name',
        'M_BIZ_TYPE_CODE': 'Format',
        'M_BIZ_TYPE_NAME': 'Format_name',
        'invest_model_name': 'Pattern',
        # 'project_category_lv3_cd' : 'Project_Type',
        'project_category_lv3_name': 'Project_Type_name',
        'inc_ext_idtf': 'Consv_Incrmt',
    })

    YWYS_df['Project_Type'] = np.where(YWYS_df['project_category_lv3_cd'] == '010201',
                                       'PT' + YWYS_df['prod_serv_type_cd'],
                                       'PT' + YWYS_df['project_category_lv3_cd'])

    YWYS_df['PM_Chars'] = 'PM01'
    YWYS_df['Pattern'] = YWYS_df['Pattern'].fillna('NoPattern')
    YWYS_df['Consv_Incrmt'] = YWYS_df['Consv_Incrmt'].fillna('NoConsv_Incrmt')
    YWYS_df['Format'] = 'F' + YWYS_df['Format']

    entity_df = pd.concat([XYT_df, YWYS_df])
    entity_df.drop('prod_serv_type_cd', axis=1, inplace=True)

    entity_dt = DataTableMySQL('entity_info')
    updatecol = list(set(entity_df.columns) - {"project_code"})
    entity_dt.insert_df(entity_df, updatecol)

    entity_df = entity_df[['project_code', 'Format', 'Pattern', 'PM_Chars', 'Project_Type', 'Consv_Incrmt']]

    # 公共层应用
    p1['app'] = 'eemapg007'
    OPTION.api.header = p1
    YS_dt = DataTableClickHouse('bewg_budget_data')
    cols = ['Project_code', 'Project_name', 'Account_code', 'Account_name', 'Year_Code', 'Period_Code', 'Tax_code',
            'figure', 'Source']
    where = "Project_code like 'Y%'"
    YS_df = YS_dt.select(columns=cols, where=where)

    # 拆分XYT和YWYS数据
    XYT_df = YS_df[YS_df['Source'] == 'XYT']

    YWYS_df = YS_df[YS_df['Source'] == 'YWYS']

    # 预算科目映射表
    account_map_dt = DataTableMySQL('budget_account_mapping')
    cols = ['Account_cd_lanke','Account_cd_wushui','Account_cd_xiaoyetai']


    account_map_df = account_map_dt.select(columns=cols).rename(columns={
        "Account_cd_lanke": "Account_GB",
        "Account_cd_wushui":"Account",
        "Account_cd_xiaoyetai":"Account_XYT"})

    XYT_df = XYT_df.merge(account_map_df[['Account_GB','Account_XYT']], how='left', left_on='Account_code', right_on='Account_XYT').drop(columns=['Account_code'])
    XYT_df['Account'] = 'Noaccount'
    YWYS_df = YWYS_df.merge(account_map_df[['Account','Account_GB']], how='left', left_on='Account_code', right_on='Account').drop(columns=['Account_code'])
    YWYS_df['Account_XYT'] = 'Noaccount'
    # 根据年份设置Scenario
    XYT_df['Scenario'] = np.where(XYT_df['Year_Code'] == '2025', 'Forecast', 'Budget')
    YWYS_df['Scenario'] = np.where(YWYS_df['Year_Code'] == '2025', 'Forecast', 'Budget')

    YS_df = pd.concat([XYT_df, YWYS_df])



    df = YS_df.merge(entity_df, how='left', left_on='Project_code', right_on='project_code')
    df = df.dropna(subset=['project_code'])
    df.drop(['Source','project_code','Source','Account_name','Project_name'], axis=1, inplace=True)
    df['Department'] = 'Operation'
    df['Measure'] = 'Expenses'
    df['Version'] = 'Y1'
    df['Misc1'] = 'Nomisc1'
    df['Misc2'] = 'Nomisc2'
    df['Misc3'] = 'Nomisc3'
    # df['Format'] = 'F' + df['Format']
    # df['Project_Type'] = 'PT' + df['Project_Type']

    df = df.rename(columns={
        "Period_Code":"Period",
        "figure":"data",
        "Project_code":"Entity_org",
        "Year_Code":"Year",
        "Tax_code":"Tax",
    })
    df['Entity_manag'] = df['Entity_org']

    # 写入业务预算分析模型
    p1['app'] = 'eemapg011'
    OPTION.api.header = p1
    cube = FinancialCube('analytical_model')
    cube.save(df)





if __name__ == "__main__":
    from budget.__debug import para1, para2

    # print('1',para1)
    main(para1, para2)
