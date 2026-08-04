"""
added by cjl
added in 20241011
added for 根据技改计划修改项目维度的技改状态
主要逻辑：
    将Operation_JG表中“Entity_Opreation”
    字段值匹配Entity_zt_new表的“project_code”字段，
    如果匹配上，就修改Entity_zt_new表的“is_JG”字段为“是”
剩余问题：无

#➢ 来源表：Operation_JG，字段“Entity_Opreation”为项目编码，如果存在说明该项目有技改项目
#➢ 来源表：Entity_zt_new，“project_code”字段为项目编码
#➢ 处理逻辑： 将Operation_JG表中“Entity_Opreation”字段值匹配Entity_zt_new表的“project_code”字段，如果匹配上，就修改Entity_zt_new表的“is_JG”字段为“是”

"""

try:
    from common._debug import para1, para2
    print(para1)
except ImportError:
    para1 = para2 = {}
from common import commons
# from kafka_main.conf.config import *
############################################################
from deepfos.element.datatable import DataTableMySQL
from deepfos.element.dimension import Dimension
from deepfos.options import OPTION
import pandas as pd

class UpdateEntity:
    def __init__(self, p2):
        # jg = DataTableMySQL('Opreation_JG')
        # jg_tb = pd.DataFrame(jg.select_raw(columns=['Entity_Opreation']))
        # print(jg_tb)



        self.df_JG = p2["Entity_wb1"]
        print(self.df_JG)
        self.dim = Dimension("Entity")

        # self.df_entity_v3 = self.dim.query(expression="AndFilter(IDescendant(1,0),Attr(ud10,'P02'))", fields=['name','ud10'])
        self.df_entity = commons.dim_.get_dim_attr("Entity", "Descendant(1,0)", fields=["name", "parent_name", "ud10"])
        self.df_entity = self.df_entity[self.df_entity['ud10'] == 'P02']
        print(self.df_entity)

        self.existing_projects = self.df_entity[self.df_entity["name"]== self.df_JG].copy()
        # self.existing_projects = self.df_entity[self.df_entity["name"].isin(jg_tb["Entity_Opreation"])].copy()
        print(self.existing_projects)
        # print(self.df_entity_v3[self.df_entity_v3['ud10']=='P02'])
        # 获取Entity_ZT_NEW的数据
        # self.target_tab = "Entity_td"
        # print("__init__函数的self.df_JG", self.df_JG)

    def update_project(self,p1):
        # Uat用户
        # p1['user'] = '41cba8da-cf06-4b4d-8104-46e9900ea0e5'
        # p1['token'] = 'C820CCAEE16E5B1B3E6A4B5558A422BAE6719FA1BBA907021E1892020861394C'
        # p1['cookie'] = 'deepfos_users=%7B%22invitationActivation%22%3Atrue%2C%22mobilePhone%22%3A%2213671042437%22%2C%22nickName%22%3A%22%E9%99%88%E6%99%B6%E7%A3%8A%22%2C%22nickname%22%3A%22%E9%99%88%E6%99%B6%E7%A3%8A%22%2C%22token%22%3A%22C820CCAEE16E5B1B3E6A4B5558A422BAE6719FA1BBA907021E1892020861394C%22%2C%22tokenKey%22%3A%22deepfos_token%22%2C%22type%22%3A1%2C%22userId%22%3A%2241cba8da-cf06-4b4d-8104-46e9900ea0e5%22%2C%22username%22%3A%22w-chenjinglei01%22%7D; deepfos_token=C820CCAEE16E5B1B3E6A4B5558A422BAE6719FA1BBA907021E1892020861394C'

        # # 生产用户
        # p1['user'] = '1ef2c32f-4a07-4f19-bff0-bf3bd2e662df'
        # p1['token'] = '675DAA54DABB51FEAA4CFCFABEA13EFA006EC29350123F06A1E03044728F9FA1'
        # p1['cookie'] = 'deepfos_users=%7B%22invitationActivation%22%3Atrue%2C%22nickName%22%3A%22chenjinglei%22%2C%22nickname%22%3A%22chenjinglei%22%2C%22token%22%3A%22675DAA54DABB51FEAA4CFCFABEA13EFA006EC29350123F06A1E03044728F9FA1%22%2C%22tokenKey%22%3A%22deepfos_token%22%2C%22type%22%3A1%2C%22userId%22%3A%221ef2c32f-4a07-4f19-bff0-bf3bd2e662df%22%2C%22username%22%3A%22chenjinglei%22%7D; deepfos_token=675DAA54DABB51FEAA4CFCFABEA13EFA006EC29350123F06A1E03044728F9FA1'


        # print(p1)
        # OPTION.api.header = p1
        if not self.existing_projects.empty:
            self.existing_projects["ud11"] = "Y"
            print('existing_projects', self.existing_projects)
            # existing_projects = existing_projects.drop_duplicates(["name"], keep="first")

            # 更新现有项目
            rsg_existing = self.dim.load_dataframe(self.existing_projects, "incr_replace")

            print("变更技改项目：", list(self.existing_projects["name"]))

def main(p1,p2):
    # p2 = {"Entity_wb1":"Y4120210008"}
    print(p2)
    e = UpdateEntity(p2)
    e.update_project(p1)

if __name__ == "__main__":
    # print(para1)
    main(para1,para2)