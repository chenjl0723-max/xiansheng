"""
added by cjl
added in 20260226
added for 更新运营项目的维度
主要逻辑：
    根据entity_info 项目表，依次写入维度：
    大区、区域、管理组织\法人、项目
剩余问题：目前项目信息不完善，无法执行代码
"""

#部署时，这些要注释以及修改
# try:
#     from common._debug import para1, para2
#     print('1',para1)
# except ImportError:
#     para1 = para2 = {}


from deepfos.element.dimension import Dimension
from deepfos.db.mysql import MySQLClient
from deepfos.element.datatable import DataTableMySQL
import pandas as pd
from datetime import datetime
from deepfos.element.variable import Variable
# from add_entity_to_flow import main as add

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)


def main(p1,p2):
    data = {
        'language_zh-cn': [
            '东部大区',
            '北京建工环境',
            '太仓建邦环境水务有限公司',
            '江苏太仓建邦公司常胜路一期项目-BOT',
            '东部大区',
            '北京建工环境',
            '太仓开发区污水处理厂',
            '江苏太仓建邦公司常胜路一期项目-BOT',
            '北控水务集团（法人组织）',
            '北控水务集团（管理组织）'
        ],
        'name': [
            'D003429',
            'D008450',
            '040190',
            'Y3220210080',
            'GL_D003429',
            'GL_D008450',
            'D007343',
            'Y3220210080',
            'D000001',
            'GL_D000001'
        ],
        'parent_name': [
            'D000001',
            'D003429',
            'D008450',
            '040190',
            'GL_D000001',
            'GL_D003429',
            'GL_D008450',
            'D007343',
            '#root',
            '#root'
        ],
        'language_en': [
            '东部大区',
            '北京建工环境',
            '太仓建邦环境水务有限公司',
            '江苏太仓建邦公司常胜路一期项目-BOT',
            '东部大区',
            '北京建工环境',
            '太仓开发区污水处理厂',
            '江苏太仓建邦公司常胜路一期项目-BOT',
            '北控水务集团（法人组织）',
            '北控水务集团（管理组织）'
        ],
        'isActive': ['Y'] * 10,
        'sharedmember': [False, False, False, False, False, False, False, True, False, False]
    }
    df = pd.DataFrame(data)

    df = pd.read_excel('all_df2.xlsx')
    # 如果你想让索引从1开始（与表格一致）
    df.index = df.index + 1
    dim = Dimension("Entity_org_test")
    rsg_new = dim.load_dataframe(df, "full_replace", reorder=True)


if __name__ == "__main__":
    from common._debug import para1, para2
    # print('1',para1)
    main(para1,para2)
