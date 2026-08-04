import time
import os
import sys
import warnings
import numpy as np
import pandas as pd
from deepfos.element.finmodel import FinancialCube
from deepfos.element.variable import Variable

warnings.filterwarnings('ignore')
top_path = os.path.abspath(os.path.join(__file__, "../.."))
sys.path.append(top_path)
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)

from budget.Python.biz.phaseII.newly import config_calc as audit
from common._debug import para1
p2 = {'elementName': 'Electricity',
              'folderId': 'DIRb6550dd20485',
              'sheetName': '电费&污泥费',
                # 电费污泥费sheetId
              # 'sheetId': 'SHT8f94a382ea18426cba26b784cdde54e9',
                # 水价收入sheetid
              'sheetId': 'SHT491538d6904b401a829131b3b70f2c9c',
              'Year_wb1': '2025',
              'Entity_wb1': 'XN21012_01',
              'Version_wb1': 'Y1',
              'Tax_wb1': 'Tax',
              'Scenario_wb1': 'Actual',
              'Department_wb1': 'Operation',
              'Material_wb1': 'Nomaterial',
              'Allocation_wb1': 'Original',
              'Misc1_wb1': 'Nomisc1',
              'Misc2_wb1': 'Nomisc2'}

rename_map = {
        "Entity_wb1":"Entity",
        "Year_wb1":"Year",
        "Measure_wb1": "Measure",
        "Allocation_wb1": "Allocation",
        "Version_wb1": "Version",
        "Department_wb1": "Department",
        "Tax_wb1": "Tax",
        'Material_wb1': 'Material',
        "Misc1_wb1": "Misc1",
        "Misc2_wb1": "Misc2"
    }
p2 = {rename_map.get(key, key): value for key, value in p2.items()}

# print(p2)
audit.main(para1, p2)


