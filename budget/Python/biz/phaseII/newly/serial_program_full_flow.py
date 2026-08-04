# -*- coding: utf-8 -*-
# @Time : 2023/9/18 10:44
# @Author : LiYuXin
# @FileName: serial_program_full_flow.py
# @Software: PyCharm
# 全流程串行脚本

from copy import deepcopy

import numpy as np
import pandas as pd
import time

from deepfos.element import FinancialCube


def other_04_actual(p2):
    # 同水价与收入脚本04部分计算
    # 04、计算超保底水量(Actual) return: A300202
    cube = FinancialCube("BEWG")
    fix = "Year{%s}->Account{%s}->Entity{%s}->Version{%s}->Scenario{%s}->" \
          "Department{%s}->Allocation{%s}->Measure{%s}->Period{%s}->" \
          "Material{%s}->Tax{%s}->misc1{%s}->misc2{%s}"
    # 清数
    clear = fix % (str(int(p2["Year"]) - 1), "A300202", p2["Entity"], p2["Version"], "Actual",
                   p2["Department"], p2["Allocation"], "Expenses", "Remove(Base(TotalPeriod,0),Adjust)",
                   p2["Material"], p2["Tax"], p2["misc1"], p2["misc2"])
    cube.delete(expression=clear)
    # 取数
    exp = fix % (str(int(p2["Year"]) - 1), "A300102;A27", p2["Entity"], p2["Version"], "Actual",
                 p2["Department"], p2["Allocation"], "Expenses", "Remove(Base(TotalPeriod,0),Adjust)",
                 p2["Material"], p2["Tax"], p2["misc1"], p2["misc2"])
    df = cube.query(expression=exp, compact=False, pivot_dim="Account")
    # 计算
    if not df.empty:
        for i in ["A300102", "A27"]:
            if i not in df.columns:
                df[i] = np.NaN
        # 当A300102为空,A27不为空，A300102=0
        df.loc[:, "A300102"] = df.apply(
            lambda x: 0
            if pd.notnull(x["A27"]) & pd.isnull(x["A300102"])
            else x["A300102"],
            axis=1,
        )
        # IF(A27 > A300102, A27 - A300102, 0) 实际处理水量 > 保底水量，实际 - 保底，否则为0
        df.loc[:, "A300202"] = df.apply(
            lambda x: x["A27"] - x["A300102"] if x["A27"] > x["A300102"] else 0,
            axis=1,
        )
        df.drop(columns=["A27", "A300102"], inplace=True)
        # 存数
        cube.save_unpivot(df, unpivot_dim="Account")


def main(p1, p2):
    begin = time.time()

    # 构造p2参数中的其他维度
    p2["Material"] = 'Nomaterial'
    p2["Allocation"] = 'Original'
    p2["Department"] = 'Operation'
    p2["misc1"] = 'Nomisc1'
    p2["misc2"] = 'Nomisc2'
    p2["sheetName"] = ""
    p2["sheetId"] = ""
    p2["elementName"] = ""
    p2["folderId"] = ""

    # 调用基础生产数据脚本
    from budget.Python.biz.phaseII.newly.basic_production_data_batch import main as main_base
    p2['Tax'] = 'Tax'
    main_base(p1, p2)
    print("basic_production_data_batch down")
    print(time.time() - begin)

    # 调用电费&污泥费脚本
    from budget.Python.biz.electricity_sludge.electricity_and_sludge import main as main_electric
    main_electric(p1, p2)
    print("electricity_and_sludge down")
    print(time.time() - begin)

    # 水价与收入新增实际数计算(仅需用于实际数接入后调用全流程时)
    other_04_actual(p2)
    print("revenue_calc:other_04_actual down")

    # 调用水价与收入脚本
    from budget.Python.biz.water_revenue.budget_revenue_calc_batch import main as main_revenue
    main_revenue(p1, p2)
    print("budget_revenue_calc_batch down")
    print(time.time() - begin)

    # 调用检验化验费脚本
    from budget.Python.biz.finance.inspection_testing_other_account_copy import main as main_inspection
    p2["sheetName"] = "检验化验费"
    pare2 = deepcopy(p2)
    main_inspection(p1, pare2)
    print("inspection_testing down")
    print(time.time() - begin)

    # 调用其他成本脚本
    p2["sheetName"] = "其他成本-汇总表"
    pare2 = deepcopy(p2)
    main_inspection(p1, pare2)
    print("other_account_copy down")
    print(time.time() - begin)

    # 调用原材料计算脚本
    p2['Measure'] = 'Expenses'
    p2['sheetId'] = "流程"
    from budget.Python.biz.material.raw_material_calc import main as main_raw
    main_raw(p1, p2)
    print("raw_material_calc down")
    print(time.time() - begin)

    # 临时提出配置表审核指标计算单独运行
    from budget.Python.biz.phaseII.newly import config_calc as audit
    print(p2)
    audit.main(p1, p2)
    print("config_calc down")
    print(time.time() - begin)

    # 调用设备计算脚本
    p2['entity'] = p2["Entity"]
    p2['version'] = p2["Version"]
    p2['department'] = "Equipment"
    p2['scenario'] = "Budget"
    # 构造sheetId等参数
    # 表单1：equipment_overhaul_repurchase
    # 表单2：equipment_overhaul_repurchase_auditing
    # 表单3：installation_overhaul_repurchase
    # 表单4：installation_overhaul_repurchase_auditing
    # 表单5：dailycare_equipment
    # 表单6：dailycare_installation
    # 表单7：dailymaintain_equipment
    # 表单8：new_equipment
    # 表单9：new_equipment_auditing
    # 表单10：Estimated_Liabilities
    list_sheet_id = ['SHT1d97a250fda9', 'SHT0fc73c7b3776', 'SHT59ff31721250', 'SHT01f4a53e304f', 'SHTedf11af03d99',
                     'SHTeab8bb25e91f', 'SHT632b969b3d96', 'SHTee095c3383e6', 'SHTe3d842f50717', 'SHTb03fad4013ae']
    list_equipment_location = ["el01", "el01", "el02", "el02", "el01",
                               "el02", "el01", "el01", "el01", ""]
    list_approve_status = ["", "", "", "", "",
                           "", "", "Status01", "", "Status01"]
    # 调用设备计算脚本biz/equipment/equipment_to_cube.py
    from budget.Python.biz.phaseII.newly.equipment_to_cube_batch import main as main_equipment_batch
    print(p2)
    for i in range(0, 10):
        p2["sheetId"] = list_sheet_id[i]
        p2["equipment_location"] = list_equipment_location[i]
        p2["approve_status"] = list_approve_status[i]
        main_equipment_batch(p1, p2)
    print("equipment_to_cube down")
    print(time.time() - begin)

    # 设备实际年税率计算和数据复制
    from budget.Python.biz.equipment import summary_equipment_notax_copy as equip_copy
    equip_copy.main(p1, p2)
    print("summary_equipment_notax_copy down")
    print(time.time() - begin)


if __name__ == "__main__":
    from common._debug import para1

    p2 = {'Entity': 'IDescendant(1,0)', 'Year': '2025', 'Version': 'Y1'}
    main(para1, p2)
