# -*- coding: utf-8 -*-
'''
@file    : safety_calc.py
@Time    : 2025-09-19
@Author  : chen
@Software:
@Desc    : 安全生产费进cube
'''

from deepfos.element.datatable import DataTableMySQL
import pandas as pd
from deepfos.element.finmodel import FinancialCube



def process(p2):
    pov = {
        # 'Version': 'Y1',
        # 'Department': 'Operation',
        'Tax': 'Tax',
        # 'Project_Type': 'NoProject_Type',
        # 'Format': 'NoFormat',
        # 'PM_Chars': 'NoPM_Chars',
        'Misc1': 'Nomisc1',
        'Misc2': 'Nomisc2',
        'Misc3': 'Nomisc3',
        'Material': 'Nomaterial',
        'Measure': 'Expenses'
    }

    Year = p2['Year_wb1']
    Entity = p2['Entity_wb1']
    # 1. 从MySQL表查询数据（精确筛选月份列）
    tb_safety = DataTableMySQL('Safety_Production_Expense_List')
    # 核心维度列（固定）
    dim_cols = ['Year', 'Version', 'Scenario', 'Entity', 'Account', 'Format',
                'Project_Type', 'PM_Chars', 'Department']
    # 明确指定12个月份列（仅Jan-Dec，排除其他业务字段）
    month_cols = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                  'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    print(f"精确指定的月份列：{month_cols}")  # 确认月份列正确
    cols = dim_cols + month_cols

    tb_safety = DataTableMySQL('Safety_Production_Expense_List')
    if Entity == 'Base(1,0)':
        where = "Year = '%s' " % (Year)
    elif Entity != 'Base(1,0)':
        where = "Year = '%s' and Entity = '%s'" % (Year, Entity)

    df_safety = tb_safety.select(columns=cols,where=where)
    # 【新增逻辑】当查询结果为空时，清理cube并返回
    if df_safety.empty:
        print(f"未查询到 {Year}年-{Entity} 的数据，执行cube清理操作")
        # 初始化cube连接
        cube = FinancialCube(element_name='S_Cube')
        # 清理条件与写入时保持一致
        delete_pov = {
            'Year': Year,
            'Entity': Entity,
            'Scenario': 'Budget',
            'Period': [str(i) for i in range(1, 13)],  # 1-12月
            'Account': 'Base(SPL010207,0)',
            'Tax': 'Tax;NoTax',
            'Version': 'Y1',
            'Department': 'Operation ',
            'Project_Type': 'NoProject_Type',
            'Format': 'NoFormat',
            'PM_Chars': 'NoPM_Chars',
            'Misc1': 'Nomisc1',
            'Misc2': 'Nomisc2',
            'Misc3': 'Nomisc3',
            'Material': 'Nomaterial',
            'Measure': 'Expenses'
        }
        # 执行清理
        cube.delete(delete_pov)
        print(f"已清理 {Year}年-{Entity} 在Cube中的安全生产费数据")
        return  # 清理后直接返回，不执行后续操作

    # 2. 处理空值（避免聚合后列被删除）
    df_safety[month_cols] = df_safety[month_cols].fillna(0)  # 空值→0
    # 确保月份列为数值类型
    for col in month_cols:
        df_safety[col] = pd.to_numeric(df_safety[col], errors='coerce').fillna(0)

    # 3. 按维度分组聚合（求和）
    group_keys = dim_cols
    df_safety_agg = df_safety.groupby(group_keys, as_index=False)[month_cols].sum()
    print(f"聚合后保留的列：{df_safety_agg.columns.tolist()}")  # 确认月份列全保留

    # 4. 月份列重命名（Jan→1，...，Dec→12）
    period_mapping = {
        'Jan': '1', 'Feb': '2', 'Mar': '3', 'Apr': '4', 'May': '5', 'Jun': '6',
        'Jul': '7', 'Aug': '8', 'Sep': '9', 'Oct': '10', 'Nov': '11', 'Dec': '12'
    }
    df_safety_agg = df_safety_agg.rename(columns=period_mapping)
    # 提取重命名后的月份列（确保与映射一致）
    renamed_month_cols = list(period_mapping.values())
    print(f"重命名后的月份列：{renamed_month_cols}")

    # 5. 补齐Cube所需的默认维度
    for k, v in pov.items():
        df_safety_agg[k] = v

    # 6. 列转行（使用重命名后的月份列）
    # index_cols = dim_cols + list(pov.keys())

    # df_result = df_safety_agg.melt(
    #     id_vars=index_cols,
    #     value_vars=renamed_month_cols,  # 此时列名一定存在
    #     var_name='Period',
    #     value_name='data'
    # )

    # 7. 写入Cube前删除旧数据（原有逻辑保留）
    cube = FinancialCube(element_name='S_Cube')
    delete_pov = {
        'Year': Year,
        'Entity': Entity,
        'Scenario': 'Budget',
        'Period': renamed_month_cols,
        'Account': 'SPL01020701',
        'Tax': 'Tax;NoTax',
        'Version': 'Y1',
        'Department': 'Operation',
        'Project_Type': 'NoProject_Type',
        'Format': 'NoFormat',
        'PM_Chars': 'NoPM_Chars',
        'Misc1': 'Nomisc1',
        'Misc2': 'Nomisc2',
        'Misc3': 'Nomisc3',
        'Material': 'Nomaterial',
        'Measure': 'Expenses'
    }
    cube.delete(delete_pov)
    cube.save_unpivot(data=df_safety_agg,unpivot_dim="Period")
    print(f"安全生产费数据已成功写入Cube：{Year}年-{Entity}，共{len(df_result)}条月度合计数据")


def main(p1, p2):
    process(p2)

if __name__ == '__main__':
    from BIZ.__debug import para1, para2
    para2 =  {'elementName': 'Safety_Expenses',
              'folderId': 'DIR82a2f129af06',
              'sheetName': '安全生产费',
              'sheetId': 'SHT963bf8f4dddf4253a472135f8cb03eab',
              'Year_wb1': '2026',
              'Entity_wb1': 'Y5120241763',
              'Department_wb1': 'Operation',
              'Scenario_wb1': 'Budget',
              'Version_wb1': 'Y1',
              'Account_wb1': 'SPL01020702',
              'Format_wb1': 'NoFormat',
              'Project_Type_wb1': 'NoProject_Type',
              'PM_Chars_wb1': 'NoPM_Chars',
              'ItemName_st1': 'SPL01020702'}


    main(para1, para2)