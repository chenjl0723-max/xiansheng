# -*- coding: utf-8 -*-
# @Time : 2023/9/18 10:44
# @Author : LiYuXin
# @FileName: serial_program_full_flow.py
# @Software: PyCharm

from copy import deepcopy

import numpy as np
import pandas as pd
import time

from deepfos.element import FinancialCube


def other_04_actual(p2):
    # 同水价与收入脚本04部分计算
    # 04、计算超保底水量(Actual) return: YW0109
    cube = FinancialCube("WS_cube")
    fix = "Year{%s}->Account{%s}->Entity{%s}->Version{%s}->Scenario{%s}->" \
          "Department{%s}->Allocation{%s}->Measure{%s}->Period{%s}->" \
          "Material{%s}->Tax{%s}->Misc1{%s}->Misc2{%s}"
    # 清数
    clear = fix % (str(int(p2["Year_wb1"]) - 1), "YW0109", p2["Entity_wb1"], p2["Version_wb1"], "Actual",
                   p2["Department_wb1"], p2["Allocation_wb1"], "Expenses", "Remove(Base(TotalPeriod,0),Adjust)",
                   p2["Material_wb1"], p2["Tax_wb1"], p2["Misc1_wb1"], p2["Misc2_wb1"])
    cube.delete(expression=clear)
    # 取数
    exp = fix % (str(int(p2["Year_wb1"]) - 1), "YW0106;YW0102", p2["Entity_wb1"], p2["Version_wb1"], "Actual",
                 p2["Department_wb1"], p2["Allocation_wb1"], "Expenses", "Remove(Base(TotalPeriod,0),Adjust)",
                 p2["Material_wb1"], p2["Tax_wb1"], p2["Misc1_wb1"], p2["Misc2_wb1"])
    df = cube.query(expression=exp, compact=False, pivot_dim="Account")
    # 计算
    if not df.empty:
        for i in ["YW0106", "YW0102"]:
            if i not in df.columns:
                df[i] = np.NaN
        # 当A300102为空,A27不为空，YW0106=0
        df.loc[:, "YW0106"] = df.apply(
            lambda x: 0
            if pd.notnull(x["YW0102"]) & pd.isnull(x["YW0106"])
            else x["YW0106"],
            axis=1,
        )
        # IF(YW0102 > YW0106, YW0102 - YW0106, 0) 实际处理水量 > 保底水量，实际 - 保底，否则为0
        df.loc[:, "YW0109"] = df.apply(
            lambda x: x["YW0102"] - x["YW0106"] if x["YW0102"] > x["YW0106"] else 0,
            axis=1,
        )
        df.drop(columns=["YW0102", "YW0106"], inplace=True)
        print(df)
        # 存数
        cube.save_unpivot(df, unpivot_dim="Account")


def main(p1, p2):

    begin = time.time()

    # 构造p2参数中的其他维度
    p2["Material_wb1"] = 'Nomaterial'
    p2["Allocation_wb1"] = 'Original'
    p2["Department_wb1"] = 'Operation'
    p2["Misc1_wb1"] = 'Nomisc1'
    p2["Misc2_wb1"] = 'Nomisc2'
    p2["sheetName_wb1"] = ""
    p2["sheetId"] = ""
    p2["elementName"] = ""
    p2["folderId"] = ""

    # 调用基础生产数据脚本
    from budget.Python.biz.basic_produce_data.new_basic_producetion_data_batch import main as main_base
    p2['Tax_wb1'] = 'Tax'
    main_base(p1, p2)
    print("basic_production_data_batch down")
    print(time.time() - begin)

    # 调用电费&污泥费脚本
    from budget.Python.biz.electricity_sludge.electricity_and_sludge import main as main_electric
    main_electric(p1, p2)
    print("electricity_and_sludge down")
    print(time.time() - begin)
    #
    # # 水价与收入新增实际数计算(仅需用于实际数接入后调用全流程时)
    p2["sheetId"] = "SHTc467b87b7841"
    other_04_actual(p2)
    print("revenue_calc:other_04_actual down")

    # 调用水价与收入脚本
    from budget.Python.biz.water_revenue.budget_revenue_calc_batch import main as main_revenue
    main_revenue(p1, p2)
    print("budget_revenue_calc_batch down")
    print(time.time() - begin)

    # 调用检验化验费、其他成本脚本
    from budget.Python.biz.other_costs.inspection_testing_other_account_copy import main as main_inspection

    p2["sheetName"] = "其他成本汇总表&检验化验费"
    pare2 = deepcopy(p2)
    main_inspection(p1, pare2)
    print("other_account_copy down")
    print(time.time() - begin)

    # 调用原材料计算脚本
    p2['Measure_wb1'] = 'Expenses'
    p2['sheetId'] = "流程"
    from budget.Python.biz.material.raw_material_calc import main as main_raw
    main_raw(p1, p2)
    print("raw_material_calc down")
    print(time.time() - begin)


    # 计算设备类实际数转换
    from budget.Python.biz.equipment import summary_equipment_notax_copy as equip_copy
    equip_copy.main(p1, p2)
    print("summary_equipment_notax_copy down")
    print(time.time() - begin)


    # 临时提出配置表审核指标计算单独运行
    from budget.Python.biz.calc import copy1_config_calc as audit_calc
    print(p2)
    audit_calc.main(p1, p2)
    print("config_calc down")
    print(time.time() - begin)

    p2['sheetId'] = "设备类吨水成本相关计算"
    from budget.Python.biz.equipment.indicators_equipment import main as main_audit
    main_audit(p1, p2)


if __name__ == "__main__":
    from common._debug import para1

    p2 = {'Entity_wb1': 'IDescendant(1,0)', 'Year_wb1': '2025', 'Version_wb1': 'Y1'}
    main(para1, p2)
