"""
更新小业态的维度
主要逻辑：
    从Entity_ZT_NEW表提取数据，更新Entity维度：大区、区域、项目
    # 包含已在维度表中的记录（更新）和不在维度表中的记录（新增）
    # 在有新项目时，更新审批记录表
    更新全周期模型
作者：cjl
日期：2025-08-01
"""

import pandas as pd
from typing import List, Optional
from deepfos.element.dimension import Dimension
from deepfos.element.datatable import DataTableMySQL
from deepfos.element.variable import Variable
from .add_entity_to_flow_inr import main as add

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)

class UpdateOperationDimension:
    def __init__(self):
        """初始化，连接数据库并加载初始数据"""
        # 获取变量年
        self.year = Variable('Variable').get_value('BudYear')

        # 获取Entity维度数据
        self.dim = Dimension("Entity")
        self.df_entity_v3 = pd.DataFrame(
            self.dim.query(
                expression="IDescendant(1,0)",
                fields=["name", "parent_name"],
                as_model=False
            )
        ).drop(columns=["id", "expectedName"], errors='ignore')

        # 获取Entity_ZT_NEW数据
        self.df_entity_sj = DataTableMySQL("Project_Basic_Information")
        # where = (
        #     (self.df_entity_sj.table.manage_region_cd.notnull()) &
        #     (self.df_entity_sj.table.manage_area_cd.notnull())
        # )
        self.df_entity = pd.DataFrame(self.df_entity_sj.select_raw())
        # 在df_source上应用过滤条件
        df_source = self.df_entity[
            (self.df_entity["manage_region_cd"].notnull()) &
            (self.df_entity["manage_area_cd"].notnull()) &
            (self.df_entity["project_corp_cd"].notnull())
        ].copy() if not self.df_entity.empty else pd.DataFrame()

        # 先找到目标行
        mask = df_source.groupby("project_corp_cd")["manage_area_cd"].transform("nunique") > 1
        # 同一法人公司所属区域不同的
        df = df_source[mask]  # 这些是要提取出来的行
        print('同一法人公司所属区域不同的',df)

        self.df_source = df_source[~mask]  # 这些是剔除掉之后的剩余行
        # print(self.df_source)

        # # 审批记录表
        # self.approve_tb = DataTableMySQL("approval_report")
        #
        # # 全周期主模型
        # self.full_model = DataTableMySQL("Basic_Data_Full")



    def update_entity(self, p1: dict, p2: dict) -> None:
        """主方法，更新所有层级的维度"""
        if self.df_source.empty:
            return
        large_new = self.update_large_area()
        area_new = self.update_area()
        org_new = self.update_org()
        project_new = self.update_project()
        # print('插入的新组织有：',large_new,area_new,org_new,project_new)

        combined_updates = (large_new or []) + (area_new or []) + (org_new or []) +  (project_new or [])

        if combined_updates:
            print("所有更新的维度列表：", combined_updates)
            # combined_updates = ['Y3220210083']
            add(p1, p2, combined_updates)

        return large_new, area_new, org_new, project_new


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
            df_large_area_existing["parent_name"] = "1"
            df_large_area_existing["ud1"] = "Org01"
            df_large_area_existing["isActive"] = "Y"
            self.dim.load_dataframe(df_large_area_existing, "incr_replace")

        # 插入新大区
        if not df_large_area_new.empty:
            df_large_area_new = df_large_area_new.rename(columns={
                "manage_region_cd": "name",
                "manage_region_name": "language_zh-cn"
            })
            df_large_area_new["language_en"] = df_large_area_new["language_zh-cn"]
            df_large_area_new["parent_name"] = "1"
            df_large_area_new["ud1"] = "Org01"
            df_large_area_new["isActive"] = "Y"
            self.dim.load_dataframe(df_large_area_new, "incr_replace")
            return list(df_large_area_new["name"])

    def update_area(self) -> None:
        """更新区域维度"""
        df_area = self.df_source[["manage_area_name", "manage_area_cd", "manage_region_cd","manage_region_name"]].drop_duplicates()
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
            df_area_existing["ud1"] = "Org02"
            df_area_existing["isActive"] = "Y"
            self.dim.load_dataframe(df_area_existing, "incr_replace")

        # 插入新区域
        if not df_area_new.empty:
            df_area_new = df_area_new.rename(columns={
                "manage_area_cd": "name",
                "manage_area_name": "language_zh-cn",
                "manage_region_cd": "parent_name",
                "manage_region_name": "ud7"
            })
            df_area_new["language_en"] = df_area_new["language_zh-cn"]
            df_area_new["ud1"] = "Org02"
            df_area_new["ud8"] = df_area_new["language_zh-cn"]

            df_area_new["isActive"] = "Y"
            self.dim.load_dataframe(df_area_new, "incr_replace")
            return list(df_area_new["name"])

    def update_org(self) -> None:
        """更新区域维度"""
        df_project_corp = self.df_source[["project_corp_cd","project_corp_name","manage_area_cd","manage_area_name","manage_region_name"]].drop_duplicates()
        df_org_existing = df_project_corp[df_project_corp["project_corp_cd"].isin(self.df_entity_v3["name"])]
        df_org_new = df_project_corp[~df_project_corp["project_corp_cd"].isin(self.df_entity_v3["name"])]

        # 更新已有法人公司
        if not df_org_existing.empty:
            df_org_existing = df_org_existing.rename(columns={
                "project_corp_cd": "name",
                "project_corp_name": "language_zh-cn",
                "manage_area_cd": "parent_name"
            })
            df_org_existing["language_en"] = df_org_existing["language_zh-cn"]
            df_org_existing["ud1"] = "Org03"
            df_org_existing["isActive"] = "Y"
            self.dim.load_dataframe(df_org_existing, "incr_replace")

        # 插入新法人公司
        if not df_org_new.empty:
            df_org_new = df_org_new.rename(columns={
                "project_corp_cd": "name",
                "project_corp_name": "language_zh-cn",
                "manage_area_cd": "parent_name",
                "manage_area_name": "ud8",
                "manage_region_name": "ud7"
            })
            df_org_new["language_en"] = df_org_new["language_zh-cn"]
            df_org_new["ud1"] = "Org03"
            df_org_new["isActive"] = "Y"
            self.dim.load_dataframe(df_org_new, "incr_replace")
            return list(df_org_new["name"])

    def update_project(self) -> None:
        """更新项目维度"""
        df_project = self.df_source[["project_cd", "project_name", "project_corp_cd","format_cd","Project_Type_code","manage_area_name","manage_region_name"]].drop_duplicates()
        df_project_existing = df_project[df_project["project_cd"].isin(self.df_entity_v3["name"])]
        df_project_new = df_project[~df_project["project_cd"].isin(self.df_entity_v3["name"])]

        # 更新已有项目
        if not df_project_existing.empty:
            df_project_existing = df_project_existing.rename(columns={
                "project_cd": "name",
                "project_name": "language_zh-cn",
                "project_corp_cd": "parent_name"
            })
            df_project_existing["language_en"] = df_project_existing["language_zh-cn"]
            df_project_existing["ud1"] = "Org04"
            df_project_existing["isActive"] = "Y"
            self.dim.load_dataframe(df_project_existing, "incr_replace")

        # 插入新项目
        if not df_project_new.empty:
            df_project_new = df_project_new.rename(columns={
                "project_cd": "name",
                "project_name": "language_zh-cn",
                "project_corp_cd": "parent_name",
                "format_cd": "ud4",
                "Project_Type_code": "ud5",
                "manage_area_name": "ud8",
                "manage_region_name": "ud7"
            })
            df_project_new["language_en"] = df_project_new["language_zh-cn"]
            df_project_new["ud1"] = "Org04"
            df_project_new["ud2"] = 'Operation'
            df_project_new["ud3"] = 'Invariant'

            df_project_new["isActive"] = "Y"

            print(df_project_new)
            self.dim.load_dataframe(df_project_new, "incr_replace")
            return list(df_project_new["name"])


    # 更新审批记录表函数
    def update_approval_report(self, project_new):
        # 如果有新增的项目，需要在审批记录表中新增
        if project_new:
            df_source = self.df_source[self.df_source['project_code'].isin(project_new)]
            df_source = df_source[['project_code', 'manage_region_cd', 'manage_area_cd']]
            # print("新增项目信息：", project_new)

            # 生成分组
            partition_ids = pd.DataFrame({"partition_id": ['null', "QY", "DQ", "JT"]})
            # 生成笛卡尔积
            df_source = df_source.merge(partition_ids, how="cross")
            df_source['Year'] = self.year
            df_source['Scenario'] = 'Year'
            df_source['result_status'] = '1'

            # 审批记录表字段映射
            df_source = df_source.rename(columns={
                'project_code': 'Entity',
                'manage_region_cd': 'Region',
                'manage_area_cd': 'Region_Company',
            })
            # print(df_source)
            self.approve_tb.insert_df(df_source, ['Region', 'Region_Company', 'result_status'])


    # 更新Basic_Data_Full主模型函数
    def update_full_model(self,p1,p2):
        # df_source = self.df_entity.copy()
        df_source = self.df_entity[[
            "project_code", "project_name", "waterworks_province", "waterworks_city",
            "manage_org_cd", "manage_org_name", "manage_area_cd", "manage_region_cd",
            "project_corp_cd", "project_corp_name", "project_type", "biz_type_lv1_cd",
            "biz_type_lv2_cd", "invest_model_cd", "project_start_dt", "project_end_dt",
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
        df_source['Approve_Status'] = '1'



        print(df_source)
        updatecol = list(set(df_source.columns) - {"Year","Entity_Number","Version"})
        self.full_model.insert_df(df_source, updatecol)



# 从项目中间表写入项目基础信息表
def update_basic_info():
    # 获取变量年
    year = Variable('Variable').get_value('BudYear')

    # # 获取业态维度数据
    # dim_format = Dimension("Format")
    #
    # df_format = pd.DataFrame(
    #     dim_format.query(
    #         expression="IDescendant(Format_all,0)",
    #         fields=["name","description_zh_cn"],
    #         as_model=False
    #     )
    # ).drop(columns=["id", "expectedName"], errors='ignore')
    # print(df_format)


    # 获取投资模式维度数据
    dim_Investment_Model = Dimension("Investment_Model")
    df_Investment_Model = pd.DataFrame(
        dim_Investment_Model.query(
            expression="IDescendant(M,0)",
            fields=["name","description_zh_cn"],
            as_model=False
        )
    ).drop(columns=["id", "expectedName"], errors='ignore')
    print(df_Investment_Model)
    df_Investment_Model = df_Investment_Model.rename(columns={
        'name': 'inv_pattern_cd',
        'description_zh_cn': 'inv_pattern'
    })

    # 获取中间表数据
    Project_Master_Data = DataTableMySQL("Project_Master_Data")
    columns = [
        'manage_region_cd',
        'manage_region_name',
        'manage_area_cd',
        'manage_area_name',
        'project_corp_cd',
        'project_corp_name',
        'manage_org_cd',
        'manage_org_name',
        'project_cd',
        'project_name',
        'biz_type_lv3_cd',
        'biz_type_lv3_name',
        'invest_model_name',
        'project_category_lv3_cd',
        'prod_serv_type_cd',
        'prod_serv_type_name'
    ]
    df_Project = pd.DataFrame(Project_Master_Data.select(columns=columns))
    print(df_Project)


    # 初始化目标表DataFrame
    df_target = df_Project.copy()


    # 1. 处理业态编码和名称
    # 直接使用中间表的biz_type_lv3_cd加前缀'F'作为format_cd
    df_target['format_cd'] = 'F' + df_target['biz_type_lv3_cd']
    df_target['format'] = df_target['biz_type_lv3_name']


    # 2. 处理投资模式编码和名称
    df_target = df_target.merge(
        df_Investment_Model[['inv_pattern_cd', 'inv_pattern']],
        how='left',
        left_on='invest_model_name',
        right_on='inv_pattern'
    )
    df_target['inv_pattern'] = df_target['inv_pattern'].fillna(df_target['invest_model_name'])
    df_target['inv_pattern_cd'] = df_target['inv_pattern_cd'].fillna(df_target['invest_model_name'])

    # 3. 添加年份
    df_target['year'] = year

    # 4. 处理项目类型编码和名称
    # 项目类型编码逻辑：
    # - 如果project_category_lv3_cd == '010103'，则Project_Type_name = '运营项目'
    # - 其他情况使用prod_serv_type_cd加前缀'PT'，名称使用biz_type_lv3_name
    df_target['Project_Type_code'] = df_target.apply(
        lambda row: 'PT' + row['prod_serv_type_cd'] if row['project_category_lv3_cd'] != '010103' else 'PT' + row['project_category_lv3_cd'],
        axis=1
    )
    df_target['Project_Type_name'] = df_target.apply(
        lambda row: '运营项目' if row['project_category_lv3_cd'] == '010103' else row['prod_serv_type_name'],
        axis=1
    )

    # 选择目标表需要的列
    target_columns = [
        'manage_region_cd',
        'manage_region_name',
        'manage_area_cd',
        'manage_area_name',
        'project_corp_cd',
        'project_corp_name',
        'manage_org_cd',
        'manage_org_name',
        'project_cd',
        'project_name',
        'format_cd',
        'format',
        'inv_pattern_cd',
        'inv_pattern',
        'year',
        'Project_Type_code',
        'Project_Type_name'
    ]
    df_target = df_target[target_columns]

    # 写入目标表（假设目标表为Target_Table）
    basic_info_table = DataTableMySQL("Project_Basic_Information")
    basic_info_table.insert_df(df_target,updatecol=[
        'manage_region_cd',
        'manage_region_name',
        'manage_area_cd',
        'manage_area_name',
        'project_corp_cd',
        'project_corp_name',
        'manage_org_cd',
        'manage_org_name',
        'project_name',
        'format_cd',
        'format',
        'inv_pattern_cd',
        'inv_pattern',
        'Project_Type_code',
        'Project_Type_name'
    ])
    print(df_target)
def main(p1: dict, p2: dict) -> None:
    # # 从项目中间表写入项目基础信息表
    update_Basic_Information = update_basic_info()

    # 更新组织维度
    update_Dimension = UpdateOperationDimension()
    large_new, area_new, project_corp_new, project_new = update_Dimension.update_entity(p1, p2)

    # # 更新审批记录表
    # updater.update_approval_report(project_new)
    #
    # # 更新Basic_Data_Full主模型
    # updater.update_full_model(p1,p2)
if __name__ == "__main__":
    from BIZ._debug import para1, para2
    main(para1, para2)