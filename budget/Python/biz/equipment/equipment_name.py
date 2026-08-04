# equipment_name
# 1 设备：新增设备拼接列（技改/非技改） location+equip_seq_new+name_new = name
# 1 设备20241014更新：新增设备拼接列（技改/非技改）“名称”=关联设施+设备序号+【标准设备名称】 location equip_seq_new、name_new = name ，例如1期1#鼓风机房4#曝气风机
# 2 从列里取数时，从维度里拿到描述值，根据成员值匹配


import pandas as pd
import traceback
from deepfos.db.mysql import MySQLClient
from deepfos.element.dimension import Dimension
from deepfos.element.datatable import DataTableMySQL


class Name_concatenation():
    def __init__(self,p1,p2):
        self.year = p2['Year_wb1']
        self.entity = p2['Entity_wb1']
        self.department = p2['Department_wb1']
        self.equipment_location = p2['equipment_location_wb1']
        self.scenario = p2['Scenario_wb1']
        self.version = p2['Version_wb1']

        # print(p1,p2)
        if self.department == 'Equipment':
            self.profile_tb = DataTableMySQL('equipment_profile_NJ')
            where = ((self.profile_tb.table.year == self.year) & (self.profile_tb.table.entity == self.entity) & (
                self.profile_tb.table.code.like('NE%')))
        elif self.department == 'Technical':
            self.profile_tb = DataTableMySQL('equipment_profile_JG')
            where = ((self.profile_tb.table.year == self.year) & (self.profile_tb.table.entity == self.entity) & (
                self.profile_tb.table.code.like('JE%'))& (self.profile_tb.table.equipment_location == self.equipment_location))

        col = ['year','code','location','name','name_new','equip_seq_new']
        # where = ((self.profile_tb.table.year == self.year) & (self.profile_tb.table.entity == self.entity) &(self.profile_tb.table.code.like('NE%')))
        self.profile_df = self.profile_tb.select(columns=col,where = where)
        print(self.profile_df)





    def name_add(self,p1, p2):

        # 查询维度
        dim = Dimension('Number', path='/02_Dimension/')
        dim_Number = dim.query('Number{Descendant(No,0)}', as_model=False, fields=["description_zh_cn"])
        dt_dim_Number = pd.DataFrame(dim_Number)
        # dt_dim_Number.drop(['expectedName','id'], axis=1, inplace=True)
        # dt_dim_Number.rename(columns={'description_zh_cn':'equip_num'}, inplace=True)
        print(dt_dim_Number)

        # 3.2 读取维度 Equipment
        dim = Dimension('Facility_name_type', path='/02_Dimension/')
        # dim_Facility = dim.query('Equipment{Base(GZW,0);Base(CJ,0);Base(XT,0)}', as_model=False, fields=["aggweight", "description_zh_cn"])
        dim_Facility = dim.query('Facility_name_type{Base(#root,0)}', as_model=False,
                                 fields=["description_zh_cn"])
        dt_dim_Facility = pd.DataFrame(dim_Facility)
        # dt_dim_Facility.drop(['expectedName', 'id'], axis=1, inplace=True)
        # dt_dim_Facility.rename(columns={'description_zh_cn': 'equip_name'}, inplace=True)
        print(dt_dim_Facility)

        # 替换设备序号 equip_seq_new
        mapping = dict(zip(dt_dim_Number['name'], dt_dim_Number['description_zh_cn']))
        self.profile_df['equip_seq_new'] = self.profile_df['equip_seq_new'].map(mapping).fillna(self.profile_df['equip_seq_new'])

        # 替换设备名称 name_new
        mapping = dict(zip(dt_dim_Facility['name'], dt_dim_Facility['description_zh_cn']))
        self.profile_df['name_new'] = self.profile_df['name_new'].map(mapping).fillna(self.profile_df['name_new'])

        # 拼接 location, equip_seq_new, name_new 到 name 列
        self.profile_df['name'] = self.profile_df['location'].astype(str) + self.profile_df['equip_seq_new'].astype(str) + self.profile_df['name_new'].astype(str)
        print(self.profile_df)
        print(1)
        dt = self.profile_df[['year','code','name']]
        self.profile_tb.insert_df(dt,updatecol=['name'])





def main(p1, p2):
    n = Name_concatenation(p1, p2)
    n.name_add(p1,p2)



# debug
if __name__ == '__main__':
    from common._debug import para1,para2
    para2 = {'elementName': 'new_equipment_float',
             'folderId': 'DIR994921cccf14',
             'sheetName': '非技改-新增设备预算填报',
             'sheetId': 'SHT96fb18823e754c28870c60d58722a533',
             'Year_wb1': '2025',
             'Entity_wb1': 'Y6120210005',
             'Department_wb1': 'Technical',
             'Scenario_wb1': 'Budget',
             'Version_wb1': 'Y1',
             'equipment_location_wb1': 'el01'}

    main(para1, para2)

