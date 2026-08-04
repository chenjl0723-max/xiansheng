'''
    公共层项目分发脚本
'''

try:
    from _debug import para1, para2
except ImportError:
    para1 = para2 = {}


from deepfos.element.datatable import DataTableMySQL
from deepfos.options import OPTION
import numpy as np
import pandas as pd
import pypika.functions as pf

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)

class DataProcessor:

    # system_id 到 app 的映射
    SYSTEM_APP_MAPPING = {
        'BUDGET': 'yhacsq002',
        'PLAN': 'yhacsq004',
    }

    def __init__(self, p1, p2):
        """初始化 DataProcessor 类，创建 DataTableMySQL 实例"""
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
        print("\n筛选条件:")
        print(self.filter_conditions if not self.filter_conditions.empty else "No filter conditions found.")

        # 查询 filed_mapping 表
        filed_mapping_table = DataTableMySQL('filed_mapping')
        t_mapping = filed_mapping_table.table
        self.field_mapping = pd.DataFrame(filed_mapping_table.select_raw(
            where=(t_mapping.id == self.distribution_id)
        ))
        print("\n字段映射:")
        print(self.field_mapping if not self.field_mapping.empty else "No field mappings found.")

        # 查询源表数据
        source_table = DataTableMySQL(self.source_table_name)
        self.source_data = pd.DataFrame(source_table.select_raw())
        # print(f"\n源数据 '{self.source_table_name}':")
        # print(self.source_data if not self.source_data.empty else "No source data found.")



    # def get_sql_db(self, table_name, col, where):
    #     """
    #     查询数据库并返回 DataFrame
    #     :param table_name: 表名
    #     :param col: 查询的列（列表或 None）
    #     :param where: 筛选条件（deepfos 表达式）
    #     :return: 查询结果（pandas.DataFrame）
    #     """
    #     get_table = DataTableMySQL(table_name)
    #     self.table = get_table.table
    #     db = pd.DataFrame(get_table.select_raw(where=where, columns=col))
    #     print(db)
    #     return db


    def get_primary_and_update_columns(self, field_mapping, data_columns):
        """
        从字段映射表中提取主键字段和更新字段
        :param field_mapping: 字段映射表数据（pandas.DataFrame 格式）
        :param data_columns: 数据中的列名（列表）
        :return: 元组 (primary_columns, update_columns)
                 - primary_columns: 主键字段列表
                 - update_columns: 用于更新的字段列表（除主键外的字段）
        """
        # 提取主键字段（is_pk == 'Yes'）
        primary_rows = field_mapping[field_mapping['is_pk'] == '1']
        primary_columns = []
        for _, row in primary_rows.iterrows():
            target_field = row['target_field']
            if target_field in data_columns:  # 确保主键字段在数据中存在
                primary_columns.append(target_field)

        # 提取更新字段（除主键外的字段）
        update_columns = [col for col in data_columns if col not in primary_columns]

        print(f"\n主键字段: {primary_columns}")
        print(f"更新字段: {update_columns}")
        return primary_columns, update_columns


    def _convert_to_numeric(self, series, filter_value, filter_op):
        """
        将字段值和筛选值转换为数值类型（用于数值比较）
        :param series: pandas.Series，待转换的字段值
        :param filter_value: 筛选值（字符串）
        :param filter_op: 操作符（例如 '大于'）
        :return: 转换后的 series 和 filter_value
        """
        if filter_op not in ['大于', '小于', '大于等于', '小于等于']:
            return series, filter_value  # 非数值比较，保持原样

        try:
            # 将字段值转换为数值类型
            converted_series = pd.to_numeric(series, errors='coerce')
            # 将 filter_value 转换为浮点数
            converted_value = float(filter_value)
            return converted_series, converted_value
        except (ValueError, TypeError) as e:
            print(f"Error converting {series.name} or {filter_value} to numeric: {e}")
            return None, None

    def _build_condition(self, series, filter_value, filter_op):
        """
        构造单个筛选条件
        :param series: pandas.Series，字段值
        :param filter_value: 筛选值（字符串）
        :param filter_op: 操作符（例如 '等于'）
        :return: 布尔 Series（条件结果），或 None（如果失败）
        """
        try:
            if filter_op == '等于':
                return series == filter_value
            elif filter_op == '不等于':
                return series != filter_value
            elif filter_op == '大于':
                converted_series, converted_value = self._convert_to_numeric(series, filter_value, filter_op)
                if converted_series is None:
                    return None
                return converted_series > converted_value
            elif filter_op == '小于':
                converted_series, converted_value = self._convert_to_numeric(series, filter_value, filter_op)
                if converted_series is None:
                    return None
                return converted_series < converted_value
            elif filter_op == '大于等于':
                converted_series, converted_value = self._convert_to_numeric(series, filter_value, filter_op)
                if converted_series is None:
                    return None
                return converted_series >= converted_value
            elif filter_op == '小于等于':
                converted_series, converted_value = self._convert_to_numeric(series, filter_value, filter_op)
                if converted_series is None:
                    return None
                return converted_series <= converted_value
            elif filter_op == 'in':
                # 将 filter_value 拆分为列表（假设以逗号分隔）
                value_list = [val.strip() for val in filter_value.split(',')]
                return series.isin(value_list)
            elif filter_op == 'like':
                # 使用 str.contains 进行模式匹配
                # 将 % 替换为 .*, 并设置 case=False（不区分大小写）
                pattern = '^' + filter_value.replace('%', '.*') + '$'
                # 区分大小写（case=True），缺失值视为 False（na=False）
                return series.str.contains(pattern, case=True, na=False, regex=True)
            else:
                print(f"不支持的filter_op: {filter_op}")
                return None
        except (ValueError, TypeError) as e:
            print(f"Error applying condition for {series.name} {filter_op} {filter_value}: {e}")
            return None

    def filter_data(self, source_data, filter_conditions):
        """
        根据 filter_conditions 表中的筛选条件对源数据进行筛选
        :param source_data: 源数据（pandas.DataFrame 格式，未重命名）
        :param filter_conditions: 筛选条件表数据（pandas.DataFrame 格式）
        :return: 筛选后的数据（pandas.DataFrame 格式）
        """
        if filter_conditions.empty:
            print("没有筛选条件. 直接返回源表数据.")
            return source_data

        # 按 rule_id 分组，构造条件
        group_conditions = []
        for rule_id, group in filter_conditions.groupby('rule_id'):
            rule_conditions = []
            for _, row in group.iterrows():
                filter_field = row['source_field']
                filter_op = row['logical']
                filter_value = row['filter_value']

                # 确保字段存在
                if filter_field not in source_data.columns:
                    print(f"在source_data中找不到字段 {filter_field}")
                    continue

                # 构造单个条件
                condition = self._build_condition(source_data[filter_field], filter_value, filter_op)
                if condition is None:
                    continue
                rule_conditions.append(condition)

            # 组内条件用 AND 组合
            if rule_conditions:
                group_conditions.append(np.logical_and.reduce(rule_conditions))

        # 组间条件用 OR 组合
        if group_conditions:
            final_condition = np.logical_or.reduce(group_conditions)
            filtered_data = source_data[final_condition]
        else:
            filtered_data = source_data  # 如果没有筛选条件，返回原数据

        print("\n筛选后数据长度:", len(filtered_data))
        return filtered_data

    def process(self):
        """
        主处理逻辑
        :return: 筛选和映射后的数据（pandas.DataFrame 格式）
        """

        # 如果 source_data 为空，直接返回
        if self.source_data.empty:
            # print("源数据为空，跳过筛选")
            raise ValueError("源数据为空，终止程序.")

        # 数据筛选（在重命名之前）
        source_data = self.filter_data(self.source_data, self.filter_conditions)

        # 提取字段映射
        if self.field_mapping.empty:
            # print("No field mappings provided. Using original column names.")
            raise ValueError("映射关系为空，终止程序.")
        else:
            field_mapping = self.field_mapping[['source_field', 'target_field']]
            rename_dict = dict(zip(field_mapping['source_field'], field_mapping['target_field']))
            # 重命名 source_data 的列
            mapped_data = source_data.rename(columns=rename_dict)
            print("\nData after field mapping:")
            print(mapped_data.columns)

        return mapped_data

    def switch_system(self, data):
        """
        根据 target_app 切换系统，插入目标表
        :param data: 筛选和映射后的数据


        :return: 布尔值（切换是否成功）
        """
        try:
            # 获取 target_app
            system_id = self.target_app

            # 获取对应的 app
            app = self.SYSTEM_APP_MAPPING.get(system_id)
            if not app:
                print(f"Error: 找不到target_app '{system_id}'的应用程序映射")
                return False

            # 切换系统
            self.p1['app'] = app
            OPTION.api.header = self.p1
            print(f"\n已成功将系统切换到应用程序 '{system_id}'")

            # 连接目标表，保留目标表内存在的字段
            target_table = DataTableMySQL(self.target_table_name)

            field_names = list(target_table.structure.columns.keys())
            print("\n目标表字段名:", field_names)
            common_columns = [col for col in data.columns if col in field_names]
            data = data[common_columns]

            # 获取主键字段和更新字段
            # field_mapper = FieldMapper(self.field_mapping)
            primary_columns, update_columns = self.get_primary_and_update_columns(self.field_mapping,
                                                                                  common_columns)

            if not primary_columns:
                print("配置中找不到主键，执行常规插入.")
                # 如果没有主键，执行普通插入
                target_table.insert_df(data)
            else:
                # 如果有主键，使用 INSERT INTO ... ON DUPLICATE KEY UPDATE
                print(f"插入主键: {primary_columns}, 更新列: {update_columns}")
                target_table.insert_df(data, updatecol=update_columns)

            return True

        except Exception as e:
            print(f"Error: {e}")
            return False


def main(p1, p2):
        """
        主函数，执行项目分发逻辑
        :param p1: 参数字典（用于切换系统）
        :param p2: 参数字典，包含 app_data 信息（id、source_table、target_table、target_app）
        """
        print(f"\nStarting project_pub.main with p1: {p1}, p2: {p2}")

        # 初始化 DataProcessor
        processor = DataProcessor(p1, p2)

        # 处理数据（筛选和字段映射）
        result = processor.process()

        # 切换系统并插入目标表
        if not result.empty:
            processor.switch_system(result)
        else:
            print("没有数据下发.")


if __name__ == '__main__':
    para2 = {'id': '001', 'source_table': 'project_public', 'target_table': 'Entity_ZT_NEW_test', 'target_app': 'BUDGET'}
    main(para1, para2)