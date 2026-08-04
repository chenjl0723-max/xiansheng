"""
added by cjl
added in 20241011
added for 在项目台账分类表中 同步技改和非技改的Operation_JG字段
主要逻辑：

剩余问题：无
"""

try:
    from common._debug import para1, para2
    print(para1)
except ImportError:
    para1 = para2 = {}


import pandas as pd
from deepfos.element.datatable import DataTableMySQL


pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)


def synchronous_update(p2):
    entity_id = p2['Entity_wb1']
    year_id = p2['Year_wb1']
    JG_dt = DataTableMySQL('equipment_profile_JG')
    where = (JG_dt.table.entity == entity_id) & (JG_dt.table.year == year_id)
    JG_df = JG_dt.select(columns=['year','code','Operation_JG'],where = where)
    print(JG_df)
    NJ_dt = DataTableMySQL('equipment_profile_NJ')
    NJ_dt.insert_df(JG_df,updatecol=['Operation_JG'])
    print(1)


# Main function
def main(p1, p2):
    # 同步更新
    synchronous_update(p2)



if __name__ == "__main__":
    p2 = {'elementName': 'taizhang',
          'folderId': 'DIR994921cccf14',
          'sheetName': '设备台账分类 -技改',
          'sheetId': 'SHT56e89e3ad7e84f3eafb4008734cbe80c',
          'Year_wb1': '2025',
          'Entity_wb1': 'Y6120210005'}

    main(para1, p2)