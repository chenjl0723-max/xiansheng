import pandas as pd
from deepfos.element.finmodel import FinancialCube

# added by wlm
# added in 20220817
# added for 电费&污泥处理费计算逻辑-优化版本

# 初始化取数Account
list_account = ['A05', 'A1001', 'A1002', 'A31010201', 'A3101020201', 'A3101020202', 'A310104010201', 'A3101040201',
                'A310104']

# 实际数Account
list_account4 = ['A3101040102', 'A31010402', 'A1001', 'A1002', 'A310104']


# 0、设置符合取数的fix
def get_fix_to_str(fix):
    pov = ""
    for k, v in fix.items():
        pov += k
        pov += "{"
        pov += v
        pov += "}"
        pov += "->"
    pov = pov[:-2]
    return pov


# 删除无用的列
def del_columns(dt_budget, col_list):
    columns = dt_budget.columns.values.tolist()
    for col in col_list:
        if col in columns:
            del dt_budget[col]

    return dt_budget


# 获取fix
def get_fix(fix, account, measure, tax):
    year = fix['Year']
    front_year = int(year) - 1
    fix['Year'] = "%s;%s" % (str(year), str(front_year))
    fix['Scenario'] = 'Budget;Actual;New'
    fix['Measure'] = measure
    fix['Period'] = '1;2;3;4;5;6;7;8;9;10;11;12;Adjust;Noperiod'
    fix['Account'] = account
    fix['Tax'] = tax
    fix = get_fix_to_str(fix)
    return fix


# 1、获取cube中的数据
def get_cube_data(fix, pivot=True):
    cube = FinancialCube('BEWG', path='/Cube')
    if "->elementName{Electricity}->folderId{DIR120caca66e0b}" in fix:
        fix = fix.replace("->elementName{Electricity}->folderId{DIR120caca66e0b}", "")
    if pivot:
        print(fix)
        dt_cube = cube.query(fix, compact=False, pivot_dim='Account')
    else:
        dt_cube = cube.query(fix, compact=False)
    if dt_cube.size == 0:
        return dt_cube

    # 因为Measure维度值不一致，需要特殊处理
    dt_expenses = dt_cube[dt_cube['Measure'] == 'Expenses']
    if pivot == False:
        return dt_expenses
    dt_expenses = del_columns(dt_expenses, list_account[0:3])
    dt_nomeasure = dt_cube[dt_cube['Measure'] == 'Nomeasure']
    dt_nomeasure = del_columns(dt_nomeasure, list_account[3:9])
    if "A3101040102" in dt_nomeasure.columns.tolist():
        del dt_nomeasure['A3101040102']
    if "A31010402" in dt_nomeasure.columns.tolist():
        del dt_nomeasure['A31010402']
    columns = ['Year', 'Entity', 'Version', 'Material', 'Allocation', 'Tax', 'Department', 'misc1', 'misc2', 'Scenario',
               'Period']
    dt_new_cube = pd.merge(left=dt_expenses, right=dt_nomeasure, how='left', on=columns)
    dt_new_cube = dt_new_cube.rename(columns={'Measure_x': 'Measure'})
    del dt_new_cube['Measure_y']

    # 将Account行专列，转换完成后，验证是否缺少Account，如去缺少，添加列，并设置列值为0
    columns = dt_new_cube.columns.values.tolist()
    for col in list_account:
        if col in columns:
            continue
        dt_new_cube[col] = 0
    dt_new_cube = dt_new_cube.fillna(0)
    return dt_new_cube


