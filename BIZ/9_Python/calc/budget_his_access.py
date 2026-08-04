# -*- coding: utf-8 -*-
'''
@file    : act_access.py
@Time    :
@Author  : XMX
@Software: PyCharm
@Desc    : 北控水务 接口数据操作主入口 涉及：主数据（Entity、Material），实际数
'''


try:
    from BIZ.__debug import para1, para2
    # print(para1)
except ImportError:
    para1 = para2 = {}
import pandas as pd
import datetime
import traceback
from deepfos.db.mysql import MySQLClient
from deepfos.element.finmodel import FinancialCube
from deepfos.element.datatable import DataTableClickHouse as ck
from deepfos.element.datatable import DataTableMySQL
from deepfos.element.variable import Variable
from deepfos.element.dimension import Dimension, DimMember
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)

class Bud_cube:
    def __init__(self,p1,p2):
        variable = Variable(element_name='Variable')
        BudYear = variable.get('BudYear')
        if p2['year'] == '空':
            year_1 = str(int(BudYear) - 1)
            year_2 = str(int(BudYear) - 2)
            year_3 = str(int(BudYear) - 3)
            Year = year_1 + ',' + year_2 + ',' + year_3
            month_begin = 1
            month_end = 12
        elif p2['year'] != '空' and p2['month_begin'] != '空' and p2['month_end'] != '空':
            year = p2['year']
            year_1 = str(int(year) - 1)
            year_2 = str(int(year) - 2)
            year_3 = str(int(year) - 3)
            Year = year_1 + ',' + year_2 + ',' + year_3
            month_begin = int(p2['month_begin'])
            month_end = int(p2['month_end'])
            BudYear = str(int(p2['year']) + 1)

            print(Year)

        where = "Year in (%s) and ((Period >= %d and Period <= %d) or Period = 99)" % (
            Year, month_begin, month_end)
        """
        从实际数中间表取数，按照项目表project_cd过滤，并补齐format, Project_Type_code, pro_characteristics
        """

        # 获取实际数中间表数据
        budget_data_tabl = DataTableMySQL("budget_his_data")
        budget_columns = [
            'Entity_cd',
            'Entity_name',
            'Year',
            'Period',
            'Account_cd',
            'Account_name',
            'Data',
            'Tax_flag',
            'Data_source',
            'Update_Time'
        ]
        self.df_budget = budget_data_tabl.select(columns=budget_columns,where=where)
        # print(self.df_budget)

        # 获取项目主数据表数据
        project_table = DataTableMySQL("Project_Basic_Information")
        project_columns = [
            'manage_region_name',
            'manage_area_name',
            'project_corp_name',
            'manage_org_name',
            'project_cd',
            'project_name',
            'format',
            'inv_pattern_cd',
            'pro_characteristics',
            'nature',
            'chg_type',
            'chg_date',
            'chg_scope',
            'new_date',
            '_id',
            'year',
            'project_corp_cd',
            'manage_org_cd',
            'contract_information',
            'manage_region_cd',
            'manage_area_cd',
            'format_cd',
            'Project_Type_code',
            'Project_Type_name',
            'inv_pattern',
            'approve_status'
        ]

        project_table = DataTableMySQL("Entity_td")
        self.df_project = pd.DataFrame(project_table.select(columns=['name']))

        # 获取历史预算数科目映射表数据（如果需要映射Account_cd，可在此处理；当前需求未明确指定，故暂不使用）
        mapping_table = DataTableMySQL("XYT_actual_mapping")
        mapping_columns = [
            'Account',
            # 'Account_name',
            'Material_code',
            'Account_cd',
            'Department'
        ]
        self.df_mapping = pd.DataFrame(mapping_table.select(columns=mapping_columns))

        # return df_target
        # df_merged['Account_name'] = df_merged['Account_name_mapped'].fillna(df_merged['Account_name'])
        # df_merged.drop(columns=['Account_name_mapped'], inplace=True)

        # 写入目标表（假设目标表名为Actual_Data_Processed，或根据实际需求调整）
        # target_table = DataTableMySQL("Actual_Data_Processed")
        # target_table.insert(df_merged.to_dict('records'))

    def df_process(self,p1,p2):
        # 注意：如果需要根据映射表过滤或补齐Account相关字段，可在此添加逻辑，例如merge df_budget 和 df_mapping on 'Account_cd'

        # 过滤实际数数据：只保留Entity_cd在项目表的project_cd中的记录
        df_budget_filtered = self.df_budget[self.df_budget['Entity_cd'].isin(self.df_project['name'])]

        # 补齐字段：通过Entity_cd (假设对应project_cd) merge项目表的format, Project_Type_code, pro_characteristics
        # df_merged = df_budget_filtered.merge(
        #     self.df_project[['project_cd', 'format_cd', 'Project_Type_code', 'pro_characteristics']],
        #     how='left',
        #     left_on='Entity_cd',
        #     right_on='project_cd'
        # ).drop(columns=['project_cd'])  # 移除多余的project_cd列

        # 如果需要使用映射表补齐或过滤，例如补齐Account_name（如果有差异）
        df_merged = df_budget_filtered.merge(self.df_mapping, how='left', on='Account_cd', suffixes=('', '_mapped'))
        acc_null = df_merged[df_merged['Account'].isnull()]
        df_merged = df_merged[df_merged['Account'].notnull()]

        print('插入失败的实际数',acc_null)


        df_merged = df_merged.rename(columns={
            'Entity_cd' : 'Entity',
            'Data' : 'data',
            'Tax_flag' : 'Tax',
            # 'format_cd' : 'Format',
            # 'Project_Type_code' : 'Project_Type',
            # 'pro_characteristics' : 'PM_Chars',
            'Material_code' : 'Material',
        })

        # 查询税率
        taxrate_df = self.query_taxrate()

        df_merged['Format'] = 'NoFormat'
        df_merged['Project_Type'] = 'NoProject_Type'
        df_merged['PM_Chars'] = 'NoPM_Chars'
        df_merged['Misc1'] = 'Nomisc1'
        df_merged['Misc2'] = 'Nomisc2'
        df_merged['Misc3'] = 'Nomisc3'
        df_merged['Measure'] = 'Expenses'
        df_merged['Version'] = 'Y1'
        df_merged['Scenario'] = 'Budget'

        # 合并税率数据，仅针对Tax='Notax'的数据
        df_notax = df_merged[df_merged['Tax'] == 'Notax']
        # df_tax = df_merged[df_merged['Tax'] != 'Notax']

        df_notax_rate = df_notax.merge(
            taxrate_df[['Account', 'Entity', 'Taxrate']],
            how='left',
            left_on=['Entity','Account'],
            right_on=['Entity', 'Account'],
            # suffixes=('', '_Tax')
        )

        # 计算含税金额：Tax = Notax * (1 + Taxrate)
        df_notax_rate['data'] = df_notax_rate.apply(
            lambda row: row['data'] * (1 + row['Taxrate']) if pd.notnull(row['Taxrate']) else row['data'],
            axis=1
        )
        df_notax_rate['Tax'] = 'Tax'  # 更新Tax字段为'Tax'
        df_Tax = df_notax_rate.drop(columns=['Taxrate'])  # 删除临时Taxrate列

        # 合并含税和不含税数据
        df_merged = pd.concat([df_notax, df_Tax], ignore_index=True)




        # 选择目标字段
        target_columns = [
            'Period',
            'Year',
            'Scenario',
            'Version',
            'Entity',
            'Measure',
            'Format',
            'Project_Type',
            'PM_Chars',
            'Tax',
            'Department',
            'Account',
            'Material',
            'Misc1',
            'Misc2',
            'Misc3',
            'data'
        ]
        df_target = df_merged[target_columns]
        print(1)
        return df_target



    def query_taxrate(self):
        variable = Variable(element_name='Variable')
        BudYear = variable.get('BudYear')
        # 税率转换逻辑
        cube_bewg = FinancialCube('S_Cube', path='/1_Cube/Financial_Model')
        # 查询税率数据
        tax_rate_query = (
            "Year{%s}->Scenario{Actual}->Version{Y1}->Entity{Base(#root,0)}->Period{Noperiod}->"
            "Material{Base(Total,0)}->Tax{Taxrate}->Account{Base(SPL01,0);SYW0301;SYW0302;SYW0303;"
            "SYW0304;SYW0305;SYW0306;SYW0307;SYW0308}->Department{Base(#root,0)}->"
            "Measure{Base(#root,0)}->Format{Base(#root,0)}->"
            "Project_Type{Base(#root,0)}->PM_Chars{Base(#root,0)}->"
            "Misc1{Nomisc1}->Misc2{Nomisc2}->Misc3{Nomisc3}"
            % str(int(BudYear) - 1)
        )
        df_tax_rate = cube_bewg.query(tax_rate_query, compact=False)
        df_tax_rate = df_tax_rate.rename(columns={'data': 'Taxrate'})
        return df_tax_rate



