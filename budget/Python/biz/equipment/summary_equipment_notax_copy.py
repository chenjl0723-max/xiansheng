# -*- coding: utf-8 -*-
# @Time : 2023/10/30 17:05
# @Author : LiYuXin
# @FileName: summary_equipment_notax_copy.py
# @Software: PyCharm

import time
import numpy as np
import pandas as pd
import asyncio
from deepfos.element.finmodel import FinancialCube, AsyncFinancialCube
from deepfos.element.variable import Variable


def clear_query(expression, year, last_year):
    # 获取含税数据
    exp_tax = expression + "->Department{Equipment;Technical}->Tax{Tax}->Period{1;2;3;4;5;6;7;8;9;10;11;12}" \
                           "->Scenario{Forecast;Budget}->Year{%s;%s}" % (year, last_year)
    # 查找税率
    exp_taxrate = expression + "->Department{Equipment;Technical}->Period{Noperiod}->Tax{Taxrate}" \
                               "->Scenario{Actual;Budget}->Year{%s;%s}" % (year, last_year)
    # 清cube
    exp_clear_fc = expression + "->Department{Equipment;Technical}->Period{10;11;12}->Tax{Notax}->" \
                                "Scenario{Forecast}->Year{%s}" % last_year
    exp_clear_bg = expression + "->Department{Equipment;Technical}->Period{1;2;3;4;5;6;7;8;9;10;11;12}->Tax{Notax}->" \
                                "Scenario{Budget}->Year{%s}" % year
    # 获取不含税数据
    exp_notax = expression + "->Department{Equipment;Technical}->Period{1;2;3;4;5;6;7;8;9;10;11;12}->Tax{Notax}" \
                             "->Scenario{Actual}->Year{%s}" % last_year
    # 清cube
    exp_clear_ac = expression + "->Department{Equipment;Technical}->Period{1;2;3;4;5;6;7;8;9;10;11;12}->Tax{Tax}" \
                                "->Scenario{Actual}->Year{%s}" % last_year
    # 清cube
    exp_clear_np = expression + "->Department{Equipment;Technical}->Period{Noperiod}->Tax{Tax;Notax}" \
                                "->Scenario{Actual}->Year{%s}" % last_year

    async def cube_deal():
        cube = AsyncFinancialCube("WS_cube")
        results = await asyncio.gather(
            cube.query(exp_tax, compact=False),
            cube.query(exp_taxrate, compact=False),
            cube.query(exp_notax, compact=False),
            cube.delete(exp_clear_fc),
            cube.delete(exp_clear_bg),
            cube.delete(exp_clear_ac),
            cube.delete(exp_clear_np),
        )
        return results
    data_result = asyncio.run(cube_deal())
    return data_result


def forecast_notax(cube, last_year, year, tax_data, taxrate_data):
    # 获取含税数据
    # exp_tax = expression + "->Department{Equipment}->Tax{Tax}" \
    #                        "->Period{1;2;3;4;5;6;7;8;9;10;11;12}->Scenario{Forecast;Budget}->Year{%s;%s}" \
    #           % (year, last_year)
    # tax_data = cube.query(expression=exp_tax, compact=False)
    tax_fc = tax_data.loc[(tax_data["Scenario"] == "Forecast")
                          & (tax_data["Year"] == last_year)
                          & (tax_data["Period"].isin(["10", "11", "12"]))]
    tax_bg = tax_data.loc[(tax_data["Scenario"] == "Budget")
                          & (tax_data["Year"] == year)]
    tax_data = pd.concat([tax_bg, tax_fc], axis=0)
    # 查找税率
    # exp_taxrate = expression + "->Department{Operation}->Period{Noperiod}->Tax{Taxrate}" \
    #                            "->Scenario{Actual;Budget}->Year{%s;%s}" % (year, last_year)
    # taxrate_data = cube.query(expression=exp_taxrate, compact=False)
    taxrate_data = taxrate_data[['Entity', 'Account', "data", "Scenario", "Year"]]
    taxrate_bg = taxrate_data.loc[(taxrate_data["Scenario"] == "Budget")
                                  & (taxrate_data["Year"] == year)]
    taxrate_ac = taxrate_data.loc[(taxrate_data["Scenario"] == "Actual")
                                  & (taxrate_data["Year"] == last_year)]
    taxrate_fc = taxrate_ac.copy(deep=True)
    taxrate_fc["Scenario"] = "Forecast"
    taxrate_data = pd.concat([taxrate_fc, taxrate_bg], axis=0)
    # 计算不含税
    merge_tax_taxrate = pd.merge(tax_data, taxrate_data, how="left", on=['Entity', 'Account', 'Scenario', "Year"],
                                 suffixes=("", "_rate"))
    # 将未找到税率科目的税率设置为0
    merge_tax_taxrate["data_rate"] = merge_tax_taxrate["data_rate"].fillna(0)
    merge_tax_taxrate['data'] = merge_tax_taxrate['data'] / (1 + merge_tax_taxrate['data_rate'])
    del merge_tax_taxrate['data_rate']
    merge_tax_taxrate['Tax'] = "Notax"

    # 清cube
    # exp_clear = expression + "->Department{Equipment}->Period{10;11;12}->Tax{Notax}->" \
    #                          "Scenario{Forecast}->Year{%s}" % last_year
    # cube.delete(expression=exp_clear)
    # exp_clear = expression + "->Department{Equipment}->Period{1;2;3;4;5;6;7;8;9;10;11;12}->Tax{Notax}->" \
    #                          "Scenario{Budget}->Year{%s}" % year
    # cube.delete(expression=exp_clear)
    # 存cube
    cube.save(merge_tax_taxrate)

    notax_fc = merge_tax_taxrate.loc[merge_tax_taxrate["Scenario"] == "Forecast"]
    return taxrate_ac, notax_fc, tax_fc


