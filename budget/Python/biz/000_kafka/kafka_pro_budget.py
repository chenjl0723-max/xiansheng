"""
added by cjl
added in 20241014
added for 业务预算下发脚本
主要逻辑：
    读取equipment_act表中的设备、设施预算信息，关联equipment_profile表、
    运营项目表（entity_ZT_new）、设备中间表（bewg_equipment_info）匹配设备的关联设施ID,
    往主数据的kafka上做下发，同时写入中间表（Budget_Production_Middle_Table）.
剩余问题：需要修改管理设施ID时，要改成取设施中间表的数据。
"""
# from equipment_installation_to_profile_to_act.test_drop import result

# from idlelib.iomenu import encoding

try:
    from common.__debug import para1, para2
    # print(para1)
except ImportError:
    para1 = para2 = {}

from deepfos.element.datatable import DataTableMySQL
from budget.Python.common import setting
from common.commons import *
from deepfos.element.dimension import Dimension

import pandas as pd
import json
from datetime import datetime

from kafka import KafkaProducer
# from kafka_main.conf import setting
# from kafka_main.conf import test_data
# from common.commons import *
from deepfos.api.space import SpaceAPI

# import pandas as pd
# import json
# from datetime import datetime

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)


# 初始化 SpaceAPI 实例
space_api = SpaceAPI()


# 使用 SpaceUserAPI 的 query 方法获取用户信息
def get_user_info(user_id):
    try:
        # 调用 SpaceUserAPI 的 query 方法
        user_info_response = space_api.user.query(userId=user_id)
        # print(user_info_response.userName)
        return user_info_response.userName  # 假设 userName 是门户账号
    except Exception as e:
        print(f"获取用户信息失败: {e}")
        return user_id  # 如果失败，返回原始的 user_id


