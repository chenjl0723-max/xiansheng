'''
公共层协议价格分发脚本
'''

try:
    from _debug import para1, para2
except ImportError:
    para1 = para2 = {}

from deepfos.element.datatable import DataTableMySQL
from deepfos.element.variable import Variable
import pandas as pd
from field_mapping import FieldMapper
from data_filter import DataFilter
from data_distribute import DataDistributor
from datetime import datetime

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)


class DataProcessor:
    def __init__(self, p1, p2):
        """初始化 DataProcessor 类，加载配置表和源数据"""
        self.p1 = p1
        self.p2 = p2

        # 从 p2 获取 app_data 信息
        self.distribution_id = p2['id']
        self.source_table_name = p2['source_table']
        self.target_table_name = p2['target_table']
        self.target_app = p2['target_app']

        # 查询 filter_conditions 表
        filter_conditions_table = DataTableMySQL('filter_conditions')
        t_filter = filter_conditions_table.table
        self.filter_conditions = pd.DataFrame(filter_conditions_table.select_raw(
            where=(t_filter.id == self.distribution_id)
        ))
        print("\nFilter conditions:")
        print(self.filter_conditions if not self.filter_conditions.empty else "No filter conditions found.")

        # 查询 filed_mapping 表
        filed_mapping_table = DataTableMySQL('filed_mapping')
        t_mapping = filed_mapping_table.table
        self.field_mapping = pd.DataFrame(filed_mapping_table.select_raw(
            where=(t_mapping.id == self.distribution_id)
        ))
        print("\nField mappings:")
        print(self.field_mapping if not self.field_mapping.empty else "No field mappings found.")

        # 查询源表数据
        source_table = DataTableMySQL(self.source_table_name)
        # where = (source_table.table.assist_item_type =='物料')
        # print(self.source_table_name)
        self.source_data = source_table.select()
        print(1)
        # print(f"\nSource data from '{self.source_table_name}':")
        # print(self.source_data if not self.source_data.empty else "No source data found.")

        # # 获取变量年
        # variable = Variable(element_name='Variable', path='/Variable')
        # self.year = variable.get('BudYear')

    def process(self):
        """
        主处理逻辑：协调调用筛选、字段映射和下发
        :return: None
        """
        # 如果 source_data 为空，抛出异常终止程序
        if self.source_data.empty:
            print("源数据为空，终止处理")
            raise ValueError("Source data is empty. Cannot proceed with processing.")


        # 数据筛选
        data_filter = DataFilter(self.filter_conditions)
        filtered_data = data_filter.filter(self.source_data)

        # 字段映射
        field_mapper = FieldMapper(self.field_mapping)
        mapped_data = field_mapper.map_fields(filtered_data)
        print(mapped_data)

        mapped_data['Material_code'] = ''
        mapped_data['Material_name'] = ''
        mapped_data['Measure_code'] = ''
        mapped_data['Measure_name'] = ''
        # 使用向量化操作处理 assist_item_type
        mapped_data.loc[mapped_data['assist_item_type'] == '物料', ['Material_code', 'Material_name']] = \
            mapped_data.loc[mapped_data['assist_item_type'] == '物料', ['assist_item_cd', 'assist_item_name']].values
        mapped_data.loc[mapped_data['assist_item_type'] == '度量', ['Measure_code', 'Measure_name']] = \
            mapped_data.loc[mapped_data['assist_item_type'] == '度量', ['assist_item_cd', 'assist_item_name']].values
        # 判断assist_item_type
        print('2',mapped_data)
        mapped_data = mapped_data.drop(['assist_item_cd','assist_item_name','assist_item_type','amt_unit','etl_date'], axis=1)
        print(1)




        # 获取主键和更新字段
        # primary_columns, update_columns = field_mapper.get_primary_and_update_columns(mapped_data.columns)

        # 数据下发
        distributor = DataDistributor(self.p1, self.target_table_name, self.target_app ,self.field_mapping)
        if not mapped_data.empty:
            distributor.distribute(mapped_data)
        else:
            print("No data to insert after processing.")


def main(p1, p2):
    """
    主函数，执行协议价格分发逻辑
    :param p1: 参数字典（用于切换系统）
    :param p2: 参数字典，包含 app_data 信息（id、source_table、target_table、target_app）
    """
    print(f"\nStarting protocol_price_pub.main with p1: {p1}, p2: {p2}")

    # 初始化 DataProcessor
    processor = DataProcessor(p1, p2)

    # 处理数据（筛选、字段映射、下发）
    try:
        processor.process()
    except ValueError as e:
        print(f"Processing failed: {e}")
        return  # 终止程序


if __name__ == '__main__':
    para2 = {'id': '001', 'source_table': 'project_public', 'target_table': 'Entity_ZT_NEW_test',
             'target_app': 'BUDGET'}
    main(para1, para2)