# 2、计算预算数&实际数12月调整&批复新增
def calc_acture_budget(dt_budget, cube_actual, cube_actual_period):
    if dt_budget.size > 0:
        # 电度电量
        dt_budget['A3101020203'] = dt_budget['A3101020202'] * dt_budget['A05']
        # 电度电费
        dt_budget["A31010202"] = dt_budget["A3101020201"] * dt_budget["A3101020203"]
        # 吨水电费（元/吨)
        dt_budget.loc[dt_budget['A05'] > 0, 'A310103'] = (dt_budget['A31010201'] + dt_budget['A31010202']) / dt_budget[
            'A05']
        dt_budget.loc[dt_budget['A05'] == 0, 'A310103'] = 0

        # 委外车辆运输
        dt_budget['A3101040102'] = dt_budget['A310104010201'] * (dt_budget['A1001'] + dt_budget['A1002']) / 10000
        # 污泥处置费
        dt_budget['A31010402'] = dt_budget['A3101040201'] * (dt_budget['A1001'] + dt_budget['A1002']) / 10000

        if "A31010402" not in dt_budget.columns.tolist():
            dt_budget["A31010402"] = 0
        if "A3101040102" not in dt_budget.columns.tolist():
            dt_budget["A3101040102"] = 0
        if "A3101040101" not in dt_budget.columns.tolist():
            dt_budget["A3101040101"] = 0
        # 污泥处理费吨水费用
        dt_budget.loc[dt_budget['A05'] > 0, 'A310105'] = (dt_budget['A31010402'] + dt_budget["A3101040102"] + dt_budget[
            "A3101040101"]) / dt_budget['A05']
        dt_budget.loc[dt_budget['A05'] == 0, 'A310105'] = 0

        # 科目复制
        dt_budget['A310109'] = dt_budget['A310104']
        dt_budget = del_columns(dt_budget, list_account)
        del dt_budget["A3101040101"]

        # 计算全年电度电费
        dt_budget_no_period = dt_budget[(dt_budget["Scenario"] == "Budget") & (
            dt_budget["Period"].isin(['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']))]
        # 删除无用的列
        for col in ["A3101040102", "A31010402", "A3101020203", "A310103", "A310105", "A310109"]:
            if col in dt_budget_no_period.columns.tolist():
                del dt_budget_no_period[col]
        # 汇总A31010202
        dt_budget_no_period = dt_budget_no_period.groupby(
            by=["Measure", "Scenario", "Year", "Entity", "Version", "Material",
                "Allocation", "Tax", "Department", "misc1", "misc2"], as_index=False).sum()
        dt_budget_no_period["Period"] = "Noperiod"

        # 删除实际数为Noperiod的数据，这块数据由外部计算好之后传递过来。
        # dt_budget = dt_budget[~((dt_budget["Scenario"] == "Actual") & (dt_budget["Period"] == "Noperiod"))]

        # 计算全年污泥处置费及委外车辆运输费
        dt_new = dt_budget[(dt_budget["Scenario"] == "Budget")]
        colu = ["Measure", "Scenario", "Year", "A31010402", "A3101040102", "Entity", "Version", "Material",
                "Allocation", "Tax", "Department", "misc1", "misc2"]
        dt_new = dt_new[colu]
        dt_new = dt_new.groupby(
            by=["Measure", "Scenario", "Year", "Entity", "Version", "Material",
                "Allocation", "Tax", "Department", "misc1", "misc2"], as_index=False).sum()
        dt_new["Period"] = "Noperiod"
        dt_new = pd.concat([dt_new, cube_actual])

        # 将所有的宽表设置为长表
        dt_budget_1 = pd.melt(dt_budget_no_period,
                              id_vars=["Scenario", "Year", "Entity", "Version", "Material", "Allocation", "Tax",
                                       "Department", "misc1",
                                       "misc2", "Period", "Measure"], var_name="Account")
        dt_budget_2 = pd.melt(dt_budget,
                              id_vars=["Scenario", "Year", "Entity", "Version", "Material", "Allocation", "Tax",
                                       "Department", "misc1",
                                       "misc2", "Period", "Measure"], var_name="Account")
        dt_budget_3 = pd.melt(dt_new,
                              id_vars=["Scenario", "Year", "Entity", "Version", "Material", "Allocation", "Tax",
                                       "Department", "misc1",
                                       "misc2", "Period", "Measure"], var_name="Account")
        dt_budget = pd.concat([dt_budget_1, dt_budget_2, dt_budget_3]).rename(columns={"value": "data"})

        # 计算电镀电量汇总数据
        dt_budget_a3101020203 = dt_budget[(dt_budget["Scenario"] == "Budget") & (dt_budget["Account"] == "A3101020203")]
        dt_budget_a3101020203 = dt_budget_a3101020203.groupby(
            by=["Measure", "Scenario", "Year", "Entity", "Version", "Material",
                "Allocation", "Tax", "Department", "misc1", "misc2", "Account"], as_index=False).sum()
        dt_budget_a3101020203["Period"] = "Noperiod"

        # 计算实际电镀电量汇总数据
        dt_actual_a3101020203 = dt_budget[
            (dt_budget["Period"] == "Adjust") & (dt_budget["Account"] == "A3101020203") & (
                    dt_budget["Scenario"] == "Actual")]

        dt_actual_a3101020203 = pd.concat([dt_actual_a3101020203, cube_actual_period])
        dt_actual_a3101020203["Period"] = "Noperiod"

        dt_actual_a3101020203 = dt_actual_a3101020203.groupby(
            by=["Scenario", "Year", "Entity", "Version", "Material", "Allocation", "Tax", "Department", "misc1",
                "misc2", "Period", "Measure", "Account"], as_index=False).sum()

        dt_budget = pd.concat([dt_budget, dt_budget_a3101020203])
        dt_budget = pd.concat([dt_budget, dt_actual_a3101020203])

        return dt_budget, dt_new


