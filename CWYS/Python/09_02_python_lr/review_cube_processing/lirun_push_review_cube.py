# -*- coding: utf-8 -*-
'''
@file    : lirun_push_review_cube.py
@Desc    : 实际数进 rev_profit_cube 财务模型 - 按图片字段映射
'''

try:
    from CWYS._debug import para1, para2
except ImportError:
    para1 = para2 = {}

import pandas as pd
import traceback
import time
import os
from datetime import datetime

from deepfos.element.datatable import DataTableMySQL
from deepfos.element.finmodel import FinancialCube
from deepfos.element.variable import Variable
from deepfos.element.dimension import Dimension
from deepfos.element.pyscript import PythonScript


def add_inc_stock(df):
    inc_stock_dt =  DataTableMySQL('project_public_data_Year')

    inc_stock_df = inc_stock_dt.select(columns=['project_cd','inc_ext_idtf','Version','Year']).rename(columns={'inc_ext_idtf':'inc_stock','project_cd':'Entity_GL'})

    df = df.merge(inc_stock_df, how='left', on=['Entity_GL','Version','Year'])

    # df = df.dropna(subset=['inc_stock'])

    return df
def actual_processing(p1, p2,Version,Year,cube):
    """实际数主处理函数"""
    year = str(int(Year) - 1)

    # cube = FinancialCube('sub_profit_cube')
    fix  = "Year{%s}->Scenario{Actual}->Version{%s}->Period{Base(TotalPeriod,0);Noperiod}->Comprehensive{NoTax}->" \
               "Entity_GL{Base(#root,0)}->Measure{Expenses;Explain;Remarks;Rate}->Account_lirun{Base(PL60,0)}->"\
               "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                % (year,Version)

    actual_df = cube.query(fix, compact=False)

    dim_GL = Dimension('Entity_GL')
    df_GL = pd.DataFrame(dim_GL.query(expression="Base(#root,0)", fields=['name','ud8','ud10'], as_model=False)).drop(['id','expectedName'],axis=1)

    actual_df =  actual_df.merge(df_GL.rename(columns={
        'name':'Entity_GL',
        # 'ud4':'inc_stock',
        'ud8':'Project_Type',
        'ud10':'Pattern'})
        , how='left', on='Entity_GL').drop(['Comprehensive'],axis=1)

    actual_df = add_inc_stock(actual_df)
    push_to_cube(actual_df, year, Version,'Actual')


def forecast_processing(p1, p2,Version,Year,cube):
    """预测数主处理函数"""
    year = str(int(Year) - 1)

    # cube = FinancialCube('sub_profit_cube')
    fix  = "Year{%s}->Scenario{Forecast}->Version{%s}->Period{Base(TotalPeriod,0);Noperiod}->Comprehensive{NoTax}->" \
               "Entity_GL{Base(#root,0)}->Measure{Expenses;Explain;Remarks;Rate}->Account_lirun{Descendant(PL60,0)}->"\
               "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                % (year,Version)

    forecast_df = cube.query(fix, compact=False)

    dim_GL = Dimension('Entity_GL')
    df_GL = pd.DataFrame(dim_GL.query(expression="Base(#root,0)", fields=['name','ud8','ud10'], as_model=False)).drop(['id','expectedName'],axis=1)

    forecast_df =  forecast_df.merge(df_GL.rename(columns={
        'name':'Entity_GL',
        'ud8':'Project_Type',
        'ud10':'Pattern'})
        , how='left', on='Entity_GL').drop(['Comprehensive'],axis=1)

    forecast_df= add_inc_stock(forecast_df)
    push_to_cube(forecast_df, year, Version,'Forecast')


