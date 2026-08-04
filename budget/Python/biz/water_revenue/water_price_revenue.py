import sys

sys.path.append('../../')
import pandas as pd
from deepfos.element.finmodel import FinancialCube
from deepfos.element.variable import Variable
import asyncio
from deepfos.element.finmodel import AsyncFinancialCube
import copy
import time
pd.set_option('display.max_rows', 500)
pd.set_option('display.max_columns', 100)
pd.set_option('display.width', 1000)

# added by wlm
# added in 20220823
# added for 水价与电费科目复制及计算

# modified by lyx
# modified in 20230809
# modified for 税率转换新增修改；污水收入审核指标计算


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


def notax_noperiod(p2, cube, year, last_year, entity):
    # 计算notax合计
    expression = "Account{Base(PL0101,0);YW0105;YW0108}->Scenario{Budget;Forecast;Actual}->Measure{Expenses}->" \
                 "Period{1;2;3;4;5;6;7;8;9;10;11;12}->Tax{Notax}->Year{%s;%s}->Entity{%s}" % (year, last_year, entity)
    data = cube.query(expression=expression, compact=False)

    variable = Variable(element_name="Variable")
    val = variable.get_value("Forcast")

    df_bg = data.loc[(data["Scenario"] == "Budget") & (data["Year"] == year)]
    if val == "Actual":
        df_ac = data.loc[(data["Scenario"] == "Actual") & (data["Year"] == last_year)
                         & (data['Period'].isin(['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']))]
        df = pd.concat([df_bg, df_ac])
    else:
        df_ac = data.loc[(data["Scenario"] == "Actual") & (data["Year"] == last_year)
                         & (data['Period'].isin(['1', '2', '3', '4', '5', '6', '7', '8', '9']))]
        df_fc = data.loc[(data["Scenario"] == "Forecast") & (data["Year"] == last_year)
                         & (data['Period'].isin(['10', '11', '12']))]
        df_ac = pd.concat([df_ac, df_fc])
        df_ac["Scenario"] = "Actual"
        df = pd.concat([df_bg, df_ac])

    df = df.groupby(['Year', 'Version', 'Entity', 'Material', 'Tax', 'Scenario', 'Allocation',
                     'Account', 'Department', 'Measure', 'Misc1', 'Misc2'],
                    as_index=False)['data'].sum()
    df["Period"] = "Noperiod"

    # 保存不含税合计信息
    r = cube.save(df)

    return


