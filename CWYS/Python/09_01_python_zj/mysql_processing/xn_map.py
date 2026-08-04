# -*- coding: utf-8 -*-
'''
@file    : xn_map.py
@Time    :
@Author  : CHEN
@Software: PyCharm
@Desc    : 虚拟项目进入虚拟项目映射表
'''


try:
    from CWYS._debug import para1, para2
    # print(para1)
except ImportError:
    para1 = para2 = {}
from deepfos.options import OPTION
import pandas as pd
import traceback
import time
import os
from datetime import datetime
from deepfos.db.mysql import MySQLClient
from deepfos.element.datatable import DataTableClickHouse
from deepfos.element.finmodel import FinancialCube
from deepfos.element.datatable import DataTableClickHouse as ck
from deepfos.element.datatable import DataTableMySQL
from deepfos.element.variable import Variable
from deepfos.element.dimension import Dimension, DimMember
from deepfos.element.pyscript import PythonScript
import numpy as np



def main_processing(p1,p2):
    Year = Variable('Variable').get('BudYear')
    source_dt = DataTableMySQL('pl_virt_proj_list')
    target_dt = DataTableMySQL('pl_virt_proj_fund_real_map')
    source_df =  source_dt.select(
        columns=['pl_virt_proj_code',
                'pl_virt_proj_name',
                'area_code',
                'area_name',
                'region_code',
                'region_name'])

    source_df['year'] = Year
    target_dt.insert_df(source_df,updatecol=['pl_virt_proj_name','area_code','area_name','region_code','region_name'])
    print(1)



def main(p1, p2):
    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    countAll = 0
    countSuccess = 0
    countError = 0
    countMsg = f"{start_time} 开始执行利润虚拟项目同步任务\n"

    try:
        main_processing(p1, p2)
        countSuccess = 1
        countAll = 1
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 利润虚拟项目同步处理完成\n"

    except Exception as e:
        countError = 1
        countAll = 1
        error_detail = traceback.format_exc()
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 利润虚拟项目同步失败: {str(e)}\n"
        countMsg += f"详细错误信息:\n{error_detail}\n"
        print(f"利润虚拟项目同步执行出错: {e}")
        traceback.print_exc()

    # ====================== 写入日志 ======================
    ele_name = os.path.basename(__file__)
    ele_path = os.path.dirname(os.path.abspath(__file__))

    try:
        sync_log = PythonScript(element_name='pyLog', path='/09_Python/common', should_log=True)
        sync_result = sync_log.run(
            parameter={
                'ele_name': ele_name,
                'ele_path': ele_path,
                'data_count': countAll,
                'error_count': countError,
                'logs': countMsg,
                'dt': datetime.now().strftime('%Y%m%d'),
                'start_time': start_time,
                'exe_parameter': str(p2)
            }
        )
        if sync_result:
            print("日志记录成功！")
        else:
            print("日志记录失败！")
    except Exception as log_e:
        print(f"日志记录异常: {log_e}")

    # 返回执行结果（与维度脚本保持一致）
    return False if countError > 0 else True



# debug
if __name__ == '__main__':
    para2 = {'Year':'2025'}
    main(para1, para2)
