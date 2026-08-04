import pandas as pd
import numpy as np

class DataFilter:
    def __init__(self, filter_conditions: pd.DataFrame):
        """
        初始化数据筛选器
        :param filter_conditions: 筛选条件表（pandas.DataFrame 格式），包含 source_field, logical, filter_value, rule_id 等字段
        """
        self.filter_conditions = filter_conditions

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
            converted_series = pd.to_numeric(series, errors='coerce')
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
                value_list = [val.strip() for val in filter_value.split(',')]
                return series.isin(value_list)
            elif filter_op == 'like':
                pattern = '^' + filter_value.replace('%', '.*') + '$'
                return series.str.contains(pattern, case=True, na=False, regex=True)
            else:
                print(f"不支持的filter_op: {filter_op}")
                return None
        except (ValueError, TypeError) as e:
            print(f"Error applying condition for {series.name} {filter_op} {filter_value}: {e}")
            return None

    def filter(self, source_data: pd.DataFrame) -> pd.DataFrame:
        """
        根据 filter_conditions 表中的筛选条件对源数据进行筛选
        :param source_data: 源数据（pandas.DataFrame 格式）
        :return: 筛选后的数据（pandas.DataFrame 格式）
        """
        if self.filter_conditions.empty:
            print("No filter conditions provided. Returning original data.")
            return source_data

        group_conditions = []
        for rule_id, group in self.filter_conditions.groupby('rule_id'):
            rule_conditions = []
            for _, row in group.iterrows():
                filter_field = row['source_field']
                filter_op = row['logical']
                filter_value = row['filter_value']

                if filter_field not in source_data.columns:
                    print(f"在source_data中找不到字段 {filter_field}")
                    continue

                condition = self._build_condition(source_data[filter_field], filter_value, filter_op)
                if condition is None:
                    continue
                rule_conditions.append(condition)

            if rule_conditions:
                group_conditions.append(np.logical_and.reduce(rule_conditions))

        if group_conditions:
            final_condition = np.logical_or.reduce(group_conditions)
            filtered_data = source_data[final_condition]
        else:
            filtered_data = source_data

        print("\n筛选后数据长度:", len(filtered_data))
        return filtered_data

if __name__ == '__main__':
    # 示例数据
    filter_conditions_data = pd.DataFrame({
        'id': ['001'],
        'source_field': ['text_field'],
        'logical': ['like'],
        'filter_value': ['Y%'],
        'rule_id': ['001']
    })
    source_data = pd.DataFrame({
        'text_field': ['Y123', 'KY123', 'yabc']
    })

    data_filter = DataFilter(filter_conditions_data)
    filtered_data = data_filter.filter(source_data)