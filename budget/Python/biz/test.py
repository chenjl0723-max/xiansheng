# -*- coding: utf-8 -*-
'''
@file    : actual_push_cube.py
@Time    :
@Author  : CHEN
@Software: PyCharm
@Desc    : 实际数进利润预算模型
'''

try:
    from common.__debug import para1, para2
    # print(para1)
except ImportError:
    para1 = para2 = {}
from deepfos.options import OPTION
import pandas as pd
import traceback
import time
import os
from datetime import datetime
from deepfos.db.mysql import MySQLClient
from deepfos.element.datatable import DataTableClickHouse
from deepfos.element.finmodel import FinancialCube
from deepfos.element.datatable import DataTableClickHouse as ck
from deepfos.element.datatable import DataTableMySQL
from deepfos.element.variable import Variable
from deepfos.element.dimension import Dimension, DimMember
from deepfos.element.pyscript import PythonScript
import numpy as np




def main(p1, p2):
    dt = DataTableMySQL('Opreation_JG')
    df = dt.select()
    # 写入财务预算分析模型
    p1['app'] = 'nlfnyl002'
    p1['space'] = 'nlfnyl'
    OPTION.api.header = p1

    dt = DataTableMySQL('slry_subj_mp_info')
    df = dt.select()
    print(1)

# debug
if __name__ == '__main__':
    para2 = {'Year': '2025'}
    main(para1, para2)

