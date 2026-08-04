# -*- coding: utf-8 -*-
'''
@file    : company_transactions_to_cube.py
@Desc    : 公司间往来明细信息进cube
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


def main_processing(p1, p2):
    """主处理函数"""
    Year = p2['Year_wb1']
    Version = p2['Version_wb1']
    Entity_FR = p2['Entity_FR_wb1']
    Commercial = p2['Commercial_wb1']
    cube = FinancialCube('sub_fund_cube')

    # 获取资金cube数据
    fix_budget_adjb = "Year{%s}->Scenario{budget_adjb}->Version{%s}->Period{Base(TotalPeriod,0)}->Comprehensive{nocompr}->Counterparty{Base(sum,0)}->" \
               "Entity_FR{%s}->Measure{Expenses;Ext_Amt;IC_Amt}->Account_zijin{CF02040201;CF02040301;CF02040401;CF0307010101;CF0307010201;CF0307010202;CF0307010301;CF030303;CF0204010103}->"\
               "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                % (Year,Version,Entity_FR)

    df_budget_adjb = cube.query(fix_budget_adjb, compact=False)

    # 获取交易对手方信息填报表
    dt = DataTableMySQL('cp_info')
    where = 'account in ("CF02040201","CF02040301","CF02040401","CF0307010101","CF0307010201","CF0307010202","CF0307010301","CF030303","CF0204010103") and year = "%s" and entity = "%s"' % (
    Year, Entity_FR)

    if Entity_FR == 'Base(#root,0)':
        where = where = 'account in ("CF02040201","CF02040301","CF02040401","CF0307010101","CF0307010201","CF0307010202","CF0307010301","CF030303","CF0204010103") and year = "%s"' % (
    Year)

    df =  (dt.select(columns=['year','entity','counterparty','account'],where = where)
    .rename(columns={
        'year':'Year',
        'entity':'Entity_FR',
        'counterparty':'Counterparty',
        'account':'Account_zijin'
    }))

    # ================== 3. 数据对比 & 同步 ==================



    # 关键匹配字段
    key_cols = ['Year', 'Entity_FR', 'Counterparty', 'Account_zijin']

    # 构造唯一键
    mysql_keys = df[key_cols].drop_duplicates()
    cube_keys = df_budget_adjb[key_cols].drop_duplicates() if not df_budget_adjb.empty else pd.DataFrame(columns=key_cols)

    merged = cube_keys.merge(
        mysql_keys,
        on=key_cols,
        how='outer',  # 关键：outer 可以同时看到左右两边独有的和共有的
        indicator=True  # 会自动生成 '_merge' 列
    )

    left_only = merged[merged['_merge'] == 'left_only']  # Cube有，MySQL没有 → 删除
    right_only = merged[merged['_merge'] == 'right_only']  # MySQL有，Cube没有 → 插入
    both = merged[merged['_merge'] == 'both']

    print(f"对比结果：Cube有 {len(cube_keys)} | MySQL有 {len(mysql_keys)}")
    print(f"  → 需要删除 (left_only): {len(left_only)} 条")
    print(f"  → 需要插入 (right_only): {len(right_only)} 条")
    print(f"  → 两边都有 (both): {len(both)} 条")

    # ================== 4. 删除 Cube 中多余的数据 ==================
    # Cube里有，但MySQL里已经没有的 → 需要删除
    if not left_only.empty:
        print("正在批量删除 Cube 中多余数据...")

        # 构造删除表达式列表（批量方式）
        for _, row in left_only.iterrows():
            delete_expr = {
                "Year": Year,
                "Scenario": "budget_adjb",
                "Version": Version,
                "Entity_FR": Entity_FR,
                "Account_zijin": row['Account_zijin'],
                "Counterparty": row['Counterparty'],
                # "Measure": "Expenses",
                "Comprehensive": "nocompr",
                "Misc1": "nomisc1",
                "Misc2": "nomisc2",
                "Commercial": "Base(YT00,0)"  # 根据实际情况调整
            }
            cube.delete(delete_expr)  # 删除该组合所有期间的数据

            delete_expr = {
                "Year": str(int(Year)-1),
                "Scenario": "Forecast",
                "Version": Version,
                "Entity_FR": Entity_FR,
                "Account_zijin": row['Account_zijin'],
                "Counterparty": row['Counterparty'],
                # "Measure": "Expenses",
                "Comprehensive": "nocompr",
                "Misc1": "nomisc1",
                "Misc2": "nomisc2",
                "Commercial": "Base(YT00,0)"  # 根据实际情况调整
            }
            cube.delete(delete_expr)  # 删除该组合所有期间的数据
            print(f"已删除: Counterparty={row['Counterparty']}, Account={row['Account_zijin']}")

    # ================== 5. 批量插入 right_only ==================
    if not right_only.empty:
        print(f"正在批量插入 {len(right_only)} 条初始化记录...")

        insert_df = right_only.copy().drop(['_merge'], axis=1)
        insert_df['Period'] = 1
        insert_df['Scenario'] = 'budget_adjb'
        insert_df['Version'] = Version
        insert_df['Comprehensive'] = 'nocompr'
        insert_df['Measure'] = 'Expenses'
        insert_df['Misc1'] = 'nomisc1'
        insert_df['Misc2'] = 'nomisc2'
        insert_df['Commercial'] = Commercial  # ← 根据需要修改
        insert_df['data'] = 0.0
        insert_df = insert_df.dropna(subset=['Account_zijin', 'Counterparty'])

        # # 创建要新增的两行数据
        # new_rows = []
        # for cp in ['XN01', 'XN02']:
        #     # 复制right_only的每一行，并修改Counterparty
        #     for _, row in insert_df.iterrows():
        #         new_row = row.copy()
        #         new_row['Counterparty'] = cp
        #         new_rows.append(new_row)
        # # 将新行转换为DataFrame并追加到insert_df
        # if new_rows:
        #     new_df = pd.DataFrame(new_rows)
        #     insert_df = pd.concat([insert_df, new_df], ignore_index=True)

        cube.save(insert_df, chunksize=200000)
    print(1)


def sum_actual_period_processing(p1,p2):
    Year = p2['Year_wb1']
    last_Year = str(int(Year)-1)
    Version = p2['Version_wb1']
    Entity_FR = p2['Entity_FR_wb1']


    sc_10 = Variable('Variable').get('zj_10_scenario')
    sc_11 = Variable('Variable').get('zj_11_scenario')
    sc_12 = Variable('Variable').get('zj_12_scenario')


    cube = FinancialCube('sub_fund_cube')
    fix_act_adjb = "Year{%s}->Scenario{actual_adjb}->Version{%s}->Period{Sep;10;11;12}->Comprehensive{nocompr}->Counterparty{Base(sum,0)}->" \
                      "Entity_FR{%s}->Measure{Expenses}->Account_zijin{CF02040201;CF02040301;CF02040401;CF0307010101;CF0307010201;CF0307010202;CF0307010301;CF030303;CF0204010103}->" \
                      "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                      % (last_Year, Version, Entity_FR)

    act_df =  cube.query(fix_act_adjb, compact=False)
    fix_forecast = "Year{%s}->Scenario{Forecast}->Version{%s}->Period{10;11;12}->Comprehensive{nocompr}->Counterparty{Base(sum,0)}->" \
                   "Entity_FR{%s}->Measure{Expenses}->Account_zijin{CF02040201;CF02040301;CF02040401;CF0307010101;CF0307010201;CF0307010202;CF0307010301;CF030303;CF0204010103}->" \
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


    def_fix =  "Year{%s}->Scenario{actual_adjb}->Version{%s}->Period{Noperiod}->Comprehensive{nocompr}->Counterparty{Base(sum,0)}->" \
                      "Entity_FR{%s}->Measure{Expenses;Ext_Amt;IC_Amt}->Account_zijin{CF02040201;CF02040301;CF02040401;CF0307010101;CF0307010201;CF0307010202;CF0307010301;CF030303;CF0204010103}->" \
                      "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                      % (last_Year, Version, Entity_FR)

    cube.delete(def_fix)
    # 打印结果
    print("实际数全年合计数据（Period=Noperiod）：")
    cube.save(yearly_sum, chunksize=200000)

    measure_sum = measure_processing(yearly_sum)
    cube.save(measure_sum, chunksize=200000)
    print(1)

def sum_budget_period_processing(p1, p2):
    Year = p2['Year_wb1']
    last_Year = str(int(Year)-1)
    Version = p2['Version_wb1']
    Entity_FR = p2['Entity_FR_wb1']
    cube = FinancialCube('sub_fund_cube')
    # 获取资金cube数据
    fix_budget_adjb = "Year{%s}->Scenario{budget_adjb}->Version{%s}->Period{Base(TotalPeriod,0)}->Comprehensive{nocompr}->Counterparty{Base(sum,0)}->" \
               "Entity_FR{%s}->Measure{Expenses}->Account_zijin{CF02040201;CF02040301;CF02040401;CF0307010101;CF0307010201;CF0307010202;CF0307010301;CF030303;CF0204010103}->"\
               "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                % (Year,Version,Entity_FR)
    df_budget = cube.query(fix_budget_adjb, compact=False)

    if df_budget.empty:
        print("实际数和预测数都为空，无需处理。")
        return


    # 按维度分组求和，排除Period维度
    group_cols = [col for col in df_budget.columns if col not in ['Period', 'data']]
    budget_yearly_sum = df_budget.groupby(group_cols, as_index=False)['data'].sum()

    # 设置Period为'Noperiod'
    budget_yearly_sum['Period'] = 'Noperiod'
    cube.save(budget_yearly_sum, chunksize=200000)

    measure_sum = measure_processing(budget_yearly_sum)
    cube.save(measure_sum, chunksize=200000)

def measure_processing(df):
    Counterparty = Dimension('Counterparty')
    Counterparty_df = (pd.DataFrame(Counterparty.query("Base(#root,0)", fields=['name','ud1'], as_model=False))
                         .rename(columns={'name':'Counterparty'})).drop(['expectedName','id'],axis=1)

    measure_sum = df.merge(Counterparty_df, how='left', on='Counterparty')
    # 根据 ud1 列的值修改 Measure 列
    measure_sum['Measure'] = measure_sum['ud1'].apply(lambda x: 'IC_Amt' if x == 'Y' else 'Ext_Amt')
    measure_sum = measure_sum.drop(['ud1'], axis=1)
    return measure_sum


def budget_nocp_processing(p1,p2):
    Year = p2['Year_wb1']
    last_Year = str(int(Year)-1)
    Version = p2['Version_wb1']
    Entity_FR = p2['Entity_FR_wb1']
    cube = FinancialCube('sub_fund_cube')
    # 获取资金cube数据
    fix_budget_adjb = "Year{%s}->Scenario{budget_adjb}->Version{%s}->Period{Base(TotalPeriod,0);Noperiod}->Comprehensive{nocompr}->Counterparty{sum}->" \
               "Entity_FR{%s}->Measure{Expenses}->Account_zijin{CF02040201;CF02040301;CF02040401;CF0307010101;CF0307010201;CF0307010202;CF0307010301;CF030303;CF0204010103}->"\
               "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                % (Year,Version,Entity_FR)
    df_budget = cube.query(fix_budget_adjb, compact=False)

    df_budget['Counterparty'] = 'nocp'
    def_fix_budget =  "Year{%s}->Scenario{budget_adjb}->Version{%s}->Period{Base(TotalPeriod,0);Noperiod}->Comprehensive{nocompr}->Counterparty{nocp}->" \
                      "Entity_FR{%s}->Measure{Expenses}->Account_zijin{CF02040201;CF02040301;CF02040401;CF0307010101;CF0307010201;CF0307010202;CF0307010301;CF030303;CF0204010103}->" \
                      "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                      % (Year, Version, Entity_FR)

    cube.delete(def_fix_budget)
    cube.save(df_budget)


    fix_forecast = "Year{%s}->Scenario{Forecast}->Version{%s}->Period{Base(TotalPeriod,0)}->Comprehensive{nocompr}->Counterparty{sum}->" \
               "Entity_FR{%s}->Measure{Expenses}->Account_zijin{CF02040201;CF02040301;CF02040401;CF0307010101;CF0307010201;CF0307010202;CF0307010301;CF030303;CF0204010103}->"\
               "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                % (last_Year,Version,Entity_FR)
    df_forecast = cube.query(fix_forecast, compact=False)

    df_forecast['Counterparty'] = 'nocp'
    def_fix_forecast =  "Year{%s}->Scenario{Forecast}->Version{%s}->Period{Base(TotalPeriod,0)}->Comprehensive{nocompr}->Counterparty{nocp}->" \
                      "Entity_FR{%s}->Measure{Expenses}->Account_zijin{CF02040201;CF02040301;CF02040401;CF0307010101;CF0307010201;CF0307010202;CF0307010301;CF030303;CF0204010103}->" \
                      "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                      % (last_Year, Version, Entity_FR)

    cube.delete(def_fix_forecast)
    cube.save(df_forecast)

    print(1)

def main(p1, p2):
    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    countAll = countSuccess = countError = 0
    countMsg = f"{start_time} 开始执行实际数接入审核模型 rev_profit_cube 任务\n"

    try:
        main_processing(p1, p2)
        sum_actual_period_processing(p1, p2)
        sum_budget_period_processing(p1, p2)
        budget_nocp_processing(p1,p2)
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
    para2 = {'elementName': 'inter_co_tx_dtl',
             'folderId': 'DIRcc223f9bef26',
             'sheetName': '1.2公司间往来明细表(调整之后)',
             'sheetId': 'SHT69b9969d507a43d8b34510d9b17c4ab0',
             'Year_wb1': '2026',
             'Entity_FR_wb1': 'Y3320231453',
             'Version_wb1': 'V1',
             'Commercial_wb1': 'YT020201'}
  # 修改这里可测试不同年份
    main(para1, para2)
