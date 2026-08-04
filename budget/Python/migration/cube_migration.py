from deepfos.element.dimension import Dimension
from deepfos.element.finmodel import FinancialCube
from deepfos.element.datatable import DataTableMySQL
import pandas as pd
from deepfos.element.variable import Variable
from deepfos.element.datatable import DataTableClickHouse
import time
from deepfos import OPTION


def main(p1,p2):
    # 1. 初始化 FinancialCube 获取 WS_cube 数据
    cube = FinancialCube(
        element_name='BEWG')
    # 定义维度表达式来提取全部数据（使用 IDescendant(#root,0) 覆盖所有维度）
    expression = (
        'Year{Base(#root,0)}->Period{Base(#root,0)}->Scenario{Base(#root,0)}->'
        'Version{Base(#root,0)}->Entity{Base(D003429,0)}->Account{Base(#root,0)}->'
        'Material{Base(#root,0)}->Allocation{Base(#root,0)}->Tax{Base(#root,0)}->'
        'Department{Operation}->Measure{Expenses}->misc1{Base(#root,0)}->'
        'misc2{Base(#root,0)}'
    )
    pov = {}  # 无固定 POV，以提取全部

    # 查询 Cube 数据
    data = cube.query(expression, pov=pov, compact=False)
    print(1)
if __name__ == '__main__':
    try:
        from common.__debug import para1
    except:
        pass
    para2 = {}
    main(para1, para2)
