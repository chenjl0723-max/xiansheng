"""
added by hr
added in 20260604
added for 更新维度 ZJ_contract 全层级自动插入
主要逻辑：
    从 ZJ_contract_ft 自动构建全维度树：
    根节点 → 一级单位 → 二级单位 → 法人组织 → 项目 → 合同
    每一层父级为空时，自动向上一层兜底，保证维度树完整不断链
    优化：存在则更新UD值，不存在则插入，无多余操作
"""

from deepfos.element.dimension import Dimension
from deepfos.element.datatable import DataTableMySQL
import pandas as pd
from deepfos.element.variable import Variable

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)


class UpdateZJContract:
    def __init__(self):
        self.year = Variable('Variable').get_value('BudYear')
        self.dim = Dimension("ZJ_contract")

        # 读取源表 ZJ_contract_ft
        table001 = "ZJ_contract"
        self.df_source_info = DataTableMySQL(table001)

        # 关联表 Entity_GL_td 取出 name, ud7
        self.df_entity_gl = DataTableMySQL("Entity_GL_td").select_raw(columns=["name", "ud7"])
        self.df_entity_gl = pd.DataFrame(self.df_entity_gl).rename(columns={"ud7": "ud11"})

        # 过滤条件：关键字段不能为空
        where = (
                self.df_source_info.table.contract_no.notnull() &
                self.df_source_info.table.fnumber.notnull()
        )

        self.df_source = pd.DataFrame(self.df_source_info.select_raw(columns=None, where=where))
        print(f"源表数据行数：{len(self.df_source)}")

    def update_full_model(self):
        if self.df_source.empty:
            print("源数据表为空")
            return

        df = self.df_source.copy()

        # ===================== 全层级自动构建 =====================
        large_new = self.update_region(df, "D000001")
        area_new = self.update_area(df)
        org_new = self.update_org(df)
        project_new = self.update_org_project(df)
        contract_new = self.update_zj_contract_level(df)

        all_df = pd.concat([
            large_new, area_new, org_new, project_new, contract_new
        ], ignore_index=True)

        # ===================== 根节点 =====================
        data = {
            "language_zh-cn": ["北控水务集团"],
            "name": ["D000001"],
            "parent_name": ["#root"],
            "language_en": ["北控水务集团"],
            "sharedmember": [False]
        }
        all_df = pd.concat([pd.DataFrame(data), all_df], ignore_index=True)

        # ===================== 终极全量清洗（必加，否则服务异常） =====================
        all_df = all_df.fillna("").astype(str)
        all_df = all_df.replace("nan", "").replace("None", "")
        all_df = all_df.replace(r'[\n\t"\'\\]', "", regex=True)

        # 去重（按name+parent_name去重，保留合同共享节点的多父级关系）
        all_df = all_df.drop_duplicates(subset=["name", "parent_name"], keep="first")

        # ===================== 必须 full_replace =====================
        self.dim.load_dataframe(all_df, "full_replace")

        print(f"✅ ZJ_contract 全层级更新完成！本次处理：{len(all_df)} 条")

    # 一级单位
    def update_region(self, df, parent_name):
        df_large = df[["lvl1_org_cd", "lvl1_org_name"]].drop_duplicates()
        df_large = df_large[df_large["lvl1_org_cd"].notna()]
        df_large.rename(columns={
            "lvl1_org_cd": "name",
            "lvl1_org_name": "language_zh-cn"
        }, inplace=True)
        df_large["parent_name"] = parent_name
        df_large["language_en"] = df_large["language_zh-cn"]
        df_large["sharedmember"] = False
        df_large["ud11"] = 'YT00'
        df_large = df_large.drop_duplicates(subset=["name"], keep="first")
        return df_large

    # 二级单位
    def update_area(self, df):
        df_area = df[["lvl2_org_cd", "lvl2_org_name", "lvl1_org_cd"]].drop_duplicates()
        df_area = df_area[df_area["lvl2_org_cd"].notna()]
        df_area["parent_name"] = df_area["lvl1_org_cd"].fillna("D000001")
        df_area.rename(columns={
            "lvl2_org_cd": "name",
            "lvl2_org_name": "language_zh-cn",
            "lvl1_org_cd": "ud1"
        }, inplace=True)
        df_area["language_en"] = df_area["language_zh-cn"]
        df_area["sharedmember"] = False
        df_area["ud11"] = 'YT00'
        df_area = df_area.drop_duplicates(subset=["name"], keep="first")
        return df_area

    # 法人组织
    def update_org(self, df):
        df_org = df[["org_code", "org_name", "lvl2_org_cd", "lvl1_org_cd"]].drop_duplicates()
        df_org = df_org[df_org["org_code"].notna()]
        df_org["parent_name"] = df_org["lvl2_org_cd"].fillna(df_org["lvl1_org_cd"]).fillna("D000001")
        df_org.rename(columns={
            "org_code": "name",
            "org_name": "language_zh-cn",
            "lvl1_org_cd": "ud1",
            "lvl2_org_cd": "ud2"

        }, inplace=True)
        df_org["language_en"] = df_org["language_zh-cn"]
        df_org["sharedmember"] = False
        df_org["ud11"] = 'YT00'
        df_org = df_org.drop_duplicates(subset=["name"], keep="first")
        return df_org

    # 项目
    def update_org_project(self, df):
        df_proj = df[["fnumber", "fname", "org_code", "lvl2_org_cd", "lvl1_org_cd"]].drop_duplicates()
        df_proj = df_proj[df_proj["fnumber"].notna()]
        df_proj["parent_name"] = df_proj["org_code"].fillna(df_proj["lvl2_org_cd"]).fillna(
            df_proj["lvl1_org_cd"]).fillna("D000001")
        df_proj.rename(columns={
            "fnumber": "name",
            "fname": "language_zh-cn",
            "lvl1_org_cd": "ud1",
            "lvl2_org_cd": "ud2",
            "org_code": "ud3"
        }, inplace=True)

        # ===================== 只在这里增加：关联 Entity_GL_td 取 ud7 → ud11 =====================
        df_proj = pd.merge(df_proj, self.df_entity_gl, on="name", how="left")
        df_proj["ud11"] = df_proj["ud11"].fillna("")  # 空值填空字符串

        df_proj["language_en"] = df_proj["language_zh-cn"]
        df_proj["sharedmember"] = False
        df_proj = df_proj.drop_duplicates(subset=["name"], keep="first")
        return df_proj

    # 合同
    def update_zj_contract_level(self, df):
        df_contract = df[[
            "bill_no", "contract_name", "fnumber",
            "lvl1_org_cd", "lvl2_org_cd", "org_code",
            "contract_attr", "loan_attr", "fin_product_name",
            "latest_rate", "biz_date", "contr_termination_date",
            "fin_contract_amount", "actual_draw_amount","biz_type_lv3_cd"
        ]].copy()

        df_contract = df_contract[df_contract["bill_no"].notna()]

        # 父级自动兜底
        df_contract["parent_name"] = (
            df_contract["fnumber"]
            .fillna(df_contract["org_code"])
            .fillna(df_contract["lvl2_org_cd"])
            .fillna(df_contract["lvl1_org_cd"])
            .fillna("D000001")
        )

        df_contract.rename(columns={
            "bill_no": "name",
            "contract_name": "language_zh-cn",
            "lvl1_org_cd": "ud1",
            "lvl2_org_cd": "ud2",
            "org_code": "ud3",
            "contract_attr": "ud4",
            "loan_attr": "ud5",
            "fin_product_name": "ud6",
            "latest_rate": "ud7",
            "biz_date": "ud8",
            "contr_termination_date": "ud9",
            "fin_contract_amount": "ud10",
            "biz_type_lv3_cd": "ud11",
            "actual_draw_amount": "ud12"
        }, inplace=True)

        # ===================== UD10、UD12 空值自动补 0 =====================
        df_contract["ud10"] = df_contract["ud10"].fillna(0)
        df_contract["ud12"] = df_contract["ud12"].fillna(0)
        df_contract["language_en"] = df_contract["language_zh-cn"]
        # 同一个合同出现多次时，第一条写False（非共享），其余写True（共享）
        df_contract["sharedmember"] = df_contract.duplicated(subset=["name"], keep="first")
        return df_contract


def main(p1: dict = None, p2: dict = None) -> None:
    updater = UpdateZJContract()
    updater.update_full_model()


if __name__ == "__main__":
    from CWYS._debug import para1, para2
    main(para1, para2)
