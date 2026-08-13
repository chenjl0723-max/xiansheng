# -*- coding: utf-8 -*-
'''
@file    : fund_push_review_cube.py
@Desc    : 资金预算 进 资金审核 rev_fund_cube 财务模型
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


def public_query(year,Version,df):
    dt = DataTableMySQL('project_public_data_Year')
    where = "Year = '%s' and Version = '%s'"%(year,Version)
    entity_df = dt.select(columns=['Year','Version','project_cd','Bud_ext_idtf'],where=where).rename(columns={'project_cd':'Entity_FR','Bud_ext_idtf':'bud_incr_stk'})

    df = pd.merge(df,entity_df,how='left',on=['Year','Version','Entity_FR'])
    df = df.dropna(subset=['bud_incr_stk'])
    return df


def get_Consol(row):
    year = row['Year']
    period = row['Period']
    merge_date = row['merge_date']

    # 任意关键字段为空 → C99
    if pd.isna(merge_date):
        return 'C99'

    try:
        # 当前记录的年月（例如 2026年4月 → 202604）
        current_month = int(str(period).strip())
        current_ym = int(year) * 100 + current_month

        # 并表日期的年月
        merge_dt = pd.to_datetime(merge_date)
        merge_ym = merge_dt.year * 100 + merge_dt.month

        # 比较年月
        if current_ym >= merge_ym:
            return 'C01'  # 并表
        else:
            return 'C02'  # 出表

    except Exception:
        return 'C99'

def get_Misc2(df,Version,year):
    # 预算主体表
    entity_budget_middle = DataTableMySQL('Corp_Project_Target')
    if Version in ['V1', 'V2', 'V3']:
        where = "year ='%s' and version = 'V3'" % year
    elif Version == 'V4':
        where = "year ='%s' and version = 'V4'" % year


    misc_df = entity_budget_middle.select(columns=['proj_cd','budget_entity', 'year','merge_date'], where=where).rename(columns={
        'year':'Year',
        'proj_cd':'Entity_FR'})


    df = pd.merge(df,misc_df,how='left',on=['Year','Entity_FR']).rename(columns={
        'budget_entity':'Misc2',
    }).drop_duplicates()

    return df

def actual_processing(p1, p2,Version,Year,cube):
    """实际数主处理函数"""
    year = str(int(Year) - 1)


    act_middle = DataTableMySQL('actual_data_zijin')
    where =  "year = '%s' and period !='Sep' " % year
    act_df = act_middle.select(columns=['year','period','account_cd','entity_cd','pattern','projtype','consv_incrmt','data'],where=where).rename(columns={
        'year':'Year',
        'entity_cd':'Entity_FR',
        'account_cd': 'Account_zijin',
        'period': 'Period',
        'pattern': 'Pattern',
        'projtype': 'Project_Type',
        'consv_incrmt': 'inc_stock'
    })

    # 生成预算主体
    act_df = get_Misc2(act_df,Version,year)
    # 生成是否出并表
    act_df['Consol'] = act_df.apply(get_Consol, axis=1)

    act_df['Counterparty'] = 'nocp'
    act_df['Measure'] = 'Expenses'
    act_df['Misc1'] = 'nomisc1'
    act_df['Scenario'] = 'Actual'
    act_df['Version'] = Version


    # 关联项目业态
    dim_FR = Dimension('Entity_FR')
    df_FR = pd.DataFrame(dim_FR.query(expression="Base(#root,0)", fields=['name','ud7'], as_model=False)).drop(['id','expectedName'],axis=1).drop_duplicates()

    act_df =  act_df.merge(df_FR.rename(columns={
        'name':'Entity_FR',
        'ud7':'Commercial'
        })
        , how='left', on='Entity_FR')

    del act_df['merge_date']
    act_df = act_df.dropna(subset=['Pattern', 'Project_Type', 'inc_stock', 'Consol','Commercial','Misc2'])

    if not act_df.empty:
        push_to_cube(act_df, year, Version,'Actual')




def forecast_processing(p1, p2,Version,Year,cube):
    """预测数主处理函数"""
    Year = str(int(Year) - 1)
    # cube = FinancialCube('sub_profit_cube')
    fix  = "Year{%s}->Scenario{Forecast}->Version{%s}->Period{10;11;12;adjust}->" \
               "Entity_FR{Base(D000001,0)}->Measure{Expenses}->Account_zijin{Base(CF00,0)}->"\
               "Counterparty{nocp}->Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                % (Year,Version)

    df = cube.query(fix, compact=False)

    dim_FR = Dimension('Entity_FR')
    df_FR = pd.DataFrame(dim_FR.query(expression="Base(#root,0)", fields=['name','ud6','ud9','ud10'], as_model=False)).drop(['id','expectedName'],axis=1).drop_duplicates()

    df =  df.merge(df_FR.rename(columns={
        'name':'Entity_FR',
        'ud6':'inc_stock',
        'ud9':'Project_Type',
        'ud10':'Pattern',
        })
        , how='left', on='Entity_FR').drop(['Comprehensive'],axis=1)

    # 生成预算主体
    df = get_Misc2(df,Version,Year)
    # 生成是否出并表
    df['Consol'] = df.apply(get_Consol, axis=1)

    del df['merge_date']
    df = df.dropna(subset=['Pattern', 'Project_Type', 'inc_stock', 'Consol', 'Commercial', 'Misc2'])

    if not df.empty:
        push_to_cube(df, Year, Version, 'Forecast')



def budget_processing(p1, p2,Version,Year,cube):
    """预算数主处理函数"""

    # cube = FinancialCube('sub_profit_cube')
    fix  = "Year{%s}->Scenario{budget_adja}->Version{%s}->Period{Base(TotalPeriod,0)}->" \
               "Entity_FR{Base(D000001,0)}->Measure{Expenses}->Account_zijin{Base(CF00,0)}->"\
               "Counterparty{nocp}->Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                % (Year,Version)

    df = cube.query(fix, compact=False)

    dim_FR = Dimension('Entity_FR')
    df_FR = pd.DataFrame(dim_FR.query(expression="Base(#root,0)", fields=['name','ud6','ud9','ud10'], as_model=False)).drop(['id','expectedName'],axis=1).drop_duplicates()

    df =  df.merge(df_FR.rename(columns={
        'name':'Entity_FR',
        'ud6':'inc_stock',
        'ud9':'Project_Type',
        'ud10':'Pattern',
        })
        , how='left', on='Entity_FR').drop(['Comprehensive'],axis=1)

    # 生成预算主体
    df = get_Misc2(df,Version,Year)
    # 生成是否出并表
    df['Consol'] = df.apply(get_Consol, axis=1)

    del df['merge_date']
    df = df.dropna(subset=['Pattern', 'Project_Type', 'inc_stock', 'Consol', 'Commercial', 'Misc2'])

    if not df.empty:
        push_to_cube(df, Year, Version, 'Budget')




def push_to_cube(df, year, Version,Scenario):
    """推送数据到 rev_profit_cube"""

    # 写入 Cube
    cube = FinancialCube('rev_fund_cube')

    # 清空对应位置（推荐做法）
    expr_dict = {
        "Year": year,
        "Scenario": Scenario,
        "Entity_FR": "IDescendant(#root,0)",
        "Account_zijin": "Base(CF00,0)",
        "Counterparty":'nocp',
        "Version": Version,
        "Measure":'Expenses',
    }
    cube.insert_null(expr_dict)


    # 过滤缺失科目
    account_dim = Dimension('Account_zijin')
    account_list = pd.DataFrame(account_dim.query(expression="Base(#root,0)", fields=['name'], as_model=False))
    df = df[df['Account_zijin'].isin(account_list['name'])]


    # 保存数据
    cube.save(df, chunksize=200000)



def actual_noperiod_processing(p1, p2, Version, Year):
    """实际数全年合计主处理函数"""
    Year = str(int(Year) - 1)



    sc_10 = Variable('Variable').get('zj_10_scenario')
    sc_11 = Variable('Variable').get('zj_11_scenario')
    sc_12 = Variable('Variable').get('zj_12_scenario')


    cube = FinancialCube('rev_fund_cube')
    fix_act_adjb = "Year{%s}->Scenario{Actual}->Version{%s}->Period{Base(TotalPeriod,0)}->Counterparty{nocp}->" \
                      "Entity_FR{IBase(D000001,0)}->Measure{Expenses}->Account_zijin{Base(CF00,0)}->" \
                      "Misc1{nomisc1}->Misc2{Base(budget_dept,0)}" \
                      % (Year, Version)

    act_df =  cube.query(fix_act_adjb, compact=False)
    fix_forecast = "Year{%s}->Scenario{Forecast}->Version{%s}->Period{10;11;12}->Counterparty{nocp}->" \
                   "Entity_FR{IBase(D000001,0)}->Measure{Expenses}->Account_zijin{Base(CF00,0)}->" \
                   "Misc1{nomisc1}->Misc2{Base(budget_dept,0)}" \
                   % (Year, Version)

    df_forecast = cube.query(fix_forecast, compact=False)

    if act_df.empty and df_forecast.empty:
        print("实际数和预测数都为空，无需处理。")
        return


    # 根据scenario配置确定数据来源

    if sc_10 == 'Forecast' and sc_11 == 'Forecast' and sc_12 == 'Forecast':
        # 10、11、12月均为预测 → 实际数只取 Sep
        act_periods = act_df[act_df['Period'].isin(['1','2','3','4','5','6','7','8','9'])]
        forecast_periods = df_forecast[df_forecast['Period'].isin(['10', '11', '12'])]
        combined_df = pd.concat([act_periods, forecast_periods], ignore_index=True)

    elif sc_10 == 'Actual_adjb' and sc_11 == 'Forecast' and sc_12 == 'Forecast':
        # sc_10 为 Actual → 实际数取 Sep + 10月，预测取 11 + 12月
        act_periods = act_df[act_df['Period'].isin(['1','2','3','4','5','6','7','8','9', '10'])]
        forecast_periods = df_forecast[df_forecast['Period'].isin(['11', '12'])]
        combined_df = pd.concat([act_periods, forecast_periods], ignore_index=True)

    elif sc_10 == 'Actual_adjb' and sc_11 == 'Actual_adjb' and sc_12 == 'Forecast':
        # sc_11 为 Actual → 实际数取 Sep + 10 + 11月，预测取 12月
        act_periods = act_df[act_df['Period'].isin(['1','2','3','4','5','6','7','8','9', '10', '11'])]
        forecast_periods = df_forecast[df_forecast['Period'] == '12']
        combined_df = pd.concat([act_periods, forecast_periods], ignore_index=True)

    else:
        # 默认情况：全部使用实际数（Sep,10,11,12）
        combined_df = act_df[act_df['Period'].isin(['1','2','3','4','5','6','7','8','9', '10', '11', '12'])].copy()


    print(combined_df)

    # 计算全年合计

    # 按维度分组求和，排除Period维度
    group_cols = [col for col in combined_df.columns if col not in ['Period', 'data','Scenario']]
    yearly_sum = combined_df.groupby(group_cols, as_index=False)['data'].sum()

    # 设置Period为'Noperiod'
    yearly_sum['Period'] = 'Noperiod'
    yearly_sum['Scenario'] = 'Actual'


    def_fix =  "Year{%s}->Scenario{Actual}->Version{%s}->Period{Noperiod}->Counterparty{nocp}->" \
                      "Entity_FR{IBase(D000001,0)}->Measure{Expenses}->Account_zijin{Base(CF00,0)}->" \
                      "Misc1{nomisc1}->Misc2{nomisc2}->Commercial{Base(YT00,0)}" \
                      % (Year, Version)

    cube.delete(def_fix)
    # 打印结果
    print("实际数全年合计数据（Period=Noperiod）：")
    cube.save(yearly_sum, chunksize=200000)


def main(p1, p2):
    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    countAll = countSuccess = countError = 0
    countMsg = f"{start_time} 开始执行资金填报进审核模型 rev_profit_cube 任务\n"

    try:
        # 统一获取全局参数
        Version = Variable('Variable').get('Edit_Ver')

        if 'Year' in p2 and p2['Year']:
            Year = str(p2['Year'])
        else:
            Year = Variable('Variable').get('BudYear')

        cube = FinancialCube('sub_fund_cube')
        actual_processing(p1, p2, Version, Year,cube)
        forecast_processing(p1, p2, Version, Year,cube)
        budget_processing(p1, p2, Version, Year,cube)
        actual_noperiod_processing(p1, p2, Version, Year)
        countAll = countSuccess = 1
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 资金填报进审核模型 rev_profit_cube 处理完成\n"
    except Exception as e:
        countError = 1
        countAll = 1
        error_detail = traceback.format_exc()
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 资金填报进审核模型 rev_profit_cube 处理失败: {str(e)}\n"
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