# 3、计算1-12月份实际数
def calc_actual_for_month(dt_budget, dt_new):
    if dt_budget.size > 0:
        if dt_new.size > 0:
            dt_budget = pd.merge(left=dt_budget, right=dt_new, how="left",
                                 on=["Measure", "Scenario", "Year", "Entity", "Version", "Material",
                                     "Allocation", "Tax", "Department", "misc1", "misc2"])
            if "A31010402_y" in dt_budget.columns.tolist():
                dt_budget.loc[
                    (dt_budget["Scenario"] == "Budget") & (dt_budget["Period_x"] == "Noperiod"), 'A31010402_x'] = \
                    dt_budget["A31010402_y"]
                dt_budget.loc[
                    (dt_budget["Scenario"] == "Actual") & (dt_budget["Period_x"] == "Noperiod"), 'A31010402_x'] = \
                    dt_budget["A31010402_y"]
            if "A3101040102_y" in dt_budget.columns.tolist():
                dt_budget.loc[
                    (dt_budget["Scenario"] == "Budget") & (dt_budget["Period_x"] == "Noperiod"), 'A3101040102_x'] = \
                    dt_budget["A3101040102_y"]
                dt_budget.loc[
                    (dt_budget["Scenario"] == "Actual") & (dt_budget["Period_x"] == "Noperiod"), 'A3101040102_x'] = \
                    dt_budget["A3101040102_y"]

        for col in ["A3101040102_y", "A31010402_y", "Period_y"]:
            if col in dt_budget.columns.tolist():
                del dt_budget[col]
        dt_budget = dt_budget.rename(
            columns={"A3101040102_x": "A3101040102", "A31010402_x": "A31010402", "Period_x": "Period"})
        # 打补丁，判断如果A3101040102不在数据中，则赋值为0
        if "A3101040102" not in dt_budget.columns.tolist():
            dt_budget["A3101040102"] = 0
        if "A31010402" not in dt_budget.columns.tolist():
            dt_budget["A31010402"] = 0
        # 运输单价（实际数）
        dt_budget['A310104010201'] = dt_budget['A3101040102'] / (dt_budget['A1001'] + dt_budget['A1002']) * 10000
        dt_budget.loc[(dt_budget['A1001'] + dt_budget['A1002']) == 0, 'A310104010201'] = 0
        # 处置单价（实际数）
        dt_budget['A3101040201'] = dt_budget['A31010402'] / (dt_budget['A1001'] + dt_budget['A1002']) * 10000
        dt_budget.loc[(dt_budget['A1001'] + dt_budget['A1002']) == 0, 'A3101040201'] = 0
        # 科目复制
        dt_budget['A310109'] = dt_budget['A310104']

        # 删除无用的列
        colu = ['Measure', 'Period', 'Scenario', 'Year', 'Entity', 'Version', 'Material', 'Allocation', 'Tax',
                'Department', 'misc1', 'misc2', 'A310104010201', 'A3101040201', 'A310109']
        dt_budget = dt_budget[colu]
        # del_columns(dt_budget, list_account4)
        return dt_budget
    else:
        return pd.DataFrame(data=None)


