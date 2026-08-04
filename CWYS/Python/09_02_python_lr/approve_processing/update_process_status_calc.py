# -*- coding: utf-8 -*-
"""
@file    : update_process_status_calc.py
@Time    :
@Author  : chen
@Software: PyCharm
@Desc    : 北控水务 审批流程状态表修改 涉及审批记录表和cube 两个权限
"""

import pandas as pd
import datetime
import traceback
import requests
import json
from deepfos.db.clickhouse import ClickHouseClient
from deepfos.db.mysql import MySQLClient
from deepfos.element.dimension import Dimension, DimMember
from deepfos.element.datatable import *
from deepfos.api.models.datatable_mysql import DatatableDataUpdateDTO
from deepfos.api.space import SpaceAPI
from budget.Python.conf import Config_File as cf


def get_user(p1, p2):
    api = SpaceAPI()
    user = api.user.query(userId=p1['user'], status='ENABLE').nickName
    return user


def fun_query_mysql(where, table_nm, path_table):
    # mysql 实例化
    client = ClickHouseClient()
    # mysql查询
    sql_01 = "select * from ${%s} %s" % (table_nm, where)
    df_table = client.query_dfs(sqls=sql_01,
                                table_info={table_nm: {'elementName': table_nm,
                                                       'elementType': 'DataTableMySQL',
                                                       'path': path_table}})
    return df_table


def fun_query_dimension(dimension, expression, fields):
    # 维度 实例化
    dim = Dimension(dimension)
    # 查询维度现有成员
    df = pd.DataFrame(dim.query(expression=expression, fields=fields, as_model=False))
    df = df.rename(columns={'description_zh_cn': 'language_zh-cn'})
    del df['id']
    df = df.where(df.notnull(), None)
    return df


# 更新clickhouse的方法
def update_ck(table: DataTableMySQL, set_map: dict, where: dict):
    where_list = {}
    for k, v in where.items():
        if not isinstance(v, list):
            v = [v]
        where_list[k] = v
    payload = DatatableDataUpdateDTO(
        setList=set_map,
        elementName=table.element_name,
        folderId=table.element_info.folderId,
        whereList=where_list
    )
    return table.api.dml.update_data(payload)


def update_mysql(client, element_name, path, df_status, result_status, original_status, user,
                 status_column='result_status'):
    """
    封装 MySQL 更新逻辑，按 form_data 中的 entity_id 和 department_id 配对更新状态
    :param client: MySQLClient 实例
    :param element_name: 表名
    :param path: 表路径
    :param df_status: form_data 转换的 DataFrame
    :param result_status: 目标状态
    :param original_status: 原始状态（逗号分隔的字符串）
    :param user: 操作用户
    :param status_column: 状态字段名，默认为 'result_status'
    :return: 更新结果
    """
    sqls = []
    for _, row in df_status.iterrows():
        entity_id_single = row['entity_id']
        version_id_single = row['version_id']
        year_id_single = row['year_id']

        # 获取该子水厂的所有子集
        expression = f'IBase({entity_id_single},1)'
        df_entity_subset = fun_query_dimension('Entity_GL', expression, ['name'])
        entity_ids = df_entity_subset['name'].to_list() if not df_entity_subset.empty else [entity_id_single]
        # 将 entity_ids 转换为逗号分隔的字符串，用于拼接sql
        entity_ids_str = "','".join(entity_ids)

        if element_name == 'Approval_Progress_Record':
            sql = (
                f"update ${{{element_name}}} set {status_column} = '{result_status}', operate_user = '{user}', "
                f"operate_time = '{datetime.datetime.now()}' where entity_id IN ('{entity_ids_str}') "
                f"and version_id = '{version_id_single}' and {status_column} in ('{original_status}') "
                f"and year_id = '{year_id_single}'"
            )
        # elif element_name == 'profile':
        #     if department_id_single == 'Equipment':
        #
        #         sql = (
        #             f"update ${{equipment_profile_NJ}} set {status_column} = '{result_status}' where entity in ('{entity_ids_str}') "
        #             f"and department = '{department_id_single}' "
        #             f"and year = '{year_id_single}'"
        #         )
        #     elif department_id_single == 'Technical':
        #         sql = (
        #             f"update ${{equipment_profile_JG}} set {status_column} = '{result_status}'"
        #             f"where entity IN ('{entity_ids_str}') and department = '{department_id_single}'  "
        #             f"and year = '{year_id_single}'"
        #         )
        #     else:
        #         sql = ''
        # elif element_name == 'BCP':
        #     sql = (
        #         f"update ${{{element_name}}} set {status_column} = '{result_status}'"
        #         f"where Entity IN ('{entity_ids_str}') and Department = '{department_id_single}' and {status_column} in ('{original_status}')"
        #         f"and Year = '{year_id_single}'"
        #     )
        # elif element_name == 'Opreation_JG':
        #     if result_status == 'Status08':
        #         sql = (
        #             f"update ${{{element_name}}} set {status_column} = '{result_status}', Is_Approve = '9' "
        #             f"where Entity_Opreation IN ('{entity_ids_str}') and Department = '{department_id_single}' and {status_column} in ('{original_status}')"
        #             f"and Year = '{year_id_single}'"
        #         )
        #     else:
        #         sql = (
        #             f"update ${{{element_name}}} set {status_column} = '{result_status}' "
        #             f"where Entity_Opreation IN ('{entity_ids_str}') and Department = '{department_id_single}' and {status_column} in ('{original_status}')"
        #             f"and Year = '{year_id_single}'"
        #         )
        elif element_name == 'datatable_block_control_sub_profit_cube':
            sql = (
                f"select datablock_seg_1_value ,datablock_id  from ${{{element_name}}} "
                f"where datablock_seg_1_value in ('{entity_ids_str}') "
            )


        sqls.append(sql)

    return sqls



