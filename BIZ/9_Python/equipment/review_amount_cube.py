# -*- coding: utf-8 -*-
'''
@file    : Review_amount_cube.py
@Time    : 2025-09-14
@Author  : chen
@Software: PyCharm
@Desc    : 设备审核表，审核金额、意见进cube）
'''

from deepfos.element.datatable import DataTableMySQL
import pandas as pd
from deepfos.element.finmodel import FinancialCube

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)


class EquipmentCalc:
    def __init__(self, p2):
        self.year = p2['Year_wb1']
        self.entity = p2['Entity_wb1']
        self.cube_name = 'S_Cube'

        # 固定维度（去掉 Measure，后面分别写）
        self.pov = {
            'Version': 'Y1',
            'Department': 'Equipment',
            'Scenario': 'Budget',
            'Tax': 'Tax',
            'Project_Type': 'NoProject_Type',
            'Format': 'NoFormat',
            'PM_Chars': 'NoPM_Chars',
            'Misc1': 'Nomisc1',
            'Misc2': 'Nomisc2',
            'Misc3': 'Nomisc3',
            'Material': 'Nomaterial',
            # 'Measure': 'Expenses'   # ← 删除
        }

        # 读取原始数据
        equipment_table = DataTableMySQL('Equipment_profile')
        where = "year = '%s' and account in ('SPL0102040201','SPL0102040202','SPL0102040203') and group_amount_er is not null" % (self.year)
        cols = [
            'year', 'entity', 'account', 'implementation_or',
            'district_amount_er', 'region_amount_er', 'group_amount_er'
        ]
        df_all = equipment_table.select(columns=cols, where=where)

        self.df_raw = df_all.rename(columns={            # 'sum': 'data_sum',
            'district_amount_er': 'data_district',
            'region_amount_er': 'data_region',
            'group_amount_er': 'data_group',
            'entity': 'Entity',
            'year': 'Year',
            'account': 'Account'
        })

    # ------------------------------------------------------------------
    def process(self):
        """主处理逻辑"""
        del_fix = "Account{SPL0102040101;SPL010204010201;SPL010204010202;SPL010204010203;SPL0102040201;SPL0102040202;SPL0102040203}->Entity{Base(1,0)}->Measure{Groupaccount}->Tax{Tax}->Year{%s}->Period{Noperiod}->Scenario{Budget}"%(self.year)
        cube = FinancialCube(self.cube_name)
        cube.delete(del_fix)

        # ==================== 3. 审核金额（Noperiod） ====================
        audit_cfg = [
            # ('data_district', 'Areaaccount'),   # 区域
            # ('data_region',   'Regionaccount'), # 大区
            ('data_group',    'Groupaccount'),  # 集团
        ]

        audit_dfs = []
        for data_col, measure_val in audit_cfg:
            if data_col not in self.df_raw.columns:
                continue
            df_a = self.df_raw[
                self.df_raw[data_col].notna() & (self.df_raw[data_col] != 0)
            ].copy()
            if df_a.empty:
                continue

            df_a = df_a.groupby(["Year", "Entity", "Account"], as_index=False)[data_col].sum()
            df_a.rename(columns={data_col: 'data'}, inplace=True)

            df_a["Period"] = "Noperiod"
            df_a["Measure"] = measure_val

            for k, v in self.pov.items():
                df_a[k] = v

            audit_dfs.append(df_a)
            self._save_to_cube(df_a, f"审核金额 - {measure_val}")

    # ------------------------------------------------------------------
    def _save_to_cube(self, df, desc=""):
        """统一保存到 Cube"""
        if df.empty:
            return
        cube = FinancialCube(element_name=self.cube_name)
        print(f"正在写入 Cube：{desc}，行数: {len(df)}")
        cube.save(df)


# ----------------------------------------------------------------------
def main(p1, p2):
    calc = EquipmentCalc(p2)
    calc.process()


if __name__ == '__main__':
    from BIZ._debug import para1, para2
    para2 = {
        'elementName': 'dailycare_equipment',
        'folderId': 'DIR40444ad68bfb',
        'sheetName': '设施日常维护费',
        'sheetId': 'SHTa72a3803d59748f8a17e05e71ec55154',
        'Year_wb1': '2026',
        'Entity_wb1': 'Y5120221036',
        'Department_wb1': 'Equipment',
        'Version_wb1': 'Y1',
        'Format_wb1': 'NoFormat',
        'Project_Type_wb1': 'NoProject_Type',
        'PM_Chars_wb1': 'NoPM_Chars'
    }

    main(para1, para2)