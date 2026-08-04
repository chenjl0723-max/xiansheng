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


def get_cube_data():
    cube = FinancialCube("WS_cube")
    account_list = ['PL0102040101','PL010204010201','PL010204010202','PL010204010203','PL0102040201','PL0102040202','PL0102040203','PL0301','PL0302','PL0303','PL0304']

    account = ";".join(account_list)
    # 根据year entity account 查询对应税率 其他维度为指定
    expression_tax = "Year{2025}->Account{%s}->Entity{Base(1,0)}->Tax{Taxrate}->Version{Y1}->Material{Nomaterial}->Allocation{Original}->Misc1{Nomisc1}->Misc2{Nomisc2}->Department{Operation}->Measure{Expenses}->Scenario{Budget}->Period{Noperiod}" % account
    data_tax = cube.query(expression=expression_tax, compact=False)
    data_tax = data_tax[["Year", "Entity", "Account", "data"]].rename(columns={"data": "rate"})


    expression_data = "Year{2025}->Account{%s}->Entity{Base(1,0)}->Tax{Tax}->Version{Y1}->Material{Nomaterial}->Allocation{Original}->Misc1{Nomisc1}->Misc2{Nomisc2}->Department{Technical;Equipment}->Measure{Expenses}->Scenario{Budget}->Period{12}" % account
    data = cube.query(expression=expression_data, compact=False)

    data_and_rate = pd.merge(data, data_tax, how="left")
    # 如果未取出税率，则将税率设置为0
    data_and_rate["rate"] = data_and_rate["rate"].fillna(0)
    # 计算不含税数
    data_and_rate['data'] = data_and_rate['data'] / (1 + data_and_rate['rate'])
    print(1)
    data_and_rate['Tax'] = "Notax"
    del data_and_rate['rate']
    cube.save(data=data_and_rate)
def main(p1, p2):
    print('p2:', p2)
    get_cube_data()

if __name__ == '__main__':
    try:
        from common.__debug import para1, p2
    except:
        pass
    p2 = {'elementName': 'dailycare_equipment_float', 'folderId': 'DIRe667e90baafd',
          'sheetName': '设备日常维护预算填报', 'sheetId': 'SHT9ef716c265e2417b88616432e08031d1', 'Year_wb1': '2025',
          'Entity_wb1': 'Y1320210011', 'Department_wb1': 'Equipment', 'Scenario_wb1': 'Budget', 'Version_wb1': 'Y1'}

    main(para1, p2)
