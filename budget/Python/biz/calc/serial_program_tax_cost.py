# -*- coding: utf-8 -*-
# @Time : 2023/9/25 10:44
# @Author : LiYuXin
# @FileName: serial_program_tax_cost.py
# @Software: PyCharm
from copy import deepcopy
import time


def main(p1, p2):
    begin = time.time()
    # 替换 Entity_wb1 的值为 Entity_st1 的值
    p2['Entity_wb1'] = p2['Entity_st1']

    # 删除 Entity_st1 键
    del p2['Entity_st1']

    # 构造p2参数中的其他维度
    p2['Tax_wb1'] = 'Tax'
    p2['Department_wb1'] = 'Operation'
    # p2['Year'] = '2024'
    print(p2)
    # 调用电费&污泥费脚本
    from budget.Python.biz.electricity_sludge.electricity_and_sludge import main as main_electric
    main_electric(p1, p2)
    print("electricity_and_sludge down")
    print(time.time() - begin)


    # 调用水价与收入脚本
    p2["sheetId"] = "SHTc467b87b7841"
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

    p2['Department_wb1'] = 'Equipment'
    # 计算设备类实际数转换
    from budget.Python.biz.equipment import summary_equipment_notax_copy as equip_copy
    equip_copy.main(p1, p2)
    print("summary_equipment_notax_copy down")
    print(time.time() - begin)

    # 新增计算审核指标
    audit = time.time()
    # p2["year"] = p2["Year"]
    from budget.Python.biz.equipment.indicators_equipment import main as main_audit
    main_audit(p1, p2)
    times = time.time() - audit
    print("审核：", times)


    # 临时提出配置表审核指标计算单独运行
    from budget.Python.biz.calc import copy1_config_calc as audit
    print(p2)
    audit.main(p1, p2)
    print("config_calc down")
    print(time.time() - begin)

    p2['sheetId'] = "设备类吨水成本相关计算"
    # 计算设备类吨水陈本 配置表审核指标计算单独运行
    from budget.Python.biz.equipment import equipment_config_calc as equipment_audit
    print(p2)
    equipment_audit.main(p1, p2)
    print("config_calc down")
    print(time.time() - begin)

if __name__ == "__main__":
    from common._debug import para1, para2
    p2 = {'elementName': 'Tax',
          'folderId': 'DIRb6550dd20485',
          'sheetName': '税率维护表（费用类）',
          'sheetId': 'SHT7b88fb86af864a288f85d01c9a89da87',
          'Year_wb1': '2025',
          'Entity_wb1': 'PS32006_01',
          'Version_wb1': 'Y1',
          'Material_wb1': 'Nomaterial',
          'Allocation_wb1': 'Original',
          'Department_wb1': 'Operation',
          'Misc1_wb1': 'Nomisc1',
          'Misc2_wb1': 'Nomisc2',
          'Entity_st1': 'XN32006_01'}


    main(para1, p2)
