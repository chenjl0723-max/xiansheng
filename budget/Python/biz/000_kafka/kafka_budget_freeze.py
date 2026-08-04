"""
added by cjl
added in 20241014
added for 冻结业务预算数据下发脚本
主要逻辑：
    # 冻结预算下发脚本，当集团审批通过撤回时触发
    # 1、获取前端发送的子水厂信息，通过维度获取项目编码
    # 2、使用项目编码在act表中修改'BUDGE_STATUS'，'APPROVE_STATUS','FREEZEFLAG'这三个字段的状态，调整为对应的冻结状态
    # 2、还应修改act表中的'PUSHFLAG'推送标识，改为'0'，保证下次数据可以正常下发
    # 3、使用项目编码在中间表中获取匹配数据
    # 4、将获取的dataframe转换为下发格式的json格式，然后下发到kafka上
剩余问题：无
"""

try:
    from common._debug import para1, para2
    # print(para1)
except ImportError:
    para1 = para2 = {}

from kafka import KafkaProducer
from common import setting
from deepfos.element.datatable import DataTableMySQL
from deepfos.element.dimension import Dimension
from deepfos.db.mysql import MySQLClient
import pandas as pd
import traceback
import json
from datetime import datetime


pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)


class FreezeBudgetDataProcessor:
    def __init__(self,p2):
        self.client = MySQLClient()
        # Budget_Production_Middle_Table表对象
        self.act_table = DataTableMySQL("Budget_Production_Middle_Table")

        # 解析参数 转置df
        df_status = pd.DataFrame(p2['form_data'])

        # 处理组织
        entity = list(set(df_status['entity_id'].to_list()))
        expression = ''
        for i in entity:
            expression += 'IBase(%s,0);' % i
        expression = expression[:-1]
        print(expression)
        df_entity = self.fun_query_dimension('Entity', expression, ['name'])
        print('df_entity',df_entity)
        self.entity = tuple(df_entity['name'].to_list())
        print('entity',entity)
        entity_id = "','".join(set(df_entity['name'].to_list()))
        print('entity_id',entity_id)

    def operate_mysql(self, element_name, path, df_status, operate):
        """
        封装 MySQL 更新逻辑，按 form_data 中的 entity_id 和 department_id 配对更新状态
        :param client: MySQLClient 实例
        :param element_name: 表名
        :param path: 表路径
        :param df_status: form_data 转换的 DataFrame
        :return: 更新结果
        """
        sqls = []
        for _, row in df_status.iterrows():
            entity_id_single = row['entity_id']
            department_id_single = row['department_id']
            year_id_single = row['year_id']

            # 获取该子水厂的所有子集
            expression = f'IBase({entity_id_single},1)'
            df_entity_subset = self.fun_query_dimension('Entity', expression, ['name'])
            entity_ids = df_entity_subset['name'].to_list() if not df_entity_subset.empty else [entity_id_single]
            # 将 entity_ids 转换为逗号分隔的字符串，用于拼接sql
            entity_ids_str = "','".join(entity_ids)

            if element_name == 'Budget_Production_Middle_Table' and operate == 'update':
                sql = (
                    f"update ${{{element_name}}} set BUDGE_STATUS='0',APPROVE_STATUS='0',FREEZEFLAG='1',PUSHFLAG ='1'"
                    f"where Entity_Number IN ('{entity_ids_str}') "
                    f"and department = '{department_id_single}' "
                    f"and YEAR = '{year_id_single}'"
                )
            elif element_name == 'Equipment_Act' and operate == 'update':
                sql = (
                    f"update ${{{element_name}}} set BUDGE_STATUS='0',APPROVE_STATUS='0',FREEZEFLAG='1',PUSHFLAG ='1'"
                    f"where Entity_Number IN ('{entity_ids_str}') "
                    f"and department = '{department_id_single}' "
                    f"and YEAR = '{year_id_single}'"
                )
            elif element_name == 'Budget_Production_Middle_Table' and operate == 'select':
                sql = (
                    f"select * from ${{{element_name}}} "
                    f"where Entity_Number IN ('{entity_ids_str}') "
                    f"and department = '{department_id_single}' "
                    f"and YEAR = '{year_id_single}'"
                )
            sqls.append(sql)

        return sqls

    def fun_query_dimension(self,dimension, expression, fields):
        # 维度 实例化
        dim = Dimension(dimension, path='/02_Dimension')
        # 查询维度现有成员
        df = pd.DataFrame(dim.query(expression=expression, fields=fields, as_model=False))
        df = df.rename(columns={'description_zh_cn': 'language_zh-cn'})
        del df['id']
        df = df.where(df.notnull(), None)
        return df

    def update_act(self,p2):
        print(p2)
        # client = MySQLClient()
        df_status = pd.DataFrame(p2['form_data'])
        middle_sqls = self.operate_mysql('Budget_Production_Middle_Table',
                                    '/05_Datatable/05_08_Equipment', df_status, 'update')
        result_01 = self.client.exec_sqls(middle_sqls)

        act_sqls = self.operate_mysql('Equipment_Act',
                                        '/05_Datatable/05_08_Equipment', df_status, 'update')
        result_02 = self.client.exec_sqls(act_sqls)

        # self.act_table = DataTableMySQL("Budget_Production_Middle_Table")
        '''
        middle_elementName = 'Budget_Production_Middle_Table'
        act_elementName = 'Equipment_Act'
        path = '/05_Datatable/05_08_Equipment'



        # # 先注释掉操作act
        # result_01 = self.client.exec_sqls(sqls=["update ${%s} set BUDGE_STATUS='0',APPROVE_STATUS='0',FREEZEFLAG='1',PUSHFLAG ='1' where Entity_Number in %s"
        #                                     % (act_elementName,self.entity)],
        #                                     table_info={act_elementName: {'elementName': act_elementName,
        #                                                        'elementType': 'DataTableMySQL',
        #                                                        'path': path}})
        # 如果传的条线
        df_department = pd.DataFrame(p2['form_data'])
        for i in df_department['department_id']:
            if i == 'Equipment':
                middle_sql = [
                    "update ${%s} set BUDGE_STATUS='0',APPROVE_STATUS='0',FREEZEFLAG='1',PUSHFLAG ='1' where Entity_Number in %s and (BUDGE_CODE like 'BY%%' or BUDGE_CODE like 'BC%%')"
                    % (middle_elementName, self.entity)]

                act_sql = [
                    "update ${%s} set BUDGE_STATUS='0',APPROVE_STATUS='0',FREEZEFLAG='1',PUSHFLAG ='1' where Entity_Number in %s and department = 'Equipment'"
                    % (act_elementName, self.entity)]

                result_01 = self.client.exec_sqls(sqls=act_sql,
                                                  table_info={act_elementName: {'elementName': act_elementName,
                                                                                'elementType': 'DataTableMySQL',
                                                                                'path': path}})

                result_02 = self.client.exec_sqls(sqls=middle_sql,
                                                  table_info={middle_elementName: {'elementName': middle_elementName,
                                                                                   'elementType': 'DataTableMySQL',
                                                                                   'path': path}})

            elif i == 'HR':
                middle_sql = [
                    "update ${%s} set BUDGE_STATUS='0',APPROVE_STATUS='0',FREEZEFLAG='1',PUSHFLAG ='1' where Entity_Number in %s and BUDGE_CODE like 'BJ%%'"
                    % (middle_elementName, self.entity)]

                act_sql = [
                    "update ${%s} set BUDGE_STATUS='0',APPROVE_STATUS='0',FREEZEFLAG='1',PUSHFLAG ='1' where Entity_Number in %s and department = 'HR'"
                    % (act_elementName, self.entity)]

                result_01 = self.client.exec_sqls(sqls=act_sql,
                                                  table_info={act_elementName: {'elementName': act_elementName,
                                                                                'elementType': 'DataTableMySQL',
                                                                                'path': path}})

                result_02 = self.client.exec_sqls(sqls=middle_sql,
                                                  table_info={middle_elementName: {'elementName': middle_elementName,
                                                                                   'elementType': 'DataTableMySQL',
                                                                                   'path': path}})
                # print(i)
            elif i == 'Operation':
                print('审批条线为运行条线')
                pass


        # print(result_02)
        '''

    def process_budget_data(self,p2):
        # elementName = 'Budget_Production_Middle_Table'
        # path = '/05_Datatable/05_08_Equipment'
        df_status = pd.DataFrame(p2['form_data'])
        middle_sqls = self.operate_mysql('Budget_Production_Middle_Table',
                                        '/05_Datatable/05_08_Equipment', df_status, 'select')
        middle_table = self.client.query_dfs(middle_sqls)
        df_final = pd.concat(middle_table)
        '''
        self.middle_table = pd.DataFrame()
        for i in df_department['department_id']:
            if i == 'Equipment':
                middle_sql = [
                    "select * from ${%s} where Entity_Number in %s and  (BUDGE_CODE like 'BY%%' or BUDGE_CODE like 'BC%%')"
                    % (elementName, self.entity)]
            elif i == 'HR':
                middle_sql = [
                    "select * from ${%s} where Entity_Number in %s and BUDGE_CODE like 'BJ%%'"
                    % (elementName, self.entity)]
            self.middle_table_item = self.client.exec_sqls(sqls=middle_sql,
                                              table_info={elementName: {'elementName': elementName,
                                                                        'elementType': 'DataTableMySQL',
                                                                        'path': path}})
            self.middle_table_item = pd.DataFrame(self.middle_table_item['selectData'])

            self.middle_table = pd.concat([self.middle_table, self.middle_table_item], ignore_index=True)
            print('中间表取数',self.middle_table)
        '''
        result_list = self.build_json_data(df_final)

        # 提取主预算信息 要发给主数据（LIST=[]）
        main_budget_list = self.extract_main_budget(result_list)

        sed_result_split = self.split_json_data(result_list)
        # with open("freeze_result.json", 'w', encoding='utf-8') as f:
        #     json.dump(result_split, f, ensure_ascii=False, indent=4)
        print("预算冻结数据处理完成。")
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

    def build_json_data(self, df_final_filtered):
        result_list = []
        current_date = datetime.now().strftime("%Y%m%d%H%M%S")

        for _, row in df_final_filtered.iterrows():

            # 将 GROUP_AMOUNT_NEW 转换为数字，如果无法转换则设置为 0
            # try:
            #     group_amount_new_value = pd.to_numeric(row["GROUP_AMOUNT_NEW"], errors='coerce')
            #     if pd.isna(group_amount_new_value):
            #         group_amount_new_value = 0
            # except Exception as e:
            #     group_amount_new_value = 0

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

                # # 新增应急专项预算
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
                "items_num": '',
                "batch_no": row["BUDGE_CODE"] + current_date,
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
                "plan": row["plan"],
                "sum": row["GROUP_AMOUNT_NEW"],
                "Budget_Allocation": row["Budget_Allocation"],
                "implementation": row["implementation"],
                "start_month": row["start_month"],
                "acceptance_month": row["acceptance_month"],
                "equipment_location": row["equipment_location"],
                "equip_name_short": row["equip_name_short"],
                "code": row["code"],
                "equip_seq": None if pd.isna(row["equip_seq"]) else row["equip_seq"],
                "equipment_type": row["equipment_type"],
                "manufacturer": row["manufacturer"],
                "location": row["location"],
                "location_no": row["location_no"],
                "former_name": row["former_name"],
                "facility_period": row["facility_period"],
                "facility_no": row["facility_no"]

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
    def split_json_data(self, data):
        # 设定每个 JSON 包含的 ITEM 数量
        batch_size = 30
        split_jsons = []
        for message in data:
            # 获取 LIST 数据
            items = message['LIST']
            message["items_num"] = len(items)
            total_batches = (len(items) + batch_size - 1) // batch_size  # 计算总批次数量

            # 拆分成多个 JSON，每个包含最多 batch_size 个 ITEM
            for batch_index, i in enumerate(range(0, len(items), batch_size)):
                new_data = message.copy()
                # 判断是否为最后一个批次，添加终止标识符
                new_data['terminated'] = "终止" if batch_index == (total_batches - 1) else "推送中"
                new_data['LIST'] = items[i:i + batch_size]
                split_jsons.append(new_data)

            # 打印拆分结果
            # for idx, json_part in enumerate(split_jsons[-total_batches:]):
            #     print(f"--- JSON 部分 {idx + 1} ---")
            #     print(json.dumps(json_part, indent=4, ensure_ascii=False))
        # 写入文件
        # with open("df_result_dongjie.json", 'w', encoding='utf-8') as f:
        #     json.dump(split_jsons, f, ensure_ascii=False, indent=4)

        return split_jsons

