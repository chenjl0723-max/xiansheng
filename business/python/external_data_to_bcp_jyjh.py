# -*- coding: utf-8 -*-
# @Time : 2023/9/19 15:17
# @Author : LiYuXin
# @FileName: external_data_to_bcp_jyjh.py
# @Software: PyCharm0
import copy

from deepfos.element.finmodel import FinancialCube
from deepfos.element.datatable import DataTableMySQL
from deepfos.element.dimension import Dimension
from deepfos.options import OPTION
from deepfos.element.variable import Variable

import time
import datetime
import pandas as pd
import numpy as np
import traceback

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)


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
    print(data_select)
    return data_select


def get_parent(p1, df):
    # 匹配运营期项目，取维度父级节点编码
    # p1["app"] = "dzsicw002"
    entity_dim = Dimension("Entity")
    df_part = pd.DataFrame(df["Entity_Number"])
    df_part.drop_duplicates(inplace=True)
    entity_all = entity_dim.query(
        "Base(#root,0)", fields=["name", "parent_name"], as_model=False
    )
    df_dim = pd.DataFrame(data=entity_all).loc[:, ["name", "parent_name"]]
    df_dim.rename(
        columns={"name": "Entity_Number", "parent_name": "Entity"}, inplace=True
    )
    df_entity = pd.merge(df_part, df_dim, how="left", on="Entity_Number")

    print('2', df_entity)
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


