"""
added by cjl
added in 20241011
added for 预算填报信息写进Equipment_Act表，为下发做准备
主要逻辑：
    根据预算信息填报的Equipment_profile表关联运营项目信息表、
    人员信息表、技改计划表，整合写入Equipment_Act表
剩余问题：无
"""

try:
    from common.__debug import para1, para2
    print(para1)
except ImportError:
    para1 = para2 = {}


from common.commons import *

import pandas as pd
import numpy as np
import datetime
from deepfos.element.datatable import DataTableMySQL
from deepfos.element.dimension import Dimension
from deepfos.element.variable import Variable
from deepfos.api.space import SpaceAPI
from kafka_pro_budget import main as kafka_main

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)


class ActTools:
    def __init__(self, p1,p2):
        # 解析参数 转置df
        print(p2)
        jg_table = DataTableMySQL('equipment_profile_JG')
        jg_columns = ['year', 'entity', 'equipment_location', 'department', 'code', 'name',
                      'location', 'plancode', 'reason', 'type', 'approve_status',
                      '_creator', '_create_time', '_modifier', '_modify_time',
                      'sum_or',  'sum_new',
                      'implementation_or','implementation_new',
                      'plan_or', 'plan_new']

        nj_table = DataTableMySQL('equipment_profile_NJ')
        nj_columns = ['year', 'entity', 'equipment_location', 'department', 'code', 'name',
                      'location', 'plancode', 'reason', 'type',  'approve_status',
                      '_creator', '_create_time', '_modifier', '_modify_time',
                      'sum_or', 'sum_dm', 'sum_dc', 'sum_new',
                      'implementation_dm','implementation_or','implementation_new',
                      'plan_dc', 'plan_or', 'plan_new']

        df_status = pd.DataFrame(p2['form_data'])
        self.df_equipment_profile = pd.DataFrame(columns=nj_columns)
        for _, row in df_status.iterrows():
            entity_id_single = row['entity_id']
            department_id_single = row['department_id']
            self.year_id_single = row['year_id']

            # 获取该子水厂的所有子集
            expression = f'IBase({entity_id_single},0)'
            df_entity_subset = self.fun_query_dimension('Entity', expression, ['name'])
            entity_ids = df_entity_subset['name'].to_list() if not df_entity_subset.empty else [entity_id_single]
            # # 将 entity_ids 转换为逗号分隔的字符串，用于拼接sql
            # entity_ids_str = "','".join(entity_ids)

            temp_data = self.load_profile_data(jg_table,nj_table,jg_columns,nj_columns,entity_ids,department_id_single,self.year_id_single)
            # 拼接数据
            self.df_equipment_profile = pd.concat([self.df_equipment_profile, temp_data], ignore_index=True)

        # 过滤 sum_new, sum_or, sum_dc, sum_dm 全部为空的行
        filter_columns = ['sum_new', 'sum_or', 'sum_dc', 'sum_dm']
        if all(col in self.df_equipment_profile.columns for col in filter_columns):
            self.df_equipment_profile = self.df_equipment_profile[
                ~self.df_equipment_profile[filter_columns].isna().all(axis=1)
            ]


        self.Act_table = DataTableMySQL("Equipment_Act")
        # Act_Data = self.Act_table.select_raw(columns=["Item", "GROUP_AMOUNT_NEW"])
        # print(Act_Data)

        # self.adj = var_.get_variable("Variable", "Scenario")  # Store adj value for later use
        # print(self.adj)
        # self.adj = 'Budget'

        # 获取entity_ZT_new
        self.entity_zt_new_columns = ['project_code', 'project_name']
        self.df_entity_zt_new = self.load_entity_zt_new()
        # print('self.df_entity_zt_new',self.df_entity_zt_new)

        # 获取mdms_employ
        self.mdms_employ_columns = ['NAME', 'USER_CODE', 'ORGNAME', 'ORGID']
        self.df_mdms_employ = self.load_mdms_employ()

        # 获取operation_jg
        self.operation_jg_short_columns = ['Entity_Opreation', 'PROJ_TYPE', 'NAME', 'ISPAID', 'PAID_TYPE', 'PLANCODE']
        self.df_operation_jg_short = self.load_operation_jg_short()

        # operation_jg重命名字段
        self.df_operation_jg_short = self.df_operation_jg_short.rename(columns={
            'PROJ_TYPE': 'PROJ_TYPE_CODE'  # 将 PROJ_TYPE 重命名为 PROJ_TYPE_CODE
        })

        replace_dict1 = {
            '0101': '达标技改',
            '0102': '提效技改-设备节能技改',
            '0103': '提效技改-工艺优化技改',
            # '0104': '应急专项-自然灾害',
            '0105': '应急专项-自然灾害',
            '0106': '提效技改-智能控制技改',
            '0107': '提效技改-新技术应用技改'

        }

        replace_dict = {
            'PT01': '调整水价/水量',
            'PT02': '政府专项补助'
        }

        # 使用 replace 函数进行替换
        self.df_operation_jg_short['PROJ_TYPE'] = self.df_operation_jg_short['PROJ_TYPE_CODE'].replace(replace_dict1)

        self.df_operation_jg_short['PAID_TYPE'] = self.df_operation_jg_short['PAID_TYPE'].replace(replace_dict)

        # Merge data
        self.df_merged = self.merge_data()


    def fun_query_dimension(self,dimension, expression, fields):
        # 维度 实例化
        dim = Dimension(dimension, path='/02_Dimension')
        # 查询维度现有成员
        df = pd.DataFrame(dim.query(expression=expression, fields=fields, as_model=False))
        df = df.rename(columns={'description_zh_cn': 'language_zh-cn'})
        del df['id']
        df = df.where(df.notnull(), None)
        return df

    def load_profile_data(self,jg_table,nj_table,jg_columns,nj_columns,entity_ids,department_id_single,year_id_single):
        result = pd.DataFrame(columns=nj_columns)
        if department_id_single == 'Equipment':
            where = ((nj_table.table.entity.isin(entity_ids)) & (nj_table.table.year == year_id_single))
            result = nj_table.select(where=where,columns=nj_columns)
        elif department_id_single == 'Technical':
            where = ((jg_table.table.entity.isin(entity_ids)) & (jg_table.table.year == year_id_single))
            result = pd.DataFrame(jg_table.select_raw(where=where, columns=jg_columns))
            # 直接写死缺失列，填充 NaN
            missing_columns = ['sum_dm', 'sum_dc', 'implementation_dm', 'plan_dc']
            for col in missing_columns:
                result[col] = None
        else:
            print(f"其他条线: {department_id_single}")
            return result
        return result


    def load_entity_zt_new(self):
        """Load Entity_ZT_NEW data."""
        return rdb_.select(columns=self.entity_zt_new_columns, tbl="Entity_ZT_NEW")

    def load_mdms_employ(self):
        """Load mdms_employ data."""
        df_mdms_employ = rdb_.select(columns=self.mdms_employ_columns, tbl="mdms_employ")
        return df_mdms_employ.rename(columns={"NAME": "CHANGEUSERNAME"})

    def load_operation_jg_short(self):
        """Load Operation_JG_short data."""
        return rdb_.select(columns=self.operation_jg_short_columns, tbl="Opreation_JG")

    # 合并表
    def merge_data(self):
        """Merge data from different sources."""
        df_merged = pd.merge(self.df_equipment_profile, self.df_entity_zt_new, how='inner', left_on='entity',
                             right_on="project_code")
        # print('两表合并',df_merged)
        df_merged = pd.merge(df_merged, self.df_operation_jg_short, how='left', left_on=['entity', 'plancode'],
                             right_on=['Entity_Opreation', 'PLANCODE'])
        # print('三表合并',df_merged)

        df_merged = df_merged.applymap(lambda x: None if pd.isna(x) or x == '' or x is pd.NaT else x)
        return df_merged

    def apply_conditions(self, df):
        """Apply conditions to determine Budget_Allocation and amount columns."""
        conditions = [
            {'mask': (df['equipment_location'] == 'el01') & (df['type'] == 'OR01') & df[
                'sum_or'].notna() & (df['sum_or'] != 0), 'Budget_Allocation': 'Eq05', 'amount_col': 'sum_or'},
            {'mask': (df['equipment_location'] == 'el01') & (df['type'] == 'OR02') & df[
                'sum_or'].notna() & (df['sum_or'] != 0), 'Budget_Allocation': 'Eq09', 'amount_col': 'sum_or'},
            {'mask': (df['equipment_location'] == 'el01') & df['sum_new'].notna() & (df['sum_new'] != 0),
             'Budget_Allocation': 'Eq06', 'amount_col': 'sum_new'},
            {'mask': (df['equipment_location'] == 'el01') & df['sum_dc'].notna() & (df['sum_dc'] != 0),
             'Budget_Allocation': 'Eq01', 'amount_col': 'sum_dc'},
            {'mask': (df['equipment_location'] == 'el01') & (df['implementation_dm'] == 'I02') & df[
                'sum_dm'].notna() & (df['sum_dm'] != 0), 'Budget_Allocation': 'Eq04', 'amount_col': 'sum_dm'},
            {'mask': (df['equipment_location'] == 'el01') & (df['implemen  tation_dm'] == 'I03') & df[
                'sum_dm'].notna() & (df['sum_dm'] != 0), 'Budget_Allocation': 'Eq03', 'amount_col': 'sum_dm'},
            {'mask': (df['equipment_location'] == 'el02') & df['sum_or'].notna() & (df['sum_or'] != 0),
             'Budget_Allocation': 'Eq07', 'amount_col': 'sum_or'},
            {'mask': (df['equipment_location'] == 'el02') & df['sum_new'].notna() & (df['sum_new'] != 0),
             'Budget_Allocation': 'Eq08', 'amount_col': 'sum_new'},
            {'mask': (df['equipment_location'] == 'el02') & df['sum_dc'].notna() & (df['sum_dc'] != 0),
             'Budget_Allocation': 'Eq02', 'amount_col': 'sum_dc'}
        ]

        # Create empty DataFrame for final results
        df_final = pd.DataFrame()

        # Apply conditions
        for condition in conditions:
            mask = condition['mask']

            df_filtered = df[mask].copy()
            df_filtered['Budget_Allocation'] = condition['Budget_Allocation']
            df_filtered['GROUP_AMOUNT_NEW'] = df_filtered[condition['amount_col']]
            df_filtered[condition['amount_col']] = np.nan  # Clear the original column after processing

            # # 对 sum_dc 和 sum_dm 相关条件进行特殊处理
            # if condition['Budget_Allocation'] in ['Eq01', 'Eq02', 'Eq03', 'Eq04']:
            #     df_filtered['department'] = 'Equipment'  # 固定 department 为 Equipment
            #     df_filtered['ISPAID'] = None  # 设置为空
            #     df_filtered['PLANCODE'] = None  # 设置为空
            #     df_filtered['reason'] = None  # 设置为空
            #     df_filtered['NAME'] = None  # 设置为空
            #     df_filtered['PAID_TYPE'] = None  # 设置为空
            #     df_filtered['PROJ_TYPE_CODE'] = None  # 设置为空
            #     df_filtered['PROJ_TYPE'] = None  # 设置为空
            #     df_filtered['BUDGE_TYPE'] = '010103'  # 固定 BUDGE_TYPE 为 010103

            df_final = pd.concat([df_final, df_filtered], ignore_index=True)

            # 根据条件赋值
            df_final.loc[df_final['Budget_Allocation'].isin(['Eq05', 'Eq07', 'Eq09']), 'plan'] = df_final['plan_or']
            df_final.loc[df_final['Budget_Allocation'].isin(['Eq05', 'Eq07', 'Eq09']), 'implementation'] = df_final['implementation_or']
            df_final.loc[df_final['Budget_Allocation'].isin(['Eq05', 'Eq07', 'Eq09']), 'reason'] = df_final['reason']

            df_final.loc[df_final['Budget_Allocation'].isin(['Eq03', 'Eq04']), 'plan'] = df_final['plan_dc']
            df_final.loc[df_final['Budget_Allocation'].isin(['Eq03', 'Eq04']), 'implementation'] = df_final[
                'implementation_dm']

            df_final.loc[df_final['Budget_Allocation'].isin(['Eq06', 'Eq08']), 'plan'] = df_final['plan_new']
            df_final.loc[df_final['Budget_Allocation'].isin(['Eq06', 'Eq08']), 'implementation'] = df_final[
                'implementation_new']
            df_final.loc[df_final['Budget_Allocation'].isin(['Eq06', 'Eq08']), 'reason'] = df_final[
                'reason']

            # print(df_final)
            # df_final.to_csv("1.csv",encoding='gbk',index=False)


        return df_final

    def process_data(self):
        """Process data based on adj value."""
        df_processed = self.apply_conditions(self.df_merged)
        # print(df_processed)
        # df_processed = df_processed[df_processed["department"].isin(self.department)]

        # 获取当前年份
        current_year = str(datetime.datetime.now().year)

        # 设置编码：判断 plancode 是否有值，生成 BUDGE_CODE
        # print('df_processed', df_processed)

        # 检查是否为空·
        if df_processed.empty:
            print("关联的数据为空. 程序中止.")
            return None

        df_processed['BUDGE_CODE'] = df_processed.apply(
            lambda row: f"{'B'}{row['project_code']}{self.year_id_single}" if row['department'] == 'Equipment'
            else f"{'B'}{row['plancode']}", axis=1
        )


        df_processed['Item'] = df_processed.apply(
            lambda row: row['code'] + self.year_id_single if row['Budget_Allocation'] in ['Eq05', 'Eq09','Eq06','Eq07','Eq08']
            else row['code'] + row['Budget_Allocation'] + self.year_id_single , axis=1
        )

        # 设置系统字段
        df_processed['BUDGE_TYPE'] = df_processed.apply(
            lambda row: '010103' if row['department'] == 'Equipment'
            else '020101', axis=1
        )
        df_processed['PUSHFLAG'] = '0'
        df_processed['PUSHTIME'] = datetime.datetime.now()
        df_processed['FREEZEFLAG'] = '0'
        # print('df_process',df_processed)

        # 插入数据状态
        df_processed["BUDGE_STATUS"] = "1"
        df_processed["APPROVE_STATUS"] = "1"

        # Transform user names
        space_api = SpaceAPI()

        def get_user_info(user_id):
            try:
                if not user_id:  # 检查 user_id 是否为空
                    return None  # 或者返回其他指示值
                user_info_response = space_api.user.query(userId=user_id)
                return user_info_response.userName
            except Exception as e:
                print("获取失败或creator、modifier为空")
                return user_id

        # df_processed['_creator'] = df_processed['_creator'].apply(get_user_info)
        # df_processed['_modifier'] = df_processed['_modifier'].apply(get_user_info)
        # df_processed['_create_time'] = pd.to_datetime(df_processed['_create_time'], errors='coerce')
        # df_processed['_modify_time'] = pd.to_datetime(df_processed['_modify_time'], errors='coerce')

        # Merge with mdms_employ
        # df_processed = pd.merge(df_processed, self.df_mdms_employ[['USER_CODE', 'CHANGEUSERNAME', 'ORGNAME']],
        #                         left_on="_creator", right_on="USER_CODE", how="left")
        # df_processed = pd.merge(df_processed, self.df_mdms_employ[['USER_CODE', 'ORGID', 'CHANGEUSERNAME']],
        #                         left_on="_modifier", right_on="USER_CODE", how="left")

        df_processed['_creator'] = 'Admin'
        df_processed['_modifier'] = 'Admin'
        df_processed['CHANGEUSERNAME_x'] = 'Admin'
        df_processed['CHANGEUSERNAME_y'] = 'Admin'
        df_processed['ORGID'] = None
        df_processed['ORGNAME'] = None

        df_processed['_create_time'] = pd.to_datetime(df_processed['_create_time'], errors='coerce')
        df_processed['_modify_time'] = pd.to_datetime(df_processed['_modify_time'], errors='coerce')

        # Rename columns and return final DataFrame
        df_processed = df_processed.rename(columns={
            "year": "YEAR",
            "project_code": "Entity_Number",
            "project_name": "Entity_Name",
            "name": "equip_name_short",
            "location": "facity",
            "CHANGEUSERNAME_x": "CHANGEUSERNAME",
            "CHANGEUSERNAME_y": "LASTUSERNAME"
        })

        budget_columns_to_keep = [
            'YEAR', 'Entity_Number', 'Entity_Name', 'Budget_Allocation', 'BUDGE_TYPE', 'department', 'code',
            'equipment_location',
            'equip_name_short', 'facity', 'BUDGE_CODE', 'BUDGE_STATUS', 'GROUP_AMOUNT_NEW', 'plan', 'implementation',
            'reason',
            'Item', 'PROJ_TYPE', 'PROJ_TYPE_CODE', 'NAME', 'ISPAID', 'PAID_TYPE', 'APPROVE_STATUS', 'PUSHFLAG',
            'FREEZEFLAG',
            'ORGNAME', 'ORGID', '_creator', '_modifier', 'PUSHTIME', '_create_time', '_modify_time', 'CHANGEUSERNAME',
            'LASTUSERNAME'
        ]

        budget_data = df_processed[budget_columns_to_keep]
        # print(budget_data)
        return budget_data

    def  write_to_database(self):
        """Write processed data to the database."""

        df_to_update = self.process_data()
        if df_to_update is None:
            print("关联数据为空")
            return None


        # 插入act表
        updatecol = list(set(df_to_update.columns) - {"Item"})
        # print(updatecol)
        self.Act_table.insert_df(df_to_update, updatecol,chunksize=1000)  # 按照 'Item' 列更新

        return True


# Main function
def main(p1, p2):
    # p1 = ...  # Initialize or fetch necessary parameters for ActTools
    # p2 = {'original_status': ['Status08'], 'result_status': 'Status06', 'form_data': [{'entity_id': 'Y3720210035', 'department_id': 'Equipment', 'year_id': '2025'}]}
    # p2 = {'original_status': ['Status06', 'Status07'], 'result_status': 'Status08',
    #  'form_data': [{'entity_id': 'PS14001_01', 'department_id': 'Technical', 'year_id': '2025'}]}

    act_tools = ActTools(p1,p2)
    result = act_tools.write_to_database()
    if result is None:
        return False
    print("写入act表成功")
    kafka_main(p1, p2)

if __name__ == "__main__":
    p2 = {'original_status': ['Status06', 'Status07'], 'result_status': 'Status08', 'form_data': [{'entity_id': 'D003429', 'department_id': 'Equipment', 'year_id': '2026'}]}
    main(para1,p2)
