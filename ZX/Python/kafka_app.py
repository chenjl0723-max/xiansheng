"""
added by cjl
added in 20260702
added for 数字化专线预算下发主数据脚本
主要逻辑：
    读取SZH_zx cube中的预算信息，关联Application_sys_01维度和bs_project_szh_wh维度获取中文名与应用状态
    往主数据的kafka上做下发，同时写入中间表（XZH_Budget_Middle_Table）.

"""


try:
    from ZX._debug import para1, para2
    # print(para1)
except ImportError:
    para1 = para2 = {}

import kafka

print("Kafka 版本:", kafka.__version__)

from deepfos.element.datatable import DataTableMySQL
from deepfos.element.finmodel import FinancialCube
from deepfos.element.variable import Variable
from deepfos.element.dimension import Dimension
from deepfos.element.pyscript import PythonScript


import json
from kafka import KafkaProducer
from deepfos.api.space import SpaceAPI
import pandas as pd
import traceback
import time
import os
from datetime import datetime
from budget.Python.common import setting

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


        # 从p2中提取所需参数
        self.year_id_singleh = p2.get('Year')

        # 获取p2 rows里的app_code

        self.app_code = [row['app_code'] for row in p2.get('rows', [])]
        self.bs_proj_name = [row['bs_proj_name'] for row in p2.get('rows', [])]




        app_dim = Dimension('Application_sys_01')
        self.app_df = pd.DataFrame(app_dim.query(expression="Base(#root,0)", fields=['name', 'description_zh_cn', 'ud3'], as_model=False)).drop(columns=['id','expectedName'],axis=1).rename(columns={'name':'app_code','description_zh_cn':'app_name','ud3':'app_Status'})
        bs_project_dim = Dimension('bs_project_szh_wh')
        self.bs_project_df = pd.DataFrame(bs_project_dim.query(expression="Base(#root,0)", fields=['name', 'description_zh_cn'], as_model=False)).drop(columns=['id','expectedName'],axis=1).rename(columns={'name':'bs_proj_name','description_zh_cn':'Name'})


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
        exp = "Scenario{NoScenario}->Budget_account{PL1002}->bs_proj_name{%s}->app_code{%s}" % (
                ';'.join(self.bs_proj_name),';'.join(self.app_code))

        # 初始化财务模型
        cube = FinancialCube('SZH_zx')
        # dims = cube.col_dim_map
        df = cube.query(expression=exp,compact=False).drop(columns=['types','Entity_Sp','Version','Application_sys_01','data_type','Scenario','Budget_account'])
        df = df.merge(self.app_df, how='left', on='app_code')
        df = df.merge(self.bs_project_df, how='left', on='bs_proj_name')
        df = df.rename(columns={
            # 'data':'GROUP_AMOUNT_NEW',
            'bs_proj_name':'BUDGE_CODE',
        })

        # 确保 Year 列是字符串类型以便比较
        df['Year'] = df['Year'].astype(str)
        # 筛选出指定年份的数据
        df_year = df[df['Year'] == self.year_id_singleh].copy()
        # 按 BUDGE_CODE 分组汇总
        group_amount_new = df_year.groupby('BUDGE_CODE')['data'].sum().reset_index()
        group_amount_new = group_amount_new.rename(columns={'data': 'GROUP_AMOUNT_NEW'})
        # 合并回原数据框
        df_year = df_year.merge(group_amount_new, on='BUDGE_CODE', how='left')


        # 计算所有年份的汇总金额
        tot_budg_amt = df.groupby('BUDGE_CODE')['data'].sum().reset_index()
        tot_budg_amt = tot_budg_amt.rename(columns={'data': 'TOT_BUDG_AMT'})

        # 保留预算年，的预算信息（包含当前年汇总金额和所有年汇总金额）
        df_year = df_year.merge(tot_budg_amt, on='BUDGE_CODE', how='left')

        df_year.drop(columns=['data'],inplace=True)


        df_year['BUDGE_TYPE'] = '020402'


        print(df_year)

        # 根据需求补列
        df_year['BUDGE_STATUS'] = '1'
        df_year['APPROVE_STATUS'] = '1'
        df_year['PUSHFLAG'] = '1'
        df_year['PUSHTIME'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        df_year['FREEZEFLAG'] = '0'
        df_year['CHANGEDATE'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        df_year['CHANGEUSERNAME'] = None
        df_year['ORGNAME'] = None
        df_year['ORGID'] = None
        df_year['CHANGEUSERID'] = 'admin'
        df_year['LASTUSERID'] = 'admin'
        df_year['LASTUSERNAME'] = None
        df_year['LASTDATE'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        df_year['SYSID'] = ''


        print(df_year)

        df_json = df_year.to_json(orient='records', force_ascii=False)
        df_json = json.loads(df_json)
# 因为 `DataFrame.to_json()` 方法返回的是一个 JSON 格式的字符串。
        # 参数 `orient='records'` 指定了输出格式为记录数组，`force_ascii=False` 允许非 ASCII 字符。
        # 这个字符串包含了 DataFrame `df_year` 中所有数据的 JSON 表示。
        # 如果需要 Python 对象（如列表或字典），可以使用 `json.loads(df_json)` 进行反序列化。



        df_middle = df_year.copy()
        updatecol = list(set(df_middle.columns) - {"Year","BUDGE_CODE"})
        self.Budget_Production_Middle_Table.insert_df(df_middle, updatecol)

        print("预算数据处理完成。")
        print("发送主数据信息为：",df_year)
        return df_json




class KafkaBudgetSender:
    def __init__(self):
        # 初始化两个 Kafka Producer，一个用于 main_data，一个用于 sed_data
        self.producer = KafkaProducer(
            bootstrap_servers=setting.kafka_setting_budget_uat['bootstrap_servers'],
            value_serializer=lambda v: json.dumps(v).encode('utf-8')
        )

    def send_to_kafka(self, main_data):
        # 发送 main_data 到主预算 Kafka 主题
        if main_data:
            print(f'发送 {len(main_data)} 条主预算数据')
            for message in main_data:
                data = [message]
                future = self.producer.send(setting.kafka_setting_budget_uat['main_topic_name'], value=data)
                future.add_callback(lambda record_metadata: self.delivery_report(None, record_metadata, 'main'))
                future.add_errback(lambda exc: self.delivery_report(exc, None, 'main'))
            self.producer.flush()



    @staticmethod
    def delivery_report(error, record_metadata, data_type):
        if error is not None:
            print(f"{data_type} 消息发送失败: {error}")
        else:
            print(f"{data_type} 消息成功发送到 {record_metadata.topic} [分区 {record_metadata.partition}]")


def main(p1, p2):
# 判断条件

    if 'Year' not in p2  or p2['target_status'] != 'Status08':
        print(f"条件不满足: 缺少Year年份' 且 target_status 需要是 Status08。")
        return


    processor = BudgetDataProcessor(p1, p2)
    main_data = processor.process_budget_data()

    sender = KafkaBudgetSender()
    sender.send_to_kafka(main_data)



if __name__ == "__main__":
    p2 = {'Year': '2027', 'target_status': 'Status08', 'rows': [{'app_code': 'LCSZH0148', 'bs_proj_name': 'XX240001'}, {'app_code': 'LCSZH0089', 'bs_proj_name': 'Z92025001909'}]}
    main(para1, p2)


