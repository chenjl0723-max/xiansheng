# -*- coding: utf-8 -*-
'''
@file    : HR_MID_CUBE.py
@Time    :
@Author  : JI
@Software: PyCharm
@Desc    : hanrui需求-py处理源表数据进人力预算模型
'''
from pandas import DataFrame

try:
    from CWYS._debug import para1, para2
    # print(para1)
except ImportError:
    para1 = para2 = {}
from deepfos.options import OPTION
import pandas as pd
from datetime import datetime
import traceback
import time
import os
from deepfos.db.mysql import MySQLClient
from deepfos.element.datatable import DataTableClickHouse
from deepfos.element.finmodel import FinancialCube
from deepfos.element.datatable import DataTableClickHouse as ck
from deepfos.element.datatable import DataTableMySQL
from deepfos.element.variable import Variable
from deepfos.element.dimension import Dimension, DimMember
from deepfos.element.pyscript import PythonScript
import numpy as np


# from _debug import p1, p2

def hr_processing(p1, p2):
    # 获取人力预算预算数据
    # 获取人力预算预算数据
    HR_dt = DataTableMySQL('budget_data_HR_MID')
    Version = Variable('Variable').get('Edit_Ver')
    cols = ['Year', 'Period', 'Scenario', 'Account_HR_cd', 'figure', 'Explan', 'Entity_GL', 'comprehensive']

    # where = "Account_HR_cd != 'YW0901'"
    HR_df = HR_dt.select(columns=cols).copy()
    HR_df.rename(
        columns={
            'Account_HR_cd': 'Account_HR',
            # 'figure': 'decimal_val',
            'comprehensive': 'Comprehensive',
            'Explan': 'Explan'},
        inplace=True
    )

    # 源表的 Entity_GL 字段
    # HR_df['Entity_GL'] = HR_dt['Entity_GL'].apply(lambda x: f"XN_{x}")
    HR_df['Entity_GL'] = HR_df['Entity_GL'].astype(str).str.replace(r'[;,\(\)\[\]]', '', regex=True)
    # HR_df['Entity_HR'] = HR_df['Entity_GL']
    HR_df.rename(columns={'Entity_GL': 'Entity_HR'}, inplace=True)

    # 场景1：源表有 comprehensive 列，直接写入
    HR_df['Comprehensive'] = HR_df['Comprehensive'].fillna('Staff_Classification')
    # 校验：确保科目编码无空值，过滤非最末级（如果有层级字段可进一步过滤）
    df = HR_df[HR_df['Account_HR'].notna()]

    df['Version'] = Version
    df['Misc1'] = 'Nomisc1'
    df['Misc2'] = 'Nomisc2'

    return df


def push_processing(df):
    # 写入模型
    # 1. 连接人力预算模型
    cube = FinancialCube('HR_Cube')
    Version = Variable('Variable').get('Edit_Ver')
    # df['Entity_HR'] = df['Entity_HR'].astype(str).str.replace(r'[;,\(\)\[\]]', '', regex=True)
    # df['Entity_GL'] = df['Entity_GL'].astype(str).str.replace(r'[;,\(\)\[\]]', '', regex=True)

    # 2. 定义写入维度范围
    expr_dict = {
        "Year": df['Year'].unique().tolist(),
        "Scenario": df['Scenario'].unique().tolist(),
        "Entity_HR": df['Entity_HR'].unique().tolist(),
        "Account_HR": df['Account_HR'].unique().tolist(),
        "Comprehensive": df['Comprehensive'].unique().tolist(),
        "Version": Version
    }

    # 3. 先清空对应区域，避免旧数据残留
    cube.insert_null(expr_dict)

    # 4. 写入数据（金额、变动说明分别对应维度）
    # 方式1：按Measure拆分成两行写入（更标准）
    df_expenses = df.rename(columns={'figure': 'data'})
    df_expenses['Measure'] = 'Expenses'

    df_explain = df.rename(columns={'Explan': 'data'})
    df_explain['Measure'] = 'Explain'

    # 合并后写入
    df_write = pd.concat([df_expenses, df_explain], ignore_index=True)
    df_write = df_write.dropna(axis=0, subset=['data'], how="any")

    # ************************************************************************
    # 过滤不需要的科目
    com_dim = Dimension('Comprehensive', path="/02_Dimension")
    com_list = pd.DataFrame(com_dim.query(expression="Base(#root,0)", fields=['name'], as_model=False))
    df_write = df_write[df_write['Comprehensive'].isin(com_list['name'])]

    # ************************************************************************
    del df_write['figure']
    del df_write['Explan']
    entity_dim = Dimension('Entity_HR')
    com_pd = pd.DataFrame(entity_dim.query(expression="Base(#root,0)", fields=['name'], as_model=False))
    df_res = df_write[df_write['Entity_HR'].isin(com_pd['name'])]

    cube.save(df_res)


def main(p1, p2):
    # # 写入财务预算分析模型

    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    countAll = 0
    countSuccess = 0
    countError = 0
    countMsg = f"{start_time} 开始执行处理源表数据进人力预算模型任务\n"

    try:
        # 公共层应用
        hr_budget_data = hr_processing(p1, p2)

        # 写入财务预算分析模型
        push_processing(hr_budget_data)
        countSuccess = 1
        countAll = 1
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 处理源表数据进人力预算模型处理完成\n"

    except Exception as e:
        countError = 1
        countAll = 1
        error_detail = traceback.format_exc()
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 处理源表数据进人力预算模型失败: {str(e)}\n"
        countMsg += f"详细错误信息:\n{error_detail}\n"
        print(f"处理源表数据进人力预算模型执行出错: {e}")
        traceback.print_exc()

    # ====================== 写入日志 ======================
    ele_name = os.path.basename(__file__)
    ele_path = os.path.dirname(os.path.abspath(__file__))
    # print(ele_name)
    # print(ele_path)

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


if __name__ == '__main__':
    # entity_dim = Dimension('Entity_HR')
    # com_list = pd.DataFrame(entity_dim.query(expression="Base(#root,0)", fields=['name'], as_model=False))
    # print(com_list['name'])
    main(para1, para2)

"""
源表：budget_data_HR_MID
目标：HR_Cube
"""
