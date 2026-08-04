# -*- coding: utf-8 -*-
'''
@file    : rate_initiation.py
@Desc    : 集团百分比初始化
'''

try:
    from CWYS._debug import para1, para2
except ImportError:
    para1 = para2 = {}

import pandas as pd
import traceback
import time
import os
from datetime import datetime

from deepfos.element.datatable import DataTableMySQL
from deepfos.element.finmodel import FinancialCube
from deepfos.element.variable import Variable
from deepfos.element.dimension import Dimension
from deepfos.element.pyscript import PythonScript






def YW08020001_ini(year, scenario,version,periods):
    """
    将 YW08020001 科目所有组织、所有期间的值初始化为 1
    """
    cube = FinancialCube('sub_profit_cube')

    # 1. 获取所有组织（Entity）
    dim = Dimension('Entity_GL')
    entities = dim.query("Base(D000001,0)", fields=['name','ud7'], as_model=False)
    entity_df = pd.DataFrame(entities).rename(columns={'name': 'Entity_GL', 'ud7': 'Commercial'})
    entity_list = [e['name'] for e in entities]

    # 2. 所有期间（1-12月 + Noperiod）


    # 3. 构造初始化数据
    init_data = []
    for entity in entity_list:
        for period in periods:
            init_data.append({
                'Account_lirun': 'YW08020001',
                'Year': str(year),
                'Scenario': scenario,
                'Measure': 'Rate',        # 根据实际调整
                'Period': period,
                'Entity_GL': entity,
                'Version': version,              # 根据实际调整
                'Comprehensive': 'NoTax',
                'Misc1': 'nomisc1',
                'Misc2': 'nomisc2',
                'data': 1
            })

    init_df = pd.DataFrame(init_data)

    init_df = pd.merge(init_df, entity_df[['Entity_GL','Commercial']],  how='left',on='Entity_GL')
    init_df = init_df[init_df['Commercial'].notna() & (init_df['Commercial'] != '')]
    # 5. 保存新数据
    cube.save(init_df)

    print(f"✅ YW08020001 初始化完成！共 {len(init_df)} 条记录（{len(entity_list)} 个组织 × {len(periods)} 个期间）")






def main(p1, p2):
    year = Variable('Variable').get('BudYear')
    last_year = str(int(year)-1)
    version = Variable('Variable').get('Edit_Ver')
    periods = [str(i) for i in range(1, 13)] 
    periods_fore = ['10','11','12']
    YW08020001_ini(year=int(year), scenario='Budget',version=version,periods=periods)
    YW08020001_ini(year=int(last_year), scenario='Actual',version=version,periods=periods+['Noperiod'])
    YW08020001_ini(year=int(last_year), scenario='Forecast',version=version,periods=periods_fore)




# debug
if __name__ == '__main__':

    main(para1, para2)