class KafkaBudgetSender:
    def __init__(self):
        # 初始化两个 Kafka Producer，一个用于 main_data，一个用于 sed_data
        self.producer = KafkaProducer(
            bootstrap_servers=setting.kafka_setting_budget_uat['bootstrap_servers'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )

    def send_to_kafka(self, main_data, sed_data):
        # 发送 main_data 到主预算 Kafka 主题
        if main_data:
            print(f'发送 {len(main_data)} 条主预算数据')
            for message in main_data:
                data = [message]
                future = self.producer.send(setting.kafka_setting_budget_uat['main_topic_name'],value=data)
                future.add_callback(lambda record_metadata: self.delivery_report(None, record_metadata, 'main'))
                future.add_errback(lambda exc: self.delivery_report(exc, None, 'main'))
            self.producer.flush()

        # 发送 sed_data 到 SED 预算 Kafka 主题
        if sed_data:
            print(f'发送 {len(sed_data)} 条 SED 预算数据')
            for message in sed_data:
                data = [message]
                future = self.producer.send(setting.kafka_setting_budget_uat['sed_topic_name'],value=data)
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
    print(p2)
    try:
        freeze = FreezeBudgetDataProcessor(p2)
        update_FREEZEFLAG = freeze.update_act(p2)
        main_data,sed_data = freeze.process_budget_data(p2)
    except Exception as e:
        traceback.print_exc()

    if main_data:
        sender = KafkaBudgetSender()
        sender.send_to_kafka(main_data, sed_data)


# debug
if __name__ == '__main__':
    p2 = {'original_status': ['Status06'], 'result_status': 'Status08',
     'form_data': [{'entity_id': 'PS61001_01', 'department_id': 'Technical', 'year_id': '2025'},
                   {'entity_id': 'PS14003_01', 'department_id': 'Equipment', 'year_id': '2025'}]}

    main(para1, p2)