def data_get_clear(p2, fix, year, last_year, entity):

    # 获取预算数税率
    rate_fix1 = copy.deepcopy(fix)
    rate_fix1['Account'] = 'Base(PL0101,0);YW0105;YW0108'
    rate_fix1['Scenario'] = 'Budget'
    rate_fix1['Measure'] = 'Expenses'
    rate_fix1['Period'] = "Remove(Base(TotalPeriod,0),Adjust)"
    rate_fix1['Year'] = year
    rate_fix1['Tax'] = 'Taxrate'
    rate_fix1 = get_fix_to_str(rate_fix1)
    print(rate_fix1)


    # 获取实际数税率
    rate_fix2 = copy.deepcopy(fix)
    rate_fix2['Account'] = 'Base(PL0101,0);YW0105;YW0108'
    rate_fix2['Scenario'] = "Actual"
    rate_fix2['Measure'] = 'Expenses'
    rate_fix2['Period'] = "Remove(Base(TotalPeriod,0),Adjust)"
    rate_fix2['Year'] = last_year
    rate_fix2['Tax'] = 'Taxrate'
    rate_fix2 = get_fix_to_str(rate_fix2)
    print(rate_fix2)

    del p2['Year']
    del p2['Entity']

    # 计算：获取含税 year，year-1年的 预测、预算、实际金额
    expression1 = "Account{Base(PL0101,0);YW0105;YW0108}->Scenario{Budget;Forecast;Actual}->Measure{Expenses}->" \
                  "Period{1;2;3;4;5;6;7;8;9;10;11;12}->Tax{Tax;Notax}->Year{%s;%s}->Entity{%s}->Version{Y1}" \
                  % (year, last_year, entity)

    # 删除不含税预算金额
    del_fix_budget1 = "Year{%s}->Version{Y1}->Material{Nomaterial}->Allocation{Original}->Tax{Notax}->" \
                      "Department{Operation}->Misc1{Nomisc1}->Misc2{Nomisc2}->Account{Base(PL0101,0);YW0105;YW0108}->" \
                      "Scenario{Budget}->Measure{Expenses}->Period{1;2;3;4;5;6;7;8;9;10;11;12}->Entity{%s}" % (
                          year, entity)

    # 删除不含税预测
    del_fix_forecast = "Year{%s}->Version{Y1}->Material{Nomaterial}->Allocation{Original}->Tax{Notax}->" \
                       "Department{Operation}->Misc1{Nomisc1}->Misc2{Nomisc2}->Account{Base(PL0101,0);YW0105;YW0108}->" \
                       "Scenario{Forecast}->Measure{Expenses}->Period{10;11;12}->Entity{%s}" % (last_year, entity)


    # 删除不含税预算数合计
    del_fix_budget2 = "Year{%s}->Version{Y1}->Material{Nomaterial}->Allocation{Original}->Tax{Notax}->" \
                      "Department{Operation}->Misc1{Nomisc1}->Misc2{Nomisc2}->Account{Base(PL0101,0);YW0105;YW0108}->" \
                      "Scenario{Budget}->Measure{Expenses}->Period{Noperiod}->Entity{%s}" % (year, entity)

    # 删除不含税实际数合计
    del_fix_actual = "Year{%s}->Version{Y1}->Material{Nomaterial}->Allocation{Original}->Tax{Notax}->" \
                     "Department{Operation}->Misc1{Nomisc1}->Misc2{Nomisc2}->Account{Base(PL0101,0);YW0105;YW0108}->" \
                     "Scenario{Actual}->Measure{Expenses}->Period{Noperiod}->Entity{%s}" % (last_year, entity)

    async def cube_deal():
        cube = AsyncFinancialCube("WS_cube")
        results = await asyncio.gather(
            cube.query(rate_fix1, compact=False),
            cube.query(rate_fix2, compact=False),
            cube.query(expression=expression1,  compact=False),
            cube.delete(del_fix_budget1),
            cube.delete(del_fix_forecast),
            cube.delete(del_fix_budget2),
            cube.delete(del_fix_actual),
        )
        return results

    data_result = asyncio.run(cube_deal())
    return data_result


