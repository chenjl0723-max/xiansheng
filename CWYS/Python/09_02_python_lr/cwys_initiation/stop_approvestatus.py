# -*- coding: utf-8 -*-
'''
@file    : stop_approvestatus.py
@Time    : 2026-08-03
@Author  : CHEN
@Software: PyCharm
@Desc    : 资金+利润停用项目状态改为Status08
'''

from deepfos.element.dimension import Dimension
from deepfos.element.finmodel import FinancialCube
from deepfos.element.datatable import DataTableMySQL
import pandas as pd
from deepfos.element.variable import Variable
from deepfos.element.datatable import DataTableClickHouse
from deepfos.element.pyscript import PythonScript
from datetime import datetime
import traceback
import time
import os
from deepfos import OPTION



pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)


OPTION.api.timeout = 3600


def get_variable(variable, v_key):
    var = Variable(variable)
    return var.get_value(v_key)





def init_pc(year):

    dt= DataTableMySQL('ZT_Entity')
    where = "ud1 != 'Y'"
    df = dt.select(columns=['name'],where=where)
    entity = ';'.join(df['name'].astype(str))
    year_1 = str(int(year) - 1)
    year_2 = str(int(year) - 2)
    year_3 = str(int(year) - 3)
    # 清空1张ck数据
    cube1 = FinancialCube("sub_profit_cube")
    # cube2 = FinancialCube("Audit_Cube")
    # 更改 process表的数据范围
    process_map = {
        "Year": "Year{%s;%s;%s;%s}" % (year, year_1, year_2,year_3),
        "Version": "Version{Base(#root, 0)}",
        "Scenario": "Scenario{Actual;Budget;Forecast;Difference}",
    }
    data_block_map = {"Entity_GL": 'Entity_GL{%s}' % entity}
    # 执行初始化
    D = cube1.pc_upsert(
        process_map=process_map, data_block_map=data_block_map, status="Status08"
    )



def main(p1, p2):

    # 获取全局变量 year的值
    year = get_variable("Variable", "BudYear")

    start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    countAll = 0
    countSuccess = 0
    countError = 0
    countMsg = f"{start_time} 开始执行利润预算启动任务\n"

    try:
        # 财务模型权限初始化
        init_pc(year)
        print("财务模型初始化完成")



    except Exception as e:
        countError = 1
        countAll = 1
        error_detail = traceback.format_exc()
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 利润预算启动失败: {str(e)}\n"
        countMsg += f"详细错误信息:\n{error_detail}\n"
        print(f"利润预算启动执行出错: {e}")
        traceback.print_exc()

        # ====================== 写入日志 ======================
    ele_name = os.path.basename(__file__)
    ele_path = os.path.dirname(os.path.abspath(__file__))

    try:
        sync_log = PythonScript(element_name='pyLog', path='/09_Python/common', should_log=True)
        sync_result = sync_log.run(
            parameter={
                'ele_name': ele_name,
                'ele_path': ele_path,
                'data_count': countAll,
                'error_count': countError,
                'logs': countMsg,
                'dt': datetime.now().strftime('%Y%m%d'),
                'start_time': start_time,
                'exe_parameter': str(p2)
            }
        )
        if sync_result:
            print("日志记录成功！")
        else:
            print("日志记录失败！")
    except Exception as log_e:
        print(f"日志记录异常: {log_e}")

    # 返回执行结果（与维度脚本保持一致）
    return False if countError > 0 else True

if __name__ == '__main__':
    try:
        from CWYS._debug import para1, para2
    except:
        pass
    para2 = {}
    main(para1, para2)


