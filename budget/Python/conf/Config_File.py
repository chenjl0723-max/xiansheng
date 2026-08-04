# -*- coding: utf-8 -*-
'''
@file    : Config_File.py
@Time    :
@Author  : XMX
@Software: PyCharm
@Desc    : 北控水务 参数配置文件 接口的url需要关注测试和生产环境的切换
'''

# 钉钉发消息
config_dingding = {
    # # 钉钉测试环境
    # "SysCode": "T0038",
    # "url": "http://10.10.20.82:8080/message/service?wsdl",
    # 钉钉生产环境
    "SysCode": "T0074",
    # "url": "http://10.10.2.85:8080/message/service?wsdl"
    # 切换域名 20221114
    "url": "http://msg.bewg.net.cn:8080/message/service?wsdl"
}
# 公共
config_common = {
    # # 预算开发环境
    # # 根据角色 / 角色组查询当前权限方案中匹配的用户
    # "url_roles": "http://budget-test.bewg.net.cn/deepfos-server/role-strategy-server1-0/get-users-by-roles",
    # "url_asy": "http://budget-test.bewg.net.cn/deepfos-server/python-server2-0/script/run"

    # # 预算UAT环境
    # # 根据角色 / 角色组查询当前权限方案中匹配的用户
    # "url_roles": "http://budget-uat.bewg.net.cn/deepfos-server/role-strategy-server1-0/get-users-by-roles",
    # "url_asy": "http://budget-uat.bewg.net.cn/deepfos-server/python-server2-0/script/run"

    # 预算生产环境
    # 根据角色 / 角色组查询当前权限方案中匹配的用户
    "url_roles": "https://planning.bewg.net.cn/deepfos-server/role-strategy-server1-0/get-users-by-roles",
    "url_asy": "https://planning.bewg.net.cn/deepfos-server/python-server2-0/script/run"
}
