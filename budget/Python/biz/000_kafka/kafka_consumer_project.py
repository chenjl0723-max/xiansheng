# '经营计划的项目信息通过kafka数据接入'
try:
    from _debug import para1, para2
    # print(para1)
except ImportError:
    para1 = para2 = {}

from kafka import KafkaConsumer
from budget.Python.common import setting
from deepfos.db.mysql import MySQLClient
import json
import pandas as pd
import logging


pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)
# 设置日志配置
logging.basicConfig(
    filename='logfile.txt',  # 日志文件的名称
    level=logging.INFO,  # 日志级别
    format='%(asctime)s - %(levelname)s - %(message)s'  # 日志格式
)

# 从设置中获取 Kafka 配置
conf = setting.kafka_setting_main_test
# employ_table = DataTableMySQL("mdms_employ")

# 初始化 KafkaConsumer
consumer = KafkaConsumer(
    'mdms_xm_inc',
    bootstrap_servers=conf['bootstrap_servers'],
    auto_offset_reset='earliest',  # 消费者从最早的消息开始消费
    # enable_auto_commit=True,  # 自动提交偏移量
    group_id='T0080',  # 消费组ID
    value_deserializer=lambda x: x.decode('utf-8')  # 解码消息为 UTF-8
)


def process_message(message):
    """处理单个消息中的多个 JSON 对象"""
    try:
        # 假设消息内容是一个列表，包含多个 JSON 对象
        # print(message["value"])

        # kafka的message对象用message.value获取值
        json_data_list = json.loads(message.value)
        print(json_data_list)

        # message是一个json文本，用message["value"]获取值
        # json_data_list = message["value"]
        print(f"Received {len(json_data_list)} records in a single message.")
        for record in json_data_list:
            if record.get("PRJ_L3_NAME") == "技改专项":
                # 这里写入数据库的代码
                print(f"Writing record to database: {record}")
                with open("xm_result.json", 'a', encoding='utf-8') as f:
                    json.dump(record, f, ensure_ascii=False, indent=4)
                    # 提取字段
                    prj_code = record.get("PRJ_CODE")
                    prj_name = record.get("PRJ_NAME")
                    prj_data_stat_name = record.get("PRJ_DATA_STAT_NAME")
                    prj_start_date = record.get("PRJ_START_DATE")
                    prj_end_date = record.get("PRJ_END_DATE")
                    budge_code = record.get("BUDGE_CODE")

                    # 更新数据库的逻辑
                    # update_equipment_act(budge_code, {
                    #     "JG_Code": prj_code,
                    #     "NAME": prj_name,
                    #     "JG_status": prj_data_stat_name,
                    #     "JG_Start": prj_start_date,
                    #     "JG_Finish": prj_end_date
                    # })

            # df_new = pd.json_normalize(json_data_list)
            else:
                print(f"Skipping record: {json_data_list}")
            # print(json_data_list)

    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}")
    except Exception as e:
        print(f"数据处理失败: {e}")

def update_equipment_act(budge_code, update_data):
    # 这里是更新 Equipment_Act 数据库的逻辑
    client = MySQLClient()
    jg_start = "NULL" if update_data["JG_Start"] is None else f"'{update_data['JG_Start']}'"
    jg_finish = "NULL" if update_data["JG_Finish"] is None else f"'{update_data['JG_Finish']}'"

    update_sql = ["""
        update ${Equipment_Act}
        set JG_Code = '%s', 
            NAME = '%s', 
            JG_status = '%s', 
            JG_Start = %s, 
            JG_Finish = %s 
        where BUDGE_CODE = '%s'
    """ % (update_data["JG_Code"],
           update_data["NAME"],
           update_data["JG_status"],
           jg_start,
           jg_finish,
           budge_code)]


    client.exec_sqls(sqls=update_sql,table_info = {'Equipment_Act': {'elementName': 'Equipment_Act',
                                'elementType': 'DataTableMySQL',
                                'path': '/Datatable/Equipment/'}})

# 消费数据
# for message in consumer:
#     process_message(message)
#     print(message)
    # break

