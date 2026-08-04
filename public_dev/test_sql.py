try:
    from _debug import para1, para2
except ImportError:
    para1 = para2 = {}


from deepfos.element.datatable import DataTableMySQL
from deepfos.options import OPTION
import numpy as np
import pandas as pd
import pypika.functions as pf
from pypika import Criterion

from deepfos.db.mysql import MySQLClient


pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)


# 查询数据表的元数据信息，字段，中文名，类型，长度，主键等
def main(p1,p2):
    app_data = DataTableMySQL("project_public")
    a = app_data.select()
    a.to_csv("project_public.csv",encoding='utf-8-sig',index=False)

    app_data_meta = app_data.meta  # 同步调用，DataTableMySQL 会自动将异步方法转为同步
    print(app_data_meta)

    app_data = DataTableMySQL("filter_conditions")
    app_data_meta = app_data.meta  # 同步调用，DataTableMySQL 会自动将异步方法转为同步
    print(app_data_meta)

    app_data = DataTableMySQL("filed_mapping")
    app_data_meta = app_data.meta  # 同步调用，DataTableMySQL 会自动将异步方法转为同步
    print(app_data_meta)



    print("Table structure for 'app_data':")
    for col in app_data_meta.datatableColumn:
        # print(type(col))
        print(f"Column: {col.name}")
        print(f"  Type: {col.type}")
        print(f"  Primary Key: {'Yes' if col.whetherPrimary else 'No'}")
        print(f"  Nullable: {'Yes' if col.whetherEmpty else 'No'}")
        print("-" * 30)



if __name__ == '__main__':
    main(para1, para2)