# import sys

# sys.path.append('../../')
# from conf._dpfs import p1, p2
from deepfos.element.datatable import DataTableMySQL
import pandas as pd
from deepfos.element.finmodel import FinancialCube
from budget.Python.biz.equipment.amount_tax_and_acc_copy import *

pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)


# 获取设备信息
def get_equipment_data(tabname, path, year, entity):
    sql_obj = DataTableMySQL(tabname, path=path)
    t = sql_obj.table
    where = (t.year == year) & (t.entity == entity)
    df = sql_obj.select(where=where)
    return df


# 拼接fix
def supply_fix(fix={}):
    a = {'Department': 'Equipment', 'Period': '12', 'Material': 'Nomaterial', 'Allocation': 'NoAllocation',
         'Tax': 'Tax',
         'Misc1': 'Nomisc1', 'Misc2': 'Nomisc2', 'Measure': 'Expenses', 'Scenario': 'budget', 'Version': 'Y1'}
    for i in a:
        if i not in fix:
            fix[i] = a[i]
    return fix


# 取profile数据
def equipment_overhaul_repurchase_sum(df, columns, recol, account, measure):
    # # 获取技改类型
    jg_dt = DataTableMySQL("Opreation_JG")
    jg_df = jg_dt.select(columns=['PLANCODE','PROJ_TYPE']).rename(columns={
        'PLANCODE'  :  'plancode',
        'PROJ_TYPE' :  'Misc1',
    })

    # 从原数据中获取需要的列
    dt_equipment = df[columns]
    dt_equipment = dt_equipment.rename(columns={recol: 'data'})
    dt_equipment = dt_equipment.merge(jg_df, on='plancode', how='left')
    # 分组求和
    # columns = columns[0:-1]+['Misc1']
    dt_equipment_1 = dt_equipment.groupby(['year','entity','department','scenario','version','Misc1'])['data'].sum().reset_index()

    # 写Misc1维度
    dt_equipment_1['Misc1'] = 'JG' + dt_equipment_1['Misc1'].astype(str)


    # 设置Account维度
    dt_equipment_1['Account'] = account
    # 设置measure维度
    if measure != '':
        dt_equipment_1['measure'] = measure

    return dt_equipment_1


# 1、设备大修重置预算填报
def equipment_overhaul_repurchase(df, columns, recol, account, measure):
    # 从原数据中获取需要的列
    dt_equipment = df[columns]
    dt_equipment = dt_equipment.rename(columns={recol: 'data'})
    # 分组求和
    columns = columns[0:-1]
    dt_equipment_1 = dt_equipment.groupby(columns)['data'].sum().reset_index()

    dt_equipment_1['Misc1'] = 'Nomisc1'
    # 设置Account维度
    dt_equipment_1['Account'] = account
    # 设置measure维度
    if measure != '':
        dt_equipment_1['measure'] = measure

    return dt_equipment_1



# 新增函数：根据 sheetId 确定表名
def get_table_name_by_sheet_id(sheet_id):
    tech_forms = {
        'SHTac171af4488d4d6eb8535911dafba492': 'equipment_profile_JG',  # 设备大修重置(技改)
        'SHTcabbd564f0a342529949d564d630635b': 'equipment_profile_JG',  # 设施大修(技改)
        'SHTff954af2b85e4aa2ba8bd544d2aed0f5': 'equipment_profile_JG',  # 新增设备(技改)
        'SHT208a02af77494471b35ecbcf31aebec0': 'equipment_profile_JG'  # 新增设施(技改)
    }
    non_tech_forms = {
        'SHTc9305cc22a394562bcfd253dedf3ef96': 'equipment_profile_NJ',  # 设备大修重置(非技改)
        'SHT89429863186a4aae84c97784df8bbab2': 'equipment_profile_NJ',  # 设施大修(非技改)
        'SHT96fb18823e754c28870c60d58722a533': 'equipment_profile_NJ',  # 新增设备(非技改)
        'SHT9ef716c265e2417b88616432e08031d1': 'equipment_profile_NJ',  # 设备日常维护
        'SHT8cf0b2092916424e979b5a32c04d1f84': 'equipment_profile_NJ',  # 设施日常维护
        'SHT6d671977518d4238bad73b64c8db5d09': 'equipment_profile_NJ',  # 设备日常维修
        'SHT795c36a1e8624dda8bcf7ca2ee868a01': 'equipment_profile_NJ',  # 预计负债表
    }


    if sheet_id in tech_forms:
        return tech_forms[sheet_id]
    elif sheet_id in non_tech_forms:
        return non_tech_forms[sheet_id]
    # elif sheet_id in both_tables_forms:
    #     return None  # 表示需要查询两个表
    else:
        raise ValueError(f"Unknown sheetId: {sheet_id}")