def update_status(p1, p2):
    # 初始化ck
    ck_client = ClickHouseClient()
    # 初始化mysql
    client = MySQLClient()
    # 获取用户
    user = get_user(p1, p2)
    # 获取 update的 状态
    result_status = p2['result_status']
    original_status = "','".join(set(p2['original_status']))
    # 解析参数 转置df
    df_status = pd.DataFrame(p2['form_data'])

    for _, row in df_status.iterrows():
        entity_id_single = row['entity_id']
        version_id_single = row['version_id']
        year_id_single = row['year_id']

    # 1、修改审批记录表的审批状态
    ApprovalProgressRecord_sqls = update_mysql(client, 'Approval_Progress_Record',
                             '/8_Approval/', df_status, result_status, original_status, user, status_column='result_status')
    # 执行sql语句
    result_01 = client.exec_sqls(ApprovalProgressRecord_sqls)


    # # 2、修改设备预算填报表的审批状态
    # profile_sqls = update_mysql(client, 'profile',
    #                             '/05_Datatable/05_08_Equipment', df_status,  result_status,
    #                             original_status, user, status_column='approve_status')
    # if profile_sqls:
    #     result_02 = client.exec_sqls(sqls=profile_sqls)
    #     result_02 = {'updateSuccessCount': 1}

    # 3、修改财务模型权限表的审批状态
    blockid_sqls = update_mysql(client, 'datatable_block_control_sub_profit_cube',
                                '/01_Cube/sub_profit_cube/', df_status, result_status,
                                original_status, user)
    block_id_info = ck_client.query_dfs(blockid_sqls)
    datablock_id = []
    for i in block_id_info:
        datablock_id += i['datablock_id'].to_list()
    # print(datablock_id)

    control_ck = DataTableClickHouse("process_control_sub_profit_cube")

    payload = DatatableDataUpdateDTO(
        setList={'process_status': result_status},
        elementName='process_control_sub_profit_cube',
        path='/01_Cube/sub_profit_cube/',
        whereList={'datablock_id': datablock_id,
                   'process_seg_2_value': [version_id_single],
                   'process_seg_1_value ': [year_id_single],
                   'process_seg_3_value': ['Difference','Actual','Budget']
                   }
    )

    result_03 = control_ck.api.dml.update_data(payload)
    payload = DatatableDataUpdateDTO(
        setList={'process_status': result_status},
        elementName='process_control_sub_profit_cube',
        path='/01_Cube/sub_profit_cube/',
        whereList={'datablock_id': datablock_id,
                   'process_seg_2_value': [version_id_single],
                   'process_seg_1_value ': [str(int(year_id_single)-1)],
                   'process_seg_3_value': ['Forecast']
                   }
    )
    result_03 = control_ck.api.dml.update_data(payload)
    # result_03 = update_ck(control_ck, {'process_status': result_status}, {'datablock_id': datablock_id,
    #                                                                   # 'process_status': original_status,
    #                                                                   'process_seg_3_value': 'Y1'})
    if result_03:
        result_03 = {'updateSuccessCount': 1}
    else:
        result_03 = {'updateSuccessCount': 0}


    # 4、修改BCP的审批状态
    # bcp_sqls = update_mysql(client, 'BCP', '/05_Datatable/05_01_BCP_Table', df_status,  result_status,
    #                          original_status, user, status_column='ApprovalStatus')
    # result_04 = client.exec_sqls(bcp_sqls)
    #
    #
    # # 5、同步修改Opreation_JG表项目的approve_status,如果 result_status 为 'Status08'，修改 Opreation_JG 表的 Is_Approve 字段为 '9'
    # opreation_jg_sqls = update_mysql(client, 'Opreation_JG', '/05_Datatable/05_01_BCP_Table/', df_status, result_status,
    #                         original_status, user, status_column='Approve_Status')
    # result_05 = client.exec_sqls(opreation_jg_sqls)



    # return result_01, result_02, result_03, result_04, result_05
    return result_01, result_03


def main(p1, p2):
    print(p2)
    try:
        # result_01, result_02, result_03, result_04, result_05 = update_status(p1, p2)
        result_01, result_03 = update_status(p1, p2)
        # print(result_01,result_02,result_03,result_04,result_05)
        if (result_01['updateSuccessCount'] >= 1) \
                and (result_03['updateSuccessCount'] >= 1):
                # and (result_03['updateSuccessCount'] >= 1)\
                # and (result_04['updateSuccessCount'] >= 1)\
                # and (result_05['updateSuccessCount'] >= 1):
            # 调用异步接口
            # asy_interface(p1, p2)
            # print(2)
            return "true"
        else:
            # print(1)
            return "false"
    except Exception as e:
        traceback.print_exc()


# debug
if __name__ == '__main__':
    from CWYS._debug import para1

    # p1 = {
    p2 = {'original_status': ['Status01'], 'result_status': 'Status02', 'form_data': [{'entity_id': 'CG200003', 'version_id': 'V1', 'year_id': '2026'}, {'entity_id': 'CG200004', 'version_id': 'V1', 'year_id': '2026'}]}

    main(para1, p2)