def actual_tax(cube, taxrate_data, notax_data):
    # 获取不含税数据
    # exp_notax = expression + "->Department{Equipment}->Period{1;2;3;4;5;6;7;8;9;10;11;12}->Tax{Notax}"/
    #                          "->Scenario{Actual}"
    # notax_data = cube.query(expression=exp_notax, compact=False)
    # 计算含税
    merge_notax_taxrate = pd.merge(notax_data, taxrate_data, how="left", on=['Entity', 'Account'],
                                   suffixes=("", "_rate"))
    # 将未找到税率科目的税率设置为0
    merge_notax_taxrate["data_rate"] = merge_notax_taxrate["data_rate"].fillna(0)
    merge_notax_taxrate['data'] = merge_notax_taxrate['data'] * (1 + merge_notax_taxrate['data_rate'])
    del merge_notax_taxrate['data_rate']
    merge_notax_taxrate['Tax'] = "Tax"
    # 清cube
    # exp_clear = expression + "->Department{Equipment}->Period{1;2;3;4;5;6;7;8;9;10;11;12}->Tax{Tax}->Scenario{Actual}"
    # cube.delete(expression=exp_clear)
    # 存cube
    cube.save(merge_notax_taxrate)
    return merge_notax_taxrate, notax_data


def actual_noperiod(cube, val, forecast_data, actual_data):
    # 清cube
    # exp_clear = expression + "->Department{Equipment}->Period{Noperiod}->Tax{Tax;Notax}->Scenario{Actual}"
    # cube.delete(expression=exp_clear)
    # 根据变量组合全年数据
    if val == "Actual":
        tax_data_ac = actual_data
    else:
        actual_data = actual_data.loc[actual_data["Period"].isin(["1", "2", "3", "4", "5", "6", "7", "8", "9"])]
        tax_data_ac = pd.concat([actual_data, forecast_data], axis=0)
    tax_data_ac["Period"] = "Noperiod"
    tax_data_ac["Scenario"] = "Actual"
    if not tax_data_ac.empty:
        group = ["Year", "Version", "Entity", "Account", "Period", "Scenario",
                 "Material", "Tax", "Allocation", "Department", "Measure", "Misc1", "Misc2"]
        tax_data_noperiod = tax_data_ac.groupby(group, as_index=False)["data"].sum()
        # 存cube
        cube.save(tax_data_noperiod)


def main(p1, p2):
    begin = time.time()
    year = p2['Year_wb1']
    last_year = str(int(year) - 1)
    if 'Entity_st1' in p2:
        entity = p2['Entity_st1']
    elif 'Entity_st1' not in p2:
        entity = p2['Entity_wb1']
    version = p2["Version_wb1"]
    allocation = p2["Allocation_wb1"]
    misc1 = p2["Misc1_wb1"]
    misc2 = p2["Misc2_wb1"]

    variable = Variable(element_name="Variable")
    val = variable.get_value("Forcast")
    cube = FinancialCube("WS_cube")
    expression = "Account{Base(PL010204,0);Base(PL03,0)}->Material{Nomaterial}->Measure{Expenses}->" \
                 "Entity{%s}->Version{%s}->Allocation{%s}->Misc1{%s}->Misc2{%s}" \
                 % (entity, version, allocation, misc1, misc2)
    # 汇总清数取数
    data = clear_query(expression, year, last_year)

    # part1 税率计算(Forecast)
    taxrate_data, notax_data, tax_data = forecast_notax(cube, last_year, year, tax_data=data[0], taxrate_data=data[1])
    forecast_data = pd.concat([tax_data, notax_data], axis=0)

    expression = expression + "->Year{%s}" % last_year

    # part2 税率计算(Actual)
    tax_data, notax_data = actual_tax(cube, taxrate_data, notax_data=data[2])
    actual_data = pd.concat([tax_data, notax_data], axis=0)

    # part3 实际全年计算(var)
    actual_noperiod(cube, val, forecast_data, actual_data)
    print("设备税率：", time.time() - begin)


if __name__ == "__main__":
    from common._debug import para1

    p2 = {'elementName': 'Equipment_Project',
          'folderId': 'DIR33a5de271905',
          'sheetName': '设备预算汇总表（技改+非技改)',
          'sheetId': 'SHT5bd1d30656cf4897aba5a699fb894a38',
          'Year_wb1': '2026',
          'Entity_wb1': 'PS14003_01',
          'Department_wb1': 'Totaldepartment',
          'Tax_wb1': 'Tax',
          'Version_wb1': 'Y1',
          'Allocation_wb1': 'Original',
          'Misc1_wb1': 'Nomisc1',
          'Misc2_wb1': 'Nomisc2',
          'Material_wb1': 'Nomaterial',
          'Scenario_wb1': 'Forecast',
          'Tax_st1': 'Tax',
          'Entity_st1': 'Y1420210001'}


    main(para1, p2)