def del_cube_data(fix, form, p2):
    if form == "SHT632b969b3d96":
        fix["Year"] = p2["year"]
        fix["Entity"] = p2["entity"]
        fix["Department"] = "Equipment"
        fix["Measure"] = "Expenses"
        fix["Account"] = "A31020202;A31020201"
        cube = FinancialCube('BEWG')
        msg = cube.delete(fix)
    # if form =="SHT1d97a250fda9":
    #     fix["Year"] = p2["year"]
    #     fix["Entity"] = p2["entity"]
    #     fix["Department"] = p2["department"]
    #     fix["Measure"] = "Expenses"
    #     fix["Account"] = p2["A3102030101"]
    # elif form =="SHT0fc73c7b3776":
    #     fix["Year"] = p2["year"]
    #     fix["Entity"] = p2["entity"]
    #     fix["Department"] = p2["department"]
    #     fix["Measure"] = "Areaaccount;"
    #     fix["Account"] = p2["A3102030101"]


def main(p1, p2):
    print('p2:', p2)
    # try:
    # 获取参数
    if 'Year_wb1' in p2:
        year = p2['Year_wb1']
    else:
        return True
    if 'Entity_wb1' in p2:
        entity = p2['Entity_wb1']
    else:
        return True
    if 'Scenario_wb1' in p2:
        version = p2['Scenario_wb1']
    if 'Scenario_wb1' in p2:
        scenario = p2['Scenario_wb1']
    if 'Department_wb1' in p2:
        department = p2['Department_wb1']
    form = p2['sheetId']

    # 添加删除fix拼接代码 20221010 wlm
    del_fix = {}
    del_fix["Scenario"] = "Budget"
    del_fix["Version"] = "Y1"
    del_fix["Period"] = "12"
    del_fix["Material"] = "Nomaterial"
    del_fix["Allocation"] = "Original"
    del_fix["Tax"] = "Tax"
    del_fix["Misc1"] = "Nomisc1"
    del_fix["Misc2"] = "Nomisc2"
    # 调用删除方法，清楚cube中的数据。这里只做了第7个表单。后续如有表单需要添加，可在方法中判断表单ID，拼接del_fix即可
    # del_cube_data(del_fix, form, p2)

    # 整理要获取的字段
    columns = ['year', 'entity', 'code', 'department', 'equipment_location', 'approve_status', 'scenario', 'version',
               'sum_or', 'sum_new','sum_dc', 'sum_dm','implementation_dm',
               'district_amount_er', 'region_amount_er', 'group_amount_er',
               'district_amount_new', 'region_amount_new', 'group_amount_new',
               'beginning', 'accrual', 'additional','reverse', 'ending', 'plancode']

    # 获取数据
    try:
        table_name = get_table_name_by_sheet_id(form)
        print(table_name)
        if table_name:
            dt_equipment = get_equipment_data(table_name,'/05_Datatable/05_08_Equipment', year, entity)
        else:
            print('sheetId未识别')
    except ValueError as e:
        print(e)
        return False

    # 获取数据--过滤条件只有entity、year，其他都条件到相应的方法中过滤
    # dt_equipment = get_equipment_data('equipment_profile_NJ', columns, '/05_Datatable/5_0_Equipment', year, entity)
    fix = {'Year': year, 'Entity': entity}

    # 10个表单处理数据开始
    if dt_equipment.size > 0:
        # 10个表单分别调用方法获取数据并保存到cube中
        dt_result = pd.DataFrame()

        # 表单1：equipment_overhaul_repurchase 设备大修重置预算调整(非技改)
        if form == 'SHTc9305cc22a394562bcfd253dedf3ef96':
            account = 'PL0102040201'
            # 拼接清cube fix
            fix['Department'] = department
            fix['Account'] = account
            print('设备大修重置fix：', fix)
            # 根据特殊条件过滤数据
            dt_equipment = dt_equipment[(dt_equipment['equipment_location'] == 'el01')]
            # dt_equipment = get_equipment_data_py(dt_equipment, form, p2)
            column = ['year', 'entity', 'department', 'scenario', 'version', 'sum_or']
            # 处理数据预算金额
            dt_equipment_sum = equipment_overhaul_repurchase(dt_equipment, column, 'sum_or', account, 'Expenses')
            # 处理审核金额
            column = ['year', 'entity', 'department', 'scenario', 'version', 'district_amount_er']
            dt_equipment_area = equipment_overhaul_repurchase(dt_equipment, column, 'district_amount_er',
                                                              account, 'Areaaccount')
            column = ['year', 'entity', 'department', 'scenario', 'version', 'region_amount_er']
            dt_equipment_region = equipment_overhaul_repurchase(dt_equipment, column, 'region_amount_er',
                                                                account, 'Regionaccount')
            column = ['year', 'entity', 'department', 'scenario', 'version', 'group_amount_er']
            dt_equipment_group = equipment_overhaul_repurchase(dt_equipment, column, 'group_amount_er',
                                                               account, 'Groupaccount')
            dt_result = pd.concat([dt_equipment_sum,dt_equipment_area, dt_equipment_region, dt_equipment_group])


        # 表单2：installation_overhaul_repurchase 设施大修预算调整(非技改)
        elif form == 'SHT89429863186a4aae84c97784df8bbab2':
            account = 'PL0102040203'
            fix['Account'] = account
            dt_equipment = dt_equipment[(dt_equipment['equipment_location'] == 'el02')]
            # dt_equipment = get_equipment_data_py(dt_equipment, form, p2)
            # 处理预算金额
            column = ['year', 'entity', 'department', 'scenario', 'version', 'sum_or']
            dt_equipment_sum = equipment_overhaul_repurchase(dt_equipment, column, 'sum_or', account, 'Expenses')
            # 处理审核金额
            column = ['year', 'entity', 'department', 'scenario', 'version', 'district_amount_er']
            dt_equipment_area = equipment_overhaul_repurchase(dt_equipment, column, 'district_amount_er',
                                                              account, 'Areaaccount')
            column = ['year', 'entity', 'department', 'scenario', 'version', 'region_amount_er']
            dt_equipment_region = equipment_overhaul_repurchase(dt_equipment, column, 'region_amount_er',
                                                                account, 'Regionaccount')
            column = ['year', 'entity', 'department', 'scenario', 'version', 'group_amount_er']
            dt_equipment_group = equipment_overhaul_repurchase(dt_equipment, column, 'group_amount_er',
                                                               account, 'Groupaccount')
            dt_result = pd.concat([dt_equipment_sum,dt_equipment_area, dt_equipment_region, dt_equipment_group])


        # 表单3：new_equipment 新增设备预算调整(非技改)
        elif form == 'SHT96fb18823e754c28870c60d58722a533':
            # 拼接清Cube  fix
            account = 'PL0102040202'
            fix['Department'] = department
            fix['Version'] = version
            fix['Scenario'] = scenario
            dt_equipment = dt_equipment[(dt_equipment['equipment_location'] == 'el01')]
            # dt_equipment = get_equipment_data_py(dt_equipment, form, p2)
            column = ['year', 'entity', 'department', 'scenario', 'version', 'sum_new']

            # 处理预算金额
            dt_equipment_sum = equipment_overhaul_repurchase(dt_equipment, column, 'sum_new', account, 'Expenses')
            # 处理审核金额
            column = ['year', 'entity', 'department', 'scenario', 'version', 'district_amount_new']
            dt_equipment_area = equipment_overhaul_repurchase(dt_equipment, column, 'district_amount_new',
                                                              account, 'Areaaccount')
            column = ['year', 'entity', 'department', 'scenario', 'version', 'region_amount_new']
            dt_equipment_region = equipment_overhaul_repurchase(dt_equipment, column, 'region_amount_new',
                                                                account, 'Regionaccount')
            column = ['year', 'entity', 'department', 'scenario', 'version', 'group_amount_new']
            dt_equipment_group = equipment_overhaul_repurchase(dt_equipment, column, 'group_amount_new',
                                                               account, 'Groupaccount')
            dt_result = pd.concat([dt_equipment_sum,dt_equipment_area, dt_equipment_region, dt_equipment_group])


        # 表单4：dailycare_equipment  设备日常维护预算填报
        elif form == 'SHT9ef716c265e2417b88616432e08031d1':
            account = 'PL010204010203'
            fix['Account'] = account
            dt_equipment = dt_equipment[(dt_equipment['equipment_location'] == 'el01')]
            # dt_equipment = get_equipment_data_py(dt_equipment, form, p2)
            column = ['year', 'entity', 'department', 'scenario', 'version', 'sum_dc']
            dt_equipment_copy = equipment_overhaul_repurchase(dt_equipment, column, 'sum_dc', account, 'Expenses')
            dt_result = dt_equipment_copy

        # 表单5：dailycare_installation 设施日常维护预算填报
        elif form == 'SHT8cf0b2092916424e979b5a32c04d1f84':
            dt_equipment = dt_equipment[(dt_equipment['equipment_location'] == 'el02')]
            # dt_equipment = get_equipment_data_py(dt_equipment, form, p2)
            column = ['year', 'entity', 'department', 'scenario', 'version', 'sum_dc']
            dt_equipment_copy = equipment_overhaul_repurchase(dt_equipment, column, 'sum_dc', 'PL0102040101','Expenses')
            dt_result = dt_equipment_copy

        # 表单6：dailymaintain_equipment 设备日常维修预算填报
        elif form == 'SHT6d671977518d4238bad73b64c8db5d09':
            dt_equipment = dt_equipment[(dt_equipment['equipment_location'] == 'el01')]
            # dt_equipment = get_equipment_data_py(dt_equipment, form, p2)
            dt_equipment_01 = dt_equipment[dt_equipment['implementation_dm'] == 'I03']
            dt_equipment_02 = dt_equipment[(dt_equipment['implementation_dm'] == 'I01') | (dt_equipment['implementation_dm'] == 'I02')]
            column = ['year', 'entity', 'department', 'scenario', 'version', 'sum_dm']
            dt_equipment_ww = equipment_overhaul_repurchase(dt_equipment_01, column, 'sum_dm','PL010204010201', 'Expenses')
            dt_equipment_zz = equipment_overhaul_repurchase(dt_equipment_02, column, 'sum_dm','PL010204010202', 'Expenses')
            dt_result = pd.concat([dt_equipment_ww, dt_equipment_zz])

        # 表单7：equipment_overhaul_repurchase 设备大修重置预算调整(技改)
        elif form == 'SHTac171af4488d4d6eb8535911dafba492':
            account = 'PL0301'
            # 拼接清cube fix
            fix['Department'] = department
            fix['Account'] = account
            # 根据特殊条件过滤数据
            dt_equipment = dt_equipment[(dt_equipment['equipment_location'] == 'el01')]
            # dt_equipment = get_equipment_data_py(dt_equipment, form, p2)
            column = ['year', 'entity', 'department', 'scenario', 'version','plancode', 'sum_or']
            # 处理数据预算金额
            dt_equipment_sum = equipment_overhaul_repurchase_sum(dt_equipment, column, 'sum_or', account, 'Expenses')
            # 处理审核金额
            column = ['year', 'entity', 'department', 'scenario', 'version', 'district_amount_er']
            dt_equipment_area = equipment_overhaul_repurchase(dt_equipment, column, 'district_amount_er',
                                                              account, 'Areaaccount')
            column = ['year', 'entity', 'department', 'scenario', 'version', 'region_amount_er']
            dt_equipment_region = equipment_overhaul_repurchase(dt_equipment, column, 'region_amount_er',
                                                                account, 'Regionaccount')
            column = ['year', 'entity', 'department', 'scenario', 'version', 'group_amount_er']
            dt_equipment_group = equipment_overhaul_repurchase(dt_equipment, column, 'group_amount_er',
                                                               account, 'Groupaccount')
            dt_result = pd.concat([dt_equipment_sum,dt_equipment_area, dt_equipment_region, dt_equipment_group])


        # 表单8：installation_overhaul_repurchase 设施大修预算调整(技改)
        elif form == 'SHTcabbd564f0a342529949d564d630635b':
            account = 'PL0302'
            fix['Account'] = account
            dt_equipment = dt_equipment[(dt_equipment['equipment_location'] == 'el02')]
            # dt_equipment = get_equipment_data_py(dt_equipment, form, p2)
            column = ['year', 'entity', 'department', 'scenario', 'version','plancode', 'sum_or']
            # 处理预算金额
            dt_equipment_sum = equipment_overhaul_repurchase_sum(dt_equipment, column, 'sum_or', account, 'Expenses')
            # 处理审核金额
            column = ['year', 'entity', 'department', 'scenario', 'version', 'district_amount_er']
            dt_equipment_area = equipment_overhaul_repurchase(dt_equipment, column, 'district_amount_er',
                                                              account, 'Areaaccount')
            column = ['year', 'entity', 'department', 'scenario', 'version', 'region_amount_er']
            dt_equipment_region = equipment_overhaul_repurchase(dt_equipment, column, 'region_amount_er',
                                                                account, 'Regionaccount')
            column = ['year', 'entity', 'department', 'scenario', 'version', 'group_amount_er']
            dt_equipment_group = equipment_overhaul_repurchase(dt_equipment, column, 'group_amount_er',
                                                               account, 'Groupaccount')
            dt_result = pd.concat([dt_equipment_sum,dt_equipment_area, dt_equipment_region, dt_equipment_group])


        # 表单9：new_equipment 新增设备预算调整(技改)
        elif form == 'SHTff954af2b85e4aa2ba8bd544d2aed0f5':
            # 拼接清Cube  fix
            account = 'PL0303'
            fix['Department'] = department
            fix['Version'] = version
            fix['Scenario'] = scenario
            dt_equipment = dt_equipment[(dt_equipment['equipment_location'] == 'el01')]
            # dt_equipment = get_equipment_data_py(dt_equipment, form, p2)
            # 处理预算金额
            column = ['year', 'entity', 'department', 'scenario', 'version','plancode', 'sum_new']
            dt_equipment_sum = equipment_overhaul_repurchase_sum(dt_equipment, column, 'sum_new', account, 'Expenses')
            # 处理审核金额
            column = ['year', 'entity', 'department', 'scenario', 'version', 'district_amount_new']
            dt_equipment_area = equipment_overhaul_repurchase(dt_equipment, column, 'district_amount_new',
                                                              account, 'Areaaccount')
            column = ['year', 'entity', 'department', 'scenario', 'version', 'region_amount_new']
            dt_equipment_region = equipment_overhaul_repurchase(dt_equipment, column, 'region_amount_new',
                                                                account, 'Regionaccount')
            column = ['year', 'entity', 'department', 'scenario', 'version', 'group_amount_new']
            dt_equipment_group = equipment_overhaul_repurchase(dt_equipment, column, 'group_amount_new',
                                                               account, 'Groupaccount')
            dt_result = pd.concat([dt_equipment_sum,dt_equipment_area, dt_equipment_region, dt_equipment_group])


        # 表单10：new_equipment 新增设施预算调整(技改)
        elif form in ['SHT208a02af77494471b35ecbcf31aebec0']:
            # 拼接清Cube  fix
            account = 'PL0304'
            fix['Department'] = department
            fix['Version'] = version
            fix['Scenario'] = scenario
            dt_equipment = dt_equipment[(dt_equipment['equipment_location'] == 'el02')]
            # dt_equipment = get_equipment_data_py(dt_equipment, form, p2)
            # 处理预算金额
            column = ['year', 'entity', 'department', 'scenario', 'version','plancode', 'sum_new']
            dt_equipment_sum = equipment_overhaul_repurchase_sum(dt_equipment, column, 'sum_new', 'PL0304','Expenses')
            # 处理审核金额
            column = ['year', 'entity', 'department', 'scenario', 'version', 'district_amount_new']
            dt_equipment_area = equipment_overhaul_repurchase(dt_equipment, column, 'district_amount_new',
                                                              account, 'Areaaccount')
            column = ['year', 'entity', 'department', 'scenario', 'version', 'region_amount_new']
            dt_equipment_region = equipment_overhaul_repurchase(dt_equipment, column, 'region_amount_new',
                                                                account, 'Regionaccount')
            column = ['year', 'entity', 'department', 'scenario', 'version', 'group_amount_new']
            dt_equipment_group = equipment_overhaul_repurchase(dt_equipment, column, 'group_amount_new',
                                                               account, 'Groupaccount')
            dt_result = pd.concat([dt_equipment_sum,dt_equipment_area, dt_equipment_region, dt_equipment_group])


        # 表单11：预计负债表
        elif form == 'SHT795c36a1e8624dda8bcf7ca2ee868a01':  # 表单10：Estimated_Liabilities
            # 拼接清Cube  fix
            fix['Department'] = department
            fix['Version'] = version
            fix['Scenario'] = scenario
            account = 'PL0102040201'
            # dt_equipment = get_equipment_data_py(dt_equipment, form, p2)
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

        print('form:',form)
        # 清空预算金额、审核金额 含税不含税
        del_cube(form, year, entity)

        if dt_result.size > 0:
            # 补全默认维度
            dt_result['Period'] = '12'
            dt_result['Material'] = 'Nomaterial'
            dt_result['Allocation'] = 'Original'
            dt_result['Tax'] = 'Tax'
            # dt_result['Misc1'] = 'Nomisc1'
            dt_result['Misc2'] = 'Nomisc2'
            dt_result = dt_result.rename(
                columns={'year': 'Year', 'entity': 'Entity', 'department': 'Department', 'scenario': 'Scenario',
                         'version': 'Version', 'measure': 'Measure'})

            # 如果表单11 则含税不含税相同 直接复制 Notax
            if form == 'SHT795c36a1e8624dda8bcf7ca2ee868a01':
                data_notax = dt_result.copy()
                data_notax['Tax'] = "NoTax"
                dt_result = pd.concat([dt_result, data_notax])
            # 如果 表单 1-10 则计算不含税
            elif form != 'SHT795c36a1e8624dda8bcf7ca2ee868a01':
                # calc_amount_inspection_tax 参数 dt_result, year, entity,
                calc_amount_inspection_tax(dt_result, year, entity, form, department)

            # 保存cube
            cube = FinancialCube('WS_cube')
            print('存前', dt_result)
            msg = cube.save(data=dt_result)
            # # 循环遍历每一列
            # for column in dt_result.columns:
            #     # 打印列名
            #     print(f"Column Name: {column}")
            #     # 打印该列的所有值
            #     print(dt_result[column])
            #     print()  # 打印一个空行以便于区分不同列的输出
            print(msg)

            # # 如果 表单 135678 则科目复制
            # if form in ["SHTedf11af03d99", "SHTeab8bb25e91f"]:
            #     account_copy(year, entity, acc="A82")
            # elif form == "SHT632b969b3d96":
            #     account_copy(year, entity, acc="A83")
            # elif form in ["SHT1d97a250fda9", "SHT59ff31721250", "SHTee095c3383e6"]:  # 1 3 8
            #     account_copy(year, entity, acc="A87")
            # print("科目复制")

            # # 1-9 表单 复制科目
            # if form != 'SHTb03fad4013ae':
            #     total_equipment_account_copy(year, entity)

    # except Exception:
    #     return Exception

    # 新增计算审核指标
    # from budget.Python.biz.equipment.indicators_equipment import main as main_audit
    # main_audit(p1, p2)
    #
    # # 计算增长额 增长率 预实完成率
    # from budget.Python.biz.equipment.equipment_config_calc import main as main_calc
    # main_calc(p1, p2)



    # # 计算毛利毛利率-删除
    # from budget.Python.biz.phaseII.newly.gross_margin_calc import main as main_gross
    # p2["Year"] = p2["year"]
    # main_gross(p1, p2)
    # print("gross_margin_calc down")


if __name__ == '__main__':
    try:
        from common._debug import para1, p2
    except:
        pass
    p2=  {'elementName': 'tb_equipment_big_fix', 'folderId': 'DIRde9daa600898', 'sheetName': '技改-设备大修重置预算填报', 'sheetId': 'SHTac171af4488d4d6eb8535911dafba492', 'Year_wb1': '2026', 'Entity_wb1': 'Y0020241559', 'Department_wb1': 'Technical', 'Scenario_wb1': 'Budget', 'Version_wb1': 'Y1'}


    main(para1, p2)
