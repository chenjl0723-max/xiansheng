#!/usr/bin/env python
# -*- coding:utf-8 -*-
"""
    描述： 原材料填报（集采药剂）-python新增

    开发： 陈 小

    日期： 2023/8/25 14:40

"""

import os
import sys

top_path = os.path.abspath(os.path.join(__file__, "../.."))
sys.path.append(top_path)

import warnings

warnings.filterwarnings("ignore")

import pandas as pd
from common.commons import *
from deepfos.element.finmodel import FinancialCube

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)

class CPM(object):
    def __init__(
            self,
    ):
        self.cube = "WS_cube"
        self.sql_tbl = "Material_Commidity_Submit"

    def get_sql_data(self, p2):
        where = (
                "(t.Entity=='%s') & (t.Year=='%s') & (t.Department=='%s') & (t.Scenario=='%s') & (t.Version=='%s')"
                % (
                    p2["Entity"],
                    p2["Year"],
                    p2["Department"],
                    p2["Scenario"],
                    p2["Version"],
                )
        )
        if p2['Entity'] == 'IDescendant(1,0)':
            where = (
                    "(t.Year=='%s') & (t.Department=='%s') & (t.Scenario=='%s') & (t.Version=='%s')"
                    % (
                        p2["Year"],
                        p2["Department"],
                        p2["Scenario"],
                        p2["Version"],
                    )
            )
        columns = [
            "Entity",
            "Ingredient",
            "Active",
            "COD",
            "TN",
            "Coefficient",
            "Equivalent",
            "UnitPrice",
            "Year",
            "Department",
            "Scenario",
            "Version",
            "Misc1",
        ]
        mcs_df = rdb_.select(tbl=self.sql_tbl, where=where, columns=columns)
        return mcs_df

    def get_mbd_data(self, p2):
        where = (
                "(t.Year=='%s') & (t.Department=='%s') & (t.Scenario=='%s') & (t.Version=='%s')"
                % (p2["Year"], p2["Department"], p2["Scenario"], p2["Version"])
        )
        columns = [
            "Ingredient",
            "COD",
            "TN",
            "Coefficient",
            "Equivalent",
        ]
        mbd_df = rdb_.select(tbl="Material_BasicData", where=where, columns=columns)
        return mbd_df

    def get_mif_data(self, p2):
        import datetime

        year = str(datetime.datetime.today().year)
        where = (
                "(t.Entity=='%s') & (t.Year=='%s') & (t.Scenario=='%s') & (t.Version=='%s')"
                % (p2["Entity"], p2['Year'], p2["Scenario"], p2["Version"])
        )
        if p2['Entity'] == 'IDescendant(1,0)':
            where = (
                    "(t.Year=='%s') & (t.Scenario=='%s') & (t.Version=='%s')"
                    % (p2['Year'], p2["Scenario"], p2["Version"])
            )
        columns = ['Entity', "Material", "Price", "Misc1"]
        mif_df = rdb_.select(tbl="bewg_price_data", where=where, columns=columns)

        # 新增df是否为空的判断
        if mif_df.empty:
            # 如果为空取前一年的
            year = str(datetime.datetime.today().year - 1)
            where = (
                    "(t.Entity=='%s') & (t.Year=='%s') & (t.Scenario=='%s') & (t.Version=='%s')"
                    % (p2["Entity"], year, p2["Scenario"], p2["Version"])
            )
            if p2["Entity"] == "IDescendant(1,0)":
                where = "(t.Year=='%s') & (t.Scenario=='%s') & (t.Version=='%s')" % (
                    p2["Entity"],
                    p2["Scenario"],
                    p2["Version"],
                )
            columns = ['Entity', "Material", "Price", "Misc1"]
            mif_df_last = rdb_.select(tbl="bewg_price_data", where=where, columns=columns)
            if not mif_df_last.empty:
                mif_df = mif_df_last

        mif_df = mif_df.rename(columns={"Price": "UnitPrice", "Material": "Ingredient"})
        return mif_df

    def data_handle(self, mcs_df, mbd_df, mif_df, dim_material, year):
        # 若COD、TN、Coefficient，Equivalent均为空，则根据"Ingredient"去dzsicw002_Material_Basic_f94ff表中取相应字段值
        ctce_none = mcs_df[
            (mcs_df["COD"].isnull())
            & (mcs_df["TN"].isnull())
            & (mcs_df["Coefficient"].isnull())
            & (mcs_df["Equivalent"].isnull())
            ]
        ctce_not_none = mcs_df[
            ~(
                    (mcs_df["COD"].isnull())
                    & (mcs_df["TN"].isnull())
                    & (mcs_df["Coefficient"].isnull())
                    & (mcs_df["Equivalent"].isnull())
            )
        ]
        ctce_none = ctce_none.drop(
            columns=[
                "COD",
                "TN",
                "Coefficient",
                "Equivalent",
            ]
        )
        ctce_none = pd.merge(ctce_none, mbd_df, how="left")
        mcs_df = pd.concat([ctce_none, ctce_not_none])

        # 当"UnitPrice"为空时，跟据"Entity"+"Year"+"Ingredient"+"Misc1"字段，Ingredient关联Material，在dzsicw002_bewg_price_dat_b0e1c获取相应字段值
        up_none = mcs_df[mcs_df["UnitPrice"].isnull()]
        up_not_none = mcs_df[~mcs_df["UnitPrice"].isnull()]
        del up_none["UnitPrice"]
        up_none = pd.merge(up_none, mif_df, how="left")
        mcs_df = pd.concat([up_none, up_not_none])

        mcs_df = mcs_df.rename(
            columns={
                "Ingredient": "Material",
                "Active": "YW0302",
                "COD": "YW0307",
                "TN": "YW0308",
                "Coefficient": "YW0317",
                "Equivalent": "YW0311",
                "UnitPrice": "YW0303",
                "Misc1": "Misc1",
            }
        )
        # 添加默认列
        mcs_df["Measure"] = "Expenses"
        mcs_df["Allocation"] = "Original"
        mcs_df["Tax"] = "Tax"
        mcs_df["Misc2"] = "Nomisc2"
        dt_month = pd.DataFrame(
            data={"Period": [str(i) for i in range(1, 13)], "Misc2": "Nomisc2"}
        )
        dt_month = dt_month.append(
            {"Period": "Noperiod", "Misc2": "Nomisc2"}, ignore_index=True
        )
        # 关联月份表，生成1-12月份的数据
        mcs_df = pd.merge(left=mcs_df, right=dt_month, how="left")
        # 11-12 Forecast
        mcs_forecast_df = mcs_df[mcs_df["Period"].isin(["10", "11", "12"])]
        mcs_forecast_df["Year"] = year
        mcs_forecast_df["Scenario"] = "Forecast"
        # Noperiod Actual
        mcs_actual_df = mcs_df[mcs_df['Period'] == 'Noperiod']
        mcs_actual_df['Year'] = year
        mcs_actual_df['Scenario'] = "Actual"
        mcs_df = pd.concat([mcs_df, mcs_forecast_df, mcs_actual_df])
        mcs_au_df = mcs_df[['Entity', 'Material', 'Year', 'Department', 'Scenario',
                            'Version', 'Misc1', 'Measure',
                            'Allocation', 'Tax', 'Misc2', 'Period', 'YW0302', 'YW0303']]
        mcs_ctce_df = mcs_df[['Entity', 'Material', 'Year', 'Department', 'Scenario',
                              'Version', 'Misc1', 'Measure',
                              'Allocation', 'Tax', 'Misc2', 'Period', 'YW0307', 'YW0308', 'YW0317', 'YW0311']]
        mcs_ctce_df['Misc1'] = 'Nomisc1'
        mcs_ctce_df = mcs_ctce_df.drop_duplicates()
        return mcs_au_df, mcs_ctce_df

    def data_to_cube(self, mcs_au_df, mcs_ctce_df, p2, year):
        cube = FinancialCube("WS_cube")

        # 查询 YW0304 YW0316
        budget_fix = (
                "Entity{%s}->Material{AndFilter(Base(MQ,0),Attr(ud1,'Centralized'))}->"
                "Department{%s}->Version{%s}->Allocation{Original}->Misc1{%s}->Misc2{Nomisc2}->Account{YW0304;YW0316}->Scenario{%s}->"
                "Measure{Expenses}->Period{1;2;3;4;5;6;7;8;9;10;11;12;Noperiod}->Tax{Tax}->Year{%s}"
                % (
                    p2["Entity"],
                    p2["Department"],
                    p2["Version"],
                    p2["Misc1"],
                    p2["Scenario"],
                    p2["Year"],
                )
        )
        budget_df = cube.query(expression=budget_fix, compact=False, pivot_dim='Account')

        forcast_fix = (
                "Entity{%s}->Material{AndFilter(Base(MQ,0),Attr(ud1,'Centralized'))}->"
                "Department{%s}->Version{%s}->Allocation{Original}->Misc1{%s}->Misc2{Nomisc2}->Account{YW0304;YW0316}->Scenario{Forecast}->"
                "Measure{Expenses}->Period{10;11;12}->Tax{Tax}->Year{%s}"
                % (p2["Entity"], p2["Department"], p2["Version"], p2["Misc1"], year)
        )
        forcast_df = cube.query(expression=forcast_fix, compact=False, pivot_dim='Account')

        actual_fix = (
                "Entity{%s}->Material{AndFilter(Base(MQ,0),Attr(ud1,'Centralized'))}->"
                "Department{%s}->Version{%s}->Allocation{Original}->Misc1{%s}->Misc2{Nomisc2}->Account{YW0304;YW0316}->Scenario{Actual}->"
                "Measure{Expenses}->Period{Noperiod}->Tax{Tax}->Year{%s}"
                % (p2["Entity"], p2["Department"], p2["Version"], p2["Misc1"], year)
        )
        actual_df = cube.query(expression=actual_fix, compact=False, pivot_dim='Account')

        df_YW0304_YW0316 = pd.concat([budget_df, forcast_df, actual_df])

        # 拼接删除fix
        del_fix = (
                "Entity{%s}->Material{AndFilter(Base(MQ,0),Attr(ud1,'Centralized'))}->"
                "Department{%s}->Version{%s}->Allocation{Original}->Misc1{%s}->Misc2{Nomisc2}->Account{YW0302;YW0303;YW0304;YW0316}->Scenario{%s}->"
                "Measure{Expenses}->Period{1;2;3;4;5;6;7;8;9;10;11;12;Noperiod}->Tax{Tax}->Year{%s}"
                % (
                    p2["Entity"],
                    p2["Department"],
                    p2["Version"],
                    p2["Misc1"],
                    p2["Scenario"],
                    p2["Year"],
                )
        )
        # 删除数据
        cube.delete(del_fix)
        del_fix = (
                "Entity{%s}->Material{AndFilter(Base(MQ,0),Attr(ud1,'Centralized'))}->"
                "Department{%s}->Version{%s}->Allocation{Original}->Misc1{%s}->Misc2{Nomisc2}->Account{YW0302;YW0303;YW0304;YW0316}->Scenario{Forecast}->"
                "Measure{Expenses}->Period{10;11;12}->Tax{Tax}->Year{%s}"
                % (p2["Entity"], p2["Department"], p2["Version"], p2["Misc1"], year)
        )
        # 删除数据
        cube.delete(del_fix)
        del_fix = (
                "Entity{%s}->Material{AndFilter(Base(MQ,0),Attr(ud1,'Centralized'))}->"
                "Department{%s}->Version{%s}->Allocation{Original}->Misc1{%s}->Misc2{Nomisc2}->Account{YW0302;YW0303;YW0304;YW0316}->Scenario{Actual}->"
                "Measure{Expenses}->Period{Noperiod}->Tax{Tax}->Year{%s}"
                % (p2["Entity"], p2["Department"], p2["Version"], p2["Misc1"], year)
        )
        # 删除数据
        cube.delete(del_fix)

        # 拼接删除fix
        del_fix = (
                "Entity{%s}->Material{AndFilter(Base(MQ,0),Attr(ud1,'Centralized'))}->"
                "Department{%s}->Version{%s}->Allocation{Original}->Misc1{%s}->Misc2{Nomisc2}->Account{YW0307;YW0308;YW0317;YW0311}->Scenario{%s}->"
                "Measure{Expenses}->Period{1;2;3;4;5;6;7;8;9;10;11;12;Noperiod}->Tax{Tax}->Year{%s}"
                % (
                    p2["Entity"],
                    p2["Department"],
                    p2["Version"],
                    "Nomisc1",
                    p2["Scenario"],
                    p2["Year"],
                )
        )
        # 删除数据
        cube.delete(del_fix)
        del_fix = (
                "Entity{%s}->Material{AndFilter(Base(MQ,0),Attr(ud1,'Centralized'))}->"
                "Department{%s}->Version{%s}->Allocation{Original}->Misc1{%s}->Misc2{Nomisc2}->Account{YW0307;YW0308;YW0317;YW0311}->Scenario{Forecast}->"
                "Measure{Expenses}->Period{10;11;12}->Tax{Tax}->Year{%s}"
                % (p2["Entity"], p2["Department"], p2["Version"], "Nomisc1", year)
        )
        # 删除数据
        cube.delete(del_fix)
        del_fix = (
                "Entity{%s}->Material{AndFilter(Base(MQ,0),Attr(ud1,'Centralized'))}->"
                "Department{%s}->Version{%s}->Allocation{Original}->Misc1{%s}->Misc2{Nomisc2}->Account{YW0307;YW0308;YW0317;YW0311}->Scenario{Actual}->"
                "Measure{Expenses}->Period{Noperiod}->Tax{Tax}->Year{%s}"
                % (p2["Entity"], p2["Department"], p2["Version"], "Nomisc1", year)
        )
        # 删除数据
        cube.delete(del_fix)
        print('mcs_au_df',mcs_au_df)
        cube.save_unpivot(data=mcs_au_df, unpivot_dim="Account")
        print('mcs_ctce_df', mcs_ctce_df)
        cube.save_unpivot(data=mcs_ctce_df, unpivot_dim="Account")

        del mcs_au_df['YW0302']
        df_baf = pd.merge(mcs_au_df, df_YW0304_YW0316, how='left').fillna(0)
        diff_list = list({"YW0304", "YW0316"}.difference(df_baf.columns))
        if diff_list:
            df_baf[diff_list] = [0] * len(diff_list)
        df_baf = df_baf[~df_baf['YW0303'].isnull()]
        df_baf = df_baf[df_baf['YW0303'] != 0]

        del df_baf['YW0303']
        if not df_baf.empty:
            print('df_baf', df_baf)
            cube.save_unpivot(data=df_baf, unpivot_dim='Account')


