# -*- coding: utf-8 -*-
# @Time : 2023/9/26 11:06
# @Author : LiYuXin
# @FileName: equipment_to_cube_batch.py
# @Software: PyCharm

import pandas as pd
from deepfos.element.datatable import DataTableMySQL
from deepfos.element.finmodel import FinancialCube
from deepfos.element.dimension import Dimension


# 获取设备信息
def get_equipment_data(name, columns, path, year, entity):
    entity_dim = Dimension("Entity")
    entity_all = entity_dim.query(entity, fields=["name"], as_model=False)
    df_entity = pd.DataFrame(data=entity_all).loc[:, ["name"]]
    df_entity.rename(columns={"name": "entity"}, inplace=True)

    sql_obj = DataTableMySQL(name, path=path)
    t = sql_obj.table
    where = (t.year == year)
    df = sql_obj.select(where=where, columns=columns)

    df_entity = pd.merge(df_entity, df, how="inner", on="entity")
    return df_entity


# 根据传入的表单id，继续过滤数据
def get_equipment_data_py(dt_equipment, form, p2):
    if 'department' in p2:
        department = p2['department']
    if 'approve_status' in p2:
        status = p2['approve_status']
    if 'equipment_location' in p2:
        location = p2['equipment_location']
    if 'version' in p2:
        version = p2['version']
    if 'scenario' in p2:
        scenario = p2['scenario']
    if form in ['SHT1d97a250fda9', 'SHT0fc73c7b3776']:  # 1、2
        dt = dt_equipment[
            (dt_equipment['department'] == department) & (
                    dt_equipment['equipment_location'] == location)]  # & (dt_equipment['approve_status'] == status)
        return dt
    elif form in ['SHT59ff31721250', 'SHT01f4a53e304f']:  # 3、4
        return dt_equipment[
            (dt_equipment['equipment_location'] == location)]  # & (dt_equipment['approve_status'] == status)

    elif form in ['SHTedf11af03d99', 'SHTeab8bb25e91f', 'SHT632b969b3d96']:  # 5、6、7
        return dt_equipment[
            (dt_equipment['equipment_location'] == location)]
    elif form == 'SHTee095c3383e6':  # 8
        return dt_equipment[
            (dt_equipment['department'] == department) & (dt_equipment['equipment_location'] == location)
            & (dt_equipment['version'] == version) & (dt_equipment['scenario'] == scenario)]
    elif form == 'SHTe3d842f50717':  # 9
        return dt_equipment[
            (dt_equipment['department'] == department) & (dt_equipment['equipment_location'] == location)
            & (dt_equipment['version'] == version) & (
                    dt_equipment['scenario'] == scenario)]  # & (dt_equipment['approve_status'] == status)
    elif form == 'SHTb03fad4013ae':  # 10
        return dt_equipment[
            (dt_equipment['scenario'] == scenario) & (dt_equipment['version'] == version)
            & (dt_equipment['department'] == department) & (dt_equipment['approve_status'] == status)]


# 1、设备大修重置预算填报
def equipment_overhaul_repurchase(df, columns, recol, account, measure):
    # 从原数据中获取需要的列
    dt_equipment = df[columns]
    dt_equipment = dt_equipment.rename(columns={recol: 'data'})
    # 分组求和
    columns = columns[0:-1]
    dt_equipment_1 = dt_equipment.groupby(columns)['data'].sum().reset_index()

    # 设置Account维度
    dt_equipment_1['Account'] = account
    # 设置measure维度
    if measure != '':
        dt_equipment_1['measure'] = measure

    return dt_equipment_1


def del_cube_data(form, year, entity):
    cube = FinancialCube('BEWG')
    if form == "SHTb03fad4013ae":
        return
    param_am = {
        'SHT1d97a250fda9': {'account': 'A3102030101', 'measure': 'Expenses'},
        'SHT0fc73c7b3776': {'account': 'A3102030101', 'measure': 'Areaaccount;Regionaccount;Groupaccount'},
        'SHT59ff31721250': {'account': 'A31020302', 'measure': 'Expenses'},
        'SHT01f4a53e304f': {'account': 'A31020302', 'measure': 'Areaaccount;Regionaccount;Groupaccount'},
        'SHTedf11af03d99': {'account': 'A31020101', 'measure': 'Expenses'},
        'SHTeab8bb25e91f': {'account': 'A31020102', 'measure': 'Expenses'},
        'SHT632b969b3d96': {'account': 'A31020201;A31020202', 'measure': 'Expenses'},
        'SHTee095c3383e6': {'account': 'A3102030102', 'measure': 'Expenses'},
        'SHTe3d842f50717': {'account': 'A3102030102', 'measure': 'Areaaccount;Regionaccount;Groupaccount'},
    }
    table_param_am = param_am[form]
    expression_delete = "Year{%s}->Entity{%s}->Account{%s}->Measure{%s}->" \
                        "Tax{Notax}->Version{Y1}->Material{Nomaterial}->Allocation{Original}->Misc1{Nomisc1}->" \
                        "Misc2{Nomisc2}->Department{Equipment}->Scenario{Budget}->Period{12}" % (
                            year, entity, table_param_am['account'], table_param_am['measure'])
    cube.delete(expression_delete)