# 4、计算不含税结果
def calc_budget_tax(dt_rate_data, dt_rate):
    # if dt_rate.size == 0:
    #     return
    columns = ['Entity', 'Version', 'Material', 'Allocation', 'Department', 'misc1', 'misc2',
               'Measure', 'Account']

    dt_budget = pd.merge(left=dt_rate_data, right=dt_rate, how='left', on=columns)
    # 新增需求，将未取到税率的科目，税率设置为0
    dt_budget['data_y'] = dt_budget['data_y'].fillna(0)
    dt_budget['data'] = dt_budget['data_x'] / (1 + dt_budget['data_y'])
    for col in ['data_x', 'data_y', 'Period_y', 'Tax_y', 'Scenario_y', 'Year_y']:
        del dt_budget[col]
    dt_budget = dt_budget.rename(
        columns={'Account_x': 'Account', 'Period_x': 'Period', 'Tax_x': 'Tax', 'Scenario_x': 'Scenario',
                 'Year_x': 'Year'})
    dt_budget['Tax'] = 'Notax'
    dt_budget = dt_budget.groupby(by=['Account', 'Measure', 'Period', 'Year', 'Entity', 'Version', 'Material',
                                      'Allocation', 'Tax', 'Department', 'misc1', 'misc2', 'Scenario'],
                                  as_index=False).sum()

    # save_cube(dt_budget, "", pivot=False)
    # 计算A310109 不含税     # 科目复制
    dt_budget_no_tax = dt_budget[dt_budget['Account'].isin(['A3101040101', 'A3101040102', 'A31010402'])]
    dt_budget_no_tax = dt_budget_no_tax.groupby(by=['Measure', 'Period', 'Year', 'Entity', 'Version', 'Material',
                                                    'Allocation', 'Tax', 'Department', 'misc1', 'misc2',
                                                    'Scenario'],
                                                as_index=False).sum()
    dt_budget_no_tax['Account'] = 'A310109'
    dt_budget_no_tax = pd.concat([dt_budget, dt_budget_no_tax])
    return dt_budget_no_tax


# 删除不含税结果
def del_no_tax_data(fix):
    year = fix["Year"]
    front_year = int(year) - 1
    budget_fix = fix.copy()
    actual_new_fix = fix.copy()
    actual_adjust_fix = fix.copy()

    budget_fix["Account"] = "Base(A310102,0);Base(A310104,0)"
    budget_fix["Scenario"] = "Budget"
    budget_fix["Measure"] = "Expenses"
    budget_fix["Period"] = "1;2;3;4;5;6;7;8;9;10;11;12"
    budget_fix["Tax"] = "Notax"

    actual_new_fix["Account"] = "Base(A310102,0);Base(A310104,0)"
    actual_new_fix["Year"] = str(front_year)
    actual_new_fix["Measure"] = "Expenses"
    actual_new_fix["Scenario"] = "New;Actual"
    actual_new_fix["Period"] = "Noperiod"
    actual_new_fix["Tax"] = "Notax"

    actual_adjust_fix["Account"] = "Base(A310102,0);Base(A310104,0)"
    actual_adjust_fix["Year"] = str(front_year)
    actual_adjust_fix["Measure"] = "Expenses"
    actual_adjust_fix["Scenario"] = "Actual"
    actual_adjust_fix["Period"] = "Adjust"
    actual_adjust_fix["Tax"] = "Notax"
    cube = FinancialCube('BEWG', path='/Cube')
    cube.delete(budget_fix)
    cube.delete(actual_new_fix)
    cube.delete(actual_adjust_fix)