def main(p1, p2):
    print(p2)
    rename_map = {
        "Entity_wb1": "Entity",
        "Year_wb1": "Year",
        "Measure_wb1": "Measure",
        "Scenario_wb1": "Scenario",
        "Allocation_wb1": "Allocation",
        "Version_wb1": "Version",
        "Department_wb1": "Department",
        "Tax_wb1": "Tax",
        "Misc1_wb1": "Misc1",
        "Misc2_wb1": "Misc2"
    }
    p2 = {rename_map.get(key, key): value for key, value in p2.items()}

    p2["Misc1"] = "Remove(IDescendant(#root,0),Nomisc1)"
    cpm = CPM()
    print(p2)
    # 查询 sql 表
    mcs_df = cpm.get_sql_data(p2)
    mbd_df = cpm.get_mbd_data(p2)
    mif_df = cpm.get_mif_data(p2)
    # 查询 维度信息
    dim_material = dim_.query_dim(dim_name="Material", expression="Base(MQ02,0)")
    year = str(int(p2["Year"]) - 1)

    print(mcs_df)
    print(mbd_df)
    print(mif_df)
    # 数据处理
    mcs_au_df, mcs_ctce_df = cpm.data_handle(mcs_df, mbd_df, mif_df, dim_material, year)
    cpm.data_to_cube(mcs_au_df, mcs_ctce_df, p2, year)
    del p2['Misc1']


if __name__ == "__main__":
    # 原材料采集脚本-集采
    try:
        from common.__debug import para1
    except:
        pass
    para2 = {'elementName': '_Material_Centralized',
             'folderId': 'DIRacd99f1aefd0',
             'sheetName': '原材料填报（集采药剂）',
             'sheetId': 'SHTc18b2165b1284c9483102eeac1f24557',
             'Year_wb1': '2026',
             'Entity_wb1': 'XN520299_01',
             'Tax_wb1': 'Tax',
             'Department_wb1': 'Operation',
             'Version_wb1': 'Y1',
             'Scenario_wb1': 'Budget',
             'Entity_st1': 'XN520299_01'}


    main(para1, para2)
