"""
更新运营项目的维度
主要逻辑：
    从Entity_ZT_NEW表提取数据，更新Entity维度：大区、区域、项目
    包含已在维度表中的记录（更新）和不在维度表中的记录（新增）
    在有新项目时，更新审批记录表
    更新全周期模型
作者：cjl
日期：2025-08-01
"""

import pandas as pd
from typing import List, Optional
from deepfos.element.dimension import Dimension
from deepfos.element.datatable import DataTableMySQL
from deepfos.element.variable import Variable

class UpdateOperationDimension:
    def __init__(self):
        """初始化，连接数据库并加载初始数据"""
        # 获取变量年
        self.year = Variable('Variable').get_value('Year')

        # 获取Entity维度数据
        self.dim = Dimension("Entity_test")
        self.df_entity_v3 = pd.DataFrame(
            self.dim.query(
                expression="IDescendant(D000001,0)",
                fields=["name", "parent_name"],
                as_model=False
            )
        ).drop(columns=["id", "expectedName"], errors='ignore')

        # 获取Entity_ZT_NEW数据
        self.df_entity_sj = DataTableMySQL("Entity_ZT_NEW")
        # where = (
        #     (self.df_entity_sj.table.manage_region_cd.notnull()) &
        #     (self.df_entity_sj.table.manage_area_cd.notnull())
        # )
        self.df_entity = pd.DataFrame(self.df_entity_sj.select_raw())
        # 在df_source上应用过滤条件
        self.df_source = self.df_entity[
            (self.df_entity["manage_region_cd"].notnull()) &
            (self.df_entity["manage_area_cd"].notnull())
        ].copy() if not self.df_entity.empty else pd.DataFrame()

        # 审批记录表
        self.approve_tb = DataTableMySQL("approval_report",path='/Process/Full_Process/')

        # 全周期主模型
        self.full_model = DataTableMySQL("Basic_Data_Full")

    def update_entity_v3(self, p1: dict, p2: dict) -> None:
        """主方法，更新所有层级的维度"""
        if self.df_source.empty:
            return
        large_new = self.update_large_area()
        area_new = self.update_area()
        project_new = self.update_project()
        print('插入的新组织有：',large_new,area_new,project_new)

        return large_new, area_new, project_new


    def update_large_area(self) -> None:
        """更新大区维度"""
        df_large_area = self.df_source[["manage_region_name", "manage_region_cd"]].drop_duplicates()
        df_large_area_existing = df_large_area[df_large_area["manage_region_cd"].isin(self.df_entity_v3["name"])]
        df_large_area_new = df_large_area[~df_large_area["manage_region_cd"].isin(self.df_entity_v3["name"])]

        # 更新已有大区
        if not df_large_area_existing.empty:
            df_large_area_existing = df_large_area_existing.rename(columns={
                "manage_region_cd": "name",
                "manage_region_name": "language_zh-cn"
            })
            df_large_area_existing["language_en"] = df_large_area_existing["language_zh-cn"]
            df_large_area_existing["parent_name"] = "D000001"
            df_large_area_existing["ud6"] = "大区"
            df_large_area_existing["ud7"] = "集团"
            df_large_area_existing["ud8"] = ""
            df_large_area_existing["ud11"] = "Y"
            df_large_area_existing["isActive"] = "Y"
            # self.dim.load_dataframe(df_large_area_existing, "incr_replace")

        # 插入新大区
        if not df_large_area_new.empty:
            df_large_area_new = df_large_area_new.rename(columns={
                "manage_region_cd": "name",
                "manage_region_name": "language_zh-cn"
            })
            df_large_area_new["language_en"] = df_large_area_new["language_zh-cn"]
            df_large_area_new["parent_name"] = "D000001"
            df_large_area_new["ud1"] = ""
            df_large_area_new["ud2"] = ""
            df_large_area_new["ud6"] = "大区"
            df_large_area_new["ud7"] = "集团"
            df_large_area_new["ud8"] = ""
            df_large_area_new["ud11"] = "Y"
            df_large_area_new["isActive"] = "Y"
            # df_large_area_new["localCurrency"] = ""
            # df_large_area_new["sharedMember"] = "N"
            # df_large_area_new["aggweight"] = 1
            # print(df_large_area_new)
            self.dim.load_dataframe(df_large_area_new, "incr_replace")
            return list(df_large_area_new["name"])

    def update_area(self) -> None:
        """更新区域维度"""
        df_area = self.df_source[["manage_area_name", "manage_area_cd", "manage_region_cd", "manage_region_name"]].drop_duplicates()
        df_area_existing = df_area[df_area["manage_area_cd"].isin(self.df_entity_v3["name"])]
        df_area_new = df_area[~df_area["manage_area_cd"].isin(self.df_entity_v3["name"])]

        # 更新已有区域
        if not df_area_existing.empty:
            df_area_existing = df_area_existing.rename(columns={
                "manage_area_cd": "name",
                "manage_area_name": "language_zh-cn",
                "manage_region_cd": "parent_name"
            })
            df_area_existing["language_en"] = df_area_existing["language_zh-cn"]
            df_area_existing["ud6"] = "区域公司"
            df_area_existing["ud7"] = df_area_existing["manage_region_name"]
            df_area_existing["ud8"] = ""
            df_area_existing["ud11"] = "Y"
            df_area_existing["isActive"] = "Y"
            # df_area_existing["sharedMember"] = "N"
            # df_area_existing["aggweight"] = 1
            # self.dim.load_dataframe(df_area_existing, "incr_replace")

        # 插入新区域
        if not df_area_new.empty:
            df_area_new = df_area_new.rename(columns={
                "manage_area_cd": "name",
                "manage_area_name": "language_zh-cn",
                "manage_region_cd": "parent_name"
            })
            df_area_new["language_en"] = df_area_new["language_zh-cn"]
            df_area_new["ud1"] = ""
            df_area_new["ud2"] = ""
            df_area_new["ud6"] = "区域公司"
            df_area_new["ud7"] = df_area_new["manage_region_name"]
            df_area_new["ud8"] = ""
            df_area_new["ud11"] = "Y"
            df_area_new["isActive"] = "Y"
            # df_area_new["sharedMember"] = "N"
            # df_area_new["aggweight"] = 1
            # df_area_new["localCurrency"] = ""
            self.dim.load_dataframe(df_area_new, "incr_replace")
            return list(df_area_new["name"])

    def update_project(self) -> None:
        """更新项目维度"""
        df_project = self.df_source[["project_code", "project_name", "manage_area_cd", "manage_region_name",
                                    "manage_area_name", "invest_model_cd", "project_category_lv3_cd",
                                    "project_phase_name", "est_com_oper_date", "biz_type_lv3_cd",
                                    "prod_serv_type_cd", "act_com_oper_date"]].drop_duplicates()
        df_project_existing = df_project[df_project["project_code"].isin(self.df_entity_v3["name"])]
        df_project_new = df_project[~df_project["project_code"].isin(self.df_entity_v3["name"])]

        # 更新已有项目
        if not df_project_existing.empty:
            df_project_existing = df_project_existing.rename(columns={
                "project_code": "name",
                "project_name": "language_zh-cn",
                "manage_area_cd": "parent_name"
            })
            df_project_existing["language_en"] = df_project_existing["language_zh-cn"]
            df_project_existing["ud6"] = "项目"
            df_project_existing["ud7"] = "XM"
            df_project_existing["ud9"] = df_project_existing["project_category_lv3_cd"].fillna("")
            df_project_existing["ud10"] = df_project_existing["project_phase_name"].fillna("")
            df_project_existing["ud12"] = df_project_existing["est_com_oper_date"].fillna("")
            df_project_existing["ud13"] = df_project_existing["biz_type_lv3_cd"].fillna("")
            df_project_existing["ud14"] = df_project_existing["prod_serv_type_cd"].fillna("")
            df_project_existing["ud15"] = df_project_existing["invest_model_cd"].fillna("")
            df_project_existing["ud16"] = df_project_existing["act_com_oper_date"]
            df_project_existing["isActive"] = "Y"
            # self.dim.load_dataframe(df_project_existing, "incr_replace")

        # 插入新项目
        if not df_project_new.empty:
            df_project_new = df_project_new.rename(columns={
                "project_code": "name",
                "project_name": "language_zh-cn",
                "manage_area_cd": "parent_name"
            })
            df_project_new["language_en"] = df_project_new["language_zh-cn"]
            df_project_new["ud1"] = ""
            df_project_new["ud2"] = ""
            df_project_new["ud6"] = "项目"
            df_project_new["ud7"] = "XM"
            df_project_new["ud9"] = df_project_new["project_category_lv3_cd"].fillna("")
            df_project_new["ud10"] = df_project_new["project_phase_name"].fillna("")
            df_project_new["ud12"] = df_project_new["est_com_oper_date"].fillna("")
            df_project_new["ud13"] = df_project_new["biz_type_lv3_cd"].fillna("")
            df_project_new["ud14"] = df_project_new["prod_serv_type_cd"].fillna("")
            df_project_new["ud15"] = df_project_new["invest_model_cd"].fillna("")
            df_project_new["ud16"] = df_project_new["act_com_oper_date"]
            df_project_new["ud11"] = "Y"
            df_project_new["isActive"] = "Y"
            # df_project_new["sharedMember"] = "N"
            # df_project_new["aggweight"] = 1
            # df_project_new["localCurrency"] = ""
            self.dim.load_dataframe(df_project_new, "incr_replace")
            return list(df_project_new["name"])


    # 更新审批记录表函数
    def update_approval_report(self):
        # 如果有新增的项目，需要在审批记录表中新增
        if not self.df_source.empty:
            # df_source = self.df_source[self.df_source['project_code'].isin(project_new)]
            df_source = self.df_source[['project_code', 'manage_region_cd', 'manage_area_cd']]
            # print("新增项目信息：", project_new)

            # 生成分组
            partition_ids = pd.DataFrame({"partition_id": ['null', "QY", "DQ", "JT"]})
            # 生成笛卡尔积
            df_source = df_source.merge(partition_ids, how="cross")
            df_source['Year'] = self.year
            df_source['Scenario'] = 'Year'
            # df_source['result_status'] = '1'

            # 审批记录表字段映射
            df_source = df_source.rename(columns={
                'project_code': 'Entity',
                'manage_region_cd': 'Region',
                'manage_area_cd': 'Region_Company',
            })
            # print(df_source)
            self.approve_tb.insert_df(df_source, ['Region', 'Region_Company'])


    # 更新Basic_Data_Full主模型函数
    def update_full_model(self,p1,p2):
        # df_source = self.df_entity.copy()
        df_source = self.df_entity[[
            "project_code", "project_name", "waterworks_province", "waterworks_city",
            "manage_org_cd", "manage_org_name", "manage_area_cd", "manage_region_cd",
            "project_corp_cd", "project_corp_name", "project_type", "biz_type_lv1_cd",
            "biz_type_lv2_cd", "biz_type_lv3_cd", "invest_model_cd", "project_start_dt", "project_end_dt",
            "project_category_lv1_name", "project_category_lv2_name", "project_category_lv3_name",
            "project_phase_cd", "project_data_status", "und_project_category", "und_project_cd",
            "und_project_name", "com_oper_flag", "est_com_oper_date", "act_com_oper_date",
            "prod_serv_type_cd", "prod_serv_type_name", "is_nt_rel_main_biz", "rel_project_cd",
            "rel_project_name", "acq_mode_name", "project_inv_ttl", "project_inv_ctl",
            "const_type", "rev_size", "pd_size_plt", "pd_size_net_km", "const_size_plt",
            "const_size_net_km", "con_per", "agr_wat_pr", "min_wat_vol", "tirr", "eirr",
            "op_vol_day", "ann_cont_rev", "op_net_km", "hand_over_date", "cur_use_econ"
        ]].drop_duplicates()
        df_source = df_source.rename(columns={
            "project_code": "Entity_Number",
            "project_name": "Entity_Name",
            "manage_org_cd": "PK_MANAG_ORG",
            "waterworks_province": "Province",
            "waterworks_city": "City",
            "manage_org_name": "ORG_NAME",
            "manage_area_cd": "Regional_Company",
            "manage_region_cd": "Region",
            "project_corp_cd": "LEG_ORG_CODE",
            "project_corp_name": "LEG_ORG_NAME",
            "project_type": "PROJ_TYPE",
            "biz_type_lv1_cd": "Format_1",
            "biz_type_lv2_cd": "Format_2",
            "biz_type_lv3_cd": "M_BIZ_TYPE_CODE",
            "invest_model_cd": "Investment",
            "project_start_dt": "PRJ_START_DATE",
            "project_end_dt": "PRJ_END_DATE",
            "project_category_lv1_name": "PRJ_L1_NAME",
            "project_category_lv2_name": "PRJ_L2_NAME",
            "project_category_lv3_name": "PRJ_L3_NAME",
            "project_phase_cd": "Project",
            "project_data_status": "PRJ_DATA_STAT_NAME",
            "und_project_category": "UND_PRJ_CAT_NAME",
            "und_project_cd": "UND_PRJ_CODE",
            "und_project_name": "UND_PRJ_NAME",
            "com_oper_flag": "IS_NT_COM_OPER",
            "est_com_oper_date": "EST_COM_OPER_DATE",
            "act_com_oper_date": "ACT_COM_OPER_DATE",
            "prod_serv_type_cd": "PROD_SERV_2ND_CODE",
            "prod_serv_type_name": "PROD_SERV_2ND_NAME",
            "is_nt_rel_main_biz": "IS_NT_REL_MAIN_BUS",
            "rel_project_cd": "REL_PRJ_CODE",
            "rel_project_name": "REL_PRJ_NAME",
            "acq_mode_name": "ACQ_MODE_NAME",
            "project_inv_ttl": "PRJ_INV_TTL",
            "project_inv_ctl": "PRJ_INV_CTL",
            "const_type": "CONST_TYPE",
            "rev_size": "REV_SIZE",
            "pd_size_plt": "Scale_SJ",
            "pd_size_net_km": "PD_SIZE_NET_KM",
            "const_size_plt": "CONST_SIZE_PLT",
            "const_size_net_km": "CONST_SIZE_NET_KM",
            "con_per": "CON_PER",
            "agr_wat_pr": "AGR_WAT_PR",
            "min_wat_vol": "MIN_WAT_VOL",
            "tirr": "TIRR",
            "eirr": "EIRR",
            "op_vol_day": "Scale_SJCL",
            "ann_cont_rev": "ANN_CONT_REV",
            "op_net_km": "Scale_GW",
            "hand_over_date": "HAND_OVER_DATE",
            "cur_use_econ": "CUR_USE_ECON"
        })
        df_source['Year'] = self.year
        df_source['Version'] = 'WorkVersion'
        # df_source['Approve_Status'] = '1'
        df_source['Scenario'] = 'Year'

        # 生成场景，一个场景生成一行
        # Scenarios = pd.DataFrame({'Scenario': ['Year','M4','M5','M6','M7','M8','M9','M10','M11','M12']})
        # df_source = df_source.merge(Scenarios, how="cross")

        # print(df_source)

        # float_cols = df_source.select_dtypes(include=['float']).columns
        updatecol = list(set(df_source.columns) - {"Year","Entity_Number","Version"})
        self.full_model.insert_df(df_source, updatecol,chunksize=10000)

def main(p1: dict, p2: dict) -> None:
    # print(pd.__version__)
    # 更新组织维度
    updater = UpdateOperationDimension()
    # large_new, area_new, project_new = updater.update_entity_v3(p1, p2)

    # 更新审批记录表
    updater.update_approval_report()

    # 更新Basic_Data_Full主模型
    updater.update_full_model(p1,p2)
if __name__ == "__main__":
    from business._debug import para1, para2
    main(para1, para2)