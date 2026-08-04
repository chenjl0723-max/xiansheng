# -*- coding: utf-8 -*-
# @Time : 2023/8/22 15:17
# @Author : LiYuXin
# @FileName: external_data_to_bcp.py
# @Software: PyCharm

from deepfos.element.finmodel import FinancialCube
from deepfos.element.datatable import DataTableMySQL
from deepfos.element.dimension import Dimension
from deepfos.options import OPTION
from deepfos.element.variable import Variable
# from deepfos.lib.concurrency import ThreadCtxExecutor

import time
import pandas as pd
import traceback

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)
# from multiprocessing import Process
# import multiprocessing
# from multiprocessing import Pool
# from billiard import Pool


def get_data(p1, table, columes, where):
    # 获取sql表源数据
    # app_name_target = p1["app"]
    # p1["app"] = app_name_source
    data = DataTableMySQL(table)
    data_table = data.table
    if len(where) == 1:
        data_select = data.select(columes, where=(data_table.Version == where[0]))
    else:
        data_select = data.select(
            columes,
            where=(
                    (data_table.Scenario == where[0]) & (data_table.Version == where[1])
            ),
        )
    # p1["app"] = app_name_target
    return data_select


def get_parent(p1, df):
    # 匹配运营期项目，取维度父级节点编码
    # p1["app"] = "dzsicw002"
    entity_dim = Dimension("Entity")
    df_part = pd.DataFrame(df["Entity_Number"])
    df_part.drop_duplicates(inplace=True)
    entity_all = entity_dim.query(
        "Base(1,0)", fields=["name", "parent_name"], as_model=False
    )
    df_dim = pd.DataFrame(data=entity_all).loc[:, ["name", "parent_name"]]
    df_dim.rename(
        columns={"name": "Entity_Number", "parent_name": "Entity"}, inplace=True
    )
    df_entity = pd.merge(df_part, df_dim, how="left", on="Entity_Number")
    return df_entity


def print_log(df, wrong):
    # 打印日志
    n = df.shape[0]
    m = len(wrong)
    log = "本次经营计划数据推送成功%s条，运营期项目匹配失败%s条，请进行核对!" % (n, m)
    # print(df.info())
    print(log)
    print(wrong)
    if n == 0:
        print("由于本次经营计划可用数据为空，因此未对BCP表进行相关清理更新，请进行检查!")


def jyjh(p1, p2):
    # 调用budget_revenue_calc_batch,水价与收入计算
    from budget.Python.biz.water_revenue import budget_revenue_calc_batch as revenue
    try:
        revenue.main(p1, p2)
    except Exception as e:
        traceback.print_exc()


def get_operation_data(p1, p2, df):
    # 调用operation_plan,经营计划数据进入cube维度
    columns = [
        "Item",
        "Department",
        "Year",
        "Scenario",
        "Version",
        "Price_before_adjust",
        "Price_adjust",
        "ExceedPrice_before_adjust",
        "ExceedPrice_adjust",
        "Yield_before_adjust",
        "Yield_adjust",
        "Price_InitialDate",
        "Yield_InitialDate",
        "Price_increase",
        "Yield",
        "Yield_increase",
        "Price",
    ]
    df_operation = df[columns]
    from budget.Python.biz.water_revenue import operational_plan as op
    # operational_plan
    op.main(p1, p2, df_operation)
    print("operational_plan over")
    return