def get_operation_data(p1, p2, df):
    # step0 获取数据
    # step1 计算逻辑
    def cacl_operation(dt_oper):
        # 复制一个原表出来，后边保存cube用
        dt_oper_copy = dt_oper.copy()
        # 计算日期的月份及日期
        dt_oper["Price_InitialDate"] = pd.to_datetime(dt_oper["Price_InitialDate"])

        Price_InitialDate_year = dt_oper["Price_InitialDate"].dt.year
        Price_InitialDate_month = dt_oper['Price_InitialDate'].dt.month
        Price_InitialDate_day = dt_oper['Price_InitialDate'].dt.day

        dt_oper["Yield_InitialDate"] = pd.to_datetime(dt_oper["Yield_InitialDate"])

        Yield_InitialDate_year = dt_oper["Yield_InitialDate"].dt.year
        Yield_InitialDate_month = dt_oper['Yield_InitialDate'].dt.month
        Yield_InitialDate_day = dt_oper['Yield_InitialDate'].dt.day
        # 将计算的月份日期添加到DataFrame中
        dt_oper['Price_InitialDate_month'] = Price_InitialDate_month
        dt_oper['Price_InitialDate_day'] = Price_InitialDate_day
        dt_oper['Yield_InitialDate_month'] = Yield_InitialDate_month
        dt_oper['Yield_InitialDate_day'] = Yield_InitialDate_day
        dt_oper["Price_InitialDate_year"] = Price_InitialDate_year
        dt_oper["Yield_InitialDate_year"] = Yield_InitialDate_year

        dt_oper.loc[dt_oper["Price_InitialDate_year"].isna(), "Price_InitialDate_year"] = dt_oper["Year"]
        dt_oper.loc[dt_oper["Yield_InitialDate_year"].isna(), "Yield_InitialDate_year"] = dt_oper["Year"]

        dt_oper['Price_InitialDate_month'] = dt_oper['Price_InitialDate_month'].astype("int", errors="ignore")
        dt_oper['Price_InitialDate_day'] = dt_oper['Price_InitialDate_day'].astype("int", errors="ignore")
        dt_oper['Yield_InitialDate_month'] = dt_oper['Yield_InitialDate_month'].astype("int", errors="ignore")
        dt_oper['Yield_InitialDate_day'] = dt_oper['Yield_InitialDate_day'].astype("int", errors="ignore")
        dt_oper["Price_InitialDate_year"] = dt_oper["Price_InitialDate_year"].astype("int", errors="ignore")
        dt_oper["Yield_InitialDate_year"] = dt_oper["Yield_InitialDate_year"].astype("int", errors="ignore")
        dt_oper["Year"] = dt_oper["Year"].astype("int", errors="ignore")

        # # dt_oper = dt_oper.fillna(0)
        # dt_oper["Price_InitialDate_year"] = dt_oper["Price_InitialDate_year"].astype(int).astype(str)
        # dt_oper["Yield_InitialDate_year"] = dt_oper["Yield_InitialDate_year"].astype(int).astype(str)
        # 根据日期计算；小于等于15号：当前月份到12月取Price_adjust ；大于15号当前月份+1 到12月份取Price_adjust

        # 判断月份
        dt_oper.loc[(dt_oper['Price_InitialDate_day'] <= 15) & (
                dt_oper["Price_InitialDate_year"].astype(int) == dt_oper["Year"].astype(int)), 'initial_month'] = \
            dt_oper[
                'Price_InitialDate_month']
        dt_oper.loc[(dt_oper['Price_InitialDate_day'] > 15) & (
                dt_oper["Price_InitialDate_year"].astype(int) == dt_oper["Year"].astype(int)), 'initial_month'] = \
            dt_oper[
                'Price_InitialDate_month'] + 1
        dt_oper.loc[(dt_oper['Yield_InitialDate_day'] <= 15) & (
                dt_oper["Yield_InitialDate_year"] == dt_oper["Year"]), 'yield_month'] = dt_oper[
            'Yield_InitialDate_month']
        dt_oper.loc[(dt_oper['Yield_InitialDate_day'] > 15) & (
                dt_oper["Yield_InitialDate_year"] == dt_oper["Year"]), 'yield_month'] = dt_oper[
                                                                                            'Yield_InitialDate_month'] + 1
        dt_oper['key'] = 1
        # 与月份关联
        dt_month = pd.DataFrame(data={'month': [i for i in range(1, 13)], 'key': 1})
        dt_oper = pd.merge(left=dt_oper, right=dt_month, how='left', on='key')
        # 判断月份计算值
        dt_oper['YW0105'] = dt_oper['Price_adjust']
        dt_oper.loc[
            (dt_oper['month'] < dt_oper['initial_month']), 'YW0105'] = dt_oper['Price_before_adjust']

        dt_oper['YW0108'] = dt_oper['ExceedPrice_adjust']
        dt_oper.loc[
            (dt_oper['month'] < dt_oper['initial_month']), 'YW0108'] = dt_oper['ExceedPrice_before_adjust']

        dt_oper['YW0107'] = dt_oper['Yield_adjust']
        dt_oper.loc[(dt_oper['month'] < dt_oper['yield_month']), 'YW0107'] = \
            dt_oper['Yield_before_adjust']

        # 判断水价调整年份，大于POV年份取before，否则取ExceedPrice_adjust
        # 判断水价调整年份，大于POV年份取before，否则取ExceedPrice_adjust
        dt_oper.loc[(dt_oper["Price_InitialDate_year"].astype(int) > dt_oper["Year"].astype(int)) | (
            pd.isnull(dt_oper['Price_InitialDate_day'])), "YW0105"] = dt_oper[
            'Price_before_adjust']
        dt_oper.loc[dt_oper["Price_InitialDate_year"] < dt_oper["Year"], "YW0105"] = dt_oper[
            'Price_adjust']

        dt_oper.loc[(dt_oper["Price_InitialDate_year"] > dt_oper["Year"]) | (
            pd.isnull(dt_oper['Price_InitialDate_day'])), "YW0108"] = dt_oper[
            'ExceedPrice_before_adjust']
        dt_oper.loc[dt_oper["Price_InitialDate_year"] < dt_oper["Year"], "YW0108"] = dt_oper[
            'ExceedPrice_adjust']

        # 判断保底水量调整年份，大于POV年份，则取before 否则取Yield_adjust
        dt_oper.loc[(dt_oper["Yield_InitialDate_year"] > dt_oper["Year"]) | (
            dt_oper['Yield_InitialDate_day'].isna()), "YW0107"] = dt_oper[
            'Yield_before_adjust']
        dt_oper.loc[dt_oper["Yield_InitialDate_year"] < dt_oper["Year"], "YW0107"] = dt_oper[
            'Yield_adjust']

        columns = ['Item', 'Department', 'Year', 'Scenario', 'Version', 'month', 'YW0105', 'YW0108', 'YW0107']
        dt_oper = dt_oper[columns].rename(columns={'Item': 'Entity', 'month': 'Period'})
        # 新增需求，将取出的字段保存到Cube的科目中
        dt_oper_copy = dt_oper_copy.rename(
            columns={'Price': 'YW0601', 'Price_before_adjust': 'YW0602', 'Price_adjust': 'YW0603',
                     'Price_increase': 'YW0604',
                     'Price_InitialDate': 'YW0605', 'Yield': 'YW0606', 'Yield_before_adjust': 'YW0607',
                     'Yield_adjust': 'YW0608',
                     'Yield_increase': 'YW0609', 'Yield_InitialDate': 'YW0610'})
        columns = ['Item', 'Department', 'Year', 'Scenario', 'Version', 'YW0601', 'YW0602', 'YW0603', 'YW0604',
                   'YW0605', 'YW0606',
                   'YW0607', 'YW0608', 'YW0609', 'YW0610']
        dt_oper_copy = dt_oper_copy[columns].rename(columns={'Item': 'Entity'})

        return dt_oper, dt_oper_copy

    # step1 数据进入cube
    def save_operation(dt_oper, pov, del_fix):
        if dt_oper.size > 0:
            # 先清数
            cube = FinancialCube('WS_cube', path='/01_Cube/')
            cube.delete(del_fix)
            # 保存数据
            response = cube.save_unpivot(dt_oper, pov=pov, unpivot_dim='Account')
            return response

    def op(p1, p2, dt_oper=pd.DataFrame()):
        # 获取经营计划中的数据
        # dt_oper = get_operation_data(tbl= tab_name, columns=columns, path=path, param=p2)
        if dt_oper.size > 0:
            # 获取计算后的数据，dt_oper为第一次保存数据；dt_oper_copy为第二次新增保存数据
            dt_oper, dt_oper_copy = cacl_operation(dt_oper)
            # 拼接要删除的
            list_entity = list(set(dt_oper['Entity'].tolist()))
            list_entity = ';'.join(list_entity)
            list_year = list(set(dt_oper['Year'].tolist()))

            pov = {'Measure': 'Expenses', 'Material': 'Nomaterial', 'Allocation': 'Original', 'Tax': 'Tax',
                   'Misc1': 'Nomisc1',
                   'Misc2': 'Nomisc2'}
            pov_copy = {'Period': 'TotalPeriod', 'Measure': 'Revenue', 'Material': 'Nomaterial',
                        'Allocation': 'Original',
                        'Tax': 'Default',
                        'Misc1': 'Nomisc1',
                        'Misc2': 'Nomisc2'}
            del_fix = copy.deepcopy(pov)
            del_fix['Department'] = "Operation"
            del_fix['Scenario'] = "Budget"
            del_fix['Version'] = 'Y1'
            del_fix['Account'] = 'YW0105;YW0108;YW0107'
            del_fix['Period'] = '1;2;3;4;5;6;7;8;9;10;11;12'

            del_fix_copy = del_fix.copy()
            del_fix_copy['Account'] = 'YW0601;YW0602;YW0603;YW0604;YW0605;YW0606;YW0607;YW0608;YW0609;YW0610'
            del_fix_copy['Period'] = 'TotalPeriod'
            del_fix_copy['Measure'] = 'Revenue'
            del_fix_copy['Tax'] = 'Default'
            dt_oper_copy["YW0605"] = dt_oper_copy.YW0605.astype(str).where(dt_oper_copy.YW0605.notnull(), None)
            dt_oper_copy["YW0610"] = dt_oper_copy.YW0610.astype(str).where(dt_oper_copy.YW0610.notnull(), None)

            def func(item):
                if item == "1":
                    return "是"
                elif item == "2":
                    return "否"

            dt_oper_copy['YW0601'] = dt_oper_copy['YW0601'].apply(func)
            dt_oper_copy['YW0606'] = dt_oper_copy['YW0606'].apply(func)

            for i in list_year:
                # year = list_year[i]
                entity = list(set(dt_oper[dt_oper['Year'] == i]['Entity'].to_list()))
                entity = ';'.join(entity)
                year = str(i)

                del_fix["Year"] = year
                del_fix["Entity"] = entity
                response = save_operation(dt_oper, pov, del_fix)

                del_fix_copy["Year"] = year
                del_fix_copy["Entity"] = entity
                response_copy = save_operation(dt_oper_copy, pov_copy, del_fix_copy)

                print(response, response_copy)

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
    # operational_plan
    op(p1, p2, df_operation)
    print("operational_plan over")
    return


