# '经营计划的项目信息通过kafka数据接入'
try:
    from _debug import para1, para2
    # print(para1)
except ImportError:
    para1 = para2 = {}

from kafka import KafkaConsumer
from kafka_main.conf import setting
from kafka_main.common import commons
from deepfos.db.mysql import MySQLClient
from deepfos.element.datatable import DataTableMySQL
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
conf = setting.kafka_setting_main
employ_table = DataTableMySQL("mdms_employ")

# 初始化 KafkaConsumer
consumer = KafkaConsumer(
    'mdms_employ_inc',
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
        json_data_list = json.loads(message.value)
        print(f"Received {len(json_data_list)} records in a single message.")

        print(json_data_list)

        # 将 JSON 数据列表转换为 DataFrame
        df_new = pd.json_normalize(json_data_list)


        df_new.to_csv('mdms_employ_all.csv')

        # 检查并转换日期字段
        date_fields = ['ENTER_BEWG_DATE', 'ENTRY_DATE', 'EXPECTED_DEPARTURE_DATE', 'ACTUAL_DEPARTURE_DATE',
                       'CHANGEDATE', 'LASTDATE']
        for field in date_fields:
            if field in df_new.columns:
                try:
                    df_new[field] = pd.to_datetime(df_new[field], errors='coerce')
                except Exception as e:
                    print(f"日期转换失败: {e}")

        # print(df_new.dtypes)
                # Convert boolean columns to strings
                    # Convert boolean columns to strings
        boolean_columns = df_new.select_dtypes(include=['bool']).columns
        for col in boolean_columns:
            df_new[col] = df_new[col].astype(str)

        # Remove unwanted columns
        if "MDMSENDSTATUS" in df_new.columns:
            df = df_new.drop(columns=["MDMSENDSTATUS"])

        # Prepare columns for insertion
        updatecol = list(set(df.columns) - {"PK_EMPLOY", "USER_CODE", "PK_ORG"})
        try:
            if "PK_EMPLOY" in df.columns and "USER_CODE" in df.columns and "PK_ORG" in df.columns:
                employ_table.insert_df(df, updatecol)
            print(f"成功插入数据到数据库，行数: {len(df)}")
        except Exception as e:
            print(f"数据插入失败: {e}")

    except json.JSONDecodeError as e:
        print(f"JSON解析失败: {e}")
    except Exception as e:
        print(f"数据处理失败: {e}")

        # if "PK_EMPLOY" in df_new.columns and "USER_CODE" in df_new.columns and "PK_ORG" in df_new.columns:
        #     updatecol = list(set(df_new.columns.drop(["PK_EMPLOY", "USER_CODE", "PK_ORG"])))
        #     employ_table.insert_df(df_new, updatecol)



        # # 从数据库中获取现有的 PK_EMPLOY
        # existing_records = commons.rdb_.select(None, "mdms_employ", path="/Datatable/Master_Data/")
        # existing_pk = existing_records['PK_EMPLOY'].tolist()
        #
        # # 分别处理插入和更新的数据
        # new_records = df_new[~df_new['PK_EMPLOY'].isin(existing_pk)]  # 不存在的插入
        # update_records = df_new[df_new['PK_EMPLOY'].isin(existing_pk)]  # 已存在的更新
        #
        # try:
        #     # 插入新数据
        #     if not new_records.empty:
        #         commons.rdb_.insert_sql(tbl="mdms_employ", data=new_records, path="/Datatable/Master_Data/")
        #         print(f"成功插入新数据到数据库，行数: {len(new_records)}")
        #
        #     # 更新已存在的数据
        #     if not update_records.empty:
        #         commons.rdb_.update_sql(tbl="mdms_employ", data=update_records, path="/Datatable/Master_Data/")
        #         print(f"成功更新已存在的数据，行数: {len(update_records)}")
        #
        # except Exception as e:
        #     print(f"数据插入/更新失败: {e}")




# 消费数据
for message in consumer:
    process_message(message)
    # break