def del_cube(p2):
    cube_bewg = FinancialCube('S_Cube', path='/1_Cube/Financial_Model')
    variable = Variable(element_name='Variable')
    BudYear = variable.get('BudYear')
    year = str(int(p2['year']) - 1)
    fix_del = "Year{%s}->Account{%s}->Scenario{%s}->Tax{%s}->Version{%s}->Material{%s}->Entity{%s}" % (
    year,"Base(SPL01,0)","Budget","Tax;Notax","Y1","01;02;03;04;05;98;99;100;Nomaterial","Base(#root,0)")
    cube_bewg.delete(fix_del)


def df_save(df):
    cube_bewg = FinancialCube('S_Cube', path='/1_Cube/Financial_Model')
    # 数据存入cube
    cube_bewg.save(df)


# 查询cube数据
def fetch_input_data(scenario, year, periods):
    """从 Cube 查询输入数据"""
    cube = FinancialCube('S_Cube', path='/1_Cube/Financial_Model')

    account_expr = "Account{Base(SPL0101,0);Base(SPL0102,0)}"
    entity_expr = "Entity{Base(1,0)}"
    period_expr = f"Period{{{';'.join(periods)}}}"
    pov = {
        'Year': year,
        'Scenario': scenario,
        'Version': 'Y1',
        # 'Department': 'Operation',
        # 'Tax': ['Tax','Notax'],
        'Project_Type': 'NoProject_Type',
        'Format': 'NoFormat',
        'PM_Chars': 'NoPM_Chars',
        'Misc1': 'Nomisc1',
        'Misc2': 'Nomisc2',
        'Misc3': 'Nomisc3',
        # 'Material': 'Nomaterial',
        'Measure': 'Expenses'
    }
    exp = f"{account_expr}->{entity_expr}->Year{{{year}}}->Scenario{{{scenario}}}->{period_expr}->Tax{{Tax;Notax}}->Department{{Operation;Equipment}}->Material{{Base(Total,0)}}"
    data = cube.query(expression=exp, pov=pov, compact=False)
    return data


