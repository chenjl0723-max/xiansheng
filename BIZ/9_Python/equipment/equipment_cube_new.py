# -*- coding: utf-8 -*-
'''
@file    : equipment_cube.py
@Time    : 2025-09-14
@Author  : chen
@Software: PyCharm
@Desc    : 设备预算进cube（含区域/大区/集团审核金额，Noperiod）
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
        if self.entity == 'Base(1,0)':
            where = "year = '%s' and account is not null" % (self.year)

        elif self.entity != 'Base(1,0)':
            where = "year = '%s' and entity = '%s' and account is not null" % (self.year, self.entity)

        cols = [
            'year', 'entity', 'account', 'implementation_or', 'sum',
            'district_amount_er', 'region_amount_er', 'group_amount_er'
        ]
        df_all = equipment_table.select(columns=cols, where=where)

        self.df_raw = df_all.rename(columns={
            'sum': 'data_sum',
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
        del_fix = "Account{SPL0102040101;SPL010204010201;SPL010204010202;SPL010204010203;SPL0102040201;SPL0102040202;SPL0102040203}->Entity{%s}->Tax{Tax}->Year{%s}->Period{1;2;3;4;5;6;7;8;9;10;11;12;Noperiod}->Scenario{Budget}"%(self.entity,self.year)
        cube = FinancialCube(self.cube_name)
        cube.delete(del_fix)
        # ==================== 1. 日常维修费 SPL0102040102（分摊） ====================
        df_repair = self.df_raw[self.df_raw['Account'] == 'SPL0102040102'].copy()
        if not df_repair.empty:
            df_repair_sum = df_repair.groupby(
                ["Year", "Entity", "Account", "implementation_or"], as_index=False
            )['data_sum'].sum()

            df_repair_sum.loc[df_repair_sum["implementation_or"] == "I05", "Account"] = "SPL010204010201"
            df_repair_sum.loc[df_repair_sum["implementation_or"] == "I06", "Account"] = "SPL010204010202"
            df_repair_sum = df_repair_sum.drop(columns=["implementation_or"])

            # 12 个月均摊
            df_monthly = df_repair_sum.loc[df_repair_sum.index.repeat(12)].copy()
            df_monthly["Period"] = df_monthly.groupby(level=0).cumcount() + 1
            df_monthly["data"] = df_monthly["data_sum"] / 12
            df_monthly = df_monthly.drop(columns=["data_sum"])

            # 补齐维度
            for k, v in self.pov.items():
                df_monthly[k] = v
            df_monthly['Measure'] = 'Expenses'

            self._save_to_cube(df_monthly, "日常维修费（分摊）")
        else:
            df_monthly = pd.DataFrame()

        # ==================== 2. 其它设备费（不含 SPL0102040102） ====================
        df_other = self.df_raw[~self.df_raw['Account'].isin(['SPL0102040102'])].copy()
        if not df_other.empty:
            df_other_sum = df_other.groupby(
                ["Year", "Entity", "Account"], as_index=False
            )['data_sum'].sum()

            df_other_monthly = df_other_sum.loc[df_other_sum.index.repeat(12)].copy()
            df_other_monthly["Period"] = df_other_monthly.groupby(level=0).cumcount() + 1
            df_other_monthly["data"] = df_other_monthly["data_sum"] / 12
            df_other_monthly = df_other_monthly.drop(columns=["data_sum"])

            for k, v in self.pov.items():
                df_other_monthly[k] = v
            df_other_monthly['Measure'] = 'Expenses'

            self._save_to_cube(df_other_monthly, "其它设备费（分摊）")
        else:
            df_other_monthly = pd.DataFrame()

        # ==================== 3. 审核金额（Noperiod） ====================
        audit_cfg = [
            ('data_district', 'Areaaccount'),   # 区域
            ('data_region',   'Regionaccount'), # 大区
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

        # ==================== 4. 汇总（仅用于调试） ====================
        all_dfs = [df for df in [df_monthly, df_other_monthly] + audit_dfs if not df.empty]
        if all_dfs:
            final_df = pd.concat(all_dfs, ignore_index=True)
            print(f"\n总计写入 Cube 行数: {len(final_df)}")
            print("维度预览：")
            print(final_df[[
                'Year', 'Entity', 'Account', 'Period', 'Measure', 'data',
                'Version', 'Department', 'Scenario'
            ]].head(12))
        else:
            print("无数据写入 Cube")

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
        'Entity_wb1': 'Base(1,0)',
        'Department_wb1': 'Equipment',
        'Version_wb1': 'Y1',
        'Format_wb1': 'NoFormat',
        'Project_Type_wb1': 'NoProject_Type',
        'PM_Chars_wb1': 'NoPM_Chars'
    }

    main(para1, para2)