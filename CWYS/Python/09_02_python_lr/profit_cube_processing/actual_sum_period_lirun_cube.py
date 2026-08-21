# -*- coding: utf-8 -*-
'''
@file    : actual_sum_period_lirun_cube.py
@Time    :
@Author  : CHEN
@Software: PyCharm
@Desc    : 实际数全年合计进利润填报模型
'''


try:
    from CWYS.__debug import para1, para2
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



def sum_actual_period_processing(p1,p2):
    Year = p2['Year_wb1']
    last_Year = str(int(Year)-1)
    Version = p2['Version_wb1']
    Entity_GL = p2['Entity_GL_wb1']


    # sc_10 = Variable('Variable').get('10_scenario')
    # sc_11 = Variable('Variable').get('11_scenario')
    # sc_12 = Variable('Variable').get('12_scenario')


    cube = FinancialCube('sub_profit_cube')
    fix_act_adj =   "Year{%s}->Scenario{Actual}->Version{%s}->Period{Base(TotalPeriod,0)}->Comprehensive{Tax;NoTax}->"\
                    "Entity_GL{IBase(%s,0)}->Measure{Expenses}->Account_lirun{Base(PL60,0);Base(YW,0);SYW02030601;SYW02030602}->"\
                    "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}"\
                      % (last_Year, Version, Entity_GL)

    act_df =  cube.query(fix_act_adj, compact=False)

    fix_forecast = "Year{%s}->Scenario{Forecast}->Version{%s}->Period{Base(TotalPeriod,0)}->Comprehensive{Tax;NoTax}->"\
                    "Entity_GL{IBase(%s,0)}->Measure{Expenses}->Account_lirun{Base(PL60,0);Base(YW,0);SYW02030601;SYW02030602}->"\
                    "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}"\
                      % (last_Year, Version, Entity_GL)

    df_forecast = cube.query(fix_forecast, compact=False)

    combined_df = pd.concat([act_df, df_forecast], ignore_index=True)


    if act_df.empty and df_forecast.empty:
        print("实际数和预测数都为空，无需处理。")
        return


    sc_10 = Variable('Variable').get('10_scenario')
    sc_11 = Variable('Variable').get('11_scenario')
    sc_12 = Variable('Variable').get('12_scenario')

    if sc_10 == 'Forecast' and sc_11 == 'Forecast' and sc_12 == 'Forecast':
        # 10、11、12月均为预测 → 实际数只取 Sep
        act_periods = act_df[act_df['Period'].isin(['1','2','3','4','5','6','7','8','9'])]
        forecast_periods = df_forecast[df_forecast['Period'].isin(['10', '11', '12'])]
        combined_df = pd.concat([act_periods, forecast_periods], ignore_index=True)

    elif sc_10 == 'Actual_adjb' and sc_11 == 'Forecast' and sc_12 == 'Forecast':
        # sc_10 为 Actual → 实际数取 Sep + 10月，预测取 11 + 12月
        act_periods = act_df[act_df['Period'].isin(['1','2','3','4','5','6','7','8','9','10'])]
        forecast_periods = df_forecast[df_forecast['Period'].isin(['11', '12'])]
        combined_df = pd.concat([act_periods, forecast_periods], ignore_index=True)

    elif sc_10 == 'Actual_adjb' and sc_11 == 'Actual_adjb' and sc_12 == 'Forecast':
        # sc_11 为 Actual → 实际数取 Sep + 10 + 11月，预测取 12月
        act_periods = act_df[act_df['Period'].isin(['1','2','3','4','5','6','7','8','9','10','11'])]
        forecast_periods = df_forecast[df_forecast['Period'] == '12']
        combined_df = pd.concat([act_periods, forecast_periods], ignore_index=True)

    else:
        # 默认情况：全部使用实际数（Sep,10,11,12）
        combined_df = act_df[act_df['Period'].isin(['1','2','3','4','5','6','7','8','9', '10', '11', '12'])].copy()


    print(combined_df)
    # 计算全年合计

    # 按维度分组求和，排除Period维度
    group_cols = [col for col in combined_df.columns if col not in ['Period', 'Scenario','data']]
    yearly_sum = combined_df.groupby(group_cols, as_index=False)['data'].sum()

    # 设置Period为'Noperiod'
    yearly_sum['Period'] = 'Noperiod'
    yearly_sum['Scenario'] = 'Actual'


    def_fix =  "Year{%s}->Scenario{Actual}->Version{%s}->Period{Noperiod}->Comprehensive{Tax;NoTax}->"\
                    "Entity_GL{IBase(%s,0)}->Measure{Expenses}->Account_lirun{Base(PL60,0);Base(YW,0);SYW02030601;SYW02030602}->"\
                    "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}"\
                      % (last_Year, Version, Entity_GL)

    cube.delete(def_fix)
    # 打印结果
    print("实际数全年合计数据（Period=Noperiod）：")
    cube.save(yearly_sum, chunksize=200000)




def main(p1, p2):
    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    countAll = 0
    countSuccess = 0
    countError = 0
    countMsg = f"{start_time} 开始执行利润实际数全年合计计算任务\n"

    try:
        sum_actual_period_processing(p1, p2)
        countSuccess = 1
        countAll = 1
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 利润实际数全年合计计算处理完成\n"

    except Exception as e:
        countError = 1
        countAll = 1
        error_detail = traceback.format_exc()
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 利润实际数全年合计计算失败: {str(e)}\n"
        countMsg += f"详细错误信息:\n{error_detail}\n"
        print(f"利润实际数全年合计计算执行出错: {e}")
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
    para2 = {'Year_wb1':'2026','Entity_GL_wb1':'D000001','Version_wb1':'V4'}
    main(para1, para2)

