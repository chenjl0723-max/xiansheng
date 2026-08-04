'''
公共层协议价格分发脚本
'''

try:
    from __debug import para1, para2
except ImportError:
    para1 = para2 = {}

from deepfos.element.datatable import DataTableMySQL
from deepfos.element.variable import Variable
import pandas as pd
from field_mapping import FieldMapper
from data_filter import DataFilter
from data_distribute import DataDistributor
from datetime import datetime
import numpy as np

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
        self.source_data = pd.DataFrame(source_table.select_raw())
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

        # misc1列的-改成_
        self.source_data['contract_cd'] = self.source_data['contract_cd'].str.replace('-', '_')

        # 数据筛选
        data_filter = DataFilter(self.filter_conditions)
        filtered_data = data_filter.filter(self.source_data)

        # 字段映射
        field_mapper = FieldMapper(self.field_mapping)
        mapped_data = field_mapper.map_fields(filtered_data)
        # 添加场景、年份、版本、条线
        mapped_data["Scenario"] = 'Budget'
        mapped_data["Version"] = 'Y1'
        mapped_data["Department"] = 'Operation'

        current_date = datetime.now()
        mapped_data["Year"] = str(current_date.year)
        # mapped_data["Year"] = '2025'
        # mapped_data["push_data_time"] = current_date

        
        # 处理价格优先级：是利润筹划的，跨过专属价，取区域价-统一价逻辑area_price > uniform_price；不是利润筹划的，按“专属价-区域价-统一价”的逻辑exclusive_price > area_price > uniform_price
        mapped_data['Price'] = np.where(
            mapped_data['is_restore'] == '1',  # 如果你确定全是字符串 '1'
            mapped_data['price2'].combine_first(mapped_data['price3']),
            mapped_data['price1'].combine_first(
                mapped_data['price2'].combine_first(mapped_data['price3'])
            )
        )
        # mapped_data['Price'] = mapped_data['price1'].combine_first(
        #     mapped_data['price2'].combine_first(mapped_data['price3'])
        # )
        # mapped_data['Price'] = mapped_data['Price'].astype('float64')
        print(mapped_data)
        # 获取主键和更新字段
        # primary_columns, update_columns = field_mapper.get_primary_and_update_columns(mapped_data.columns)

        # 数据下发
        distributor = DataDistributor(self.p1, self.target_table_name, self.target_app ,self.field_mapping)
        price_dt = DataTableMySQL(self.target_table_name)
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