"""
added by cjl
added in 20250522
added for 原材料基本信息中间变存进目标表
主要逻辑：

"""

#部署时，这些要注释以及修改
# try:
#     from common._debug import para1, para2
#     print('1',para1)
# except ImportError:
#     para1 = para2 = {}

# from numpy.distutils.system_info import dfftw_info
from deepfos.element.dimension import Dimension
from deepfos.db.mysql import MySQLClient
from deepfos.element.datatable import DataTableMySQL
import pandas as pd
from datetime import datetime
from deepfos.element.variable import Variable

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)

class MaterialV1:
    def __init__(self):
        # self.year = Variable(element_name='Variable').get_value('BudYear')
        self.year = Variable('Variable').get_value('BudYear')
        self.df_material_source = DataTableMySQL("Material_active_ingredient")

        self.df_material_target = DataTableMySQL("Material_BasicData")

    def process(self,p1,p2):
        print(1)
        df_material_s = pd.DataFrame(self.df_material_source.select_raw(columns=["Ingredient","COD","TN","Coefficient","Equivalent"]))
        df_material_s["Year"] = self.year
        df_material_s["Department"] = "Operation"
        df_material_s["Scenario"] = "Budget"
        df_material_s["Version"] = "Y1"

        self.df_material_target.insert_df(df_material_s,updatecol=["COD","TN","Coefficient","Equivalent","Scenario","Department","Version"])
        print(2)



def main(p1,p2):
    e = MaterialV1()
    e.process(p1,p2)


if __name__ == "__main__":
    from common._debug import para1, para2
    # print('1',para1)
    main(para1,para2)