def calc_amount_inspection_tax(data, year, entity, form):
    cube = FinancialCube("BEWG")
    list_account = list(set(data['Account'].tolist()))
    account = ";".join(list_account)
    data = data.rename(columns={"data": "org_data"})

    # 根据year entity account 查询对应税率 其他维度为指定
    expression_rate = "Year{%s}->Entity{%s}->Account{%s}->Tax{Taxrate}->" \
                      "Version{Y1}->Material{NoMaterial}->Allocation{Original}->Misc1{Nomisc1}->Misc2{Nomisc2}->" \
                      "Department{Operation}->Measure{Expenses}->Scenario{Budget}->Period{Noperiod}"\
                      % (year, entity, account)
    data_rate = cube.query(expression=expression_rate, compact=False)
    data_rate = data_rate[["Year", "Entity", "Account", "data"]].rename(columns={"data": "rate"})
    # 合并含税数据和税率
    data_and_rate = pd.merge(data, data_rate, how="left")
    # 如果未取出税率，则将税率设置为0
    data_and_rate["rate"] = data_and_rate["rate"].fillna(0)
    # 计算不含税数
    data_and_rate['data'] = data_and_rate['org_data'] / (1 + data_and_rate['rate'])
    del data_and_rate['org_data']
    del data_and_rate['rate']

    if data_and_rate.size > 0:
        # 根据表单确定存cube数据    维度的值
        data_and_rate['Department'] = "Equipment"
        data_and_rate['Scenario'] = "Budget"
        data_and_rate['Version'] = "Y1"
        data_and_rate['Period'] = "12"
        data_and_rate['Material'] = "Nomaterial"
        data_and_rate['Allocation'] = 'Original'
        data_and_rate['Tax'] = "Notax"
        data_and_rate['Misc1'] = "Nomisc1"
        data_and_rate['Misc2'] = "Nomisc2"
        if form in ["SHT1d97a250fda9", "SHT59ff31721250", "SHTedf11af03d99", "SHTeab8bb25e91f", "SHT632b969b3d96",
                    "SHTee095c3383e6"]:
            data_and_rate['Measure'] = "Expenses"
        cube.save(data=data_and_rate)


