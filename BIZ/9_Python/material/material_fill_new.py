# -*- coding: utf-8 -*-
'''
@file    : material_fill.py
@Time    : 2025-09-28
@Author  : XMX
@Software:
@Desc    : 根据 MySQL 表的物料编码，查询 Cube 中 6 个科目的数据，补齐缺失科目记录（值为 0），插入到 Cube
'''

import traceback
import pandas as pd
from deepfos.element.datatable import DataTableMySQL
from deepfos.element.finmodel import FinancialCube

class MaterialFill:
    def __init__(self, p2):
        self.year = p2['Year_wb1']  # e.g., '2026'
        self.entity = p2['Entity_wb1']
        self.p2 = p2
        self.cube_name = 'S_Cube'
        self.folder_id = '/1_Cube/Financial_Model'

        # 固定维度，使用 Measure=Nomeasure 以匹配 Cube 数据
        self.fixed_pov = {
            'Version': 'Y1',
            'Department': 'Operation',
            'Tax': 'Tax',
            'Project_Type': 'NoProject_Type',
            'Format': 'NoFormat',
            'PM_Chars': 'NoPM_Chars',
            'Misc1': 'Nomisc1',
            'Misc2': 'Nomisc2',
            'Misc3': 'Nomisc3',
            'Measure': 'Expenses'
        }

        # 科目列表
        self.accounts = ['SYW0309', 'SYW0310', 'SYW0311', 'SYW0312', 'SYW0313', 'SPL01020101']

    def fetch_material_data(self):
        """从 MySQL 表查询原材料数据"""
        try:
            material_table = DataTableMySQL('Raw_material_non_cp_price')
            where = f"Year = '{self.year}' AND Entity = '{self.entity}'"
            df_material = material_table.select(where=where)
            print(f"查询到原材料数据：\n{df_material[['Ingredient']]}")
            return df_material
        except Exception as e:
            print(f"查询数据错误: {str(e)}")
            traceback.print_exc()
            return pd.DataFrame()

    def generate_and_insert_zero_data(self, df_material):
        """查询 Cube 数据（df1），生成所有物料-科目组合（df2），合并 df1 和 df2，插入缺失记录到 Cube"""
        try:
            cube = FinancialCube(element_name=self.cube_name)

            # 检查物料数据是否为空
            if df_material.empty:
                print("物料数据为空，无法生成科目记录。")
                return

            # 查询 Cube 数据（df1）
            material_expr = f"Material{{{';'.join(df_material['Ingredient'])}}}"
            account_expr = f"Account{{{';'.join(self.accounts)}}}"
            entity_expr = f"Entity{{{self.entity}}}"
            exp = f"{account_expr}->{material_expr}->{entity_expr}->Year{{{self.year}}}->Scenario{{Budget}}->Period{{1}}"
            df1 = cube.query(expression=exp, pov=self.fixed_pov, compact=False)
            print(f"df1（Cube 查询结果）：\n{df1[['Year', 'Entity', 'Scenario', 'Period', 'Material', 'Account', 'data']] if not df1.empty else '空'}")

            # 生成所有物料-科目组合（df2）
            expanded_rows = []
            for material in df_material['Ingredient']:
                for account in self.accounts:
                    insert_row = {
                        'Year': self.year,
                        'Entity': self.entity,
                        'Scenario': 'Budget',
                        'Period': '1',
                        'Material': material,
                        'Account': account,
                        'data': 0
                    }
                    insert_row.update(self.fixed_pov)
                    expanded_rows.append(insert_row)
            df2 = pd.DataFrame(expanded_rows)
            print(f"df2（生成的所有组合）：\n{df2[['Year', 'Entity', 'Scenario', 'Period', 'Material', 'Account', 'data']]}")

            # 合并 df1 和 df2，以 df1 为准，补齐 df2 的缺失记录
            if df1.empty:
                df_merged = df2
            else:
                # 使用 Material 和 Account 作为键，优先保留 df1
                df_merged = df1.merge(
                    df2,
                    on=['Year', 'Entity', 'Scenario', 'Period', 'Material', 'Account', 'Version', 'Department', 'Tax', 'Project_Type', 'Format', 'PM_Chars', 'Misc1', 'Misc2', 'Misc3', 'Measure'],
                    how='outer',
                    suffixes=('_df1', '_df2')
                )
                # 优先使用 df1 的 data 值，若 df1 缺失则用 df2 的 data（0）
                df_merged['data'] = df_merged['data_df1'].combine_first(df_merged['data_df2'])
                # 删除辅助列
                df_merged = df_merged.drop(columns=['data_df1', 'data_df2'])

            print(f"合并后的数据：\n{df_merged[['Year', 'Entity', 'Scenario', 'Period', 'Material', 'Account', 'data']]}")

            # 插入到 Cube
            if df_merged.empty:
                print("合并后数据为空，无需插入。")
                return

            try:
                cube.save(data=df_merged, data_column='data', need_check=True, data_audit=True)
                print(f"插入成功：{len(df_merged)} 条记录")
            except Exception as e:
                print(f"插入失败：错误={str(e)}")
                traceback.print_exc()

        except Exception as e:
            print(f"生成并插入数据错误: {str(e)}")
            traceback.print_exc()

    def process(self):
        """主处理逻辑"""
        # 查询数据
        df_material = self.fetch_material_data()
        if df_material.empty:
            print("未检索到数据。")
            return pd.DataFrame()

        # 生成并插入科目数据
        self.generate_and_insert_zero_data(df_material)

        print("原材料科目数据填报完成。")
        return df_material

def main(p1, p2):
    material = MaterialFill(p2)
    material.process()

# debug
if __name__ == '__main__':
    from BIZ._debug import para1, para2
    para2 = {
        'elementName': 'Material_Centralized',
        'folderId': 'DIR40444ad68bfb',
        'sheetName': '原材料填报信息',
        'sheetId': 'SHT5874187a888b4d2aa45bf7929aa19895',
        'Year_wb1': '2026',
        'Entity_wb1': 'Y4520241641',
        'Version_wb1': 'Y1',
        'Scenario_wb1': 'Budget',
        'Tax_wb1': 'Tax',
        'Project_Type_wb1': 'NoProject_Type',
        'Department_wb1': 'Operation',
        'Format_wb1': 'Format_all'
    }
    main(para1, para2)