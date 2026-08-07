# -*- coding: utf-8 -*-
'''
@file    : actual_push_zijin_cube.py
@Time    :
@Author  : CHEN
@Software: PyCharm
@Desc    : 实际数进资金模型
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


# from _debug import p1, p2


def group_and_sum(df, group_cols, value_col='figure'):
    """
    按指定维度汇总数值
    """
    if df.empty:
        return df

    # 确保 group_cols 中的列都存在
    exist_cols = [col for col in group_cols if col in df.columns]

    df = df.groupby(exist_cols, as_index=False)[value_col].sum()
    return df


def actual_processing(p1, p2,year,Version):
    
    # 获取资金实际数中间表数据
    act_dt = DataTableMySQL('actual_data_zijin')
    cols = ['period', 'year', 'entity_cd', 'account_cd','commerical','counterparty','data']



    where = "year = '%s' and counterparty = 'nocp' " % year

    act_df = act_dt.select(columns=cols,where = where)

    act_df = act_df.rename(columns={
        "period": "Period",
        "entity_cd": "Entity_FR",
        "year": "Year",
        "account_cd": "Account_zijin",
        "commerical":"Commercial",
        "counterparty": "Counterparty",
    })

    act_df['Scenario'] = 'Actual_adjb'


    # 筛选条件：Entity_FR 列以 'XN' 开头，并且 Counterparty 列等于 'nocp'，将Sep替换为9
    act_xn = act_df[act_df['Entity_FR'].str.startswith('XN') & (act_df['Counterparty'] == 'nocp') & (act_df['Period'].isin(['Sep','10','11','12']))].copy()
    act_xn['data'] = act_xn['data'] * -1
    act_xn['Scenario'] = 'Actual_adj'
    # 将Period为'Sep'的记录替换为'9'
    act_xn.loc[act_xn['Period'] == 'Sep', 'Period'] = '9'


    # 处理出并表实际数
    cols = ['period', 'year', 'entity_cd', 'account_cd', 'commerical', 'counterparty', 'data']
    where = "year = '%s' and counterparty != 'nocp' " % year

    cons_df = act_dt.select(columns=cols, where=where)
    cons_df = cons_df.rename(columns={
        "period": "Period",
        "entity_cd": "Entity_FR",
        "year": "Year",
        "account_cd": "Account_zijin",
        "commerical":"Commercial",
        "counterparty": "Counterparty",
    })
    cons_df['Scenario'] = 'Actual_adjb'

    # cons_df['Counterparty'] = cons_df['Consol'].apply(lambda x: 'XN03' if x == 1 else 'XN04')
    # del cons_df['Consol']
    # print(cons_df)



    act_df = pd.concat([act_df,act_xn,cons_df])
    act_df.loc[act_df['Account_zijin'] == 'CF09', 'Account_zijin'] = 'CF0901'

    act_df['Version'] = Version
    act_df['Measure'] = 'Expenses'
    act_df['Comprehensive'] = 'nocompr'
    act_df['Misc1'] = 'nomisc1'
    act_df['Misc2'] = 'nomisc2'
    print(1)

    entity_dim = Dimension('Entity_FR')
    entity_list = pd.DataFrame(entity_dim.query(expression="Base(#root,0)", fields=['name'], as_model=False))
    act_df = act_df[act_df['Entity_FR'].isin(entity_list['name'])]


    # 过滤缺失科目
    account_dim = Dimension('Account_zijin')
    account_list = pd.DataFrame(account_dim.query(expression="Base(#root,0)", fields=['name'], as_model=False))
    act_df = act_df[act_df['Account_zijin'].isin(account_list['name'])]


    # 过滤缺失交易对手方
    Counterparty_dim = Dimension('Counterparty')
    Counterparty_list = pd.DataFrame(Counterparty_dim.query(expression="Base(#root,0)", fields=['name'], as_model=False))
    act_df = act_df[act_df['Counterparty'].isin(Counterparty_list['name'])]

    # 插入明细月份实际数
    cube = FinancialCube('sub_fund_cube')

    expr_dict_actual = {
        "Year": year,
        "Scenario":'Actual_adjb',
        "Entity_FR": "IDescendant(#root,0)",
        "Account_zijin": "IDescendant(#root,0)",
        "Period": ["Base(TotalPeriod,0)","Sep"],
        "Version": Version,
    }
    cube.delete(expr_dict_actual)

    cube.save(act_df,chunksize=400000)




    # 插入附表1、2的全项目实际数汇总
    from company_transactions_to_cube import sum_actual_period_processing as company_sum
    from Investment_cash_to_cube import sum_actual_period_processing as investment_sum
    Year = Variable('Variable').get('BudYear')

    p2 = {'Year_wb1': Year,
         'Entity_FR_wb1': 'Base(#root,0)',
         'Version_wb1': Version,}

    company_sum(p1, p2)
    investment_sum(p1, p2)

    sum_actual_adjb_period_processing(p1,p2)
    sum_actual_adj_period_processing(p1,p2)



def sum_actual_adjb_period_processing(p1,p2):
    Year = p2['Year_wb1']
    last_Year = str(int(Year)-1)
    Version = p2['Version_wb1']
    Entity_FR = p2['Entity_FR_wb1']


    sc_10 = Variable('Variable').get('zj_10_scenario')
    sc_11 = Variable('Variable').get('zj_11_scenario')
    sc_12 = Variable('Variable').get('zj_12_scenario')


    cube = FinancialCube('sub_fund_cube')
    fix_act_adjb = "Year{%s}->Scenario{actual_adjb}->Version{%s}->Period{Sep;10;11;12}->Comprehensive{nocompr}->Counterparty{nocp}->" \
                      "Entity_FR{%s}->Measure{Expenses}->Account_zijin{Base(CF00,0)}->" \
                      "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                      % (last_Year, Version, Entity_FR)

    act_df =  cube.query(fix_act_adjb, compact=False)
    fix_forecast = "Year{%s}->Scenario{Forecast}->Version{%s}->Period{10;11;12}->Comprehensive{nocompr}->Counterparty{nocp}->" \
                   "Entity_FR{%s}->Measure{Expenses}->Account_zijin{Base(CF00,0)}->" \
                   "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                   % (last_Year, Version, Entity_FR)

    df_forecast = cube.query(fix_forecast, compact=False)

    if act_df.empty and df_forecast.empty:
        print("实际数和预测数都为空，无需处理。")
        return


    # 根据scenario配置确定数据来源

    if sc_10 == 'Forecast' and sc_11 == 'Forecast' and sc_12 == 'Forecast':
        # 10、11、12月均为预测 → 实际数只取 Sep
        act_periods = act_df[act_df['Period'] == 'Sep']
        forecast_periods = df_forecast[df_forecast['Period'].isin(['10', '11', '12'])]
        combined_df = pd.concat([act_periods, forecast_periods], ignore_index=True)

    elif sc_10 == 'Actual_adjb' and sc_11 == 'Forecast' and sc_12 == 'Forecast':
        # sc_10 为 Actual → 实际数取 Sep + 10月，预测取 11 + 12月
        act_periods = act_df[act_df['Period'].isin(['Sep', '10'])]
        forecast_periods = df_forecast[df_forecast['Period'].isin(['11', '12'])]
        combined_df = pd.concat([act_periods, forecast_periods], ignore_index=True)

    elif sc_10 == 'Actual_adjb' and sc_11 == 'Actual_adjb' and sc_12 == 'Forecast':
        # sc_11 为 Actual → 实际数取 Sep + 10 + 11月，预测取 12月
        act_periods = act_df[act_df['Period'].isin(['Sep', '10', '11'])]
        forecast_periods = df_forecast[df_forecast['Period'] == '12']
        combined_df = pd.concat([act_periods, forecast_periods], ignore_index=True)

    else:
        # 默认情况：全部使用实际数（Sep,10,11,12）
        combined_df = act_df[act_df['Period'].isin(['Sep', '10', '11', '12'])].copy()


    print(combined_df)

    # 计算全年合计

    # 按维度分组求和，排除Period维度
    group_cols = [col for col in combined_df.columns if col not in ['Period', 'data','Scenario']]
    yearly_sum = combined_df.groupby(group_cols, as_index=False)['data'].sum()

    # 设置Period为'Noperiod'
    yearly_sum['Period'] = 'Noperiod'
    yearly_sum['Scenario'] = 'actual_adjb'


    def_fix =  "Year{%s}->Scenario{actual_adjb}->Version{%s}->Period{Noperiod}->Comprehensive{nocompr}->Counterparty{nocp}->" \
                      "Entity_FR{%s}->Measure{Expenses}->Account_zijin{Base(CF00,0)}->" \
                      "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                      % (last_Year, Version, Entity_FR)

    cube.delete(def_fix)
    # 打印结果
    print("实际数全年合计数据（Period=Noperiod）：")
    cube.save(yearly_sum, chunksize=200000)


def sum_actual_adj_period_processing(p1,p2):
    Year = p2['Year_wb1']
    last_Year = str(int(Year)-1)
    Version = p2['Version_wb1']
    Entity_FR = p2['Entity_FR_wb1']


    # sc_10 = Variable('Variable').get('zj_10_scenario')
    # sc_11 = Variable('Variable').get('zj_11_scenario')
    # sc_12 = Variable('Variable').get('zj_12_scenario')


    cube = FinancialCube('sub_fund_cube')
    fix_act_adj = "Year{%s}->Scenario{actual_adj}->Version{%s}->Period{Sep;10;11;12}->Comprehensive{nocompr}->Counterparty{nocp}->" \
                      "Entity_FR{%s}->Measure{Expenses}->Account_zijin{Base(CF00,0)}->" \
                      "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                      % (last_Year, Version, Entity_FR)

    act_df =  cube.query(fix_act_adj, compact=False)


    if act_df.empty:
        print("实际数调整数都为空，无需处理。")
        return


    # 计算全年合计

    # 按维度分组求和，排除Period维度
    group_cols = [col for col in act_df.columns if col not in ['Period', 'data']]
    yearly_sum = act_df.groupby(group_cols, as_index=False)['data'].sum()

    # 设置Period为'Noperiod'
    yearly_sum['Period'] = 'Noperiod'
    # yearly_sum['Scenario'] = 'actual_adjb'


    def_fix =  "Year{%s}->Scenario{actual_adj}->Version{%s}->Period{Noperiod}->Comprehensive{nocompr}->Counterparty{nocp}->" \
                      "Entity_FR{%s}->Measure{Expenses}->Account_zijin{Base(CF00,0)}->" \
                      "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                      % (last_Year, Version, Entity_FR)

    cube.delete(def_fix)
    # 打印结果
    print("实际数全年合计数据（Period=Noperiod）：")
    cube.save(yearly_sum, chunksize=200000)




def main(p1, p2):
    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    countAll = 0
    countSuccess = 0
    countError = 0
    countMsg = f"{start_time} 开始执行实际数接入任务\n"

    try:

        if 'Year' in p2 and p2['Year']:
            year = str(p2['Year'])
        else:
            BudYear = Variable('Variable').get('BudYear')
            year = str(int(BudYear) - 1)

        Version = Variable('Variable').get('Edit_Ver')

        actual_processing(p1, p2,year,Version)
        countSuccess = 1
        countAll = 1
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 实际数接入处理完成\n"

    except Exception as e:
        countError = 1
        countAll = 1
        error_detail = traceback.format_exc()
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 实际数接入失败: {str(e)}\n"
        countMsg += f"详细错误信息:\n{error_detail}\n"
        print(f"实际数推送执行出错: {e}")
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

