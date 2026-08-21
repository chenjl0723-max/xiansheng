# -*- coding: utf-8 -*-
'''
@file    : budget_initiation.py
@Time    : 2026-04-22
@Author  : CHEN
@Software: PyCharm
@Desc    : 利润预算启动任务
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


def get_dim(dim, expression):
    dim_client = Dimension(dim)
    fields = ["name"]
    dim_data = pd.DataFrame(
        dim_client.query(expression=expression, fields=fields, as_model=False)
    )
    dim_data = dim_data[['name']]
    return dim_data


def init_pc(year):
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
    data_block_map = {"Entity_GL": 'Entity_GL{IDescendant(#root, 0)}'}
    # 执行初始化
    D = cube1.pc_upsert(
        process_map=process_map, data_block_map=data_block_map, status="Status08"
    )
    # D = cube2.pc_upsert(
    #     process_map=process_map, data_block_map=data_block_map, status="Status08"
    # )
    # print(D)
def init_pc_status01(year):
    year_1 = str(int(year) - 1)
    year_2 = str(int(year) - 2)
    year_3 = str(int(year) - 3)
    # 清空2张ck数据
    cube1 = FinancialCube("sub_profit_cube")
    # cube2 = FinancialCube("Audit_Cube")


    # 更改 process表的数据范围
    process_map_budget = {
        "Year": "Year{%s}" % year,
        "Version": "Version{Base(#root, 0)}",
        "Scenario": "Scenario{Budget}",
    }
    process_map_forecast = {
        "Year": "Year{%s}" % year_1,
        "Version": "Version{Base(#root, 0)}",
        "Scenario": "Scenario{Forecast;Difference}",
    }

    process_map_actual = {
        "Year": "Year{%s;%s}" % (year_1,year_2),
        "Version": "Version{Base(#root, 0)}",
        "Scenario": "Scenario{Actual;Budget}"

    }

    data_block_map = {"Entity_GL": 'Entity_GL{IDescendant(#root, 0)}'}
    data_block_map_act = {"Entity_GL":"Entity_GL{Base(PT_D000001,0);Base(ZG_D000001,0);Base(D003437,0);Base(D003440,0);Base(D003448,0)}"}

    # 执行初始化
    cube1.pc_upsert(
        process_map=process_map_budget, data_block_map=data_block_map, status="Status01"
    )

    cube1.pc_upsert(
        process_map=process_map_forecast, data_block_map=data_block_map, status="Status01"
    )

    cube1.pc_upsert(
        process_map=process_map_actual, data_block_map=data_block_map, status="Status01"
    )


    # cube2.pc_upsert(
    #     process_map=process_map, data_block_map=data_block_map, status="Status01"
    # )





def merge_process_block_entity(year):
    table_client = DataTableClickHouse("process_control_sub_profit_cube")
    t = table_client.table
    process_data = table_client.select(
        columns=[
            "datablock_id",
            "process_seg_1_value",
            "process_seg_2_value",
            "process_seg_3_value",
            "process_status",
            # "create_time"
        ],
        where=(t.process_seg_1_value == year)
              & (t.process_seg_3_value == "Budget")
              # & (t.process_seg_2_value == "Y1")
              & (t.process_status == "Status01")
        # distinct=True
    )
    # print(len(process_data))

    table_client = DataTableClickHouse("datatable_block_control_sub_profit_cube")
    block_data = table_client.select(
        columns=[
            "datablock_id",
            "datablock_seg_1_value",
            # "datablock_seg_2_value",
        ],
    )

    # print(len(block_data))
    # 获取 Entity维度中存在的 entity。29400 5880 1118
    entity_data = get_dim("Entity_GL", "Entity_GL{Descendant(#root, 0)}")
    # print(len(entity_data))
    entity_data = entity_data.rename(columns={"name": "entity_id"})
    block_data = block_data.rename(
        columns={
            "datablock_seg_1_value": "entity_id",
            # "datablock_seg_2_value": "department_id",
        }
    )
    process_data = process_data.rename(
        columns={
            "process_seg_1_value": "year_id",
            "process_seg_3_value": "scenario_id",
            "process_seg_2_value": "version_id",
            "process_status": "result_status",
        }
    )
    merge_block_entity_data = pd.merge(block_data, entity_data)
    # print(len(merge_block_entity_data))
    merge_process_block_entity_data = pd.merge(process_data, merge_block_entity_data)
    # print(len(merge_process_block_entity_data))
    # del merge_process_block_entity_data["id"]
    del merge_process_block_entity_data["datablock_id"]
    merge_process_block_entity_data = merge_process_block_entity_data.drop_duplicates()
    return merge_process_block_entity_data


def data_to_sql(table, merge_data, year, scenario):
    sql_client = DataTableMySQL(table)
    t = sql_client.table
    sql_client.delete(where=(t.year_id == year) & (t.scenario_id == scenario))
    sql_client.insert_df(merge_data)


def updata_y1_status():
    process_table_client = DataTableClickHouse("process_control_WS_cube")
    t = process_table_client.table
    process_data = process_table_client.select(where=t.process_seg_3_value == "Y1")
    block_table_client = DataTableClickHouse("datatable_block_control_WS_cube")
    block_data = block_table_client.select()[["datablock_seg_2_value", "datablock_id"]]
    data = pd.merge(process_data, block_data, how="left", on="datablock_id")
    data = data[data["process_seg_3_value"] == "Y1"]
    data.loc[data["datablock_seg_2_value"] != "Totaldepartment", "process_status"] = "Status01"
    # 过滤掉 datablock_seg_2_value == "Totaldepartment" 的记录
    data = data[data["datablock_seg_2_value"] != "Totaldepartment"]
    # 假设 DataFrame 名为 df
    result = data[data['datablock_id'] == 'CewwYLNH']
    # print(result)
    data = data[
        [
            "process_seg_5_value",
            # "create_time",
            "process_seg_3_value",
            "process_seg_4_value",
            "process_seg_10_value",
            "process_seg_8_value",
            "process_seg_2_value",
            "datablock_id",
            "process_seg_7_value",
            "process_seg_9_value",
            "process_status",
            "creater",
            "process_seg_6_value",
            "process_seg_1_value",
        ]
    ]

    process_table_client.delete(
        {
            "process_seg_3_value": [
                "Y1"
            ],
            "datablock_seg_2_value":[
                "Equipment","Nodepartment","Operation","Technical"
            ]
        }
    )
    print()
    process_table_client.insert_df(data,chuncksize=50000)


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

        # # 步骤3
        # # 更新 Y1 的status 为 Status01
        init_pc_status01(year)
        print("状态修改完成")

        # # 步骤4
        merge_data = merge_process_block_entity(year)

        # 业务模型初始化
        data_to_sql("Approval_Progress_Record", merge_data, year, "Budget")
        print("业务模型初始化完成。")


        # 集团分红比

        countSuccess = 1
        countAll = 1
        countMsg += f"{time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())} 利润预算启动处理完成\n"


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
        from CWYS.__debug import para1, para2
    except:
        pass
    para2 = {}
    main(para1, para2)


