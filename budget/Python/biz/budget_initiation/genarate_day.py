"""
每月天数初始化进 cube
"""

import time
import calendar
import pandas as pd

from deepfos.element.dimension import Dimension
from deepfos.element.finmodel import FinancialCube
from deepfos.element.variable import Variable


def get_variable():
    """
    获取全局变量对应的值
    :return:全局变量对应的值
    """

    var = Variable('Variable', path='/03_Variable')
    print('var:', var.get_value('BudYear'))
    return var.get_value('BudYear')


def get_dimension():
    """
    获取 Entity 维度下，name 字段中，所有子节点的数据
    :return:Entity 维度下，name 字段中，所有子节点的数据
    """

    dim = Dimension('Entity', path='/02_Dimension')
    org2 = dim.query("AndFilter(Base(#root,0),Attr(isActive,'Y'))", as_model=False, fields=['name'])
    dt_dim = pd.DataFrame(org2)
    return dt_dim


def genarate_per_day(year, scenario, start_month, end_month):
    """
    计算特定年份，需要的月份有多少天。并将该数据，与从维度中取出来的数据，一同做处理笛卡尔积处理
    :param year:
    :param scenario:
    :param start_month:
    :param end_month:
    :return:
    """

    # 计算每月的天数，生成月份和天数对应的 DataFrame 类型的数据
    year_month_days = [[m_data, calendar.monthrange(year, m_data)[1]] for m_data in range(start_month, end_month + 1)]
    df_days = pd.DataFrame(year_month_days, columns=['Period', 'data'])
    print("df_days:", df_days)

    # 获取维度数据
    name_id = get_dimension()

    # 生成两数据连接标志字段
    name_id_left = name_id.assign(key=1)
    df_days_right = df_days.assign(key=1)

    # 数据做笛卡尔积合并
    name_days = pd.merge(name_id_left, df_days_right, on='key').drop('key', axis=1)
    # 复制笛卡尔积合并后的数据
    name_days_other = name_days.copy(deep=True)

    # 1 . 把其他维度的数据加入到 name_days 中
    other_data_1 = {'Account': 'YW0202',
                    'Year': str(year),
                    'Scenario': scenario,
                    'Measure': 'Nomeasure',
                    # 'Period': '1；2；3；4；5；6；7；8；9；10；11；12',
                    'Version': 'Y1',
                    'Material': 'Nomaterial',
                    'Department': 'Operation',
                    'Allocation': 'Original',
                    'Tax': 'Tax',
                    'Misc1': 'Nomisc1',
                    'Misc2': 'Nomisc2'}

    for data_col, data_values in other_data_1.items():
        name_days[data_col] = data_values

    # 2 . 把其他维度的数据加入到 name_days_other 中，这里 'Measure' 为 'Expense'
    other_data_2 = {'Account': 'YW0202',
                    'Year': str(year),
                    'Scenario': scenario,
                    'Measure': 'Expenses',
                    # 'Period': '1；2；3；4；5；6；7；8；9；10；11；12',
                    'Version': 'Y1',
                    'Material': 'Nomaterial',
                    'Department': 'Operation',
                    'Allocation': 'Original',
                    'Tax': 'Tax',
                    'Misc1': 'Nomisc1',
                    'Misc2': 'Nomisc2'}

    for data_col_other, data_values_other in other_data_2.items():
        name_days_other[data_col_other] = data_values_other

    # 将 name_days_other 合并到 name_days 中
    name_days = pd.concat([name_days, name_days_other], ignore_index=True)

    # 最后去掉 id 列 ， 把 name 的名称该成 Entity。并将数据存回 Cube
    name_days.drop('id', axis=1, inplace=True)
    name_days.rename(columns={'name': 'Entity'}, inplace=True)

    # 对上述数据进行覆盖存储
    cube = FinancialCube('WS_cube')

    # 将上面的第一部分十三个对应维度数据删除，其中 Entity 为 name_id
    expression_1_dict = other_data_1
    expression_1_dict['Entity'] = name_id['name'].tolist()
    expression_1_dict['Period'] = [str(year_data) for year_data in range(1, 13)]
    cube.delete(expression_1_dict)

    # 将上面的第二部分十三个对应维度数据删除，其中 Entity 为 name_id
    expression_2_dict = other_data_2
    expression_2_dict['Entity'] = name_id['name'].tolist()
    expression_2_dict['Period'] = [str(year_data) for year_data in range(1, 13)]
    cube.delete(expression_2_dict)

    print('name_days:', name_days)
    # 对新生成的数据进行保存
    cube.save(name_days)
    print('运行结束')


def main(p1, p2):
    year = get_variable()
    genarate_per_day(year=int(year), scenario='Budget', start_month=1, end_month=12)
    genarate_per_day(year=(int(year) - 1), scenario='Forecast', start_month=10, end_month=12)


if __name__ == '__main__':
    try:
        from common._debug import para1
    except:
        pass
    p2 = {}
    main(para1, p2)
