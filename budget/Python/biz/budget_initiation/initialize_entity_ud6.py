# -*- coding: utf-8 -*-
'''
@file    : initialize_entity_ud6.py
@Time    :
@Author  : XMX
@Software: PyCharm
@Desc    : 初始化 水厂、虚拟子水厂、项目 的 边界性质 为 边界不变
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


def calc(p1, p2):
    # 限定维度表达式、字段选择
    dimension = 'Entity'
    # 水厂、虚拟子水厂、项目
    expression = 'Entity{Level(#root,0,4,5)}'
    fields = ['name', 'parent_name', 'ud6']
    df_data, dim = fun_qurey_dimension(dimension, expression, fields)
    print(df_data)

    # 初始化 边界不变
    df_data['ud6'] = 'Invariant'

    # 更新维度
    dim.load_dataframe(dataframe=df_data, strategy='incr_replace')


def main(p1, p2):
    if "folderId" in p2:
        del p2['folderId']
    if "elementName" in p2:
        del p2['elementName']
    try:
        calc(p1, p2)
    except Exception as e:
        traceback.print_exc()


# debug
if __name__ == '__main__':
    from common._debug import para1,para2
    main(para1, para2)

