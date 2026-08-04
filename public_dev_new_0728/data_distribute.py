from deepfos.element.datatable import DataTableMySQL
from deepfos.options import OPTION
import pandas as pd
from field_mapping import FieldMapper
from deepfos.element.variable import Variable

class DataDistributor:
    SYSTEM_APP_MAPPING = {
        'BUDGET_01': 'yhacsq014',
        'PLAN': 'yhacsq004',
    }

    def __init__(self, p1: dict, target_table_name: str, target_app: str ,field_mapping):
        """
        初始化数据下发器
        :param p1: 参数字典（用于切换系统）
        :param target_table_name: 目标表名
        :param target_app: 目标应用程序（system_id）
        :param field_mapping:
        """
        self.p1 = p1
        self.target_table_name = target_table_name
        self.target_app = target_app
        self.field_mapping = field_mapping

    def distribute(self, data: pd.DataFrame) -> bool:
        """
        将数据插入目标表
        :param data: 要插入的数据（pandas.DataFrame 格式）
        :param primary_columns: 主键字段列表
        :param update_columns: 更新字段列表
        :return: 布尔值（下发是否成功）
        """
        try:
        # 获取对应的 app
            app = self.SYSTEM_APP_MAPPING.get(self.target_app)
            if not app:
                print(f"Error: 找不到target_app '{self.target_app}'的应用程序映射")
                return False

            # 切换系统
            self.p1['app'] = app
            OPTION.api.header = self.p1
            print(f"\n已成功将系统切换到应用程序 '{self.target_app}'")

            # 获取变量年
            # variable = Variable(element_name='Variable', path='/Variable')
            # year = variable.get('BudYear')
            # data['Year'] = year


            # 连接目标表，保留目标表内存在的字段
            target_table = DataTableMySQL(self.target_table_name)
            field_names = list(target_table.structure.columns.keys())
            print("\n目标表字段名:", field_names)
            common_columns = [col for col in data.columns if col in field_names]
            print(common_columns)
            data = data[common_columns]
            # 获取主键字段和更新字段
            field_mapper = FieldMapper(data)
            primary_columns, update_columns = field_mapper.get_primary_and_update_columns(self.field_mapping, data.columns)

            if not primary_columns:
                print("配置中找不到主键，执行常规插入.")
                target_table.insert_df(data)
            else:
                print(f"插入主键: {primary_columns}, 更新列: {update_columns}")
                print(data)
                target_table.insert_df(data, updatecol=update_columns)

            return True

        except Exception as e:
            print(f"Error: {e}")
            return False




if __name__ == '__main__':
    # 示例数据
    p1 = {'some_param': 'value'}
    target_table_name = 'Entity_ZT_NEW_test'
    target_app = 'BUDGET'
    data = pd.DataFrame({
        'tgt_field1': ['val1', 'val3'],
        'tgt_field2': ['val2', 'val4']
    })
    primary_columns = ['tgt_field1']
    update_columns = ['tgt_field2']

    distributor = DataDistributor(p1, target_table_name, target_app)
    distributor.distribute(data, primary_columns, update_columns)