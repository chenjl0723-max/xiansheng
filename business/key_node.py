"""
added by wlm
added in 20230805
added for 关键节点
主要逻辑：

剩余问题：
"""
from deliver_plan import *
from deepfos.element.datatable import DataTableMySQL
import datetime

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)

class key_node:
    def __init__(self):
        self.source_table = "Construction_Key"
        self.log_table = "Construction_Key_log"
        self.source_url = "/ETL/Form_Business/"

        self.target_table = "2_Construction_Key"
        self.target_main_table = "Basic_Data_Full"
        self.target_url = "/Form/0_Business_Model/Full_Business_Model/"

        # 获取年份变量
        self.year = var_.get_variable("Variable", "Year")

        period = str(datetime.datetime.now().month)
        self.key = key_map[period]
        # 获取中间表数据
        df_data = rdb_.select(columns=None, tbl=self.source_table, path=self.source_url)

        # 翻译大区、区域、法人公司
        dict_mapping = get_org_mapping()
        df_data["Region_GJ"] = df_data["Region_GJ"].map(dict_mapping)
        df_data["Regional_Company_GJ"] = df_data["Regional_Company_GJ"].map(
            dict_mapping
        )
        df_data["Incorporated_Company_GJ"] = df_data["Incorporated_Company_GJ"].map(
            dict_mapping
        )
        # 处理数据
        self.source_data = control_df(df_data, "Entity_Investment_GJ", "关键节点")

    def get_key_data(self):
        """
        获取并保存关键节点数据
        """

        if self.source_data.empty:
            print("关键节点中间表数据为空")
            return

        # 保存Basic_Data_Full表
        # cols = [
        #     "Year",
        #     "name",
        #     "Region_GJ",
        #     "Regional_Company_GJ",
        #     "parent_name",
        #     "Entity_Name_GJ",
        #     "Format_1_GJ",
        #     "Format_2_GJ",
        #     "Investment_GJ",
        # ]
        # df_basic = self.source_data[cols].rename(
        #     columns={
        #         "name": "Entity_Number",
        #         "Region_GJ": "Region",
        #         "Regional_Company_GJ": "Regional_Company",
        #         "parent_name": "Incorporated_Company",
        #         "Entity_Name_GJ": "Entity_Name",
        #         "Format_1_GJ": "Format_1",
        #         "Format_2_GJ": "Format_2",
        #         "Investment_GJ": "Investment",
        #     }
        # )
        # df_basic["Version"] = "WorkVersion"
        # 设置更新列
        # updatecol = list(set(df_basic.columns.drop(["Year", "Entity_Number"])))

        # 保存目标数据
        # rdb_.insert_sql(
        #     self.target_main_table, df_basic, path=self.target_url, updatecol=updatecol
        # )
        # 保存2_Construction_Key 表
        cols = [
            "Year",
            "Scenario",
            "name",
            "Entity_Investment_GJ",
            "Entity_Name_GJ",
            "Project_Status",
            "ProjectKey_XMZB",
            "ProjectKey_TZXYQD",
            "XMKG_Actual",
            "XMKG_Forecast",
            "XMKG_DelayReason",
            "ZSY_Actual",
            "ZSY_Forecast",
            "ZSY_DelayReason",
            "JSSJ_Actual",
            "JSSJ_Forecast",
            "JSSJ_DelayReason",
            "ProjectKey_YDJYDQR",
            "ZSY_YN",
            "ZSY_Contract_Remarks",
            "TPKey_TZXYQD",
            "TPKey_XMKG",
            "TPKey_ZSY",
            "TPKey_JSSJ",
            "QSSGT_Actual",
            "QSSGT_Forecast",
            "QSSGT_DelayReason",
            "RZHTQS_Actual",
            "RZHTQS_Forecast",
            "RZHTQS_DelayReason",
            "LHSYX_Actual",
            "LHSYX_Forecast",
            "LHSYX_DelayReason",
            "ZSGM",
            "ETL_Audit_Status",
            "construction_type",
            "incremental_memory",
            "ProjectKey_JSSJ",
            "ProjectKey_ZSY",
            "ProjectKey_QSSGT",
            "ProjectKey_RZHTQS",
            "ProjectKey_LHSYX",
            "ProjectKey_XMKG",
        ]

        df_key = self.source_data[cols].rename(
            columns={
                "name": "Entity_Number",
                "Entity_Investment_GJ": "Entity_Construction",
                "Entity_Name_GJ": "Entity_Name",
                "ETL_Audit_Status": "Examine_Status",
            }
        )
        df_key["Version"] = "WorkVersion"
        updatecol = list(
            set(
                df_key.columns.drop(
                    ["Year", "Scenario", "Entity_Number", "Entity_Construction"]
                )
            )
        )

        '''
        datetime_cols = df_key.select_dtypes(include=['datetime64']).columns
        print(datetime_cols)


        for col in datetime_cols:
            # 先转为字符串避免后续问题
            # df_key[col] = df_key[col].dt.strftime('%Y-%m-%d %H:%M:%S')
            # df_key[col] = df_key[col].astype(str)

            df_key[col] = df_key[col].apply(
                lambda x: f"'{x.strftime('%Y-%m-%d %H:%M:%S')}'" if pd.notna(x) else pd.np.nan
            )
            # df_key[col] = pd.to_datetime(df_key[col])
        '''

        # 保存目标数据
        dt = DataTableMySQL('2_Construction_Key')

        dt.insert_df(df_key, updatecol=updatecol)

        # 暂时：调试注释
        # rdb_.insert_sql(
        #     self.target_table, df_key, path=self.target_url, updatecol=updatecol, auto_fit=False
        # )

        self.source_data["ETL_Datetime"] = datetime.datetime.now()

        # 去掉多余的字段并重命名字段
        if "ud2" in self.source_data.columns.to_list():
            del self.source_data["ud2"]
            del self.source_data["name"]
            del self.source_data["parent_name"]
        updatecol = list(
            set(
                self.source_data.columns.drop(
                    ["Year", "Scenario", "Entity_Investment_GJ"]
                )
            )
        )
        updatecol.append("ETL_Datetime")
        # 保存历史数据，有则更新，没有则加入
        rdb_.insert_sql(
            self.log_table, self.source_data, path=self.source_url, updatecol=updatecol
        )
        print("共同步【%s】条关键节点数据" % self.source_data.shape[0])


def main(p1, p2):
    kn = key_node()
    kn.get_key_data()


# debug
if __name__ == "__main__":
    from business._debug import para1,para2

    # p2 = {"Year": "2023", "Scenario": "Year,M1,M2", "Incorporated_Company": "Ntest0101"}
    main(para1, para2)
