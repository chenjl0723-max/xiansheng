"""
 config_kafka 用于定义物料主数据同步接口相关信息，发布到UAT、生产环境需要调整这里的相关属性
 group_id_ws:污水二期
 group_id_jy:经营计划
"""
config_kafka = {
    "group_id_ws": "T0080",
    "group_id_jy": "T0102",
    "bootstrap_servers": [
        "alikafka-pre-cn-sco3vox9b006-1-vpc.alikafka.aliyuncs.com:9092",
        "alikafka-pre-cn-sco3vox9b006-2-vpc.alikafka.aliyuncs.com:9092",
        "alikafka-pre-cn-sco3vox9b006-3-vpc.alikafka.aliyuncs.com:9092",
    ],
}

# cube名称
cube = "BEWG"
# 操作cube的fix字符串，后续根据需要传参即可
dim_list = "Entity{%s}->Material{%s}->Account{%s}"

# 涉及到操作的业务表名

# 增量计划、建设期项目、低效计划等的Scenario取值范围
key_map = {
    "1": "Q4",
    "2": "Q4",
    "3": "Q4",
    "4": "Q1",
    "5": "Q1",
    "6": "Q1",
    "7": "Q2;Year",
    "8": "Q2;Year",
    "9": "Q2;Year",
    "10": "Q3",
    "11": "Q3",
    "12": "Q3",
}

# p1参数里经营计划的app编码
app_name_source = 'dzsicw005'