def budget_processing(p1, p2,Version,Year,cube):
    """预算数主处理函数"""

    # cube = FinancialCube('sub_profit_cube')
    fix  = "Year{%s}->Scenario{Budget}->Version{%s}->Period{Base(TotalPeriod,0);Noperiod}->Comprehensive{NoTax}->" \
               "Entity_GL{Base(#root,0)}->Measure{Expenses;Explain;Remarks;Rate}->Account_lirun{Descendant(PL60,0)}->"\
               "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                % (Year,Version)

    budget_df = cube.query(fix, compact=False)

    dim_GL = Dimension('Entity_GL')
    df_GL = pd.DataFrame(dim_GL.query(expression="Base(#root,0)", fields=['name','ud8','ud10'], as_model=False)).drop(['id','expectedName'],axis=1)

    budget_df =  budget_df.merge(df_GL.rename(columns={
        'name':'Entity_GL',
        'ud8':'Project_Type',
        'ud10':'Pattern'})
        , how='left', on='Entity_GL').drop(['Comprehensive'],axis=1)

    budget_df = add_inc_stock(budget_df)
    push_to_cube(budget_df, Year, Version,'Budget')

def push_to_cube(df, year, Version,Scenario):
    """推送数据到 rev_profit_cube"""

    # 1. 过滤维度中存在的成员
    entity_dim = Dimension('Entity_GL')
    entity_list = pd.DataFrame(entity_dim.query("Base(#root,0)", fields=['name'], as_model=False))
    df = df[df['Entity_GL'].isin(entity_list['name'].tolist())]

    account_dim = Dimension('Account_lirun')
    account_list = pd.DataFrame(account_dim.query("Descendant(#root,0)", fields=['name'], as_model=False))
    df = df[df['Account_lirun'].isin(account_list['name'].tolist())]

    # 过滤关键字段为空的行
    df = df[
        (df['Commercial'].notna()) & (df['Commercial'] != '') &
        (df['Project_Type'].notna()) & (df['Project_Type'] != '') &
        (df['Pattern'].notna()) & (df['Pattern'] != '') &
        (df['inc_stock'].notna()) & (df['inc_stock'] != '')
    ]

    # df['Misc2'] = df['Misc2'].fillna('')

    # 4. 写入 Cube
    cube = FinancialCube('rev_profit_cube')

    # 清空对应位置（推荐做法）
    expr_dict = {
        "Year": year,
        "Scenario": Scenario,
        "Entity_GL": "IDescendant(#root,0)",
        "Account_lirun": "IDescendant(#root,0)",
        "Period":['1','2','3','4','5','6','7','8','9','10','11','12','Noperiod'],
        "Version": Version,
    }
    cube.insert_null(expr_dict)

    # 保存数据
    cube.save(df, chunksize=200000)




def main(p1, p2):
    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    countAll = countSuccess = countError = 0
    countMsg = f"{start_time} 开始执行实际数接入审核模型 rev_profit_cube 任务\n"

    try:
        # 统一获取全局参数
        Version = Variable('Variable').get('Edit_Ver')

        if 'Year' in p2 and p2['Year']:
            Year = str(p2['Year'])
        else:
            Year = Variable('Variable').get('BudYear')

        cube = FinancialCube('sub_profit_cube')
        actual_processing(p1, p2, Version, Year,cube)
        forecast_processing(p1, p2, Version, Year,cube)
        budget_processing(p1, p2, Version, Year,cube)
        countAll = countSuccess = 1
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 实际数接入处理完成\n"
    except Exception as e:
        countError = 1
        countAll = 1
        error_detail = traceback.format_exc()
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 实际数接入失败: {str(e)}\n"
        countMsg += f"详细错误:\n{error_detail}\n"
        print(f"执行出错: {e}")
        traceback.print_exc()

    # ====================== 写入日志 ======================
    ele_name = os.path.basename(__file__)
    ele_path = os.path.dirname(os.path.abspath(__file__))

    try:
        sync_log = PythonScript(element_name='pyLog', path='/09_Python/common', should_log=True)
        sync_log.run(
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
        print("日志记录成功！")
    except Exception as log_e:
        print(f"日志记录异常: {log_e}")

    return countError == 0


# ==================== 本地调试 ====================
if __name__ == '__main__':
    para2 = {'Year': '2026'}  # 修改这里可测试不同年份
    main(para1, para2)