# 计算实际数全年合计
def noperiod_calc(p2):
    cube = FinancialCube('S_Cube', path='/1_Cube/Financial_Model')
    Forcast = Variable('Variable').get('Forcast')
    BudYear = Variable('Variable').get('BudYear')
    act_Year = str(int(p2['year']) - 1)

    if Forcast == 'Forecast':
        actual_detail = fetch_input_data('Actual', act_Year, ['1','2','3','4','5','6','7','8','9'], )
        forecast_detail = fetch_input_data('Forecast', act_Year, ['10', '11', '12'])
        forecast_detail['Scenario'] = 'Actual'
        # budget_detail = self.fetch_input_data('Budget', self.year, self.periods_budget, self.account_budget)
        # noperiod_result = noperiod_cala(actual_detail, forecast_detail)

    elif Forcast == 'Actual':
        actual_detail = fetch_input_data('Actual', act_Year, ['1','2','3','4','5','6','7','8','9','10','11','12'])
        forecast_detail = pd.DataFrame()
        # forecast_detail = self.fetch_input_data('Forecast', self.last_year, self.periods_forecast, self.account_actual)
        # budget_detail = self.fetch_input_data('Budget', self.year, self.periods_budget, self.account_budget)
        # noperiod_result = noperiod_cala(actual_detail)

    df_noperiod = pd.concat([actual_detail, forecast_detail], ignore_index=True)
    df_noperiod["Period"] = "Noperiod"
    df_noperiod = df_noperiod.groupby(
        by=[
            "Account",
            "Year",
            "Scenario",
            "Measure",
            "Period",
            "Entity",
            "Version",
            "Material",
            "Department",
            "Tax",
            'Project_Type',
            'Format',
            'PM_Chars',
            "Misc1",
            "Misc2",
            "Misc3",
        ],
        as_index=False,
    ).sum()

    print(1)

    # entity_expr = self.entity if self.entity else "Base(1,0)"
    pov =  {'Version': 'Y1',
            'Department': ['Operation','Equipment'],
            'Tax': ['Tax','Notax'],
            'Project_Type': 'NoProject_Type',
            'Format': 'NoFormat',
            'PM_Chars': 'NoPM_Chars',
            'Misc1': 'Nomisc1',
            'Misc2': 'Nomisc2',
            'Misc3': 'Nomisc3',
            'Material': 'Base(Total,0)',
            'Measure': 'Expenses',
            'Year': act_Year,
            'Scenario': 'Actual',
            'Period': 'Noperiod',
            'Account': 'Base(SPL0101,0);Base(SPL0102,0)',
            'Entity': 'Base(1,0)'}
    cube.delete(pov)

    cube.save(data=df_noperiod)


def main(p1, p2):
    p2 = { 'year': "2026", 'month_begin': "1", 'month_end': "12", 'entity': "空"}
    update_Basic_Information = Bud_cube(p1,p2)
    df = update_Basic_Information.df_process(p1, p2)
    del_cube(p2)
    df_save(df)

    noperiod_calc(p2)





# debug
if __name__ == '__main__':
    # p1 = {}
    para2 = {'year': '2026', 'month_end': '12', 'month_begin': '1', 'entity': '空'}
    main(para1, para2)


