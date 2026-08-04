# -*- coding: utf-8 -*-
# @Time : 2023/9/7 15:29
# @Author : LiYuXin
# @FileName: serial_program_base_elect.py
# @Software: PyCharm
# 串行调用基础生产数据和电费污泥费和原材料

import time


def main(p1, p2):
    begin = time.time()
    # 避免毛利率重复计算
    p2['sheetName'] = '串行'
    # 调用基础生产数据脚本
    from Python.biz.phaseII.newly.basic_production_data_batch import main as main_base
    main_base(p1, p2)
    print("basic_production_data_batch down")
    print(time.time() - begin)

    # 调用电费污泥费脚本
    from Python.biz.phaseII.newly.electricity_and_sludge import main as main_elect
    main_elect(p1, p2)
    print("electricity_and_sludge down")
    print(time.time() - begin)

    # 调用原材料计算脚本
    p2['Measure'] = 'Expenses'
    from biz.finance.raw_material_calc import main as main_raw
    main_raw(p1, p2)
    print("raw_material_calc down")
    print(time.time() - begin)

    # 调用毛利率计算
    from biz.phaseII.newly.gross_margin_calc import main as main_gross
    main_gross(p1, p2)
    print("gross_margin_calc down")
    print(time.time() - begin)


# debug
if __name__ == '__main__':
    from conf._evn import p1, p2

    p2 = {'Year': '2024', 'Entity': 'Y2021011087', 'Version': 'Y1', 'Material': 'Nomaterial', 'Allocation': 'Original',
          'Tax': 'Tax', 'Department': 'Operation', 'misc1': 'Nomisc1', 'misc2': 'Nomisc2',
          'sheetName': '基础生产数据-水量、泥量', 'sheetId': 'SHTb4ed3d626a2d', 'elementName': 'ProductData',
          'folderId': 'DIRe437ed8262b4'}
    main(p1, p2)
