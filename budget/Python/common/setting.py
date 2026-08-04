# 业务预算下发的kafka服务地址——业务预算UAT地址
kafka_setting_budget_uat = {
    'bootstrap_servers': [
        "alikafka-pre-cn-2r42hmobn01z-1-vpc.alikafka.aliyuncs.com:9092",
        "alikafka-pre-cn-2r42hmobn01z-2-vpc.alikafka.aliyuncs.com:9092",
        "alikafka-pre-cn-2r42hmobn01z-3-vpc.alikafka.aliyuncs.com:9092"
    ],

    # 'main_topic_name': 'source_mdms_bizbud_all',(增量)
    'main_topic_name': 'source_mdms_bizbud_inc',

    # 'sed_topic_name': 'detailed_budget_all', (全量)
    'sed_topic_name': 'detailed_budget_inc',
}


kafka_setting_prd = {
    'bootstrap_servers': [
        "alikafka-pre-cn-7mz2ue17v00n-1-vpc.alikafka.aliyuncs.com:9092",
        "alikafka-pre-cn-7mz2ue17v00n-2-vpc.alikafka.aliyuncs.com:9092",
        "alikafka-pre-cn-7mz2ue17v00n-3-vpc.alikafka.aliyuncs.com:9092",
    ],
    'topic_name': 'source_mdms_bizbud_inc',
    'main_topic_name': 'source_mdms_bizbud_inc',
    'sed_topic_name': 'detailed_budget_inc',
    # 'group_name': 'XXX'
}

# 主数据平台kafka服务地址UAT
kafka_setting_main = {
    'bootstrap_servers': [
        "alikafka-pre-cn-2r42hmobn01z-1-vpc.alikafka.aliyuncs.com:9092",
        "alikafka-pre-cn-2r42hmobn01z-2-vpc.alikafka.aliyuncs.com:9092",
        "alikafka-pre-cn-2r42hmobn01z-3-vpc.alikafka.aliyuncs.com:9092"
    ],
    # 'topic_name': 'mdms_xm_all',
    # 'group_name': 'XXX'
}



# 业务预算下发的kafka服务地址——主数据的test地址
kafka_setting_budget_test = {
    'bootstrap_servers': [
        "alikafka-pre-cn-7mz2cn5pt00q-1-vpc.alikafka.aliyuncs.com:9092",
        "alikafka-pre-cn-7mz2cn5pt00q-2-vpc.alikafka.aliyuncs.com:9092",
        "alikafka-pre-cn-7mz2cn5pt00q-3-vpc.alikafka.aliyuncs.com:9092",
    ],
    'topic_name': 'source_mdms_bizbud_inc',
}

# 主数据平台kafka服务地址UAT
kafka_setting_main_test = {
    'bootstrap_servers': [
        "alikafka-pre-cn-7mz2cn5pt00q-1-vpc.alikafka.aliyuncs.com:9092",
        "alikafka-pre-cn-7mz2cn5pt00q-2-vpc.alikafka.aliyuncs.com:9092",
        "alikafka-pre-cn-7mz2cn5pt00q-3-vpc.alikafka.aliyuncs.com:9092",
    ],
    # 'topic_name': 'mdms_xm_all',
    # 'group_name': 'XXX'
}