# 5、将计算数据保存到cube    先删后加
def save_cube(df_budget, fix, pivot=True):
    if df_budget.size > 0:
        # 先清数
        cube = FinancialCube('BEWG', path='/Cube')
        # cube.delete(fix)
        # 保存数据
        if pivot:
            response = cube.save_unpivot(df_budget, unpivot_dim='Account')
        else:
            response = cube.save(df_budget)
        return response


# 格式化DataFrame
def formal_dataframe(dt_cube, year, front_year):
    if dt_cube.size > 0:
        month = ['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']
        period = ['Adjust', 'Noperiod']
        # 获取Budget预算数据
        dt_budget = dt_cube[
            (dt_cube['Scenario'] == 'Budget') & (dt_cube['Period'].isin(month)) & (
                    dt_cube['Measure'] == 'Expenses') & (
                    dt_cube['Year'] == str(year)) & (dt_cube['Tax'] == 'Tax')]
        # 获取Actual实际数据12月调整
        dt_actual = dt_cube[
            (dt_cube['Scenario'] == 'Actual') & (dt_cube['Period'].isin(period)) & (
                    dt_cube['Measure'] == 'Expenses') & (
                    dt_cube['Year'] == str(front_year)) & (dt_cube['Tax'] == 'Tax')]
        # 获取New新增数据
        dt_new = dt_cube[
            (dt_cube['Scenario'] == 'New') & (dt_cube['Period'] == 'Noperiod') & (
                    dt_cube['Measure'] == 'Expenses') & (
                    dt_cube['Year'] == str(front_year)) & (dt_cube['Tax'] == 'Tax')]
        # 获取Actual实际数据1-12月份
        dt_actual_mn = dt_cube[
            (dt_cube['Scenario'] == 'Actual') & (dt_cube['Period'].isin(month + ["Noperiod"])) & (
                    dt_cube['Measure'] == 'Expenses') & (dt_cube['Year'] == str(front_year)) & (
                    dt_cube['Tax'] == 'Tax')]
        # 获取Budget预算数据Noperiod数据
        dt_budget_m = dt_cube[
            (dt_cube['Scenario'] == 'Budget') & (dt_cube['Period'] == "Noperiod") & (
                    dt_cube['Measure'] == 'Expenses') & (dt_cube['Year'] == str(year)) & (
                    dt_cube['Tax'] == 'Tax')]
        dt_actual_m = pd.concat([dt_actual_mn, dt_budget_m])

        # 获取税率信息
        dt_rate = dt_cube[
            (dt_cube['Scenario'] == 'Budget') & (dt_cube['Period'] == 'Noperiod') & (
                    dt_cube['Measure'] == 'Expenses') & (
                    dt_cube['Year'] == str(year)) & (dt_cube['Tax'] == 'Taxrate')]
        dt_budget = pd.concat([dt_budget, dt_actual, dt_new])
        return dt_budget, dt_actual_m, dt_rate