def main(p1, p2):
    rename_map = {
        "Entity_wb1": "Entity",
        "Year_wb1": "Year",
        "Measure_wb1": "Measure",
        "Scenario_wb1": "Scenario",
        "Allocation_wb1": "Allocation",
        "Version_wb2": "Version",
        "Department_wb1": "Department",
        "Tax_wb1": "Tax",
        "Misc1_wb1": "Misc1",
        "Misc2_wb1": "Misc2"
    }
    p2 = {rename_map.get(key, key): value for key, value in p2.items()}

    for i in ['elementName', 'folderId', 'sheetName', 'sheetId']:
        if i in p2:
            del p2[i]

    cube = FinancialCube("WS_cube")
    year = p2['Year']
    last_year = str(int(year) - 1)
    entity = p2["Entity"]
    fix = copy.deepcopy(p2)

    data = data_get_clear(p2, fix, year, last_year, entity)

    # 1、获取预算数税率信息
    dt_rate_bg = data[0][
        ['Account', 'Period', 'Year', 'Scenario', 'Entity', 'Material', 'Department', 'Allocation', 'Misc1', 'Misc2',
         'Version', 'Measure', 'data']]
    dt_rate_bg = dt_rate_bg.rename(columns={"data": "taxrate"})


    # 2、获取10、11、12月预测税率 信息
    dt_rate_fc = data[1][
        ['Account', 'Period', 'Year', 'Scenario', 'Entity', 'Material', 'Department', 'Allocation', 'Misc1', 'Misc2',
         'Version', 'Measure', 'data']]
    dt_rate_fc = dt_rate_fc.loc[dt_rate_fc["Period"].isin(["10", "11", "12"])]
    dt_rate_fc = dt_rate_fc.rename(columns={"data": "taxrate"})
    dt_rate_fc["Scenario"] = "Forecast"
    # dt_rate = pd.concat([dt_rate_ac, dt_rate_bg, dt_rate_fc])
    dt_rate = pd.concat([dt_rate_bg, dt_rate_fc])

    # 3、获取需要计算税率的金额
    tax_data = data[2]
    # print(tax_data)


    # 4、计算预算+预测税率转换
    # 4.1 提取year-1年 预测金额
    dt_forecast = tax_data[
        (tax_data['Year'] == last_year) & (tax_data['Scenario'] == "Forecast") &
        (tax_data['Tax'] == 'Tax') &
        (tax_data['Measure'] == "Expenses") & (
            tax_data['Period'].isin(['10', '11', '12']))]
    print('预测',dt_forecast)

    # 4.2 提取year年 预算金额
    dt_budget = tax_data[
        (tax_data['Year'] == year) & (tax_data['Scenario'] == "Budget") &
        (tax_data['Tax'] == 'Tax') &(tax_data['Measure'] == "Expenses") & (
            tax_data['Period'].isin(['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']))]
    print('预算',dt_budget)

    tax_data1 = pd.concat([dt_forecast, dt_budget])

    # 4.3 拼接税率
    rate_merge_tax = pd.merge(tax_data1, dt_rate, how='left',
                              on=['Account', 'Period', 'Year', 'Scenario', 'Entity', 'Material', 'Department',
                                  'Allocation', 'Misc1', 'Misc2', 'Version', 'Measure'])
    # 4.4 新增需求，将未取到税率的科目，税率设置为0
    rate_merge_tax["taxrate"] = rate_merge_tax["taxrate"].fillna(0)

    rate_merge_notax = rate_merge_tax.copy()
    del rate_merge_tax['taxrate']
    rate_merge_notax = rate_merge_notax[rate_merge_notax['taxrate'].notna()]

    if rate_merge_notax.size > 0:
        rate_merge_notax['data'] = rate_merge_notax['data'] / (1 + rate_merge_notax['taxrate'])
        rate_merge_notax['Tax'] = 'Notax'
        # print(rate_merge_notax)
        del rate_merge_notax['taxrate']
        # 保存预算+预测不含税信息
        r = cube.save(rate_merge_notax)

    # 5、计算实际税率转换 不含税->含税
    # 5.1 提取year-1年 实际金额
    dt_actual = tax_data[
        (tax_data['Year'] == last_year) & (tax_data['Scenario'] == "Actual") & (tax_data['Tax'] == 'Notax')&
        (tax_data['Measure'] == "Expenses") & (
            tax_data['Period'].isin(['1', '2', '3', '4', '5', '6', '7', '8', '9', '10', '11', '12']))]
    print('实际',dt_budget)

    # 5.2 拼接税率
    dt_rate = data[1]
    dt_rate_actual = dt_rate.rename(columns={"data": "taxrate"})
    rate_actaul_notax = pd.merge(dt_actual, dt_rate_actual, how='left',
                              on=['Account', 'Period', 'Year', 'Scenario', 'Entity', 'Material', 'Department',
                                  'Allocation', 'Misc1', 'Misc2', 'Version', 'Measure'])
    # 5.3 新增需求，将未取到税率的科目，税率设置为0
    rate_actaul_notax["taxrate"] = rate_actaul_notax["taxrate"].fillna(0)

    rate_actaul_tax = rate_actaul_notax.copy()
    del rate_actaul_notax['taxrate']
    rate_actaul_tax = rate_actaul_tax[rate_actaul_tax['taxrate'].notna()]

    if rate_actaul_tax.size > 0:
        rate_actaul_tax['data'] = rate_actaul_tax['data'] * (1 + rate_actaul_tax['taxrate'])
        rate_actaul_tax['Tax'] = 'Tax'
        # print(rate_merge_notax)
        del rate_actaul_tax['taxrate']
        # 保存不含税信息
        r = cube.save(rate_actaul_tax)



    # 6、新增计算notax合计
    notax_noperiod(p2, cube, year, last_year, entity)
    return


if __name__ == '__main__':
    from common.__debug import para1, para2

    p2 =  {'elementName': 'Revenue',
           'folderId': 'DIRb6550dd20485',
           'sheetName': '水价与收入',
           'sheetId': 'SHT491538d6904b401a829131b3b70f2c9c',
           'Year_wb1': '2025',
           'Entity_wb1': 'Y3720241908',
           'Version_wb2': 'Y1',
           'Department_wb1': 'Operation',
           'Scenario_wb1': 'Forecast',
           'Tax_wb1': 'Tax'}

    main(para1, p2)