def main(p1, p2):
    begin = time.time()
    # 获取经营计划app编码
    from common.config import app_name_source

    app_name_target = p1["app"]
    # 更改p1参数获取经营计划里的数据
    p1["app"] = app_name_source
    OPTION.api.header = p1

    columns = [
        "Year",
        "Entity_Number",
        "Entity_Opreation",
        "Incorporated_Company",
        "Investment",
        "Scale_SJCL",
    ]
    full = get_data(p1, table="Basic_Data_Full", columes=columns, where=["WorkVersion"])
    columns = [
        "Year",
        "Entity_Number",
        "Entity_Opreation",
        "YN_TJJH",
        "ReasonType",
        "TJ_Type",
        "TJ_YN_XSJ",
        "InvestmentPrice",
        "LastAD_BD",
        "LastAD_CBD",
        "TJ_AfterAD_BD",
        "TJ_AfterAD_CBD",
        "TJ_BDSJ_Amount",
        "TJ_Time_Forecast",
        "TJ_Time_XJG",
        "TJ_Amount",
        "TJ_LastTaxAmount",
        "TJ_TodayTaxAmount",
        "Reason",
        "TJ_SJTJReasonSort",
        "TJ_TJXMSpecificReason",
        "TJ_CalculationProcess_BNSHZSE",
        "TJ_CalculationProcess_ZSYWNDSHZSE",
    ]
    tj = get_data(
        p1, table="3_Opreation_TJ", columes=columns, where=["Year", "WorkVersion"]
    )
    columns = [
        "Year",
        "Entity_Number",
        "Entity_Opreation",
        "Time_ZSY",
        "YN_TBDJH",
        "Reason",
        "TBD_Type",
        "TBD_YN_XBD",
        "LastAD",
        "TBD_AfterAD",
        "TBD_BDSL_Amount",
        "TBD_Time_Forecast",
        "TBD_Time_XSL",
        "TBD_Amount",
        "TBD_LastTaxAmount",
        "TBD_CurrentTaxAmount",
    ]
    tbd = get_data(
        p1, table="3_Opreation_TBD", columes=columns, where=["Year", "WorkVersion"]
    )

    # 按照业务模型的表联系拼接数据
    group = ["Year", "Entity_Number", "Entity_Opreation"]
    if not tj.empty or not tbd.empty:
        df_tj_tbd = pd.merge(tj, tbd, how="outer", on=group)
        df = pd.merge(full, df_tj_tbd, how="inner", on=group)
    else:
        df = pd.DataFrame()

    p1["app"] = app_name_target

    # 获取变量
    variable = Variable(element_name="Variable")
    year = variable.get_value("BudYear")
    # today = datetime.datetime.today()
    # year_now = today.year

    if not df.empty:
        # 只更新预算年份的数据
        df = df.loc[df["Year"] == str(year)]
        # 查询维度中父级节点
        df_entity = get_parent(p1, df=df)
        # 取出有缺失值的行,转为列表
        df_isnull = df_entity[df_entity.isnull().T.any()]
        wrong_entity_number = df_isnull["Entity_Number"].tolist()
        # 丢弃列中有缺失值的行
        df_entity.dropna(axis=0, subset=["Entity"], inplace=True)
        df = pd.merge(df, df_entity, how="inner", on="Entity_Number")
    else:
        wrong_entity_number = []

    if not df.empty:
        for i in [
            "Entity",
            "Entity_Number",
            "Year",
            "Incorporated_Company",
            "Investment",
            "YN_TJJH",
            "ReasonType",
            "TJ_Type",
            "TJ_YN_XSJ",
            "InvestmentPrice",
            "LastAD_BD",
            "LastAD_CBD",
            "TJ_AfterAD_BD",
            "TJ_AfterAD_CBD",
            "TJ_BDSJ_Amount",
            "TJ_Time_Forecast",
            "TJ_Time_XJG",
            "TJ_Amount",
            "TJ_LastTaxAmount",
            "TJ_TodayTaxAmount",
            "Reason_x",
            "TJ_SJTJReasonSort",
            "TJ_TJXMSpecificReason",
            "TJ_CalculationProcess_BNSHZSE",
            "TJ_CalculationProcess_ZSYWNDSHZSE",
            "Time_ZSY",
            "Scale_SJCL",
            "YN_TBDJH",
            "Reason_y",
            "TBD_Type",
            "TBD_YN_XBD",
            "LastAD",
            "TBD_AfterAD",
            "TBD_BDSL_Amount",
            "TBD_Time_Forecast",
            "TBD_Time_XSL",
            "TBD_Amount",
            "TBD_LastTaxAmount",
            "TBD_CurrentTaxAmount",
        ]:
            if i not in df.columns:
                df[i] = None
        # 更改df列名为目标表列名
        df.rename(
            columns={
                "Entity_Number": "Item",
                "Incorporated_Company": "Company",
                "YN_TJJH": "Price",
                "ReasonType": "UnadjustPrice_Reason",
                "TJ_Type": "Price_AdjustType",
                "TJ_YN_XSJ": "Price_TraceBack",
                "InvestmentPrice": "Review_Price",
                "LastAD_BD": "Price_before_adjust",
                "LastAD_CBD": "ExceedPrice_before_adjust",
                "TJ_AfterAD_BD": "Price_adjust",
                "TJ_AfterAD_CBD": "ExceedPrice_adjust",
                "TJ_BDSJ_Amount": "Price_increase",
                "TJ_Time_Forecast": "Price_FinishedDate",
                "TJ_Time_XJG": "Price_InitialDate",
                "TJ_Amount": "PriceIncome_increase",
                "TJ_LastTaxAmount": "PrePriceIncome_increase",
                "TJ_TodayTaxAmount": "BudPriceIncome_increase",
                "Reason_x": "UnadjustPrice_explain",
                "TJ_SJTJReasonSort": "Price_decrease_reason",
                "TJ_TJXMSpecificReason": "Price_decrease_explain",
                "TJ_CalculationProcess_BNSHZSE": "BudYieldIncome_calculate",
                "TJ_CalculationProcess_ZSYWNDSHZSE": "PreYieldIncome_calculate",
                "Time_ZSY": "Transittime",
                "Scale_SJCL": "Scale",
                "YN_TBDJH": "Yield",
                "Reason_y": "UnadjustYield_Reason",
                "TBD_Type": "Yield_AdjustType",
                "TBD_YN_XBD": "Yield_TraceBack",
                "LastAD": "Yield_before_adjust",
                "TBD_AfterAD": "Yield_adjust",
                "TBD_BDSL_Amount": "Yield_increase",
                "TBD_Time_Forecast": "Yield_FinishedDate",
                "TBD_Time_XSL": "Yield_InitialDate",
                "TBD_Amount": "YieldIncome_increase",
                "TBD_LastTaxAmount": "PreYieldIncome_increase",
                "TBD_CurrentTaxAmount": "BudYieldIncome_increase",
            },
            inplace=True,
        )
        # 补充固定值数据列
        df["Department"] = "Operation"
        df["Scenario"] = "Budget"
        df["Version"] = "Y1"
        df.drop(columns=["Entity_Opreation"], inplace=True)

    if not df.empty:
        # print(df.info())
        # 修改df中除了时间日期/浮点数之外的列数据格式为字符串
        type_list = df.columns.tolist()
        type_list.remove("Price_FinishedDate")
        type_list.remove("Price_InitialDate")
        type_list.remove("Transittime")
        type_list.remove("Yield_FinishedDate")
        type_list.remove("Yield_InitialDate")

        type_list.remove("Review_Price")
        type_list.remove("Price_before_adjust")
        type_list.remove("ExceedPrice_before_adjust")
        type_list.remove("Price_adjust")
        type_list.remove("ExceedPrice_adjust")
        type_list.remove("PrePriceIncome_increase")
        type_list.remove("BudPriceIncome_increase")
        type_list.remove("PreYieldIncome_increase")
        type_list.remove("BudYieldIncome_increase")

        df[type_list] = df[type_list].astype(str)
        df[type_list] = df[type_list].applymap(
            lambda x: None if ((x == "nan") | (x == "None")) else x
        )
        #
        # # 只更新预算年份的数据
        # df_insert = df.loc[df["Year"] == str(year)]
        # 如果数据为空不进行更新
        if not df.empty:
            # 目标表清数
            bcp = DataTableMySQL("BCP")
            t = bcp.table
            # df['where'] = "Year = " + df["Year"] + " and Item = " + df["Item"]
            # bcp.update_from_dataframe(df, chucksize=None)
            # 清数bcp表
            bcp.delete(where=(t.Year == str(year)))

            # 清数cube
            cube = FinancialCube('WS_cube', path='/01_Cube')
            fix_del = "Account{YW0105;YW0108;YW0107;YW0106;PL01010102;YW0109;PL01010101}->" \
                      "Year{%s}->Scenario{Budget}->Measure{Expenses}->" \
                      "Period{1;2;3;4;5;6;7;8;9;10;11;12;Noperiod}->Entity{AndFilter(Base(1,0),Attr(ud10,'P02'))}->" \
                      "Version{Y1}->Material{Nomaterial}->Department{Operation}->Allocation{Original}->Tax{Tax;Notax}->" \
                      "Misc1{Nomisc1}->Misc2{Nomisc2}" \
                      % year
            d = cube.delete(fix_del)

            # 插入数据
            bcp.insert_df(df)

    # 输出信息
    print_log(df=df, wrong=wrong_entity_number)
    print(
        "*******************************************************************************"
    )

    if not df.empty:
        # 存数入cube
        get_operation_data(p1, p2, df)

        # 构建批量entity的p2参数
        list_entity = list(set(df["Item"].tolist()))
        entity = ";".join(list_entity)
        p2 = {
            "Year": year,
            "Entity": entity,
            "Version": "Y1",
            "Material": "Nomaterial",
            "Scenario": "Budget",
            "Allocation": "Original",
            "Tax": "Tax",
            "Department": "Operation",
            "Misc1": "Nomisc1",
            "Misc2": "Nomisc2",
            "sheetName": "",
            "sheetId": "",
            "elementName": "",
            "folderId": "",
        }
        # 运行水价与收入计算
        jyjh(p1, p2)
    times = time.time() - begin
    print("all time = ")
    print(times)

    return


if __name__ == "__main__":
    from common._debug import para1

    p2 = {}
    main(para1, p2)