# 吨水电耗科目计算
def water_power_per(fix):
    fix['Account'] = 'A3101020203;A05;A31010402;A31010401;A31010201;A31010202'
    fix['Scenario'] = 'Budget;Actual'
    fix['Measure'] = 'Expenses;Nomeasure'
    fix['Period'] = 'Noperiod'
    fix = get_fix_to_str(fix)
    cube = FinancialCube('BEWG', path='/Cube')
    # dt_cube = cube.query(fix, compact=False)
    dt_cube = cube.query(fix, compact=False, pivot_dim='Account')
    if not dt_cube.empty:
        col_list = ["Scenario", "Year", "Entity", "Version", "Material", "Allocation", "Tax", "Department", "misc1",
                    "misc2", "Period"]
        dt_expenses = dt_cube[dt_cube["Measure"] == "Expenses"]
        if "A05" in dt_expenses.columns.tolist():
            del dt_expenses["A05"]
        dt_no_expenses = dt_cube[dt_cube["Measure"] == "Nomeasure"]
        if dt_no_expenses.size == 0:
            dt_no_expenses["A05"] = 0
        for col in ["A3101020203", "A31010402", "A31010401", "A31010201", "A31010202"]:
            if col in dt_no_expenses.columns.tolist():
                del dt_no_expenses[col]
        dt_cube = pd.merge(left=dt_expenses, right=dt_no_expenses, how="inner", on=col_list)
        if not dt_cube.empty:
            if "A31010402" not in dt_cube:
                dt_cube["A31010402"] = 0
            del dt_cube["Measure_y"]
            dt_cube = dt_cube.rename(columns={"Measure_x": "Measure"})

            # 20221201 xmx 优化bug
            dt_cube = dt_cube.where(dt_cube.notnull(), 0)
            if "A31010201" not in dt_cube:
                dt_cube["A31010201"] = 0

            dt_cube["A3101020202"] = dt_cube["A3101020203"] / dt_cube["A05"]
            dt_cube.loc[dt_cube['A05'] == 0, 'A3101020202'] = 0

            dt_cube["A310105"] = (dt_cube["A31010402"] + dt_cube["A31010401"]) / dt_cube["A05"]
            dt_cube.loc[dt_cube['A05'] == 0, 'A310105'] = 0

            dt_cube["A310103"] = (dt_cube["A31010201"] + dt_cube["A31010202"]) / dt_cube["A05"]
            dt_cube.loc[dt_cube['A05'] == 0, 'A310103'] = 0

            for col in ["Measure", "A3101020202", "A310105", "A310103"]:
                col_list.append(col)
            dt_cube = dt_cube[col_list]

            # 宽表改长表
            dt_cube_melt = pd.melt(dt_cube,
                                   id_vars=["Scenario", "Year", "Entity", "Version", "Material", "Allocation", "Tax",
                                            "Department", "misc1",
                                            "misc2", "Period", "Measure"], var_name="Account").rename(
                columns={"value": "data"})
            # dt_cube = dt_cube_melt[
            #     ~((dt_cube_melt["Scenario"] == "Actual") & (dt_cube_melt["Account"] == "A310103"))].rename(
            #     columns={"value": "data"})

            save_cube(dt_cube_melt, "", pivot=False)


