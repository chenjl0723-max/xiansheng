# -*- coding: utf-8 -*-
# @Time : 2026/1/6 10:44
# @Author : chenjinglei
# @FileName: full_flow.py
# @Software: PyCharm
from copy import deepcopy
from deepfos.element.pyscript import PythonScript
import time,os,inspect
import numpy as np
import pandas as pd
import time


def main(p1, p2):
    para2 = {
        'Year_wb1': p2['Year'],
        'Entity_wb1': 'Base(1,0)',
        'Department_wb1': 'Operation',
        'Version_wb1': 'Y1',
        'Tax_wb1': 'Tax',
    }
    ele_name=os.path.basename(__file__)
    ele_path=os.path.dirname(os.path.abspath(__file__))

    # 运行安全生产费脚本
    safety=PythonScript(element_name='safety_calc',should_log=True)
    safety_result=safety.run(
        parameter=para2
    )
    print('安全生产费脚本运行成功')

    # 运行其他原材料费脚本
    other=PythonScript(element_name='material_other',should_log=True)
    other_result=other.run(
        parameter=para2
    )
    print('其他原材料费脚本运行成功')

    # 运行设备类费脚本
    equip=PythonScript(element_name='equipment_calc',should_log=True)
    equip_result=equip.run(
        parameter=para2
    )
    print('设备类费脚本运行成功')

    # 运行能源费脚本
    energy=PythonScript(element_name='energy_cost',should_log=True)
    energy_result=energy.run(
        parameter=para2
    )
    print('能源费脚本运行成功')

    # 运行污泥处理费脚本
    sludge_transport=PythonScript(element_name='sludge_transport',should_log=True)
    sludge_transport_result=sludge_transport.run(
        parameter=para2
    )
    print('污泥处理费脚本运行成功')

    # 运行污泥处置费脚本
    sludge_disposal=PythonScript(element_name='sludge_disposal',should_log=True)
    sludge_disposal_result=sludge_disposal.run(
        parameter=para2
    )
    print('污泥处置费脚本运行成功')

    water_revenue = PythonScript(element_name='water_revenue', should_log=True)
    water_revenue_result = water_revenue.run(
        parameter=para2
    )
    print('村镇污水收入脚本运行成功')

    gwyy_revenue = PythonScript(element_name='gwyy_revenue', should_log=True)
    gwyy_revenue_result = gwyy_revenue.run(
        parameter=para2
    )
    print('管网运营收入脚本运行成功')

    wncl_revenue = PythonScript(element_name='wncl_revenue', should_log=True)
    wncl_revenue_result = wncl_revenue.run(
        parameter=para2
    )
    print('污泥处理收入脚本运行成功')

    # 运行收入汇总脚本
    summary_revenue = PythonScript(element_name='summary_revenue', should_log=True)
    summary_revenue_result = summary_revenue.run(
        parameter=para2
    )
    print('收入汇总脚本运行成功')

    # 非薪酬付现成本脚本
    para2['sheetName'] = '非薪酬付现成本'
    para2['sheetId'] = 'SHTa4a7c60013a0'
    para2['Format_wb1'] = 'NoFormat'
    para2['Project_Type_wb1'] = 'NoProject_Type'
    para2['PM_Chars_wb1'] = 'NoPM_Chars'
    payment_revenue = PythonScript(element_name='non_compensation_cash_payment_costs_account_copy', should_log=True)
    payment_result = payment_revenue.run(
        parameter=para2
    )
    print('非薪酬成本复现脚本脚本运行成功')

    # cube1进cube2脚本
    cube_revenue = PythonScript(element_name='cube_transfer', should_log=True)
    cube_result = cube_revenue.run(
        parameter=para2
    )
    print('cube1进cube2脚本运行成功')

    # cube2审核指标计算脚本
    cube2_revenue = PythonScript(element_name='config_calc', should_log=True)
    cube2_result = cube2_revenue.run(
        parameter=para2
    )
    print('cube2审核指标计算脚本运行成功')


if __name__ == "__main__":
    from BIZ.__debug import para1, para2

    p2 = {'Year': '2026'}
    main(para1, p2)