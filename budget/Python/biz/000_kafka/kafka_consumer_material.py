"""
added by wlm
added in 20230808
added for kafka同步主数据统一入口
主要逻辑：
    通过传入topic获取相应数，并写入到相应的中间表中
剩余问题：
"""
from common.setting import *
from common.commons import *


from kafka import KafkaConsumer
import time
import datetime
import pandas as pd
import json
import traceback


class kafka_():
    """
    调用kafka接口，获取数据
    """

    def __init__(self):
        self.topic = "mdms-ypyj"
        self.group_id = kafka_setting_budget_uat["group_id_ws"]
        self.servers = kafka_setting_budget_uat["bootstrap_servers"]

    def get_kafka_data(self):
        c = KafkaConsumer(
            self.topic,
            group_id=self.group_id,
            bootstrap_servers=self.servers,
            consumer_timeout_ms=10000,
            api_version=(1, 3, 5),
        )
        try:
            for message in c:
                if message is None:
                    break

                print("Received message: {}".format(message.value.decode("utf-8")))
                str_json = json.loads(message.value.decode())
                if "data_json" in str_json or "metaData" in str_json:
                    str_json = str_json["data_json"]
                elif "data" in str_json:
                    str_json = str_json["data"]
                # 判断返回值类型，将数据存入到DataFrame里
                if type(str_json) == list:
                    df_data = pd.DataFrame(str_json)
                else:
                    if type(str_json) == dict:
                        # 特殊情况，这个字段值是true，报错
                        if "mdmsendstatus" in str_json:
                            del str_json["mdmsendstatus"]
                        df_data = pd.DataFrame(str_json, index=[0])
                    else:
                        df_data = pd.DataFrame(json.loads(str_json), index=[0])
                # print("共获取到数据条数为："+df_data.shape[0])

                if message.topic in ["mdms-ypyj", "mdms-ypyj-all"]:
                    """
                    增量同步药品药剂信息
                    """
                    self.save_ypyj_data(df_data)

                else:
                    continue

                time.sleep(3)
            print("topic:%s与kafka建立连接，并消费数据" % self.topic)
            # sys.exit()
        except Exception:
            traceback.print_exc()
        finally:
            c.close()

    # def save_org_data(self, df):
    #     """
    #     保存kafka接口获取到的组织架构数据
    #     """
    #     # 过滤数据 取ISVALID = “2” 并且 fathercode！=“890006”
    #     df = df[(df["ISVALID"] == "2") & (df["FATHERCODE"] != "890006")]
    #
    #     col = ["CODE", "NAME", "PK_ORG", "FATHERCODE", "FATHERNAME"]
    #     df_org = df[col]
    #     df_org["Data_push_Time"] = datetime.datetime.now()
    #
    #     # 保存ORG主数据信息
    #     updatecol = list(set(df_org.columns.drop(["CODE", "FATHERCODE", "PK_ORG"])))
    #     rdb_.insert_sql(
    #         tbl="org_inc",
    #         data=df_org,
    #         path="/Datatable/Middle_Table/2023/",
    #         updatecol=updatecol,
    #     )
    #     print("【%s】同步组织架构【%s】条" % (datetime.datetime.now(), df_org.shape[0]))
    #
    # def save_build_data(self, df, pro_type):
    #     """
    #     保存建设期计划
    #     """
    #     # 获取pro_status_code=“商运”，operate_period=“运营期”数据
    #     # 这个条件去掉了：20230817 & (df["operate_period"] == "运营期")
    #     df = df[
    #         (df["pro_status_name"] == "商运")
    #         & (~pd.isnull(df["operate_waterworks_code"]))
    #     ]
    #     col = [
    #         "pro_name",
    #         "pro_code",
    #         "operate_waterworks_code",
    #         "operate_waterworks_name",
    #         "pro_company_id",
    #     ]
    #     df_build = df[col]
    #
    #     df_build["Data_push_Time"] = datetime.datetime.now()
    #     df_build["Status"] = "0"
    #     updatecol = list(
    #         set(
    #             df_build.columns.drop(
    #                 ["pro_code", "operate_waterworks_code", "pro_company_id"]
    #             )
    #         )
    #     )
    #     rdb_.insert_sql(
    #         tbl="build_business",
    #         data=df_build,
    #         path="/Datatable/Middle_Table/2023/",
    #         updatecol=updatecol,
    #     )
    #     msg = "同步运营期项目"
    #     print("【%s】%s【%s】条" % (datetime.datetime.now(), msg, df_build.shape[0]))

    def save_ypyj_data(self, df):
        """
        增量同步药品药剂信息到中间表
        """
        # 这块配合kafka进行调整，他会同步两个报文，有一个么有desc14 ，这个报文不处理
        if (
            "desc14" not in df.columns.to_list()
            or "freezeflag" not in df.columns.tolist()
        ):
            print("这个报文不处理")
            return
        # 新增逻辑，去掉单位为g的数据
        # 编码  名称  名称  小数  单位描述
        # CD001	kg	千克	 4	kg,千克
        # CD002	g	克	1	g,克
        # CD003	m3	立方米	2	m3,立方米
        # CD004	ml	毫升	1	ml,毫升
        # CD005	pc	个	0	pc,个
        # CD006	tai	台	0	tai,台
        df_cd = df[df["desc17"] == "CD002"]
        df = df[(df["desc17"] != "CD002") & (df["freezeflag"] == "0")]
        # print("单位为g的数量为："+df_cd.shape[0]+"          单位不为g的数量为"+df.shape[0])
        del df_cd
        # 物料编码  物料名称  功能/用途  剂型  主要有效成分  含量  基本计量单位
        df = df[["code", "desc7", "desc14", "desc11", "desc12", "desc13", "desc17"]]
        # 插入更新时间
        df["Data_push_Time"] = datetime.datetime.now()
        df["status"] = "0"

        # 插入更新 暂时注释，测试时放开
        updatecol = list(set(df.columns.drop(["code"])))
        rdb_.insert_sql(
            tbl="bewg_material_data",
            data=df,
            path="/05_Datatable/5_2_Middle_Table",
            updatecol=updatecol,
        )
        print("【%s】同步药品药剂【%s】条" % (datetime.datetime.now(), df.shape[0]))

    # def save_user_info(self, df):
    #     """
    #     增量同步人员主数据信息
    #     """
    #     col = [
    #         "PK_PSNDOC",
    #         "CODE",
    #         "USER_CODE",
    #         "NAME",
    #         "SEX",
    #         "ID",
    #         "MOBILE",
    #         "EMAIL",
    #         "POSTSTAT",
    #         "ISVALID",
    #         "PK_ORG",
    #     ]
    #     df = df[col]
    #     df["etl_date"] = datetime.datetime.now()
    #     df["etl_status"] = "0"
    #     # 插入更新
    #     updatecol = list(set(df.columns.drop(["PK_PSNDOC"])))
    #     rdb_.insert_sql(
    #         tbl="sys_mdm_user",
    #         data=df,
    #         path="/Datatable/Master_Data/",
    #         updatecol=updatecol,
    #     )
    #     print("【%s】同步人员信息【%s】条" % (datetime.datetime.now(), df.shape[0]))


def main(p1,p2):
    """
    调用kafka接口，获取数据
    """
    receiver = kafka_()
    receiver.get_kafka_data()


if __name__ == "__main__":
    from common._debug import para1, para2
    main(para1, para2)