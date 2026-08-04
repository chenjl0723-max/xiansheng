import pandas as pd

class FieldMapper:
    def __init__(self, field_mapping: pd.DataFrame):
        """
        初始化字段映射器
        :param field_mapping: 字段映射表（pandas.DataFrame 格式），包含 source_field, target_field, is_pk 等字段
        """
        self.field_mapping = field_mapping

    def map_fields(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        字段映射：根据 field_mapping 表重命名数据列
        :param data: 输入数据（pandas.DataFrame 格式）
        :return: 映射后的数据（pandas.DataFrame 格式）
        """
        if self.field_mapping.empty:
            print("No field mappings provided. Using original column names.")
            return data

        field_mapping = self.field_mapping[['source_field', 'target_field']]
        rename_dict = dict(zip(field_mapping['source_field'], field_mapping['target_field']))
        mapped_data = data.rename(columns=rename_dict)
        # print("\nData after field mapping:")
        print('映射名称',mapped_data.columns)
        return mapped_data

    def get_primary_and_update_columns(self, field_mapping, data_columns: list) -> tuple:
        """
        从字段映射表中提取主键字段和更新字段
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

if __name__ == '__main__':
    # 示例数据
    field_mapping_data = pd.DataFrame({
        'id': ['001', '001'],
        'source_field': ['src_field1', 'src_field2'],
        'target_field': ['tgt_field1', 'tgt_field2'],
        'comments': ['map1', 'map2'],
        'is_pk': ['Yes', 'No']
    })
    data = pd.DataFrame({
        'src_field1': ['val1', 'val3'],
        'src_field2': ['val2', 'val4']
    })

    mapper = FieldMapper(field_mapping_data)
    mapped_data = mapper.map_fields(data)
    primary_cols, update_cols = mapper.get_primary_and_update_columns(mapped_data.columns)