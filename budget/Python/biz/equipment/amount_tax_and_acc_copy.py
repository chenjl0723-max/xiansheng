import pandas as pd
from deepfos.element.finmodel import FinancialCube


def calc_amount_inspection_tax(data, year, entity, form, department):
    cube = FinancialCube("WS_cube")
    list_account = list(set(data['Account'].tolist()))
    account = ";".join(list_account)
    pov = {'Year': year}
    data = data.rename(columns={"data": "org_data"})

    # 根据year entity account 查询对应税率 其他维度为指定
    expression_rate = "Entity{%s}->Account{%s}->Tax{Taxrate}->Version{Y1}->Material{Nomaterial}->Allocation{Original}->Misc1{Nomisc1}->Misc2{Nomisc2}->Department{Operation}->Measure{Expenses}->Scenario{Budget}->Period{Noperiod}" % (entity,account)
    data_rate = cube.query(expression=expression_rate, pov=pov, compact=False)
    data_rate = data_rate[["Year", "Entity", "Account", "data"]].rename(columns={"data": "rate"})
    # 合并含税数据和税率数据
    data_and_rate = pd.merge(data, data_rate, how="left")
    # 如果未取出税率，则将税率设置为0
    data_and_rate["rate"] = data_and_rate["rate"].fillna(0)
    # 计算不含税数
    data_and_rate['data'] = data_and_rate['org_data'] / (1 + data_and_rate['rate'])
    del data_and_rate['org_data']
    del data_and_rate['rate']

    if data_and_rate.size > 0:
        # 根据表单确定存cube数据    维度的值
        data_and_rate['Department'] = department
        data_and_rate['Scenario'] = "Budget"
        data_and_rate['Version'] = "Y1"
        data_and_rate['Period'] = "12"
        data_and_rate['Material'] = "Nomaterial"
        data_and_rate['Allocation'] = 'Original'
        data_and_rate['Tax'] = "Notax"
        # data_and_rate['Misc1'] = "Nomisc1"
        data_and_rate['Misc2'] = "Nomisc2"
        # if form in ["SHTc9305cc22a394562bcfd253dedf3ef96", "SHT89429863186a4aae84c97784df8bbab2", "SHT96fb18823e754c28870c60d58722a533",
        #             "SHT9ef716c265e2417b88616432e08031d1", "SHT8cf0b2092916424e979b5a32c04d1f84","SHT6d671977518d4238bad73b64c8db5d09",
        #             "SHTac171af4488d4d6eb8535911dafba492","SHTcabbd564f0a342529949d564d630635b","SHTff954af2b85e4aa2ba8bd544d2aed0f5","SHT208a02af77494471b35ecbcf31aebec0"]:
        #     data_and_rate['Measure'] = "Expenses"
        print('不含税', data_and_rate)
        cube.save(data=data_and_rate)


def account_copy(tax_data, notax_data, year, entity, acc):
    cube = FinancialCube("BEWG")
    year_last = str(int(year) - 1)
    if acc == "A82":
        tax_data = tax_data[tax_data['Account'].isin(["A31020101", "A31020102"])]
        notax_data = notax_data[notax_data['Account'].isin(["A31020101", "A31020102"])]
        tax_data['Account'] = "A82"
        notax_data['Account'] = "A82"
    else:
        tax_data = tax_data[tax_data['Account'].isin(["A31020201", "A31020202"])]
        notax_data = notax_data[notax_data['Account'].isin(["A31020201", "A31020202"])]
        tax_data['Account'] = "A83"
        notax_data['Account'] = "A83"

    tax_data_actual = tax_data.copy()
    notax_data_actual = notax_data.copy()

    tax_data_actual['Year'] = year_last
    tax_data_actual['Scenario'] = 'Actural'
    notax_data_actual['Year'] = year_last
    notax_data_actual['Scenario'] = 'Actural'

    data = pd.concat([tax_data, notax_data, tax_data_actual, notax_data_actual])
    data = data.groupby(
        by=["Year", "Entity", "Department", "Scenario", "Version", "Account", "Measure", "Allocation", "Tax", "Misc1",
            "Misc2"], as_index=False)['data'].sum()
    cube.save(data=data)


# 根据Form判断，给account、measure赋值 TODO。。。。。。。
def del_cube(form, year, entity):
    if form == "SHT795c36a1e8624dda8bcf7ca2ee868a01":
        return
    cube = FinancialCube("WS_cube")
    param_am = {
        'SHTc9305cc22a394562bcfd253dedf3ef96': {'account': 'PL0102040201', 'measure': 'Expenses;Areaaccount;Regionaccount;Groupaccount','department':'Equipment','misc1':'Nomisc1'},  # 设备大修重置预算填报(非技改)
        'SHTac171af4488d4d6eb8535911dafba492': {'account': 'PL0301', 'measure': 'Expenses;Areaaccount;Regionaccount;Groupaccount','department':'Technical','misc1':'Base(#root,0)'},  # new设备大修重置预算填报(技改)

        'SHT89429863186a4aae84c97784df8bbab2': {'account': 'PL0102040203', 'measure': 'Expenses;Areaaccount;Regionaccount;Groupaccount','department':'Equipment','misc1':'Nomisc1'},  # 设施大修预算填报(非技改)
        'SHTcabbd564f0a342529949d564d630635b': {'account': 'PL0302', 'measure': 'Expenses;Areaaccount;Regionaccount;Groupaccount','department':'Technical','misc1':'Base(#root,0)'},  # new设施大修预算填报(技改)

        'SHT9ef716c265e2417b88616432e08031d1': {'account': 'PL010204010203', 'measure': 'Expenses','department':'Equipment','misc1':'Nomisc1'},  # 设备日常维护预算填报(非技改)
        'SHT8cf0b2092916424e979b5a32c04d1f84': {'account': 'PL0102040101', 'measure': 'Expenses','department':'Equipment','misc1':'Nomisc1'},  # 设施日常维护预算填报(非技改)
        'SHT6d671977518d4238bad73b64c8db5d09': {'account': 'PL010204010202;PL010204010201', 'measure': 'Expenses','department':'Equipment','misc1':'Nomisc1'},  # 设备日常维修预算填报(非技改)

        'SHT96fb18823e754c28870c60d58722a533': {'account': 'PL0102040202', 'measure': 'Expenses;Areaaccount;Regionaccount;Groupaccount','department':'Equipment','misc1':'Nomisc1'},  # 新增设备预算填报(非技改)
        'SHTff954af2b85e4aa2ba8bd544d2aed0f5': {'account': 'PL0303', 'measure': 'Expenses;Areaaccount;Regionaccount;Groupaccount','department':'Technical','misc1':'Base(#root,0)'},  # new新增设备预算填报(技改)

        'SHT208a02af77494471b35ecbcf31aebec0': {'account': 'PL0304', 'measure': 'Expenses;Areaaccount;Regionaccount;Groupaccount','department':'Technical','misc1':'Base(#root,0)'},  # new新增设施预算填报(技改)


    }

    table_param_am = param_am[form]

    expression_delete = "Year{%s}->Entity{%s}->Account{%s}->Tax{Notax;Tax}->Version{Y1}->Material{Nomaterial}->Allocation{Original}->Misc1{%s}->" \
                        "Misc2{Nomisc2}->Department{%s}->Measure{%s}->Scenario{Budget}->Period{12}" % (
                            year, entity, table_param_am['account'],table_param_am['misc1'], table_param_am['department'],table_param_am['measure'])
    cube.delete(expression_delete)
