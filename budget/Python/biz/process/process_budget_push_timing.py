# -*- coding: utf-8 -*-
'''
@file    : process_budget_push_timing.py
@Time    :
@Author  : XMX
@Software: PyCharm
@Desc    : 北控水务 预算数推送接口 定时推送全量最新版到预算数据中间表 Y1 每次全量覆盖
           暂不考虑历史数据问题，预算数据表每年预算编制开始前，做初始化动作
'''
try:
    from _debug import para1, para2
    # print(para1)
except ImportError:
    para1 = para2 = {}

import traceback
import pandas as pd
import requests
import json
from deepfos.element.datatable import DataTableClickHouse as ck
from deepfos.element.variable import Variable
from .process_budget_push import main as push
from budget_push.conf import Config_File as cf

# from _debug import p1, p2


def call_asy(p1):
    url = cf.config_common['url_asy']
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
        "app": p1['app'],
        "space": p1['space'],
        "user": p1['user'],
        "cookie": p1['cookie'],
        "language": "zh-cn"
    }

    body = {
        "elementName": "process_budget_push_timing_save_his",
        "elementType": "PY",
        "path": "/Python_prd/biz/process",
        "parameter": ''
    }

    response = requests.post(url, headers=headers, json=body)
    responsejson = json.loads(response.text)
    print(responsejson)


def main(p1, p2):
    if "folderId" in p2:
        del p2['folderId']
    if "elementName" in p2:
        del p2['elementName']
    try:
        # 初始化
        table = ck('bewg_budget_data')
        # # 获取系统变量 预算编制年
        # variable = Variable(element_name='Variable', path='/Variable')
        # Year = variable.get('BudYear')
        # 先全量删除 版本数据
        d = table.delete({"Version_Info": "Y1"})
        print("删除", d)
        # 默认值
        df_check = pd.DataFrame(['不为空'])
        # 默认值 Y1 全量 组织、部门
        p2 = {"Version": "Y1", "Entity": "Base(#root,0)", "Department": "Base(#root,0)"}

        push(p1, p2, df_check)
        print("Y1最新版数据已推送至预算数据中间表")
        print(df_check)
        # 异步调用保存历史数据接口
        call_asy(p1)
    except Exception as e:
        traceback.print_exc()


# debug
if __name__ == '__main__':
    # p1 = {}
    main(para1, para2)


