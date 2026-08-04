'''
公共层主脚本，调用统一的 data_distribution 模块
'''

try:
    from _debug import para1, para2
except ImportError:
    para1 = para2 = {}

from deepfos.element.datatable import DataTableMySQL
import data_distribution


def main(p1, p2: dict):
    """
    主脚本，通过 p2 参数获取分发 ID，调用 data_distribution.main 处理数据。

    Args:
        p1: 参数字典（用于切换系统）
        p2: 包含分发 ID 的字典，例如 {'id': '001', 'source_table': 'project_public', 'target_table': 'Entity_ZT_NEW_test', 'target_app': 'BUDGET'}
    """
    distribution_id = p2['id']
    print(f"分发ID: {distribution_id}")

    if not distribution_id:
        raise ValueError("Distribution ID (p2['id']) cannot be empty.")

    # 初始化 app_data 表
    app_data_table = DataTableMySQL("app_data")

    # 验证 app_data 表中是否存在对应记录
    t_app = app_data_table.table
    app_data = app_data_table.select_raw(
        columns=["id", "source_table", "target_table", "target_app"],
        where=t_app.id == distribution_id
    )

    if not app_data:
        raise ValueError(f"No record found in app_data table for id: {distribution_id}")

    print(f"分发ID '{distribution_id}' 正在执行 data_distribution.main...")
    data_distribution.main(p1, p2)


if __name__ == "__main__":
    para2 = {'id': '001', 'source_table': 'project_public', 'target_table': 'Entity_ZT_NEW_test',
             'target_app': 'BUDGET'}
    main(para1, para2)