def main(p1, p2):
    # message = {"value":
    #     [
    #         {
    #             "CHANGEDATE": "2024-09-25 19:36:59",
    #             "PRJ_DATA_MAINT_NAME": "孙春亮",
    #             "FREEZEFLAG": "0",
    #             "VER": "0",
    #             "PRJ_L1_NAME": "专项项目",
    #             "M_BIZ_TYPE_NAME": "市政污水处理",
    #             "PRJ_INTRO": "3中堂长",
    #             "LASTUSERID": "wangwenxiao01",
    #             "PRJ_DATA_STAT_NAME": "01",
    #             "CHANGEUSERNAME": "王文啸",
    #             "ORGNAME": "北控水务（中国）投资有限公司",
    #             "PAID_TECH_CHG_TYPE": "调整水价/水量",
    #             "PK_MANAG_ORG": "1202842",
    #             "MS_PA": "sunchunliang",
    #             "LASTUSERNAME": "王文啸",
    #             "PK_CO_ORG": "0001D210000000000G5T",
    #             "BUDGE_CODE": "BJ2024400129",
    #             "M_FIR_BIZ_CODE": "01",
    #             "M_SEC_BIZ": "市政污水处理",
    #             "MDMSENDSTATUS": True,
    #             "CHANGEUSERID": "wangwenxiao01",
    #             "GROUP_AMOUNT_NEW": "36.0",
    #             "LEG_ORG_CODE": "040013",
    #             "IS_NT_REL_MAIN_BUS": "1",
    #             "PRJ_NAME": "3中堂长",
    #             "ORGID": "1540426",
    #             "PROJ_TYPE": "提标技改",
    #             "ORG_NAME": "东莞市中堂溢源污水处理厂",
    #             "IS_PAID": "1",
    #             "REL_PRJ_NAME": "广东东莞中堂镇污水处理厂一期-BOT",
    #             "PRJ_END_DATE": "2025-09-30",
    #             "M_SEC_BIZ_CODE": "0101",
    #             "M_FIR_BIZ": "污水",
    #             "PRJ_L2_NAME": "生产专项",
    #             "USE_FOR_BUSI": "1",
    #             "LEG_ORG_NAME": "东莞市中堂溢源水务有限公司",
    #             "REL_PRJ_CODE": "Y4420210035",
    #             "SYSID": "1727264198208864",
    #             "APPROVE_STATUS": "1",
    #             "LASTDATE": "2024-09-25 19:36:59",
    #             "ORG_CODE": "D004302",
    #             "BUDGE_STATUS": "1",
    #             "M_BIZ_TYPE_CODE": "010101",
    #             "PRJ_L3_NAME": "技改专项",
    #             "PRJ_CODE": "Z92024000033"
    #         },
    #         {
    #             "CHANGEDATE": "2024-09-25 20:52:37",
    #             "PRJ_DATA_MAINT_NAME": "孙春亮",
    #             "FREEZEFLAG": "0",
    #             "PRJ_START_DATE": "2024-09-25",
    #             "VER": "0",
    #             "PRJ_L1_NAME": "专项项目",
    #             "M_BIZ_TYPE_NAME": "市政污水处理",
    #             "PRJ_INTRO": "1小凌河北控测试预算",
    #             "LASTUSERID": "sunchunliang",
    #             "PRJ_DATA_STAT_NAME": "01",
    #             "CHANGEUSERNAME": "孙春亮",
    #             "ORGNAME": "北控水务（中国）投资有限公司",
    #             "PAID_TECH_CHG_TYPE": "调整水价/水量",
    #             "PK_MANAG_ORG": "1202420",
    #             "MS_PA": "sunchunliang",
    #             "LASTUSERNAME": "孙春亮",
    #             "PK_CO_ORG": "0001N6100000000041OJ",
    #             "BUDGE_CODE": "BJ2024400130",
    #             "M_FIR_BIZ_CODE": "01",
    #             "M_SEC_BIZ": "市政污水处理",
    #             "MDMSENDSTATUS": True,
    #             "CHANGEUSERID": "sunchunliang",
    #             "GROUP_AMOUNT_NEW": "23.0",
    #             "LEG_ORG_CODE": "040233",
    #             "IS_NT_REL_MAIN_BUS": "1",
    #             "PRJ_NAME": "1小凌河北控",
    #             "ORGID": "1540426",
    #             "PROJ_TYPE": "提标技改",
    #             "ORG_NAME": "锦州市北控联合污水处理厂",
    #             "PRJ_DATA_MAINT_CODE": "0001A41000000074DGQR",
    #             "IS_PAID": "1",
    #             "REL_PRJ_NAME": "辽宁锦州小凌河污水治理工程－TOT",
    #             "PRJ_END_DATE": "2025-09-30",
    #             "M_SEC_BIZ_CODE": "0101",
    #             "M_FIR_BIZ": "污水",
    #             "PRJ_L2_NAME": "生产专项",
    #             "USE_FOR_BUSI": "1",
    #             "LEG_ORG_NAME": "锦州市小凌河北控水务有限公司",
    #             "REL_PRJ_CODE": "Y2120210020",
    #             "SYSID": "1727268696313993",
    #             "APPROVE_STATUS": "1",
    #             "LASTDATE": "2024-09-25 20:52:37",
    #             "ORG_CODE": "D000013",
    #             "BUDGE_STATUS": "1",
    #             "M_BIZ_TYPE_CODE": "010101",
    #             "PRJ_L3_NAME": "技改专项",
    #             "PRJ_CODE": "Z92024000034"
    #         }
    #     ]
    # }
    # process_message(message)
    # 消费数据
    for message in consumer:
        process_message(message)



if __name__ == "__main__":
    # from conf._evn import p1, p2
    main(para1, para2)