def main(p1, p2):
    print(p2)
    if "folderId" in p2:
        del p2['folderId']
    if "elementName" in p2:
        del p2['elementName']

    # 获取参数中的预算年份，并且计算出去年的年份用于后续取实际数使用
    year = p2['Year']
    front_year = int(year) - 1
    # 删掉P2中无用的参数
    for item in ['sheetName', 'sheetId']:
        del p2[item]
    rate_fix = p2.copy()
    fix = p2.copy()

    # 获取含税数据并计算保存
    measure = 'Expenses;Nomeasure'
    account = 'A05;A1001;A1002;A31010201;A3101020201;A3101020202;A310104010201;A3101040201;A310104;A310104;A3101040102;A31010402;A3101040101'

    fix = get_fix(fix, account, measure, 'Tax')
    dt_cube = get_cube_data(fix, pivot=True)
    if not dt_cube.empty:
        dt_budget, dt_actual_m, dt_rate = formal_dataframe(dt_cube, year, front_year)
        # 删掉多余的字段
        for col in ["A3101040101_x", "A3101040101_y"]:
            if col in dt_actual_m.columns.tolist():
                del dt_actual_m[col]
        if "A3101040101_y" in dt_budget.columns.tolist():
            del dt_budget["A3101040101_y"]
        dt_budget = dt_budget.rename(columns={"A3101040101_x": "A3101040101"})

        # 获取Actual TotalPeriod数据
        fix_actual = p2.copy()
        fix_actual["Measure"] = "Expenses"
        fix_actual["Account"] = "A3101040102;A31010402"
        fix_actual["Year"] = str(front_year)
        fix_actual["Scenario"] = "Actual"
        fix_actual["Period"] = "TotalPeriod"
        fix_actual = get_fix_to_str(fix_actual)
        cube = FinancialCube('BEWG', path='/Cube')
        if "->elementName{Electricity}->folderId{DIR120caca66e0b}" in fix_actual:
            fix_actual = fix_actual.replace("->elementName{Electricity}->folderId{DIR120caca66e0b}", "")
        cube_actual = cube.query(fix_actual, compact=False, pivot_dim='Account')
        cube_actual["Period"] = "Noperiod"

        fix_actual_period = p2.copy()
        fix_actual_period["Measure"] = "Expenses"
        fix_actual_period["Account"] = "A3101020203"
        fix_actual_period["Year"] = str(front_year)
        fix_actual_period["Scenario"] = "Actual"
        fix_actual_period["Period"] = "1;2;3;4;5;6;7;8;9;10;11;12"
        fix_actual_period = get_fix_to_str(fix_actual_period)
        if "->elementName{Electricity}->folderId{DIR120caca66e0b}" in fix_actual_period:
            fix_actual_period = fix_actual_period.replace("->elementName{Electricity}->folderId{DIR120caca66e0b}", "")
        cube_actual_period = cube.query(fix_actual_period, compact=False)

        dt_budget, dt_new = calc_acture_budget(dt_budget, cube_actual, cube_actual_period)
        dt_actural_m = calc_actual_for_month(dt_actual_m, dt_new)
        # 保存计算结果
        save_cube(dt_budget, '', False)
        save_cube(dt_actural_m, '', True)

        # 获取A31010202-电镀电费 计算全年电镀电费科目
        fix_actual_A31010202 = p2.copy()
        fix_actual_A31010202["Measure"] = "Expenses"
        fix_actual_A31010202["Account"] = "A31010202"
        fix_actual_A31010202["Year"] = str(front_year)
        fix_actual_A31010202["Scenario"] = "Actual"
        fix_actual_A31010202["Period"] = "1;2;3;4;5;6;7;8;9;10;11;12;Adjust"
        fix_actual_A31010202 = get_fix_to_str(fix_actual_A31010202)
        if "->elementName{Electricity}->folderId{DIR120caca66e0b}" in fix_actual_A31010202:
            fix_actual_A31010202 = fix_actual_A31010202.replace("->elementName{Electricity}->folderId{DIR120caca66e0b}",
                                                                "")
        cube_actual_A31010202 = cube.query(fix_actual_A31010202, compact=False)

        cube_actual_A31010202 = cube_actual_A31010202.groupby(
            by=["Measure", "Scenario", "Year", "Entity", "Version", "Material",
                "Allocation", "Tax", "Department", "misc1", "misc2", "Account"], as_index=False).sum()
        cube_actual_A31010202["Period"] = "Noperiod"

        cube.save(data=cube_actual_A31010202)

    # 获取不含税数据并计算保存
    measure = 'Expenses'
    account = 'Base(A310102,0);Base(A310104,0)'
    tax = 'TaxRate;Tax'
    rate_fix = get_fix(rate_fix, account, measure, tax)
    dt_rate_cube = get_cube_data(rate_fix, pivot=False)
    # 删除数据
    del_no_tax_data(p2)
    if not dt_rate_cube.empty:
        # 根据规则再次过滤数据并分类
        dt_rate_data, dt_actural_m, dt_rate = formal_dataframe(dt_rate_cube, year, front_year)
        if dt_rate_data.size > 0:
            # 计算不含税结果
            dt_budget_no_tax = calc_budget_tax(dt_rate_data, dt_rate)
            save_cube(dt_budget_no_tax, "", pivot=False)

    # 计算吨水电耗
    water_fix = p2.copy()
    water_fix["Year"] = str(year) + ";" + str(front_year)
    water_power_per(water_fix)


if __name__ == '__main__':
    try:
        from bewg.conf._evn import p1, p2
    except:
        pass
    main(p1, p2)