def revenue_full(p1, p2):
    # from python.conf.config import app_name_target
    # p1["app"] = app_name_target
    # OPTION.api.header = p1
    # print('p1',p1)
    # from python.biz.water_revenue.budget_revenue_calc_batch import main as revenue
    # revenue(p1, p2)
    import python.bp.interface.budget_revenue_calc_batch_copy as revenue

    # from python.bp.interface.budget_revenue_calc_batch import main as revenue
    print('p1', p1)
    print('p2', p2)
    revenue.main(p1, p2)


def main(p1, p2):
    begin = time.time()
    # 获取业务预算app编码
    from business.conf.config import app_name_target
    # 保存经营计划app编码
    app_name_source = p1["app"]

    # OPTION.api.header = p1

    columns = [
        "Year",
        "Entity_Number",
        "Entity_Opreation",
        "Incorporated_Company",
        "Investment",
        "Scale_SJCL",
        "LastAD_BD",
        "LastAD_CBD",
        "TJ_AfterAD_BD",
        "TJ_AfterAD_CBD",
        "TJ_Time_XJG",
        "TJ_Type",
        "LastAD",
        "TBD_AfterAD",
        "TBD_Time_XSL",
    ]
    full = get_data(p1, table="Basic_Data_Full", columes=columns, where=["WorkVersion"])

    # print(full)
    columns = [
        "Year",
        "Entity_Number",
        "Entity_Opreation",
        "YN_TJJH",
        "ReasonType",
        # "TJ_Type",
        "TJ_YN_XSJ",
        "InvestmentPrice",
        # "LastAD_BD",
        # "LastAD_CBD",
        # "TJ_AfterAD_BD",
        # "TJ_AfterAD_CBD",
        "TJ_BDSJ_Amount",
        "TJ_Time_Forecast",
        # "TJ_Time_XJG",
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
        # "LastAD",
        # "TBD_AfterAD",
        "TBD_BDSL_Amount",
        "TBD_Time_Forecast",
        # "TBD_Time_XSL",
        "TBD_Amount",
        "TBD_LastTaxAmount",
        "TBD_CurrentTaxAmount",
    ]
    tbd = get_data(
        p1, table="3_Opreation_TBD", columes=columns, where=["Year", "WorkVersion"]
    )
    # print('df001',tbd.query("Entity_Number == 'Y3720231346'"))

    # 按照业务模型的表联系拼接数据
    group = ["Year", "Entity_Number", "Entity_Opreation"]
    if not tj.empty or not tbd.empty:
        df_tj_tbd = pd.merge(tj, tbd, how="outer", on=group)
        # print('df01',df_tj_tbd.query("Entity_Number == 'Y3720231346'"))
        df = pd.merge(full, df_tj_tbd, how="inner", on=group)
        # print('df02',df.query("Entity_Number == 'Y3720231346'"))
    else:
        df = pd.DataFrame()

    # 切换为业务预算
    p1["app"] = app_name_target
    OPTION.api.header = p1

    # 获取变量
    variable = Variable(element_name="Variable")
    year = variable.get_value("BudYear")
    year = '2026'
    # today = datetime.datetime.today()
    # year_now = today.year
    # print('df1',df.query("Entity_Number == 'Y3720231346'"))
    print('1,', df)
    if not df.empty:

        # 只更新预算年份的数据
        df = df.loc[df["Year"] == str(year)]
        print('2', df)

        # 查询维度中父级节点
        df_entity = get_parent(p1, df=df)
        # 取出有缺失值的行,转为列表
        df_isnull = df_entity[df_entity.isnull().T.any()]
        wrong_entity_number = df_isnull["Entity_Number"].tolist()
        # 丢弃列中有缺失值的行
        df_entity.dropna(axis=0, subset=["Entity"], inplace=True)
        df = pd.merge(df, df_entity, how="inner", on="Entity_Number")
        # print('df2',df)
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
        # 生成当前系统时间并赋值给dt字段
        current_system_time = pd.Timestamp.now()
        df['dt'] = current_system_time

    # 处理数据类型并写入BCP表
    if not df.empty:
        # -------------------------- 类型处理调整开始 --------------------------
        # 1. 日期时间字段统一转换为Timestamp类型
        datetime_fields = [
            "Price_FinishedDate", "Price_InitialDate", "Transittime",
            "Yield_FinishedDate", "Yield_InitialDate", "dt"
        ]
        for col in datetime_fields:
            if col in df.columns:
                # 字符串转Timestamp，无效值设为NaT
                df[col] = pd.to_datetime(
                    df[col],
                    errors="coerce",
                    format="%Y-%m-%d"  # 按实际日期格式调整，含时间则用"%Y-%m-%d %H:%M:%S"
                )

        # 2. 数值字段转换为数值类型
        numeric_fields = [
            "Review_Price", "Price_before_adjust", "ExceedPrice_before_adjust",
            "Price_adjust", "ExceedPrice_adjust", "PrePriceIncome_increase",
            "BudPriceIncome_increase", "PreYieldIncome_increase", "BudYieldIncome_increase"
        ]
        for col in numeric_fields:
            if col in df.columns:
                # 清除非数字字符，转为数值类型
                df[col] = df[col].astype(str).str.replace(r"[^\d.-]", "", regex=True)
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # 3. 剩余字段处理为字符串（排除已处理的日期和数值字段）
        type_list = df.columns.tolist()
        # 移除日期字段
        for col in datetime_fields:
            if col in type_list:
                type_list.remove(col)
        # 移除数值字段
        for col in numeric_fields:
            if col in type_list:
                type_list.remove(col)
        # 转换为字符串并处理空值
        df[type_list] = df[type_list].astype(str)
        df[type_list] = df[type_list].applymap(
            lambda x: None if ((x == "nan") | (x == "None")) else x
        )
        # -------------------------- 类型处理调整结束 --------------------------
        #######################原类型处理代码######################################
        # if not df.empty:
        #     # print(df.info())
        #     # 修改df中除了时间日期/浮点数之外的列数据格式为字符串
        #     type_list = df.columns.tolist()
        #     type_list.remove("Price_FinishedDate")
        #     type_list.remove("Price_InitialDate")
        #     type_list.remove("Transittime")
        #     type_list.remove("Yield_FinishedDate")
        #     type_list.remove("Yield_InitialDate")

        #     type_list.remove("Review_Price")
        #     type_list.remove("Price_before_adjust")
        #     type_list.remove("ExceedPrice_before_adjust")
        #     type_list.remove("Price_adjust")
        #     type_list.remove("ExceedPrice_adjust")
        #     type_list.remove("PrePriceIncome_increase")
        #     type_list.remove("BudPriceIncome_increase")
        #     type_list.remove("PreYieldIncome_increase")
        #     type_list.remove("BudYieldIncome_increase")

        #     df[type_list] = df[type_list].astype(str)
        #     df[type_list] = df[type_list].applymap(
        #         lambda x: None if ((x == "nan") | (x == "None")) else x
        #     )
        #################################################################

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
            cube = FinancialCube('WS_cube', path='/01_Cube/')
            fix_del = "Account{YW0105;YW0108;YW0107;YW0106;PL01010102;YW0109;PL01010101}->" \
                      "Year{%s}->Scenario{Budget}->Measure{Expenses}->" \
                      "Period{1;2;3;4;5;6;7;8;9;10;11;12;Noperiod}->Entity{AndFilter(Base(1,0),Attr(ud10,'P02'))}->" \
                      "Version{Y1}->Material{Nomaterial}->Department{Operation}->Allocation{Original}->Tax{Tax;Notax}->" \
                      "Misc1{Nomisc1}->Misc2{Nomisc2}" \
                      % year
            d = cube.delete(fix_del)
            # print("df4",df)
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
        revenue_full(p1, p2)

    times = time.time() - begin
    print("all time = ")
    print(times)

    return


if __name__ == "__main__":
    try:
        from business.__debug import para1, para2
    except ImportError:
        para1 = para2 = {}
    main(para1, para2)
