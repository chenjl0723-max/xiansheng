# -*- coding: utf-8 -*-
'''
@file    : material_fill.py
@Time    :
@Author  : XMX
@Software:
@Desc    : "填报原材料信息时，；
# 原材料信息填报
'''

import traceback
import pandas as pd
from deepfos.element.dimension import Dimension
from deepfos.element.variable import Variable
from deepfos.element.datatable import DataTableMySQL
from deepfos.element.finmodel import FinancialCube
from deepfos.db.mysql import MySQLClient
from deepfos.lib.constant import DFLT_DATA_COLUMN


class MaterialFill:
    def __init__(self,p2):
        # 获取变量年
        self.year = p2['Year_wb1']
        self.entity = p2['Entity_wb1']

    def fetch_material_data(self):
        """从 MySQL 表查询原材料数据"""
        try:
            material_table = DataTableMySQL('Raw_material_non_cp_price')
            where = f"Year = '{self.year}' AND Entity = '{self.entity}'"
            df_material = material_table.select(where=where)
            return df_material
        except Exception as e:
            print(f"查询数据错误: {str(e)}")
            traceback.print_exc()
            return pd.DataFrame()

    def delete_cube_material(self,df_material):
        """删除 Cube 中不属于项目物料的数据，使用 Remove 函数"""
        try:
            cube = FinancialCube('S_Cube', path='/1_Cube/Financial_Model')
            if df_material.empty:
                print("物料数据为空，无法删除非项目物料。")
                material_expr = f"Material{{IDescendant(MQ,0)}}"
                exp = f"{material_expr}->Entity{{{self.entity}}}->Year{{{self.year}}}"
                exp_lastyear = f"{material_expr}->Entity{{{self.entity}}}->Year{{{str(int(self.year) - 1)}}}"
                cube.delete(expression=exp)
                cube.delete(expression=exp_lastyear)
                return

            # 获取项目物料列表
            project_materials = df_material['Ingredient'].unique()
            # 构建 Remove 表达式，排除项目物料
            material_expr = f"Material{{Remove(IDescendant(MQ,0),{','.join(project_materials)})}}"
            exp = f"{material_expr}->Entity{{{self.entity}}}->Year{{{self.year}}}"
            exp_lastyear = f"{material_expr}->Entity{{{self.entity}}}->Year{{{str(int(self.year)-1)}}}"

            print(f"删除非项目物料的表达式：{exp}")
            # 删除非项目物料的数据
            cube.delete(expression=exp)
            cube.delete(expression=exp_lastyear)
            print(f"已删除非项目物料数据，保留物料：{project_materials}")
        except Exception as e:
            print(f"删除非项目物料数据错误: {str(e)}")
            traceback.print_exc()

    def map_accounts(self, df):
        """根据物料编码映射科目并补充额外科目"""

        # 定义科目映射规则
        def get_account_code(material):
            if material.startswith('MQ05'):
                return 'SYW0312'  # 吨干泥药耗 (kg/tDS)
            elif material.startswith('MQ98'):
                return 'SYW0313'  # 吨泥药耗 (kg/t)
            else:
                return None  # 非 MQ05 和 MQ98，返回 None，后续处理 SYW0311 和 SYW0313

        # 创建扩展后的行列表
        expanded_rows = []

        for _, row in df.iterrows():
            material = row['Ingredient']
            account_code = get_account_code(material)

            # 定义基础科目列表
            base_accounts = [
                {'Account': 'SYW0309', '科目': '药量（吨）'},
                {'Account': 'SYW0310', '科目': '单价（元/吨）'},
                {'Account': 'SPL01020101', '科目': '原材料费用（万元）'}
            ]

            # 根据物料编码添加特定科目
            if account_code:
                # MQ05 或 MQ98，只添加对应的单一科目
                base_accounts.append({'Account': account_code, '科目': account_code})
            else:
                # 非 MQ05 和 MQ98，添加 SYW0311 和 SYW0313 两个科目
                base_accounts.append({'Account': 'SYW0311', '科目': '吨水药耗 (mg/L)'})
                base_accounts.append({'Account': 'SYW0313', '科目': '吨泥药耗 (kg/t)'})

            # 为每个科目生成一行
            for account_info in base_accounts:
                new_row = row.copy()
                new_row['Account'] = account_info['Account']
                new_row['科目'] = account_info['科目']
                expanded_rows.append(new_row)

        # 创建扩展后的 DataFrame
        df_expanded = pd.DataFrame(expanded_rows)
        print(f"扩展后数据：\n{df_expanded[['Ingredient', 'Account', '科目']]}")

        # 过滤无数据的行（假设存在 'Value' 列表示数据存在）
        if 'Value' in df_expanded.columns:
            df_expanded = df_expanded[df_expanded['Value'].notnull()]
            print(f"过滤后数据（Value 不为空）：\n{df_expanded[['Ingredient', 'Account', '科目', 'Value']]}")

        return df_expanded



    def check_and_insert_zero_if_empty(self, df_processed):
        """检查 Cube 中指定维度数据是否存在，如果为空则补 0 插入"""
        try:
            # 初始化 FinancialCube
            cube = FinancialCube('S_Cube', path='/1_Cube/Financial_Model')

            # 循环处理每个独特的 Material 和其扩展的 Account
            unique_materials = df_processed['Ingredient'].unique()

            for material in unique_materials:
                df_material_accounts = df_processed[df_processed['Ingredient'] == material]
                material_accounts = df_material_accounts['Account'].unique()

                # 构造 POV（视点）字典，包含所有必要维度
                pov = {
                    'Year': self.year,
                    'Entity': self.entity,
                    'Scenario': 'Budget',
                    'Period': '1',  # 假设 Period 成员为 '1'，表示 1 月
                    'Material': material,  # 原材料 (Ingredient)
                    'Version': 'Y1',
                    'Department': 'Operation',
                    'Tax': 'Tax',
                    'Project_Type': 'NoProject_Type',
                    'Format': 'NoFormat',
                    'PM_Chars': 'NoPM_Chars',
                    'Misc1':'Nomisc1',
                    'Misc2':'Nomisc2',
                    'Misc3':'Nomisc3',
                }

                # 构造维度表达式，查询该 Material 的所有科目
                account_expr = f"Account{{{';'.join(material_accounts)}}}"

                # 执行查询
                data = cube.query(
                    expression=account_expr,
                    pov=pov,
                    compact=False
                )


                # 确定现有科目（有非空值）
                existing_accounts = set()
                if not data.empty and DFLT_DATA_COLUMN in data.columns:
                    existing_accounts = set(data[data[DFLT_DATA_COLUMN].notnull()]['Account'].unique())

                # 找出缺失的科目（无数据或值为空）
                missing_accounts = [acc for acc in material_accounts if acc not in existing_accounts]


                # 如果查询结果为空，则补 0 插入
                if missing_accounts:
                    print(
                        f"为 Material={material} 在 Year={self.year}, Entity={self.entity}, Scenario=Budget, Period=1 补 0，缺失科目={missing_accounts}")

                    # 创建补 0 的 DataFrame
                    insert_rows = []
                    for account in missing_accounts:
                        insert_row = {
                            'Year': self.year,
                            'Entity': self.entity,
                            'Scenario': 'Budget',
                            'Period': '1',
                            'Material': material,
                            'Account': account,
                            'Version': 'Y1',
                            'Department': 'Operation',
                            'Tax': 'Tax',
                            'Project_Type': 'NoProject_Type',
                            'Format': 'NoFormat',
                            'PM_Chars': 'NoPM_Chars',
                            'Misc1': 'Nomisc1',
                            'Misc2': 'Nomisc2',
                            'Misc3': 'Nomisc3',
                            'Measure': 'Expenses',
                            'data': 0
                        }
                        insert_rows.append(insert_row)

                    df_insert = pd.DataFrame(insert_rows)

                    # 保存到 Cube
                    cube.save(
                        data=df_insert
                    )
                    print(f"已插入 0 值记录到 Cube 中，针对 Material={material} 和科目={missing_accounts}")
                else:
                    print(f"Material={material} 的所有科目已有非空数据，无需补 0")

        except Exception as e:
            print(f"检查并插入 0 值时错误: {str(e)}")
            traceback.print_exc()

    def process(self):
        """主处理逻辑"""
        # 查询数据
        df_material = self.fetch_material_data()
        if df_material.empty:
            print("未检索到数据。")
            return pd.DataFrame()


        # 删除功能:查询二维表填报物料,然后删除cube中,不存在得物料信息
        self.delete_cube_material(df_material)
        # 映射科目并补充
        df_processed = self.map_accounts(df_material)

        # 检查并补 0
        self.check_and_insert_zero_if_empty(df_processed)

        # print(df_processed)
        return df_processed

def main(p1, p2):
    material = MaterialFill(p2)
    material.process()




# debug
if __name__ == '__main__':
    from BIZ._debug import para1, para2
    # p2 = {'func': "实际数", 'year': "空", 'month_begin': 1, 'month_end': 12, 'entity': "空"}
    para2 = {'elementName': 'Material_Centralized',
          'folderId': 'DIR40444ad68bfb',
          'sheetName': '原材料填报信息',
          'sheetId': 'SHT5874187a888b4d2aa45bf7929aa19895',
          'Year_wb1': '2026',
          'Entity_wb1': 'Q92024000331',
          'Version_wb1': 'Y1',
          'Scenario_wb1': 'Budget',
          'Tax_wb1': 'Tax',
          'Project_Type_wb1': 'NoProject_Type',
          'Department_wb1': 'Operation',
          'Format_wb1': 'Format_all'}
    main(para1, para2)

