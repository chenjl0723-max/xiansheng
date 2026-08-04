"""
预算初始化   陈小
"""
from deepfos.element.dimension import Dimension
from deepfos.element.finmodel import FinancialCube
from deepfos.element.datatable import DataTableMySQL
import pandas as pd
from deepfos.element.variable import Variable
from deepfos.element.datatable import DataTableClickHouse
import time
from deepfos import OPTION



pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)


OPTION.api.timeout = 3600


def get_variable(variable, v_key):
    var = Variable(variable)
    return var.get_value(v_key)


def init_pc(year):
    year_1 = str(int(year) - 1)
    year_2 = str(int(year) - 2)
    year_3 = str(int(year) - 3)
    # 清空2张ck数据
    cube1 = FinancialCube("S_Cube")
    cube2 = FinancialCube("Audit_Cube")
    # 更改 process表的数据范围
    process_map = {
        "Year": "Year{%s;%s;%s;%s}" % (year, year_1, year_2,year_3),
        "Version": "Version{Base(#root, 0)}",
        "Scenario": "Scenario{Actual;Budget;Forecast;Difference}",
    }
    data_block_map = {"Entity": 'Entity{IDescendant(1, 0)}', "Department": 'Department{IDescendant(#root, 0)}'}
    # 执行初始化
    D = cube1.pc_upsert(
        process_map=process_map, data_block_map=data_block_map, status="Status08"
    )
    D = cube2.pc_upsert(
        process_map=process_map, data_block_map=data_block_map, status="Status08"
    )
    print(D)
def init_pc_status01(year):
    year_1 = str(int(year) - 1)
    year_2 = str(int(year) - 2)
    year_3 = str(int(year) - 3)
    # 清空2张ck数据
    cube1 = FinancialCube("S_Cube")
    cube2 = FinancialCube("Audit_Cube")
    # 更改 process表的数据范围
    process_map = {
        "Year": "Year{%s;%s;%s;%s}" % (year, year_1, year_2, year_3),
        "Version": "Version{Y1}",
        "Scenario": "Scenario{Actual;Budget;Forecast;Difference}",
    }
    data_block_map = {"Entity": 'Entity{IDescendant(1, 0)}', "Department": 'Department{Base(#root, 0)}'}
    # 执行初始化
    cube1.pc_upsert(
        process_map=process_map, data_block_map=data_block_map, status="Status01"
    )
    cube2.pc_upsert(
        process_map=process_map, data_block_map=data_block_map, status="Status01"
    )


def get_dim(dim, expression):
    dim_client = Dimension(dim)
    fields = ["name"]
    dim_data = pd.DataFrame(
        dim_client.query(expression=expression, fields=fields, as_model=False)
    )
    dim_data = dim_data[['name']]
    return dim_data


def merge_process_block_entity(year):
    table_client = DataTableClickHouse("process_control_S_Cube")
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
              & (t.process_seg_2_value == "Budget")
              & (t.process_seg_3_value == "Y1")
              & (t.process_status == "Status01")
        # distinct=True
    )
    print(len(process_data))

    table_client = DataTableClickHouse("datatable_block_control_S_Cube")
    block_data = table_client.select(
        columns=[
            "datablock_id",
            "datablock_seg_1_value",
            "datablock_seg_2_value",
        ],
    )
    print(len(block_data))
    # 获取 Entity维度中存在的 entity。29400 5880 1118
    entity_data = get_dim("Entity", "Entity{Descendant(1, 0)}")
    print(len(entity_data))
    entity_data = entity_data.rename(columns={"name": "entity_id"})
    block_data = block_data.rename(
        columns={
            "datablock_seg_1_value": "entity_id",
            "datablock_seg_2_value": "department_id",
        }
    )
    process_data = process_data.rename(
        columns={
            "process_seg_1_value": "year_id",
            "process_seg_2_value": "scenario_id",
            "process_seg_3_value": "version_id",
            "process_status": "result_status",
        }
    )
    merge_block_entity_data = pd.merge(block_data, entity_data)
    print(len(merge_block_entity_data))
    merge_process_block_entity_data = pd.merge(process_data, merge_block_entity_data)
    print(len(merge_process_block_entity_data))
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
    print(result)
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
    # print(p2)
    # 获取全局变量 year的值
    year = get_variable("Variable", "BudYear")
    # print(year)

    # 步骤1
    # tbl = DataTableClickHouse("process_control_BEWG")
    # tbl.delete({
    #     # "process_seg_1_value": ['2024', '2023', '2022', '2021', '2020', '2019', '2018', '2025', '2026', '2027', '2028',
    #     #                         '2029', '2030'],
    #     "process_seg_1_value": ['2025'],
    #     "datablock_id":["yvpEj55D"]
    # })
    # tbl = DataTableClickHouse("datatable_block_control_BEWG")
    # tbl.delete({
    #     "datablock_seg_2_value": ['Totaldepartment', 'Operation', 'Nodepartment', 'HR', 'Equipment']
    # })

    # 步骤2
    # 财务模型权限初始化
    init_pc(year)
    print("财务模型初始化完成")

    # # 步骤3
    # # 更新 Y1 的status 为 Status01
    init_pc_status01(year)
    print("状态修改完成")

    # # 步骤4
    merge_data = merge_process_block_entity(year)
    print(merge_data)
    # 业务模型初始化
    data_to_sql("Approval_Progress_Record", merge_data, year, "Budget")
    print("业务模型初始化完成。")

    '''
    # 初始化运行天数
    from budget.Python.biz.budget_initiation.genarate_day import main
    main(p1, p2)

    # 新增 初始化 组织Etntiy的ud7、8、9 --xmx
    from budget.Python.biz.budget_initiation.initialize_entity_ud789 import main as init
    init(p1, p2)

    # 新增 初始化 水厂、虚拟子水厂、项目 的 边界性质 为 边界不变 --xmx
    from budget.Python.biz.budget_initiation.initialize_entity_ud6 import main as init_ud6
    init_ud6(p1, p2)

    # 新增 水厂分摊比例、原材料基本信息、协议价格、水厂项目基本信息、税率年份复制  --cjl-2025/06/09
    from budget.Python.biz.budget_initiation.year_initialization import main as year_init
    year_init(p1, p2)

    # 新增 台账信息保留两年数据；把year-2年数据存进历史台账表中  --cjl-2025/06/09
    from budget.Python.biz.budget_initiation.equipment_installation_to_profile import main as equipment_installation
    equipment_installation(p1, p2)

    # 新增 预算明细表，把year-1年数据存进历史表中 --cjl-2025/06/09
    from budget.Python.biz.budget_initiation.detail_to_his import main as detail_installatin
    detail_installatin(p1, p2)
    '''

if __name__ == '__main__':
    try:
        from BIZ._debug import para1, para2
    except:
        pass
    para2 = {}
    main(para1, para2)


