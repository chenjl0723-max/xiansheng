# -*- coding: utf-8 -*-
'''
@file    : initialize_entity_ud789.py
@Time    :
@Author  : XMX
@Software: PyCharm
@Desc    : 初始化 组织Etntiy的ud7、8、9
'''

import traceback
import pandas as pd
from deepfos.element.dimension import Dimension, DimMember

# from _debug import p1, p2


def fun_qurey_dimension(dimension, expression, fields):
    # 维度 实例化
    dim = Dimension(dimension, path='/02_Dimension')
    # 查询维度现有成员
    df = pd.DataFrame(dim.query(expression=expression, fields=fields, as_model=False))
    df = df.rename(columns={'description_zh_cn': 'language_zh-cn'})
    del df['id']
    df = df.where(df.notnull(), None)

    return df, dim


def initialize(p1, p2):
    # 查询维度数据
    dimension = 'Entity'
    fields = ['name', 'parent_name', 'ud7', 'ud8', 'ud9']
    expression = 'IDescendant(1,0)'
    df_entity, dim = fun_qurey_dimension(dimension, expression, fields)

    # 初始化为空
    df_entity['ud7'] = ''
    df_entity['ud8'] = None
    df_entity['ud9'] = None

    # 更新维度
    a = dim.load_dataframe(dataframe=df_entity, strategy='incr_replace')
    print('已初始化Entity的ud7、8、9')


def main(p1, p2):
    if "folderId" in p2:
        del p2['folderId']
    if "elementName" in p2:
        del p2['elementName']
    try:
        # 初始化 组织Etntiy的ud7、8、9
        initialize(p1, p2)
    except Exception as e:
        traceback.print_exc()


# # debug
# if __name__ == '__main__':
#     # p1 = {}
#     p2 = {'name': 'PS33003_01', 'sheetName': 'Sheet1', 'sheetId': 'SHT472355511aca'}
#     main(p1, p2)

