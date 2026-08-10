# -*- coding: utf-8 -*-
'''
@file    : cesuan_push_zijin.py
@Desc    : 财务测算进资金预算
'''

try:
    from CWYS._debug import para1, para2
except ImportError:
    para1 = para2 = {}

import pandas as pd
import traceback
import time
import os
import json
from datetime import datetime

from deepfos.element.datatable import DataTableMySQL
from deepfos.element.finmodel import FinancialCube
from deepfos.element.variable import Variable
from deepfos.element.dimension import Dimension
from deepfos.element.pyscript import PythonScript



def main_processing(p1, p2,Version,Year,cube):

    # 获取预测数场景筛选条件
    pov = {'Scenario':'Forecast','Period':['10','11','12']}
    df_forecast = query_CS_cube(pov,str(int(Year) - 1), Version, cube)

    # 获取预测数场景删除条件
    del_zijin_cube(pov,'Forecast',str(int(Year) - 1),Version)

    # 预测数科目映射+虚拟项目映射+汇总+写入资金模型
    df_forecast = mapping_and_group(df_forecast)
    push_to_cube(df_forecast,'Forecast')

    # 获取预算数场景筛选条件
    pov = {'Scenario': 'Budget', 'Period': ['1','2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']}
    df_budget = query_CS_cube(pov,Year, Version, cube)

    # 获取预算数场景删除条件
    del_zijin_cube(pov,'budget_adjb',Year,Version)

    # 预算数科目映射+虚拟项目映射+汇总+写入资金模型
    df_budget = mapping_and_group(df_budget)
    push_to_cube(df_budget,'budget_adjb')






def query_CS_cube(pov,Year,Version,cube):

    # Account_lirun =  ';'.join(pov.get('CW_CS_Account'))
    Scenario =  pov.get('Scenario')
    Period =  ';'.join(pov.get('Period'))

    pov_list = [{'Measure':'Expenses','CW_CS_Account':'TK_Expenses'},{'Measure':'Adjusted_Expenses','CW_CS_Account':'HK_Expenses'},{'Measure':'Expenses','CW_CS_Account':'Int_Amt_ZJ'}]
    df_all = pd.DataFrame()
    for pov in pov_list:
        fix = "Year{%s}->Version{%s}->" \
              "Entity_FR{Base(#root,0)}->" \
              "Scenario{%s}->Period{%s}"\
        %(Year, Version,Scenario, Period)
        df = cube.query(expression=fix, pov=pov,compact=False)
        if not df.empty:
            df_all = pd.concat([df_all,df],ignore_index=True)

    return df_all

def del_zijin_cube(pov,Scenario,Year,Version):
    cube = FinancialCube('sub_fund_cube')
    # Scenario = pov.get('Scenario')
    Period = ';'.join(pov.get('Period'))

    fix = "Year{%s}->Version{%s}->Account_zijin{CF020301;CF030401;CF030501}->" \
          "Entity_FR{Base(#root,0)}->Measure{Expenses}->" \
          "Scenario{%s}->Period{%s}"\
    %(Year, Version,Scenario, Period)
    cube.delete(expression=fix)




def mapping_and_group(df):

    # 定义替换映射字典
    replace_dict = {
        'TK_Expenses': 'CF020301',
        'HK_Expenses': 'CF030401',
        'Int_Amt_ZJ': 'CF030501'
    }
    # 对CW_CS_Account列进行替换
    df['CW_CS_Account'] = df['CW_CS_Account'].replace(replace_dict)
    df['Measure'] = 'Expenses'

    df = df.drop(columns=['ZJ_contract'])
    group_cols = [col for col in df.columns if col != 'data']
    # exist_cols = [col for col in group_cols if col in df.columns]
    df = df.groupby(group_cols, as_index=False)['data'].sum()
    print(1)

    return df


def push_to_cube(df,Scenario):
    """推送数据到 rev_profit_cube"""

    entity_dim =  Dimension('Entity_FR')
    entity_df = pd.DataFrame(entity_dim.query(expression="Base(#root,0)", fields=['name','ud2'], as_model=False)).drop(['id','expectedName'],axis=1).rename(columns={
        'name':'Entity_FR',
        'ud2':'Commercial',})
    entity_df = entity_df.drop_duplicates(subset=['Entity_FR'])

    df = df.merge(entity_df, how='left', on='Entity_FR')
    df = df[df['Commercial'].notna() & (df['Commercial'] != '')]

    df['Counterparty'] = 'nocp'
    df['Comprehensive'] = 'nocompr'
    df['Scenario'] = Scenario
    df['Misc1'] = 'nomisc1'

    df = df.rename(columns={'CW_CS_Account': 'Account_zijin'})

    # 4. 写入 Cube
    cube = FinancialCube('sub_fund_cube')

    # 保存数据
    cube.save(df, chunksize=200000)




def main(p1, p2):

    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    countAll = countSuccess = countError = 0
    countMsg = f"{start_time} 开始执行测算数据进资金预算任务\n"

    try:
        # 统一获取全局参数
        Version = Variable('Variable').get('Edit_Ver')

        if 'Year' in p2 and p2['Year']:
            Year = str(p2['Year'])
        else:
            Year = Variable('Variable').get('BudYear')

        cube = FinancialCube('CW_CS')
        main_processing(p1, p2, Version, Year,cube)
        countAll = countSuccess = 1
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 测算数据进资金预算处理完成\n"
    except Exception as e:
        countError = 1
        countAll = 1
        error_detail = traceback.format_exc()
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 利测算数据资金预算处理失败: {str(e)}\n"
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