class BudgetDataProcessor:
    def __init__(self,p1,p2):
        df_status = pd.DataFrame(p2['form_data'])
        for _, row in df_status.iterrows():
            entity_id_single = row['entity_id']
            department_id_single = row['department_id']
            year_id_single = row['year_id']
        # print(p2)
        # df_status = pd.DataFrame(p2['form_data'])
        # # 处理组织
        # entity = list(set(df_status['entity_id'].to_list()))
        # expression = ''
        # for i in entity:
        #     expression += 'IBase(%s,0);' % i
        # expression = expression[:-1]
        # print(expression)
        # df_entity = self.fun_query_dimension('Entity', expression, ['name'])
        # print('df_entity',df_entity)
        # self.entity = tuple(df_entity['name'].to_list())
        #
        # self.department = df_status['department_id'].to_list()


        act_columns = [
                       # CHANGEDATE制单时间取_create_time,
                       # CHANGEUSERID修改人编码、LASTUSERID最后修改人编码取_modifier,
                       # LASTDATE最后更新时间取_modify_time ;
                       # SYSID写入空  ,"LASTUSERNAME"还没在act里存
                       # 用作关联profile表
                        "Entity_Number", "Entity_Name",
                       "Item", "code", "equip_name_short","Budget_Allocation","equipment_location",
                       "department","GROUP_AMOUNT_NEW","implementation","plan","reason",
                        "BUDGE_TYPE", "BUDGE_CODE", "NAME", "GROUP_AMOUNT_NEW",
                        "BUDGE_STATUS", "PROJ_TYPE", "PROJ_TYPE_CODE",
                        "ISPAID", "PAID_TYPE", "YEAR", "APPROVE_STATUS", "PUSHFLAG", "PUSHTIME", "FREEZEFLAG",
                        "_create_time", "CHANGEUSERNAME",
                        "ORGNAME", "ORGID", "_modifier", "_modify_time", "LASTUSERNAME"
                       ]

        self.act_table = DataTableMySQL("Equipment_Act")
        # print(profile_table)

        # 查询act表 技改、非技改数据
        where_jg = (self.act_table.table.PUSHFLAG == '0') & (self.act_table.table.department== 'Technical') & (self.act_table.table.Year == year_id_single)
        where_nj = (self.act_table.table.PUSHFLAG == '0') & (self.act_table.table.department== 'Equipment') & (self.act_table.table.Year == year_id_single)
        act_jg = pd.DataFrame(self.act_table.select_raw(columns=act_columns, where=where_jg))
        act_nj = pd.DataFrame(self.act_table.select_raw(columns=act_columns, where=where_nj))


        profile_columns = ["code","start_month","acceptance_month",  "equip_seq", "equipment_type",
                           "manufacturer",'type',"location","location_no","former_name", "facility_period", "facility_no","equip_no"]

        # 查询profile技改表、非技改表数据
        where = "year = '%s' " % (
            year_id_single)
        profile_jg = DataTableMySQL("equipment_profile_JG")
        df_profile_jg = pd.DataFrame(profile_jg.select_raw(columns=profile_columns,where = where))
        profile_nj = DataTableMySQL("equipment_profile_NJ")
        df_profile_nj = pd.DataFrame(profile_nj.select_raw(columns=profile_columns,where = where))



        entity_columns = ["project_code", "project_name", "org_name", "pk_manag_org", "org_code", "pk_company",
                          "company_name", "company_code", "M_FIR_BIZ","M_FIR_BIZ_CODE", "M_SEC_BIZ", "M_SEC_BIZ_CODE",
                          "M_BIZ_TYPE_NAME", "M_BIZ_TYPE_CODE", "sub_factory_code",
                          "sub_factory_name", "factory_code", "factory_name"]
        # 查询组织维度表信息
        dt_entity =  DataTableMySQL("Entity_ZT_NEW")
        df_entity = pd.DataFrame(dt_entity.select_raw(columns=entity_columns))

        if not act_jg.empty:
            # 关联act和profile
            df_jg = pd.merge(act_jg, df_profile_jg, on=["code"], how="left")
            df_jg = pd.merge(df_jg, df_entity, left_on=["Entity_Number", "Entity_Name"],
                                 right_on=["project_code", "project_name"],
                                 how="inner")
        else:
            df_jg = pd.DataFrame()
        if not act_nj.empty:
            df_nj = pd.merge(act_nj, df_profile_nj, how="left",on=["code"])
            df_nj = pd.merge(df_nj, df_entity, left_on=["Entity_Number", "Entity_Name"],
                             right_on=["project_code", "project_name"],
                             how="inner")
        else:
            df_nj = pd.DataFrame()

        self.profile_df = pd.concat([df_jg, df_nj], ignore_index=True)

        # 设备中间表
        # equipment_info_columns = ["Operation", "fati_name","fati_code"]
        #
        # self.df_equipment_info = rdb_.select(columns=equipment_info_columns, tbl="bewg_equipment_info",
        #                                      path="/Datatable/Middle_Table/His_Table/")

        # 下发中间表，用于下发冻结预算
        self.Budget_Production_Middle_Table = DataTableMySQL("Budget_Production_Middle_Table")


    def fun_query_dimension(self,dimension, expression, fields):
        # 维度 实例化
        dim = Dimension(dimension)
        # 查询维度现有成员
        df = pd.DataFrame(dim.query(expression=expression, fields=fields, as_model=False))
        df = df.rename(columns={'description_zh_cn': 'language_zh-cn'})
        del df['id']
        df = df.where(df.notnull(), None)
        return df

    def process_budget_data(self):
        # print(df_final)
        if self.profile_df.empty:
            print("一个或多个源数据表为空。")
            return None,None
        columns_to_keep = [
            "BUDGE_TYPE", "BUDGE_CODE", "Entity_Number", "Entity_Name", "department","org_name", "pk_manag_org", "org_code",
            "pk_company",
            "company_name", "company_code", "M_FIR_BIZ","M_FIR_BIZ_CODE", "M_SEC_BIZ", "M_SEC_BIZ_CODE",
            "M_BIZ_TYPE_NAME", "M_BIZ_TYPE_CODE",  "sub_factory_code", "sub_factory_name", "factory_code",
            "factory_name", "NAME","GROUP_AMOUNT_NEW",
            "BUDGE_STATUS", "PROJ_TYPE", "PROJ_TYPE_CODE","ISPAID", "PAID_TYPE", "YEAR", "APPROVE_STATUS", "Item",
            "Budget_Allocation","plan","implementation",
            "reason", "start_month", "acceptance_month", "equipment_location", "equip_name_short", "code",
            "equip_seq", "equipment_type","equip_no",
            # 如果是设备类型el01，则“location_no”取中间表里的“FACILITYNO”，需要与bewg_equipment_info中间表关联
            # 如果是设施类型el02，则“location_no”取code
            "manufacturer", "location", "location_no", "former_name", "facility_period", "facility_no",
            # 制单时间'CHANGEDATE' = '_create_time'
            # 修改人编码'CHANGEUSERID' = '_modifier'
            # 最后更新时间'LASTDATE' = '_modify_time'
            "PUSHFLAG", "PUSHTIME", "FREEZEFLAG", "_create_time", "CHANGEUSERNAME", "ORGNAME", "ORGID", "_modifier",
            "_modify_time", "LASTUSERNAME"
        ]

        df_final_filtered = self.profile_df[columns_to_keep].copy()
        # 将空值替换为null（None）
        df_final_filtered = df_final_filtered.where(pd.notnull(df_final_filtered), None)

        # 存入下发中间表
        df_middle = df_final_filtered.copy()

        time_columns = ['_create_time', '_modify_time', 'start_month', 'acceptance_month', 'PUSHTIME']
        for col in time_columns:
            df_middle[col] = pd.to_datetime(df_middle[col], errors='coerce')  # 转换为日期时间对象

        df_middle["PUSHFLAG"] = "1"

        # # 新增应急专项预算字段
        # df_middle["IS_INSURANCE"] = "0"
        # df_middle["IS_SUBSIDY "] = "0"
        # 存入Budget_Production_Middle_Table中间表
        updatecol = list(set(df_middle.columns) - {"Item"})
        self.Budget_Production_Middle_Table.insert_df(df_middle, updatecol)


        time_columns = ['_create_time', '_modify_time', 'start_month', 'acceptance_month', 'PUSHTIME']
        for col in time_columns:
            # df_final_filtered[col] = df_final_filtered[col].astype(str)
            df_final_filtered.loc[:, col] = df_final_filtered[col].astype(str)

        # 将 start_month 和 acceptance_month 列中的 NaT 替换为 None
        df_final_filtered[['start_month', 'acceptance_month']] = df_final_filtered[
            ['start_month', 'acceptance_month']].applymap(lambda x: None if  x =='NaT' else x)


        # 生成的全部预算数据
        result_all = self.build_json_data(df_final_filtered)

        # 提取主预算信息 要发给主数据（LIST=[]）
        main_budget_list = self.extract_main_budget(result_all)

        # 包含子预算的数据 要发给sed
        sed_result_split = self.split_json_data(result_all)
        # print("下发的预算数据：", result_list)



        print("预算数据处理完成。")
        return main_budget_list,sed_result_split

    # 为主数据提取主预算信息
    def extract_main_budget(self, result_list):
        """提取主预算信息，去掉 LIST 字段"""
        main_budget_list = []
        for item in result_list:
            # 方法 1：使用 del 删除 LIST 键
            main_budget = item.copy()  # 复制以避免修改原数据
            main_budget['LIST'] = []
            main_budget_list.append(main_budget)

            # 方法 2：使用 pop 删除（如果需要获取被删除的值）
            # main_budget = item.copy()
            # main_budget.pop('LIST', None)  # None 是默认值，防止键不存在时出错
            # main_budget_list.append(main_budget)

            # 方法 3：使用字典推导式（更简洁）
            # main_budget = {key: value for key, value in item.items() if key != 'LIST'}
            # main_budget_list.append(main_budget)

        return main_budget_list

    # 将数组按照接口格式转成json格式
    def build_json_data(self, df_final_filtered):
        result_list = []
        current_date = datetime.now().strftime("%Y%m%d%H%M%S")

        for _, row in df_final_filtered.iterrows():

            # 将 GROUP_AMOUNT_NEW 转换为数字，如果无法转换则设置为 0
            try:
                group_amount_new_value = float(row["GROUP_AMOUNT_NEW"])
                group_amount_new_value = round(group_amount_new_value, 4)
            except Exception as e:
                group_amount_new_value = 0.0

            main_budget_data = {
                # "PRJ_CODE": row["JG_Code"],
                # "PRJ_DATA_STAT_NAME": row["JG_status"],
                # "PRJ_START_DATE": row["JG_Start"],
                # "PRJ_END_DATE": row["JG_Finish"],
                "ORG_NAME": row["org_name"],
                "PK_MANAG_ORG": row["pk_manag_org"],
                "ORG_CODE": row["org_code"],
                "PK_CO_ORG": row["pk_company"],
                "LEG_ORG_NAME": row["company_name"],
                "LEG_ORG_CODE": row["company_code"],
                "FIR_BIZ": row["M_FIR_BIZ"],
                "FIR_BIZ_CODE": row["M_FIR_BIZ_CODE"],
                "SEC_BIZ": row["M_SEC_BIZ"],
                "SEC_BIZ_CODE": row["M_SEC_BIZ_CODE"],
                "BIZ_TYPE_NAME": row["M_BIZ_TYPE_NAME"],
                "BIZ_TYPE_CODE": row["M_BIZ_TYPE_CODE"],
                "sub_factory_code": row["sub_factory_code"],
                "sub_factory_name": row["sub_factory_name"],
                "factory_code": row["factory_code"],
                "factory_name": row["factory_name"],
                "REL_PRJ_CODE": row["Entity_Number"],
                "REL_PRJ_NAME": row["Entity_Name"],
                "BUDGE_CODE": row["BUDGE_CODE"],
                "NAME": row["NAME"],
                "GROUP_AMOUNT_NEW": group_amount_new_value,
                "BUDGE_STATUS": row["BUDGE_STATUS"],
                "PROJ_TYPE": row["PROJ_TYPE"],
                "PROJ_TYPE_CODE": row["PROJ_TYPE_CODE"],
                "ISPAID": row["ISPAID"],
                "PAID_TYPE": row["PAID_TYPE"],

                # 新增应急专项预算
                # "IS_INSURANCE": row["IS_INSURANCE"],
                # "IS_SUBSIDY ": row["IS_SUBSIDY "],


                "YEAR": row["YEAR"],
                "BUDGE_TYPE": row["BUDGE_TYPE"],
                "APPROVE_STATUS": row["APPROVE_STATUS"],
                "PUSHFLAG": row["PUSHFLAG"],
                "PUSHTIME": row["PUSHTIME"],
                # 冻结标识：1冻结，0归档
                "FREEZEFLAG": row["FREEZEFLAG"],
                "terminated": '',
                "items_num" : '',
                "batch_no" : row["BUDGE_CODE"]+current_date,
                "CHANGEDATE": row["_create_time"],
                "CHANGEUSERNAME": row["CHANGEUSERNAME"],
                "ORGNAME": row["ORGNAME"],
                "ORGID": row["ORGID"],
                "CHANGEUSERID": row["_modifier"],
                "LASTUSERID": row["_modifier"],
                "LASTUSERNAME": row["LASTUSERNAME"],
                "LASTDATE": row["_modify_time"],
                "SYSID": '',
                "LIST": []  # 初始化空的 LIST
            }

            # list_key = f"LIST_{row['Item']}"
            list_data = {
                "Item": row["Item"],
                "reason": row["reason"],
                # "plan": row["plan"],
                "sum": row["GROUP_AMOUNT_NEW"],
                "Budget_Allocation": row["Budget_Allocation"],
                "plan": row["plan"],
                "implementation": row["implementation"],
                "start_month": row["start_month"],
                "acceptance_month": row["acceptance_month"],
                "equipment_location": row["equipment_location"],
                "equip_name_short": row["equip_name_short"],
                "code": row["code"],
                "equip_seq": row["equip_seq"],
                "equipment_type": row["equipment_type"],
                "manufacturer": row["manufacturer"],
                "location": row["location"],
                "location_no": row["location_no"],
                "former_name": row["former_name"],
                "facility_period": row["facility_period"],
                "facility_no": row["facility_no"],
                "equip_no":row["equip_no"],

            }

            main_budget_entry = next((item for item in result_list if item["BUDGE_CODE"] == row["BUDGE_CODE"]), None)

            if main_budget_entry is None:
                main_budget_entry = main_budget_data
                main_budget_entry["LIST"].append(list_data)  # 添加到 LIST
                result_list.append(main_budget_entry)
            else:
                # main_budget_entry["GROUP_AMOUNT_NEW"] += group_amount_new_value
                main_budget_entry["GROUP_AMOUNT_NEW"] = round(
                    main_budget_entry["GROUP_AMOUNT_NEW"] + group_amount_new_value, 4)
                main_budget_entry["LIST"].append(list_data)  # 将新项添加到现有 LIST 中

        return result_list


    # 将项目的设备信息切片
    def split_json_data(self,data):
        # 设定每个 JSON 包含的 ITEM 数量
        batch_size = 10
        split_jsons = []
        for message in data:
            # split_jsons = []
            # 获取 LIST 数据
            items = message['LIST']
            message["items_num"] = len(items)
            total_batches = (len(items) + batch_size - 1) // batch_size  # 计算总批次数量

            # 拆分成多个 JSON，每个包含最多 batch_size 个 ITEM
            for batch_index, i in enumerate(range(0, len(items), batch_size)):
                new_data = message.copy()
                # 判断是否为最后一个批次，添加终止标识符
                new_data['terminated'] = "完成" if batch_index == (total_batches - 1) else "推送中"
                new_data['LIST'] = items[i:i + batch_size]

                split_jsons.append(new_data)

            # 打印拆分结果
            # for idx, json_part in enumerate(split_jsons[-total_batches:]):
            #     print(f"--- JSON 部分 {idx + 1} ---")
            #     print(json.dumps(json_part, indent=4, ensure_ascii=False))
            #
            #     print(1)
        # 写入文件
        # with open("df_resultfasong.json", 'w', encoding='utf-8') as f:
        #     json.dump(split_jsons, f, ensure_ascii=False, indent=4)

        return split_jsons

    # 更新推送状态
    def update_freeze_flag(self):
        updatesql = "update ${%s} set PUSHFLAG = '1'" % 'Equipment_Act'
        insertsql = rdb_.exec_sql(updatesql)