def main(p1, p2):
    year = p2['year']
    entity = p2['entity']
    form = p2['sheetId']
    department = "Equipment"

    # 整理要获取的字段
    columns = ['year', 'entity', 'department', 'equipment_location', 'approve_status', 'scenario', 'version',
               'sum_or', 'district_amount_er', 'region_amount_er', 'group_amount_er', 'sum_dc', 'sum_dm',
               'implementation_dm', 'sum_new',
               'district_amount_new', 'region_amount_new', 'group_amount_new', 'beginning', 'accrual', 'additional',
               'reverse', 'ending']
    # 获取数据--过滤条件只有entity、year，其他都条件到相应的方法中过滤
    dt_equipment = get_equipment_data('equipment_profile', columns, '/Datatable/Equipment', year, entity)

    # 10个表单处理数据开始
    if dt_equipment.size > 0:
        # 10个表单分别调用方法获取数据并保存到cube中
        dt_result = pd.DataFrame()
        if form == 'SHT1d97a250fda9':  # 表单1：equipment_overhaul_repurchase
            account = 'A3102030101'
            # 根据特殊条件过滤数据
            dt_equipment = get_equipment_data_py(dt_equipment, form, p2)
            column = ['year', 'entity', 'department', 'scenario', 'version', 'sum_or']
            # 处理数据
            dt_equipment_copy = equipment_overhaul_repurchase(dt_equipment, column, 'sum_or', account, 'Expenses')
            dt_result = dt_equipment_copy
            print(dt_result)
        elif form == 'SHT0fc73c7b3776':  # 表单2：equipment_overhaul_repurchase_auditing
            account = 'A3102030101'
            dt_equipment = get_equipment_data_py(dt_equipment, form, p2)
            column = ['year', 'entity', 'department', 'scenario', 'version', 'district_amount_er']
            dt_equipment_area = equipment_overhaul_repurchase(dt_equipment, column, 'district_amount_er',
                                                              account, 'Areaaccount')
            column = ['year', 'entity', 'department', 'scenario', 'version', 'region_amount_er']
            dt_equipment_region = equipment_overhaul_repurchase(dt_equipment, column, 'region_amount_er',
                                                                account, 'Regionaccount')
            column = ['year', 'entity', 'department', 'scenario', 'version', 'group_amount_er']
            dt_equipment_group = equipment_overhaul_repurchase(dt_equipment, column, 'group_amount_er',
                                                               account, 'Groupaccount')
            dt_result = pd.concat([dt_equipment_area, dt_equipment_region, dt_equipment_group])
        elif form == 'SHT59ff31721250':  # 表单3：installation_overhaul_repurchase
            account = 'A31020302'
            dt_equipment = get_equipment_data_py(dt_equipment, form, p2)
            column = ['year', 'entity', 'department', 'scenario', 'version', 'sum_or']
            dt_equipment_copy = equipment_overhaul_repurchase(dt_equipment, column, 'sum_or', account, 'Expenses')
            dt_result = dt_equipment_copy
        elif form == 'SHT01f4a53e304f':  # 表单4：installation_overhaul_repurchase_auditing
            account = 'A31020302'
            dt_equipment = get_equipment_data_py(dt_equipment, form, p2)
            column = ['year', 'entity', 'department', 'scenario', 'version', 'district_amount_er']
            dt_equipment_area = equipment_overhaul_repurchase(dt_equipment, column, 'district_amount_er',
                                                              account, 'Areaaccount')
            column = ['year', 'entity', 'department', 'scenario', 'version', 'region_amount_er']
            dt_equipment_region = equipment_overhaul_repurchase(dt_equipment, column, 'region_amount_er',
                                                                account, 'Regionaccount')
            column = ['year', 'entity', 'department', 'scenario', 'version', 'group_amount_er']
            dt_equipment_group = equipment_overhaul_repurchase(dt_equipment, column, 'group_amount_er',
                                                               account, 'Groupaccount')
            dt_result = pd.concat([dt_equipment_area, dt_equipment_region, dt_equipment_group])
        elif form == 'SHTedf11af03d99':  # 表单5：dailycare_equipment
            account = 'A31020101'
            dt_equipment = get_equipment_data_py(dt_equipment, form, p2)
            column = ['year', 'entity', 'department', 'scenario', 'version', 'sum_dc']
            dt_equipment_copy = equipment_overhaul_repurchase(dt_equipment, column, 'sum_dc', account, 'Expenses')
            dt_result = dt_equipment_copy
        elif form == 'SHTeab8bb25e91f':  # 表单6：dailycare_installation
            dt_equipment = get_equipment_data_py(dt_equipment, form, p2)
            column = ['year', 'entity', 'department', 'scenario', 'version', 'sum_dc']
            dt_equipment_copy = equipment_overhaul_repurchase(dt_equipment, column, 'sum_dc', 'A31020102',
                                                              'Expenses')
            dt_result = dt_equipment_copy
        elif form == 'SHT632b969b3d96':  # 表单7：dailymaintain_equipment
            dt_equipment = get_equipment_data_py(dt_equipment, form, p2)
            dt_equipment_01 = dt_equipment[dt_equipment['implementation_dm'] == 'I03']
            dt_equipment_02 = dt_equipment[
                (dt_equipment['implementation_dm'] == 'I01') | (dt_equipment['implementation_dm'] == 'I02')]
            column = ['year', 'entity', 'department', 'scenario', 'version', 'sum_dm']
            dt_equipment_area = equipment_overhaul_repurchase(dt_equipment_01, column, 'sum_dm',
                                                              'A31020201', 'Expenses')
            dt_equipment_region = equipment_overhaul_repurchase(dt_equipment_02, column, 'sum_dm',
                                                                'A31020202', 'Expenses')
            dt_result = pd.concat([dt_equipment_area, dt_equipment_region])
        elif form == 'SHTee095c3383e6':  # 表单8：new_equipment
            dt_equipment = get_equipment_data_py(dt_equipment, form, p2)
            column = ['year', 'entity', 'department', 'scenario', 'version', 'sum_new']
            dt_equipment_copy = equipment_overhaul_repurchase(dt_equipment, column, 'sum_new', 'A3102030102',
                                                              'Expenses')
            dt_result = dt_equipment_copy
        elif form == 'SHTe3d842f50717':  # 表单9：new_equipment_auditing
            account = 'A3102030102'
            dt_equipment = get_equipment_data_py(dt_equipment, form, p2)
            column = ['year', 'entity', 'department', 'scenario', 'version', 'district_amount_new']
            dt_equipment_area = equipment_overhaul_repurchase(dt_equipment, column, 'district_amount_new',
                                                              account, 'Areaaccount')
            column = ['year', 'entity', 'department', 'scenario', 'version', 'region_amount_new']
            dt_equipment_region = equipment_overhaul_repurchase(dt_equipment, column, 'region_amount_new',
                                                                account, 'Regionaccount')
            column = ['year', 'entity', 'department', 'scenario', 'version', 'group_amount_new']
            dt_equipment_group = equipment_overhaul_repurchase(dt_equipment, column, 'group_amount_new',
                                                               account, 'Groupaccount')
            dt_result = pd.concat([dt_equipment_area, dt_equipment_region, dt_equipment_group])
        elif form == 'SHTb03fad4013ae':  # 表单10：Estimated_Liabilities
            account = 'A3102030101'
            dt_equipment = get_equipment_data_py(dt_equipment, form, p2)
            column = ['year', 'entity', 'department', 'scenario', 'version', 'beginning']
            dt_equipment_begin = equipment_overhaul_repurchase(dt_equipment, column, 'beginning',
                                                               account, 'Liability')
            column = ['year', 'entity', 'department', 'scenario', 'version', 'accrual']
            dt_equipment_accrual = equipment_overhaul_repurchase(dt_equipment, column, 'accrual',
                                                                 account, 'Accrue')
            column = ['year', 'entity', 'department', 'scenario', 'version', 'additional']
            dt_equipment_additional = equipment_overhaul_repurchase(dt_equipment, column, 'additional',
                                                                    account, 'provision')
            column = ['year', 'entity', 'department', 'scenario', 'version', 'reverse']
            dt_equipment_reverse = equipment_overhaul_repurchase(dt_equipment, column, 'reverse',
                                                                 account, 'Writeoff')
            column = ['year', 'entity', 'department', 'scenario', 'version', 'ending']
            dt_equipment_end = equipment_overhaul_repurchase(dt_equipment, column, 'ending',
                                                             account, 'Liabilitybalance')

            dt_result = pd.concat([dt_equipment_begin, dt_equipment_accrual, dt_equipment_additional,
                                   dt_equipment_reverse, dt_equipment_end])
        # 清数
        del_cube_data(form, year, entity)
        #
        if dt_result.size > 0:
            # 补全默认维度
            dt_result['Period'] = '12'
            dt_result['Material'] = 'Nomaterial'
            dt_result['Allocation'] = 'Original'
            dt_result['Tax'] = 'Tax'
            dt_result['Misc1'] = 'Nomisc1'
            dt_result['Misc2'] = 'Nomisc2'
            dt_result = dt_result.rename(
                columns={'year': 'Year', 'entity': 'Entity', 'department': 'Department', 'scenario': 'Scenario',
                         'version': 'Version', 'measure': 'Measure'})
            # 保存cube
            cube = FinancialCube('BEWG')
            msg = cube.save(data=dt_result)
            print(msg)

            # 如果表单10 则复制 Notax
            if form == 'SHTb03fad4013ae':
                data_notax = dt_result.copy()
                data_notax['Tax'] = "NoTax"
                dt_result = pd.concat([dt_result, data_notax])
            # 如果 表单 1-9 则计算不含税
            elif form != 'SHTb03fad4013ae':
                # calc_amount_inspection_tax 参数 dt_result, year, entity,
                calc_amount_inspection_tax(dt_result, year, entity, form)

            msg = cube.save(data=dt_result)
            print(msg)

    # # 新增计算审核指标
    # from budget.Python.biz.phaseII.newly.indicators_equipment import main as main_audit
    # main_audit(p1, p2)
    # # 第七部分：计算毛利毛利率
    # from budget.Python.biz.phaseII.newly.gross_margin_calc import main as main_gross
    # main_gross(p1, p2)


if __name__ == '__main__':
    try:
        from common._debug import para1, para2
        p2 = {'year': '2024', 'entity': 'IDescendant(1,0)', 'sheetId': 'SHT2dee513bd945'}
    except:
        pass
    main(para1, p2)
