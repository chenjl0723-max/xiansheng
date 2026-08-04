try:
    from __debug import para1, para2
except ImportError:
    para1 = para2 = {}

from deepfos.element.datatable import DataTableMySQL
import project_pub_bak
import project_pub
import protocol_price_pub
import act_job_pub

# 子程序：无特殊逻辑映射（组织推业务预算、经营计划；法人组织推敬意计划；实际数推送业务预算、小业态）
def distribute_to_business_budget(p1, p2: dict, app_data_table: DataTableMySQL):
    """
    项目分发到业务预算。

    Args:
        p2: 包含分发 ID 的字典，例如 {'id': '001'}。
        app_data_table: app_data 表的 DataTableMySQL 实例。
    """
    distribution_id = p2['id']
    print(f"Running 'distribute_to_business_budget' for distribution ID: {distribution_id}")

    # 查询 app_data 表，获取与分发 ID 相关的记录
    t_app = app_data_table.table
    app_data = app_data_table.select_raw(
        columns=["id", "source_table", "target_table", "target_app"],
        where=t_app.id == distribution_id
    )
    app_data = app_data[0]
    # print(app_data)
    if app_data:
        print(app_data)
        project_pub_bak.main(p1,app_data)
    else:
        raise ValueError(f"No record found in app_data table for id: {distribution_id}")


# 子程序：有比较级的校验（协议价格推业务预算）
def protocol_price_to_business_budget(p1, p2: dict, app_data_table: DataTableMySQL):
    """
    协议价格进入业务预算。

    Args:
        p2: 包含分发 ID 的字典，例如 {'id': '003'}。
        app_data_table: app_data 表的 DataTableMySQL 实例。
    """
    distribution_id = p2['id']
    print(f"Running 'distribute_to_business_budget' for distribution ID: {distribution_id}")

    # 查询 app_data 表，获取与分发 ID 相关的记录
    t_app = app_data_table.table
    app_data = app_data_table.select_raw(
        columns=["id", "source_table", "target_table", "target_app"],
        where=t_app.id == distribution_id
    )
    app_data = app_data[0]
    # print(app_data)
    if app_data:
        print(app_data)
        protocol_price_pub.main(p1,app_data)
    else:
        raise ValueError(f"No record found in app_data table for id: {distribution_id}")


# 子程序：补充维度信息（实际数进入业务预算）
def act_to_business_budget(p1, p2: dict, app_data_table: DataTableMySQL):
    """
    协议价格进入业务预算。

    Args:
        p2: 包含分发 ID 的字典，例如 {'id': '003'}。
        app_data_table: app_data 表的 DataTableMySQL 实例。
    """
    distribution_id = p2['id']
    print(f"Running 'distribute_to_business_budget' for distribution ID: {distribution_id}")

    # 查询 app_data 表，获取与分发 ID 相关的记录
    t_app = app_data_table.table
    app_data = app_data_table.select_raw(
        columns=["id", "source_table", "target_table", "target_app"],
        where=t_app.id == distribution_id
    )
    app_data = app_data[0]
    # print(app_data)
    if app_data:
        print(app_data)
        act_job_pub.main(p1,app_data)
    else:
        raise ValueError(f"No record found in app_data table for id: {distribution_id}")

def main(p1,p2: dict):
    """
    主脚本，通过 p2 参数获取分发 ID，根据映射字典调用对应的子程序。

    Args:
        p2: 包含分发 ID 的字典，例如 {'id': '001'}。
    """
    # 验证 p2 参数
    distribution_id = p2['id']
    print(distribution_id)
    if not distribution_id:
        raise ValueError("Distribution ID (p2['id']) cannot be empty.")

    # 初始化 app_data 表
    app_data_table = DataTableMySQL("app_data")

    # 定义分发 ID 到子程序的映射
    distribution_scripts = {
        '001': distribute_to_business_budget,
        '002': distribute_to_business_budget,
        '003': protocol_price_to_business_budget,
        '004': protocol_price_to_business_budget,
        '005': act_to_business_budget,
        '006': distribute_to_business_budget,
        '007': distribute_to_business_budget,
        '008': distribute_to_business_budget,
        '009': distribute_to_business_budget,
        '010': protocol_price_to_business_budget,
        '011': distribute_to_business_budget,
        '012': distribute_to_business_budget,
    }

    # 根据分发 ID 获取对应的子程序
    script = distribution_scripts.get(distribution_id)
    if script:
        print(f"分发ID '{distribution_id}' 映射到 {script.__name__}. 正在执行...")
        script(p1, p2, app_data_table)
    else:
        raise ValueError(
            f" 不支持分发ID '{distribution_id}'。  支持的ID: {list(distribution_scripts.keys())}")


if __name__ == "__main__":
    # 示例调用
    # try:
    para2 = {'id': '003'}  # 假设分发 ID 为 '001'
    main(para1,para2)
    # except Exception as e:
    #     print(f"Error in main script: {e}")