class KafkaBudgetSender:
    def __init__(self):
        # 初始化两个 Kafka Producer，一个用于 main_data，一个用于 sed_data
        self.producer = KafkaProducer(
            bootstrap_servers=setting.kafka_setting_prd['bootstrap_servers'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )

    def send_to_kafka(self, main_data, sed_data):
        # 发送 main_data 到主预算 Kafka 主题
        if main_data:
            print(f'发送 {len(main_data)} 条主预算数据')
            for message in main_data:
                data = [message]
                future = self.producer.send(setting.kafka_setting_prd['main_topic_name'], value=data)
                future.add_callback(lambda record_metadata: self.delivery_report(None, record_metadata, 'main'))
                future.add_errback(lambda exc: self.delivery_report(exc, None, 'main'))
            self.producer.flush()

        # 发送 sed_data 到 SED 预算 Kafka 主题
        if sed_data:
            print(f'发送 {len(sed_data)} 条 SED 预算数据')
            for message in sed_data:
                data = [message]
                future = self.producer.send(setting.kafka_setting_prd['sed_topic_name'], value=data)
                future.add_callback(lambda record_metadata: self.delivery_report(None, record_metadata, 'sed'))
                future.add_errback(lambda exc: self.delivery_report(exc, None, 'sed'))
            self.producer.flush()

    @staticmethod
    def delivery_report(error, record_metadata, data_type):
        if error is not None:
            print(f"{data_type} 消息发送失败: {error}")
        else:
            print(f"{data_type} 消息成功发送到 {record_metadata.topic} [分区 {record_metadata.partition}]")


def main(p1, p2):
    print('p2:',p2)

    processor = BudgetDataProcessor(p1,p2)
    main_data,sed_data = processor.process_budget_data()
    print('main_data',main_data)
    print('sed_data',sed_data)
    # 实际
    if main_data:
        sender = KafkaBudgetSender()
        sender.send_to_kafka(main_data, sed_data)
        processor.update_freeze_flag()
    else:
        print("没有匹配到数据")

    # 测试造数
    # if True:
    #     sender = KafkaBudgetSender()
    #     sender.send_to_kafka(budget_data)
        # print("打印下发数据",budget_data)
        # print(test_data.uat_0919_1)
        # sender.send_to_kafka(test_data.uat_0919_1)


if __name__ == "__main__":
    p2 = {'original_status': ['Status06', 'Status07'],
          'result_status': 'Status08',
          'form_data': [{'entity_id': 'PS14001_01', 'department_id': 'Equipment', 'year_id': '2026'},{'entity_id': 'PS61001_01', 'department_id': 'Equipment', 'year_id': '2026'}]}
    main(para1, p2)


