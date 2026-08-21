# -*- coding: utf-8 -*-
'''
@file    : actual_sum_period_zijin_cube.py
@Time    :
@Author  : CHEN
@Software: PyCharm
@Desc    : 实际数全年合计进资金模型
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
                      "Entity_FR{IBase(%s,0)}->Measure{Expenses}->Account_zijin{Remove(IDescendant(CF00,0),CF01)}->" \
                      "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                      % (last_Year, Version, Entity_FR)

    act_df =  cube.query(fix_act_adjb, compact=False)
    fix_forecast = "Year{%s}->Scenario{Forecast}->Version{%s}->Period{10;11;12}->Comprehensive{nocompr}->Counterparty{nocp}->" \
                   "Entity_FR{IBase(%s,0)}->Measure{Expenses}->Account_zijin{Remove(IDescendant(CF00,0),CF01)}->" \
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
                      "Entity_FR{IBase(%s,0)}->Measure{Expenses}->Account_zijin{Remove(IDescendant(CF00,0),CF01)}->" \
                      "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                      % (last_Year, Version, Entity_FR)

    cube.delete(def_fix)
    # 打印结果
    print("实际数调整前全年合计数据（Period=Noperiod）：")
    cube.save(yearly_sum, chunksize=200000)



def sum_actual_adj_period_processing(p1,p2):
    Year = p2['Year_wb1']
    last_Year = str(int(Year)-1)
    Version = p2['Version_wb1']
    Entity_FR = p2['Entity_FR_wb1']



    sc_10 = Variable('Variable').get('zj_10_scenario')
    sc_11 = Variable('Variable').get('zj_11_scenario')
    sc_12 = Variable('Variable').get('zj_12_scenario')


    cube = FinancialCube('sub_fund_cube')
    fix_act_adj = "Year{%s}->Scenario{actual_adj}->Version{%s}->Period{Sep;10;11;12}->Comprehensive{nocompr}->Counterparty{nocp}->" \
                      "Entity_FR{IBase(%s,0)}->Measure{Expenses}->Account_zijin{Remove(IDescendant(CF00,0),CF01)}->" \
                      "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                      % (last_Year, Version, Entity_FR)

    act_df =  cube.query(fix_act_adj, compact=False)

    fix_forecast = "Year{%s}->Scenario{Forecast}->Version{%s}->Period{adjust}->Comprehensive{nocompr}->Counterparty{nocp}->" \
                   "Entity_FR{IBase(%s,0)}->Measure{Expenses}->Account_zijin{Remove(IDescendant(CF00,0),CF01)}->" \
                   "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                   % (last_Year, Version, Entity_FR)

    df_forecast = cube.query(fix_forecast, compact=False)

    if sc_10 == 'Forecast' and sc_11 == 'Forecast' and sc_12 == 'Forecast':
        # 10、11、12月均为预测 → 实际数只取 Sep
        act_periods = act_df[act_df['Period'] == 'Sep']
        forecast_periods = df_forecast[df_forecast['Period'] == 'adjust']
        combined_df = pd.concat([act_periods, forecast_periods], ignore_index=True)

    elif sc_10 == 'Actual_adjb' and sc_11 == 'Forecast' and sc_12 == 'Forecast':
        # sc_10 为 Actual → 实际数取 Sep + 10月，预测取 11 + 12月
        act_periods = act_df[act_df['Period'].isin(['Sep', '10'])]
        forecast_periods = df_forecast[df_forecast['Period'] == 'adjust']
        combined_df = pd.concat([act_periods, forecast_periods], ignore_index=True)

    elif sc_10 == 'Actual_adjb' and sc_11 == 'Actual_adjb' and sc_12 == 'Forecast':
        # sc_11 为 Actual → 实际数取 Sep + 10 + 11月，预测取 12月
        act_periods = act_df[act_df['Period'].isin(['Sep', '10', '11'])]
        forecast_periods = df_forecast[df_forecast['Period'] == 'adjust']
        combined_df = pd.concat([act_periods, forecast_periods], ignore_index=True)

    else:
        # 默认情况：全部使用实际数（Sep,10,11,12）
        act_periods = act_df[act_df['Period'].isin(['Sep', '10', '11','12'])]
        forecast_periods = df_forecast[df_forecast['Period'] == 'adjust']
        combined_df = pd.concat([act_periods, forecast_periods], ignore_index=True)


    if combined_df.empty:
        print("实际数调整数都为空，无需处理。")
        return


    # 计算全年合计

    # 按维度分组求和，排除Period维度
    group_cols = [col for col in combined_df.columns if col not in ['Period', 'Scenario','data']]
    yearly_sum = combined_df.groupby(group_cols, as_index=False)['data'].sum()

    # 设置Period为'Noperiod'
    yearly_sum['Period'] = 'Noperiod'
    yearly_sum['Scenario'] = 'actual_adj'


    def_fix =  "Year{%s}->Scenario{actual_adj}->Version{%s}->Period{Noperiod}->Comprehensive{nocompr}->Counterparty{nocp}->" \
                      "Entity_FR{IBase(%s,0)}->Measure{Expenses}->Account_zijin{Remove(IDescendant(CF00,0),CF01)}->" \
                      "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                      % (last_Year, Version, Entity_FR)


    cube.delete(def_fix)

    # 打印结果
    print("实际数调整全年合计数据（Period=Noperiod）：")
    cube.save(yearly_sum, chunksize=200000)

def CF01_noperiod_processing(p1,p2):
    Year = p2['Year_wb1']
    last_Year = str(int(Year)-1)
    Version = p2['Version_wb1']
    Entity_FR = p2['Entity_FR_wb1']

    cube = FinancialCube('sub_fund_cube')
    fix_act_adjb = "Year{%s}->Scenario{actual_adjb}->Version{%s}->Period{Sep}->Comprehensive{nocompr}->Counterparty{nocp}->" \
                      "Entity_FR{IBase(%s,0)}->Measure{Expenses}->Account_zijin{CF01}->" \
                      "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                      % (last_Year, Version, Entity_FR)
    act_df =  cube.query(fix_act_adjb, compact=False)
    act_df['Period'] = 'Noperiod'

    fix_act_adj = "Year{%s}->Scenario{actual_adj}->Version{%s}->Period{Sep}->Comprehensive{nocompr}->Counterparty{nocp}->" \
                      "Entity_FR{IBase(%s,0)}->Measure{Expenses}->Account_zijin{CF01}->" \
                      "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                      % (last_Year, Version, Entity_FR)
    act_df_adj =  cube.query(fix_act_adj, compact=False)
    act_df_adj['Period'] = 'Noperiod'

    act_df = pd.concat([act_df,act_df_adj],ignore_index=True)

    def_fix =  "Year{%s}->Scenario{actual_adj;actual_adjb}->Version{%s}->Period{Noperiod}->Comprehensive{nocompr}->Counterparty{nocp}->" \
                      "Entity_FR{IBase(%s,0)}->Measure{Expenses}->Account_zijin{CF01}->" \
                      "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                      % (last_Year, Version, Entity_FR)

    cube.delete(def_fix)
    print("CF01全年合计数据（Period=Noperiod）：")
    cube.save(act_df, chunksize=200000)




def get_variable(variable, v_key):
    var = Variable(variable)
    return var.get_value(v_key)


def safe_sum(series: pd.Series):
    """安全求和，兼容空序列，统一返回原生数值"""
    val = series.sum()
    if pd.isna(val):
        return 0.0
    num = val.item() if hasattr(val, "item") else float(val)
    return num


# 实际年期初现金金额
def del_act_start_count_processing(year, Entity_FR, Commercial, version, scenario_10, scenario_11, scenario_12):

    sce_map = {'Sep': 'Actual_adja', '10': scenario_10, '11': scenario_11, '12': scenario_12, 'adjust': 'Forecast'}
    print(sce_map)
    # 基础维度模板，所有行共用
    base_dim = {
        "Account_zijin": "CF01",
        "Commercial": Commercial,
        "Comprehensive": "nocompr",
        "Counterparty": "nocp",
        "Entity_FR": Entity_FR,
        "Measure": "Expenses",
        "Misc1": "nomisc1",
        "Misc2": "nomisc2",
        "Version": "V1",
        "Year": year
    }

    cube = FinancialCube('sub_fund_cube')
    fix_act_adj = "Year{%s}->Entity_FR{%s}->Account_zijin{IBase(CF02,0);IBase(CF07,0)}->Commercial{%s}->Comprehensive{nocompr}->Counterparty{nocp}" \
                  "->Measure{Expenses}->Misc1{nomisc1}->Misc2{nomisc2}->Version{V1}" % (
                      year, Entity_FR, Commercial)

    act_df = cube.query(fix_act_adj, compact=False)
    act_df.loc[act_df["Period"] == "Sep", "Scenario"] = "Actual_adja"

    df_act_1 = act_df[
        (act_df["Period"].isin(['Sep', '10', '11', '12', 'adjust'])) & (act_df["Account_zijin"] != "CF02") & (
                act_df["Account_zijin"] != "CF07") & (
            act_df.apply(lambda row: (row['Period'], row['Scenario']) in sce_map.items(), axis=1))]

    reduce_act_adj = "Year{%s}->Entity_FR{%s}->Account_zijin{IBase(CF03,0);IBase(CF06,0)}->Commercial{%s}->Comprehensive{nocompr}->Counterparty{nocp}" \
                     "->Measure{Expenses}->Misc1{nomisc1}->Misc2{nomisc2}->Version{V1}" % (
                         year, Entity_FR, Commercial)

    reduce_df_1 = cube.query(reduce_act_adj, compact=False)
    reduce_df_1.loc[reduce_df_1["Period"] == "Sep", "Scenario"] = "Actual_adja"

    df_reduce_1 = reduce_df_1[
        (reduce_df_1["Period"].isin(['Sep', '10', '11', '12', 'adjust'])) & (reduce_df_1["Account_zijin"] != "CF03") & (
                reduce_df_1["Account_zijin"] != "CF06") & (
            reduce_df_1.apply(lambda row: (row['Period'], row['Scenario']) in sce_map.items(), axis=1))]
    cf01_dict = {}
    dim_list = []

    act_09_adj = "Year{%s}->Entity_FR{%s}->Account_zijin{IBase(CF01,0)}->Commercial{%s}->Comprehensive{nocompr}->Counterparty{nocp}" \
                 "->Measure{Expenses}->Period{%s}->Scenario{%s}->Misc1{nomisc1}->Misc2{nomisc2}->Version{V1}" % (
                     year, Entity_FR, Commercial, 'Sep', 'Actual_adja')

    reduce_df_1 = cube.query(act_09_adj, compact=False)

    cf04_count_adj = "Year{%s}->Entity_FR{%s}->Account_zijin{IBase(CF04,0)}->Commercial{%s}->Comprehensive{nocompr}->Counterparty{nocp}" \
                     "->Measure{Expenses}->Misc1{nomisc1}->Misc2{nomisc2}->Version{V1}" % (
                         year, Entity_FR, Commercial)
    reduce_df_04 = cube.query(cf04_count_adj, compact=False)

    ini_09_count = safe_sum(reduce_df_1['data'])
    # ini_09_count = 0

    for mon, sce in sce_map.items():
        if mon == 'Sep':
            next_mon = '10'
        elif mon == '12':
            next_mon = 'adjust'
        elif mon == 'adjust':
            next_mon = '13'
        else:
            next_mon = str(int(mon) + 1)

        mon_count = safe_sum(
            df_act_1[(df_act_1['Period'] == mon) & (df_act_1['Scenario'] == sce)]['data'])
        reduce_count = safe_sum(df_reduce_1[(df_reduce_1['Period'] == mon) & (df_reduce_1['Scenario'] == sce)]['data'])
        ini_09_count = round(ini_09_count + mon_count - reduce_count, 4)
        cf01_dict[next_mon] = ini_09_count
        if mon != 'adjust':
            base_dim_2 = base_dim.copy()
            base_dim_2.update({'Period': next_mon, 'Scenario': sce_map[next_mon], 'data': ini_09_count})
            dim_list.append(base_dim_2)
    res_df = pd.DataFrame(dim_list)
    # def_fix = "Year{%s}->Scenario{Actual_adjb;Forecast}->Version{%s}->Period{10;11;12}->Comprehensive{nocompr}->Counterparty{nocp}->" \
    #           "Entity_FR{IBase(%s,0)}->Measure{Expenses}->Account_zijin{CF01}->" \
    #           "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{%s}" \
    #           % (year, version, Entity_FR, Commercial)
    # cube.delete(def_fix)

    cube.save(res_df, chunksize=50000)
    return res_df, cf01_dict['13']


# 预算数数据
def del_budget_start_count_processing(year, Entity_FR, Commercial, budget_cf01_count):
    mons_query = [str(i) for i in range(1, 13)]
    base_dim = {
        "Account_zijin": "CF01",
        "Commercial": Commercial,
        "Comprehensive": "nocompr",
        "Counterparty": "nocp",
        "Scenario": "budget_adjb",
        "Entity_FR": Entity_FR,
        "Measure": "Expenses",
        "Misc1": "nomisc1",
        "Misc2": "nomisc2",
        "Version": "V1",
        "Year": year
    }
    cube = FinancialCube('sub_fund_cube')
    fix_bud_adj = "Year{%s}->Entity_FR{%s}->Account_zijin{IBase(CF02,0);IBase(CF07,0)}->Commercial{%s}->Comprehensive{nocompr}->Counterparty{nocp}" \
                  "->Measure{Expenses}->Misc1{nomisc1}->Misc2{nomisc2}->Version{V1}" % (
                      year, Entity_FR, Commercial)
    _df = cube.query(fix_bud_adj, compact=False)
    df_act_1 = _df[(_df["Period"].isin(mons_query)) & (_df["Account_zijin"] != "CF02") & (
            _df["Account_zijin"] != "CF07") & (_df["Scenario"] == "budget_adjb")]

    reduce_act_adj = "Year{%s}->Entity_FR{%s}->Account_zijin{IBase(CF03,0);IBase(CF06,0)}->Commercial{%s}->Comprehensive{nocompr}->Counterparty{nocp}" \
                     "->Measure{Expenses}->Misc1{nomisc1}->Misc2{nomisc2}->Version{V1}" % (
                         year, Entity_FR, Commercial)

    reduce_df_1 = cube.query(reduce_act_adj, compact=False)
    df_reduce_1 = reduce_df_1[
        (reduce_df_1["Period"].isin(mons_query)) & (reduce_df_1["Account_zijin"] != "CF03") & (
                reduce_df_1["Account_zijin"] != "CF06") & (reduce_df_1["Scenario"] == "budget_adjb")]
    last_amont = budget_cf01_count
    ini_dict = {}
    base_dim_1 = base_dim.copy()
    base_dim_1.update({'Period': '1', 'data': last_amont})
    dim_list = [base_dim_1, ]
    for mon in mons_query:
        base_dim_2 = base_dim.copy()
        budget_amount = safe_sum(df_act_1[df_act_1['Period'] == mon]['data'])
        reduce_amount = safe_sum(df_reduce_1[df_reduce_1['Period'] == mon]['data'])
        last_amont = round(last_amont + budget_amount - reduce_amount, 4)
        ini_dict[mon] = last_amont
        if mon != '12':
            base_dim_2.update({'Period': str(int(mon) + 1), 'data': last_amont})
            dim_list.append(base_dim_2)
        else:
            # base_dim_2.update({'Account_zijin': 'CF09', 'Period': 'TotalPeriod', 'data': last_amont})
            pass
    res_df = pd.DataFrame(dim_list)

    cube.save(res_df, chunksize=50000)

def CF01_Process(p1, p2):
    Year = p2['Year_wb1']
    last_Year = str(int(Year) - 1)
    Entity_FR = p2['Entity_FR_wb1']
    version = p2['Version_wb1']
    Commercial = p2['Commercial_wb1']
    scenario_10 = get_variable("Variable", "zj_10_scenario")
    scenario_11 = get_variable("Variable", "zj_11_scenario")
    scenario_12 = get_variable("Variable", "zj_12_scenario")

    res_df, budget_cf01_count = del_act_start_count_processing(last_Year, Entity_FR, Commercial, version, scenario_10,
                                                               scenario_11, scenario_12)
    del_budget_start_count_processing(Year, Entity_FR, Commercial, budget_cf01_count)



def main(p1, p2):
    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    countAll = 0
    countSuccess = 0
    countError = 0
    countMsg = f"{start_time} 开始执行实际数全年合计计算任务\n"

    try:
        sum_actual_adjb_period_processing(p1, p2)
        sum_actual_adj_period_processing(p1, p2)
        CF01_noperiod_processing(p1, p2)
        CF01_Process(p1, p2)
        countSuccess = 1
        countAll = 1
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 实际数全年合计计算处理完成\n"

    except Exception as e:
        countError = 1
        countAll = 1
        error_detail = traceback.format_exc()
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 实际数全年合计计算失败: {str(e)}\n"
        countMsg += f"详细错误信息:\n{error_detail}\n"
        print(f"实际数全年合计计算执行出错: {e}")
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
    para2 = {'Year_wb1':'2027','Entity_FR_wb1':'D000001','Version_wb1':'V1'}
    main(para1, para2)

